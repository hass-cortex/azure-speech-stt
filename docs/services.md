# Services

## Transcription

### `azure_speech_stt.transcribe`

[![Try](https://my.home-assistant.io/badges/developer_call_service.svg)](https://my.home-assistant.io/redirect/developer_call_service/?service=azure_speech_stt.transcribe)

Direct transcription service for programmatic use (returns response data).

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `entity_id` | Yes | -- | Target Azure Speech STT entity |
| `audio_data` | Yes | -- | Base64-encoded WAV audio (PCM 16kHz mono 16-bit) |
| `format` | No | `wav` | Audio format (`wav` or `ogg`) |
| `codec` | No | `pcm` | Audio codec (`pcm` or `opus`) |
| `language` | No | `en-US` | BCP-47 language code |

Response:
```yaml
text: "transcribed text"
```
