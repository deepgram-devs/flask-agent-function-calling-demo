---
wave: 2
stream: integration
depends_on:
  - 01-backend-json-config
  - 02-frontend-redesign
  - 03-demo-configs
files_modified:
  - client.py
  - templates/index.html
  - common/agent_templates.py
autonomous: true
requirements:
  - R-05-A
  - R-05-B
  - R-05-C
  - R-05-D
  - R-05-E
---

# Phase 4: Integration

## Goal
Wire backend JSON config API, frontend demo selector, builder form, and all 5 demo configs together. Verify complete end-to-end voice agent flow using any selected config.

## must_haves
- `GET /configs` returns all 5 demo configs at page load
- Frontend demo selector renders all 5 as `dg-card--selectable` cards
- Selecting a card and clicking Start Session initiates a voice session with that config's settings
- Builder form creates new config via POST, card appears in grid immediately
- VoiceAgent receives correct voiceModel, language, and systemPrompt from selected config
- All 5 demo configs successfully start a voice session without errors
- No regressions in existing audio/WebSocket logic

## Tasks

<task id="4.1">
**Audit and wire config selection to VoiceAgent**

In `client.py`, trace how the frontend triggers a VoiceAgent session. The SocketIO `connect` or `start_session` event handler likely receives the selected industry/config. Update this handler to:

1. Accept `config_id` in the event payload (in addition to or instead of `industry`)
2. Load the full config: `cfg = AgentTemplates.load(config_id)`
3. Extract `voiceModel`, `voiceName`, `language`, `systemPrompt`, `functions` from config
4. Pass to VoiceAgent: `VoiceAgent(config_id, cfg['voiceModel'], cfg['voiceName'], cfg['language'], browser_audio)`

If the frontend sends an `industry` field, accept both `industry` and `config_id` for backward compat:
```python
config_id = data.get('config_id') or data.get('industry', 'deepgram')
```
</task>

<task id="4.2">
**Update frontend JS to send config_id on session start**

In `templates/index.html`, find the SocketIO emit that starts the voice session. Update it to include the selected config:

```javascript
document.getElementById('start-btn').addEventListener('click', () => {
  if (!selectedConfig) {
    alert('Please select a demo first.');
    return;
  }
  const language = document.getElementById('language-select').value || selectedConfig.language;
  const voiceModel = document.getElementById('voice-model-select').value || selectedConfig.voiceModel;

  socket.emit('start_session', {
    config_id: selectedConfig.id,
    language: language,
    voice_model: voiceModel,
    browser_audio: true
  });
  setStatus('connecting', 'Connecting...');
});
```

Update the stop/disconnect button similarly to call `socket.emit('stop_session')` or the equivalent existing event.
</task>

<task id="4.3">
**Smoke test all 5 demo configs**

With Flask running, verify each config loads and renders:

```bash
cd /coding/flask-agent-function-calling-demo
# Start server in background
python client.py &
SERVER_PID=$!
sleep 2

# Test GET /configs returns 5 configs
python -c "
import urllib.request, json
res = urllib.request.urlopen('http://localhost:5000/configs')
configs = json.loads(res.read())
print(f'Configs count: {len(configs)}')
for c in configs:
    print(f'  - {c[\"id\"]}: {c[\"name\"]}')
assert len(configs) == 5, 'Expected 5 configs'
print('PASS: All 5 configs returned')
"

kill $SERVER_PID
```

Fix any loading errors (missing fields, JSON parse failures, import errors).
</task>

<task id="4.4">
**Verify builder form end-to-end**

Manual verification steps (document results):

1. Open browser to `http://localhost:5000`
2. Confirm 5 demo cards render in left panel
3. Click "New Demo" — builder panel slides in
4. Fill out all required fields with a test demo
5. Click Save — panel closes, new 6th card appears in grid
6. Click the new card — it highlights, name updates in center panel
7. Click the edit (pencil) icon — builder re-opens with pre-populated data
8. Verify `configs/test-demo.json` was created on disk
9. Delete the test file: `DELETE /configs/test-demo` (can use curl or browser dev tools)
10. Reload page — test card gone, 5 original configs present

Document: pass/fail for each step.
</task>

<task id="4.5">
**Final regression check**

Confirm no regressions against original functionality:

1. `python -c "import client"` -- no import errors
2. All routes respond:
   - `GET /` returns 200
   - `GET /configs` returns JSON array
   - `GET /industries` returns 200 (backward compat)
   - `GET /tts-models` returns 200 (if exists)
3. SocketIO connects successfully from browser
4. Audio microphone capture works (if test environment supports it)
5. VoiceAgent receives correct systemPrompt from selected config

If any audio/WebSocket code was accidentally modified, revert it from git:
```bash
git diff client.py | grep "^[+-]" | grep -v "config_id\|AgentTemplates\|configs route"
# Should only show config-related changes, not audio logic changes
```
</task>

## Verification Criteria
- Flask starts without errors
- `GET /configs` returns all 5 demo configs
- Frontend renders all 5 cards
- Selecting a card updates the session config
- Start Session with any of the 5 configs initiates VoiceAgent without errors
- Builder form creates new config and card appears without page reload
- `/industries` still returns 200
- No changes to audio/WebSocket processing logic in `client.py`
