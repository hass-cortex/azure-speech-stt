"""Constants for Azure Speech-to-Text integration."""

from __future__ import annotations

DOMAIN = "azure_speech_stt"

# Config entry data keys
CONF_SPEECH_KEY = "speech_key"
CONF_SPEECH_REGION = "speech_region"

# Options keys
CONF_ENABLE_ENTITY_HINTS = "enable_entity_hints"
CONF_FUZZY_THRESHOLD = "fuzzy_threshold"
CONF_CUSTOM_PHRASES = "custom_phrases"
CONF_CUSTOM_REPLACEMENTS = "custom_replacements"
CONF_ENABLE_CUSTOM_REPLACEMENTS = "enable_custom_replacements"
CONF_ENABLE_FUZZY_MATCHING = "enable_fuzzy_matching"
CONF_CUSTOM_EXCLUSIONS = "custom_exclusions"
CONF_API_MODES = "api_modes"
CONF_CORRECTION_STAGES = "correction_stages"
CORRECTION_STAGE_HINTS = "hints"
CORRECTION_STAGE_REPLACEMENTS = "replacements"
CORRECTION_STAGE_SIMILARITY = "similarity"
DEFAULT_CORRECTION_STAGES: list[str] = [
    CORRECTION_STAGE_HINTS,
    CORRECTION_STAGE_REPLACEMENTS,
    CORRECTION_STAGE_SIMILARITY,
]
CONF_AUTO_COLLECT_SOURCES = "auto_collect_sources"
CONF_SECTION_AUTO_COLLECT = "auto_collect"
AUTO_COLLECT_FLOORS = "floors"
AUTO_COLLECT_AREAS = "areas"
AUTO_COLLECT_DEVICES = "devices"
AUTO_COLLECT_ENTITIES = "entities"
DEFAULT_AUTO_COLLECT_SOURCES: list[str] = [
    AUTO_COLLECT_FLOORS,
    AUTO_COLLECT_AREAS,
    AUTO_COLLECT_DEVICES,
    AUTO_COLLECT_ENTITIES,
]
CONF_SECTION_STAGE1 = "stage_1"
CONF_SECTION_STAGE2 = "stage_2"
CONF_SECTION_STAGE3 = "stage_3"
# Defaults
DEFAULT_FUZZY_THRESHOLD = 0.80
DEFAULT_ENABLE_ENTITY_HINTS = True
DEFAULT_ENABLE_CUSTOM_REPLACEMENTS = True
DEFAULT_ENABLE_FUZZY_MATCHING = True
API_MODE_FAST = "fast_transcription"
API_MODE_REALTIME = "realtime"
DEFAULT_API_MODES: list[str] = [API_MODE_FAST, API_MODE_REALTIME]

# Azure regions
AZURE_REGIONS: list[dict[str, str]] = [
    {"value": "eastasia", "label": "East Asia"},
    {"value": "southeastasia", "label": "Southeast Asia"},
    {"value": "eastus", "label": "East US"},
    {"value": "eastus2", "label": "East US 2"},
    {"value": "westus", "label": "West US"},
    {"value": "westus2", "label": "West US 2"},
    {"value": "centralus", "label": "Central US"},
    {"value": "northeurope", "label": "North Europe"},
    {"value": "westeurope", "label": "West Europe"},
    {"value": "japaneast", "label": "Japan East"},
    {"value": "japanwest", "label": "Japan West"},
    {"value": "koreacentral", "label": "Korea Central"},
    {"value": "australiaeast", "label": "Australia East"},
    {"value": "canadacentral", "label": "Canada Central"},
    {"value": "uksouth", "label": "UK South"},
]

# All supported locales (Fast Transcription + Real-time API).
# Locales in REALTIME_ONLY_LOCALES are routed to the Real-time REST API.
# Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt
SUPPORTED_LOCALES: dict[str, str] = {
    "af-ZA": "Afrikaans (South Africa)",
    "am-ET": "Amharic (Ethiopia)",
    "ar-AE": "Arabic (UAE)",
    "ar-BH": "Arabic (Bahrain)",
    "ar-DZ": "Arabic (Algeria)",
    "ar-EG": "Arabic (Egypt)",
    "ar-IL": "Arabic (Israel)",
    "ar-IQ": "Arabic (Iraq)",
    "ar-JO": "Arabic (Jordan)",
    "ar-KW": "Arabic (Kuwait)",
    "ar-LB": "Arabic (Lebanon)",
    "ar-LY": "Arabic (Libya)",
    "ar-MA": "Arabic (Morocco)",
    "ar-OM": "Arabic (Oman)",
    "ar-PS": "Arabic (Palestine)",
    "ar-QA": "Arabic (Qatar)",
    "ar-SA": "Arabic (Saudi Arabia)",
    "ar-SY": "Arabic (Syria)",
    "ar-TN": "Arabic (Tunisia)",
    "ar-YE": "Arabic (Yemen)",
    "as-IN": "Assamese (India)",
    "az-AZ": "Azerbaijani (Azerbaijan)",
    "bg-BG": "Bulgarian (Bulgaria)",
    "bn-IN": "Bengali (India)",
    "bs-BA": "Bosnian (Bosnia and Herzegovina)",
    "ca-ES": "Catalan (Spain)",
    "cs-CZ": "Czech (Czechia)",
    "cy-GB": "Welsh (United Kingdom)",
    "da-DK": "Danish (Denmark)",
    "de-AT": "German (Austria)",
    "de-CH": "German (Switzerland)",
    "de-DE": "German (Germany)",
    "en-AU": "English (Australia)",
    "en-CA": "English (Canada)",
    "en-GB": "English (United Kingdom)",
    "en-GH": "English (Ghana)",
    "en-HK": "English (Hong Kong)",
    "en-IE": "English (Ireland)",
    "en-IN": "English (India)",
    "en-KE": "English (Kenya)",
    "en-NG": "English (Nigeria)",
    "en-NZ": "English (New Zealand)",
    "en-PH": "English (Philippines)",
    "en-SG": "English (Singapore)",
    "en-TZ": "English (Tanzania)",
    "en-US": "English (United States)",
    "en-ZA": "English (South Africa)",
    "es-AR": "Spanish (Argentina)",
    "es-BO": "Spanish (Bolivia)",
    "es-CL": "Spanish (Chile)",
    "es-CO": "Spanish (Colombia)",
    "es-CR": "Spanish (Costa Rica)",
    "es-CU": "Spanish (Cuba)",
    "es-DO": "Spanish (Dominican Republic)",
    "es-EC": "Spanish (Ecuador)",
    "es-ES": "Spanish (Spain)",
    "es-GQ": "Spanish (Equatorial Guinea)",
    "es-GT": "Spanish (Guatemala)",
    "es-HN": "Spanish (Honduras)",
    "es-MX": "Spanish (Mexico)",
    "es-NI": "Spanish (Nicaragua)",
    "es-PA": "Spanish (Panama)",
    "es-PE": "Spanish (Peru)",
    "es-PR": "Spanish (Puerto Rico)",
    "es-PY": "Spanish (Paraguay)",
    "es-SV": "Spanish (El Salvador)",
    "es-US": "Spanish (United States)",
    "es-UY": "Spanish (Uruguay)",
    "es-VE": "Spanish (Venezuela)",
    "el-GR": "Greek (Greece)",
    "et-EE": "Estonian (Estonia)",
    "eu-ES": "Basque (Spain)",
    "fa-IR": "Persian (Iran)",
    "fi-FI": "Finnish (Finland)",
    "fil-PH": "Filipino (Philippines)",
    "fr-BE": "French (Belgium)",
    "fr-CA": "French (Canada)",
    "fr-CH": "French (Switzerland)",
    "fr-FR": "French (France)",
    "ga-IE": "Irish (Ireland)",
    "gl-ES": "Galician (Spain)",
    "gu-IN": "Gujarati (India)",
    "he-IL": "Hebrew (Israel)",
    "hi-IN": "Hindi (India)",
    "hr-HR": "Croatian (Croatia)",
    "hu-HU": "Hungarian (Hungary)",
    "hy-AM": "Armenian (Armenia)",
    "id-ID": "Indonesian (Indonesia)",
    "is-IS": "Icelandic (Iceland)",
    "it-CH": "Italian (Switzerland)",
    "it-IT": "Italian (Italy)",
    "ja-JP": "Japanese (Japan)",
    "jv-ID": "Javanese (Indonesia)",
    "ka-GE": "Georgian (Georgia)",
    "kk-KZ": "Kazakh (Kazakhstan)",
    "km-KH": "Khmer (Cambodia)",
    "kn-IN": "Kannada (India)",
    "ko-KR": "Korean (Korea)",
    "lo-LA": "Lao (Laos)",
    "lt-LT": "Lithuanian (Lithuania)",
    "lv-LV": "Latvian (Latvia)",
    "mk-MK": "Macedonian (North Macedonia)",
    "ml-IN": "Malayalam (India)",
    "mn-MN": "Mongolian (Mongolia)",
    "mr-IN": "Marathi (India)",
    "ms-MY": "Malay (Malaysia)",
    "mt-MT": "Maltese (Malta)",
    "my-MM": "Burmese (Myanmar)",
    "nb-NO": "Norwegian Bokmål (Norway)",
    "ne-NP": "Nepali (Nepal)",
    "nl-BE": "Dutch (Belgium)",
    "nl-NL": "Dutch (Netherlands)",
    "or-IN": "Odia (India)",
    "pa-IN": "Punjabi (India)",
    "pl-PL": "Polish (Poland)",
    "ps-AF": "Pashto (Afghanistan)",
    "pt-BR": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "ro-RO": "Romanian (Romania)",
    "ru-RU": "Russian (Russia)",
    "si-LK": "Sinhala (Sri Lanka)",
    "sk-SK": "Slovak (Slovakia)",
    "sl-SI": "Slovenian (Slovenia)",
    "so-SO": "Somali (Somalia)",
    "sq-AL": "Albanian (Albania)",
    "sr-RS": "Serbian (Serbia)",
    "sv-SE": "Swedish (Sweden)",
    "sw-KE": "Swahili (Kenya)",
    "sw-TZ": "Kiswahili (Tanzania)",
    "ta-IN": "Tamil (India)",
    "te-IN": "Telugu (India)",
    "th-TH": "Thai (Thailand)",
    "tr-TR": "Turkish (Turkey)",
    "uk-UA": "Ukrainian (Ukraine)",
    "ur-IN": "Urdu (India)",
    "uz-UZ": "Uzbek (Uzbekistan)",
    "vi-VN": "Vietnamese (Vietnam)",
    "wuu-CN": "Chinese (Wu, Simplified)",
    "yue-CN": "Chinese (Cantonese, Simplified)",
    "zh-CN": "Chinese (Simplified, China)",
    "zh-CN-shandong": "Chinese (Jilu Mandarin, Simplified)",
    "zh-CN-sichuan": "Chinese (Southwestern Mandarin, Simplified)",
    "zh-HK": "Chinese (Cantonese, Hong Kong)",
    "zh-TW": "Chinese (Traditional, Taiwan)",
    "zu-ZA": "Zulu (South Africa)",
}

# Locales that must use the Real-time REST API instead of Fast Transcription.
# These locales support real-time speech-to-text but are NOT supported by
# the Fast Transcription API.
# Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt
REALTIME_ONLY_LOCALES: set[str] = {
    "ar-DZ",  # Arabic (Algeria)
    "ar-MA",  # Arabic (Morocco)
    "ar-TN",  # Arabic (Tunisia)
    "ar-YE",  # Arabic (Yemen)
    "as-IN",  # Assamese (India)
    "bs-BA",  # Bosnian (Bosnia and Herzegovina)
    "el-GR",  # Greek (Greece)
    "fr-BE",  # French (Belgium)
    "fr-CA",  # French (Canada)
    "fr-CH",  # French (Switzerland)
    "gu-IN",  # Gujarati (India)
    "it-CH",  # Italian (Switzerland)
    "km-KH",  # Khmer (Cambodia)
    "kn-IN",  # Kannada (India)
    "ne-NP",  # Nepali (Nepal)
    "nl-BE",  # Dutch (Belgium)
    "or-IN",  # Odia (India)
    "pa-IN",  # Punjabi (India)
    "si-LK",  # Sinhala (Sri Lanka)
    "sw-TZ",  # Kiswahili (Tanzania)
    "te-IN",  # Telugu (India)
    "wuu-CN",  # Chinese (Wu, Simplified)
    "yue-CN",  # Chinese (Cantonese, Simplified)
    "zh-CN-shandong",  # Chinese (Jilu Mandarin, Simplified)
    "zh-CN-sichuan",  # Chinese (Southwestern Mandarin, Simplified)
    "zh-TW",  # Chinese (Taiwanese Mandarin, Traditional)
}

# Token endpoint template
TOKEN_ENDPOINT = "https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"

# Fast Transcription REST API endpoint (supports phraseList, most locales)
FAST_TRANSCRIPTION_ENDPOINT = (
    "https://{region}.api.cognitive.microsoft.com"
    "/speechtotext/transcriptions:transcribe?api-version=2025-10-15"
)

# Real-time REST API for short audio (supports zh-TW, streaming, no phraseList)
REALTIME_STT_ENDPOINT = (
    "https://{region}.stt.speech.microsoft.com"
    "/speech/recognition/conversation/cognitiveservices/v1"
    "?language={language}&format=detailed"
)
