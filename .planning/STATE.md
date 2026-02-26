# Flask Voice Agent Demo Redesign — Project State

**Project:** Flask Voice Agent Demo Redesign
**Working directory:** /coding/flask-agent-function-calling-demo
**Created:** 2026-02-26
**Status:** Planning

---

## Locked Decisions

### Backend
- JSON config loader replaces `match/case` in `common/agent_templates.py`
- `configs/` directory at repo root holds one JSON file per demo
- Config schema: `id`, `name`, `company`, `personality`, `language`, `voiceModel`, `voiceName`, `systemPrompt`, `functions[]`, `hotword?`, `mode`, `greeting`
- CRUD routes: `GET /configs`, `POST /configs`, `DELETE /configs/<id>`
- `VoiceAgent` class signature stays unchanged
- `/industries` aliased or kept for backward compat

### Frontend
- Deepgram CDN design system replaces custom CSS
- Force dark mode via `:root { color-scheme: dark; }`
- 3-panel layout using `dg-columns` (sidebar | conversation | logs)
- Demo selector = `dg-card--selectable` grid (replaces popup)
- Vanilla JS only — no frameworks
- Builder form as slide-in panel or modal

### Demo Configs
- 5 configs: hey-manny, dubai-real-estate, bpo-tagalog, hey-saga, deepgram

---

## Phase Status

| Phase | Name | Stream | Status |
|-------|------|--------|--------|
| 1 | Backend JSON Config System | A | Complete |
| 2 | Frontend Redesign | B | Complete |
| 3 | Demo JSON Configs | C | Complete |
| 4 | Integration | - | Planned |

---

## Key Files

- `client.py` — Flask server, VoiceAgent class, SocketIO handlers (DO NOT change audio/WS logic)
- `common/agent_templates.py` — AgentTemplates (hardcoded match/case, to be replaced)
- `common/agent_functions.py` — FUNCTION_MAP, FUNCTION_DEFINITIONS
- `common/prompt_templates.py` — PROMPT_TEMPLATE, DEEPGRAM_PROMPT_TEMPLATE
- `templates/index.html` — Main UI template (~500+ lines inline JS)
- `static/style.css` — Custom CSS (to be replaced with DG design system)
