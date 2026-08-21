# XiaoLe 2.0 Self Profile Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route current-user identity and employment-history questions through a deterministic, privacy-minimized Profile-only policy with code-owned provenance.

**Architecture:** Add finite personal-profile scopes to the existing deterministic intent router, then isolate field admission and answer rendering in a focused policy module. `BrainCore` calls the existing Profile gateway exactly once for these scopes, never calls Memory or the model, and emits additive value-free diagnostics describing source categories and exclusions.

**Tech Stack:** Project virtualenv Python, Pydantic, SQLAlchemy, unittest, FastAPI TestClient

**Spec:** `docs/superpowers/specs/2026-08-21-self-profile-grounding-design.md`

## Global Constraints

- Do not commit, push, deploy, or publish.
- Do not modify User Profile data or Lezhi Memory Governance.
- Do not delete or rewrite Legacy Memory.
- Do not modify XiaoKe, Home, Bark, reminders, notifications, or UI.
- Do not add dependencies or database migrations.
- Do not serialize prompts, messages, Profile values, Memory text, or family data in diagnostics.
- `self_profile` and `employment_history` must not call the model or free-form Memory.
- Confirmed current Profile overrides historical data for current-user answers.

---

### Task 1: Deterministic Personal Scope Routing

**Files:**
- Modify: `xiaole_core/intent.py`
- Test: `tests/xiaole_core/test_intent.py`

**Interfaces:**
- Produces: `is_self_profile_query(message: str) -> bool`
- Produces: `is_employment_history_query(message: str) -> bool`
- Produces reason codes `self_profile` and `employment_history` under `Intent.KNOWLEDGE`.

- [ ] **Step 1: Write failing table-driven routing tests**

Add literal expectations for the seven self-profile phrasings and the explicit
history question. Also assert current-employment routing remains
`current_employment` and a generic conversation stays outside both new scopes.

- [ ] **Step 2: Run RED**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_intent -v`

Expected: FAIL because the required phrases return `safe_default` or
`model_fallback`, and the history question has no deterministic reason code.

- [ ] **Step 3: Implement minimal normalized phrase-family matchers**

Normalize whitespace and punctuation, route explicit employment history before
self-profile, and return `IntentDecision(Intent.KNOWLEDGE, <finite reason>)`.
Do not create an exact answer lookup or call the classifier for these scopes.

- [ ] **Step 4: Run GREEN**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_intent -v`

Expected: all intent tests PASS.

### Task 2: Profile Projection and Deterministic Rendering Policy

**Files:**
- Create: `xiaole_core/self_profile.py`
- Create: `tests/xiaole_core/test_self_profile.py`

**Interfaces:**
- Produces: `SelfProfileResult(answer: str, admitted_sources: tuple[str, ...], provenance_categories: tuple[str, ...])`
- Produces: `render_self_profile(profile: dict) -> SelfProfileResult`
- Produces: `render_employment_history(profile: dict) -> SelfProfileResult`
- Produces: `render_profile_unavailable(scope: str) -> SelfProfileResult`

- [ ] **Step 1: Write failing self-profile policy tests**

Use a complete literal Profile fixture containing confirmed current fields,
historical school, `needs_confirmation` teaching subjects, and prohibited
privacy-shaped fields. Assert the rendered current answer includes the confirmed
name/current school/high-level roles or interests, mentions teaching subjects as
unconfirmed without their value, and excludes historical school, family, precise
address, food, child, appearance, schedule, and candidate subject markers.

- [ ] **Step 2: Run RED**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_self_profile -v`

Expected: collection FAIL because `xiaole_core.self_profile` does not exist.

- [ ] **Step 3: Implement the minimal allowlist projector and renderer**

Admit only `subject=current_user`. For self-profile, render allowed confirmed
current fields and a narrow `needs_confirmation` sentence for
`current_teaching_subjects` and current grade coverage. For history, render only
historical school fields. Return finite source/provenance categories owned by
code. Never interpolate a `needs_confirmation` value.

- [ ] **Step 4: Add failing provenance, history, and fail-closed tests**

Assert confirmed Profile wording is code-owned, the forbidden blanket claim is
absent, history is explicitly labelled past, empty/malformed Profile returns a
safe unavailable answer, and no historical value appears in self-profile.

- [ ] **Step 5: Run RED and implement the remaining minimal branches**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_self_profile -v`

Expected before implementation: FAIL on the new branches. Implement only the
finite failure and history cases, then rerun until all policy tests PASS.

### Task 3: Brain Integration and Source Isolation

**Files:**
- Modify: `xiaole_core/brain.py`
- Modify: `xiaole_core/schemas.py`
- Test: `tests/xiaole_core/test_real_use_recovery.py`

**Interfaces:**
- Consumes intent reason codes `self_profile` and `employment_history`.
- Consumes deterministic render functions from `xiaole_core.self_profile`.
- Adds optional finite Diagnostics fields: `profile_scope`,
  `admitted_source_categories`, `excluded_source_categories`, `renderer`, and
  `provenance_categories`.

- [ ] **Step 1: Write failing Brain tests for the seven current questions**

Use a recording gateway whose Profile result contains current, historical,
candidate, Legacy-shaped, and private markers; whose Memory methods fail the
test if called; and a model fake that fails if called. Seed context with shared
conversation markers. Assert each answer uses the confirmed current school and
contains none of the forbidden markers.

- [ ] **Step 2: Run RED**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_real_use_recovery -v`

Expected: FAIL because the new routes still enter generic read/model behavior.

- [ ] **Step 3: Add the dedicated Brain branch**

Pass the `IntentDecision.reason_code` into a focused private method that calls
`read_gateway.profile(request_id)` once, handles `ProfileGatewayResponse`, invokes
the deterministic renderer, sets `model=""`, returns no source snippets, and
never reads history as evidence. Preserve history only for intent classification
and conversation persistence.

- [ ] **Step 4: Write and run failing Profile-unavailable isolation test**

Assert unavailable/unauthorized/invalid Profile responses produce an explicit
safe degradation with Profile diagnostics, zero Memory calls, and zero model
calls. Run the focused test and confirm it fails before adding the failure branch.

- [ ] **Step 5: Implement failure mapping and run GREEN**

Map existing Profile result/reason codes without exception text or value leakage.
Run: `./venv/bin/python -m unittest tests.xiaole_core.test_real_use_recovery -v`

Expected: all focused tests PASS.

### Task 4: Value-Free Safe Diagnostics

**Files:**
- Modify: `xiaole_core/safe_diagnostics.py`
- Modify: `xiaole_core/brain.py`
- Modify: `routers/chat_v2.py`
- Test: `tests/xiaole_core/test_safe_diagnostics.py`
- Test: `tests/xiaole_core/test_chat_v2_api.py`

**Interfaces:**
- Extends `Core2SafeDiagnosticsEvent` with optional finite enum/list fields that
  match the Diagnostics fields introduced in Task 3.

- [ ] **Step 1: Write failing whitelist and sensitive-marker tests**

Assert self-profile events report deterministic renderer, Profile admission,
Legacy/conversation/model exclusions, and code-owned provenance categories.
Assert serialized JSON contains no question, answer, field name, Profile value,
history content, URL, token, or exception marker.

- [ ] **Step 2: Run RED**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_safe_diagnostics tests.xiaole_core.test_chat_v2_api -v`

Expected: FAIL because the additive fields are absent.

- [ ] **Step 3: Implement strict additive serialization**

Add defaults for backward compatibility, copy each field explicitly into the
event payload, and pass only finite categories from Brain. Keep router failure
events on safe empty defaults.

- [ ] **Step 4: Run GREEN**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_safe_diagnostics tests.xiaole_core.test_chat_v2_api -v`

Expected: all diagnostics/API tests PASS.

### Task 5: Local API E2E and Regression Verification

**Files:**
- Create: `scripts/run_self_profile_local_e2e.py`
- Create: `tests/xiaole_core/test_self_profile_local_e2e.py`

**Interfaces:**
- Produces a local-only executable acceptance harness using controlled local
  Profile data and no external action or notification gateway.
- Exits 0 only when all seven required questions and safe diagnostics pass.

- [ ] **Step 1: Write failing E2E test around the API boundary**

Exercise `/api/v2/chat` with authentication dependency overridden locally and a
real `BrainCore` wired to in-memory context, a controlled Profile gateway, and
model/Memory doubles that raise on use. Assert the six required self-profile
questions plus `你记得我什么？` satisfy current/privacy/provenance constraints;
assert the history question includes the historical school only as history.

- [ ] **Step 2: Run RED**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_self_profile_local_e2e -v`

Expected: FAIL until the local harness and completed integration are present.

- [ ] **Step 3: Implement the reusable local harness**

Keep all Profile values inside controlled test fixtures, capture Safe Diagnostics
in memory, print only PASS/FAIL checks, and never connect to production, Lezhi,
XiaoKe, Bark, or notification endpoints.

- [ ] **Step 4: Run focused E2E GREEN**

Run: `./venv/bin/python -m unittest tests.xiaole_core.test_self_profile_local_e2e -v`

Run: `python scripts/run_self_profile_local_e2e.py`

Expected: both exit 0 and the script reports `Self Profile Grounding Local: PASS`.

- [ ] **Step 5: Run full relevant regression suite**

Run: `./venv/bin/python -m unittest discover -s tests/xiaole_core -t . -v`

Run: `python -m compileall -q xiaole_core routers/chat_v2.py scripts/run_self_profile_local_e2e.py`

Run: `git diff --check`

Expected: all commands exit 0. Review `git status --short` and confirm only the
approved backend docs, implementation, tests, and local harness changed. Do not
commit, push, deploy, or publish.
