# XiaoLe 2.0 Deterministic Self Profile Grounding Design

## Goal

Establish one governed `self_profile` / `user_identity` read policy for natural
questions about the current user. The policy must prefer confirmed current User
Profile facts, minimize disclosure, isolate Legacy and conversation-derived
personal facts, and assign provenance deterministically.

This is not an exact-string answer patch. It is a routing, source-admission,
projection, rendering, and diagnostics boundary.

## Production Evidence and Root Cause

The failed production request emitted the following value-free Safe Diagnostics
classification:

- intent: `conversation`
- scope: `safe_default`
- gateways used: none
- Profile gateway called: false
- Memory gateway called: false
- model called: true

The conversation path sent the Core2 persona, the current request, and up to 12
messages from the shared conversation table to the model. It did not load the
confirmed current User Profile. Consequently, confirmed `current_school` never
entered the request and could not override an old school appearing in shared
conversation history.

Safe Diagnostics proves the request-level source categories, but intentionally
cannot attribute each emitted personal detail without reading sensitive content.
For that request, old school, subject, address, food, and family details were not
supplied by Profile or a live Lezhi Memory gateway call. They could only have
been reproduced from shared conversation content or invented by the model.

The statement that all facts came from user-confirmed Lezhi data was generated
by the model. No runtime provenance object supported it.

## Scope Classification

Add deterministic scopes below the broad `knowledge` intent:

- `self_profile`: a present-day summary of the current user.
- `employment_history`: an explicit request for past schools or employment.

`self_profile` includes natural phrasings such as:

- 你认识我吗？
- 你知道我是谁吗？
- 我是谁？
- 介绍一下我
- 你对我了解多少？
- 说说你知道的我
- 你记得我什么？

Classification uses normalized semantic phrase families and composable cues,
not one exact-match response table. Specific governed personal-fact routes such
as current employment and employment history run before the broad self-profile
matcher where necessary.

## Source Admission Policy

### Self profile

The default `self_profile` path may consume:

1. confirmed current User Profile fields;
2. governed Lezhi `user_knowledge` only through a purpose-specific structured
   gateway if that interface exists and returns field-level source metadata;
3. `needs_confirmation` state only to state that the item remains unconfirmed.

It must not consume:

- historical Profile fields;
- XiaoLe Legacy memories or facts;
- old schedules;
- behavior or learned-pattern data;
- conversation messages as personal-fact evidence;
- a free-form Memory answer;
- model prior knowledge or completion.

The initial implementation uses the existing Profile gateway only. It does not
change Lezhi Memory Governance or invent a new Lezhi endpoint. Governed
`user_knowledge` can be admitted later only through an additive structured
contract with field-level provenance.

### Employment history

The `employment_history` path may consume only confirmed Profile facts whose
status is explicitly historical and whose subject is the current user. It must
not infer history from Legacy, conversation, schedules, or free-form Memory.

## Priority and Conflict Rules

The global priority is:

1. confirmed current User Profile;
2. confirmed historical Profile, only for explicit historical scope;
3. governed Lezhi `user_knowledge` with field-level provenance;
4. `needs_confirmation`, rendered as unconfirmed state rather than a fact.

Legacy and conversation are not lower-priority candidates. They are excluded
sources for these scopes and therefore cannot override or supplement Profile.

When current and historical facts conflict, confirmed current Profile always
wins in current-user answers. A historical school never appears as the current
school. Historical facts appear only in explicit historical answers and are
labelled as historical.

## Default Privacy Projection

The default self-profile allowlist is:

- `display_name`
- coarse-grained `region`
- `current_school`
- `occupation`
- `professional_roles`
- `education_focus`
- `stable_interests`
- `long_term_projects`
- `long_term_goals`

Only fields for the current user with an allowed status are projected. The
default path excludes:

- precise address or residential compound;
- family member identities;
- children's schools or appearance;
- food preferences;
- dynamic age;
- old schedules;
- historical schools;
- unconfirmed current teaching subjects or grade coverage.

Missing optional fields are omitted. Relevant `needs_confirmation` fields are
summarized narrowly, for example that current teaching subjects remain
unconfirmed. The answer does not enumerate all missing Profile fields.

## Deterministic Rendering and Provenance

Both scopes use code-owned rendering. The answer model is not called.

Field provenance maps deterministically:

- confirmed Profile: `根据你已确认的个人资料`
- governed user knowledge: `根据乐知中保存的资料`
- historical Profile: explicitly identifies the fact as a past experience
- needs confirmation: `这一项目前还没有确认`

Mixed sources must be attributed separately. The renderer must never emit a
blanket user-confirmed claim for mixed or unverified facts. Model-generated
provenance is impossible because the model is outside the path.

If Profile is unavailable, unauthorized, invalid, or missing required structure,
the response states that the current profile cannot be safely confirmed. It does
not fall back to Legacy, conversation, Memory search, or the model.

## Components and Data Flow

1. `IntentRouter` assigns the broad `knowledge` intent and a deterministic
   `self_profile` or `employment_history` reason code.
2. `BrainCore` converts the reason code into a read-policy scope.
3. The existing Profile gateway is called exactly once.
4. A focused projector admits only fields, statuses, subjects, and scopes allowed
   by this design.
5. A deterministic renderer builds the concise answer and provenance language.
6. The response is persisted in conversation history only after rendering; past
   conversation content never feeds the current personal-fact decision.
7. One value-free Safe Diagnostics event records the route and source categories.

No Profile data, Legacy data, or Lezhi data is modified or deleted.

## Safe Diagnostics

Extend the strict whitelist event with finite, value-free metadata sufficient to
audit these scopes:

- route scope: `self_profile` or `employment_history`
- gateways used
- Profile gateway called/result
- model called
- admitted source categories
- excluded source categories
- renderer: `deterministic`
- provenance categories used

Allowed source category names are finite enums such as `confirmed_profile`,
`historical_profile`, `needs_confirmation`, and `governed_user_knowledge`.
Excluded category names include `legacy`, `conversation`, `old_schedule`,
`behavior_pattern`, and `model_inference`.

Diagnostics must never serialize the request, response, prompt, field names,
Profile values, Memory text, conversation text, family data, URLs, credentials,
or exception text.

## Testing Strategy

Use red-green-refactor TDD.

Unit tests cover:

- all required self-profile phrasings and close normalized variants;
- explicit employment-history routing;
- confirmed current Profile priority over historical and Legacy-shaped fixtures;
- default field allowlist and privacy exclusions;
- `needs_confirmation` rendering without promoting values to current facts;
- historical fields excluded from self-profile and admitted for history only;
- Profile failure is fail-closed without Memory, Legacy, conversation, or model;
- deterministic provenance for each admitted category;
- mixed-source blanket claims are impossible;
- value-free diagnostics and sensitive-marker absence.

Integration tests use real Brain components with controlled gateway fixtures and
prove gateway call counts, projected source categories, deterministic answers,
and `model_called=false`.

Local E2E sends the required natural questions through the local `/api/v2/chat`
boundary with a controlled local Profile gateway. It verifies:

- current school is the confirmed current value;
- historical school is absent from current self-profile answers;
- family, precise address, food, schedule, and unconfirmed subject data are absent;
- no incorrect provenance appears;
- explicit employment history includes the historical school and labels it as
  historical;
- captured Safe Diagnostics contain only allowed metadata.

Local E2E must not connect to XiaoKe or Bark and must not publish or deploy.

## Migration and Compatibility

No database or data migration is required. This change does not modify Profile
records, delete Legacy Memory, or alter Lezhi Memory Governance.

The API response schema remains backward compatible. Safe Diagnostics receives
additive optional finite fields with defaults so existing callers and stored logs
remain valid. Current-employment deterministic behavior remains intact.

Rollback consists of reverting the code and tests. No data rollback is needed.

## Out of Scope

- production deployment or validation;
- changes to User Profile values;
- deletion or rewriting of Legacy Memory;
- changes to Lezhi Memory Governance;
- XiaoKe, Home, Bark, notifications, or reminder behavior;
- a new general-purpose personal-data retrieval system.

## Acceptance

The local result is PASS only when all focused tests, relevant Core2 regression
tests, and Local E2E pass, with no prohibited data source consumed and no model
call for either governed scope. Anything less is reported as FAIL with the exact
unverified or failing gate.
