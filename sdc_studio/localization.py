"""Редактор переводов предмета."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from . import constants
from .theme import ThemeColors, style_tk_listbox, style_tk_text


class _PickLocaleDialog(simpledialog.Dialog):
    def __init__(self, parent, taken: set[str], colors: ThemeColors | None = None):
        self.taken = taken
        self.colors = colors
        self.locale_code: str | None = None
        super().__init__(parent, title="Новая локаль")

    def body(self, master):
        ttk.Label(master, text="Выберите или введите код локали (например ru_ru):",
                  wraplength=330, justify="left").grid(row=0, column=0, sticky="w", pady=(0, 7))
        available = [f"{code} — {label}" for code, label in constants.KNOWN_LOCALES if code not in self.taken]
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(master, textvariable=self.var, values=available, width=34)
        self.combo.grid(row=1, column=0, sticky="ew")
        return self.combo

    def apply(self):
        raw = self.var.get().strip()
        code = raw.split(" — ")[0].strip().lower() if raw else ""
        self.locale_code = code


class LocalizationDialog(tk.Toplevel):
    def __init__(self, parent, lang: dict[str, dict], colors: ThemeColors | None = None):
        super().__init__(parent)
        self.colors = colors
        self.title(f"{constants.APP_TITLE} · Переводы")
        self.geometry("760x520")
        self.minsize(680, 450)
        self.transient(parent)

        self.lang: dict[str, dict] = {
            k: {"name": v.get("name"), "description": list(v.get("description", []))}
            for k, v in lang.items()
        }
        self.result: dict[str, dict] | None = None
        self._current_locale: str | None = None

        self._build()
        self._refresh_list()
        self._center_on_parent(parent)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()

    def _center_on_parent(self, parent) -> None:
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=(18, 14))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Локализация предмета", style="Section.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Переводы хранятся отдельно от item.json. Пустая локализация не является ошибкой: тогда мод использует основное имя и описание.",
            style="Muted.TLabel", wraplength=700, justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 12))

        body = ttk.Frame(outer)
        body.grid(row=2, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsw")
        left.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(left, height=14, width=16, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="ns")
        if self.colors:
            style_tk_listbox(self.listbox, self.colors)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        left_buttons = ttk.Frame(left)
        left_buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(left_buttons, text="+ Добавить", command=self._on_add_locale).pack(side="left")
        ttk.Button(left_buttons, text="Удалить", command=self._on_remove_locale,
                   style="Subtle.TButton").pack(side="left", padx=(6, 0))

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(5, weight=1)

        ttk.Label(right, text="Язык", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        self.locale_label = ttk.Label(right, text="Не выбран", style="CardTitle.TLabel")
        self.locale_label.grid(row=1, column=0, sticky="w", pady=(1, 12))

        ttk.Label(right, text="Имя", style="Muted.TLabel").grid(row=2, column=0, sticky="new")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(right, textvariable=self.name_var)
        self.name_entry.grid(row=3, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(right, text="Описание · одна строка на пункт тултипа", style="Muted.TLabel").grid(
            row=4, column=0, sticky="nw")
        self.desc_text = tk.Text(right, height=8, wrap="word")
        self.desc_text.grid(row=5, column=0, sticky="nsew", pady=(2, 8))
        if self.colors:
            style_tk_text(self.desc_text, self.colors)

        ttk.Button(right, text="Сохранить перевод", command=self._on_save_current,
                   style="Subtle.TButton").grid(row=6, column=0, sticky="ew")

        nav = ttk.Frame(outer)
        nav.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(nav, text="Отмена", command=self._on_cancel, style="Subtle.TButton").pack(side="right")
        ttk.Button(nav, text="Готово", command=self._on_finish, style="Accent.TButton").pack(side="right", padx=(0, 8))

        self._set_form_enabled(False)

    def _set_form_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.name_entry.config(state=state)
        self.desc_text.config(state=state)

    def _refresh_list(self, select: str | None = None) -> None:
        self.listbox.delete(0, "end")
        codes = sorted(self.lang.keys())
        for code in codes:
            self.listbox.insert("end", code)
        if select and select in self.lang:
            idx = codes.index(select)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            self._load_locale(select)
        elif not self.lang:
            self._current_locale = None
            self.locale_label.config(text="Не выбран")
            self.name_var.set("")
            self.desc_text.config(state="normal")
            self.desc_text.delete("1.0", "end")
            self._set_form_enabled(False)

    def _on_select(self, _event=None) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        self._load_locale(self.listbox.get(sel[0]))

    def _load_locale(self, code: str) -> None:
        self._current_locale = code
        self.locale_label.config(text=code)
        entry = self.lang.get(code, {})
        self.name_entry.config(state="normal")
        self.name_var.set(entry.get("name") or "")
        self.desc_text.config(state="normal")
        self.desc_text.delete("1.0", "end")
        self.desc_text.insert("1.0", "\n".join(entry.get("description", [])))
        self._set_form_enabled(True)

    def _on_add_locale(self) -> None:
        dlg = _PickLocaleDialog(self, taken=set(self.lang.keys()), colors=self.colors)
        code = dlg.locale_code
        if not code:
            return
        if not constants.LOCALE_PATTERN.match(code):
            messagebox.showerror(constants.APP_TITLE,
                                 "Код локали: строчные латинские буквы, цифры и '_' (например ru_ru).",
                                 parent=self)
            return
        if code in self.lang:
            messagebox.showerror(constants.APP_TITLE, f"Локаль «{code}» уже добавлена.", parent=self)
            return
        self.lang[code] = {"name": None, "description": []}
        self._refresh_list(select=code)

    def _on_remove_locale(self) -> None:
        if not self._current_locale:
            return
        del self.lang[self._current_locale]
        self._current_locale = None
        self._refresh_list()

    def _save_current_silent(self) -> None:
        if not self._current_locale:
            return
        name = self.name_var.get().strip()
        desc_text = self.desc_text.get("1.0", "end-1c").strip("\n")
        description = desc_text.split("\n") if desc_text.strip() else []
        self.lang[self._current_locale] = {"name": name or None, "description": description}

    def _on_save_current(self) -> None:
        if not self._current_locale:
            messagebox.showinfo(constants.APP_TITLE, "Сначала выберите или добавьте локаль.", parent=self)
            return
        self._save_current_silent()
        messagebox.showinfo(constants.APP_TITLE, f"Перевод для «{self._current_locale}» сохранён.", parent=self)

    def _on_finish(self) -> None:
        self._save_current_silent()
        self.result = self.lang
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
