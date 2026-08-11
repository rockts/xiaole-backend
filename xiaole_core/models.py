from dataclasses import dataclass
import requests

from .errors import ModelUnavailable


class ModelError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class ModelResult:
    text: str
    model: str
    fallback: bool = False


class ModelRouter:
    def __init__(self, primary, fallback=None, primary_name="deepseek", fallback_name="qwen"):
        self.primary, self.fallback = primary, fallback
        self.primary_name, self.fallback_name = primary_name, fallback_name

    def complete(self, system_prompt: str, messages: list[dict], request_id: str) -> ModelResult:
        try:
            return ModelResult(self.primary.complete(system_prompt, messages, request_id), self.primary_name)
        except ModelError as exc:
            if not exc.retryable or not self.fallback:
                raise ModelUnavailable("model service unavailable") from exc
        try:
            return ModelResult(self.fallback.complete(system_prompt, messages, request_id), self.fallback_name, True)
        except ModelError as exc:
            raise ModelUnavailable("model service unavailable") from exc

    def classify(self, message: str, history: list[dict], request_id: str) -> str:
        result = self.complete("Return exactly one of: conversation, memory, action.", [*history, {"role":"user","content":message}], request_id)
        return result.text.strip().lower()


class OpenAICompatibleProvider:
    def __init__(self, url: str, api_key: str, model: str, timeout: float = 60, transport=None):
        self.url, self.api_key, self.model, self.timeout = url, api_key, model, timeout
        self.transport = transport or requests.Session()

    def complete(self, system_prompt: str, messages: list[dict], request_id: str) -> str:
        if not self.api_key or self.api_key.startswith("your_"):
            raise ModelError("model API key is not configured", retryable=False)
        try:
            response = self.transport.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json", "X-Request-ID":request_id},
                json={"model":self.model,"messages":[{"role":"system","content":system_prompt},*messages],"temperature":.3,"max_tokens":1024,"stream":False},
                timeout=self.timeout,
            )
            if response.status_code in (401,403): raise ModelError("model authentication failed", False)
            if response.status_code == 429 or response.status_code >= 500: raise ModelError("model service unavailable", True)
            if response.status_code >= 400: raise ModelError("model request rejected", False)
            text = response.json()["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip(): raise ModelError("invalid model response", True)
            return text.strip()
        except ModelError:
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ModelError("model transport failed", True) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelError("invalid model response", True) from exc
