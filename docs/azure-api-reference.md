# Azure API Reference

## API Modes

The integration supports two Azure Speech APIs. Users can select which APIs to enable in **Settings > Devices & Services > Azure Speech-to-Text > Configure**.

| API | Locales | phraseList | Max audio |
|-----|---------|------------|-----------|
| **Fast Transcription API** (v2025-10-15) | Most locales | Supported | 2 hours / 300 MB |
| **Real-time API** | Select locales | Not supported | Short audio |

**Default behavior** (both APIs enabled): Fast Transcription API is preferred. Locales not supported by Fast Transcription API (e.g., `zh-TW`, `el-GR`, `fr-CA`, and others) are automatically routed to the Real-time API. See `REALTIME_ONLY_LOCALES` in `const.py` for the full list.

**Single API mode**: When only one API is enabled, only that API is used. If a locale is not supported by the enabled API (e.g., enabling only Fast Transcription API with a Real-time-only locale), transcription is skipped with a warning.

## Supported Audio Formats

| Parameter | Values |
|-----------|--------|
| Formats | WAV, OGG |
| Codecs | PCM, OPUS |
| Sample Rate | 16 kHz |
| Bit Depth | 16-bit |
| Channels | Mono |

## Supported Regions

| Region Code | Region Name |
|-------------|-------------|
| `eastasia` | East Asia |
| `southeastasia` | Southeast Asia |
| `eastus` | East US |
| `eastus2` | East US 2 |
| `westus` | West US |
| `westus2` | West US 2 |
| `centralus` | Central US |
| `northeurope` | North Europe |
| `westeurope` | West Europe |
| `japaneast` | Japan East |
| `japanwest` | Japan West |
| `koreacentral` | Korea Central |
| `australiaeast` | Australia East |
| `canadacentral` | Canada Central |
| `uksouth` | UK South |

## Supported Languages

| Locale | Language | API |
|--------|----------|-----|
| `af-ZA` | Afrikaans (South Africa) | Fast Transcription |
| `am-ET` | Amharic (Ethiopia) | Fast Transcription |
| `ar-AE` | Arabic (UAE) | Fast Transcription |
| `ar-BH` | Arabic (Bahrain) | Fast Transcription |
| `ar-DZ` | Arabic (Algeria) | Real-time |
| `ar-EG` | Arabic (Egypt) | Fast Transcription |
| `ar-IL` | Arabic (Israel) | Fast Transcription |
| `ar-IQ` | Arabic (Iraq) | Fast Transcription |
| `ar-JO` | Arabic (Jordan) | Fast Transcription |
| `ar-KW` | Arabic (Kuwait) | Fast Transcription |
| `ar-LB` | Arabic (Lebanon) | Fast Transcription |
| `ar-LY` | Arabic (Libya) | Fast Transcription |
| `ar-MA` | Arabic (Morocco) | Real-time |
| `ar-OM` | Arabic (Oman) | Fast Transcription |
| `ar-PS` | Arabic (Palestine) | Fast Transcription |
| `ar-QA` | Arabic (Qatar) | Fast Transcription |
| `ar-SA` | Arabic (Saudi Arabia) | Fast Transcription |
| `ar-SY` | Arabic (Syria) | Fast Transcription |
| `ar-TN` | Arabic (Tunisia) | Real-time |
| `ar-YE` | Arabic (Yemen) | Real-time |
| `as-IN` | Assamese (India) | Real-time |
| `az-AZ` | Azerbaijani (Azerbaijan) | Fast Transcription |
| `bg-BG` | Bulgarian (Bulgaria) | Fast Transcription |
| `bn-IN` | Bengali (India) | Fast Transcription |
| `bs-BA` | Bosnian (Bosnia and Herzegovina) | Real-time |
| `ca-ES` | Catalan (Spain) | Fast Transcription |
| `cs-CZ` | Czech (Czechia) | Fast Transcription |
| `cy-GB` | Welsh (United Kingdom) | Fast Transcription |
| `da-DK` | Danish (Denmark) | Fast Transcription |
| `de-AT` | German (Austria) | Fast Transcription |
| `de-CH` | German (Switzerland) | Fast Transcription |
| `de-DE` | German (Germany) | Fast Transcription |
| `el-GR` | Greek (Greece) | Real-time |
| `en-AU` | English (Australia) | Fast Transcription |
| `en-CA` | English (Canada) | Fast Transcription |
| `en-GB` | English (United Kingdom) | Fast Transcription |
| `en-GH` | English (Ghana) | Fast Transcription |
| `en-HK` | English (Hong Kong) | Fast Transcription |
| `en-IE` | English (Ireland) | Fast Transcription |
| `en-IN` | English (India) | Fast Transcription |
| `en-KE` | English (Kenya) | Fast Transcription |
| `en-NG` | English (Nigeria) | Fast Transcription |
| `en-NZ` | English (New Zealand) | Fast Transcription |
| `en-PH` | English (Philippines) | Fast Transcription |
| `en-SG` | English (Singapore) | Fast Transcription |
| `en-TZ` | English (Tanzania) | Fast Transcription |
| `en-US` | English (United States) | Fast Transcription |
| `en-ZA` | English (South Africa) | Fast Transcription |
| `es-AR` | Spanish (Argentina) | Fast Transcription |
| `es-BO` | Spanish (Bolivia) | Fast Transcription |
| `es-CL` | Spanish (Chile) | Fast Transcription |
| `es-CO` | Spanish (Colombia) | Fast Transcription |
| `es-CR` | Spanish (Costa Rica) | Fast Transcription |
| `es-CU` | Spanish (Cuba) | Fast Transcription |
| `es-DO` | Spanish (Dominican Republic) | Fast Transcription |
| `es-EC` | Spanish (Ecuador) | Fast Transcription |
| `es-ES` | Spanish (Spain) | Fast Transcription |
| `es-GQ` | Spanish (Equatorial Guinea) | Fast Transcription |
| `es-GT` | Spanish (Guatemala) | Fast Transcription |
| `es-HN` | Spanish (Honduras) | Fast Transcription |
| `es-MX` | Spanish (Mexico) | Fast Transcription |
| `es-NI` | Spanish (Nicaragua) | Fast Transcription |
| `es-PA` | Spanish (Panama) | Fast Transcription |
| `es-PE` | Spanish (Peru) | Fast Transcription |
| `es-PR` | Spanish (Puerto Rico) | Fast Transcription |
| `es-PY` | Spanish (Paraguay) | Fast Transcription |
| `es-SV` | Spanish (El Salvador) | Fast Transcription |
| `es-US` | Spanish (United States) | Fast Transcription |
| `es-UY` | Spanish (Uruguay) | Fast Transcription |
| `es-VE` | Spanish (Venezuela) | Fast Transcription |
| `et-EE` | Estonian (Estonia) | Fast Transcription |
| `eu-ES` | Basque (Spain) | Fast Transcription |
| `fa-IR` | Persian (Iran) | Fast Transcription |
| `fi-FI` | Finnish (Finland) | Fast Transcription |
| `fil-PH` | Filipino (Philippines) | Fast Transcription |
| `fr-BE` | French (Belgium) | Real-time |
| `fr-CA` | French (Canada) | Real-time |
| `fr-CH` | French (Switzerland) | Real-time |
| `fr-FR` | French (France) | Fast Transcription |
| `ga-IE` | Irish (Ireland) | Fast Transcription |
| `gl-ES` | Galician (Spain) | Fast Transcription |
| `gu-IN` | Gujarati (India) | Real-time |
| `he-IL` | Hebrew (Israel) | Fast Transcription |
| `hi-IN` | Hindi (India) | Fast Transcription |
| `hr-HR` | Croatian (Croatia) | Fast Transcription |
| `hu-HU` | Hungarian (Hungary) | Fast Transcription |
| `hy-AM` | Armenian (Armenia) | Fast Transcription |
| `id-ID` | Indonesian (Indonesia) | Fast Transcription |
| `is-IS` | Icelandic (Iceland) | Fast Transcription |
| `it-CH` | Italian (Switzerland) | Real-time |
| `it-IT` | Italian (Italy) | Fast Transcription |
| `ja-JP` | Japanese (Japan) | Fast Transcription |
| `jv-ID` | Javanese (Indonesia) | Fast Transcription |
| `ka-GE` | Georgian (Georgia) | Fast Transcription |
| `kk-KZ` | Kazakh (Kazakhstan) | Fast Transcription |
| `km-KH` | Khmer (Cambodia) | Real-time |
| `kn-IN` | Kannada (India) | Real-time |
| `ko-KR` | Korean (Korea) | Fast Transcription |
| `lo-LA` | Lao (Laos) | Fast Transcription |
| `lt-LT` | Lithuanian (Lithuania) | Fast Transcription |
| `lv-LV` | Latvian (Latvia) | Fast Transcription |
| `mk-MK` | Macedonian (North Macedonia) | Fast Transcription |
| `ml-IN` | Malayalam (India) | Fast Transcription |
| `mn-MN` | Mongolian (Mongolia) | Fast Transcription |
| `mr-IN` | Marathi (India) | Fast Transcription |
| `ms-MY` | Malay (Malaysia) | Fast Transcription |
| `mt-MT` | Maltese (Malta) | Fast Transcription |
| `my-MM` | Burmese (Myanmar) | Fast Transcription |
| `nb-NO` | Norwegian Bokmal (Norway) | Fast Transcription |
| `ne-NP` | Nepali (Nepal) | Real-time |
| `nl-BE` | Dutch (Belgium) | Real-time |
| `nl-NL` | Dutch (Netherlands) | Fast Transcription |
| `or-IN` | Odia (India) | Real-time |
| `pa-IN` | Punjabi (India) | Real-time |
| `pl-PL` | Polish (Poland) | Fast Transcription |
| `ps-AF` | Pashto (Afghanistan) | Fast Transcription |
| `pt-BR` | Portuguese (Brazil) | Fast Transcription |
| `pt-PT` | Portuguese (Portugal) | Fast Transcription |
| `ro-RO` | Romanian (Romania) | Fast Transcription |
| `ru-RU` | Russian (Russia) | Fast Transcription |
| `si-LK` | Sinhala (Sri Lanka) | Real-time |
| `sk-SK` | Slovak (Slovakia) | Fast Transcription |
| `sl-SI` | Slovenian (Slovenia) | Fast Transcription |
| `so-SO` | Somali (Somalia) | Fast Transcription |
| `sq-AL` | Albanian (Albania) | Fast Transcription |
| `sr-RS` | Serbian (Serbia) | Fast Transcription |
| `sv-SE` | Swedish (Sweden) | Fast Transcription |
| `sw-KE` | Swahili (Kenya) | Fast Transcription |
| `sw-TZ` | Kiswahili (Tanzania) | Real-time |
| `ta-IN` | Tamil (India) | Fast Transcription |
| `te-IN` | Telugu (India) | Real-time |
| `th-TH` | Thai (Thailand) | Fast Transcription |
| `tr-TR` | Turkish (Turkey) | Fast Transcription |
| `uk-UA` | Ukrainian (Ukraine) | Fast Transcription |
| `ur-IN` | Urdu (India) | Fast Transcription |
| `uz-UZ` | Uzbek (Uzbekistan) | Fast Transcription |
| `vi-VN` | Vietnamese (Vietnam) | Fast Transcription |
| `wuu-CN` | Chinese (Wu, Simplified) | Real-time |
| `yue-CN` | Chinese (Cantonese, Simplified) | Real-time |
| `zh-CN` | Chinese (Simplified, China) | Fast Transcription |
| `zh-CN-shandong` | Chinese (Jilu Mandarin, Simplified) | Real-time |
| `zh-CN-sichuan` | Chinese (Southwestern Mandarin, Simplified) | Real-time |
| `zh-HK` | Chinese (Cantonese, Hong Kong) | Fast Transcription |
| `zh-TW` | Chinese (Traditional, Taiwan) | Real-time |
| `zu-ZA` | Zulu (South Africa) | Fast Transcription |
