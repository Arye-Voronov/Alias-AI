import random

import sys
import tkinter as tk
from tkinter import messagebox, ttk
import words
# AliasGameApp implements the full Alias guessing game UI and logic.
class AliasGameApp:
    # Initialize app state, UI styles, and starting state when constructed.
    def __init__(self, root):
        self.colors = {
            "bg": "#eef4ff",
            "hero": "#dfeaff",
            "hero_accent": "#7c9cff",
            "card": "#f9fbff",
            "card_alt": "#eef3ff",
            "card_inner": "#ffffff",
            "text": "#122033",
            "muted": "#6b7a90",
            "primary": "#0a84ff",
            "primary_hover": "#0066d6",
            "success": "#30b05f",
            "error": "#ff6b57",
            "info": "#5e7cff",
            "border": "#d6e3ff",
            "entry": "#ffffff",
            "list": "#ffffff",
            "shadow": "#c9d8f7",
            "warning": "#ffb340",
        }
        self.root = root
        self.root.title("Alias AI")
        self.root.geometry("980x720")
        self.root.minsize(820, 620)
        self.root.configure(bg=self.colors["bg"])

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

        self.configure_styles()
        self.build_layout()
        self.populate_categories()
        self.render_intro_state()

    # Configure all ttk style themes and widget visual styles used by the app.
    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"], relief="flat")
        style.configure("Hero.TFrame", background=self.colors["hero"], relief="flat")
        style.configure(
            "Title.TLabel",
            background=self.colors["hero"],
            foreground=self.colors["text"],
            font=("Helvetica", 30, "bold"),
            anchor="e",
            justify="right",
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.colors["hero"],
            foreground=self.colors["muted"],
            font=("Helvetica", 12),
            anchor="e",
            justify="right",
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=("Helvetica", 15, "bold"),
            anchor="e",
            justify="right",
        )
        style.configure(
            "Body.TLabel",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=("Helvetica", 12),
            anchor="e",
            justify="right",
        )
        style.configure(
            "MetricValue.TLabel",
            background=self.colors["card_alt"],
            foreground=self.colors["text"],
            font=("Helvetica", 21, "bold"),
            anchor="center",
            justify="center",
        )
        style.configure(
            "MetricLabel.TLabel",
            background=self.colors["card_alt"],
            foreground=self.colors["info"],
            font=("Helvetica", 10, "bold"),
            anchor="center",
            justify="center",
        )
        style.configure("Start.TButton", font=("Helvetica", 12, "bold"), padding=(18, 12), background=self.colors["primary"], foreground="#ffffff", borderwidth=0)
        style.map("Start.TButton", background=[("active", self.colors["primary_hover"])], foreground=[("disabled", "#d7e8ff")])
        style.configure("Next.TButton", font=("Helvetica", 12, "bold"), padding=(18, 12), background=self.colors["success"], foreground="#ffffff", borderwidth=0)
        style.map("Next.TButton", background=[("active", "#25984f")], foreground=[("disabled", "#d7f5e1")])
        style.configure("Guess.TButton", font=("Helvetica", 13, "bold"), padding=(18, 14), background=self.colors["hero_accent"], foreground="#ffffff", borderwidth=0)
        style.map("Guess.TButton", background=[("active", "#5a7eff")], foreground=[("disabled", "#e0e8ff")])
        style.configure(
            "Game.Horizontal.TProgressbar",
            troughcolor="#e5edff",
            background=self.colors["hero_accent"],
            bordercolor="#e5edff",
            lightcolor=self.colors["hero_accent"],
            darkcolor=self.colors["hero_accent"],
            thickness=12,
        )

    # Build the GUI layout with frames, buttons, labels and interactive widgets.
    def build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, style="App.TFrame", padding=20)
        outer.grid(sticky="nsew")
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(3, weight=1)

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
            text="משחק ניחוש מילים עם רמזים שמתחילים קשים והופכים קלים יותר בכל ניסיון.",
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

        controls_card = tk.Frame(outer, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=20, pady=20)
        controls_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        controls_card.grid_columnconfigure(0, weight=1)
        controls_card.grid_columnconfigure(1, weight=1)
        controls_card.grid_columnconfigure(2, weight=0)
        controls_card.grid_columnconfigure(3, weight=0)

        ttk.Label(controls_card, text="קטגוריה", style="CardTitle.TLabel").grid(
            row=0, column=3, sticky="e", padx=(12, 0)
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
        self.start_button.grid(row=0, column=1, sticky="ew", padx=(12, 0))

        self.next_button = ttk.Button(
            controls_card,
            text="למילה הבאה",
            style="Next.TButton",
            command=self.next_round,
            state="disabled",
        )
        self.next_button.grid(row=0, column=0, sticky="ew")

        self.categories_summary = tk.Label(
            controls_card,
            text="",
            bg=self.colors["card"],
            fg=self.colors["muted"],
            font=("Helvetica", 11),
            anchor="e",
            justify="right",
        )
        self.categories_summary.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(14, 0))

        metrics = ttk.Frame(outer, style="App.TFrame")
        metrics.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for index in range(3):
            metrics.grid_columnconfigure(index, weight=1)

        self.score_value = self.build_metric(metrics, 0, "ניקוד", "0")
        self.hints_value = self.build_metric(metrics, 1, "רמזים פתוחים", f"0/{words.MAX_HINTS}")
        self.category_value = self.build_metric(metrics, 2, "קטגוריה", "עדיין לא נבחרה")

        content = ttk.Frame(outer, style="App.TFrame")
        content.grid(row=3, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        game_card = tk.Frame(content, bg=self.colors["card"], bd=0, highlightthickness=1, highlightbackground="#ffffff", padx=22, pady=22)
        game_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        game_card.grid_columnconfigure(0, weight=1)
        game_card.grid_rowconfigure(4, weight=1)

        self.round_title = ttk.Label(game_card, text="מוכנים להתחיל?", style="CardTitle.TLabel")
        self.round_title.grid(row=0, column=0, sticky="e")

        self.status_box = tk.Label(
            game_card,
            text="בחר קטגוריה ולחץ על התחל משחק כדי לקבל את הרמז הראשון.",
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
            highlightthickness=2,
            highlightbackground="#dbe6ff",
            highlightcolor=self.colors["primary"],
            insertbackground=self.colors["text"],
            disabledbackground="#f3f6fb",
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

        ttk.Label(input_card, text="היסטוריית ניחושים", style="CardTitle.TLabel").grid(
            row=3, column=0, sticky="e", pady=(18, 8)
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
        self.guesses_list.grid(row=4, column=0, sticky="nsew")

        self.footer_label = ttk.Label(
            input_card,
            text="ניחוש נכון מוקדם יותר שווה יותר נקודות.",
            style="Body.TLabel",
            wraplength=260,
        )
        self.footer_label.grid(row=5, column=0, sticky="sew", pady=(14, 0))

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

    def build_rounds(self, category):
        entries = list(words.get_words_by_category(category).items())
        self.randomizer.shuffle(entries)
        return entries

    def get_next_entry(self):
        entries = self.build_rounds(self.current_category)
        available_entries = [(word, hints) for word, hints in entries if word not in self.used_words]
        if not available_entries:
            return None, None
        word, hints = available_entries[0]
        self.used_words.add(word)
        return word, hints

    def start_game(self):
        self.populate_categories()
        selected_label = self.category_var.get().strip()
        if not selected_label:
            messagebox.showwarning("קטגוריה חסרה", "בחר קטגוריה לפני תחילת המשחק.")
            return

        self.current_category = self.category_lookup[selected_label]
        self.score = 0
        self.round_number = 0
        self.used_words = set()
        self.next_round()

    # Proceed to the next round, choose the next word, and show the first hint.
    def next_round(self):
        self.populate_categories()
        if not self.current_category:
            return

        self.secret_word, hints = self.get_next_entry()
        if not self.secret_word:
            self.finish_game()
            return

        self.round_number += 1
        self.all_hints = words.order_hints_by_difficulty(hints)
        self.revealed_hints = self.all_hints[:1]
        self.attempts_used = 0
        self.round_finished = False
        self.guess_var.set("")
        self.guesses_list.delete(0, tk.END)
        self.set_status("הרמז הראשון מוכן. תנסה לנחש.")
        self.update_round_title()
        self.refresh_hints()
        self.refresh_metrics()
        self.submit_button.configure(state="normal")
        self.next_button.configure(state="disabled")
        self.guess_entry.configure(state="normal")
        self.guess_entry.focus_set()

    def finish_game(self):
        self.secret_word = None
        self.all_hints = []
        self.revealed_hints = []
        self.attempts_used = 0
        self.round_finished = True
        self.submit_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        self.guess_entry.configure(state="disabled")
        self.refresh_hints()
        self.refresh_metrics()
        self.round_title.configure(text="המשחק הסתיים")
        self.set_status(f"סיימת את הקטגוריה עם {self.score} נקודות.")
        messagebox.showinfo("סיום משחק", f"המשחק הסתיים עם {self.score} נקודות.")

    # Handle guess submission: validate, score, reveal hints, end round if needed.
    def submit_guess(self, event=None):
        if self.round_finished or not self.secret_word:
            return

        guess = self.guess_var.get().strip()
        if not guess:
            self.set_status("צריך לכתוב ניחוש לפני שבודקים.")
            return

        self.attempts_used += 1
        self.guesses_list.insert(0, guess)

        if words.normalize_guess(guess) == words.normalize_guess(self.secret_word):
            points = words.get_points_for_hint_number(len(self.revealed_hints))
            self.score += points
            self.round_finished = True
            self.set_status(f"בול! קיבלת {points} נקודות. המילה הייתה: {self.secret_word}")
            self.submit_button.configure(state="disabled")
            self.next_button.configure(state="normal")
            self.guess_entry.configure(state="disabled")
            self.refresh_metrics()
            return

        if self.attempts_used >= words.MAX_HINTS:
            self.round_finished = True
            self.set_status(f"לא הצלחת אחרי 5 רמזים. המילה הייתה: {self.secret_word}")
            self.submit_button.configure(state="disabled")
            self.next_button.configure(state="normal")
            self.guess_entry.configure(state="disabled")
            self.refresh_metrics()
            return
        next_hint_count = min(self.attempts_used + 1, len(self.all_hints))
        self.revealed_hints = self.all_hints[:next_hint_count]

        self.guess_var.set("")
        self.set_status("לא נכון. נפתח רמז נוסף, קצת יותר קל.")
        self.refresh_hints()
        self.refresh_metrics()
        self.guess_entry.focus_set()

    def update_round_title(self):
        category_label = words.get_category_label(self.current_category) if self.current_category else "ללא קטגוריה"
        self.round_title.configure(text=f"סבב {self.round_number} | {category_label}")

    def set_status(self, text):
        lower_text = text.lower()
        bg = "#eef6ff"
        fg = self.colors["info"]
        if "בול" in text or "נקודות" in text:
            bg = "#e8f8ef"
            fg = self.colors["success"]
        elif "לא הצלחת" in text or "צריך לכתוב" in text:
            bg = "#fff0ee"
            fg = self.colors["error"]
        elif "לא נכון" in text:
            bg = "#fff6e7"
            fg = self.colors["warning"]

        self.status_box.configure(text=text, bg=bg, fg=fg)

    def refresh_metrics(self):
        category_text = words.get_category_label(self.current_category) if self.current_category else "עדיין לא נבחרה"
        self.score_value.configure(text=str(self.score))
        self.hints_value.configure(text=f"{len(self.revealed_hints)}/{words.MAX_HINTS}")
        self.category_value.configure(text=category_text)
        self.progress.configure(value=self.attempts_used)

    def refresh_hints(self):
        self.hints_text.configure(state="normal")
        self.hints_text.delete("1.0", tk.END)

        if not self.revealed_hints:
            self.hints_text.insert("1.0", "כאן יופיעו הרמזים של הסבב.")
            self.hints_text.tag_add("rtl", "1.0", "end")
            self.hints_text.configure(state="disabled")
            return

        for index, hint in enumerate(self.revealed_hints, start=1):
            points = words.get_points_for_hint_number(index)
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

    def render_intro_state(self):
        self.refresh_metrics()
        self.refresh_hints()
        self.guess_entry.configure(state="disabled")


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
