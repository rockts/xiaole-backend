import requests
from urllib.parse import urljoin

from ..errors import MemoryUnavailable
from ..schemas import MemoryResult, ProfileGatewayResponse


class MemoryGateway:
    def __init__(self, base_url: str, token: str = "", timeout: float = 20, transport=None):
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), token, timeout
        self.transport = transport or requests.Session()

    def ask(self, question: str, context: list[dict], request_id: str) -> MemoryResult:
        headers = {"X-Request-ID": request_id}
        if self.token:
            headers["X-KOS-Token"] = self.token
        try:
            response = self.transport.post(f"{self.base_url}/ask", json={"q":question,"mode":"ask","context":context}, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                raise MemoryUnavailable("knowledge system unavailable")
            body = response.json()
        except MemoryUnavailable:
            raise
        except Exception as exc:
            raise MemoryUnavailable("knowledge system unavailable") from exc
        if not isinstance(body, dict) or not body.get("ok") or not isinstance(body.get("answer"), str) or not isinstance(body.get("sources"), list):
            raise MemoryUnavailable("knowledge system returned an invalid response")
        sources = []
        for raw_source in body["sources"]:
            if not isinstance(raw_source, dict):
                sources.append(raw_source)
                continue
            source = dict(raw_source)
            for field in ("open_url", "preview_url"):
                value = source.get(field)
                if isinstance(value, str) and value.startswith("/"):
                    source[field] = urljoin(self.base_url + "/", value)
            sources.append(source)
        confidence = "degraded" if (body.get("flags") or {}).get("degraded") else ("grounded" if sources else "no_sources")
        return MemoryResult(answer=body["answer"], sources=sources, confidence=confidence, request_id=request_id)

    def _get(self, path: str, request_id: str) -> dict:
        headers = {"X-Request-ID": request_id}
        if self.token: headers["X-KOS-Token"] = self.token
        try:
            response = self.transport.get(f"{self.base_url}{path}", headers=headers, timeout=self.timeout)
            if response.status_code != 200: raise MemoryUnavailable("knowledge system unavailable")
            body = response.json()
        except MemoryUnavailable:
            raise
        except Exception as exc:
            raise MemoryUnavailable("knowledge system unavailable") from exc
        if not isinstance(body, dict): raise MemoryUnavailable("knowledge system returned an invalid response")
        return body

    def status(self, request_id: str) -> dict: return self._get("/api/v1/status/intelligence", request_id)
    def knowledge(self, request_id: str) -> dict: return self._get("/api/v1/status/knowledge", request_id)
    def profile(self, request_id: str) -> ProfileGatewayResponse:
        headers = {"X-Request-ID": request_id}
        if self.token: headers["X-KOS-Token"] = self.token
        try:
            response = self.transport.get(f"{self.base_url}/api/v1/profile", headers=headers, timeout=self.timeout)
        except requests.Timeout:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_timeout"])
        except requests.ConnectionError:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_connect_error"])
        except Exception:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_connect_error"])
        status = response.status_code
        if status in (401, 403):
            return ProfileGatewayResponse(result="unauthorized", reason_codes=[f"profile_http_{status}"])
        if status == 404:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_http_404"])
        if status >= 500:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_http_5xx"])
        if status != 200:
            return ProfileGatewayResponse(result="unavailable", reason_codes=["profile_connect_error"])
        try:
            body = response.json()
        except Exception:
            return ProfileGatewayResponse(result="invalid_response", reason_codes=["profile_invalid_json"])
        if not isinstance(body, dict):
            return ProfileGatewayResponse(result="invalid_response", reason_codes=["profile_schema_invalid"])
        return ProfileGatewayResponse(payload=body, result="success", reason_codes=["profile_request_success"])
