# XiaoLe LLM Cost Governance Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. Do not
> commit, push, deploy, or modify production keys.

**Goal:** Route every XiaoLe production DeepSeek request through a fail-closed
gateway with model policy, context limits, bounded retries, usage accounting,
budgets, alerts, and multi-instance background idempotency.

**Architecture:** Add a focused gateway package and keep Legacy/Core2 as thin
adapters. Use a transactional local ledger interface for atomic reservations and
leases, and inject test doubles for all external side effects.

**Tech Stack:** Python 3, requests, sqlite3, FastAPI, APScheduler, unittest/pytest.

**Spec:** `docs/superpowers/specs/2026-08-21-llm-cost-governance-design.md`

## Global constraints

- No commit, push, deployment, provider-console operation, or production-key
  change.
- Flash is the default. Pro requires explicit foreground authorization.
- Governance and budget-store failures fail closed.
- Every production DeepSeek network call must pass through the gateway.

### Task 1: Gateway policy, context, retry, and ledger tests

**Files:**
- Create: `tests/test_llm_gateway.py`
- Create: `llm_gateway.py`

1. Write failing tests for model policy, category context caps, total input cap,
   three-attempt retry sequence, non-retryable termination, per-task caps,
   foreground/background/global budgets, complete audit fields, and fail-closed
   ledger errors.
2. Run `python -m pytest tests/test_llm_gateway.py -q` and verify failures are
   caused by the missing gateway.
3. Implement the smallest gateway, in-memory ledger, SQLite ledger, context
   limiter, model policy, retry classifier, usage parser, and cost estimator that
   satisfy the tests.
4. Re-run the focused tests until green.

### Task 2: Legacy adapter migration

**Files:**
- Create: `tests/test_legacy_llm_governance.py`
- Modify: `agent.py`
- Modify: `routers/documents.py`

1. Write failing tests proving `_call_deepseek`, `_call_deepseek_with_history`,
   and `_call_deepseek_stream` delegate to one gateway; ordinary chat cannot
   exceed three calls; caller names distinguish chat, tool selection, memory
   extraction, document summary, and task planning.
2. Run the focused tests and verify RED.
3. Replace direct requests and transport retry adapters with gateway calls while
   retaining current method return shapes and Qwen fallback behavior.
4. Pass stable request/task IDs from chat and background feature boundaries.
5. Run focused legacy tests until green.

### Task 3: Core2 adapter migration

**Files:**
- Modify: `tests/xiaole_core/test_models.py`
- Modify: `tests/xiaole_core/test_brain.py`
- Modify: `xiaole_core/models.py`
- Modify: `xiaole_core/dependencies.py`
- Modify: `xiaole_core/brain.py`

1. Write failing tests proving classification and answer calls share the same
   request budget and use `core2.intent`/`core2.answer` caller identities.
2. Verify RED.
3. Make `OpenAICompatibleProvider` delegate DeepSeek requests to `LLMGateway`;
   retain the existing Qwen provider for fallback.
4. Pass priority and explicit Pro permission from authenticated user requests;
   keep defaults Flash-only.
5. Run Core2 tests until green.

### Task 4: Scheduler leases, loop caps, and alerts

**Files:**
- Create: `tests/test_llm_background_governance.py`
- Modify: `scheduler.py`
- Modify: `modules/task_executor.py`
- Modify: `dependencies.py`

1. Write failing tests for duplicate scheduler start, duplicate scheduled lease,
   maximum three agent/tool rounds, maximum two background calls, and alert
   invocation on fuse events.
2. Verify RED.
3. Add process start locking, durable execution leases, explicit loop guards,
   background gateway context, and the existing-notification adapter.
4. Run focused background tests until green.

### Task 5: Configuration, static enforcement, and documentation

**Files:**
- Modify: `.env.example`
- Create: `tests/test_deepseek_gateway_boundary.py`
- Modify: `backend/DEEPSEEK_SETUP.md` if present in the backend repository.

1. Write a failing static boundary test that rejects DeepSeek URLs,
   authorization-header construction, and direct DeepSeek requests outside
   `llm_gateway.py`.
2. Verify RED against the current direct call paths.
3. Add non-secret default budget/context configuration and document caller names,
   thresholds, fuse behavior, and the external-key limitation.
4. Remove all production direct-call paths and make the boundary test green.

### Task 6: Verification and report evidence

1. Run all focused governance tests.
2. Run the complete backend test suite.
3. Run static searches for DeepSeek URLs, key access, authorization headers,
   direct `requests` calls, retry loops, scheduler starts, and model names.
4. Run a deterministic two-chat and three-chat regression simulation and record
   total calls and estimated cost.
5. Inspect `git diff --check`, `git status --short`, and the final diff; preserve
   unrelated user changes.
6. Report exact entry counts, migrated paths, theoretical maximum calls, context
   and budget defaults, fuse layers, remaining secret traces, and any unverified
   production behavior.
