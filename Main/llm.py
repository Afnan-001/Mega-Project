import litellm
import time
import json

from log_file import LLMCallLogger

# Drop unsupported parameters automatically
litellm.drop_params = True


# ----------------------------
# Helper: Make JSON Safe
# ----------------------------

def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        return make_json_safe(vars(obj))
    else:
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)


# ----------------------------
# LLM Class
# ----------------------------

class LLM:

    def __init__(
        self,
        model="azure/si-ia-gpt-5",
        sys_msg="You are an AI assistant that helps people find information.",
        log_path="common_log.jsonl",
        temperature=0.7
    ):
        self.model = model

        # Credentials provided
        self.api_base = "http://10.221.0.164:4000"
        self.api_version = "2025-01-01-preview"
        self.api_key = "sk-81VWPJdAXK2Jkuj_4vXI7Q"

        self.sys_msg = sys_msg
        self.temperature = temperature

        self.logger = LLMCallLogger(log_path)

    # ----------------------------
    # LLM Call
    # ----------------------------

    def get_response(self, usr_msg, sys_msg=None):

        if sys_msg:
            self.sys_msg = sys_msg

        start = time.time()

        messages = [
            {
                "role": "system",
                "content": self.sys_msg
            },
            {
                "role": "user",
                "content": usr_msg
            }
        ]

        try:

            response = litellm.completion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                api_version=self.api_version,
                temperature=self.temperature,
                messages=messages
            )

            latency_ms = int((time.time() - start) * 1000)

            text = response["choices"][0]["message"]["content"]

            usage = make_json_safe(response.get("usage", {}))
            safe_messages = make_json_safe(messages)

            self.logger.log_success(
                provider="azure-openai",
                model_or_deployment=self.model,
                messages=safe_messages,
                response_text=text,
                usage=usage,
                latency_ms=latency_ms
            )

            return text

        except Exception as e:

            latency_ms = int((time.time() - start) * 1000)

            self.logger.log_error(
                provider="azure-openai",
                model_or_deployment=self.model,
                messages=make_json_safe(messages),
                error=str(e),
                latency_ms=latency_ms
            )

            raise