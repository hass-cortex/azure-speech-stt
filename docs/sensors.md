# Runtime Statistics Sensors

The integration provides sensor entities grouped under a single device, tracking transcription usage and correction performance.

All sensors are diagnostic entities. Sensors disabled by default can be enabled in **Settings > Devices & Services > Azure Speech-to-Text > Entities**.

## Transcription Output

| Sensor | Enabled | Unit | Description |
|--------|---------|------|-------------|
| **Transcribed text** | Yes | -- | Azure's original transcription output (cleared on no-speech) |
| **Corrected text** | Yes | -- | Text after correction pipeline (cleared when no correction or no-speech) |
| **Last result** | Yes | -- | Status of most recent attempt: `Success`, `No speech`, or `API error` |

## Usage Counters

| Sensor | Enabled | Unit | Description |
|--------|---------|------|-------------|
| **Total requests** | Yes | count | Total API calls (success + failure) |
| **Successful requests** | No | count | Requests that returned a transcription |
| **Failed requests** | Yes | count | Requests that returned an API error (HTTP errors, timeouts). Does not include no-speech results |
| **Corrections applied** | Yes | count | Number of requests where correction changed the text |
| **Total audio duration** | Yes | minutes | Cumulative audio processed (for free tier tracking) |

## Last Request Details

| Sensor | Enabled | Unit | Description |
|--------|---------|------|-------------|
| **Last API used** | No | -- | Which Azure API was used: `Fast Transcription API` or `Real-time API` |
| **Last API duration** | Yes | ms | Response time of the most recent API call |
| **Average API duration** | Yes | ms | Mean response time across successful requests since last HA restart |
| **Last audio size** | No | bytes | Size of the most recent audio payload |
| **Last audio duration** | No | seconds | Duration of the most recent audio clip |
| **Last language** | No | -- | BCP-47 locale used in the most recent request |
