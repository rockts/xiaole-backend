# Profile Gateway Safe Diagnostics Design

## Goal

Add safe, finite diagnostics to the Core2 current-employment path without changing matching, profile facts, deterministic eligibility, or user-facing answers.

## Design

`MemoryGateway.profile()` returns an internal result containing the parsed payload plus a finite gateway result and reason codes. It maps timeout, connection, HTTP, JSON, and schema failures without retaining URLs, response bodies, credentials, or exception text.

`BrainCore` accepts that internal result while remaining compatible with existing read-gateway test doubles that return dictionaries. For current-employment requests it evaluates the existing `current_school` conditions in their existing order and projects only booleans, finite states, and finite reason codes into `Diagnostics`.

## Public diagnostics

- `profile_gateway_called`: boolean
- `profile_gateway_result`: `not_called | success | unavailable | unauthorized | invalid_response | missing_fact`
- `profile_current_school_state`: `not_applicable | ready | missing | not_confirmed | wrong_subject | invalid`
- `deterministic_profile_hit`: boolean
- `profile_reason_codes`: finite string enum list

The diagnostics never include profile values, raw responses, URLs, exception messages, authorization data, prompts, or conversation history.

## Verification

Unit tests cover success, 401, timeout, missing `fields`, missing fact, unconfirmed status, wrong subject, empty value, and serialized diagnostics leakage. Existing Core2, Real Use Recovery, Home, Legacy/Scheduler, compileall, and diff checks remain required.
