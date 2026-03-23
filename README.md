# Azure Speech-to-Text for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/hass-cortex/azure-speech-stt)](https://github.com/hass-cortex/azure-speech-stt/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![HA Version](https://img.shields.io/badge/HA-2026.3.0+-green.svg)](https://www.home-assistant.io/)
[![GitHub License](https://img.shields.io/github/license/hass-cortex/azure-speech-stt)](https://github.com/hass-cortex/azure-speech-stt/blob/main/LICENSE)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/hass-cortex/azure-speech-stt)

A Home Assistant custom integration providing cloud-based speech-to-text via [Microsoft Azure Speech Services](https://azure.microsoft.com/en-us/products/ai-services/speech-to-text), with pre-recognition phrase hints for improved voice command accuracy.

```
Audio ──► Azure API ──► Transcribed Text
              ▲
              │
         phraseList
       (entity/area hints)
```

Auto-collected entity, device, area, and floor names are sent as `phraseList` hints to bias Azure recognition toward home automation terminology.

> **Looking for post-recognition correction?** See the [STT Corrector](https://github.com/hass-cortex/stt-corrector) integration, which wraps any STT entity with phonetic/fuzzy correction.

## Features

- **Multi-locale support** via Azure Fast Transcription API and Real-time API, with configurable API selection ([details](docs/azure-api-reference.md))
- **Pre-recognition phrase hints** -- auto-collected entity, device, area, and floor names sent as Azure `phraseList`
- **Configurable auto-collect** -- independently toggle collection of exposed entities, devices, areas, and floor names from HA registries
- **Runtime statistics** -- sensor entities tracking usage, API performance, and free tier consumption ([details](docs/sensors.md))
- **Transcription service** for programmatic use ([details](docs/services.md))

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

- **API Modes** -- enable/disable Fast Transcription and Real-time APIs
- **Enable phrase hints** -- toggle pre-recognition hints sent to Azure
- **Auto-collect sources** -- choose which HA registries to collect names from (floors, areas, devices, exposed entities)
- **Custom phrases** -- additional phrases to include in the hint list

### Uninstallation

**Settings > Devices & Services** > Azure Speech-to-Text > three-dot menu > **Delete** > remove `custom_components/azure_speech_stt/` > restart HA.

## Debugging

Enable debug logging to see phrase list and API details:

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
- Add custom phrases for domain-specific words like device names
- Consider using the [STT Corrector](https://github.com/hass-cortex/stt-corrector) integration for post-recognition correction

**How do I track Azure free tier usage?**

The **Total audio duration** sensor tracks cumulative audio processed in minutes. Azure's free tier includes 5 hours (300 minutes) per month. See [Runtime Statistics](docs/sensors.md) for all available sensors.

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
| [Sensors](docs/sensors.md) | Sensor entities for usage tracking and monitoring |
| [Services](docs/services.md) | Transcribe service with parameters and examples |
| [Azure API Reference](docs/azure-api-reference.md) | API modes, supported regions, and supported languages |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## License

[MIT](LICENSE)
