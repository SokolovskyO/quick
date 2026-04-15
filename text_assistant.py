import threading
import time
import sys
import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
import pyperclip
import keyboard
import anthropic
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

# ─── CONFIG ───────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"api_key": ""}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

config = load_config()

# ─── CLAUDE API ───────────────────────────────────────────────────────────────
ACTIONS = {
    "🌐 Перевести на русский":   "Переведи следующий текст на русский язык. Верни ТОЛЬКО перевод, без пояснений.",
    "🌐 Перевести на английский":"Переведи следующий текст на английский язык. Верни ТОЛЬКО перевод, без пояснений.",
    "✏️ Исправить орфографию":   "Исправь орфографические и грамматические ошибки в тексте. Верни ТОЛЬКО исправленный текст, без пояснений и без изменения стиля.",
    "📝 Расставить запятые":     "Расставь запятые и знаки препинания в тексте. Не меняй слова, стиль и структуру — только пунктуация. Верни ТОЛЬКО исправленный текст.",
    "🔄 Перефразировать":        "Перефразируй текст, сохранив смысл. Верни ТОЛЬКО перефразированный текст, без пояснений.",
    "💡 Объяснить слово/фразу":  "Объясни значение следующего слова или фразы простым языком на русском. Кратко, 2-3 предложения.",
}

def call_claude(action_name: str, text: str) -> str:
    api_key = load_config().get("api_key", "").strip()
    if not api_key:
        return "⚠️ API-ключ не задан. Откройте настройки (иконка в трее → Настройки)."
    try:
        client = anthropic.Anthropic(api_key=api_key)
        system_prompt = ACTIONS[action_name]
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"{system_prompt}\n\nТекст:\n{text}"}]
        )
        return message.content[0].text.strip()
    except anthropic.AuthenticationError:
        return "❌ Неверный API-ключ. Проверьте в настройках."
    except Exception as e:
        return f"❌ Ошибка: {e}"

# ─── POPUP WINDOW ─────────────────────────────────────────────────────────────
class PopupMenu:
    def __init__(self):
        self.root = None
        self.result_win = None

    def show_menu(self, selected_text: str):
        """Show action menu near cursor."""
        if self.root and self.root.winfo_exists():
            self.root.destroy()

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e2e")

        # Position near mouse
        try:
            import win32api
            x, y = win32api.GetCursorPos()
        except Exception:
            x, y = 100, 100
        self.root.geometry(f"+{x+10}+{y+10}")

        frame = tk.Frame(self.root, bg="#1e1e2e", padx=2, pady=2)
        frame.pack()

        # Header
        header = tk.Label(frame, text="✦ Текстовый помощник",
                          bg="#313244", fg="#cdd6f4",
                          font=("Segoe UI", 9, "bold"),
                          padx=10, pady=5)
        header.pack(fill="x")

        # Preview of selected text
        preview = selected_text[:60] + ("…" if len(selected_text) > 60 else "")
        tk.Label(frame, text=f'"{preview}"',
                 bg="#1e1e2e", fg="#6c7086",
                 font=("Segoe UI", 8), wraplength=240,
                 padx=8, pady=3).pack(fill="x")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=2)

        # Action buttons
        for action_name in ACTIONS:
            btn = tk.Button(
                frame, text=action_name,
                bg="#1e1e2e", fg="#cdd6f4",
                activebackground="#313244", activeforeground="#89b4fa",
                font=("Segoe UI", 9),
                relief="flat", anchor="w",
                padx=12, pady=4, cursor="hand2",
                command=lambda a=action_name, t=selected_text: self._run_action(a, t)
            )
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#313244"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#1e1e2e"))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=2)

        close_btn = tk.Button(frame, text="✕ Закрыть",
                              bg="#1e1e2e", fg="#6c7086",
                              activebackground="#313244",
                              font=("Segoe UI", 8),
                              relief="flat", padx=12, pady=3,
                              cursor="hand2",
                              command=self.root.destroy)
        close_btn.pack(fill="x")

        # Close on click outside
        self.root.bind("<FocusOut>", lambda e: self._close_if_unfocused())
        self.root.focus_force()
        self.root.mainloop()

    def _close_if_unfocused(self):
        try:
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass

    def _run_action(self, action_name: str, text: str):
        try:
            if self.root and self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass
        threading.Thread(target=self._show_result, args=(action_name, text), daemon=True).start()

    def _show_result(self, action_name: str, text: str):
        result = call_claude(action_name, text)
        self._open_result_window(action_name, text, result)

    def _open_result_window(self, action_name, original, result):
        win = tk.Tk()
        win.title(action_name)
        win.configure(bg="#1e1e2e")
        win.attributes("-topmost", True)
        win.geometry("480x360")
        win.resizable(True, True)

        # Try center on screen
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - 480) // 2
        y = (sh - 360) // 2
        win.geometry(f"480x360+{x}+{y}")

        tk.Label(win, text=action_name, bg="#313244", fg="#89b4fa",
                 font=("Segoe UI", 11, "bold"), padx=10, pady=8).pack(fill="x")

        tk.Label(win, text="Результат:", bg="#1e1e2e", fg="#a6adc8",
                 font=("Segoe UI", 9), anchor="w", padx=10).pack(fill="x")

        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=("Segoe UI", 10),
                                         bg="#313244", fg="#cdd6f4",
                                         insertbackground="#cdd6f4",
                                         relief="flat", padx=8, pady=8)
        txt.pack(fill="both", expand=True, padx=10, pady=4)
        txt.insert("1.0", result)

        btn_frame = tk.Frame(win, bg="#1e1e2e")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        def copy_result():
            pyperclip.copy(txt.get("1.0", tk.END).strip())
            copy_btn.config(text="✓ Скопировано!")
            win.after(1500, lambda: copy_btn.config(text="📋 Копировать"))

        copy_btn = tk.Button(btn_frame, text="📋 Копировать",
                             bg="#89b4fa", fg="#1e1e2e",
                             font=("Segoe UI", 9, "bold"),
                             relief="flat", padx=12, pady=5,
                             cursor="hand2", command=copy_result)
        copy_btn.pack(side="left", padx=(0, 6))

        tk.Button(btn_frame, text="✕ Закрыть",
                  bg="#313244", fg="#cdd6f4",
                  font=("Segoe UI", 9),
                  relief="flat", padx=12, pady=5,
                  cursor="hand2", command=win.destroy).pack(side="left")

        win.mainloop()

popup = PopupMenu()

# ─── HOTKEY LISTENER ──────────────────────────────────────────────────────────
last_clipboard = ""

def on_hotkey():
    global last_clipboard
    # Save current clipboard
    try:
        original_clip = pyperclip.paste()
    except Exception:
        original_clip = ""

    # Simulate Ctrl+C to copy selection
    keyboard.send("ctrl+c")
    time.sleep(0.15)

    try:
        selected = pyperclip.paste()
    except Exception:
        selected = ""

    if not selected or selected == original_clip:
        return  # Nothing new selected

    if selected.strip():
        threading.Thread(target=popup.show_menu, args=(selected,), daemon=True).start()

# ─── SETTINGS WINDOW ──────────────────────────────────────────────────────────
def open_settings():
    win = tk.Tk()
    win.title("Настройки — Текстовый помощник")
    win.configure(bg="#1e1e2e")
    win.geometry("440x220")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"440x220+{(sw-440)//2}+{(sh-220)//2}")

    tk.Label(win, text="⚙️ Настройки", bg="#313244", fg="#89b4fa",
             font=("Segoe UI", 12, "bold"), padx=10, pady=10).pack(fill="x")

    tk.Label(win, text="Anthropic API Key:", bg="#1e1e2e", fg="#a6adc8",
             font=("Segoe UI", 9), anchor="w", padx=14).pack(fill="x", pady=(10, 2))

    entry = tk.Entry(win, font=("Segoe UI", 9), bg="#313244", fg="#cdd6f4",
                     insertbackground="#cdd6f4", relief="flat",
                     show="•", width=50)
    entry.pack(fill="x", padx=14)
    entry.insert(0, load_config().get("api_key", ""))

    tk.Label(win, text="Получить ключ: console.anthropic.com",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8),
             anchor="w", padx=14).pack(fill="x", pady=(4, 0))

    tk.Label(win, text="Горячая клавиша: Ctrl + Shift + A (выделите текст сначала)",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8),
             anchor="w", padx=14).pack(fill="x", pady=(2, 0))

    def save():
        cfg = load_config()
        cfg["api_key"] = entry.get().strip()
        save_config(cfg)
        win.destroy()

    btn_f = tk.Frame(win, bg="#1e1e2e")
    btn_f.pack(pady=14)
    tk.Button(btn_f, text="💾 Сохранить", bg="#89b4fa", fg="#1e1e2e",
              font=("Segoe UI", 9, "bold"), relief="flat",
              padx=14, pady=6, cursor="hand2", command=save).pack(side="left", padx=6)
    tk.Button(btn_f, text="Отмена", bg="#313244", fg="#cdd6f4",
              font=("Segoe UI", 9), relief="flat",
              padx=14, pady=6, cursor="hand2", command=win.destroy).pack(side="left")

    win.mainloop()

# ─── TRAY ICON ────────────────────────────────────────────────────────────────
def create_tray_image():
    img = Image.new("RGB", (64, 64), color="#1e1e2e")
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill="#89b4fa")
    d.text((22, 18), "T", fill="#1e1e2e")
    return img

def run_tray():
    menu = Menu(
        MenuItem("⚙️ Настройки", lambda icon, item: threading.Thread(target=open_settings, daemon=True).start()),
        MenuItem("❌ Выход", lambda icon, item: (icon.stop(), os._exit(0)))
    )
    icon = Icon("TextAssistant", create_tray_image(),
                "Текстовый помощник\nCtrl+Shift+A", menu)
    icon.run()

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Register hotkey: Ctrl + Shift + A
    keyboard.add_hotkey("ctrl+shift+a", on_hotkey)

    # Show settings on first launch if no API key
    if not load_config().get("api_key"):
        threading.Thread(target=open_settings, daemon=True).start()

    print("✅ Текстовый помощник запущен.")
    print("   Выделите текст в любом приложении → нажмите Ctrl+Shift+A")
    print("   Иконка в трее → Настройки (введите API-ключ)")

    # Tray in main thread
    run_tray()
