# Sarvam STT smoke test

This folder is an isolated smoke test for Sarvam Speech-to-Text. It does not modify or bypass the EmergencyIQ Flutter/FastAPI workflow.

## Setup

1. Put a real speech recording in this folder as `test_audio.wav`.
2. Copy the API key into `.env` locally:

```text
SARVAM_API_KEY=replace_with_your_server_side_key
SARVAM_API_URL=https://api.sarvam.ai/speech-to-text
SARVAM_STT_MODEL=saaras:v2.5
SARVAM_TIMEOUT_SECONDS=60
```

Never commit `.env` or place the key in source code. The repository `.gitignore` already ignores nested `.env` files.

Use the project's backend virtual environment, which already contains `httpx` and `python-dotenv`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
cd ..\Sarvam_STT_Test
python test_sarvam_stt.py --language en-IN
```

## Language tests

Use one command per language:

```powershell
python test_sarvam_stt.py --language en-IN
python test_sarvam_stt.py --language hi-IN
python test_sarvam_stt.py --language gu-IN
python test_sarvam_stt.py --language mr-IN
python test_sarvam_stt.py --language auto
```

The script prints only the transcription response and never prints the API key. Use real speech recordings for meaningful results; a silent or synthetic fixture may correctly produce an empty transcript.
