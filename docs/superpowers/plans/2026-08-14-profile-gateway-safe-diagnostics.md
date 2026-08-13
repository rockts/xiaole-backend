# Profile Gateway Safe Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add value-free, finite diagnostics for the Core2 current-employment Profile Gateway path.

**Architecture:** The Profile Gateway classifies transport and parsing outcomes into an internal structured result. BrainCore aggregates that result with the unchanged current-school eligibility checks into the public Diagnostics schema.

**Tech Stack:** Python 3.11, requests, Pydantic, unittest

## Global Constraints

Do not modify the matcher, current-school eligibility logic, answer copy, Profile data, Lezhi, XiaoKe, Home, Recommendation, Memory Governance, or secrets. Never emit values, URLs, raw errors/responses, authorization data, prompts, or conversation history.

---

### Task 1: Gateway classification and schema

**Files:**
- Modify: `xiaole_core/schemas.py`
- Modify: `xiaole_core/gateways/memory.py`
- Test: `tests/xiaole_core/test_gateways.py`

**Interfaces:**
- Produces: `ProfileGatewayResponse(payload, result, reason_codes)` with finite literals.

- [ ] Add failing tests for success, 401, timeout, and malformed/schema-invalid responses.
- [ ] Run the focused gateway tests and confirm expected failures.
- [ ] Implement the minimal safe result mapping.
- [ ] Run the focused gateway tests and confirm they pass.

### Task 2: Brain aggregation and leakage guard

**Files:**
- Modify: `xiaole_core/brain.py`
- Modify: `xiaole_core/schemas.py`
- Test: `tests/xiaole_core/test_real_use_recovery.py`
- Test: `tests/xiaole_core/test_schemas.py`

**Interfaces:**
- Consumes: `ProfileGatewayResponse` or a backward-compatible dictionary.
- Produces: the five public Profile diagnostics fields.

- [ ] Add failing table-driven tests for ready, unauthorized, timeout, fields missing, fact missing, unconfirmed, wrong subject, empty value, and leakage.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Implement minimal aggregation without changing deterministic conditions or answer copy.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Full verification and authorized release

**Files:**
- Verify all changed files only.

- [ ] Run Core2, Real Use Recovery, Home, Legacy/Scheduler, compileall, and `git diff --check`.
- [ ] Run one local current-employment request and inspect only serialized safe diagnostics.
- [ ] Review the diff for scope and secret safety.
- [ ] Commit and push `main`.
- [ ] Wait for GitHub Actions Docker build/push.
- [ ] Wait for Watchtower natural adoption without manual pull or restart.
- [ ] Ask production once and record only the five safe fields; classify A-H and stop.
