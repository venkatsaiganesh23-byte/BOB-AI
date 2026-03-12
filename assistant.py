"""
BOB-AI Assistant Core Brain
Handles: wake word, speech recognition, Gemini AI, command routing
"""

import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import os
import time
import datetime
import threading
from modules.commands import CommandHandler

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
WAKE_WORDS      = ["hey bob", "bob", "hey jarvis", "jarvis", "hey bub"]
BOT_NAME        = "BOB"

genai.configure(api_key=GEMINI_API_KEY)


class Assistant:
    def __init__(self, gui_callback=None):
        self.gui_callback   = gui_callback
        self.recognizer     = sr.Recognizer()
        self.mic            = sr.Microphone()
        self.is_listening   = False
        self.awake          = False

        # ── TTS ENGINE ──
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate",  175)    # speed
        self.engine.setProperty("volume", 1.0)
        voices = self.engine.getProperty("voices")
        # prefer male voice (index 0 on most Windows systems)
        self.engine.setProperty("voice", voices[0].id if voices else None)

        # ── GEMINI ──
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=f"""You are {BOT_NAME}-AI, a Jarvis-class personal voice assistant.
You speak in short, crisp sentences — like a smart AI assistant.
Keep ALL responses under 3 sentences unless asked for detail.
You are helpful, witty, and confident. Never say you're an AI model; you ARE {BOT_NAME}.
When you don't know something factual, say so briefly."""
        )
        self.chat = self.model.start_chat(history=[])

        # ── COMMAND HANDLER ──
        self.cmd = CommandHandler(speak_fn=self.speak, gui_fn=self.gui_callback)

        # ── MICROPHONE CALIBRATION ──
        self._log("Calibrating microphone...", "system")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        self._log("Microphone ready.", "system")

    # ─────────────────────────────────────────────────────────────────────────
    # LOGGING / GUI UPDATE
    # ─────────────────────────────────────────────────────────────────────────
    def _log(self, text, role="info"):
        print(f"[{role.upper()}] {text}")
        if self.gui_callback:
            self.gui_callback(text, role)

    # ─────────────────────────────────────────────────────────────────────────
    # TEXT-TO-SPEECH
    # ─────────────────────────────────────────────────────────────────────────
    def speak(self, text):
        self._log(text, "bob")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"[TTS ERROR] {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SPEECH RECOGNITION
    # ─────────────────────────────────────────────────────────────────────────
    def listen(self, timeout=5, phrase_limit=8) -> str:
        """Listen from mic and return recognized text (lowercase)."""
        try:
            with self.mic as source:
                self.is_listening = True
                if self.gui_callback:
                    self.gui_callback("Listening...", "listening")
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )
            self.is_listening = False
            text = self.recognizer.recognize_google(audio).lower().strip()
            self._log(f"Heard: {text}", "user")
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            self._log(f"Speech service error: {e}", "error")
            return ""
        finally:
            self.is_listening = False

    # ─────────────────────────────────────────────────────────────────────────
    # WAKE WORD DETECTION
    # ─────────────────────────────────────────────────────────────────────────
    def wait_for_wake_word(self):
        """Passively listen for the wake word."""
        if self.gui_callback:
            self.gui_callback("Waiting for wake word... (say 'Hey Bob')", "idle")
        while True:
            heard = self.listen(timeout=10, phrase_limit=4)
            if any(wake in heard for wake in WAKE_WORDS):
                self._log("Wake word detected!", "system")
                return True

    # ─────────────────────────────────────────────────────────────────────────
    # AI FALLBACK (GEMINI)
    # ─────────────────────────────────────────────────────────────────────────
    def ask_gemini(self, query: str) -> str:
        try:
            response = self.chat.send_message(query)
            return response.text.strip()
        except Exception as e:
            return f"I couldn't reach my AI brain. Error: {e}"

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESS COMMAND
    # ─────────────────────────────────────────────────────────────────────────
    def process_command(self, command: str):
        """Route command to handler or Gemini."""
        self._log(f"Processing: {command}", "processing")

        # Try local command handlers first (fast, no internet needed)
        handled = self.cmd.handle(command)

        # If not handled locally → ask Gemini AI
        if not handled:
            reply = self.ask_gemini(command)
            self.speak(reply)

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        self.speak(f"BOB AI online. Say 'Hey Bob' to activate me.")
        self._log("BOB-AI Started. Waiting for wake word.", "system")

        while True:
            try:
                # Step 1: Wait for wake word
                self.wait_for_wake_word()

                # Step 2: Acknowledge
                self.speak("Yes, I'm listening.")

                # Step 3: Listen for actual command
                command = self.listen(timeout=6, phrase_limit=12)

                if not command:
                    self.speak("I didn't catch that. Try again.")
                    continue

                if any(w in command for w in ["stop", "sleep", "bye", "shutdown bob"]):
                    self.speak("Going to sleep. Say Hey Bob to wake me up.")
                    continue

                # Step 4: Process command
                self.process_command(command)

            except KeyboardInterrupt:
                self.speak("Shutting down. Goodbye!")
                break
            except Exception as e:
                self._log(f"Loop error: {e}", "error")
                time.sleep(1)
