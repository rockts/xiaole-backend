# XiaoLe LLM Cost Governance Design

## Status and scope

This design addresses XiaoLe's internal LLM governance gap. It does not rotate,
revoke, create, or modify any production API key and it cannot block a client
that calls DeepSeek directly with a leaked key.

The 2026-08-17 to 2026-08-18 billing incident has two independent causes:

1. The leaked `xiaole-ai-prod` key was used outside the observable XiaoLe NAS
   backend. This is the direct cause of the abnormal bill.
2. XiaoLe has no single enforcement point for model choice, context size,
   retries, usage accounting, budgets, or background priority. This design fixes
   that architectural gap.

## Existing call inventory

Production DeepSeek HTTP requests currently originate from two code surfaces:

- Legacy `XiaoLeAgent`: non-streaming, history-aware, and streaming helpers in
  `agent.py`. Several product features call those helpers, including chat,
  information extraction, document summarization, tool intent selection, task
  planning, and proactive analysis.
- Core2 `OpenAICompatibleProvider`: `xiaole_core/models.py`, used for intent
  classification and final response generation.

Feature-level callers are identified separately even when they share an HTTP
helper: `legacy.chat`, `legacy.tool_selection`, `legacy.memory_extraction`,
`legacy.document_summary`, `legacy.task_planning`, `core2.intent`,
`core2.answer`, `memory`, `notification`, and `scheduler`.

After migration, only `llm_gateway.py` may contain the DeepSeek API URL or send
an HTTP request authenticated by `DEEPSEEK_API_KEY`. Qwen and vision providers
remain separate because they use different keys and billing domains.

## Architecture

`LLMGateway` is the single production DeepSeek enforcement point. Legacy and
Core2 become adapters that build an `LLMRequest` and delegate to the gateway.
The gateway performs the following ordered pipeline:

1. Validate caller, request/task identity, foreground/background priority, and
   explicit model policy.
2. Normalize and independently cap system text, chat history, memory context,
   and tool-result context.
3. Atomically reserve a per-task and budget-pool call before network access.
4. Execute a bounded request with bounded exponential-backoff retries.
5. Parse provider usage, estimate cost, and finalize the ledger record.
6. On failure, finalize the record with a stable error category and fail closed.
7. Emit a structured log and request a cost alert when a fuse trips.

The gateway accepts an injected ledger, transport, clock, sleeper, and notifier
so governance behavior is testable without external calls.

## Model policy

- Default and background model: `deepseek-v4-flash`.
- `deepseek-v4-pro` is accepted only when `priority=user` and
  `allow_pro=true`. Both conditions are mandatory.
- Background callers can never use or upgrade to Pro.
- Legacy environment values `deepseek-chat` and `deepseek-reasoner` are
  normalized to Flash. Unknown model names fail closed.
- No automatic Flash-to-Pro fallback exists.

## Context policy

Limits apply before every provider request:

- System/persona/instructions: 8,000 estimated tokens.
- Chat history: 12,000 estimated tokens, retaining the newest complete messages.
- Memory: 4,000 estimated tokens.
- Tool results: 4,000 estimated tokens.
- Current user input: 4,000 estimated tokens.
- Absolute combined input: 24,000 estimated tokens.

The estimator conservatively treats every Unicode code point as one token when
provider tokenization is unavailable. This intentionally overestimates English
and avoids the unsafe chars-per-token assumption for Chinese. Each category is truncated
independently; the gateway records which categories were truncated. Full
conversation history or a complete knowledge base is never sent implicitly.

## Call, retry, and loop limits

- Ordinary foreground chat: maximum 3 LLM calls for one request ID. This covers
  optional intent/tool selection plus one final answer and one bounded recovery.
- Background task: maximum 2 LLM calls for one task ID.
- Agent/tool orchestration: maximum 3 rounds. A fourth round returns a bounded
  termination result without calling a model.
- Transport retry: maximum 2 retries after the first attempt, delays 1 and 2
  seconds, only for timeout, connection failure, HTTP 429, and HTTP 5xx.
- Authentication, billing, policy, budget, invalid request, and context errors
  are never retried.

## Usage ledger and budgets

Every attempted call records:

- timestamp, caller, source, priority, request ID, task ID;
- requested and effective model;
- estimated input and actual input/output/cache-hit/cache-miss tokens;
- estimated cost in CNY, duration, attempt count;
- success/failure, error category, and truncation categories.

The default limits are deliberately conservative and configurable through
non-secret environment variables:

- Foreground user pool: 30 calls/hour, 100 calls/day.
- Background pool: 10 calls/hour, 30 calls/day.
- Global hard ceiling: 40 calls/hour, 120 calls/day.
- Per-task limits: 3 foreground calls, 2 background calls.

Reservations are atomic. If the ledger is unavailable, cannot acquire its lock,
or cannot persist the reservation, the request fails closed before network I/O.
Background budget exhaustion blocks background only. A global hard ceiling
blocks all new model calls; foreground exhaustion blocks only foreground calls.

The initial implementation uses a process-safe SQLite ledger in the mounted
`logs` directory with WAL mode, transactions, unique request/task sequence keys,
and a short busy timeout. This is deployable without a production schema change.
For a future horizontally distributed deployment, the same ledger interface can
be backed by PostgreSQL without changing callers.

## Scheduler and worker idempotency

Scheduler registration retains fixed job IDs and adds a process-wide start lock.
Each background execution obtains a durable lease keyed by job name and scheduled
time bucket before work begins. An existing unexpired lease causes a no-op.
Leases have explicit expiry so a crashed worker can recover later without
concurrent duplicate execution.

## Alerting

Fuse events emit structured logs and call an injected notification adapter. The
default adapter reuses the existing notification capability when configured.
Alert delivery failure is recorded but never causes the blocked LLM request to
proceed. Alerts contain counts, pool, threshold, caller, and time bucket; they
never contain prompts, responses, authorization headers, or API keys.

## Secret handling

Production code reads DeepSeek credentials only through
`os.getenv("DEEPSEEK_API_KEY")` while building the gateway. The gateway never
logs the key or authorization header. Tests use non-secret placeholders. Static
verification fails if production files outside the gateway contain the DeepSeek
URL, construct a DeepSeek authorization header, or contain a secret-shaped
literal.

Historical secret removal is outside this implementation because rewriting a
public Git history is destructive and requires separate approval.

## Tests and acceptance

Automated tests must prove:

- retries stop after the configured maximum and use exponential backoff;
- agent/tool rounds stop at three;
- scheduler registration and execution leases prevent duplicates;
- a task cannot consume more than its call cap;
- background work stops at its hourly/daily budget while foreground remains
  available;
- a normal chat cannot exceed three LLM calls;
- model policy forbids Pro for background callers;
- each context category and total input are bounded;
- ledger fields and cost calculations are populated;
- ledger failure prevents transport access;
- static production search finds no DeepSeek network path outside the gateway;
- a day with two or three ordinary chats and no new background event remains
  below ten total DeepSeek calls, never tens or hundreds.
