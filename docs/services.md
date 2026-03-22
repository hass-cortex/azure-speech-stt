# Services

All services are persistent — changes are saved to the config entry and take effect immediately without restart.

## Transcription

### `azure_speech_stt.transcribe`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.transcribe)

Direct transcription service for programmatic use (returns response data).

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `audio_data` | Yes | -- | Base64-encoded WAV audio (PCM 16kHz mono 16-bit) |
| `format` | No | `wav` | Audio format (`wav` or `ogg`) |
| `codec` | No | `pcm` | Audio codec (`pcm` or `opus`) |
| `language` | No | `zh-TW` | BCP-47 language code |
| `apply_correction` | No | `true` | Apply post-recognition correction pipeline |

Response:
```yaml
text: "corrected transcription"
raw_text: "original Azure output"
corrections:
  - from: "original Azure output"
    to: "corrected transcription"
```

## Configuration Management

### `azure_speech_stt.add_phrases`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.add_phrases)

Add phrases to the recognition hints list (deduplicated).

```yaml
service: azure_speech_stt.add_phrases
data:
  phrases:
    - "Living Room Light"
    - "Kitchen Fan"
    - "Hallway Lamp"
```

### `azure_speech_stt.remove_phrases`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.remove_phrases)

Remove phrases from the recognition hints list.

```yaml
service: azure_speech_stt.remove_phrases
data:
  phrases:
    - "Living Room Light"
```

### `azure_speech_stt.add_replacements`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.add_replacements)

Add or update custom replacement rules (wrong to correct).

```yaml
service: azure_speech_stt.add_replacements
data:
  replacements:
    "livin room": "living room"
    "kichen light": "kitchen light"
```

### `azure_speech_stt.remove_replacements`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.remove_replacements)

Remove replacement rules by key (the "wrong" text).

```yaml
service: azure_speech_stt.remove_replacements
data:
  keys:
    - "livin room"
```

### `azure_speech_stt.add_exclusions`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.add_exclusions)

Add segments to the correction exclusion list. Excluded segments are never corrected by similarity matching.

```yaml
service: azure_speech_stt.add_exclusions
data:
  exclusions:
    - "pocket"
    - "chicken"
```

### `azure_speech_stt.remove_exclusions`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.remove_exclusions)

Remove segments from the correction exclusion list.

```yaml
service: azure_speech_stt.remove_exclusions
data:
  exclusions:
    - "pocket"
```

### `azure_speech_stt.get_correction_config`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.get_correction_config)

Returns the current correction configuration (response-only service).

```yaml
service: azure_speech_stt.get_correction_config
```

Response:
```yaml
custom_phrases: ["Living Room Light", "Kitchen Fan"]
custom_replacements:
  "livin room": "living room"
enable_custom_replacements: true
enable_fuzzy_matching: true
fuzzy_threshold: 0.8
custom_exclusions: ["pocket"]
```

### `azure_speech_stt.set_correction_config`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.set_correction_config)

Import correction configuration. Accepts the same format as `get_correction_config` output. All fields are optional — only provided fields are updated.

```yaml
service: azure_speech_stt.set_correction_config
data:
  custom_phrases: ["Living Room Light", "Kitchen Fan"]
  custom_replacements:
    "livin room": "living room"
  enable_custom_replacements: true
  enable_fuzzy_matching: true
  fuzzy_threshold: 0.8
```

## Testing & Debugging

### `azure_speech_stt.test_correction`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.test_correction)

Run text through the correction pipeline with diagnostic output. Shows all candidate matches and their scores — useful for tuning `fuzzy_threshold`.

```yaml
service: azure_speech_stt.test_correction
data:
  text: "turn on the livin room lite"
```

Response:
```yaml
original: "turn on the livin room lite"
corrected: "turn on the living room light"
changes:
  - from: "livin room lite"
    to: "living room light"
candidates:
  - phrase: "living room light"
    segment: "livin room lite"
    score: 0.8823
    threshold: 0.8
    accepted: true
  - phrase: "kitchen light"
    segment: "livin room lite"
    score: 0.5200
    threshold: 0.8
    accepted: false
```

## Migration Workflow

Export from old instance, import to new instance:

```yaml
# 1. Export: call get_correction_config, copy the response JSON
# 2. Import: paste into set_correction_config
service: azure_speech_stt.set_correction_config
data:
  # paste the full get_correction_config response here
```
