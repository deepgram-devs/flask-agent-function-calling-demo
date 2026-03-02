import json
import os
import glob
from pathlib import Path
from common.agent_functions import FUNCTION_DEFINITIONS, CHECK_HOTWORD_DEFINITION, CLOSE_HOTWORD_SESSION_DEFINITION, set_hotword
from common.prompt_templates import DEEPGRAM_PROMPT_TEMPLATE, PROMPT_TEMPLATE
from datetime import datetime


# ---------------------------------------------------------------------------
# Module-level constants (preserved for backward compat — client.py imports
# AGENT_AUDIO_SAMPLE_RATE directly from this module)
# ---------------------------------------------------------------------------

VOICE = "aura-2-thalia-en"

USER_AUDIO_SAMPLE_RATE = 16000
USER_AUDIO_SECS_PER_CHUNK = 0.05
USER_AUDIO_SAMPLES_PER_CHUNK = round(USER_AUDIO_SAMPLE_RATE * USER_AUDIO_SECS_PER_CHUNK)

AGENT_AUDIO_SAMPLE_RATE = 16000
AGENT_AUDIO_BYTES_PER_SEC = 2 * AGENT_AUDIO_SAMPLE_RATE

VOICE_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"

AUDIO_SETTINGS = {
    "input": {
        "encoding": "linear16",
        "sample_rate": USER_AUDIO_SAMPLE_RATE,
    },
    "output": {
        "encoding": "linear16",
        "sample_rate": AGENT_AUDIO_SAMPLE_RATE,
        "container": "none",
    },
}

# ---------------------------------------------------------------------------
# JSON config directory
# ---------------------------------------------------------------------------

CONFIGS_DIR = Path(__file__).parent.parent / "configs"


# ---------------------------------------------------------------------------
# Helper — read Deepgram documentation files (kept for deepgram config compat)
# ---------------------------------------------------------------------------

def read_documentation_files(docs_dir):
    """Read all .mdx files in the specified directory and return their contents."""
    documentation = {}
    if not os.path.exists(docs_dir):
        return documentation
    mdx_files = glob.glob(os.path.join(docs_dir, "*.mdx"))
    for file_path in mdx_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                key = os.path.basename(file_path).replace(".mdx", "")
                documentation[key] = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return documentation


# ---------------------------------------------------------------------------
# AgentTemplates — JSON config loader + instance settings builder
# ---------------------------------------------------------------------------

class AgentTemplates:
    """Loads demo configs from configs/*.json.

    Instance usage (called by VoiceAgent):
        templates = AgentTemplates(industry, voiceModel, voiceName, language)
        templates.settings          -> dict to send as WS Settings message
        templates.voice_agent_url   -> str
        templates.user_audio_sample_rate / user_audio_samples_per_chunk

    Static CRUD usage (called by Flask routes):
        AgentTemplates.load_all()       -> list[dict]
        AgentTemplates.load(id)         -> dict | None
        AgentTemplates.save(config)     -> dict
        AgentTemplates.delete(id)       -> bool
    """

    def __init__(
        self,
        industry="deepgram",
        voiceModel="aura-2-thalia-en",
        voiceName="",
        language="en",
        docs_dir="deepgram-docs/fern/docs",
    ):
        self.industry = industry
        self.voiceModel = voiceModel
        self.voiceName = voiceName if voiceName else self._voice_name_from_model(voiceModel)
        self.language = language

        self.voice_agent_url = VOICE_AGENT_URL
        self.user_audio_sample_rate = USER_AUDIO_SAMPLE_RATE
        self.user_audio_secs_per_chunk = USER_AUDIO_SECS_PER_CHUNK
        self.user_audio_samples_per_chunk = USER_AUDIO_SAMPLES_PER_CHUNK
        self.agent_audio_sample_rate = AGENT_AUDIO_SAMPLE_RATE
        self.agent_audio_bytes_per_sec = AGENT_AUDIO_BYTES_PER_SEC

        # Try to load config from JSON; fall back to a sensible default
        cfg = AgentTemplates.load(industry)
        if cfg:
            system_prompt = cfg.get("systemPrompt", "")
            greeting = cfg.get("greeting", "Hello, how can I help you today?")
            voice_model = cfg.get("voiceModel", voiceModel)
            config_language = cfg.get("language", language)
            hotword = cfg.get("hotword")
            # Substitute {{agentName}} using the caller-passed voice name/model,
            # not the config default (which would ignore the user's selection)
            agent_name = voiceName if voiceName else AgentTemplates._voice_name_from_model(voiceModel)
            system_prompt = system_prompt.replace("{{agentName}}", agent_name)
            greeting = greeting.replace("{{agentName}}", agent_name)
        else:
            # No JSON config found — build defaults (legacy behavior for unknown ids)
            system_prompt = PROMPT_TEMPLATE.format(
                current_date=datetime.now().strftime("%A, %B %d, %Y")
            )
            greeting = "Hello, how can I help you today?"
            voice_model = voiceModel
            config_language = language
            hotword = None

            # Special case: deepgram industry still uses doc-based prompt
            if industry == "deepgram":
                doc_text = ""
                docs = read_documentation_files(docs_dir)
                if docs:
                    doc_text = "Available documentation topics: " + ", ".join(docs.keys())
                system_prompt = DEEPGRAM_PROMPT_TEMPLATE.format(documentation=doc_text)

        # Override voice model and language if explicitly passed by caller
        if voiceModel != "aura-2-thalia-en":
            voice_model = voiceModel
        if language != "en":
            config_language = language

        # Hotword mode: register the hotword and extend system prompt + functions
        set_hotword(hotword)
        if hotword:
            system_prompt += (
                f"\n\nHOTWORD ACTIVATION (CRITICAL RULE):\n"
                f"You are in hotword mode. The activation hotword is \"{hotword}\".\n"
                f"You MUST call check_hotword with the exact transcript before responding to ANYTHING the user says.\n"
                f"- If check_hotword returns {{\"active\": false}}: Do not speak. Stay completely silent.\n"
                f"- If check_hotword returns {{\"active\": true}}: Respond naturally to the \"query\" field.\n"
                f"This rule applies to every single utterance, no exceptions.\n\n"
                f"ENDING A HOTWORD CONVERSATION:\n"
                f"When the user's request is fully resolved and they signal they are done "
                f"(e.g. 'thanks', 'got it', 'okay', 'perfect', 'that's all', 'great'), "
                f"call close_hotword_session, then give a brief closing remark and go silent. "
                f"Do not keep the conversation going after the task is complete."
            )
            functions = FUNCTION_DEFINITIONS + [CHECK_HOTWORD_DEFINITION, CLOSE_HOTWORD_SESSION_DEFINITION]
        else:
            functions = FUNCTION_DEFINITIONS

        self.settings = {
            "type": "Settings",
            "audio": AUDIO_SETTINGS,
            "agent": {
                "language": config_language,
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": "nova-3",
                    }
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": "gpt-4o-mini",
                        "temperature": 0.7,
                    },
                    "prompt": system_prompt,
                    "functions": functions,
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": voice_model,
                    }
                },
                "greeting": greeting,
            },
        }

    # ------------------------------------------------------------------
    # Static CRUD methods
    # ------------------------------------------------------------------

    @staticmethod
    def load_all() -> list:
        """Return all config dicts from configs/*.json.
        Configs with 'default: true' sort first; otherwise alphabetical by id.
        Configs with 'disabled: true' are excluded.
        """
        configs = []
        for f in sorted(CONFIGS_DIR.glob("*.json")):
            with open(f) as fh:
                cfg = json.load(fh)
            if not cfg.get("disabled"):
                configs.append(cfg)
        configs.sort(key=lambda c: (0 if c.get("default") else 1, c.get("id", "")))
        return configs

    @staticmethod
    def load(config_id: str):
        """Load a single config by id (matches filename stem)."""
        path = CONFIGS_DIR / f"{config_id}.json"
        if not path.exists():
            return None
        with open(path) as fh:
            return json.load(fh)

    @staticmethod
    def save(config: dict) -> dict:
        """Write a config dict to configs/<id>.json."""
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

    # ------------------------------------------------------------------
    # Backward-compat helpers (used by VoiceAgent or external callers)
    # ------------------------------------------------------------------

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
    def get_functions(config_id: str) -> list:
        cfg = AgentTemplates.load(config_id)
        if cfg:
            return cfg.get("functions", [])
        return []

    @staticmethod
    def get_available_industries():
        """Return a dict of available configs as id -> name.

        Merges any JSON configs with the legacy hardcoded list so the
        /industries route keeps working during the Phase 2 transition.
        """
        # Start with JSON-loaded configs
        result = {}
        for cfg in AgentTemplates.load_all():
            result[cfg["id"]] = cfg.get("name", cfg["id"])

        # Fall back to legacy hardcoded list if no JSON configs exist yet
        if not result:
            result = {
                "deepgram": "Deepgram",
                "healthcare": "Healthcare",
                "banking": "Banking",
                "pharmaceuticals": "Pharmaceuticals",
                "retail": "Retail",
                "travel": "Travel",
            }
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _voice_name_from_model(model: str) -> str:
        return (
            model.replace("aura-2-", "").replace("aura-", "").split("-")[0].capitalize()
        )

    # Keep old name as alias
    def get_voice_name_from_model(self, model: str) -> str:
        return self._voice_name_from_model(model)
