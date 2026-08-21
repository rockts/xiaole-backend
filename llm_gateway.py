"""Single enforcement point for production DeepSeek requests.

The module intentionally owns the provider URL, authorization header, model
policy, context limits, retries, usage accounting, budgets, and execution
leases. Callers pass metadata; they never receive or log the API key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import threading
import time
from functools import wraps
from typing import Callable, Iterable

import requests


logger = logging.getLogger(__name__)
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


class LLMGovernanceError(RuntimeError):
    category = "governance"


class GovernanceUnavailable(LLMGovernanceError):
    category = "governance_unavailable"


class BudgetExceeded(LLMGovernanceError):
    category = "budget_exceeded"


class ModelPolicyError(LLMGovernanceError):
    category = "model_policy"


class ProviderError(RuntimeError):
    def __init__(self, message: str, category: str, retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.retryable = retryable


@dataclass(frozen=True)
class LLMRequest:
    caller: str
    source: str
    request_id: str
    task_id: str | int | None = None
    priority: str = "user"
    model: str = "deepseek-v4-flash"
    allow_pro: bool = False
    system: str = ""
    messages: list[dict] = field(default_factory=list)
    memory_context: str = ""
    tool_context: str = ""
    max_output_tokens: int = 1024
    temperature: float = 0.3
    stream: bool = False


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_hit_tokens: int
    cache_miss_tokens: int
    estimated_cost_cny: float
    attempt_count: int
    truncated_categories: tuple[str, ...] = ()
    raw_response: object | None = None


DEFAULT_CONTEXT_LIMITS = {
    "system": 8_000,
    "history": 12_000,
    "memory": 4_000,
    "tool": 4_000,
    "user": 4_000,
    "total": 24_000,
}

DEFAULT_BUDGET_LIMITS = {
    "user_hour": 30,
    "user_day": 100,
    "background_hour": 10,
    "background_day": 30,
    "global_hour": 40,
    "global_day": 120,
}

DEFAULT_TASK_LIMITS = {"user": 3, "background": 2}

# Conservative CNY rates per one million tokens, matching the highest rate
# tiers present in the supplied 2026-08 billing export.
MODEL_PRICES_CNY = {
    "deepseek-v4-flash": {"hit": 0.10, "miss": 3.0, "output": 9.0},
    "deepseek-v4-pro": {"hit": 0.30, "miss": 9.0, "output": 27.0},
}


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def configured_budget_limits() -> dict[str, int]:
    return {
        key: _env_int(f"LLM_BUDGET_{key.upper()}", value)
        for key, value in DEFAULT_BUDGET_LIMITS.items()
    }


def configured_context_limits() -> dict[str, int]:
    return {
        key: _env_int(f"LLM_CONTEXT_{key.upper()}_TOKENS", value)
        for key, value in DEFAULT_CONTEXT_LIMITS.items()
    }


def estimate_tokens(value: str) -> int:
    if not value:
        return 0
    # One Unicode code point per estimated token deliberately overestimates
    # English and is materially safer for Chinese than the common chars/4 rule.
    return len(value)


def _truncate_tail(value: str, token_limit: int) -> tuple[str, bool]:
    char_limit = token_limit
    if len(value) <= char_limit:
        return value, False
    return value[-char_limit:], True


def _truncate_head(value: str, token_limit: int) -> tuple[str, bool]:
    char_limit = token_limit
    if len(value) <= char_limit:
        return value, False
    return value[:char_limit], True


def estimate_cost_cny(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit_tokens: int,
    cache_miss_tokens: int,
) -> float:
    rates = MODEL_PRICES_CNY[model]
    known_input = cache_hit_tokens + cache_miss_tokens
    uncategorized = max(0, input_tokens - known_input)
    cost = (
        cache_hit_tokens * rates["hit"]
        + (cache_miss_tokens + uncategorized) * rates["miss"]
        + output_tokens * rates["output"]
    ) / 1_000_000
    return round(cost, 8)


class InMemoryLedger:
    """Deterministic ledger for tests and explicit development use."""

    def __init__(self):
        self.records: list[dict] = []
        self.leases: dict[str, float] = {}
        self._lock = threading.Lock()

    def reserve(self, metadata, now, budget_limits, task_limits):
        with self._lock:
            priority = metadata["priority"]
            request_key = str(metadata.get("task_id") or metadata["request_id"])
            matching_task = [
                row for row in self.records
                if row["request_key"] == request_key
                and row["priority"] == priority
            ]
            task_attempts = sum(
                int(row.get("attempt_count") or 1) for row in matching_task
            )
            if task_attempts >= task_limits[priority]:
                raise BudgetExceeded(f"{priority} task call limit reached")

            hour = now.strftime("%Y-%m-%dT%H")
            day = now.strftime("%Y-%m-%d")
            hour_rows = [row for row in self.records if row["hour"] == hour]
            day_rows = [row for row in self.records if row["day"] == day]
            pool_hour = [row for row in hour_rows if row["priority"] == priority]
            pool_day = [row for row in day_rows if row["priority"] == priority]
            consumed = lambda rows: sum(
                int(row.get("attempt_count") or 1) for row in rows
            )
            checks = (
                (consumed(pool_hour), budget_limits[f"{priority}_hour"], "pool_hour"),
                (consumed(pool_day), budget_limits[f"{priority}_day"], "pool_day"),
                (consumed(hour_rows), budget_limits["global_hour"], "global_hour"),
                (consumed(day_rows), budget_limits["global_day"], "global_day"),
            )
            for current, limit, label in checks:
                if current >= limit:
                    raise BudgetExceeded(f"{label} budget reached")

            record = {
                **metadata,
                "request_key": request_key,
                "timestamp": now.isoformat(),
                "hour": hour,
                "day": day,
                "result": "reserved",
                "error_category": None,
                "attempt_count": 1,
            }
            self.records.append(record)
            return len(self.records) - 1

    def finalize(self, reservation_id, updates):
        with self._lock:
            self.records[reservation_id].update(updates)

    def reserve_retry(self, reservation_id, budget_limits, task_limits):
        with self._lock:
            row = self.records[reservation_id]
            priority = row["priority"]
            request_key = row["request_key"]
            scopes = (
                ([r for r in self.records if r["request_key"] == request_key and r["priority"] == priority], task_limits[priority], "task"),
                ([r for r in self.records if r["hour"] == row["hour"] and r["priority"] == priority], budget_limits[f"{priority}_hour"], "pool_hour"),
                ([r for r in self.records if r["day"] == row["day"] and r["priority"] == priority], budget_limits[f"{priority}_day"], "pool_day"),
                ([r for r in self.records if r["hour"] == row["hour"]], budget_limits["global_hour"], "global_hour"),
                ([r for r in self.records if r["day"] == row["day"]], budget_limits["global_day"], "global_day"),
            )
            for rows, limit, label in scopes:
                if sum(int(item.get("attempt_count") or 1) for item in rows) >= limit:
                    raise BudgetExceeded(f"{label} budget reached before retry")
            row["attempt_count"] = int(row.get("attempt_count") or 1) + 1

    def acquire_lease(self, key: str, now: datetime, ttl_seconds: int) -> bool:
        with self._lock:
            timestamp = now.timestamp()
            if self.leases.get(key, 0) > timestamp:
                return False
            self.leases[key] = timestamp + ttl_seconds
            return True

    def summarize(self, period: str, bucket: str) -> dict:
        if period not in {"hour", "day"}:
            raise ValueError("period must be hour or day")
        rows = [row for row in self.records if row[period] == bucket]
        return _summarize_rows(rows)


class SQLiteLedger:
    """Process-safe usage ledger and durable execution lease store."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL, hour TEXT NOT NULL, day TEXT NOT NULL,
                    caller TEXT NOT NULL, source TEXT NOT NULL,
                    priority TEXT NOT NULL, request_id TEXT NOT NULL,
                    task_id TEXT, request_key TEXT NOT NULL, model TEXT NOT NULL,
                    estimated_input_tokens INTEGER NOT NULL DEFAULT 0,
                    input_tokens INTEGER, output_tokens INTEGER,
                    cache_hit_tokens INTEGER, cache_miss_tokens INTEGER,
                    estimated_cost_cny REAL, duration_ms INTEGER,
                    attempt_count INTEGER, result TEXT NOT NULL,
                    error_category TEXT, truncated_categories TEXT
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS llm_execution_leases (
                    lease_key TEXT PRIMARY KEY, expires_at REAL NOT NULL
                )
            """)

    def reserve(self, metadata, now, budget_limits, task_limits):
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                priority = metadata["priority"]
                request_key = str(metadata.get("task_id") or metadata["request_id"])
                hour, day = now.strftime("%Y-%m-%dT%H"), now.strftime("%Y-%m-%d")
                task_count = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE request_key=? AND priority=?",
                    (request_key, priority),
                ).fetchone()[0]
                if task_count >= task_limits[priority]:
                    raise BudgetExceeded(f"{priority} task call limit reached")
                pool_hour = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE hour=? AND priority=?",
                    (hour, priority),
                ).fetchone()[0]
                pool_day = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE day=? AND priority=?",
                    (day, priority),
                ).fetchone()[0]
                global_hour = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE hour=?", (hour,)
                ).fetchone()[0]
                global_day = connection.execute(
                    "SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE day=?", (day,)
                ).fetchone()[0]
                checks = (
                    (pool_hour, budget_limits[f"{priority}_hour"], "pool_hour"),
                    (pool_day, budget_limits[f"{priority}_day"], "pool_day"),
                    (global_hour, budget_limits["global_hour"], "global_hour"),
                    (global_day, budget_limits["global_day"], "global_day"),
                )
                for current, limit, label in checks:
                    if current >= limit:
                        raise BudgetExceeded(f"{label} budget reached")
                cursor = connection.execute("""
                    INSERT INTO llm_usage (
                        timestamp,hour,day,caller,source,priority,request_id,
                        task_id,request_key,model,estimated_input_tokens,result
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    now.isoformat(), hour, day, metadata["caller"], metadata["source"],
                    priority, metadata["request_id"],
                    None if metadata.get("task_id") is None else str(metadata["task_id"]),
                    request_key, metadata["model"],
                    metadata.get("estimated_input_tokens", 0), "reserved",
                ))
                connection.execute(
                    "UPDATE llm_usage SET attempt_count=1 WHERE id=?",
                    (cursor.lastrowid,),
                )
                connection.commit()
                return cursor.lastrowid
        except BudgetExceeded:
            raise
        except (sqlite3.Error, OSError) as exc:
            raise GovernanceUnavailable("usage ledger unavailable") from exc

    def finalize(self, reservation_id, updates):
        allowed = {
            "input_tokens", "output_tokens", "cache_hit_tokens",
            "cache_miss_tokens", "estimated_cost_cny", "duration_ms",
            "attempt_count", "result", "error_category",
            "truncated_categories",
        }
        values = {key: value for key, value in updates.items() if key in allowed}
        if isinstance(values.get("truncated_categories"), (list, tuple)):
            values["truncated_categories"] = json.dumps(values["truncated_categories"])
        assignments = ",".join(f"{key}=?" for key in values)
        try:
            with self._connect() as connection:
                connection.execute(
                    f"UPDATE llm_usage SET {assignments} WHERE id=?",
                    (*values.values(), reservation_id),
                )
        except (sqlite3.Error, OSError) as exc:
            raise GovernanceUnavailable("usage ledger finalize failed") from exc

    def reserve_retry(self, reservation_id, budget_limits, task_limits):
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM llm_usage WHERE id=?", (reservation_id,)
                ).fetchone()
                if row is None:
                    raise GovernanceUnavailable("usage reservation missing")
                priority = row["priority"]
                queries = (
                    ("request_key=? AND priority=?", (row["request_key"], priority), task_limits[priority], "task"),
                    ("hour=? AND priority=?", (row["hour"], priority), budget_limits[f"{priority}_hour"], "pool_hour"),
                    ("day=? AND priority=?", (row["day"], priority), budget_limits[f"{priority}_day"], "pool_day"),
                    ("hour=?", (row["hour"],), budget_limits["global_hour"], "global_hour"),
                    ("day=?", (row["day"],), budget_limits["global_day"], "global_day"),
                )
                for where, params, limit, label in queries:
                    used = connection.execute(
                        f"SELECT COALESCE(SUM(COALESCE(attempt_count,1)),0) FROM llm_usage WHERE {where}",
                        params,
                    ).fetchone()[0]
                    if used >= limit:
                        raise BudgetExceeded(
                            f"{label} budget reached before retry"
                        )
                connection.execute(
                    "UPDATE llm_usage SET attempt_count=COALESCE(attempt_count,1)+1 WHERE id=?",
                    (reservation_id,),
                )
                connection.commit()
        except (BudgetExceeded, GovernanceUnavailable):
            raise
        except (sqlite3.Error, OSError) as exc:
            raise GovernanceUnavailable("retry reservation unavailable") from exc

    def acquire_lease(self, key: str, now: datetime, ttl_seconds: int) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                expires = connection.execute(
                    "SELECT expires_at FROM llm_execution_leases WHERE lease_key=?",
                    (key,),
                ).fetchone()
                timestamp = now.timestamp()
                if expires and expires[0] > timestamp:
                    connection.rollback()
                    return False
                connection.execute(
                    "INSERT OR REPLACE INTO llm_execution_leases VALUES (?,?)",
                    (key, timestamp + ttl_seconds),
                )
                connection.commit()
                return True
        except (sqlite3.Error, OSError) as exc:
            raise GovernanceUnavailable("execution lease unavailable") from exc

    def summarize(self, period: str, bucket: str) -> dict:
        if period not in {"hour", "day"}:
            raise ValueError("period must be hour or day")
        try:
            with self._connect() as connection:
                rows = [dict(row) for row in connection.execute(
                    f"SELECT * FROM llm_usage WHERE {period}=?", (bucket,)
                ).fetchall()]
            return _summarize_rows(rows)
        except (sqlite3.Error, OSError) as exc:
            raise GovernanceUnavailable("usage summary unavailable") from exc


def _summarize_rows(rows: Iterable[dict]) -> dict:
    return {
        "calls": sum(int(row.get("attempt_count") or 1) for row in rows),
        "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
        "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
        "cache_hit_tokens": sum(int(row.get("cache_hit_tokens") or 0) for row in rows),
        "cache_miss_tokens": sum(int(row.get("cache_miss_tokens") or 0) for row in rows),
        "estimated_cost_cny": round(sum(
            float(row.get("estimated_cost_cny") or 0) for row in rows
        ), 8),
        "successes": sum(row.get("result") == "success" for row in rows),
        "failures": sum(row.get("result") == "failure" for row in rows),
    }


class LLMGateway:
    def __init__(
        self,
        api_key: str,
        transport=None,
        ledger=None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] | None = None,
        notifier: Callable[[dict], None] | None = None,
        context_limits: dict[str, int] | None = None,
        budget_limits: dict[str, int] | None = None,
        task_limits: dict[str, int] | None = None,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.transport = transport or requests.Session()
        self.ledger = ledger or SQLiteLedger(
            os.getenv("LLM_USAGE_DB", str(Path(__file__).parent / "logs" / "llm_usage.sqlite3"))
        )
        self.sleeper = sleeper
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.notifier = notifier
        self.context_limits = context_limits or configured_context_limits()
        self.budget_limits = budget_limits or configured_budget_limits()
        self.task_limits = task_limits or DEFAULT_TASK_LIMITS.copy()
        self.max_retries = max(0, max_retries)

    def complete(self, request: LLMRequest) -> LLMResult:
        model = self._effective_model(request)
        messages, truncated = self._bounded_messages(request)
        estimated_input = sum(estimate_tokens(item["content"]) for item in messages)
        metadata = {
            "caller": request.caller,
            "source": request.source,
            "priority": request.priority,
            "request_id": request.request_id,
            "task_id": request.task_id,
            "model": model,
            "estimated_input_tokens": estimated_input,
        }
        now = self.clock()
        try:
            reservation = self.ledger.reserve(
                metadata, now, self.budget_limits, self.task_limits
            )
        except BudgetExceeded as exc:
            self._notify_fuse(metadata, str(exc))
            raise
        except Exception as exc:
            if isinstance(exc, GovernanceUnavailable):
                raise
            raise GovernanceUnavailable("usage ledger reservation failed") from exc

        started = time.monotonic()
        attempts = 0
        try:
            while True:
                attempts += 1
                try:
                    response = self.transport.post(
                        DEEPSEEK_URL,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "X-Request-ID": request.request_id,
                            "X-XiaoLe-Caller": request.caller,
                            "X-XiaoLe-Source": request.source,
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": request.temperature,
                            "max_tokens": request.max_output_tokens,
                            "stream": False,
                            "thinking": {"type": "disabled"},
                        },
                        timeout=60,
                    )
                    self._raise_for_status(response)
                    payload = response.json()
                    text = payload["choices"][0]["message"]["content"]
                    if not isinstance(text, str) or not text.strip():
                        raise ProviderError("empty model response", "invalid_response", True)
                    usage = payload.get("usage") or {}
                    input_tokens = int(usage.get("prompt_tokens") or estimated_input)
                    output_tokens = int(usage.get("completion_tokens") or estimate_tokens(text))
                    cache_hit = int(usage.get("prompt_cache_hit_tokens") or usage.get("input_cache_hit_tokens") or 0)
                    cache_miss = int(usage.get("prompt_cache_miss_tokens") or usage.get("input_cache_miss_tokens") or 0)
                    cost = estimate_cost_cny(
                        model, input_tokens, output_tokens, cache_hit, cache_miss
                    )
                    duration_ms = int((time.monotonic() - started) * 1000)
                    updates = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_hit_tokens": cache_hit,
                        "cache_miss_tokens": cache_miss,
                        "estimated_cost_cny": cost,
                        "duration_ms": duration_ms,
                        "attempt_count": attempts,
                        "result": "success",
                        "error_category": None,
                        "truncated_categories": tuple(truncated),
                    }
                    self.ledger.finalize(reservation, updates)
                    logger.info(
                        "llm_call caller=%s source=%s request_id=%s task_id=%s "
                        "model=%s input_tokens=%s output_tokens=%s cost_cny=%s "
                        "duration_ms=%s result=success attempts=%s",
                        request.caller, request.source, request.request_id,
                        request.task_id, model, input_tokens, output_tokens, cost,
                        duration_ms, attempts,
                    )
                    return LLMResult(
                        text=text.strip(), model=model,
                        input_tokens=input_tokens, output_tokens=output_tokens,
                        cache_hit_tokens=cache_hit, cache_miss_tokens=cache_miss,
                        estimated_cost_cny=cost, attempt_count=attempts,
                        truncated_categories=tuple(truncated), raw_response=response,
                    )
                except (requests.Timeout, requests.ConnectionError) as exc:
                    error = ProviderError("model transport failed", "transport", True)
                    error.__cause__ = exc
                    if attempts > self.max_retries:
                        raise error
                    self._reserve_retry(reservation, metadata)
                    self.sleeper(float(2 ** (attempts - 1)))
                except ProviderError as exc:
                    if not exc.retryable or attempts > self.max_retries:
                        raise
                    self._reserve_retry(reservation, metadata)
                    self.sleeper(float(2 ** (attempts - 1)))
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            category = getattr(exc, "category", "unexpected")
            try:
                self.ledger.finalize(reservation, {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_hit_tokens": 0,
                    "cache_miss_tokens": 0,
                    "estimated_cost_cny": 0.0,
                    "duration_ms": duration_ms,
                    "attempt_count": attempts,
                    "result": "failure",
                    "error_category": category,
                    "truncated_categories": tuple(truncated),
                })
            except Exception as ledger_exc:
                raise GovernanceUnavailable("usage ledger finalize failed") from ledger_exc
            raise

    def acquire_execution_lease(
        self, key: str, ttl_seconds: int = 3600
    ) -> bool:
        try:
            return self.ledger.acquire_lease(key, self.clock(), ttl_seconds)
        except Exception as exc:
            if isinstance(exc, GovernanceUnavailable):
                raise
            raise GovernanceUnavailable("execution lease failed") from exc

    def _reserve_retry(self, reservation, metadata):
        try:
            self.ledger.reserve_retry(
                reservation, self.budget_limits, self.task_limits
            )
        except BudgetExceeded as exc:
            self._notify_fuse(metadata, str(exc))
            raise

    @staticmethod
    def _raise_for_status(response):
        status = response.status_code
        if status < 400:
            return
        if status in (401, 403):
            raise ProviderError("model authentication failed", "authentication", False)
        if status == 402:
            raise ProviderError("model billing unavailable", "billing_quota", False)
        if status == 429:
            raise ProviderError("model rate limited", "rate_limit", True)
        if status >= 500:
            raise ProviderError("model service unavailable", "service_unavailable", True)
        raise ProviderError("model request rejected", "request_rejected", False)

    @staticmethod
    def _effective_model(request: LLMRequest) -> str:
        aliases = {
            "deepseek-chat": "deepseek-v4-flash",
            "deepseek-reasoner": "deepseek-v4-flash",
            "deepseek-v4-flash": "deepseek-v4-flash",
            "deepseek-v4-pro": "deepseek-v4-pro",
        }
        model = aliases.get(request.model)
        if not model:
            raise ModelPolicyError("unsupported DeepSeek model")
        if request.priority not in ("user", "background"):
            raise ModelPolicyError("invalid request priority")
        if model == "deepseek-v4-pro" and not (
            request.priority == "user" and request.allow_pro
        ):
            raise ModelPolicyError("Pro requires explicit foreground permission")
        return model

    def _bounded_messages(self, request: LLMRequest):
        limits = self.context_limits
        truncated: list[str] = []
        system, changed = _truncate_head(request.system or "", limits["system"])
        if changed:
            truncated.append("system")
        memory, changed = _truncate_tail(request.memory_context or "", limits["memory"])
        if changed:
            truncated.append("memory")
        tool, changed = _truncate_tail(request.tool_context or "", limits["tool"])
        if changed:
            truncated.append("tool")

        raw_messages = [
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in request.messages
        ]
        last_user_index = next(
            (index for index in range(len(raw_messages) - 1, -1, -1)
             if raw_messages[index]["role"] == "user"),
            None,
        )
        current_user = ""
        history = raw_messages
        if last_user_index is not None:
            current_user = raw_messages[last_user_index]["content"]
            history = raw_messages[:last_user_index] + raw_messages[last_user_index + 1:]
        current_user, changed = _truncate_head(current_user, limits["user"])
        if changed:
            truncated.append("user")

        history_budget = limits["history"]
        kept_history = []
        used = 0
        for item in reversed(history):
            content = item["content"]
            if used + len(content) > history_budget:
                remaining = max(0, history_budget - used)
                if remaining:
                    kept_history.append({**item, "content": content[-remaining:]})
                truncated.append("history")
                break
            kept_history.append(item)
            used += len(content)
        kept_history.reverse()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if memory:
            messages.append({"role": "system", "content": "Memory context:\n" + memory})
        if tool:
            messages.append({"role": "system", "content": "Tool result:\n" + tool})
        messages.extend(kept_history)
        if current_user:
            messages.append({"role": "user", "content": current_user})

        total_chars = limits["total"]
        current_chars = sum(len(item["content"]) for item in messages)
        if current_chars > total_chars:
            truncated.append("total")
            overflow = current_chars - total_chars
            # Preserve the newest user input and discard oldest context first.
            for item in messages:
                if overflow <= 0:
                    break
                removable = min(len(item["content"]), overflow)
                item["content"] = item["content"][removable:]
                overflow -= removable
            messages = [item for item in messages if item["content"]]
        return messages, list(dict.fromkeys(truncated))

    def _notify_fuse(self, metadata: dict, reason: str):
        event = {
            "event": "llm_budget_fuse",
            "caller": metadata["caller"],
            "source": metadata["source"],
            "priority": metadata["priority"],
            "request_id": metadata["request_id"],
            "task_id": metadata.get("task_id"),
            "reason": reason,
        }
        logger.error("llm_budget_fuse %s", json.dumps(event, ensure_ascii=False))
        if self.notifier:
            try:
                self.notifier(event)
            except Exception:
                logger.exception("llm_budget_alert_failed")


_gateway = None
_gateway_lock = threading.Lock()
_request_context: ContextVar[str | None] = ContextVar(
    "xiaole_llm_request_id", default=None
)


def current_llm_request_id() -> str | None:
    return _request_context.get()


def governed_entrypoint(function):
    """Bind all nested foreground LLM calls to one request budget."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        import uuid
        token = _request_context.set(str(uuid.uuid4()))
        try:
            return function(*args, **kwargs)
        finally:
            _request_context.reset(token)
    return wrapper


def governed_stream_entrypoint(function):
    """Keep the request budget context alive while a generator is consumed."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        import uuid
        token = _request_context.set(str(uuid.uuid4()))
        try:
            yield from function(*args, **kwargs)
        finally:
            _request_context.reset(token)
    return wrapper


def get_llm_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        with _gateway_lock:
            if _gateway is None:
                key = os.getenv("DEEPSEEK_API_KEY", "")
                _gateway = LLMGateway(
                    api_key=key,
                    notifier=_default_budget_notifier,
                )
    return _gateway


def _default_budget_notifier(event: dict) -> None:
    """Reuse XiaoKe Action notification when it is configured."""
    base_url = os.getenv("XIAOKE_ACTION_URL", "").rstrip("/")
    token = os.getenv("XIAOKE_API_TOKEN", "")
    if not base_url or not token:
        logger.warning("llm_budget_alert_not_configured")
        return
    request_id = f"llm-budget:{event['request_id']}"
    payload = {
        "idempotency_key": request_id,
        "source_system": "xiaole",
        "task_type": "notification.send",
        "priority": "high",
        "target": {"channel": "mobile"},
        "parameters": {
            "title": "小乐 LLM 费用保险丝触发",
            "content": (
                f"来源 {event['caller']}，预算池 {event['priority']}，"
                f"原因 {event['reason']}。已停止本次模型调用。"
            ),
        },
        "risk_level": "low",
        "requires_confirmation": False,
        "confirmation_token": "",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {"request_id": event["request_id"], "event": event["event"]},
    }
    response = requests.post(
        f"{base_url}/v1/tasks",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Request-ID": request_id},
        timeout=5,
    )
    if response.status_code not in (200, 202):
        raise RuntimeError("budget alert was not accepted")
