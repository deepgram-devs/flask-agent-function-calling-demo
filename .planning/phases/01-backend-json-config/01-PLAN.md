---
wave: 1
stream: A
depends_on: []
files_modified:
  - common/agent_templates.py
  - client.py
  - configs/ (new directory)
autonomous: true
requirements:
  - R-01-A
  - R-01-B
  - R-01-C
  - R-01-D
  - R-01-E
  - R-01-F
  - R-01-G
  - R-01-H
---

# Phase 1: Backend JSON Config System

## Goal
Replace hardcoded `match/case` industry templates with dynamic JSON config loading. Add CRUD REST routes for configs.

## must_haves
- `configs/` directory exists at repo root
- `GET /configs` returns JSON array of all config objects
- `POST /configs` accepts JSON body, writes file, returns created config
- `DELETE /configs/<id>` removes config file
- `AgentTemplates` class loads from `configs/*.json` instead of hardcoded match/case
- `VoiceAgent` init signature unchanged: `VoiceAgent(industry, voiceModel, voiceName, language, browser_audio)`
- `/industries` route still works (alias or kept)

## Tasks

<task id="1.1">
**Create `configs/` directory and JSON schema**

Create the `configs/` directory at repo root. Document the JSON schema:
```json
{
  "id": "string (slug, matches filename)",
  "name": "string (display name)",
  "company": "string",
  "personality": "string (short descriptor)",
  "language": "string (BCP-47, e.g. en-US, tl)",
  "voiceModel": "string (e.g. aura-2-arcas-en)",
  "voiceName": "string (display name for voice)",
  "systemPrompt": "string (full system prompt)",
  "functions": ["array of function names from FUNCTION_MAP"],
  "hotword": "string (optional, e.g. 'Hey Saga')",
  "mode": "voice_agent | agent_assist",
  "greeting": "string (initial greeting message)"
}
```

Create `configs/.gitkeep` placeholder so the empty directory is tracked.
</task>

<task id="1.2">
**Rewrite `common/agent_templates.py` — JSON config loader**

Replace the hardcoded `AgentTemplates` class with a dynamic JSON loader:

```python
import json
import os
from pathlib import Path

CONFIGS_DIR = Path(__file__).parent.parent / "configs"

class AgentTemplates:
    @staticmethod
    def load_all() -> list[dict]:
        """Return all config dicts from configs/*.json"""
        configs = []
        for f in sorted(CONFIGS_DIR.glob("*.json")):
            with open(f) as fh:
                configs.append(json.load(fh))
        return configs

    @staticmethod
    def load(config_id: str) -> dict | None:
        """Load a single config by id (matches filename stem)"""
        path = CONFIGS_DIR / f"{config_id}.json"
        if not path.exists():
            return None
        with open(path) as fh:
            return json.load(fh)

    @staticmethod
    def save(config: dict) -> dict:
        """Write a config dict to configs/<id>.json"""
        config_id = config["id"]
        path = CONFIGS_DIR / f"{config_id}.json"
        with open(path, "w") as fh:
            json.dump(config, fh, indent=2)
        return config

    @staticmethod
    def delete(config_id: str) -> bool:
        """Delete configs/<id>.json. Returns True if deleted."""
        path = CONFIGS_DIR / f"{config_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # --- Backward-compat helpers (used by VoiceAgent) ---
    @staticmethod
    def get_system_prompt(config_id: str) -> str:
        cfg = AgentTemplates.load(config_id)
        if cfg:
            return cfg.get("systemPrompt", "")
        return ""

    @staticmethod
    def get_greeting(config_id: str) -> str:
        cfg = AgentTemplates.load(config_id)
        if cfg:
            return cfg.get("greeting", "Hello, how can I help you?")
        return "Hello, how can I help you?"

    @staticmethod
    def get_functions(config_id: str) -> list[str]:
        cfg = AgentTemplates.load(config_id)
        if cfg:
            return cfg.get("functions", [])
        return []
```

Remove all hardcoded WELCOME_MESSAGES and CAPABILITY_TEMPLATES dicts. Keep any methods that `client.py` calls — add stubs that delegate to the JSON loader.
</task>

<task id="1.3">
**Add CRUD routes to `client.py`**

Add three new Flask routes below the existing `/industries` route:

```python
@app.route("/configs", methods=["GET"])
def get_configs():
    """Return all demo configs as JSON array."""
    return jsonify(AgentTemplates.load_all())

@app.route("/configs", methods=["POST"])
def create_config():
    """Create a new demo config. Body must include 'id' field."""
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"error": "id field required"}), 400
    config = AgentTemplates.save(data)
    return jsonify(config), 201

@app.route("/configs/<config_id>", methods=["DELETE"])
def delete_config(config_id):
    """Delete a demo config by id."""
    deleted = AgentTemplates.delete(config_id)
    if deleted:
        return jsonify({"deleted": config_id}), 200
    return jsonify({"error": "not found"}), 404
```

Also update (or alias) the `/industries` route to use `AgentTemplates.load_all()` so existing frontend code doesn't break during Phase 2 transition.
</task>

<task id="1.4">
**Verify VoiceAgent compatibility**

Audit `client.py` VoiceAgent class for all calls to `AgentTemplates`. Ensure every call is satisfied by the new JSON-based methods. The init signature `VoiceAgent(industry, voiceModel, voiceName, language, browser_audio)` must remain valid -- the `industry` parameter now maps to a config `id`.

Run a quick smoke test:
```bash
cd /coding/flask-agent-function-calling-demo
python -c "from common.agent_templates import AgentTemplates; print(AgentTemplates.load_all())"
```
Should return an empty list (or list of any configs already present) without errors.
</task>

## Verification Criteria
- `python -c "from common.agent_templates import AgentTemplates; print('ok')"` exits 0
- `GET /configs` returns `[]` (empty list, no configs yet) with 200 status
- `POST /configs` with valid JSON creates a file in `configs/` and returns 201
- `DELETE /configs/<id>` removes the file and returns 200; 404 if missing
- No import errors when starting Flask: `python client.py` starts without crashing
- Existing `/industries` route still returns 200
