# Resume Pipeline — Status

> **Current Phase:** Phase 7 — Bug Fixes & UX Improvements  
> **Plan Version:** 3.0 (Bugfix Round 1)  
> **Last Updated:** June 26, 2026 — 05:00 PM

---

## Current State

| Item | Status |
|------|--------|
| Phases 0-6 (MVP) | ✅ Complete — all committed and pushed to `origin main` |
| Fix: API response wrapping (5 hooks) | ✅ Complete — committed as `7750c05` |
| Fix: Dashboard `?.filter` crash (line 20) | ✅ Complete — committed as `f44fd3b` |
| **Phase 7 Plan** | ✅ Confirmed by Owner |
| Owner confirmation | ✅ Confirmed — June 26, 2026 |

---

## Open Issues

| # | Issue | Severity | Assigned To |
|---|-------|----------|-------------|
| 1 | `PromptManager()` missing required arg — 500 crash on generation | 🔴 Critical | `@backend-dev` |
| 2 | `LLMService()` ignores `.env` model — uses hardcoded `"gemini-2.5-pro"` | 🔴 Critical | `@backend-dev` |
| 3 | App init code outside try block in `run_points_only()` | 🟠 High | `@backend-dev` |
| 4 | Pydantic models not JSON-serializable in SSE complete event | 🟠 High | `@backend-dev` |
| 5 | Frontend blocks generation when no projects selected (no auto-match) | 🟡 Medium | `@frontend-dev` |
| 6 | Project selection UX requires manual clicks (no auto-match flow) | 🟡 Medium | `@frontend-dev` |

---

## Next Actions

1. ✅ **Phase 7 plan confirmed** by Owner
2. ☐ **Hand off** PLAN.md, TASKS.md, AGENT_TEAM.md to Orchestrator
3. ☐ Phase 7.1: Backend fixes (PromptManager, LLMService config, try block, SSE serialization)
4. ☐ Phase 7.2: Frontend auto-matching (remove guard, simplify UX)
5. ☐ Phase 7.3: Regression tests
