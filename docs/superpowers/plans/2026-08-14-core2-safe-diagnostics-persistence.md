# Core2 Safe Diagnostics Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist one whitelist-only `core2_safe_diagnostics` JSON event for each completed Core2 request.

**Architecture:** A focused persistence module owns the strict event schema and explicit JSON serialization. Brain emits once after constructing its final response; the router emits fixed safe fallback data only when Brain fails before returning.

**Tech Stack:** Python 3.11, Pydantic, standard logging, unittest

## Global Constraints

Do not change matcher, intent decisions, current-school logic, Profile projection/data, gateways, model calls, answers, secrets, or log retention. Never serialize request, response, Diagnostics, prompts, messages, Profile values, memory text, URLs, credentials, or exception text.

---

### Task 1: Whitelist event serializer

**Files:**
- Create: `xiaole_core/safe_diagnostics.py`
- Test: `tests/xiaole_core/test_safe_diagnostics.py`

**Interfaces:**
- Produces: `Core2SafeDiagnosticsEvent` and `emit_core2_safe_diagnostics(event)`.

- [ ] Write failing tests proving strict whitelist validation and compact single-line JSON.
- [ ] Run the focused test and confirm missing implementation failure.
- [ ] Implement explicit field-by-field serialization and existing logger emission.
- [ ] Run the focused test and confirm pass.

### Task 2: Single final Brain event and router fallback

**Files:**
- Modify: `xiaole_core/brain.py`
- Modify: `routers/chat_v2.py`
- Test: `tests/xiaole_core/test_safe_diagnostics.py`
- Test: `tests/xiaole_core/test_chat_v2_api.py`

**Interfaces:**
- Consumes: the whitelist event emitter.
- Produces: one final event per successful Brain request, or one fixed router fallback event when Brain raises.

- [ ] Add failing tests for deterministic hit, 401, timeout, fallback model call, uniqueness, scope semantics, router fallback, and sensitive marker absence.
- [ ] Run focused tests and confirm expected failures.
- [ ] Add the unified successful response emission and failure-only router emission.
- [ ] Run focused tests and confirm pass.

### Task 3: Verification and release

**Files:**
- Verify changed files only.

- [ ] Run Core2, Real Use Recovery, Home, Legacy/Scheduler, compileall, and diff check.
- [ ] Run a local request, query the captured log by request ID, and verify marker absence.
- [ ] Commit and push `main`.
- [ ] Wait for CI Docker push and Watchtower schema/code adoption without manual container operations.
- [ ] Send one production request, query `xiaole_ai.log` by request ID and event, classify A-H, then stop.
