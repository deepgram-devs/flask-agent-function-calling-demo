# Flask Voice Agent Demo Redesign — Requirements

**Project:** Flask Voice Agent Demo Redesign
**Created:** 2026-02-26

---

## R-01: JSON Config System (Backend)

- R-01-A: Create `configs/` directory at repo root with one JSON file per demo
- R-01-B: JSON schema per config: `id`, `name`, `company`, `personality`, `language`, `voiceModel`, `voiceName`, `systemPrompt`, `functions` (array), `hotword` (optional), `mode` (`voice_agent` | `agent_assist`), `greeting`
- R-01-C: Replace hardcoded `match/case` in `common/agent_templates.py` with dynamic JSON config loader
- R-01-D: New Flask route: `GET /configs` — returns list of all configs
- R-01-E: New Flask route: `POST /configs` — creates new config, writes JSON file
- R-01-F: New Flask route: `DELETE /configs/<id>` — deletes config file
- R-01-G: Maintain backward compat: `VoiceAgent(industry, voiceModel, voiceName, language, browser_audio)` signature unchanged
- R-01-H: `/industries` route kept or aliased to `/configs` for compatibility

## R-02: Frontend Redesign (Deepgram Design System)

- R-02-A: Replace `static/style.css` with Deepgram CDN: `https://unpkg.com/@deepgram/styles/dist/deepgram.css`
- R-02-B: Load Font Awesome: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css`
- R-02-C: Force dark mode: `:root { color-scheme: dark; }`
- R-02-D: Design tokens: brand green `#13ef95`, brand blue `#149afb`, bg `#0b0b0c`, Inter/Noto Sans fonts
- R-02-E: Use `dg-columns` for 3-panel layout (left sidebar + center conversation + right logs)
- R-02-F: Demo selector: replace popup with `dg-card--selectable` grid loading all JSON configs from `GET /configs`
- R-02-G: Start button: large `dg-btn--primary` with Font Awesome `fa-microphone` icon
- R-02-H: Status indicator: `dg-status` component
- R-02-I: Language/voice selects: `dg-select` inside `dg-form-field`
- R-02-J: Components to use: `dg-btn`, `dg-card dg-card--selectable`, `dg-form-field`, `dg-input`, `dg-select`, `dg-textarea`, `dg-toggle`, `dg-status`, `dg-spinner`, `dg-columns`, `dg-page-heading`, `dg-alert`

## R-03: Builder Form (New Feature)

- R-03-A: "New Demo" button opens slide-in panel or modal
- R-03-B: Form fields: name, company, personality (textarea), system prompt (textarea), language (select), voice model (select from `/tts-models`), functions (toggle group), hotword (optional input)
- R-03-C: Submit POSTs to `/configs`; new card appears in selector immediately (no page reload)
- R-03-D: Edit existing: pre-populate form from existing config

## R-04: Demo JSON Configs

- R-04-A: `hey-manny.json` — Manny Pacquiao persona, Filipino English BPO, voice model `aura-2-arcas-en`
- R-04-B: `dubai-real-estate.json` — Luxury real estate AI concierge, Dubai, English, professional
- R-04-C: `bpo-tagalog.json` — BPO call center agent, Tagalog, language `tl`, voice model `aura-2-luna-en`
- R-04-D: `hey-saga.json` — Smart city concierge, hotword "Hey Saga", Saga persona
- R-04-E: `deepgram.json` — Existing Deepgram tech support demo converted to config format

## R-05: Integration

- R-05-A: Frontend demo selector populates from `GET /configs` at page load
- R-05-B: Selecting a config loads it into the VoiceAgent session on connect
- R-05-C: Builder form creates configs via `POST /configs` and refreshes selector grid live
- R-05-D: All 5 demo configs render in selector and successfully start a voice session
- R-05-E: Existing WebSocket/audio logic in `client.py` remains unchanged

## Constraints

- Keep all Python WebSocket/audio logic in `client.py` untouched
- No external JS frameworks — vanilla JS only for frontend
- Python only for backend — no Node.js
- VoiceAgent class init signature must remain compatible
