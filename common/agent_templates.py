from common.agent_functions import FUNCTION_DEFINITIONS
from common.prompt_templates import DEEPGRAM_PROMPT_TEMPLATE, PROMPT_TEMPLATE
from datetime import datetime
import os
import glob


# Function to read documentation files from the deepgram-docs/fern/docs directory
def read_documentation_files(docs_dir):
    """Read all .mdx files in the specified directory and return their contents as a dictionary."""
    documentation = {}
    if not os.path.exists(docs_dir):
        return documentation

    # Get all .mdx files in the directory
    mdx_files = glob.glob(os.path.join(docs_dir, "*.mdx"))

    for file_path in mdx_files:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Use the filename without extension as the key
                key = os.path.basename(file_path).replace(".mdx", "")
                documentation[key] = content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return documentation


VOICE = "aura-2-thalia-en"

# audio settings
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

LISTEN_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": "nova-3",
    }
}

THINK_SETTINGS = {
    "provider": {
        "type": "open_ai",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
    },
    "prompt": PROMPT_TEMPLATE.format(
        current_date=datetime.now().strftime("%A, %B %d, %Y")
    ),
    "functions": FUNCTION_DEFINITIONS,
}

SPEAK_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": VOICE,
    }
}

AGENT_SETTINGS = {
    "language": "en",
    "listen": LISTEN_SETTINGS,
    "think": THINK_SETTINGS,
    "speak": SPEAK_SETTINGS,
    "greeting": "",
}

SETTINGS = {"type": "Settings", "audio": AUDIO_SETTINGS, "agent": AGENT_SETTINGS}

# Translated welcome message templates: {voiceName}, {company}, {capabilities}
# Languages supported: en (American, British, Australian, Irish, Filipino), es (Mexican, Peninsular, Colombian, Latin American), de, fr, nl, it, ja
WELCOME_MESSAGES = {
    "en": "Hello! I'm {voiceName} from {company} customer service. {capabilities} How can I help you today?",
    "es": "¡Hola! Soy {voiceName} del servicio al cliente de {company}. {capabilities} ¿Cómo puedo ayudarte hoy?",
    "de": "Hallo! Ich bin {voiceName} vom Kundenservice von {company}. {capabilities} Wie kann ich Ihnen heute helfen?",
    "fr": "Bonjour ! Je suis {voiceName} du service client de {company}. {capabilities} Comment puis-je vous aider aujourd'hui ?",
    "nl": "Hallo! Ik ben {voiceName} van de klantenservice van {company}. {capabilities} Hoe kan ik u vandaag helpen?",
    "it": "Ciao! Sono {voiceName} del servizio clienti di {company}. {capabilities} Come posso aiutarti oggi?",
    "ja": "こんにちは！{company}のカスタマーサービス担当の{voiceName}です。{capabilities}本日はどのようなご用件でしょうか？",
}

# Single capabilities template per language: "I can help you answer questions about {topic}."
CAPABILITY_TEMPLATES = {
    "en": "I can help you answer questions about {topic}.",
    "es": "Puedo ayudarte a responder preguntas sobre {topic}.",
    "de": "Ich kann Ihnen bei Fragen zu {topic} helfen.",
    "fr": "Je peux vous aider à répondre à vos questions sur {topic}.",
    "nl": "Ik kan u helpen met vragen over {topic}.",
    "it": "Posso aiutarti a rispondere a domande su {topic}.",
    "ja": "{topic}に関するご質問にお答えします。",
}

# Topic name per industry per language (plugged into CAPABILITY_TEMPLATES)
CAPABILITY_TOPICS = {
    "deepgram": {
        "en": "Deepgram",
        "es": "Deepgram",
        "de": "Deepgram",
        "fr": "Deepgram",
        "nl": "Deepgram",
        "it": "Deepgram",
        "ja": "Deepgram",
    },
    "healthcare": {
        "en": "healthcare",
        "es": "atención médica",
        "de": "Gesundheitsversorgung",
        "fr": "soins de santé",
        "nl": "gezondheidszorg",
        "it": "assistenza sanitaria",
        "ja": "ヘルスケア",
    },
    "banking": {
        "en": "banking",
        "es": "banca",
        "de": "Bankwesen",
        "fr": "banque",
        "nl": "bankzaken",
        "it": "banking",
        "ja": "銀行業務",
    },
    "pharmaceuticals": {
        "en": "pharmaceuticals",
        "es": "productos farmacéuticos",
        "de": "Arzneimittel",
        "fr": "produits pharmaceutiques",
        "nl": "farmaceutische producten",
        "it": "prodotti farmaceutici",
        "ja": "医薬品",
    },
    "retail": {
        "en": "retail",
        "es": "retail",
        "de": "Einzelhandel",
        "fr": "vente au détail",
        "nl": "retail",
        "it": "vendita al dettaglio",
        "ja": "小売",
    },
    "travel": {
        "en": "travel",
        "es": "viajes",
        "de": "Reisen",
        "fr": "voyages",
        "nl": "reizen",
        "it": "viaggi",
        "ja": "旅行",
    },
}


class AgentTemplates:
    def __init__(
        self,
        industry="deepgram",
        voiceModel="aura-2-thalia-en",
        voiceName="",
        language="en",
        docs_dir="deepgram-docs/fern/docs",
    ):
        self.voiceModel = voiceModel
        if voiceName == "":
            self.voiceName = self.get_voice_name_from_model(self.voiceModel)
        else:
            self.voiceName = voiceName
        self.language = language

        self.personality = ""
        self.company = ""
        self.first_message = ""
        self.capabilities = ""

        self.industry = industry

        self.voice_agent_url = VOICE_AGENT_URL
        self.settings = SETTINGS
        self.user_audio_sample_rate = USER_AUDIO_SAMPLE_RATE
        self.user_audio_secs_per_chunk = USER_AUDIO_SECS_PER_CHUNK
        self.user_audio_samples_per_chunk = USER_AUDIO_SAMPLES_PER_CHUNK
        self.agent_audio_sample_rate = AGENT_AUDIO_SAMPLE_RATE
        self.agent_audio_bytes_per_sec = AGENT_AUDIO_BYTES_PER_SEC

        match self.industry:
            case "deepgram":
                self.deepgram()

                # Format documentation for the prompt
                doc_text = ""
                # Read documentation files
                self.documentation = read_documentation_files(docs_dir)

                if self.documentation:
                    doc_text = "Available documentation topics: " + ", ".join(
                        self.documentation.keys()
                    )

                self.prompt = DEEPGRAM_PROMPT_TEMPLATE.format(documentation=doc_text)
            case "healthcare":
                self.healthcare()
            case "banking":
                self.banking()
            case "pharmaceuticals":
                self.pharmaceuticals()
            case "retail":
                self.retail()
            case "travel":
                self.travel()

        if self.industry != "deepgram":
            # deepgram has its own specific prompt based on the product documentation
            self.prompt = PROMPT_TEMPLATE.format(
                current_date=datetime.now().strftime("%A, %B %d, %Y")
            )

        # Use base language code (e.g. en from en-US) for welcome message and capabilities lookup
        lang_base = (self.language or "en").split("-")[0].lower()
        cap_template = CAPABILITY_TEMPLATES.get(lang_base) or CAPABILITY_TEMPLATES["en"]
        topic = (
            (CAPABILITY_TOPICS.get(self.industry) or {}).get(lang_base)
            or (CAPABILITY_TOPICS.get(self.industry) or {}).get("en")
            or self.industry
        )
        self.capabilities = cap_template.format(topic=topic)

        welcome_template = WELCOME_MESSAGES.get(lang_base, WELCOME_MESSAGES["en"])
        self.first_message = welcome_template.format(
            voiceName=self.voiceName,
            company=self.company,
            capabilities=self.capabilities,
        )

        self.settings["agent"]["speak"]["provider"]["model"] = self.voiceModel
        self.settings["agent"]["language"] = self.language
        self.settings["agent"]["think"]["prompt"] = self.prompt
        self.settings["agent"]["greeting"] = self.first_message

        self.prompt = self.personality + "\n\n" + self.prompt

    def deepgram(self, company="Deepgram"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and professional customer service representative for {self.company}, a Voice API company who provides STT and TTS capabilities via API. Your role is to assist potential customers with general inquiries about Deepgram."

    def healthcare(self, company="HealthFirst"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a compassionate and knowledgeable healthcare assistant for {self.company}, a leading healthcare provider. Your role is to assist patients with general information about their appointments and orders."

    def banking(self, company="SecureBank"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a professional and trustworthy banking representative for {self.company}, a secure financial institution. Your role is to assist customers with general information about their accounts and transactions."

    def pharmaceuticals(self, company="MedLine"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a professional and trustworthy pharmaceutical representative for {self.company}, a secure pharmaceutical company. Your role is to assist customers with general information about their prescriptions and orders."

    def retail(self, company="StyleMart"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and attentive retail associate for {self.company}, a trendy clothing and accessories store. Your role is to assist customers with general information about their orders and transactions."

    def travel(self, company="TravelTech"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and professional customer service representative for {self.company}, a tech-forward travel agency. Your role is to assist customers with general information about their travel plans and orders."

    @staticmethod
    def get_available_industries():
        """Return a dictionary of available industries with display names"""
        return {
            "deepgram": "Deepgram",
            "healthcare": "Healthcare",
            "banking": "Banking",
            "pharmaceuticals": "Pharmaceuticals",
            "retail": "Retail",
            "travel": "Travel",
        }

    def get_voice_name_from_model(self, model):
        return (
            model.replace("aura-2-", "").replace("aura-", "").split("-")[0].capitalize()
        )
