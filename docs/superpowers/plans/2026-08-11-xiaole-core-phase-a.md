# 小乐 2.0 Core Phase A Implementation Plan

> **For agentic workers:** Execute inline with strict Red → Green → Refactor cycles. Do not commit, push, deploy, modify Lezhi/Xiaoke, connect production, or send Bark.

**Goal:** Build an isolated XiaoLe Brain Core and prove conversation, grounded Lezhi memory, and Xiaoke notification action paths.

**Architecture:** Add `xiaole_core` as a dependency-injected orchestration boundary inside the existing backend. Reuse only JWT and Conversation/Message persistence primitives; hide Lezhi and Xiaoke behind HTTP gateways and leave every old agent capability untouched.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, SQLAlchemy, requests/httpx, standard-library unittest.

## Global Constraints

- `/api/v2/chat` reuses `auth.get_current_user`; no anonymous or second auth system.
- New Core never imports or instantiates `XiaoLeAgent`, old Memory, TaskExecutor, ToolRegistry, Reminder, behavior, or proactive systems.
- Context reads/writes only `conversations` and `messages`, isolated by authenticated user and conversation ID, maximum 12 messages.
- Lezhi answer and complete sources are the only factual basis; no unsupported enrichment.
- Brain never sees Xiaoke Attempt/Dispatcher/Adapter/monitor-service/Bark internals.
- Automated tests never connect to real external services.
- E2E B alone may call local Lezhi; E2E C uses local Xiaoke plus a mock notification downstream.
- No real Bark, production Web switch, commit, push, or deployment.

---

### Task 1: Core contracts and intent routing

**Files:** Create `xiaole_core/__init__.py`, `xiaole_core/schemas.py`, `xiaole_core/errors.py`, `xiaole_core/intent.py`, `xiaole_core/persona.md`; test `tests/xiaole_core/test_intent.py`, `test_schemas.py`.

**Interfaces:** `Intent`, `BrainRequest`, `BrainResponse`, `MemoryResult`, `ActionCommand`, `ActionResult`, `Diagnostics`, and `IntentRouter.classify(message, history, request_id)`.

- [ ] Write unittest cases for three deterministic intents, ambiguous classifier fallback, invalid fallback safety, action command schema, and diagnostics secret-field exclusion.
- [ ] Run `./venv/bin/python -m unittest tests.xiaole_core.test_intent tests.xiaole_core.test_schemas -v`; confirm missing-module failure.
- [ ] Implement minimal strict Pydantic contracts, deterministic rules, injected classifier fallback, domain errors, and persona file.
- [ ] Re-run the focused tests; confirm all pass.
- [ ] Refactor names only while keeping focused tests green.

### Task 2: Short-context repository

**Files:** Create `xiaole_core/context.py`; test `tests/xiaole_core/test_context.py`.

**Interfaces:** `CoreContextRepository.resolve(user_id, conversation_id, first_message) -> str`, `history(user_id, conversation_id, limit=12)`, and `append_exchange(...)`.

- [ ] Write tests with a temporary SQLite database for new conversation creation, authenticated ownership, cross-user denial, different-conversation isolation, 12-message cap, and writes limited to conversations/messages.
- [ ] Run the focused test and confirm missing implementation failure.
- [ ] Implement repository queries using injected SQLAlchemy session factory and existing `Conversation`/`Message` models; every existing-conversation query includes both session_id and user_id.
- [ ] Run focused tests and confirm pass; inspect SQL/table counts to prove no other table writes.

### Task 3: Primary/fallback model router

**Files:** Create `xiaole_core/models.py`; test `tests/xiaole_core/test_models.py`.

**Interfaces:** `ModelProvider.complete(system_prompt, messages, request_id)`, `ModelRouter.complete(...) -> ModelResult`, and `ModelRouter.classify(...)`.

- [ ] Test primary success, retryable primary failure to fallback, both failures, non-retryable configuration/auth failure, finite calls, and sanitized diagnostics.
- [ ] Run focused tests and observe failure because router is absent.
- [ ] Implement a provider-neutral router and OpenAI-compatible HTTP provider using environment configuration; no SDK details in Brain.
- [ ] Run focused tests and confirm pass; verify tests use fake providers and no network.

### Task 4: Lezhi Memory Gateway

**Files:** Create `xiaole_core/gateways/__init__.py`, `memory.py`; test `tests/xiaole_core/test_memory_gateway.py`.

**Interfaces:** `MemoryGateway.ask(question, context, request_id) -> MemoryResult`.

- [ ] Test exact POST `/ask` request, optional `X-KOS-Token`, full source preservation, confidence mapping, timeout/403/non-JSON/ok=false mapping, and token exclusion.
- [ ] Run focused tests and observe missing implementation failure.
- [ ] Implement with an injected transport/session, configured URL/token/timeout, and domain errors; never read Lezhi files.
- [ ] Run focused tests and confirm pass; compare fixtures with the currently verified Lezhi response shape.

### Task 5: Xiaoke Action Gateway

**Files:** Create `xiaole_core/gateways/action.py`; test `tests/xiaole_core/test_action_gateway.py`.

**Interfaces:** `ActionGateway.execute(command, request_id) -> ActionResult`.

- [ ] Test Bearer POST `/v1/tasks`, real TaskCommand field names, task ID capture, GET polling, success, failed/cancelled/dead, timeout, idempotency, and internal-field exclusion.
- [ ] Run focused tests and observe missing implementation failure.
- [ ] Implement injected HTTP transport and clock/sleep, allow only `notification.send`, and expose only safe result/evidence.
- [ ] Run focused tests and confirm pass; prove no real Xiaoke endpoint is contacted.

### Task 6: Brain orchestration and grounded behavior

**Files:** Create `xiaole_core/brain.py`; test `tests/xiaole_core/test_brain.py`.

**Interfaces:** `BrainCore.respond(request, user_id) -> BrainResponse`.

- [ ] Test conversation calls neither gateway; memory calls only Memory Gateway and preserves all sources; memory unavailable cannot fabricate; action calls only Action Gateway; success/failure wording follows status; context exchange persists.
- [ ] Add a grounded-memory test where a model attempts to add an unsupported fact and prove the final answer remains constrained to Lezhi output.
- [ ] Run focused tests and observe missing implementation failure.
- [ ] Implement one-gateway-at-most orchestration. For Phase A memory, use Lezhi answer as the response with only deterministic light formatting, avoiding free-form factual regeneration.
- [ ] Run focused tests and confirm pass.

### Task 7: JWT-protected v2 API and dependency assembly

**Files:** Create `xiaole_core/dependencies.py`, `routers/chat_v2.py`; modify `main.py`; test `tests/xiaole_core/test_chat_v2_api.py`.

**Interfaces:** `POST /api/v2/chat`, `get_brain_core()`, and test override hooks through FastAPI dependencies.

- [ ] Test no JWT 401, invalid JWT 401, valid existing JWT success, authenticated user passed to Core, conversation ownership 403, and response schema.
- [ ] Run focused test and observe 404/missing route failure.
- [ ] Implement route with `Depends(get_current_user)` and `Depends(get_brain_core)`; include only under `/api` so no anonymous/unprefixed duplicate is created.
- [ ] Run focused tests and confirm pass.

### Task 8: Architecture, security, and compatibility suite

**Files:** Create `tests/xiaole_core/test_architecture_boundaries.py`, `test_security.py`, `test_compatibility.py`; update `.env.example` and `README.md` only for new environment variables and local v2 test instructions.

- [ ] Test forbidden imports, no old-table access, secret redaction, no Prompt/Token diagnostics, old chat routes still registered, and external network prohibition in the automated suite.
- [ ] Run tests and observe each new guard fail for the intended missing documentation/guard condition.
- [ ] Add minimal documentation/config and boundary helpers needed to satisfy the tests; do not refactor old routes.
- [ ] Run `./venv/bin/python -m unittest discover -s tests -v` and record total/pass/fail.

### Task 9: E2E A, B, and C

**Files:** Create `scripts/run_xiaole_core_e2e.py` and, if needed, test-only fixture helpers under `tests/xiaole_core/`.

**Interfaces:** Script modes `conversation`, `memory`, `action`; JSON report includes production_connected and bark_sent booleans.

- [ ] Test the runner's safety defaults: action mode refuses any non-local Xiaoke URL and starts mock notification downstream configuration only.
- [ ] E2E A: run Core with deterministic local model provider; verify conversation intent and zero Gateway calls.
- [ ] E2E B: call currently running local `http://127.0.0.1:8765/ask`; verify memory intent, nonempty grounded answer, and unchanged sources. If service cannot run, stop B and report without modifying Lezhi.
- [ ] E2E C: start an isolated local Xiaoke Action Core process with temporary DB and a local mock monitor endpoint, then call through Action Gateway; verify success and mock delivery evidence. Do not load production notification settings.
- [ ] Re-run full automated suite after E2E work and run `git diff --check`.
- [ ] Record modified files, contracts, commands, exact results, non-use of old systems, and all safety flags; stop without Phase B.
