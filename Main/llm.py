from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Force UTF-8 stdout encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# GeminiKeyManager loads keys securely from environment variables (.env)
class GeminiKeyManager:
    """Manages multi-key rotation for Gemini API when quota/rate limits are exhausted."""

    def __init__(self, keys: list[str] | None = None):
        if keys:
            parsed_keys = list(keys)
        else:
            env_keys = os.getenv("GEMINI_API_KEYS", "")
            parsed_keys = [k.strip() for k in env_keys.split(",") if k.strip()]

        # Add single GEMINI_API_KEY if present and not already in list
        single_key = os.getenv("GEMINI_API_KEY", "").strip()
        if single_key and single_key not in parsed_keys:
            parsed_keys.insert(0, single_key)
        self.keys = parsed_keys
        self.current_index = 0

    def get_current_key(self) -> str:
        if not self.keys:
            raise ValueError("No Gemini API keys configured.")
        return self.keys[self.current_index]

    def rotate_key(self) -> str:
        """Rotate to the next available API key in the list."""
        old_key = self.get_current_key()
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key = self.get_current_key()
        print(
            f"[GeminiKeyManager] Key exhausted ({old_key[:12]}...). "
            f"Rotated to key #{self.current_index + 1}/{len(self.keys)} ({new_key[:12]}...)"
        )
        return new_key


class OllamaLLM:
    """Ollama local LLM client wrapper (e.g. Qwen2.5 / Llama3)."""

    def __init__(
        self,
        sys_msg: str | None = None,
        model_name: str = "qwen2.5:7b-instruct-q4_K_M",
        temperature: float = 0.0,
        base_url: str = "http://localhost:11434",
        json_mode: bool = True,
    ):
        self.sys_msg = sys_msg
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = base_url.rstrip("/")
        self.json_mode = json_mode

    def get_response(self, usr_msg: str, max_retries: int = 3) -> str:
        messages = []
        if self.sys_msg:
            messages.append({"role": "system", "content": self.sys_msg})
        messages.append({"role": "user", "content": usr_msg})

        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_ctx": 4096,
                    },
                }
                # On final retry, drop json_mode if Ollama strict json constrained sampling failed
                if self.json_mode and attempt == 0:
                    payload["format"] = "json"

                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/api/chat",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )

                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    content = result.get("message", {}).get("content", "").strip()
                    if content:
                        return content
                    raise ValueError("Empty response received from Ollama model.")
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[OllamaLLM] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in 1s...")
                    time.sleep(1)
                else:
                    raise e

        raise RuntimeError("Failed to generate response from Ollama model.")


class LLM:
    """Unified LLM client wrapper supporting Gemini API and local Ollama backend."""

    def __init__(
        self,
        sys_msg: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.0,
        keys: list[str] | None = None,
        provider: str | None = None,
    ):
        provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower().strip()
        self.provider = provider
        self.sys_msg = sys_msg
        self.temperature = temperature

        if self.provider == "ollama":
            target_model = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
            self.backend = OllamaLLM(
                sys_msg=sys_msg,
                model_name=target_model,
                temperature=temperature,
            )
        else:
            target_model = model_name or "gemini-3.6-flash"
            self.model_name = target_model
            self.key_manager = GeminiKeyManager(keys)
            self._configure_gemini_client()

    def _configure_gemini_client(self):
        current_key = self.key_manager.get_current_key()
        genai.configure(api_key=current_key)
        system_instruction = self.sys_msg if self.sys_msg else None
        generation_config = genai.GenerationConfig(temperature=self.temperature)
        self.gemini_model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

    def get_response(self, usr_msg: str, max_retries: int | None = None) -> str:
        if self.provider == "ollama":
            return self.backend.get_response(usr_msg, max_retries=max_retries or 3)

        if max_retries is None:
            max_retries = len(self.key_manager.keys) * 2

        for attempt in range(max_retries):
            try:
                response = self.gemini_model.generate_content(usr_msg)
                if response and response.text:
                    return response.text.strip()
                raise ValueError("Empty response received from Gemini model.")
            except Exception as e:
                err_str = str(e).lower()
                is_quota_err = any(
                    term in err_str
                    for term in ["429", "quota", "resource_exhausted", "rate_limit", "exhausted", "limit", "invalid_api_key", "403"]
                )
                if is_quota_err and len(self.key_manager.keys) > 1:
                    print(f"[LLM] Key quota/rate limit error encountered: {e}")
                    self.key_manager.rotate_key()
                    self._configure_gemini_client()
                    time.sleep(0.5)
                else:
                    if attempt < max_retries - 1:
                        print(f"[LLM] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying...")
                        time.sleep(1)
                    else:
                        raise e

        raise RuntimeError("Failed to generate response after rotating through all Gemini API keys.")


if __name__ == "__main__":
    print("Testing LLM wrapper...")
    llm = LLM(sys_msg="You are a helpful assistant.", provider="ollama")
    print(f"Ollama response test: {llm.get_response('Say hello in 3 words!')}")
