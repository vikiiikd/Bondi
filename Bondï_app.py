import json
import hashlib
import os
from datetime import date, datetime, timedelta
from typing import Optional
import csv
import subprocess
import platform

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# =====================================================
# Storage & Core Helpers
# =====================================================

DATABASE_FILE = "datasets/users_data.json"
USERS_CSV_FILE = "datasets/users.csv"
EXPENSES_CSV_FILE = "datasets/expenses.csv"
GOALS_CSV_FILE = "datasets/goals.csv"
PODS_CSV_FILE = "datasets/pods.csv"
SHARED_EXPENSES_CSV_FILE = "datasets/shared_expenses.csv"


def open_video(path: str):
    """Open a local video file (.mp4) with the system’s default player."""
    if platform.system() == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])


# =====================================================
# Simple Hash Table (Hash Set for strings)
# =====================================================


class SimpleHashSet:
    """Very small hash set using separate chaining for string keys."""

    def __init__(self, capacity: int = 101):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]

    def _index(self, key: str) -> int:
        return hash(key) % self.capacity

    def add(self, key: str) -> bool:
        """Insert key if not present. Return True if inserted, False if duplicate."""
        idx = self._index(key)
        bucket = self.buckets[idx]

        for existing in bucket:
            if existing == key:
                return False

        bucket.append(key)
        return True

    def contains(self, key: str) -> bool:
        """Return True if key is stored in the set."""
        idx = self._index(key)
        bucket = self.buckets[idx]
        for existing in bucket:
            if existing == key:
                return True
        return False

    def to_list(self):
        """Return a flat list of all keys in the set."""
        result = []
        for bucket in self.buckets:
            result.extend(bucket)
        return result


# =====================================================
# Search Algorithms
# =====================================================


def binary_search(sorted_items, target):
    """Binary search over a sorted list; return index or None."""
    first = 0
    last = len(sorted_items) - 1

    while first <= last:
        mid = (first + last) // 2
        mid_elem = sorted_items[mid]

        if mid_elem == target:
            return mid
        elif mid_elem < target:
            first = mid + 1
        else:
            last = mid - 1

    return None


def selection_sort(items):
    """Selection sort (O(n²)). Return new sorted list."""
    items = items[:]
    n = len(items)
    for i in range(n):
        smallest_index = i
        for j in range(i + 1, n):
            if items[j] < items[smallest_index]:
                smallest_index = j
        items[i], items[smallest_index] = items[smallest_index], items[i]
    return items


# =====================================================
# Recursion + Divide & Conquer (Quicksort)
# =====================================================


def quicksort_expenses_by_amount(expenses):
    """Quicksort-style recursive sort of expenses by 'amount' (descending)."""
    if len(expenses) < 2:
        return expenses[:]

    pivot = expenses[0]
    pivot_amount = pivot["amount"]

    higher = [e for e in expenses[1:] if e["amount"] > pivot_amount]
    lower_or_equal = [e for e in expenses[1:] if e["amount"] <= pivot_amount]

    return (
        quicksort_expenses_by_amount(higher)
        + [pivot]
        + quicksort_expenses_by_amount(lower_or_equal)
    )


# =====================================================
# Hash / Encoding helpers
# =====================================================


def hash_text(text: str) -> str:
    """Return a SHA-256 hash of the given string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode_text(plain_text: str) -> str:
    """
    Convert text into a space-separated sequence of Unicode code points.
    Example: 'Ana' -> '65 110 97'
    """
    plain_text = str(plain_text)
    return " ".join(str(ord(ch)) for ch in plain_text)


def decode_text(encoded_text: str) -> str:
    """Convert space-separated Unicode numbers back into normal text."""
    if not encoded_text:
        return ""
    chars = []
    for num_str in encoded_text.split():
        code_num = int(num_str)
        chars.append(chr(code_num))
    return "".join(chars)


def maybe_decode_text(encoded_text: str) -> str:
    """
    Try to interpret a string as space-separated code points.
    If it fails, return the original string (for old, non-encoded data).
    """
    if not encoded_text:
        return ""
    parts = encoded_text.split()
    try:
        chars = [chr(int(p)) for p in parts]
        return "".join(chars)
    except ValueError:
        return encoded_text


def encode_structure(obj):
    """
    Recursively encode string and numeric values with encode_text.
    Keys remain unchanged.
    """
    if isinstance(obj, str):
        return encode_text(obj)
    if isinstance(obj, (int, float)):
        return encode_text(str(obj))
    if isinstance(obj, list):
        return [encode_structure(v) for v in obj]
    if isinstance(obj, dict):
        return {k: encode_structure(v) for k, v in obj.items()}
    return obj


def decode_structure(obj):
    """
    Recursively decode values that look like encoded Unicode sequences.
    If decoded value looks numeric, convert to int/float.
    """
    if isinstance(obj, str):
        decoded = maybe_decode_text(obj)

        try:
            if "." in decoded:
                return float(decoded)
            if decoded.isdigit():
                return int(decoded)
        except ValueError:
            pass

        return decoded

    if isinstance(obj, list):
        return [decode_structure(v) for v in obj]
    if isinstance(obj, dict):
        return {k: decode_structure(v) for k, v in obj.items()}
    return obj


# =====================================================
# Database & CSV export (using encoding)
# =====================================================


def load_database():
    """
    Load the main JSON database from disk.
    If missing, return an empty structure.
    """
    if not os.path.exists(DATABASE_FILE):
        return {"users": {}}
    with open(DATABASE_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return decode_structure(raw)


def export_all_to_csv(db):
    """Export all info to CSVs, encoding text and numeric fields."""
    users = db.get("users", {})

    sorted_usernames = selection_sort(list(users.keys()))

    # ---- USERS ----
    with open(USERS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "full_name", "email"])
        for username in sorted_usernames:
            user = users[username]
            writer.writerow(
                [
                    encode_text(username),
                    encode_text(user.get("full_name", "")),
                    encode_text(user.get("email", "")),
                ]
            )

    # ---- EXPENSES ----
    with open(EXPENSES_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "date", "amount", "category", "note"])
        for username in sorted_usernames:
            user = users[username]
            for e in user.get("expenses", []):
                writer.writerow(
                    [
                        encode_text(username),
                        encode_text(e.get("date", "")),
                        encode_text(str(e.get("amount", ""))),
                        encode_text(e.get("category", "")),
                        encode_text(e.get("note", "")),
                    ]
                )

    # ---- GOALS ----
    with open(GOALS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["username", "name", "target", "saved", "deadline", "created_at"]
        )
        for username in sorted_usernames:
            user = users[username]
            for g in user.get("goals", []):
                writer.writerow(
                    [
                        encode_text(username),
                        encode_text(g.get("name", "")),
                        encode_text(str(g.get("target", ""))),
                        encode_text(str(g.get("saved", ""))),
                        encode_text(g.get("deadline", "")),
                        encode_text(g.get("created_at", "")),
                    ]
                )

    # ---- PODS ----
    with open(PODS_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["username", "pod_name", "type", "members", "created_at", "end_date"]
        )
        for username in sorted_usernames:
            user = users[username]
            for p in user.get("pods", []):
                writer.writerow(
                    [
                        encode_text(username),
                        encode_text(p.get("name", "")),
                        encode_text(p.get("type", "")),
                        encode_text(", ".join(p.get("members", []))),
                        encode_text(p.get("created_at", "")),
                        encode_text(p.get("end_date", "")),
                    ]
                )

    # ---- SHARED EXPENSES ----
    with open(SHARED_EXPENSES_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "username",
                "pod_name",
                "pod_type",
                "members",
                "date",
                "amount",
                "category",
                "note",
                "split",
                "approvals",
            ]
        )
        for username in sorted_usernames:
            user = users[username]
            for p in user.get("pods", []):
                members = ", ".join(p.get("members", []))
                for exp in p.get("expenses", []):
                    writer.writerow(
                        [
                            encode_text(username),
                            encode_text(p.get("name", "")),
                            encode_text(p.get("type", "")),
                            encode_text(members),
                            encode_text(exp.get("date", "")),
                            encode_text(str(exp.get("amount", ""))),
                            encode_text(exp.get("category", "")),
                            encode_text(exp.get("note", "")),
                            encode_text(json.dumps(exp.get("split", {}))),
                            encode_text(json.dumps(exp.get("approvals", {}))),
                        ]
                    )


def save_database(db):
    """Save encoded JSON database and update CSV exports."""
    encoded_db = encode_structure(db)
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(encoded_db, f, indent=2)
    export_all_to_csv(db)


def ensure_user_shape(user_record: dict):
    """Ensure a user record has all expected keys."""
    user_record.setdefault("expenses", [])
    user_record.setdefault("goals", [])
    user_record.setdefault("pods", [])
    user_record.setdefault("streak", {"count": 0, "last_active_on": None})


def increment_streak(
    database: dict, username: str, event_date_iso: Optional[str] = None
):
    """
    Update user streak based on event date:
    - if active yesterday: increment
    - if skipped: reset to 1
    - if first activity: start at 1
    """
    user = database["users"][username]
    ensure_user_shape(user)
    s = user["streak"]
    today = date.fromisoformat(event_date_iso) if event_date_iso else date.today()

    if s.get("last_active_on") == today.isoformat():
        return

    last = s.get("last_active_on")
    if last:
        last_d = date.fromisoformat(last)
        if today - last_d == timedelta(days=1):
            s["count"] = int(s.get("count", 0)) + 1
        else:
            s["count"] = 1
    else:
        s["count"] = 1

    s["last_active_on"] = today.isoformat()
    save_database(database)


def streak_badge(count: int) -> str:
    """Return a badge string for the given streak length."""
    if count >= 30:
        return "🏆 Legendary"
    if count >= 14:
        return "🔥🔥 On Fire"
    if count >= 7:
        return "🔥 Streaker"
    if count >= 3:
        return "✨ Getting Consistent"
    if count >= 1:
        return "✅ Day 1"
    return "—"


# =====================================================
# Split helpers for shared expenses
# =====================================================


def split_equally(total_amount, members):
    """Split total_amount equally among non-empty members."""
    members = [m for m in members if m]
    if not members:
        return {}
    each = round(float(total_amount) / len(members), 2)
    return {m: each for m in members}


def split_by_percentage(total_amount, percentages):
    """
    Split total_amount according to {member: pct}.
    Percentages must sum to ~100%.
    """
    total_pct = round(sum(percentages.values()), 2)
    if abs(total_pct - 100.0) > 0.01:
        raise ValueError("Percentages must sum to 100%.")
    return {
        m: round((pct / 100.0) * float(total_amount), 2)
        for m, pct in percentages.items()
    }


# =====================================================
# GUI Application
# =====================================================


class BondiApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Böndi")
        self.geometry("1100x700")
        self.center_window()
        self.minsize(850, 550)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", padding=10)
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("SubHeader.TLabel", font=("Segoe UI", 12))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))

        self.database = load_database()
        self.current_user: Optional[str] = None

        self._build_auth_frame()
        self._build_app_frame()
        self._build_intro_frame()

        self.app_frame.pack_forget()
        self.intro_frame.pack_forget()
        self.auth_frame.pack(fill="both", expand=True)

        export_all_to_csv(self.database)

    def center_window(self, y_offset=-30):
        """Center the window on the screen and offset vertically by y_offset."""
        self.update_idletasks()

        w = self.winfo_width()
        h = self.winfo_height()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = int((screen_w / 2) - (w / 2))
        y = int((screen_h / 2) - (h / 2))

        y = y + y_offset

        self.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- AUTH SCREEN ----------
    def _build_auth_frame(self):
        """Build login / sign-up screen with a tabbed notebook."""
        self.auth_frame = ttk.Frame(self)

        container = ttk.Frame(self.auth_frame)
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = ttk.Label(container, text="Welcome to Böndi", style="Header.TLabel")
        subtitle = ttk.Label(
            container,
            text="Track expenses, smash goals, share costs with your pod.",
            style="SubHeader.TLabel",
        )
        title.grid(row=0, column=0, columnspan=2, pady=(0, 4))
        subtitle.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        nb = ttk.Notebook(container)
        nb.grid(row=2, column=0, columnspan=2)

        # Login tab
        login_tab = ttk.Frame(nb, padding=10)
        nb.add(login_tab, text="Login")

        ttk.Label(login_tab, text="Username").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.login_username = ttk.Entry(login_tab, width=30)
        self.login_username.grid(row=0, column=1, pady=5)

        ttk.Label(login_tab, text="Password").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.login_password = ttk.Entry(login_tab, width=30, show="*")
        self.login_password.grid(row=1, column=1, pady=5)

        login_btn = ttk.Button(login_tab, text="Sign in", command=self.handle_login)
        login_btn.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        forgot_user_btn = ttk.Button(
            login_tab, text="Forgot username?", command=self.forgot_username
        )
        forgot_user_btn.grid(row=3, column=0, pady=5, sticky="w")

        forgot_pw_btn = ttk.Button(
            login_tab, text="Forgot password?", command=self.forgot_password
        )
        forgot_pw_btn.grid(row=3, column=1, pady=5, sticky="e")

        # Signup tab
        signup_tab = ttk.Frame(nb, padding=10)
        nb.add(signup_tab, text="Create account")

        ttk.Label(signup_tab, text="Full name").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.signup_full_name = ttk.Entry(signup_tab, width=30)
        self.signup_full_name.grid(row=0, column=1, pady=5)

        ttk.Label(signup_tab, text="Email").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.signup_email = ttk.Entry(signup_tab, width=30)
        self.signup_email.grid(row=1, column=1, pady=5)

        ttk.Label(signup_tab, text="Username").grid(
            row=2, column=0, sticky="w", pady=5
        )
        self.signup_username = ttk.Entry(signup_tab, width=30)
        self.signup_username.grid(row=2, column=1, pady=5)

        ttk.Label(signup_tab, text="Password").grid(
            row=3, column=0, sticky="w", pady=5
        )
        self.signup_password1 = ttk.Entry(signup_tab, width=30, show="*")
        self.signup_password1.grid(row=3, column=1, pady=5)

        ttk.Label(signup_tab, text="Repeat password").grid(
            row=4, column=0, sticky="w", pady=5
        )
        self.signup_password2 = ttk.Entry(signup_tab, width=30, show="*")
        self.signup_password2.grid(row=4, column=1, pady=5)

        ttk.Label(
            signup_tab,
            text="Recovery word\n(e.g. 'yellow', 'cat', 'cereal')",
        ).grid(row=5, column=0, sticky="w", pady=5)
        self.signup_recovery = ttk.Entry(signup_tab, width=30)
        self.signup_recovery.grid(row=5, column=1, pady=5)

        signup_btn = ttk.Button(
            signup_tab, text="Create account", command=self.handle_signup
        )
        signup_btn.grid(row=6, column=0, columnspan=2, pady=15, sticky="ew")

    # ---------- MAIN APP SCREEN ----------
    def _build_app_frame(self):
        """Build main UI: top bar and 4 tabs."""
        self.app_frame = ttk.Frame(self)

        topbar = ttk.Frame(self.app_frame)
        topbar.pack(side="top", fill="x")

        self.user_label = ttk.Label(topbar, text="", style="Title.TLabel")
        self.user_label.pack(side="left")

        self.streak_label = ttk.Label(topbar, text="")
        self.streak_label.pack(side="left", padx=(15, 0))

        info_btn = ttk.Button(topbar, text="ℹ", width=3, command=self.show_info_dialog)
        info_btn.pack(side="right", padx=(0, 5))

        logout_btn = ttk.Button(topbar, text="Log out", command=self.handle_logout)
        logout_btn.pack(side="right", padx=(0, 10))

        nb = ttk.Notebook(self.app_frame)
        nb.pack(fill="both", expand=True, pady=10)

        self.goals_tab = ttk.Frame(nb, padding=10)
        nb.add(self.goals_tab, text="Goals")
        self._build_goals_tab()

        self.expenses_tab = ttk.Frame(nb, padding=10)
        nb.add(self.expenses_tab, text="Expenses")
        self._build_expenses_tab()

        self.shared_tab = ttk.Frame(nb, padding=10)
        nb.add(self.shared_tab, text="Shared")
        self._build_shared_tab()

        self.streak_tab = ttk.Frame(nb, padding=10)
        nb.add(self.streak_tab, text="Streak")
        self._build_streak_tab()

    # ---------- INTRO PAGE ----------
    def _build_intro_frame(self):
        """Build intro screen shown after login."""
        self.intro_frame = ttk.Frame(self)

        title = ttk.Label(
            self.intro_frame, text="Welcome to Böndi", style="Header.TLabel"
        )
        title.pack(pady=(30, 10))

        text = (
            "Böndi helps you manage both personal and shared money.\n\n"
            "• Track your own expenses and see where your money goes.\n"
            "• Create goals and save towards things that matter to you.\n"
            "• Use pods to split costs with friends, roommates, or trips.\n"
            "• Use Böndi regularly to build your streak and keep your finances under control.\n"
            "\n"
            "When you enter the app you can tap the info button (i) on the top right of the screen to watch a video "
            "explaining how Böndi works."
        )

        info_label = ttk.Label(
            self.intro_frame,
            text=text,
            justify="left",
            anchor="center",
        )
        info_label.pack(pady=10)

        self.intro_check_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(
            self.intro_frame,
            text="I understood",
            variable=self.intro_check_var,
            command=self._on_intro_check_changed,
        )
        chk.pack(pady=(20, 5))

        self.intro_continue_btn = ttk.Button(
            self.intro_frame,
            text="Continue",
            command=self._intro_continue,
            state="disabled",
        )
        self.intro_continue_btn.pack(pady=10)

    def _on_intro_check_changed(self):
        """Enable/disable Continue button based on checkbox."""
        if self.intro_check_var.get():
            self.intro_continue_btn.config(state="normal")
        else:
            self.intro_continue_btn.config(state="disabled")

    def _intro_continue(self):
        """Hide intro and show main app once user confirms."""
        if not self.intro_check_var.get():
            messagebox.showerror(
                "Please confirm", "Please check 'I understood' before continuing."
            )
            return

        self.intro_frame.pack_forget()
        self.app_frame.pack(fill="both", expand=True)

    # =====================================================
    # AUTH HANDLERS + RECOVERY
    # =====================================================

    def handle_signup(self):
        """Validate and create a new account."""
        users = self.database["users"]
        full_name = self.signup_full_name.get().strip()
        email = self.signup_email.get().strip()
        username = self.signup_username.get().strip().lower()
        pw1 = self.signup_password1.get()
        pw2 = self.signup_password2.get()
        recovery = self.signup_recovery.get().strip().lower()

        if not all([full_name, email, username, pw1, pw2, recovery]):
            messagebox.showerror("Missing info", "Please fill out all fields.")
            return

        if username in users:
            messagebox.showerror("Username taken", "That username already exists.")
            return

        if pw1 != pw2:
            messagebox.showerror("Password mismatch", "Passwords do not match.")
            return

        users[username] = {
            "full_name": full_name,
            "email": email,
            "password_hash": hash_text(pw1),
            "recovery_hash": hash_text(recovery),
            "goals": [],
            "expenses": [],
            "pods": [],
            "streak": {"count": 0, "last_active_on": None},
        }
        save_database(self.database)

        messagebox.showinfo(
            "Account created",
            f"Account created for '{username}'. Return to the login page to sign in",
        )

        self.signup_password1.delete(0, tk.END)
        self.signup_password2.delete(0, tk.END)

    def handle_login(self):
        """Handle user login using selection_sort + binary_search."""
        users = self.database["users"]
        username = self.login_username.get().strip().lower()
        password = self.login_password.get()

        username_list = list(users.keys())
        sorted_usernames = selection_sort(username_list)
        idx = binary_search(sorted_usernames, username)

        if idx is None:
            messagebox.showerror(
                "Login failed", "No such user (checked with binary search)."
            )
            return

        if hash_text(password) != users[username]["password_hash"]:
            messagebox.showerror("Login failed", "Incorrect password.")
            return

        ensure_user_shape(users[username])
        self.current_user = username
        self.update_topbar()
        self.refresh_all_views()

        self.auth_frame.pack_forget()
        self.intro_check_var.set(False)
        self.intro_continue_btn.config(state="disabled")
        self.intro_frame.pack(fill="both", expand=True)

        self.login_password.delete(0, tk.END)

    def handle_logout(self):
        """Log out and return to auth screen."""
        self.current_user = None
        self.app_frame.pack_forget()
        self.intro_frame.pack_forget()
        self.auth_frame.pack(fill="both", expand=True)

    def show_info_dialog(self):
        """Open the tutorial video."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        video_path = os.path.join(base_dir, "video", "tutorial.mp4")

        if not os.path.exists(video_path):
            messagebox.showerror(
                "Video not found",
                f"Could not find video file:\n{video_path}"
            )
            return

        open_video(video_path)

    def show_shared_help(self):
        """Explain how to add a shared expense and configure splits."""
        message = (
            "How to add a shared expense:\n\n"
            "1. Select your pod.\n"
            "   Click on a pod in the list. When selected, it will highlight in blue.\n\n"
            "2. Enter the total amount.\n"
            "   Fill in the amount, category, and note in the fields below.\n\n"
            "3. Choose how you want to split the expense:\n\n"
            "   a) Percentages\n"
            "      This option lets you assign different percentages to each member.\n"
            "      To use it:\n"
            "      • Select 'Percentages' in the Split Type menu.\n"
            "      • Click 'Add shared expense'.\n"
            "      • You will be prompted to enter the percentage for each member.\n\n"
            "   b) Equal\n"
            "      This option automatically splits the total evenly among all pod members.\n"
            "   c) Custom amounts\n"
            "      This option lets you choose the exact amount each member pays.\n"
            "      To use it:\n"
            "      • Select 'Custom amounts' in the Split Type menu.\n"
            "      • Click 'Add shared expense'.\n"
            "      • You will be prompted to enter the amount for each member.\n"
            "        The total of these amounts must match the total you entered.\n"
        )
        messagebox.showinfo("Shared Expense Help", message)

    def forgot_username(self):
        """Recover username(s) using email + recovery word."""
        email = simpledialog.askstring(
            "Recover username", "Enter your email:", parent=self
        )
        if email is None or not email.strip():
            return
        email = email.strip()

        answer = simpledialog.askstring(
            "Recover username",
            "Enter your recovery answer:",
            parent=self,
        )
        if answer is None or not answer.strip():
            return
        answer_hash = hash_text(answer.strip().lower())

        found = []
        for username, user in self.database.get("users", {}).items():
            if (
                user.get("email", "").lower() == email.lower()
                and user.get("recovery_hash") == answer_hash
            ):
                found.append(username)

        if found:
            msg = "Your username(s):\n" + "\n".join(found)
            messagebox.showinfo("Username found", msg)
        else:
            messagebox.showerror(
                "Not found", "No username matched that email + recovery answer."
            )

    def forgot_password(self):
        """Reset password using username + recovery word."""
        username = simpledialog.askstring(
            "Reset password", "Enter your username:", parent=self
        )
        if username is None or not username.strip():
            return
        username = username.strip().lower()

        users = self.database.get("users", {})
        if username not in users:
            messagebox.showerror("Error", "No such user.")
            return

        answer = simpledialog.askstring(
            "Reset password",
            "Enter your recovery answer:",
            parent=self,
        )
        if answer is None or not answer.strip():
            return

        answer_hash = hash_text(answer.strip().lower())
        if answer_hash != users[username].get("recovery_hash"):
            messagebox.showerror("Error", "Recovery answer is incorrect.")
            return

        new_pw1 = simpledialog.askstring(
            "Reset password", "New password:", parent=self, show="*"
        )
        if new_pw1 is None or not new_pw1:
            return
        new_pw2 = simpledialog.askstring(
            "Reset password", "Repeat new password:", parent=self, show="*"
        )
        if new_pw2 is None or not new_pw2:
            return

        if new_pw1 != new_pw2:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        users[username]["password_hash"] = hash_text(new_pw1)
        save_database(self.database)
        messagebox.showinfo(
            "Password reset",
            "Your password has been updated. You can log in now.",
        )

    # =====================================================
    # EXPENSES
    # =====================================================

    def _build_expenses_tab(self):
        """Build the 'Expenses' tab UI."""
        form = ttk.LabelFrame(self.expenses_tab, text="Add expense", padding=10)
        form.pack(side="top", fill="x")

        ttk.Label(form, text="Amount").grid(row=0, column=0, sticky="w", pady=5)
        self.exp_amount = ttk.Entry(form, width=15)
        self.exp_amount.grid(row=0, column=1, pady=5, padx=(0, 10))

        ttk.Label(form, text="Category").grid(row=0, column=2, sticky="w", pady=5)
        self.exp_category = ttk.Entry(form, width=20)
        self.exp_category.grid(row=0, column=3, pady=5, padx=(0, 10))

        ttk.Label(form, text="Note").grid(row=0, column=4, sticky="w", pady=5)
        self.exp_note = ttk.Entry(form, width=30)
        self.exp_note.grid(row=0, column=5, pady=5)

        add_btn = ttk.Button(form, text="Add", command=self.add_expense)
        add_btn.grid(row=0, column=6, padx=(10, 0))

        list_frame = ttk.Frame(self.expenses_tab)
        list_frame.pack(fill="both", expand=True, pady=(10, 0))

        cols = ("date", "amount", "category", "note")
        self.exp_tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        for c in cols:
            self.exp_tree.heading(c, text=c.title())
        self.exp_tree.column("date", width=150)
        self.exp_tree.column("amount", width=80, anchor="e")
        self.exp_tree.column("category", width=120)
        self.exp_tree.column("note", width=300)

        vsb = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.exp_tree.yview
        )
        self.exp_tree.configure(yscroll=vsb.set)
        self.exp_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.exp_total_label = ttk.Label(
            self.expenses_tab, text="Total: $0.00", style="Title.TLabel"
        )
        self.exp_total_label.pack(side="bottom", anchor="e", pady=5)

    def add_expense(self):
        """Add a new expense and update streak."""
        if not self.current_user:
            return

        amount_text = self.exp_amount.get().strip()
        category = self.exp_category.get().strip() or "General"
        note = self.exp_note.get().strip()

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a number.")
            return

        user = self.database["users"][self.current_user]
        exp = {
            "amount": round(amount, 2),
            "category": category,
            "note": note,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        user["expenses"].append(exp)

        increment_streak(self.database, self.current_user, date.today().isoformat())
        save_database(self.database)

        self.exp_amount.delete(0, tk.END)
        self.exp_note.delete(0, tk.END)

        self.refresh_expenses()
        self.update_topbar()
        messagebox.showinfo("Expense added", "Expense added successfully!")

    def refresh_expenses(self):
        """Refresh expenses table and total using quicksort by amount."""
        for i in self.exp_tree.get_children():
            self.exp_tree.delete(i)

        total = 0.0
        if not self.current_user:
            self.exp_total_label.config(text="Total: $0.00")
            return

        user = self.database["users"][self.current_user]
        expenses = user.get("expenses", [])

        sorted_expenses = quicksort_expenses_by_amount(expenses)

        for exp in sorted_expenses:
            self.exp_tree.insert(
                "",
                "end",
                values=(
                    exp["date"],
                    f"${exp['amount']:.2f}",
                    exp["category"],
                    exp["note"],
                ),
            )
            total += exp["amount"]

        self.exp_total_label.config(text=f"Total: ${total:.2f}")

    # =====================================================
    # GOALS
    # =====================================================

    def _build_goals_tab(self):
        """Build the 'Goals' tab UI."""
        top = ttk.Frame(self.goals_tab)
        top.pack(side="top", fill="x")

        create_frame = ttk.LabelFrame(top, text="Create new goal", padding=10)
        create_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ttk.Label(create_frame, text="Name Goal").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.goal_name = ttk.Entry(create_frame, width=20)
        self.goal_name.grid(row=0, column=1, pady=5)

        ttk.Label(create_frame, text="Target amount").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.goal_target = ttk.Entry(create_frame, width=20)
        self.goal_target.grid(row=1, column=1, pady=5)

        ttk.Label(
            create_frame,
            text="Deadline (optional, YYYY-MM-DD)",
        ).grid(row=2, column=0, sticky="w", pady=5)
        self.goal_deadline = ttk.Entry(create_frame, width=20)
        self.goal_deadline.grid(row=2, column=1, pady=5)

        ttk.Button(
            create_frame, text="Create goal", command=self.create_goal
        ).grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")

        save_frame = ttk.LabelFrame(top, text="Add saving to goal", padding=10)
        save_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        ttk.Label(save_frame, text="Goal").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.goal_combo = ttk.Combobox(save_frame, state="readonly", width=25)
        self.goal_combo.grid(row=0, column=1, pady=5)

        ttk.Label(save_frame, text="Amount").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.goal_add_amount = ttk.Entry(save_frame, width=20)
        self.goal_add_amount.grid(row=1, column=1, pady=5)

        ttk.Button(save_frame, text="Add saving", command=self.add_saving).grid(
            row=2, column=0, columnspan=2, pady=10, sticky="ew"
        )

        self.goals_list_frame = ttk.Frame(self.goals_tab)
        self.goals_list_frame.pack(fill="both", expand=True, pady=(10, 0))

    def create_goal(self):
        """Create a new goal for the current user."""
        if not self.current_user:
            return

        name = self.goal_name.get().strip()
        target_text = self.goal_target.get().strip()
        deadline = self.goal_deadline.get().strip()

        if not name or not target_text:
            messagebox.showerror("Missing info", "Please enter a name and target.")
            return

        try:
            target = float(target_text)
        except ValueError:
            messagebox.showerror("Invalid amount", "Target must be a number.")
            return

        user = self.database["users"][self.current_user]
        user["goals"].append(
            {
                "name": name,
                "target": round(target, 2),
                "saved": 0.0,
                "deadline": deadline,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )
        save_database(self.database)

        self.goal_name.delete(0, tk.END)
        self.goal_target.delete(0, tk.END)
        self.goal_deadline.delete(0, tk.END)

        self.refresh_goals()
        messagebox.showinfo("Goal created", "Goal created!")

    def add_saving(self):
        """Add a saving amount to the selected goal and update streak."""
        if not self.current_user:
            return

        idx = self.goal_combo.current()
        if idx == -1:
            messagebox.showerror("No goal", "Please choose a goal.")
            return

        amount_text = self.goal_add_amount.get().strip()
        try:
            amt = float(amount_text)
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a number.")
            return

        user = self.database["users"][self.current_user]
        try:
            goal = user["goals"][idx]
        except IndexError:
            messagebox.showerror("Error", "Selected goal not found.")
            return

        goal["saved"] = round(goal["saved"] + amt, 2)
        increment_streak(self.database, self.current_user, date.today().isoformat())
        save_database(self.database)

        self.goal_add_amount.delete(0, tk.END)

        self.refresh_goals()
        self.update_topbar()
        messagebox.showinfo("Saving added", "Saving added to goal!")

    def refresh_goals(self):
        """Rebuild goals list UI and combo box."""
        for w in self.goals_list_frame.winfo_children():
            w.destroy()

        if not self.current_user:
            return

        user = self.database["users"][self.current_user]
        goals = user.get("goals", [])

        names = [g["name"] for g in goals]
        self.goal_combo["values"] = names

        if not goals:
            ttk.Label(
                self.goals_list_frame,
                text="No goals yet. Create one to get started.",
            ).pack(pady=20)
            return

        for g in goals:
            frame = ttk.Frame(self.goals_list_frame, padding=8)
            frame.pack(fill="x", pady=4)

            header = ttk.Label(frame, text=g["name"], style="Title.TLabel")
            header.pack(anchor="w")

            info = (
                f"Target: ${g['target']:.2f} | Saved: ${g['saved']:.2f} "
                f"| Deadline: {g['deadline'] or '—'}"
            )
            ttk.Label(frame, text=info).pack(anchor="w")

            prog = (g["saved"] / g["target"]) * 100 if g["target"] > 0 else 0
            pb = ttk.Progressbar(frame, maximum=100, value=min(prog, 100))
            pb.pack(fill="x", pady=3)
            ttk.Label(frame, text=f"{prog:.2f}%").pack(anchor="w")

    # =====================================================
    # SHARED / PODS TAB
    # =====================================================

    def _build_shared_tab(self):
        """Build the 'Shared' tab UI."""
        create_frame = ttk.LabelFrame(
            self.shared_tab, text="Create shared pod", padding=10
        )
        create_frame.pack(side="top", fill="x")

        ttk.Label(create_frame, text="Pod name").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.pod_name_entry = ttk.Entry(create_frame, width=20)
        self.pod_name_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(create_frame, text="Type").grid(
            row=0, column=2, sticky="w", pady=5
        )
        self.pod_type_combo = ttk.Combobox(
            create_frame, values=["ongoing", "temporary"], width=15
        )
        self.pod_type_combo.set("ongoing")
        self.pod_type_combo.grid(row=0, column=3, pady=5, padx=5)

        ttk.Label(
            create_frame,
            text="Other members (usernames, comma separated)",
        ).grid(row=1, column=0, sticky="w", pady=5)

        self.pod_members_entry = ttk.Entry(create_frame, width=50)
        self.pod_members_entry.grid(
            row=1, column=1, columnspan=3, pady=5, padx=5, sticky="we"
        )

        self.include_self_var = tk.BooleanVar(value=True)
        self.include_self_check = ttk.Checkbutton(
            create_frame,
            text="Include me in this pod (default)",
            variable=self.include_self_var,
        )
        self.include_self_check.grid(
            row=2, column=1, columnspan=3, sticky="w", pady=(0, 10)
        )

        ttk.Label(create_frame, text="End date (optional, YYYY-MM-DD)").grid(
            row=3, column=0, sticky="w", pady=5
        )

        self.pod_end_entry = ttk.Entry(create_frame, width=20)
        self.pod_end_entry.grid(row=3, column=1, pady=5, padx=5, sticky="w")

        ttk.Button(
            create_frame, text="Create pod", command=self.create_pod
        ).grid(row=0, column=4, rowspan=3, padx=10, pady=5, sticky="ns")

        pod_explanation = (
            "A pod is a shared space where you add\n"
            "people to split expenses together.\n\n"
            "There are two types:\n"
            "• Ongoing pods — roommates, projects, etc.\n"
            "• Temporary pods — trips, dinners, events.\n\n"
        )

        info_label = ttk.Label(create_frame, text=pod_explanation, justify="left")
        info_label.grid(row=0, column=5, rowspan=4, sticky="nw", padx=20)

        middle = ttk.PanedWindow(self.shared_tab, orient="horizontal")
        middle.pack(fill="both", expand=True, pady=(10, 0))

        pods_frame = ttk.LabelFrame(middle, text="Pods", padding=5)
        middle.add(pods_frame, weight=1)

        self.pods_tree = ttk.Treeview(
            pods_frame, columns=("type", "members"), show="headings", height=8
        )
        self.pods_tree.heading("type", text="Type")
        self.pods_tree.heading("members", text="Members")
        self.pods_tree.column("type", width=80)
        self.pods_tree.column("members", width=200)

        pods_scroll = ttk.Scrollbar(
            pods_frame, orient="vertical", command=self.pods_tree.yview
        )
        self.pods_tree.configure(yscroll=pods_scroll.set)
        self.pods_tree.pack(side="left", fill="both", expand=True)
        pods_scroll.pack(side="right", fill="y")

        self.pods_tree.bind("<<TreeviewSelect>>", self.on_pod_selected)

        exp_frame = ttk.LabelFrame(
            middle, text="Shared expenses (selected pod)", padding=5
        )
        middle.add(exp_frame, weight=3)

        cols = ("date", "amount", "category", "note", "split")
        self.shared_exp_tree = ttk.Treeview(exp_frame, columns=cols, show="headings")
        for c in cols:
            self.shared_exp_tree.heading(c, text=c.title())
        self.shared_exp_tree.column("date", width=130)
        self.shared_exp_tree.column("amount", width=80, anchor="e")
        self.shared_exp_tree.column("category", width=100)
        self.shared_exp_tree.column("note", width=180)
        self.shared_exp_tree.column("split", width=220)

        sh_scroll = ttk.Scrollbar(
            exp_frame, orient="vertical", command=self.shared_exp_tree.yview
        )
        self.shared_exp_tree.configure(yscroll=sh_scroll.set)
        self.shared_exp_tree.pack(side="left", fill="both", expand=True)
        sh_scroll.pack(side="right", fill="y")

        help_btn = ttk.Button(
            self.shared_tab,
            text="How to add a shared expense",
            command=self.show_shared_help,
        )
        help_btn.pack(anchor="w", padx=10, pady=(5, 0))

        add_frame = ttk.LabelFrame(
            self.shared_tab, text="Add shared expense to selected pod", padding=10
        )
        add_frame.pack(side="bottom", fill="x", pady=(10, 0))

        ttk.Label(add_frame, text="Amount").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.shared_amount_entry = ttk.Entry(add_frame, width=10)
        self.shared_amount_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(add_frame, text="Category").grid(
            row=0, column=2, sticky="w", pady=5
        )
        self.shared_category_entry = ttk.Entry(add_frame, width=15)
        self.shared_category_entry.grid(row=0, column=3, pady=5, padx=5)

        ttk.Label(add_frame, text="Note").grid(
            row=0, column=4, sticky="w", pady=5
        )
        self.shared_note_entry = ttk.Entry(add_frame, width=30)
        self.shared_note_entry.grid(row=0, column=5, pady=5, padx=5)

        ttk.Label(add_frame, text="Split type").grid(
            row=0, column=6, sticky="w", pady=5
        )
        self.split_type_combo = ttk.Combobox(
            add_frame,
            values=["Equal", "Percentages", "Custom amounts"],
            width=15,
            state="readonly",
        )
        self.split_type_combo.set("Equal")
        self.split_type_combo.grid(row=0, column=7, pady=5, padx=5)

        ttk.Button(
            add_frame, text="Add shared expense", command=self.add_shared_expense
        ).grid(row=0, column=8, padx=10)

    def create_pod(self):
        """
        Create a new pod:
        - uses SimpleHashSet to remove duplicate members
        - validates that all members exist and end date is valid
        """
        if not self.current_user:
            return

        name = self.pod_name_entry.get().strip()
        ptype = self.pod_type_combo.get().strip() or "ongoing"
        members_str = self.pod_members_entry.get().strip()
        end_date_text = self.pod_end_entry.get().strip()

        if not name:
            messagebox.showerror("Missing info", "Please enter a pod name.")
            return

        if not members_str and not self.include_self_var.get():
            messagebox.showerror(
                "Missing members",
                "Please add at least one member or include yourself in the pod.",
            )
            return

        member_set = SimpleHashSet()

        raw_members = [m.strip().lower() for m in members_str.split(",") if m.strip()]
        for m in raw_members:
            member_set.add(m)

        if self.include_self_var.get():
            member_set.add(self.current_user)

        members = member_set.to_list()
        if not members:
            messagebox.showerror(
                "Missing members", "Please add at least one member username."
            )
            return

        all_users = set(self.database.get("users", {}).keys())
        unknown = [u for u in members if u not in all_users]

        if unknown:
            message = "These usernames do not exist:\n" + ", ".join(unknown)
            messagebox.showerror("Unknown usernames", message)
            return

        if end_date_text:
            try:
                datetime.strptime(end_date_text, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Invalid date", "End date must be in format YYYY-MM-DD."
                )
                return

        user = self.database["users"][self.current_user]
        pod = {
            "name": name,
            "type": ptype,
            "members": members,
            "expenses": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "end_date": end_date_text,
        }
        user["pods"].append(pod)
        save_database(self.database)

        self.pod_name_entry.delete(0, tk.END)
        self.pod_members_entry.delete(0, tk.END)
        self.pod_end_entry.delete(0, tk.END)
        self.include_self_var.set(True)

        self.refresh_pods()
        messagebox.showinfo("Pod created", f"Pod '{name}' created successfully.")

    def get_current_pods(self):
        """
        Return only active pods:
        - no end date
        - or end_date >= today
        """
        if not self.current_user:
            return []
        user = self.database["users"][self.current_user]
        ensure_user_shape(user)
        pods = user["pods"]

        today = date.today()
        active_pods = []

        for p in pods:
            end_date_text = p.get("end_date", "")
            if not end_date_text:
                active_pods.append(p)
            else:
                try:
                    end_d = datetime.strptime(end_date_text, "%Y-%m-%d").date()
                    if end_d >= today:
                        active_pods.append(p)
                except ValueError:
                    active_pods.append(p)

        return active_pods

    def refresh_pods(self):
        """Refresh pods list with only active pods."""
        for i in self.pods_tree.get_children():
            self.pods_tree.delete(i)

        pods = self.get_current_pods()
        for idx, pod in enumerate(pods):
            members = ", ".join(pod.get("members", []))
            self.pods_tree.insert(
                "", "end", iid=str(idx), values=(pod.get("type", ""), members)
            )

        self.refresh_pod_expenses(None)

    def on_pod_selected(self, event):
        """When a pod is selected, refresh its shared expenses."""
        selection = self.pods_tree.selection()
        if not selection:
            self.refresh_pod_expenses(None)
            return
        idx = int(selection[0])
        self.refresh_pod_expenses(idx)

    def refresh_pod_expenses(self, pod_index: Optional[int]):
        """Refresh shared expenses table for the given pod index."""
        for i in self.shared_exp_tree.get_children():
            self.shared_exp_tree.delete(i)

        if pod_index is None or not self.current_user:
            return

        pods = self.get_current_pods()
        if pod_index < 0 or pod_index >= len(pods):
            return

        pod = pods[pod_index]
        for exp in pod.get("expenses", []):
            split_info = ", ".join(
                [f"{m}: ${a:.2f}" for m, a in exp.get("split", {}).items()]
            )
            self.shared_exp_tree.insert(
                "",
                "end",
                values=(
                    exp.get("date", ""),
                    f"${exp.get('amount', 0):.2f}",
                    exp.get("category", ""),
                    exp.get("note", ""),
                    split_info,
                ),
            )

    def add_shared_expense(self):
        """Add a shared expense to the selected pod (equal / % / custom splits)."""
        if not self.current_user:
            return

        selection = self.pods_tree.selection()
        if not selection:
            messagebox.showerror("No pod", "Please select a pod first.")
            return
        pod_index = int(selection[0])

        pods = self.get_current_pods()
        if pod_index < 0 or pod_index >= len(pods):
            messagebox.showerror("Error", "Selected pod not found.")
            return
        pod = pods[pod_index]

        amount_text = self.shared_amount_entry.get().strip()
        category = self.shared_category_entry.get().strip() or "General"
        note = self.shared_note_entry.get().strip()

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a number.")
            return

        split_type = self.split_type_combo.get()
        members = pod.get("members", [])

        if not members:
            messagebox.showerror("No members", "This pod has no members.")
            return

        if split_type == "Equal":
            split_map = split_equally(amount, members)

        elif split_type == "Percentages":
            percentages = {}
            for m in members:
                pct = simpledialog.askfloat(
                    "Percentage split",
                    f"Percentage for {m} (0-100):",
                    minvalue=0.0,
                    maxvalue=100.0,
                    parent=self,
                )
                if pct is None:
                    messagebox.showinfo(
                        "Cancelled", "Split configuration cancelled."
                    )
                    return
                percentages[m] = pct
            try:
                split_map = split_by_percentage(amount, percentages)
            except ValueError as e:
                messagebox.showerror("Invalid percentages", str(e))
                return

        elif split_type == "Custom amounts":
            split_map = {}
            total_entered = 0.0
            for m in members:
                part = simpledialog.askfloat(
                    "Custom split",
                    f"Amount for {m}:",
                    minvalue=0.0,
                    parent=self,
                )
                if part is None:
                    messagebox.showinfo(
                        "Cancelled", "Split configuration cancelled."
                    )
                    return
                part = round(float(part), 2)
                split_map[m] = part
                total_entered += part

            total_entered = round(total_entered, 2)
            if abs(total_entered - amount) > 0.01:
                messagebox.showerror(
                    "Mismatch",
                    f"The amounts you entered add up to {total_entered:.2f}, "
                    f"but the total is {amount:.2f}. Please try again.",
                )
                return
        else:
            messagebox.showerror("Error", "Unknown split type.")
            return

        approvals = {m: "pending" for m in members}
        exp = {
            "amount": round(amount, 2),
            "category": category,
            "note": note,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "split": split_map,
            "approvals": approvals,
        }
        pod.setdefault("expenses", []).append(exp)

        increment_streak(self.database, self.current_user, date.today().isoformat())
        save_database(self.database)

        self.shared_amount_entry.delete(0, tk.END)
        self.shared_note_entry.delete(0, tk.END)

        self.refresh_pod_expenses(pod_index)
        self.update_topbar()
        messagebox.showinfo(
            "Shared expense added", "Shared expense recorded successfully."
        )

    # =====================================================
    # STREAK TAB & HELPERS
    # =====================================================

    def _build_streak_tab(self):
        """Build the 'Streak' tab UI."""
        self.streak_main_label = ttk.Label(
            self.streak_tab, text="", style="Header.TLabel"
        )
        self.streak_main_label.pack(pady=(10, 5))

        self.streak_last_label = ttk.Label(
            self.streak_tab, text="", style="SubHeader.TLabel"
        )
        self.streak_last_label.pack(pady=(0, 10))

        self.streak_bar_label = ttk.Label(
            self.streak_tab, text="", font=("Segoe UI Emoji", 16)
        )
        self.streak_bar_label.pack()

        streak_info = (
            "What is a streak?\n"
            "A streak counts how many days in a row you have been active.\n"
            "You increase your streak by doing any of the following:\n"
            " • Adding an expense\n"
            " • Adding savings to a goal\n"
            " • Adding a shared expense\n\n"
            "If you skip a day, your streak resets to 1.\n"
            "Longer streaks unlock special badges:\n"
            " • 1+ days → ✅ Day 1\n"
            " • 3+ days → ✨ Getting Consistent\n"
            " • 7+ days → 🔥 Streaker\n"
            " • 14+ days → 🔥🔥 On Fire\n"
            " • 30+ days → 🏆 Legendary\n\n"
            "Keep going to earn better streak rewards!"
        )

        self.streak_explanation = ttk.Label(
            self.streak_tab,
            text=streak_info,
            justify="left",
            font=("Segoe UI", 10),
        )
        self.streak_explanation.pack(pady=15)

    def refresh_streak_tab(self):
        """Refresh labels in the streak tab with current user's streak."""
        if not self.current_user:
            self.streak_main_label.config(text="")
            self.streak_last_label.config(text="")
            self.streak_bar_label.config(text="")
            return

        user = self.database["users"][self.current_user]
        s = user.get("streak", {"count": 0, "last_active_on": None})
        count = int(s.get("count", 0))
        last = s.get("last_active_on") or "—"
        badge = streak_badge(count)

        self.streak_main_label.config(
            text=f"Current streak: {count} days  ({badge})"
        )
        self.streak_last_label.config(text=f"Last activity: {last}")
        self.streak_bar_label.config(text="🔥 " * min(count, 10))

    def update_topbar(self):
        """Update top bar username and streak badge."""
        if not self.current_user:
            self.user_label.config(text="")
            self.streak_label.config(text="")
            return

        user = self.database["users"][self.current_user]
        s = user.get("streak", {"count": 0})
        count = int(s.get("count", 0))
        badge = streak_badge(count)

        self.user_label.config(text=f"👤 {self.current_user}")
        self.streak_label.config(text=f"Streak: {count}  ({badge})")

    def refresh_all_views(self):
        """Refresh all tabs at once for the current user."""
        self.refresh_expenses()
        self.refresh_goals()
        self.refresh_pods()
        self.refresh_streak_tab()


# =====================================================
# Run the app
# =====================================================

if __name__ == "__main__":
    app = BondiApp()
    app.mainloop()
