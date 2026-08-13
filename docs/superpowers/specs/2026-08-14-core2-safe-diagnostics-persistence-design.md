# Core2 Safe Diagnostics Persistence Design

## Goal

Persist one final, queryable, value-free diagnostics event for every completed Core2 request without changing routing, matching, Profile handling, model behavior, or user answers.

## Design

`Core2SafeDiagnosticsEvent` is an independent strict whitelist model. Its serializer constructs each log field explicitly and never serializes a request, response, or `Diagnostics` object. `BrainCore.respond()` creates the final response first, then emits exactly one compact JSON event through XiaoLe's existing `xiaole_ai` logger.

The event's `scope` is the current `IntentDecision.reason_code`: it describes why the intent router selected the request path, not an authorization, data-access, or Profile scope. This semantic is documented in the type and protected by tests.

If Brain cannot return a response, the router emits one validation-safe fallback event with a router-owned request ID and fixed safe defaults. A successful Brain response is never logged again by the router.

No log database or independent debug file is added. Existing rotating `xiaole_ai.log` handlers and retention remain unchanged.

## Safety

Only event name, request ID, intent, routing scope, gateway names, model-called boolean, and the five Profile diagnostics fields can be serialized. Dynamic exception text and all user/Profile/model/memory content are excluded by construction.
