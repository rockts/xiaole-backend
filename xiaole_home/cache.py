from __future__ import annotations

import time
from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from typing import Any, Callable


class HomeCache:
    def __init__(self, fresh_ttl: float = 60, stale_ttl: float = 900, max_entries: int = 32, clock: Callable[[], float] = time.monotonic):
        self.fresh_ttl = fresh_ttl
        self.stale_ttl = stale_ttl
        self.max_entries = max_entries
        self.clock = clock
        self._entries: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = Lock()

    def put(self, user: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._entries[user] = (self.clock(), deepcopy(value))
            self._entries.move_to_end(user)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def _get(self, user: str, maximum_age: float):
        with self._lock:
            entry = self._entries.get(user)
            if not entry:
                return None
            created, value = entry
            age = self.clock() - created
            if age > maximum_age:
                if age > self.stale_ttl:
                    self._entries.pop(user, None)
                return None
            self._entries.move_to_end(user)
            return deepcopy(value), max(0, int(age))

    def get_fresh(self, user: str):
        result = self._get(user, self.fresh_ttl)
        return result[0] if result else None

    def get_stale(self, user: str):
        return self._get(user, self.stale_ttl)
