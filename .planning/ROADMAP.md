# Flask Voice Agent Demo Redesign — Roadmap

**Project:** Flask Voice Agent Demo Redesign
**Working directory:** /coding/flask-agent-function-calling-demo
**Created:** 2026-02-26

---

## Phases

### Phase 1: Backend JSON Config System
**Goal:** Replace hardcoded `match/case` industry templates with a dynamic JSON config loader. Add CRUD routes for configs.
**Parallel stream:** A
**Status:** Planned

### Phase 2: Frontend Redesign (Deepgram Design System)
**Goal:** Replace `static/style.css` and `templates/index.html` with Deepgram design system components, new 3-panel layout, demo selector grid, and builder form.
**Parallel stream:** B
**Status:** Planned

### Phase 3: Demo JSON Configs
**Goal:** Create 5 demo JSON config files in `configs/` directory: hey-manny, dubai-real-estate, bpo-tagalog, hey-saga, deepgram.
**Parallel stream:** C
**Status:** Planned

### Phase 4: Integration
**Goal:** Wire together backend config API, frontend selector/builder, and demo configs. Verify end-to-end voice agent flow works with any config.
**Depends on:** Phase 1, 2, 3
**Status:** Planned

---

## Parallel Execution Strategy

Phases 1, 2, 3 can all run in parallel (no dependencies between them).
Phase 4 depends on all three completing first.

```
Phase 1 (Backend) ─┐
Phase 2 (Frontend) ─┼──► Phase 4 (Integration)
Phase 3 (Configs) ──┘
```
