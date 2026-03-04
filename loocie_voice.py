"""
================================================================================
LOOCIE BASE MODEL — VOICE ENGINE
File: loocie_voice.py
Version: 1.2 (Wake phrase: "Hey Loocie" via Whisper detection)

Run with:
    python loocie_voice.py

Requires server running on http://127.0.0.1:8080
================================================================================
"""

import os
import time
import wave
import threading
import tempfile
import logging
import subprocess

import numpy as np
import sounddevice as sd
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOOCIE VOICE] %(message)s")
log = logging.getLogger("loocie.voice")

# ── Config ────────────────────────────────────────────────────────────────────
API_URL          = "http://127.0.0.1:8080/chat"
SAMPLE_RATE      = 16000
CHANNELS         = 1
SILENCE_DB       = -40       # dB threshold for silence detection
SILENCE_PAUSE_MS = 800       # ms of silence before stopping recording
MAX_RECORD_SECS  = 30        # max recording length

# Wake phrase mode (this gives you EXACT "Hey Loocie")
WAKE_PHRASE          = "hey loocie"
WAKE_LISTEN_SECONDS  = 2.0    # length of tiny "wake check" snippets
WAKE_CHECK_COOLDOWN  = 2.0    # seconds between checks
WAKE_MIN_TEXT_LEN    = 3

WHISPER_MODEL    = "tiny"    # base is accurate; you can switch to "small" or "tiny" for speed

API_KEY_ENV      = "LOOCIE_API_KEY"
API_KEY_HEADER   = "X-API-Key"


# ══════════════════════════════════════════════════════════════════════════════
# TTS — macOS say
# ══════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    VOICE = "Samantha"
    RATE  = 185

    def speak(self, text: str):
        if not text or not text.strip():
            return
        threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()

    def speak_blocking(self, text: str):
        if not text or not text.strip():
            return
        self._speak_thread(text)

    def _speak_thread(self, text: str):
        try:
            clean = self._clean_text(text)
            subprocess.run(["say", "-v", self.VOICE, "-r", str(self.RATE), clean], check=True, capture_output=True)
        except Exception as e:
            log.error(f"TTS error: {e}")

    def _clean_text(self, text: str) -> str:
        import re
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'#+\s', '', text)
        text = re.sub(r'http\S+', 'a link', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'[\[\]]', '', text)
        return text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO RECORDER
# ══════════════════════════════════════════════════════════════════════════════

class AudioRecorder:
    def record_until_silence(self, max_seconds: int = MAX_RECORD_SECS) -> str:
        frames        = []
        silence_count = 0
        silence_limit = int((SILENCE_PAUSE_MS / 1000) * SAMPLE_RATE)

        log.info("🎙️  Listening...")

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32') as stream:
            start = time.time()
            while time.time() - start < max_seconds:
                data, _ = stream.read(1024)
                frames.append(data)

                rms_db = 20 * np.log10(np.sqrt(np.mean(data**2)) + 1e-10)
                if rms_db < SILENCE_DB:
                    silence_count += 1024
                    if silence_count >= silence_limit:
                        break
                else:
                    silence_count = 0

        audio = np.concatenate(frames, axis=0)
        tmp   = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

        with wave.open(tmp.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())

        return tmp.name


# ══════════════════════════════════════════════════════════════════════════════
# SPEECH TO TEXT
# ══════════════════════════════════════════════════════════════════════════════

class WhisperSTT:
    def __init__(self):
        log.info(f"Loading Whisper model '{WHISPER_MODEL}'...")
        import whisper
        self.whisper = whisper
        self.model = whisper.load_model(WHISPER_MODEL)
        log.info("✅ Whisper loaded.")

    def transcribe(self, audio_path: str) -> str:
        try:
            result = self.model.transcribe(audio_path, language="en", task="transcribe")
            text = (result.get("text", "") or "").strip()
            if len(text) < WAKE_MIN_TEXT_LEN:
                return ""
            return text
        except Exception as e:
            log.error(f"Transcription error: {e}")
            return ""


# ══════════════════════════════════════════════════════════════════════════════
# LOOCIE API CALLER
# ══════════════════════════════════════════════════════════════════════════════

class LooiceChatAPI:
    def __init__(self):
        self.api_key = os.getenv(API_KEY_ENV, "").strip()
        if not self.api_key:
            log.warning(f"⚠️  {API_KEY_ENV} is not set. /chat will return 401 if API key auth is enabled.")

    def send(self, message: str) -> str:
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers[API_KEY_HEADER] = self.api_key

            response = requests.post(API_URL, json={"message": message}, headers=headers, timeout=15)

            if response.status_code == 200:
                data  = response.json()
                reply = data.get("reply", data.get("response", ""))
                log.info(f"💬 Loocie: '{reply[:80]}...'")
                return reply

            if response.status_code == 401:
                log.error("API returned 401 Unauthorized (missing/invalid X-API-Key).")
                return "I'm secured right now. Please check the API key configuration."

            log.error(f"API error {response.status_code}: {response.text}")
            return "I'm having trouble connecting right now. Please try again."

        except requests.exceptions.ConnectionError:
            log.error("Cannot reach Loocie server. Is it running on port 8080?")
            return "I can't reach my brain right now. Please make sure the server is running."
        except requests.exceptions.Timeout:
            log.error("API request timed out.")
            return "I timed out talking to my brain. Please try again."
        except Exception as e:
            log.error(f"API call failed: {e}")
            return "Something went wrong. Please try again."


# ══════════════════════════════════════════════════════════════════════════════
# WAKE PHRASE LISTENER (Hey Loocie)
# ══════════════════════════════════════════════════════════════════════════════

class WakePhraseListener:
    """
    Listens continuously in small chunks and triggers when WAKE_PHRASE is spoken.
    Uses Whisper to detect the phrase (no pretrained wake model needed).
    """
    def __init__(self, stt: WhisperSTT, callback):
        self.stt = stt
        self.callback = callback
        self._running = False
        self._last_check = 0.0
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("👂 Wake phrase listening active... say 'Hey Loocie'")

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            now = time.time()
            if now - self._last_check < WAKE_CHECK_COOLDOWN:
                time.sleep(0.05)
                continue
            self._last_check = now

            # record a short snippet for wake detection
            wav_path = self._record_snippet(seconds=WAKE_LISTEN_SECONDS)
            text = self.stt.transcribe(wav_path).lower().strip()

            try:
                os.unlink(wav_path)
            except Exception:
                pass

            if not text:
                continue

            if WAKE_PHRASE in text:
                log.info(f"✨ Wake phrase detected! Heard: '{text}'")
                threading.Thread(target=self.callback, daemon=True).start()

    def _record_snippet(self, seconds: float) -> str:
        frames = []
        samples_needed = int(seconds * SAMPLE_RATE)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32') as stream:
            collected = 0
            while collected < samples_needed:
                data, _ = stream.read(1024)
                frames.append(data)
                collected += len(data)

        audio = np.concatenate(frames, axis=0)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        return tmp.name


# ══════════════════════════════════════════════════════════════════════════════
# MAIN VOICE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class LooiceVoice:
    def __init__(self):
        log.info("Initialising Loocie Voice Engine...")

        self.tts      = TTSEngine()
        self.recorder = AudioRecorder()
        self.stt      = WhisperSTT()
        self.api      = LooiceChatAPI()

        self.wake     = WakePhraseListener(stt=self.stt, callback=self._on_wake_word)
        self._processing = False

        log.info("✅ Loocie Voice Engine ready.")

    def start(self):
        self.tts.speak_blocking("Loocie voice is online. Say hey Loocie to get started.")
        self.wake.start()

        log.info("")
        log.info("=" * 50)
        log.info("  LOOCIE VOICE ACTIVE")
        log.info("  Say 'Hey Loocie' to activate")
        log.info("  Press Ctrl+C to stop")
        log.info("=" * 50)
        log.info("")

    def _on_wake_word(self):
        if self._processing:
            return

        self._processing = True
        try:
            wav_path = self.recorder.record_until_silence(max_seconds=MAX_RECORD_SECS)
            text = self.stt.transcribe(wav_path)

            try:
                os.unlink(wav_path)
            except Exception:
                pass

            if not text:
                return

            log.info(f"📝 Heard: '{text}'")
            reply = self.api.send(text)
            self.tts.speak(reply)

        finally:
            self._processing = False


def main():
    voice = LooiceVoice()
    voice.start()

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        log.info("Stopping Loocie Voice...")
        voice.wake.stop()


if __name__ == "__main__":
    main()