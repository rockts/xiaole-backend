import requests
from urllib.parse import urljoin

from ..errors import MemoryUnavailable
from ..schemas import MemoryResult


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
