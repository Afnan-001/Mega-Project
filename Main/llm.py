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


class GeminiRateLimiter:
    """Enforces client-side rate limits (RPM) and spacing to prevent 429 errors on free tiers."""

    RPM_LIMITS = {
        "gemini-3.8-flash": 10,
        "gemini-3.7-flash": 10,
        "gemini-3.5-flash": 10,
        "gemini-3.5-flash-lite": 10,
        "gemini-3.1-flash-lite": 10,
        "gemini-flash-latest": 10,
        "gemini-flash-lite-latest": 10,
        "gemini-2.5-flash-lite": 10,
    }
    DEFAULT_RPM = 10  # Free-tier safe default RPM across Gemini flash models

    def __init__(self):
        self.request_timestamps: dict[str, list[float]] = {}
        self.last_call_time: dict[str, float] = {}

    def get_rpm(self, model_name: str) -> int:
        clean_name = model_name.split("/")[-1].lower()
        for k, v in self.RPM_LIMITS.items():
            if k in clean_name:
                return v
        return self.DEFAULT_RPM

    def wait_if_needed(self, model_name: str):
        rpm = self.get_rpm(model_name)
        min_interval = 60.0 / rpm
        now = time.time()

        # Clean timestamps older than 60s
        history = [t for t in self.request_timestamps.get(model_name, []) if now - t < 60.0]
        self.request_timestamps[model_name] = history

        # Check if 60-second window quota is reached
        if len(history) >= rpm:
            sleep_needed = 60.0 - (now - history[0]) + 0.5
            if sleep_needed > 0:
                print(f"\n[GeminiRateLimiter] Rate window full ({len(history)}/{rpm} RPM for {model_name}). Sleeping {sleep_needed:.1f}s to stay within free tier limits...")
                time.sleep(sleep_needed)
                now = time.time()
                self.request_timestamps[model_name] = [t for t in self.request_timestamps.get(model_name, []) if now - t < 60.0]

        # Ensure minimum spacing between calls
        last_time = self.last_call_time.get(model_name, 0.0)
        elapsed = now - last_time
        if elapsed < min_interval and len(history) > 0:
            delay = min_interval - elapsed
            time.sleep(delay)

        self.last_call_time[model_name] = time.time()
        self.request_timestamps[model_name].append(time.time())


class GeminiModelManager:
    """Manages multi-model fallback chain when a model hits quota or rate limits."""

    DEFAULT_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash-lite",
    ]

    def __init__(self, initial_model: str | None = None):
        env_models = os.getenv("GEMINI_MODELS", "").strip()
        if env_models:
            models = [m.strip() for m in env_models.split(",") if m.strip()]
        else:
            models = list(self.DEFAULT_MODELS)

        if initial_model:
            if initial_model in models:
                models.remove(initial_model)
            models.insert(0, initial_model)

        self.models = models
        self.current_index = 0
        self.exhausted_models: set[str] = set()

    def get_current_model(self) -> str:
        return self.models[self.current_index]

    def rotate_model(self) -> str:
        """Rotate to next available model in fallback chain."""
        old_model = self.get_current_model()
        self.exhausted_models.add(old_model)

        for _ in range(len(self.models)):
            self.current_index = (self.current_index + 1) % len(self.models)
            candidate = self.models[self.current_index]
            if candidate not in self.exhausted_models:
                print(f"\n[GeminiModelManager] Model '{old_model}' free tier limit reached. Switching to fallback model '{candidate}'...")
                return candidate

        # If all exhausted, reset history and cycle
        print(f"\n[GeminiModelManager] All {len(self.models)} Gemini models exhausted once on current key. Resetting cycle...")
        self.exhausted_models.clear()
        self.current_index = (self.current_index + 1) % len(self.models)
        return self.models[self.current_index]


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
    """Unified LLM client wrapper supporting Gemini API and local Ollama backend with multi-model failover."""

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
            primary_model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            self.model_manager = GeminiModelManager(primary_model)
            self.rate_limiter = GeminiRateLimiter()
            self.key_manager = GeminiKeyManager(keys)
            self._configure_gemini_client()

    @property
    def model_name(self) -> str:
        if self.provider == "ollama":
            return self.backend.model_name
        return self.model_manager.get_current_model()

    def _configure_gemini_client(self):
        current_key = self.key_manager.get_current_key()
        genai.configure(api_key=current_key, transport="rest")
        system_instruction = self.sys_msg if self.sys_msg else None
        generation_config = genai.GenerationConfig(temperature=self.temperature)
        current_model = self.model_manager.get_current_model()
        self.gemini_model = genai.GenerativeModel(
            model_name=current_model,
            generation_config=generation_config,
            system_instruction=system_instruction,
        )

    def get_response(self, usr_msg: str, max_retries: int | None = None) -> str:
        if self.provider == "ollama":
            return self.backend.get_response(usr_msg, max_retries=max_retries or 3)

        num_keys = max(1, len(self.key_manager.keys))
        num_models = len(self.model_manager.models)
        if max_retries is None:
            max_retries = num_keys * num_models * 2

        key_rotations_on_current_model = 0

        for attempt in range(max_retries):
            current_model = self.model_manager.get_current_model()
            # Enforce RPM limits before dispatching request
            self.rate_limiter.wait_if_needed(current_model)

            try:
                response = self.gemini_model.generate_content(usr_msg)
                if response and response.text:
                    return response.text.strip()
                raise ValueError(f"Empty response received from Gemini model {current_model}.")
            except Exception as e:
                err_str = str(e).lower()
                is_unavailable = any(
                    term in err_str
                    for term in ["404", "not found", "no longer available", "not available", "unsupported"]
                )
                is_quota_or_rate = any(
                    term in err_str
                    for term in ["429", "quota", "resource_exhausted", "rate_limit", "limit", "exhausted", "per-day", "rpd"]
                )

                if is_unavailable:
                    print(f"\n[LLM] Model '{current_model}' unavailable on this API ({e}). Switching to next model...")
                    self.model_manager.rotate_model()
                    self._configure_gemini_client()
                    key_rotations_on_current_model = 0
                    time.sleep(0.5)
                elif is_quota_or_rate:
                    old_model = current_model
                    new_model = self.model_manager.rotate_model()
                    # If all models completed a pass, rotate to next key
                    if len(self.model_manager.exhausted_models) == 0 and len(self.key_manager.keys) > 1:
                        self.key_manager.rotate_key()
                    print(f"\n[LLM] Free tier limit reached on '{old_model}' ({e}). Switched to fallback model '{new_model}'...")
                    self._configure_gemini_client()
                    time.sleep(1.0)
                else:
                    if attempt < max_retries - 1:
                        print(f"[LLM] Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in 2s...")
                        time.sleep(2.0)
                    else:
                        raise e

        raise RuntimeError("Failed to generate response after rotating through all Gemini models and API keys.")


if __name__ == "__main__":
    print("Testing LLM wrapper...")
    llm = LLM(sys_msg="You are a helpful assistant.", provider="ollama")
    print(f"Ollama response test: {llm.get_response('Say hello in 3 words!')}")
