"""
BOB-AI GUI — Minimal Sci-Fi Status HUD
Shows: Status, what BOB heard, what BOB said
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time


COLORS = {
    "bg":         "#050a12",
    "panel":      "#0b1220",
    "border":     "#1a3a5c",
    "accent":     "#00d4ff",
    "accent2":    "#00ffaa",
    "danger":     "#ff4466",
    "text":       "#c8e0f4",
    "muted":      "#4a6a8a",
    "idle":       "#1a3a5c",
    "listening":  "#00d4ff",
    "bob":        "#00ffaa",
    "user":       "#0088cc",
    "error":      "#ff4466",
    "system":     "#888888",
    "processing": "#ffaa00",
}

ROLE_PREFIX = {
    "bob":        "BOB",
    "user":       "YOU",
    "system":     "SYS",
    "error":      "ERR",
    "listening":  "MIC",
    "idle":       "   ",
    "info":       "INF",
    "processing": "...",
}


class AssistantGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()
        self._build_ui()
        self._pulse_running = True
        self._start_pulse()

    def _setup_window(self):
        self.root.title("BOB-AI — Virtual Assistant")
        self.root.geometry("480x560")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg"])
        self.root.attributes("-topmost", True)       # always on top
        self.root.attributes("-alpha", 0.95)         # slight transparency

        # Try to position bottom-right corner
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"480x560+{sw-500}+{sh-600}")

        # Remove default title bar style (Windows only)
        try:
            self.root.overrideredirect(False)
        except:
            pass

    def _build_ui(self):
        # ── TITLE BAR ──
        title_frame = tk.Frame(self.root, bg=COLORS["panel"], pady=10)
        title_frame.pack(fill="x")

        # Orb
        self.orb_canvas = tk.Canvas(title_frame, width=36, height=36,
                                    bg=COLORS["panel"], highlightthickness=0)
        self.orb_canvas.pack(side="left", padx=(16,8))
        self._draw_orb(COLORS["accent"])

        # Title
        title_inner = tk.Frame(title_frame, bg=COLORS["panel"])
        title_inner.pack(side="left")
        tk.Label(title_inner, text="BOB-AI", bg=COLORS["panel"],
                 fg=COLORS["accent"], font=("Courier New", 16, "bold")).pack(anchor="w")
        tk.Label(title_inner, text="JARVIS-CLASS VIRTUAL ASSISTANT  v1.0",
                 bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Courier New", 7)).pack(anchor="w")

        # Status dot
        self.status_var = tk.StringVar(value="● IDLE")
        self.status_lbl = tk.Label(title_frame, textvariable=self.status_var,
                                   bg=COLORS["panel"], fg=COLORS["muted"],
                                   font=("Courier New", 9, "bold"))
        self.status_lbl.pack(side="right", padx=16)

        # Divider
        tk.Frame(self.root, bg=COLORS["border"], height=1).pack(fill="x")

        # ── STATUS BAR ──
        self.current_frame = tk.Frame(self.root, bg=COLORS["panel"], pady=10)
        self.current_frame.pack(fill="x")
        self.current_var = tk.StringVar(value="Say 'Hey Bob' to activate...")
        tk.Label(self.current_frame, textvariable=self.current_var,
                 bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Courier New", 10), wraplength=440).pack(padx=14)

        # Divider
        tk.Frame(self.root, bg=COLORS["border"], height=1).pack(fill="x")

        # ── CHAT LOG ──
        log_frame = tk.Frame(self.root, bg=COLORS["bg"])
        log_frame.pack(fill="both", expand=True, padx=0, pady=0)

        self.log = tk.Text(
            log_frame,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Courier New", 10),
            relief="flat",
            bd=0,
            wrap="word",
            state="disabled",
            padx=14, pady=10,
            cursor="arrow",
            selectbackground=COLORS["border"],
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log.yview,
                                 bg=COLORS["panel"], troughcolor=COLORS["bg"],
                                 relief="flat", width=6)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)

        # Configure text tags
        for role, color in COLORS.items():
            self.log.tag_configure(role, foreground=color)
        self.log.tag_configure("timestamp", foreground=COLORS["muted"])
        self.log.tag_configure("bold", font=("Courier New", 10, "bold"))

        # ── FOOTER ──
        tk.Frame(self.root, bg=COLORS["border"], height=1).pack(fill="x")
        footer = tk.Frame(self.root, bg=COLORS["panel"], pady=8)
        footer.pack(fill="x")

        # Wake word hint
        tk.Label(footer, text="Wake word: 'Hey Bob'  |  BOB-AI © 2026 Ganesh",
                 bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Courier New", 8)).pack()

    # ─────────────────────────────────────────────────────────────────────────
    def _draw_orb(self, color):
        self.orb_canvas.delete("all")
        self.orb_canvas.create_oval(3, 3, 33, 33, fill=color,
                                    outline=COLORS["accent"], width=1)
        self.orb_canvas.create_oval(8, 8, 16, 16, fill="white",
                                    outline="", stipple="gray25")

    def _start_pulse(self):
        def pulse():
            colors = [COLORS["accent"], "#006688", COLORS["accent"], "#004455"]
            i = 0
            while self._pulse_running:
                try:
                    self.orb_canvas.after(0, lambda c=colors[i % len(colors)]: self._draw_orb(c))
                    i += 1
                    time.sleep(0.8)
                except:
                    break
        t = threading.Thread(target=pulse, daemon=True)
        t.start()

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: UPDATE FROM ASSISTANT
    # ─────────────────────────────────────────────────────────────────────────
    def update(self, text: str, role: str = "info"):
        """Called from assistant thread to update GUI."""
        self.root.after(0, lambda: self._update_ui(text, role))

    def _update_ui(self, text: str, role: str):
        # Update status
        status_map = {
            "listening":  ("● LISTENING", COLORS["accent"]),
            "bob":        ("● SPEAKING",  COLORS["accent2"]),
            "user":       ("● HEARD",     COLORS["user"]),
            "idle":       ("● IDLE",      COLORS["muted"]),
            "processing": ("● THINKING",  COLORS["processing"]),
            "error":      ("● ERROR",     COLORS["danger"]),
            "system":     ("● SYSTEM",    COLORS["muted"]),
        }
        if role in status_map:
            label, color = status_map[role]
            self.status_var.set(label)
            self.status_lbl.config(fg=color)

        # Update current action label
        self.current_var.set(text[:80] + ("..." if len(text) > 80 else ""))

        # Append to log
        ts      = __import__("datetime").datetime.now().strftime("%H:%M:%S")
        prefix  = ROLE_PREFIX.get(role, "   ")
        color   = COLORS.get(role, COLORS["text"])

        self.log.configure(state="normal")
        self.log.insert("end", f"[{ts}] ", "timestamp")
        self.log.insert("end", f"{prefix}  ", role if role in COLORS else "text")
        self.log.insert("end", f"{text}\n", role if role in COLORS else "text")
        self.log.configure(state="disabled")
        self.log.see("end")

        # Orb color flash
        if role == "listening":
            self._draw_orb(COLORS["accent"])
        elif role == "bob":
            self._draw_orb(COLORS["accent2"])
        elif role == "error":
            self._draw_orb(COLORS["danger"])
