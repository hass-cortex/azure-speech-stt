# Azure Speech-to-Text for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/hass-cortex/azure-speech-stt)](https://github.com/hass-cortex/azure-speech-stt/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![HA Version](https://img.shields.io/badge/HA-2026.3.0+-green.svg)](https://www.home-assistant.io/)
[![GitHub License](https://img.shields.io/github/license/hass-cortex/azure-speech-stt)](https://github.com/hass-cortex/azure-speech-stt/blob/main/LICENSE)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-hass--cortex%2Fazure--speech--stt-blue.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAyCAYAAAAnWDnqAAAAAXNSR0IArs4c6QAAA05JREFUaEPtmUtyEzEQhtWTQyQLHNak2AB7ZnyXZMEjXMGeK/AIi+QuHrMnbChYY7MIh8g01fJoopFb0uhhEqqcbWTp06/uv1saEDv4O3n3dV60RfP947Mm9/SQc0ICFQgzfc4CYZoTPAswgSJCCUJUnAAoRHOAUOcATwbmVLWdGoH//PB8mnKqScAhsD0kYP3j/Yt5LPQe2KvcXmGvRHcDnpxfL2zOYJ1mFwrryWTz0advv1Ut4CJgf5uhDuDj5eUcAUoahrdY/56ebRWeraTjMt/00Sh3UDtjgHtQNHwcRGOC98BJEAEymycmYcWwOprTgcB6VZ5JK5TAJ+fXGLBm3FDAmn6oPPjR4rKCAoJCal2eAiQp2x0vxTPB3ALO2CRkwmDy5WohzBDwSEFKRwPbknEggCPB/imwrycgxX2NzoMCHhPkDwqYMr9tRcP5qNrMZHkVnOjRMWwLCcr8ohBVb1OMjxLwGCvjTikrsBOiA6fNyCrm8V1rP93iVPpwaE+gO0SsWmPiXB+jikdf6SizrT5qKasx5j8ABbHpFTx+vFXp9EnYQmLx02h1QTTrl6eDqxLnGjporxl3NL3agEvXdT0WmEost648sQOYAeJS9Q7bfUVoMGnjo4AZdUMQku50McDcMWcBPvr0SzbTAFDfvJqwLzgxwATnCgnp4wDl6Aa+Ax283gghmj+vj7feE2KBBRMW3FzOpLOADl0Isb5587h/U4gGvkt5v60Z1VLG8BhYjbzRwyQZemwAd6cCR5/XFWLYZRIMpX39AR0tjaGGiGzLVyhse5C9RKC6ai42ppWPKiBagOvaYk8lO7DajerabOZP46Lby5wKjw1HCRx7p9sVMOWGzb/vA1hwiWc6jm3MvQDTogQkiqIhJV0nBQBTU+3okKCFDy9WwferkHjtxib7t3xIUQtHxnIwtx4mpg26/HfwVNVDb4oI9RHmx5WGelRVlrtiw43zboCLaxv46AZeB3IlTkwouebTr1y2NjSpHz68WNFjHvupy3q8TFn3Hos2IAk4Ju5dCo8B3wP7VPr/FGaKiG+T+v+TQqIrOqMTL1VdWV1DdmcbO8KXBz6esmYWYKPwDL5b5FA1a0hwapHiom0r/cKaoqr+27/XcrS5UwSMbQAAAABJRU5ErkJggg==)](https://deepwiki.com/hass-cortex/azure-speech-stt)

A Home Assistant custom integration providing cloud-based speech-to-text via [Microsoft Azure Speech Services](https://azure.microsoft.com/en-us/products/ai-services/speech-to-text), with a built-in correction pipeline for improved voice command accuracy.

```
Audio ──► Azure API ──► Raw Text ──► Custom Replacements ──► Similarity Matching ──► Final Text
              ▲                          (Stage 2)              (Stage 3)
              │
         phraseList
          (Stage 1)
```

| Stage | When | What |
|-------|------|------|
| **1. Pre-recognition Hints** | Before API call | Auto-collected + custom phrases sent as `phraseList` to bias Azure recognition |
| **2. Custom Replacements** | After API call | User-defined `wrong=correct` substitution rules |
| **3. Similarity Matching** | After API call | Fuzzy/phonetic matching against known phrases (pinyin for Chinese) |

Each stage can be enabled/disabled independently. See [Correction Pipeline Details](docs/correction-pipeline.md) for full documentation.

## Features

- **Multi-locale support** via Azure Fast Transcription API and Real-time API, with configurable API selection ([details](docs/azure-api-reference.md))
- **Three-stage correction pipeline** -- entity hints, custom replacements, and fuzzy/phonetic similarity matching ([details](docs/correction-pipeline.md))
- **Configurable auto-collect** -- independently toggle collection of exposed entities, devices, areas, and floor names from HA registries
- **Language-aware matching** -- pinyin for Chinese, fuzzy matching for other languages
- **Runtime statistics** -- sensor entities tracking usage, API performance, and free tier consumption ([details](docs/sensors.md))
- **Management services** for runtime configuration ([details](docs/services.md))

## Getting Started

**Prerequisites:** Home Assistant **2026.3.0+** and an Azure account with a [Speech Services resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) ([free tier](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) -- 5 hours/month).

### 1. Install

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hass-cortex&repository=azure-speech-stt&category=integration)

Click the button above, or manually: HACS > three-dot menu > **Custom repositories** > add `https://github.com/hass-cortex/azure-speech-stt` (Integration) > install > restart HA.

<details>
<summary>Manual installation</summary>

Copy `custom_components/azure_speech_stt/` to your HA `config/custom_components/` directory, then restart.
</details>

### 2. Get Azure Credentials

1. Sign in to the [Azure Portal](https://portal.azure.com/)
2. Create a [Speech Services resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) (or use an existing one)
3. Go to **Keys and Endpoint** and copy **Key 1** and **Region**

### 3. Add Integration

[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=azure_speech_stt)

Click the button above, or manually: **Settings > Devices & Services > Add Integration** > search "Azure Speech-to-Text".

Enter your Azure **Speech Key** and **Region**. Optionally set a custom **Display Name** (useful when configuring multiple instances). The integration validates your credentials before completing setup.

### 4. Assign to Voice Pipeline

[![Open your Home Assistant instance and manage your voice assistants.](https://my.home-assistant.io/badges/voice_assistants.svg)](https://my.home-assistant.io/redirect/voice_assistants/)

Select or create a voice pipeline, then set **Speech-to-text** to your Azure Speech-to-Text instance.

### Configuration Options

[![Open your Home Assistant instance and show this integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=azure_speech_stt)

Configure via the integration page > **Configure**:

### Uninstallation

**Settings > Devices & Services** > Azure Speech-to-Text > three-dot menu > **Delete** > remove `custom_components/azure_speech_stt/` > restart HA.

## Debugging

Enable debug logging to see detailed correction pipeline output:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.azure_speech_stt: debug
```

## FAQ

**Why is my transcription inaccurate?**

- Ensure your audio is 16kHz mono 16-bit PCM or OGG/OPUS
- Check that the correct language/locale is selected in your voice pipeline
- Add custom phrases (Stage 1) for domain-specific words like device names
- Add replacement rules (Stage 2) for consistently misrecognized words
- Lower the similarity threshold (Stage 3) if fuzzy matching is not catching errors

**How do I track Azure free tier usage?**

The **Total audio duration** sensor tracks cumulative audio processed in minutes. Azure's free tier includes 5 hours (300 minutes) per month. See [Runtime Statistics](docs/sensors.md) for all available sensors.

**What is pinyin matching?**

For Chinese (CJK) text, the integration converts characters to their romanized pronunciation and compares phonetic similarity, handling cases where Azure recognizes a homophone instead of the intended word.

**Can I use this without the correction pipeline?**

Yes. Disable all three stages independently in the configuration options, or set `apply_correction: false` in the `transcribe` service call for one-off raw output.

**Can I configure multiple Azure instances?**

Yes. Add the integration multiple times with different Azure keys, regions, or display names. Each instance creates its own device with independent sensors and configuration.

**How do I install the latest development version?**

After the integration is installed via HACS, you can switch to the latest `main` branch using the `update.install` action:

1. Go to **Developer Tools > Actions**
2. Select the `update.install` action
3. In **Target**, select the Azure Speech-to-Text update entity (e.g., `update.azure_speech_to_text_update`)
4. In **Version**, enter `main` (or a specific commit hash, e.g., `4f44b6c`)
5. Click **Perform Action**
6. Restart HA

This bypasses the HACS UI version selector and instructs HACS to pull the specified branch or commit directly from GitHub. Development versions may contain breaking changes — to revert, run the same action with a release tag (e.g., `0.2.0`).

## Documentation

| Document | Description |
|----------|-------------|
| [Correction Pipeline](docs/correction-pipeline.md) | Three-stage correction pipeline details |
| [Runtime Statistics](docs/sensors.md) | Sensor entities for usage tracking and monitoring |
| [Services](docs/services.md) | Service definitions with parameters and examples |
| [Azure API Reference](docs/azure-api-reference.md) | API modes, supported regions, and supported languages |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## License

[MIT](LICENSE)
