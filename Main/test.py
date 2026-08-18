import json
from llm import LLM

# ----------------------------
# Helper
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
# Test LLM API
# ----------------------------

llm = LLM()

try:
    print(f"Configured Model: {llm.model}")

    response = llm.get_response("Hello, who are you?")

    print("\nResponse:\n")
    print(response)

except Exception as e:
    print(f"\nError: {e}")