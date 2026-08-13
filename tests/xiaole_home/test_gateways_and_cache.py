import unittest

from xiaole_home.cache import HomeCache
from xiaole_home.gateways.action_readiness import ActionReadinessGateway
from xiaole_home.gateways.lezhi import LezhiHomeGateway


class Response:
    def __init__(self, body=None, status_code=200):
        self._body = body or {}
        self.status_code = status_code

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http failure")


class Transport:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    def post(self, *args, **kwargs):
        raise AssertionError("readiness and Home reads must never POST")


class GatewayAndCacheTests(unittest.TestCase):
    def test_lezhi_uses_backend_token_and_returns_only_json(self):
        transport = Transport([Response({"schema_version": 1, "today": {}})])
        gateway = LezhiHomeGateway("http://127.0.0.1:8765", "server-secret", transport=transport)
        value = gateway.intelligence()
        method, url, options = transport.calls[0]
        self.assertEqual("GET", method)
        self.assertEqual("http://127.0.0.1:8765/api/v1/status/intelligence", url)
        self.assertEqual("server-secret", options["headers"]["X-KOS-Token"])
        self.assertEqual(1, value["schema_version"])
        self.assertNotIn("server-secret", str(value))

    def test_action_readiness_is_get_only_and_maps_health(self):
        transport = Transport([Response({"status": "ok"})])
        value = ActionReadinessGateway("https://action.example", "action-secret", transport=transport).check()
        self.assertEqual("healthy", value.status)
        self.assertEqual("GET", transport.calls[0][0])
        self.assertEqual("https://action.example/health", transport.calls[0][1])

    def test_action_without_url_is_unavailable_without_transport_call(self):
        transport = Transport()
        value = ActionReadinessGateway("", "", transport=transport).check()
        self.assertEqual("unavailable", value.status)
        self.assertEqual([], transport.calls)

    def test_cache_is_user_isolated_and_has_fresh_and_stale_windows(self):
        now = [1000.0]
        cache = HomeCache(max_entries=2, clock=lambda: now[0])
        cache.put("alice", {"owner": "alice"})
        self.assertEqual("alice", cache.get_fresh("alice")["owner"])
        self.assertIsNone(cache.get_fresh("bob"))
        now[0] += 61
        self.assertIsNone(cache.get_fresh("alice"))
        self.assertEqual("alice", cache.get_stale("alice")[0]["owner"])
        now[0] += 840
        self.assertIsNone(cache.get_stale("alice"))


if __name__ == "__main__":
    unittest.main()
