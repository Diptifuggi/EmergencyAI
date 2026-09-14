"""Small, safe smoke test for Sarvam Speech-to-Text.

The API key is loaded only from Sarvam_STT_Test/.env and is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

SUPPORTED_LANGUAGES = {"auto", "en-IN", "hi-IN", "gu-IN", "mr-IN"}
DEFAULT_URL = "https://api.sarvam.ai/speech-to-text"
DEFAULT_MODEL = "saaras:v2.5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Sarvam multilingual STT")
    parser.add_argument("--audio", type=Path, default=ROOT / "test_audio.wav")
    parser.add_argument("--language", default="auto", choices=sorted(SUPPORTED_LANGUAGES))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key or api_key.startswith("replace_"):
        print("SARVAM_API_KEY is missing. Set it in Sarvam_STT_Test/.env.")
        return 2

    audio_path = args.audio if args.audio.is_absolute() else ROOT / args.audio
    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}")
        return 2
    audio = audio_path.read_bytes()
    if not audio:
        print("Audio file is empty.")
        return 2

    url = os.getenv("SARVAM_API_URL", DEFAULT_URL).strip() or DEFAULT_URL
    model = os.getenv("SARVAM_STT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    form = {"model": model}
    if args.language != "auto":
        form["language_code"] = args.language

    print(f"Sending {audio_path.name} ({len(audio)} bytes) to Sarvam ({args.language})...")
    try:
        response = httpx.post(
            url,
            headers={"api-subscription-key": api_key},
            data=form,
            files={"file": (audio_path.name, audio, "audio/wav")},
            timeout=float(os.getenv("SARVAM_TIMEOUT_SECONDS", "60")),
        )
    except httpx.TimeoutException:
        print("Sarvam request timed out.")
        return 1
    except httpx.HTTPError as exc:
        print(f"Sarvam request failed: {exc}")
        return 1

    if response.status_code >= 400:
        print(f"Sarvam returned HTTP {response.status_code}.")
        try:
            detail = response.json().get("message") or response.json().get("detail")
            if detail:
                print(f"Provider message: {detail}")
        except ValueError:
            pass
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("Sarvam returned non-JSON output.")
        return 1

    transcript = str(payload.get("transcript") or payload.get("text") or "").strip()
    print(json.dumps({
        "success": bool(transcript),
        "transcript": transcript,
        "language": payload.get("language_code") or payload.get("detected_language_code"),
        "provider": "sarvam",
        "model": model,
    }, ensure_ascii=False, indent=2))
    return 0 if transcript else 1


if __name__ == "__main__":
    sys.exit(main())
