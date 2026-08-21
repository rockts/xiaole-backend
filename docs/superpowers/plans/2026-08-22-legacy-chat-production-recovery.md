# Legacy Chat Production Recovery Implementation Plan

> **For agentic workers:** Execute inline with strict Red -> Green verification. Do not change Core2, provider secrets, fallback policy, or frontend IA.

**Goal:** Prevent short ordinary Legacy conversations from blocking on an unnecessary tool-intent model call before the real answer.

**Architecture:** Keep the existing Legacy answer and DeepSeek-to-Qwen fallback chain unchanged. Extract the existing simple-chat predicate into one helper, evaluate it before tool selection, and reuse the result for the later complex-task guard.

**Tech Stack:** Python, unittest, FastAPI Legacy `/chat/stream`, Vue/Vitest regression suite.

**Spec:** User-provided XiaoLe Compatibility Mode Production Recovery requirements, 2026-08-22.

## Global Constraints

- No Core2 changes.
- No provider secret or fallback-policy changes.
- No UI IA, Home, Knowledge, Action, Profile, Lezhi, or XiaoKe changes.
- Preserve the Legacy answer call; only skip unnecessary pre-answer tool intent analysis for short ordinary chat.
- Do not send Bark or execute Action.

---

### Task 1: Reproduce the backend blocking decision

**Files:**
- Modify: `tests/test_legacy_model_fallback.py`
- Modify: `agent.py`

**Interfaces:**
- Consumes: Legacy chat prompt text.
- Produces: `XiaoLeAgent._is_simple_chat(prompt) -> bool` used before tool selection and complex-task detection.

- [ ] Add a failing unit test proving `你好，只回复 OK` is ordinary chat and must bypass tool-intent analysis.
- [ ] Run the focused test and verify it fails because the helper/early bypass is absent.
- [ ] Add the minimal helper and move the existing simple-chat decision before tool selection.
- [ ] Run focused Legacy tests and verify the main answer/fallback behavior remains intact.

### Task 2: Verify lifecycle regressions

**Files:**
- Test only: `xiaole-web/src/chat/__tests__/transports.test.js`
- Test only: `xiaole-web/src/services/__tests__/*`
- Test only: `xiaole-web/src/chat/__tests__/chatStoreCore2.test.js`

**Interfaces:**
- Consumes: current frontend Legacy stream callbacks and abort signal.
- Produces: evidence for success/fallback/error completion cleanup, stream close, abort cleanup, mode switching, and Core2 isolation.

- [ ] Run the focused frontend chat/transport suites.
- [ ] Add only missing regression coverage required to prove the observed lifecycle; do not change frontend production code unless a new RED exposes an independent defect.
- [ ] Run the complete frontend test suite and production build.

### Task 3: Release and production acceptance

**Files:**
- No additional product files unless deployment metadata requires it.

**Interfaces:**
- Consumes: verified backend commit and existing CI/deployment workflow.
- Produces: deployed Legacy behavior and production acceptance evidence.

- [ ] Run the full relevant backend suite and inspect the final diff.
- [ ] Commit and push the isolated fix, then observe CI/deployment to completion.
- [ ] Verify the same authenticated production Legacy endpoint reports HTTP status, provider/fallback, completion, and latency without exposing secrets.
- [ ] In production Web, run Legacy `你好，只回复 OK` three times and verify OK plus cleared thinking.
- [ ] Verify standard conversation, standard -> Legacy -> standard, new conversation, old Legacy session, attachment compatibility prompt, Home, Knowledge, and Action without executing Action or sending Bark.
- [ ] Report migration status and PASS/FAIL.
