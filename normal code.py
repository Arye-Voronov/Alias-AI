# -*- coding: utf-8 -*-
import difflib
import json
import random
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
import words


# שם המודל המקומי ש-Ollama יריץ בשביל רמזי AI.
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_TIMEOUT_SECONDS = 60
APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "settings.json"
SCORES_FILE = APP_DIR / "scores.json"
STATS_FILE = APP_DIR / "stats.json"
EXPORTS_DIR = APP_DIR / "game_exports"
DIFFICULTY_SETTINGS = {
    "קל": {"seconds": 90, "start_hints": 2, "max_attempts": 5, "score_bonus": 0},
    "רגיל": {"seconds": 60, "start_hints": 1, "max_attempts": 5, "score_bonus": 0},
    "קשה": {"seconds": 45, "start_hints": 1, "max_attempts": 4, "score_bonus": 2},
}
GAME_LENGTH_OPTIONS = ["כל הקטגוריה", "5", "10", "15", "20"]


# מנקה תשובת AI מכותרות וממרכאות כדי להציג רק את הרמז עצמו.
def clean_ai_hint(hint):
    hint = hint.strip()
    for prefix in ("הרמז:", "רמז:", "Hint:"):
        if hint.startswith(prefix):
            hint = hint[len(prefix):].strip()
    return hint.strip("\"'“”")


# בודק שהרמז שה-AI החזיר באמת מתאים למשחק ולא חושף את המילה.
def is_usable_ai_hint(hint, word):
    normalized_hint = words.normalize_guess(hint)
    if not normalized_hint:
        return False
    if words.normalize_guess(word) in normalized_hint:
        return False
    if len(normalized_hint) < 6:
        return False
    if normalized_hint.count(" ") == 0 and any(mark in normalized_hint for mark in "?!"):
        return False
    return True


# הופך תשובת AI ארוכה לרשימה של 5 רמזים תקינים.
def parse_ai_hints(text, word):
    hints = []
    for line in text.splitlines():
        hint = clean_ai_hint(line)
        hint = hint.lstrip("-•0123456789. )(").strip()
        if is_usable_ai_hint(hint, word):
            hints.append(hint)
        if len(hints) == words.MAX_HINTS:
            break
    return hints if len(hints) == words.MAX_HINTS else None


# שולח ל-Ollama את המילה והרמזים המוכנים, ומבקש ממנו לשפר אותם.
def generate_ollama_hints(word, prepared_hints, category):
    prompt = (
        "כתוב 5 רמזים בעברית למשחק Alias.\n"
        f"המילה הסודית היא: {word}\n"
        f"הקטגוריה היא: {category}\n"
        f"הרמזים המוכנים שכבר קיימים, מהקשה לקל, הם: {prepared_hints}\n"
        "שפר את הרמזים האלה מעט, אבל שמור על אותו רעיון ועל אותו סדר קושי.\n"
        "רמז 1 צריך להיות הכי קשה, ורמז 5 הכי קל.\n"
        "אסור להשתמש במילה הסודית עצמה או בהטיות ישירות שלה.\n"
        "אל תיתן משחק אותיות, אל תכתוב את האותיות של המילה, ואל תשתמש בצליל של המילה.\n"
        "ענה ב-5 שורות בלבד. בכל שורה רמז אחד קצר. בלי הסברים ובלי כותרות."
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        return parse_ai_hints(data.get("response", ""), word)
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


# שכבת עטיפה: כרגע ה-AI היחיד הוא Ollama, אבל כך קל להחליף ספק בעתיד.
def generate_ai_hints(word, prepared_hints, category):
    return generate_ollama_hints(word, prepared_hints, category)


def read_json_file(path, fallback):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json_file(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def get_hint_similarity(first_hint, second_hint):
    first = words.normalize_guess(first_hint)
    second = words.normalize_guess(second_hint)
    return difflib.SequenceMatcher(None, first, second).ratio()


def filter_duplicate_ai_hints(ai_hints, prepared_hints):
    if not ai_hints:
        return None
    filtered = []
    for hint in ai_hints:
        if any(get_hint_similarity(hint, existing) > 0.86 for existing in filtered):
            continue
        filtered.append(hint)
    if len(filtered) < words.MAX_HINTS:
        for hint in prepared_hints:
            if all(get_hint_similarity(hint, existing) <= 0.86 for existing in filtered):
                filtered.append(hint)
            if len(filtered) == words.MAX_HINTS:
                break
    return filtered[:words.MAX_HINTS] if len(filtered) == words.MAX_HINTS else None


# AliasGameApp implements the full Alias guessing game UI and logic.
class AliasGameApp:
    # Initialize app state, UI styles, and starting state when constructed.
    def __init__(self, root):
        self.colors = {
            "hero":         "#C8102E",
            "hero_accent":  "#9B0D23",
            "card":         "#FFFFFF",
            "card_alt":     "#FFF5F6",
            "card_inner":   "#FFF0F2",
            "entry":        "#FFFFFF",
            "list":         "#FFFFFF",
            "primary":      "#C8102E",
            "text":         "#1A1A1A",
            "muted":        "#888888",
            "info":         "#C8102E",
            "success":      "#1A7A4A",
            "warning":      "#B45309",
            "error":        "#9B0D23",
            "bg":           "#FAFAFA",
        }
        self.root = root
        self.root.title("Alias AI")
        self.root.geometry("1060x760")
        self.root.minsize(900, 660)
        self.root.configure(bg=self.colors["bg"])

        # מצב המשחק: ניקוד, מילה נוכחית, רמזים, ניסיונות וקטגוריה.
        self.score = 0
        self.secret_word = None
        self.all_hints = []
        self.revealed_hints = []
        self.attempts_used = 0
        self.round_number = 0
        self.round_finished = False
        self.current_category = None
        self.randomizer = random.SystemRandom()
        self.category_options = []
        self.category_lookup = {}
        self.used_words = set()
        self.hint_source_var = tk.StringVar(value="prepared")
        self.difficulty_var = tk.StringVar(value="רגיל")
        self.game_length_var = tk.StringVar(value=GAME_LENGTH_OPTIONS[0])
        self.player_name_var = tk.StringVar(value="שחקן")
        self.practice_mode_var = tk.BooleanVar(value=False)
        self.timer_enabled_var = tk.BooleanVar(value=True)
        self.ai_request_id = 0
        self.timer_after_id = None
        self.animation_after_id = None
        self.time_left = 0
        self.max_rounds = None
        self.correct_words = 0
        self.failed_words = 0
        self.skipped_words = 0
        self.total_hints_used = 0
        self.last_summary = ""
        self.round_results = []
        self.settings = read_json_file(SETTINGS_FILE, {})

        # בניית המסך והכנת הנתונים הראשוניים.
        self.configure_styles()
        self.build_layout()
        self.populate_categories()
        self.load_saved_settings()
        self.render_intro_state()

    # Configure all ttk style themes and self.colors["bg" visual styles used by the app.
    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
    
        # צבעי בסיס לסגנונות Tkinter/ttk.
        red       = "#C8102E"
        red_dark  = "#9B0D23"
        red_soft  = "#FFF0F2"
        red_muted = "#F5C6CC"
        white     = "#FFFFFF"
        bg_main   = "#FAFAFA"
        text_dark = "#1A1A1A"
        muted     = "#888888"
    
        style.configure("App.TFrame", background=bg_main)
    
        style.configure("Title.TLabel",
            background=red, foreground=white,
            font=("Segoe UI", 32, "bold"), anchor="center")
    
        style.configure("Subtitle.TLabel",
            background=red, foreground="#FFCCCC",
            font=("Segoe UI", 11), anchor="center")
    
        style.configure("CardTitle.TLabel",
            background=white, foreground=red,
            font=("Segoe UI", 12, "bold"))
    
        style.configure("Body.TLabel",
            background=white, foreground=muted,
            font=("Segoe UI", 10))
    
        style.configure("MetricValue.TLabel",
            background=white, foreground=red,
            font=("Segoe UI", 24, "bold"))
    
        style.configure("MetricLabel.TLabel",
            background=white, foreground=muted,
            font=("Segoe UI", 10, "bold"))
    
        style.configure("Start.TButton",
            font=("Segoe UI", 12, "bold"),
            background=red, foreground=white, borderwidth=0)
        style.map("Start.TButton",
            background=[("active", red_dark), ("disabled", red_muted)])
    
        style.configure("Next.TButton",
            font=("Segoe UI", 12),
            background=white, foreground=red, borderwidth=1, relief="solid")
        style.map("Next.TButton",
            background=[("active", red_soft), ("disabled", white)],
            foreground=[("disabled", muted)])
    
        style.configure("Guess.TButton",
            font=("Segoe UI", 12, "bold"),
            background=red_dark, foreground=white, borderwidth=0)
        style.map("Guess.TButton",
            background=[("active", "#7A0A1B"), ("disabled", red_muted)])
    
        style.configure("Game.Horizontal.TProgressbar",
            troughcolor=red_muted, background=red, thickness=8, borderwidth=0)
    
        style.configure("TCombobox",
            fieldbackground=white, background=white, foreground=text_dark,
            selectbackground=red_soft, selectforeground=text_dark)
        style.map("TCombobox",
        fieldbackground=[("readonly", white)],
        foreground=[("readonly", text_dark)])
    # Build the GUI layout with frames, buttons, labels and interactive widgets.
    def build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.home_screen = ttk.Frame(self.root, style="App.TFrame", padding=22)
        self.game_screen = ttk.Frame(self.root, style="App.TFrame", padding=20)
        for screen in (self.home_screen, self.game_screen):
            screen.grid(row=0, column=0, sticky="nsew")
            screen.grid_columnconfigure(0, weight=1)

        self.home_screen.grid_rowconfigure(1, weight=1)

        home_header = tk.Frame(
            self.home_screen,
            bg=self.colors["hero"],
            highlightthickness=1,
            highlightbackground="#f9fbff",
            bd=0,
            padx=30,
            pady=28,
        )
        home_header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        home_header.grid_columnconfigure(0, weight=1)
        ttk.Label(home_header, text="Alias AI", style="Title.TLabel").grid(row=0, column=0, sticky="e")
        ttk.Label(
            home_header,
            text="בחר הגדרות, בדוק את המאגר, ואז עבור למשחק",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="e", pady=(6, 0))

        # מעטפת מסך המשחק.
        outer = self.game_screen
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(3, weight=1)

        # כותרת עליונה של המשחק.
        header = tk.Frame(
            outer,
            bg=self.colors["hero"],
            highlightthickness=1,
            highlightbackground="#f9fbff",
            bd=0,
            padx=26,
            pady=24,
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(header, text="Alias AI", style="Title.TLabel").grid(row=0, column=0, sticky="e")
        ttk.Label(
            header,
            text="משחק ניחוש מילים עם רמזים שמתחילים קשים והופכים קלים יותר בכל ניסיון",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="e", pady=(6, 0))
        self.hero_badge = tk.Label(
            header,
            text="Game Center Style",
            bg=self.colors["hero_accent"],
            fg="#ffffff",
            font=("Helvetica", 10, "bold"),
            padx=16,
            pady=8,
        )
        self.hero_badge.grid(row=0, column=1, rowspan=2, sticky="w", padx=(0, 12))

        # אזור בחירת קטגוריה, התחלת משחק ובחירת מקור הרמזים.
        controls_card = tk.Frame(self.home_screen, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=24, pady=24)
        controls_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        controls_card.grid_columnconfigure(0, weight=1)
        controls_card.grid_columnconfigure(1, weight=1)
        controls_card.grid_columnconfigure(2, weight=0)
        controls_card.grid_columnconfigure(3, weight=0)

        ttk.Label(controls_card, text="קטגוריה", style="CardTitle.TLabel").grid(
            row=0, column=3, sticky="ne", padx=(0, 10)
        )

        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            controls_card,
            textvariable=self.category_var,
            state="readonly",
            justify="right",
            font=("Arial", 12),
        )
        self.category_combo.grid(row=0, column=2, sticky="ew", padx=(12, 0))

        self.start_button = ttk.Button(
            controls_card,
            text="התחל משחק",
            style="Start.TButton",
            command=self.start_game,
        )
        self.start_button.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(12, 0))

        ttk.Label(controls_card, text="רמת קושי", style="CardTitle.TLabel").grid(
            row=1, column=3, sticky="ne", padx=(0, 10), pady=(14, 0)
        )

        self.difficulty_combo = ttk.Combobox(
            controls_card,
            textvariable=self.difficulty_var,
            values=list(DIFFICULTY_SETTINGS),
            state="readonly",
            justify="right",
            font=("Arial", 12),
            width=10,
        )
        self.difficulty_combo.grid(row=1, column=2, sticky="ew", padx=(12, 0), pady=(14, 0))

        ttk.Label(controls_card, text="שם שחקן", style="CardTitle.TLabel").grid(
            row=2, column=3, sticky="ne", padx=(0, 10), pady=(14, 0)
        )
        self.player_entry = tk.Entry(
            controls_card,
            textvariable=self.player_name_var,
            justify="right",
            font=("Arial", 12),
            relief="solid",
            bd=1,
            bg=self.colors["entry"],
            fg=self.colors["text"],
        )
        self.player_entry.grid(row=2, column=2, sticky="ew", padx=(12, 0), pady=(14, 0))

        self.game_length_combo = ttk.Combobox(
            controls_card,
            textvariable=self.game_length_var,
            values=GAME_LENGTH_OPTIONS,
            state="readonly",
            justify="right",
            font=("Arial", 12),
            width=12,
        )
        self.game_length_combo.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(14, 0))

        self.practice_check = tk.Checkbutton(
            controls_card,
            text="אימון ללא ניקוד (0 נקודות)",
            variable=self.practice_mode_var,
            bg=self.colors["card"],
            fg=self.colors["text"],
            activebackground=self.colors["card"],
            activeforeground=self.colors["primary"],
            selectcolor=self.colors["card_inner"],
            font=("Helvetica", 11, "bold"),
            anchor="e",
            justify="right",
        )
        self.practice_check.grid(row=2, column=0, sticky="e", pady=(14, 0))

        self.timer_check = tk.Checkbutton(
            controls_card,
            text="משחק עם טיימר",
            variable=self.timer_enabled_var,
            bg=self.colors["card"],
            fg=self.colors["text"],
            activebackground=self.colors["card"],
            activeforeground=self.colors["primary"],
            selectcolor=self.colors["card_inner"],
            font=("Helvetica", 11, "bold"),
            anchor="e",
            justify="right",
        )
        self.timer_check.grid(row=3, column=0, sticky="e", pady=(14, 0))

        # בחירה בין רמזים מוכנים לבין רמזים שה-AI משפר בתחילת כל סבב.
        hint_source_frame = tk.Frame(controls_card, bg=self.colors["card"])
        hint_source_frame.grid(row=3, column=2, columnspan=2, sticky="e", pady=(14, 0), padx=(0, 10))

        self.prepared_hints_radio = tk.Radiobutton(
            hint_source_frame,
            text="רמזים מוכנים מראש",
            variable=self.hint_source_var,
            value="prepared",
            bg=self.colors["card"],
            fg=self.colors["text"],
            activebackground=self.colors["card"],
            activeforeground=self.colors["primary"],
            selectcolor=self.colors["card_inner"],
            font=("Helvetica", 11, "bold"),
            anchor="e",
            justify="right",
        )
        self.prepared_hints_radio.grid(row=0, column=1, sticky="e", padx=(14, 0))

        self.ai_hints_radio = tk.Radiobutton(
            hint_source_frame,
            text="AI משפר רמזים מוכנים",
            variable=self.hint_source_var,
            value="ai",
            bg=self.colors["card"],
            fg=self.colors["text"],
            activebackground=self.colors["card"],
            activeforeground=self.colors["primary"],
            selectcolor=self.colors["card_inner"],
            font=("Helvetica", 11, "bold"),
            anchor="e",
            justify="right",
        )
        self.ai_hints_radio.grid(row=0, column=0, sticky="e")

        self.categories_summary = tk.Label(
            controls_card,
            text="",
            bg=self.colors["card"],
            fg=self.colors["muted"],
            font=("Helvetica", 11),
            anchor="e",
            justify="right",
        )
        self.categories_summary.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        tools_frame = tk.Frame(controls_card, bg=self.colors["card"])
        tools_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        for index in range(3):
            tools_frame.grid_columnconfigure(index, weight=1)

        ttk.Button(tools_frame, text="שיאים", style="Next.TButton", command=self.show_high_scores).grid(
            row=0, column=2, sticky="ew", padx=(0, 8)
        )
        ttk.Button(tools_frame, text="סטטיסטיקה", style="Next.TButton", command=self.show_category_stats).grid(
            row=0, column=1, sticky="ew", padx=8
        )
        ttk.Button(tools_frame, text="ייצוא סיכום", style="Next.TButton", command=self.export_last_summary).grid(
            row=0, column=0, sticky="ew", padx=(8, 0)
        )

        game_actions = tk.Frame(outer, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=18, pady=14)
        game_actions.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            game_actions.grid_columnconfigure(index, weight=1)

        ttk.Button(game_actions, text="חזרה לבית", style="Next.TButton", command=self.return_home).grid(
            row=0, column=3, sticky="ew", padx=(0, 8)
        )
        self.next_button = ttk.Button(
            game_actions,
            text="למילה הבאה",
            style="Next.TButton",
            command=self.next_round,
            state="disabled",
        )
        self.next_button.grid(row=0, column=2, sticky="ew", padx=8)
        self.skip_button = ttk.Button(
            game_actions,
            text="דלג",
            style="Next.TButton",
            command=self.skip_round,
            state="disabled",
        )
        self.skip_button.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(game_actions, text="ייצוא סיכום", style="Next.TButton", command=self.export_last_summary).grid(
            row=0, column=0, sticky="ew", padx=(8, 0)
        )

        # כרטיסי מדדים: ניקוד, כמות רמזים פתוחים וקטגוריה.
        metrics = ttk.Frame(outer, style="App.TFrame")
        metrics.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for index in range(4):
            metrics.grid_columnconfigure(index, weight=1)

        self.score_value = self.build_metric(metrics, 0, "ניקוד", "0")
        self.hints_value = self.build_metric(metrics, 1, "רמזים פתוחים", f"0/{words.MAX_HINTS}")
        self.timer_value = self.build_metric(metrics, 2, "זמן", "--")
        self.category_value = self.build_metric(metrics, 3, "קטגוריה", "עדיין לא נבחרה")

        # אזור התוכן הראשי: רמזים בצד אחד וניחושים בצד השני.
        content = ttk.Frame(outer, style="App.TFrame")
        content.grid(row=3, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        # לוח הסבב: סטטוס, התקדמות ורשימת הרמזים שנפתחו.
        game_card = tk.Frame(content, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=22, pady=22)
        game_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        game_card.grid_columnconfigure(0, weight=1)
        game_card.grid_rowconfigure(4, weight=1)

        self.round_title = ttk.Label(game_card, text="?מוכנים להתחיל", style="CardTitle.TLabel")
        self.round_title.grid(row=0, column=0, sticky="e")
        self.status_box = tk.Label(
            game_card,
            text="!בחר קטגוריה ולחץ על התחל משחק כדי לקבל את הרמז הראשון",
            bg="#f3f7ff",
            fg=self.colors["info"],
            font=("Helvetica", 12, "bold"),
            anchor="e",
            justify="right",
            wraplength=520,
            padx=18,
            pady=16,
        )
        self.status_box.grid(row=1, column=0, sticky="ew", pady=(12, 10))

        self.progress_label = ttk.Label(game_card, text="התקדמות בסבב", style="Body.TLabel")
        self.progress_label.grid(row=2, column=0, sticky="e", pady=(0, 6))

        self.progress = ttk.Progressbar(
            game_card,
            maximum=words.MAX_HINTS,
            value=0,
            style="Game.Horizontal.TProgressbar",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(0, 14))

        hints_card = tk.Frame(game_card, bg=self.colors["card_inner"], bd=0, highlightthickness=1, highlightbackground="#edf3ff", padx=12, pady=12)
        hints_card.grid(row=4, column=0, sticky="nsew")
        hints_card.grid_columnconfigure(0, weight=1)
        hints_card.grid_rowconfigure(0, weight=1)

        self.hints_text = tk.Text(
            hints_card,
            height=12,
            wrap="word",
            font=("Helvetica", 13),
            bg=self.colors["card_inner"],
            fg=self.colors["text"],
            relief="flat",
            padx=10,
            pady=10,
            insertbackground=self.colors["text"],
        )
        self.hints_text.grid(row=0, column=0, sticky="nsew")
        self.hints_text.tag_configure("rtl", justify="right", rmargin=10, lmargin1=10, lmargin2=10)
        self.hints_text.tag_configure("hint_title", foreground=self.colors["primary"], font=("Helvetica", 13, "bold"))
        self.hints_text.tag_configure("hint_points", foreground=self.colors["muted"], font=("Helvetica", 11, "bold"))
        self.hints_text.configure(state="disabled")

        # לוח הניחוש: שדה כתיבה, כפתור בדיקה והיסטוריית ניחושים.
        input_card = tk.Frame(content, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=22, pady=22)
        input_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        input_card.grid_columnconfigure(0, weight=1)
        input_card.grid_rowconfigure(5, weight=1)

        ttk.Label(input_card, text="הניחוש שלך", style="CardTitle.TLabel").grid(row=0, column=0, sticky="e")

        self.guess_var = tk.StringVar()
        self.guess_entry = tk.Entry(
            input_card,
            textvariable=self.guess_var,
            justify="right",
            font=("Helvetica", 15),
            relief="solid",
            bd=1,
            bg=self.colors["entry"],
            fg=self.colors["text"],
            highlightthickness=2,
            highlightbackground="#dbe6ff",
            highlightcolor=self.colors["primary"],
            insertbackground=self.colors["text"],
            disabledbackground="#f3f6fb",
            disabledforeground=self.colors["muted"],
        )
        self.guess_entry.grid(row=1, column=0, sticky="ew", pady=(10, 12))
        self.guess_entry.bind("<Return>", self.submit_guess)

        self.submit_button = ttk.Button(
            input_card,
            text="בדיקת ניחוש",
            style="Guess.TButton",
            command=self.submit_guess,
            state="disabled",
        )
        self.submit_button.grid(row=2, column=0, sticky="ew")

        self.reveal_button = ttk.Button(
            input_card,
            text="גלה תשובה",
            style="Next.TButton",
            command=self.reveal_answer,
            state="disabled",
        )
        self.reveal_button.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        ttk.Label(input_card, text="היסטוריית ניחושים", style="CardTitle.TLabel").grid(
            row=4, column=0, sticky="e", pady=(18, 8)
        )

        self.guesses_list = tk.Listbox(
            input_card,
            font=("Helvetica", 12),
            activestyle="none",
            relief="flat",
            bg=self.colors["list"],
            fg=self.colors["text"],
            highlightthickness=2,
            highlightbackground="#dbe6ff",
            selectbackground="#dfe8ff",
            selectforeground="#10264f",
            justify="right",
            bd=0,
        )
        self.guesses_list.grid(row=5, column=0, sticky="nsew")

        self.footer_label = ttk.Label(
            input_card,
            text="ניחוש נכון מוקדם יותר שווה יותר נקודות",
            style="Body.TLabel",
            wraplength=260,
        )
        self.footer_label.grid(row=6, column=0, sticky="sew", pady=(14, 0))

    # בונה כרטיס מדד קטן עבור הניקוד/רמזים/קטגוריה.
    def build_metric(self, parent, column, label, value):
        card = tk.Frame(parent, bg=self.colors["card_alt"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=4, pady=4)
        card.grid(row=0, column=column, sticky="ew", padx=6)
        card.grid_columnconfigure(0, weight=1)

        ttk.Label(card, text=label, style="MetricLabel.TLabel").grid(row=0, column=0, sticky="ew", pady=(10, 2))
        value_label = ttk.Label(card, text=value, style="MetricValue.TLabel")
        value_label.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=12)
        return value_label

    # Load categories from words.py and refresh category combobox values and summary.
    def populate_categories(self):
        current_label = self.category_var.get().strip()
        self.category_options = words.get_category_options()
        self.category_lookup = {label: category for category, label in self.category_options}
        labels = [label for _, label in self.category_options]
        self.category_combo["values"] = labels
        self.categories_summary.configure(
            text="כל הקטגוריות מהקובץ: " + " | ".join(labels) if labels else "לא נמצאו קטגוריות ב-data.json"
        )
        if current_label in labels:
            self.category_var.set(current_label)
        elif labels:
            self.category_combo.current(0)

    # טוען את ההגדרות האחרונות שנשמרו, אם הן עדיין תקפות.
    def load_saved_settings(self):
        settings = self.settings
        if settings.get("category") in self.category_lookup:
            self.category_var.set(settings["category"])
        if settings.get("difficulty") in DIFFICULTY_SETTINGS:
            self.difficulty_var.set(settings["difficulty"])
        if settings.get("hint_source") in ("prepared", "ai"):
            self.hint_source_var.set(settings["hint_source"])
        if settings.get("game_length") in GAME_LENGTH_OPTIONS:
            self.game_length_var.set(settings["game_length"])
        if settings.get("player_name"):
            self.player_name_var.set(settings["player_name"])
        self.practice_mode_var.set(bool(settings.get("practice_mode", False)))
        self.timer_enabled_var.set(bool(settings.get("timer_enabled", True)))

    # שומר את ההגדרות שנבחרו כך שהאפליקציה תיפתח איתן בפעם הבאה.
    def save_current_settings(self):
        write_json_file(SETTINGS_FILE, {
            "category": self.category_var.get().strip(),
            "difficulty": self.difficulty_var.get(),
            "hint_source": self.hint_source_var.get(),
            "game_length": self.game_length_var.get(),
            "player_name": self.player_name_var.get().strip() or "שחקן",
            "practice_mode": self.practice_mode_var.get(),
            "timer_enabled": self.timer_enabled_var.get(),
        })

    # מתרגם את בחירת אורך המשחק למספר סבבים או None לכל הקטגוריה.
    def get_selected_game_length(self):
        value = self.game_length_var.get()
        return None if value == GAME_LENGTH_OPTIONS[0] else int(value)

    # מציג את מסך הבית ומסתיר את מסך המשחק.
    def show_home_screen(self):
        self.home_screen.tkraise()
        self.root.title("Alias AI - בית")

    # מציג את מסך המשחק אחרי שההגדרות נבחרו.
    def show_game_screen(self):
        self.game_screen.tkraise()
        self.root.title("Alias AI - משחק")

    # חוזר למסך הבית, עם אישור אם סבב עדיין פעיל.
    def return_home(self):
        if self.secret_word and not self.round_finished:
            should_return = messagebox.askyesno("חזרה לבית", "המשחק הפעיל ייעצר. לחזור למסך הבית?")
            if not should_return:
                return
        self.stop_timer()
        self.ai_request_id += 1
        self.secret_word = None
        self.all_hints = []
        self.revealed_hints = []
        self.attempts_used = 0
        self.round_finished = True
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.set_setup_controls_state("normal")
        self.refresh_metrics()
        self.refresh_hints()
        self.show_home_screen()

    # מציג את השיאים האחרונים והשיאים הגבוהים ביותר.
    def show_high_scores(self):
        scores = read_json_file(SCORES_FILE, [])
        if not scores:
            messagebox.showinfo("שיאים", "עדיין אין שיאים שמורים.")
            return
        best_scores = sorted(scores, key=lambda item: item.get("score", 0), reverse=True)[:10]
        lines = []
        for index, score in enumerate(best_scores, start=1):
            lines.append(
                f"{index}. {score.get('player', 'שחקן')} | {score.get('score', 0)} נקודות | "
                f"{score.get('category', '')} | {score.get('difficulty', '')}"
            )
        messagebox.showinfo("שיאים", "\n".join(lines))

    # מציג סטטיסטיקה מצטברת לפי קטגוריה.
    def show_category_stats(self):
        stats = read_json_file(STATS_FILE, {})
        if not stats:
            messagebox.showinfo("סטטיסטיקה", "עדיין אין סטטיסטיקה שמורה.")
            return
        lines = []
        for category, data in stats.items():
            played = data.get("played", 0)
            correct = data.get("correct", 0)
            success_rate = (correct / played * 100) if played else 0
            lines.append(
                f"{category}: {correct}/{played} נכונות ({success_rate:.0f}%), "
                f"שיא {data.get('best_score', 0)}"
            )
        messagebox.showinfo("סטטיסטיקה לפי קטגוריה", "\n".join(lines))

    # מערבב את המילים בקטגוריה כדי שכל משחק יהיה בסדר שונה.
    def build_rounds(self, category):
        entries = list(words.get_words_by_category(category).items())
        self.randomizer.shuffle(entries)
        return entries

    # מחזיר את המילה הבאה שלא השתמשנו בה עדיין במשחק הנוכחי.
    def get_next_entry(self):
        if self.max_rounds is not None and self.round_number >= self.max_rounds:
            return None, None
        entries = self.build_rounds(self.current_category)
        available_entries = [(word, hints) for word, hints in entries if word not in self.used_words]
        if not available_entries:
            return None, None
        word, hints = available_entries[0]
        self.used_words.add(word)
        return word, hints

    # מכין את רשימת הרמזים לסבב: מוכנים מראש או משופרים על ידי AI.
    def build_hints_for_current_round(self):
        prepared_hints = words.order_hints_by_difficulty(self.all_hints)
        return prepared_hints

    # מחזיר את הגדרות הקושי הנוכחיות, עם ברירת מחדל יציבה.
    def get_difficulty_settings(self):
        return DIFFICULTY_SETTINGS.get(self.difficulty_var.get(), DIFFICULTY_SETTINGS["רגיל"])

    # מחשב ניקוד לסבב לפי מספר הרמזים שנפתחו ורמת הקושי.
    def get_points_for_current_difficulty(self, hint_number):
        return words.get_points_for_hint_number(hint_number) + self.get_difficulty_settings()["score_bonus"]

    # מפעיל קריאת Ollama ברקע כדי שהממשק הגרפי לא יקפא בזמן יצירת הרמזים.
    def start_ai_hint_generation(self, prepared_hints):
        self.ai_request_id += 1
        request_id = self.ai_request_id
        word = self.secret_word
        category_label = words.get_category_label(self.current_category)
        prepared_hints = list(prepared_hints)
        self.set_round_controls_state("disabled")
        self.skip_button.configure(state="normal")
        self.set_status("מכין רמזי AI לסבב הזה...")

        def worker():
            ai_hints = generate_ai_hints(word, prepared_hints, category_label)
            filtered_hints = filter_duplicate_ai_hints(ai_hints, prepared_hints)
            self.root.after(0, lambda: self.finish_ai_hint_generation(request_id, filtered_hints))

        threading.Thread(target=worker, daemon=True).start()

    # מחיל את תוצאת ה-AI אם היא עדיין שייכת לסבב הנוכחי.
    def finish_ai_hint_generation(self, request_id, ai_hints):
        if request_id != self.ai_request_id or self.round_finished or not self.secret_word:
            return
        if ai_hints:
            self.all_hints = ai_hints
            self.reveal_starting_hints()
            self.set_status("רמזי AI מוכנים. תנסה לנחש!")
        else:
            self.set_status("ה-AI לא עובד כרגע, אז הסבב ממשיך עם הרמזים המוכנים.")
            messagebox.showwarning("AI לא זמין", "ה-AI לא עובד כרגע, אז הסבב ממשיך עם הרמזים המוכנים.")
        self.refresh_hints()
        self.refresh_metrics()
        self.set_round_controls_state("normal")
        self.start_timer()
        self.guess_entry.focus_set()

    # מתחיל משחק חדש בקטגוריה שנבחרה ומאפס ניקוד ומילים שכבר שוחקו.
    def start_game(self):
        self.populate_categories()
        selected_label = self.category_var.get().strip()
        if not selected_label:
            messagebox.showwarning("קטגוריה חסרה", "בחר קטגוריה לפני תחילת המשחק.")
            return

        self.current_category = self.category_lookup[selected_label]
        self.save_current_settings()
        self.set_setup_controls_state("disabled")
        self.show_game_screen()
        self.score = 0
        self.round_number = 0
        self.max_rounds = self.get_selected_game_length()
        self.used_words = set()
        self.correct_words = 0
        self.failed_words = 0
        self.skipped_words = 0
        self.total_hints_used = 0
        self.round_results = []
        self.last_summary = ""
        self.next_round()

    # Proceed to the next round, choose the next word, and show the first hint.
    def next_round(self):
        self.stop_timer()
        self.ai_request_id += 1
        self.populate_categories()
        if not self.current_category:
            return

        self.secret_word, hints = self.get_next_entry()
        if not self.secret_word:
            self.finish_game()
            return

        self.round_number += 1
        self.all_hints = words.order_hints_by_difficulty(hints)
        self.all_hints = self.build_hints_for_current_round()
        self.revealed_hints = []
        self.attempts_used = 0
        self.round_finished = False
        self.time_left = self.get_difficulty_settings()["seconds"] if self.timer_enabled_var.get() else 0
        self.guess_var.set("")
        self.guesses_list.delete(0, tk.END)
        self.reveal_starting_hints()
        self.set_status("!הרמז הראשון מוכן. תנסה לנחש")
        self.update_round_title()
        self.refresh_hints()
        self.refresh_metrics()
        self.next_button.configure(state="disabled")
        self.skip_button.configure(state="normal")
        self.reveal_button.configure(state="normal")
        if self.hint_source_var.get() == "ai":
            self.start_ai_hint_generation(self.all_hints)
        else:
            self.set_round_controls_state("normal")
            self.start_timer()
            self.guess_entry.focus_set()

    # מסיים את המשחק כאשר נגמרו המילים בקטגוריה.
    def finish_game(self):
        self.stop_timer()
        self.secret_word = None
        self.all_hints = []
        self.revealed_hints = []
        self.attempts_used = 0
        self.round_finished = True
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.set_setup_controls_state("normal")
        self.refresh_hints()
        self.refresh_metrics()
        self.round_title.configure(text="המשחק הסתיים")
        summary = self.build_game_summary()
        self.last_summary = summary
        self.save_game_records()
        self.set_status(f"סיימת את הקטגוריה עם {self.score} נקודות.")
        messagebox.showinfo("סיום משחק", summary)
        self.show_home_screen()

    # בונה הודעת סיכום עשירה יותר לסוף המשחק.
    def build_game_summary(self):
        played_rounds = self.correct_words + self.failed_words + self.skipped_words
        average_hints = self.total_hints_used / played_rounds if played_rounds else 0
        result_lines = []
        for result in self.round_results:
            result_label = {
                "correct": "נכון",
                "failed": "לא נוחש",
                "skipped": "דולג",
                "revealed": "נחשף",
            }.get(result["result"], result["result"])
            result_lines.append(f"- {result['word']}: {result_label}, {result['hints']} רמזים")
        details = "\n\nפירוט מילים:\n" + "\n".join(result_lines) if result_lines else ""
        return (
            f"המשחק הסתיים עם {self.score} נקודות.\n\n"
            f"שחקן: {self.player_name_var.get().strip() or 'שחקן'}\n"
            f"קטגוריה: {words.get_category_label(self.current_category) if self.current_category else ''}\n"
            f"רמת קושי: {self.difficulty_var.get()}\n"
            f"טיימר: {'פעיל' if self.timer_enabled_var.get() else 'כבוי'}\n"
            f"מצב: {'אימון' if self.practice_mode_var.get() else 'ניקוד'}\n\n"
            f"מילים שנוחשו נכון: {self.correct_words}\n"
            f"מילים שלא נוחשו: {self.failed_words}\n"
            f"מילים שדולגו: {self.skipped_words}\n"
            f"ממוצע רמזים למילה: {average_hints:.1f}"
            f"{details}"
        )

    # שומר שיאים וסטטיסטיקה לאחר משחק מלא.
    def save_game_records(self):
        category_label = words.get_category_label(self.current_category) if self.current_category else ""
        played_rounds = self.correct_words + self.failed_words + self.skipped_words
        if not played_rounds:
            return

        if not self.practice_mode_var.get():
            scores = read_json_file(SCORES_FILE, [])
            scores.append({
                "player": self.player_name_var.get().strip() or "שחקן",
                "score": self.score,
                "category": category_label,
                "difficulty": self.difficulty_var.get(),
                "rounds": played_rounds,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            write_json_file(SCORES_FILE, scores[-100:])

        stats = read_json_file(STATS_FILE, {})
        current = stats.setdefault(category_label, {
            "played": 0,
            "correct": 0,
            "failed": 0,
            "skipped": 0,
            "best_score": 0,
        })
        current["played"] += played_rounds
        current["correct"] += self.correct_words
        current["failed"] += self.failed_words
        current["skipped"] += self.skipped_words
        current["best_score"] = max(current.get("best_score", 0), self.score)
        write_json_file(STATS_FILE, stats)

    # מייצא את הסיכום האחרון לקובץ טקסט.
    def export_last_summary(self):
        if not self.last_summary:
            messagebox.showinfo("ייצוא סיכום", "אין עדיין סיכום משחק לייצוא.")
            return
        EXPORTS_DIR.mkdir(exist_ok=True)
        path = EXPORTS_DIR / f"alias-summary-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        path.write_text(self.last_summary + "\n", encoding="utf-8")
        messagebox.showinfo("ייצוא סיכום", f"הסיכום נשמר בקובץ:\n{path}")

    # מזהה ניחוש קרוב מספיק כדי לתת פידבק בלי לפתוח רמז נוסף.
    def is_close_guess(self, guess):
        normalized_guess = words.normalize_guess(guess)
        normalized_word = words.normalize_guess(self.secret_word or "")
        if len(normalized_guess) < 3 or len(normalized_word) < 3:
            return False
        return difflib.SequenceMatcher(None, normalized_guess, normalized_word).ratio() >= 0.74

    # Handle guess submission: validate, score, reveal hints, end round if needed.
    def submit_guess(self, event=None):
        if self.round_finished or not self.secret_word:
            return

        guess = self.guess_var.get().strip()
        if not guess:
            self.set_status("!צריך לכתוב ניחוש לפני שבודקים")
            return

        normalized_guess = words.normalize_guess(guess)
        normalized_word = words.normalize_guess(self.secret_word)
        if normalized_guess != normalized_word and self.is_close_guess(guess):
            self.guesses_list.insert(0, f"{guess} - קרוב")
            self.guess_var.set("")
            self.set_status("קרוב מאוד! נסה לדייק בלי לפתוח רמז נוסף.")
            self.play_feedback("warning")
            self.guess_entry.focus_set()
            return

        self.attempts_used += 1
        self.guesses_list.insert(0, guess)

        if normalized_guess == normalized_word:
            points = self.get_points_for_current_difficulty(len(self.revealed_hints))
            if self.practice_mode_var.get():
                points = 0
            self.score += points
            self.round_finished = True
            self.correct_words += 1
            self.total_hints_used += len(self.revealed_hints)
            self.round_results.append({"word": self.secret_word, "result": "correct", "hints": len(self.revealed_hints)})
            self.stop_timer()
            if self.practice_mode_var.get():
                self.set_status(f"בול! מצב אימון לא נותן ניקוד. המילה הייתה: {self.secret_word}!")
            else:
                self.set_status(f"בול! קיבלת {points} נקודות. המילה הייתה: {self.secret_word}!")
            self.play_feedback("success")
            self.submit_button.configure(state="disabled")
            self.next_button.configure(state="normal")
            self.skip_button.configure(state="disabled")
            self.reveal_button.configure(state="disabled")
            self.guess_entry.configure(state="disabled")
            self.refresh_metrics()
            return

        if self.attempts_used >= self.get_difficulty_settings()["max_attempts"]:
            self.end_round_without_success("לא הצלחת אחרי כל הניסיונות")
            return
        next_hint_index = len(self.revealed_hints)
        if next_hint_index < len(self.all_hints):
            self.revealed_hints.append(self.all_hints[next_hint_index])

        self.guess_var.set("")
        self.set_status(".לא נכון. נפתח רמז נוסף, קצת יותר קל")
        self.refresh_hints()
        self.refresh_metrics()
        self.guess_entry.focus_set()

    # מדלג על הסבב הנוכחי וממשיך למילה הבאה בלי לתת ניקוד.
    def skip_round(self):
        if self.round_finished or not self.secret_word:
            return
        word = self.secret_word
        self.round_finished = True
        self.skipped_words += 1
        self.total_hints_used += len(self.revealed_hints)
        self.round_results.append({"word": word, "result": "skipped", "hints": len(self.revealed_hints)})
        self.stop_timer()
        self.set_status(f"דילגת על המילה: {word}")
        self.play_feedback("warning")
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="normal")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.refresh_metrics()

    # מגלה את התשובה ומסיים את הסבב בלי ניקוד.
    def reveal_answer(self):
        if self.round_finished or not self.secret_word:
            return
        word = self.secret_word
        self.round_finished = True
        self.failed_words += 1
        self.total_hints_used += len(self.revealed_hints)
        self.round_results.append({"word": word, "result": "revealed", "hints": len(self.revealed_hints)})
        self.stop_timer()
        self.set_status(f"התשובה היא: {word}")
        self.play_feedback("warning")
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="normal")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.refresh_metrics()

    # מסיים סבב אחרי כישלון, בלי לשכפל קוד בין זמן שנגמר וניסיונות שנגמרו.
    def end_round_without_success(self, reason):
        if self.round_finished:
            return
        word = self.secret_word
        self.round_finished = True
        self.failed_words += 1
        self.total_hints_used += len(self.revealed_hints)
        self.round_results.append({"word": word, "result": "failed", "hints": len(self.revealed_hints)})
        self.stop_timer()
        self.set_status(f"{reason}. המילה הייתה: {word}")
        self.play_feedback("error")
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="normal")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.refresh_metrics()

    # פותח רמזים התחלתיים לפי רמת הקושי.
    def reveal_starting_hints(self):
        self.revealed_hints = []
        hints_to_reveal = self.get_difficulty_settings()["start_hints"]
        for hint in self.all_hints[:hints_to_reveal]:
            self.revealed_hints.append(hint)

    # מפעיל/מכבה את אזור הניחוש בזמן טעינת AI או סיום סבב.
    def set_round_controls_state(self, state):
        self.submit_button.configure(state=state)
        self.guess_entry.configure(state=state)

    # נועל הגדרות משחק אחרי ההתחלה כדי שהן יהיו בחירה של תחילת משחק בלבד.
    def set_setup_controls_state(self, state):
        readonly_state = "readonly" if state == "normal" else "disabled"
        self.category_combo.configure(state=readonly_state)
        self.difficulty_combo.configure(state=readonly_state)
        self.game_length_combo.configure(state=readonly_state)
        self.player_entry.configure(state=state)
        self.prepared_hints_radio.configure(state=state)
        self.ai_hints_radio.configure(state=state)
        self.practice_check.configure(state=state)
        self.timer_check.configure(state=state)
        self.start_button.configure(state=state)

    # מתחיל טיימר חדש לסבב הנוכחי.
    def start_timer(self):
        self.stop_timer()
        self.refresh_metrics()
        if not self.timer_enabled_var.get():
            return
        self.timer_after_id = self.root.after(1000, self.tick_timer)

    # עוצר את הטיימר הפעיל, אם קיים.
    def stop_timer(self):
        if self.timer_after_id:
            self.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None

    # מוריד שנייה מהטיימר ומסיים את הסבב אם הזמן נגמר.
    def tick_timer(self):
        if self.round_finished or not self.secret_word:
            self.timer_after_id = None
            return
        self.time_left -= 1
        self.refresh_metrics()
        if self.time_left <= 0:
            self.timer_after_id = None
            self.end_round_without_success("נגמר הזמן")
            return
        self.timer_after_id = self.root.after(1000, self.tick_timer)

    # מעדכן את כותרת הסבב לפי מספר הסבב והקטגוריה.
    def update_round_title(self):
        category_label = words.get_category_label(self.current_category) if self.current_category else "ללא קטגוריה"
        self.round_title.configure(text=f"סבב {self.round_number} | {category_label}")

    # מציג הודעת מצב בצבע מתאים לפי סוג האירוע.
    def set_status(self, text):
        bg = "#eef6ff"
        fg = self.colors["info"]
        if "בול" in text or "נקודות" in text:
            bg = "#e8f8ef"
            fg = self.colors["success"]
        elif "לא הצלחת" in text or "צריך לכתוב" in text or "נגמר הזמן" in text:
            bg = "#fff0ee"
            fg = self.colors["error"]
        elif "לא נכון" in text or "דילגת" in text:
            bg = "#fff6e7"
            fg = self.colors["warning"]
        elif "קרוב" in text or "התשובה היא" in text:
            bg = "#fff6e7"
            fg = self.colors["warning"]

        self.status_box.configure(text=text, bg=bg, fg=fg)

    # נותן פידבק קטן של צליל וצבע אחרי אירוע חשוב.
    def play_feedback(self, kind):
        try:
            self.root.bell()
        except tk.TclError:
            pass
        flash_color = {
            "success": "#d9fbe8",
            "warning": "#fff1c2",
            "error": "#ffd9d4",
        }.get(kind, "#eef6ff")
        if self.animation_after_id:
            self.root.after_cancel(self.animation_after_id)
        original = self.status_box.cget("bg")
        self.status_box.configure(bg=flash_color)
        self.animation_after_id = self.root.after(220, lambda: self.status_box.configure(bg=original))

    # מרענן את המדדים שמוצגים מעל אזור המשחק.
    def refresh_metrics(self):
        category_text = words.get_category_label(self.current_category) if self.current_category else "עדיין לא נבחרה"
        self.score_value.configure(text=str(self.score))
        self.hints_value.configure(text=f"{len(self.revealed_hints)}/{words.MAX_HINTS}")
        if not self.secret_word:
            timer_text = "--"
        elif not self.timer_enabled_var.get():
            timer_text = "ללא"
        else:
            timer_text = f"{self.time_left}s"
        self.timer_value.configure(text=timer_text)
        self.category_value.configure(text=category_text)
        self.progress.configure(maximum=self.get_difficulty_settings()["max_attempts"], value=self.attempts_used)

    # מציג את כל הרמזים שנפתחו עד עכשיו בתוך תיבת הטקסט.
    def refresh_hints(self):
        self.hints_text.configure(state="normal")
        self.hints_text.delete("1.0", tk.END)

        if not self.revealed_hints:
            self.hints_text.insert("1.0", "כאן יופיעו הרמזים של הסבב")
            self.hints_text.tag_add("rtl", "1.0", "end")
            
            self.hints_text.configure(state="disabled")
            return

        for index, hint in enumerate(self.revealed_hints, start=1):
            points = self.get_points_for_current_difficulty(index)
            start = self.hints_text.index("end-1c")
            self.hints_text.insert("end", f"רמז {index}\n")
            self.hints_text.insert("end", f"{hint}\n")
            self.hints_text.insert("end", f"נקודות בשלב הזה: {points}\n\n")
            end = self.hints_text.index("end-1c")
            self.hints_text.tag_add("rtl", start, end)

        content = self.hints_text.get("1.0", "end-1c")
        lines = content.splitlines()
        current_index = "1.0"
        for line in lines:
            line_end = f"{current_index} lineend"
            if line.startswith("רמז "):
                self.hints_text.tag_add("hint_title", current_index, line_end)
            elif line.startswith("נקודות בשלב הזה:"):
                self.hints_text.tag_add("hint_points", current_index, line_end)
            current_index = self.hints_text.index(f"{current_index} +1 line")

        self.hints_text.tag_add("rtl", "1.0", "end")
        self.hints_text.configure(state="disabled")

    # מצב פתיחה לפני שהמשתמש התחיל סבב.
    def render_intro_state(self):
        self.refresh_metrics()
        self.refresh_hints()
        self.guess_entry.configure(state="disabled")
        self.skip_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self.show_home_screen()


# Entry point: initialize TK root and launch the AliasGameApp.
def main():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"לא ניתן לפתוח חלון גרפי: {error}")
        print("נסה להריץ את הקובץ מסביבה גרפית רגילה על המחשב.")
        sys.exit(1)

    print("Alias AI נפתח בחלון חדש. כדי לסיים, סוגרים את החלון.")
    AliasGameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
