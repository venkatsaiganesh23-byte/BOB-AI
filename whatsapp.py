"""
BOB-AI WhatsApp Module
Sends WhatsApp messages using WhatsApp Web automation.

Usage example:
  wa = WhatsAppHandler(speak_fn)
  wa.send("Ganesh", "Hey bro what's up")
  wa.send("+919876543210", "Meeting at 3 PM")
"""

import webbrowser
import time
import pyautogui
import urllib.parse
import pywhatkit as kit
import datetime


# ── CONTACT BOOK ─────────────────────────────────────────────────────────────
# Add contacts here: "name": "+91XXXXXXXXXX"
CONTACTS = {
    "ganesh":   "+919999999999",   # replace with real numbers
    "mom":      "+919999999998",
    "dad":      "+919999999997",
    "ravi":     "+919999999996",
    "college":  "+919999999995",
    # Add more as needed...
}


class WhatsAppHandler:
    def __init__(self, speak_fn):
        self.speak = speak_fn

    def resolve_number(self, name_or_number: str) -> str:
        """Resolve a name to phone number using contact book."""
        n = name_or_number.lower().strip()
        if n in CONTACTS:
            return CONTACTS[n]
        if name_or_number.startswith("+"):
            return name_or_number  # already a number
        return None

    def send(self, recipient: str, message: str):
        """
        Send a WhatsApp message.
        recipient: name (from contacts) or phone number with country code
        """
        number = self.resolve_number(recipient)

        if not number:
            self.speak(f"I don't have {recipient}'s number in my contacts. Please add it.")
            return False

        self.speak(f"Sending WhatsApp message to {recipient}. Please wait.")

        try:
            # Method 1: pywhatkit (scheduled, opens browser)
            now    = datetime.datetime.now()
            hour   = now.hour
            minute = now.minute + 2
            if minute >= 60:
                minute -= 60
                hour   = (hour + 1) % 24

            kit.sendwhatmsg(number, message, hour, minute,
                            wait_time=20, tab_close=True)
            self.speak("Message sent successfully via WhatsApp!")
            return True

        except Exception as e:
            # Method 2: Fallback - open WhatsApp Web directly
            try:
                self._send_via_web(number, message)
                return True
            except Exception as e2:
                self.speak(f"Couldn't send message. Error: {e2}")
                return False

    def _send_via_web(self, number: str, message: str):
        """Fallback: Open WhatsApp Web and send via automation."""
        encoded = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={number}&text={encoded}&app_absent=0"
        webbrowser.open(url)
        time.sleep(12)  # wait for WhatsApp Web to load
        pyautogui.press("enter")
        time.sleep(1)
        self.speak("Message sent via WhatsApp Web.")

    def add_contact(self, name: str, number: str):
        """Dynamically add a contact (runtime only)."""
        CONTACTS[name.lower()] = number
        self.speak(f"Added {name} to contacts with number {number}.")
