from dataclasses import dataclass
import logging
import requests

from .errors import ModelUnavailable


logger = logging.getLogger(__name__)


class ModelError(Exception):
    def __init__(
        self,
        message: str,
        retryable: bool = False,
        category: str = "unknown",
    ):
        super().__init__(message)
        self.retryable = retryable
        self.category = category


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
            logger.warning(
                "model_primary_failed provider=%s category=%s "
                "request_id=%s fallback=%s",
                self.primary_name,
                exc.category,
                request_id,
                bool(exc.retryable and self.fallback),
            )
            if not exc.retryable or not self.fallback:
                raise ModelUnavailable("model service unavailable") from exc
        try:
            return ModelResult(self.fallback.complete(system_prompt, messages, request_id), self.fallback_name, True)
        except ModelError as exc:
            logger.warning(
                "model_fallback_failed provider=%s category=%s request_id=%s",
                self.fallback_name,
                exc.category,
                request_id,
            )
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
            raise ModelError(
                "model API key is not configured",
                retryable=False,
                category="configuration",
            )
        try:
            response = self.transport.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type":"application/json", "X-Request-ID":request_id},
                json={"model":self.model,"messages":[{"role":"system","content":system_prompt},*messages],"temperature":.3,"max_tokens":1024,"stream":False},
                timeout=self.timeout,
            )
            if response.status_code in (401,403):
                raise ModelError("model authentication failed", False, "authentication")
            if response.status_code == 402:
                if self._is_billing_or_quota_error(response):
                    raise ModelError(
                        "model billing or quota unavailable",
                        True,
                        "billing_quota",
                    )
                raise ModelError("model request rejected", False, "request_rejected")
            if response.status_code == 429:
                raise ModelError("model service unavailable", True, "rate_limit")
            if response.status_code >= 500:
                raise ModelError("model service unavailable", True, "service_unavailable")
            if response.status_code >= 400:
                raise ModelError("model request rejected", False, "request_rejected")
            text = response.json()["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ModelError("invalid model response", True, "invalid_response")
            return text.strip()
        except ModelError:
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ModelError("model transport failed", True, "transport") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelError("invalid model response", True, "invalid_response") from exc

    @staticmethod
    def _is_billing_or_quota_error(response) -> bool:
        try:
            payload = response.json()
        except (TypeError, ValueError):
            return False

        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        if not isinstance(error, dict):
            return False
        fields = (error.get("code"), error.get("type"), error.get("message"))
        details = " ".join(str(value).lower() for value in fields if value)
        markers = (
            "insufficient balance",
            "insufficient_balance",
            "account balance",
            "billing",
            "quota",
            "余额不足",
            "额度不足",
        )
        return any(marker in details for marker in markers)
