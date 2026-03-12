"""
BOB-AI Command Handler
Handles ALL automation:
  - WhatsApp messages
  - Open apps (Notepad, Chrome, VS Code, etc.)
  - System (volume, screenshot, shutdown)
  - Web search / YouTube
  - Time, date, greetings
  - Typing text anywhere
  - Clipboard operations
"""

import os
import sys
import time
import datetime
import webbrowser
import subprocess
import pyautogui
import pyperclip
import pywhatkit as kit
import pyttsx3

# Make pyautogui safe (add delay between actions)
pyautogui.PAUSE         = 0.3
pyautogui.FAILSAFE      = True


class CommandHandler:
    def __init__(self, speak_fn, gui_fn=None):
        self.speak = speak_fn
        self.gui   = gui_fn

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ROUTER
    # ─────────────────────────────────────────────────────────────────────────
    def handle(self, command: str) -> bool:
        """
        Try to match command to a local handler.
        Returns True if handled, False to fall through to Gemini.
        """
        c = command.lower().strip()

        # ── GREETINGS ──
        if any(w in c for w in ["hello", "hi bob", "good morning", "good evening", "good night", "how are you"]):
            return self._greet(c)

        # ── TIME / DATE ──
        if "time" in c and "what" in c or c == "time":
            return self._tell_time()
        if "date" in c or "today" in c:
            return self._tell_date()
        if "day" in c:
            return self._tell_day()

        # ── WHATSAPP ──
        if "whatsapp" in c or "send message" in c or "message to" in c or "text to" in c:
            return self._whatsapp_flow(c)

        # ── OPEN APPLICATIONS ──
        if c.startswith("open "):
            return self._open_app(c.replace("open ", "").strip())

        # ── WEB SEARCH ──
        if "search" in c or "google" in c or "look up" in c:
            return self._web_search(c)

        # ── YOUTUBE ──
        if "youtube" in c or "play" in c:
            return self._youtube(c)

        # ── TYPE SOMETHING ──
        if c.startswith("type ") or "type this" in c:
            return self._type_text(c)

        # ── SCREENSHOT ──
        if "screenshot" in c or "take a picture of screen" in c:
            return self._screenshot()

        # ── VOLUME ──
        if "volume up" in c or "increase volume" in c:
            return self._volume("up")
        if "volume down" in c or "decrease volume" in c:
            return self._volume("down")
        if "mute" in c:
            return self._volume("mute")

        # ── SHUTDOWN / RESTART ──
        if "shutdown" in c and "computer" in c:
            return self._system_shutdown()
        if "restart" in c and "computer" in c:
            return self._system_restart()

        # ── LOCK SCREEN ──
        if "lock" in c and ("screen" in c or "computer" in c or "pc" in c):
            return self._lock()

        # ── COPY / PASTE ──
        if "copy" in c:
            pyautogui.hotkey("ctrl", "c")
            self.speak("Copied to clipboard.")
            return True
        if "paste" in c:
            pyautogui.hotkey("ctrl", "v")
            self.speak("Pasted.")
            return True

        # ── CLOSE APP ──
        if "close" in c or "exit" in c or "quit" in c:
            pyautogui.hotkey("alt", "f4")
            self.speak("Closing the application.")
            return True

        # ── MINIMIZE / MAXIMIZE ──
        if "minimize" in c:
            pyautogui.hotkey("win", "down")
            self.speak("Minimized.")
            return True
        if "maximize" in c:
            pyautogui.hotkey("win", "up")
            self.speak("Maximized.")
            return True

        # ── SWITCH WINDOW ──
        if "switch" in c and "window" in c:
            pyautogui.hotkey("alt", "tab")
            self.speak("Switched window.")
            return True

        # ── CALCULATOR ──
        if "calculator" in c:
            return self._open_app("calculator")

        # ── TELL JOKE ──
        if "joke" in c:
            import random
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
                "Why was the Python developer so calm? Because he knew how to handle exceptions!",
                "My WiFi password is 'incorrect'. So when someone asks, I just say the password is incorrect!"
            ]
            self.speak(random.choice(jokes))
            return True

        return False  # Not handled — send to Gemini

    # ─────────────────────────────────────────────────────────────────────────
    # GREETING
    # ─────────────────────────────────────────────────────────────────────────
    def _greet(self, c):
        hour = datetime.datetime.now().hour
        if "how are you" in c:
            self.speak("I'm fully operational and running at peak performance. How can I help?")
        elif hour < 12:
            self.speak("Good morning! BOB AI at your service. What can I do for you?")
        elif hour < 17:
            self.speak("Good afternoon! Ready to assist you.")
        else:
            self.speak("Good evening! BOB AI here. How can I help?")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # TIME / DATE
    # ─────────────────────────────────────────────────────────────────────────
    def _tell_time(self):
        now  = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        self.speak(f"The current time is {time_str}.")
        return True

    def _tell_date(self):
        now = datetime.datetime.now()
        self.speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")
        return True

    def _tell_day(self):
        self.speak(f"Today is {datetime.datetime.now().strftime('%A')}.")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # WHATSAPP AUTOMATION
    # ─────────────────────────────────────────────────────────────────────────
    def _whatsapp_flow(self, command):
        """
        Handles:
          'send whatsapp to Ganesh saying hello how are you'
          'send message to mom that I'll be late'
          'whatsapp Ravi I am on my way'
        """
        # ── Parse recipient ──
        recipient = None
        message   = None

        # Try to find "to <name>" pattern
        if " to " in command:
            parts = command.split(" to ", 1)
            after = parts[1]  # e.g. "ravi saying hello"

            # Get name (first word or two after "to")
            words = after.split()
            name_words = []
            msg_start = 0
            for i, w in enumerate(words):
                if w in ["saying", "that", "message", "saying that", "and", "tell", "i", "that"]:
                    msg_start = i
                    break
                name_words.append(w)
                msg_start = i + 1

            recipient = " ".join(name_words).strip()
            message   = " ".join(words[msg_start:]).strip()

        if not recipient:
            self.speak("Who should I send the message to?")
            # Note: in real use, the assistant loop listens again here
            return True

        if not message:
            self.speak(f"What message should I send to {recipient}?")
            return True

        # ── Ask confirmation ──
        self.speak(f"Sending '{message}' to {recipient} on WhatsApp. Shall I proceed?")
        return True

    def send_whatsapp_now(self, phone_number: str, message: str):
        """
        Sends WhatsApp message via pywhatkit.
        phone_number format: '+919999999999'
        """
        try:
            now = datetime.datetime.now()
            hour   = now.hour
            minute = now.minute + 2  # send 2 minutes from now
            if minute >= 60:
                minute -= 60
                hour   += 1

            kit.sendwhatmsg(phone_number, message, hour, minute, wait_time=15)
            self.speak(f"WhatsApp message sent successfully.")
        except Exception as e:
            self.speak(f"Couldn't send WhatsApp message. Error: {e}")

    def send_whatsapp_instant(self, phone_number: str, message: str):
        """
        Sends WhatsApp instantly using web automation.
        """
        import urllib.parse
        encoded = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded}"
        webbrowser.open(url)
        time.sleep(8)  # wait for WhatsApp to load
        pyautogui.press("enter")
        self.speak("Message sent via WhatsApp Web.")

    # ─────────────────────────────────────────────────────────────────────────
    # OPEN APPS
    # ─────────────────────────────────────────────────────────────────────────
    def _open_app(self, app_name):
        apps = {
            # Windows apps
            "notepad":      "notepad.exe",
            "calculator":   "calc.exe",
            "paint":        "mspaint.exe",
            "word":         "winword.exe",
            "excel":        "excel.exe",
            "powerpoint":   "powerpnt.exe",
            "task manager": "taskmgr.exe",
            "cmd":          "cmd.exe",
            "command prompt": "cmd.exe",
            "file explorer": "explorer.exe",
            "explorer":     "explorer.exe",
            "camera":       "start microsoft.windows.camera:",
            "settings":     "ms-settings:",
            # Dev tools
            "vs code":      "code",
            "visual studio code": "code",
            "vscode":       "code",
            "pycharm":      "pycharm64.exe",
            "git bash":     "git-bash.exe",
            # Browsers
            "chrome":       "chrome.exe",
            "google chrome": "chrome.exe",
            "firefox":      "firefox.exe",
            "edge":         "msedge.exe",
            # Media
            "spotify":      "spotify.exe",
            "vlc":          "vlc.exe",
            "discord":      "discord.exe",
            "telegram":     "telegram.exe",
            "whatsapp":     "whatsapp.exe",
            # System
            "control panel": "control.exe",
            "device manager": "devmgmt.msc",
        }

        # Normalize
        key = app_name.lower().strip()

        if key in apps:
            exe = apps[key]
            try:
                if exe.startswith("ms-") or exe.startswith("start "):
                    os.system(f"start {exe}")
                else:
                    subprocess.Popen(exe, shell=True)
                self.speak(f"Opening {app_name}.")
            except Exception as e:
                self.speak(f"Couldn't open {app_name}. Make sure it's installed.")
        else:
            # Generic attempt
            try:
                subprocess.Popen(key, shell=True)
                self.speak(f"Trying to open {app_name}.")
            except:
                self.speak(f"I couldn't find {app_name} on your system.")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # WEB SEARCH
    # ─────────────────────────────────────────────────────────────────────────
    def _web_search(self, command):
        # Extract search query
        query = command
        for prefix in ["search for", "search", "google", "look up", "find"]:
            query = query.replace(prefix, "").strip()

        if query:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            self.speak(f"Searching for {query} on Google.")
        else:
            self.speak("What should I search for?")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # YOUTUBE
    # ─────────────────────────────────────────────────────────────────────────
    def _youtube(self, command):
        query = command
        for prefix in ["play", "on youtube", "youtube", "search youtube for"]:
            query = query.replace(prefix, "").strip()

        if query:
            try:
                kit.playonyt(query)
                self.speak(f"Playing {query} on YouTube.")
            except:
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(url)
                self.speak(f"Opening YouTube for {query}.")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # TYPE TEXT
    # ─────────────────────────────────────────────────────────────────────────
    def _type_text(self, command):
        text = command
        for prefix in ["type this", "type the text", "type "]:
            text = text.replace(prefix, "").strip()

        if text:
            time.sleep(0.5)
            pyautogui.write(text, interval=0.04)
            self.speak("Done, I've typed that for you.")
        else:
            self.speak("What should I type?")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # SCREENSHOT
    # ─────────────────────────────────────────────────────────────────────────
    def _screenshot(self):
        try:
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(os.path.expanduser("~"), "Desktop", f"screenshot_{ts}.png")
            pyautogui.screenshot(path)
            self.speak(f"Screenshot saved to your Desktop as screenshot_{ts}.png")
        except Exception as e:
            self.speak(f"Couldn't take screenshot. Error: {e}")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # VOLUME CONTROL
    # ─────────────────────────────────────────────────────────────────────────
    def _volume(self, action):
        try:
            if action == "up":
                for _ in range(5):
                    pyautogui.press("volumeup")
                self.speak("Volume increased.")
            elif action == "down":
                for _ in range(5):
                    pyautogui.press("volumedown")
                self.speak("Volume decreased.")
            elif action == "mute":
                pyautogui.press("volumemute")
                self.speak("Muted.")
        except:
            self.speak("Couldn't control volume on this system.")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # SYSTEM CONTROLS
    # ─────────────────────────────────────────────────────────────────────────
    def _system_shutdown(self):
        self.speak("Shutting down the computer in 10 seconds.")
        os.system("shutdown /s /t 10")
        return True

    def _system_restart(self):
        self.speak("Restarting the computer in 10 seconds.")
        os.system("shutdown /r /t 10")
        return True

    def _lock(self):
        self.speak("Locking your screen.")
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return True
