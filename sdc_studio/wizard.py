"""Универсальный пошаговый мастер SDC-Studio."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from . import constants
from .schema import FieldSpec, FileSchema
from .theme import ThemeColors, style_tk_canvas, style_tk_text


class WizardDialog(tk.Toplevel):
    def __init__(self, parent, file_schema: FileSchema, initial_values: dict | None = None,
                 field_info: dict[str, str] | None = None, finish_label: str = "Готово",
                 colors: ThemeColors | None = None):
        super().__init__(parent)
        self.colors = colors
        self.title(f"{constants.APP_TITLE} · {file_schema.title}")
        self.geometry("820x660")
        self.minsize(700, 540)
        self.transient(parent)

        self.schema = file_schema
        self.values: dict = dict(initial_values or {})
        self.field_info = field_info or {}
        self.finish_label = finish_label
        self.result: dict | None = None
        self._step_index = 0
        self._total_steps = len(file_schema.steps) + 1
        self._widgets: dict[str, tuple[FieldSpec, object]] = {}
        self._wrap_labels: list[tuple[ttk.Label, tk.Widget]] = []

        self._build_chrome()
        self._render_step()
        self._center_on_parent(parent)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.grab_set()
        self.bind("<Escape>", lambda _e: self._on_cancel())
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.after(50, self._focus_first_widget)

    def _center_on_parent(self, parent) -> None:
        self.update_idletasks()
        pw = parent.winfo_rootx() + max(0, (parent.winfo_width() - self.winfo_width()) // 2)
        ph = parent.winfo_rooty() + max(0, (parent.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{pw}+{ph}")

    def _build_chrome(self) -> None:
        outer = ttk.Frame(self, padding=(18, 14))
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        self.progress_label = ttk.Label(outer, style="Muted.TLabel")
        self.progress_label.grid(row=0, column=0, sticky="w")
        self.step_title = ttk.Label(outer, style="Section.TLabel")
        self.step_title.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        self.step_intro = ttk.Label(outer, wraplength=740, style="Muted.TLabel", justify="left")
        self.step_intro.grid(row=2, column=0, sticky="new")

        body_shell = ttk.Frame(outer)
        body_shell.grid(row=3, column=0, sticky="nsew", pady=(8, 6))
        outer.rowconfigure(3, weight=1)
        body_shell.rowconfigure(0, weight=1)
        body_shell.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(body_shell, borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(body_shell, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        if self.colors:
            style_tk_canvas(self.canvas, self.colors)

        self.body = ttk.Frame(self.canvas)
        self.body_window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._sync_scroll_region)
        self.canvas.bind("<Configure>", self._resize_body)
        self.canvas.bind("<Enter>", lambda _e: self.canvas.focus_set())
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        self.error_label = ttk.Label(outer, style="Error.TLabel", wraplength=740, justify="left")
        self.error_label.grid(row=4, column=0, sticky="ew", pady=(2, 4))

        nav = ttk.Frame(outer)
        nav.grid(row=5, column=0, sticky="ew", pady=(2, 0))
        self.back_btn = ttk.Button(nav, text="Назад", command=self._on_back)
        self.back_btn.pack(side="left")
        ttk.Button(nav, text="Отмена", command=self._on_cancel, style="Subtle.TButton").pack(side="right")
        self.next_btn = ttk.Button(nav, text="Далее", command=self._on_next, style="Accent.TButton")
        self.next_btn.pack(side="right", padx=(0, 8))

    def _sync_scroll_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_body(self, event) -> None:
        self.canvas.itemconfigure(self.body_window, width=event.width)
        width = max(420, event.width - 20)
        self.step_intro.configure(wraplength=width)
        self.error_label.configure(wraplength=width)
        for label, _ in self._wrap_labels:
            label.configure(wraplength=max(220, width - 210))

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _focus_first_widget(self) -> None:
        for _spec, widget in self._widgets.values():
            try:
                widget.focus_set()
                return
            except tk.TclError:
                pass

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self._widgets.clear()
        self._wrap_labels.clear()
        self.error_label.config(text="")
        self.canvas.yview_moveto(0)

    def _render_step(self) -> None:
        self._clear_body()
        self.progress_label.config(text=f"Шаг {self._step_index + 1} из {self._total_steps}")
        self.back_btn.config(state=("disabled" if self._step_index == 0 else "normal"))

        if self._step_index == len(self.schema.steps):
            self._render_review_step()
            self.next_btn.config(text=self.finish_label, command=self._on_finish)
            return

        self.next_btn.config(text="Далее", command=self._on_next)
        step = self.schema.steps[self._step_index]
        self.step_title.config(text=step.title)
        self.step_intro.config(text=step.intro or "Введите данные ниже.")

        rendered = 0
        for field_spec in step.fields:
            if field_spec.visible_if and not field_spec.visible_if(self.values):
                continue
            self._render_field(field_spec)
            rendered += 1
        if rendered == 0:
            ttk.Label(self.body, text="Этот шаг не нужен для выбранных параметров.",
                      style="Muted.TLabel", wraplength=650).pack(anchor="w", pady=12)

        self.after_idle(self._sync_scroll_region)

    def _render_field(self, field_spec: FieldSpec) -> None:
        row = ttk.Frame(self.body)
        row.pack(fill="x", pady=7)
        row.columnconfigure(1, weight=1)

        label_text = field_spec.label + ("  *" if field_spec.required else "")
        label = ttk.Label(row, text=label_text, wraplength=220, justify="left", anchor="nw")
        label.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        self._wrap_labels.append((label, self.body))

        col = ttk.Frame(row)
        col.grid(row=0, column=1, sticky="ew")
        col.columnconfigure(0, weight=1)

        current = self.values.get(field_spec.key)
        if current is None:
            current = field_spec.resolve_default(self.values)

        widget: object
        if field_spec.kind == "multiline":
            widget = tk.Text(col, height=5, wrap="word")
            widget.insert("1.0", current or "")
            widget.grid(row=0, column=0, sticky="ew")
            if self.colors:
                style_tk_text(widget, self.colors)
        elif field_spec.kind in ("choice", "choice_editable"):
            labels = [lbl for _, lbl in (field_spec.choices or [])]
            values_by_label = {lbl: val for val, lbl in (field_spec.choices or [])}
            var = tk.StringVar()
            current_label = next((lbl for val, lbl in (field_spec.choices or []) if val == current), current)
            var.set(current_label or "")
            state = "readonly" if field_spec.kind == "choice" else "normal"
            widget = ttk.Combobox(col, textvariable=var, values=labels, state=state)
            widget._sdc_var = var  # type: ignore[attr-defined]
            widget._sdc_map = values_by_label  # type: ignore[attr-defined]
            widget.grid(row=0, column=0, sticky="ew")
        elif field_spec.kind == "bool":
            var = tk.BooleanVar(value=bool(current))
            widget = ttk.Checkbutton(col, variable=var, text="Включено")
            widget._sdc_var = var  # type: ignore[attr-defined]
            widget.grid(row=0, column=0, sticky="w")
        elif field_spec.kind == "file_png":
            var = tk.StringVar(value=current or "")
            entry_row = ttk.Frame(col)
            entry_row.grid(row=0, column=0, sticky="ew")
            entry_row.columnconfigure(0, weight=1)
            entry = ttk.Entry(entry_row, textvariable=var, state="readonly")
            entry.grid(row=0, column=0, sticky="ew")
            ttk.Button(entry_row, text="Выбрать…", command=lambda v=var: self._browse_png(v),
                       style="Subtle.TButton").grid(row=0, column=1, padx=(7, 0))
            widget = entry
            widget._sdc_var = var  # type: ignore[attr-defined]
            info = self.field_info.get(field_spec.key)
            if info:
                info_label = ttk.Label(col, text=info, style="Muted.TLabel", wraplength=650, justify="left")
                info_label.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        else:
            var = tk.StringVar(value="" if current is None else str(current))
            widget = ttk.Entry(col, textvariable=var)
            widget._sdc_var = var  # type: ignore[attr-defined]
            widget.grid(row=0, column=0, sticky="ew")

        if field_spec.help:
            help_label = ttk.Label(col, text=field_spec.help, style="Muted.TLabel",
                                   wraplength=650, justify="left")
            help_label.grid(row=2 if field_spec.kind == "file_png" and self.field_info.get(field_spec.key) else 1,
                            column=0, sticky="ew", pady=(5, 0))

        self._widgets[field_spec.key] = (field_spec, widget)

    def _browse_png(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=constants.PNG_FILE_TYPES, title="Выберите PNG")
        if path:
            var.set(path)

    def _render_review_step(self) -> None:
        self.step_title.config(text="Проверка и подтверждение")
        self.step_intro.config(text="Проверьте данные. После подтверждения предмет будет добавлен в текущий пак.")

        for step in self.schema.steps:
            ttk.Separator(self.body, orient="horizontal").pack(fill="x", pady=7)
            ttk.Label(self.body, text=step.title, style="CardTitle.TLabel").pack(anchor="w", pady=(2, 5))
            for field_spec in step.fields:
                if field_spec.visible_if and not field_spec.visible_if(self.values):
                    continue
                if field_spec.key not in self.values:
                    continue
                display = self._format_value_for_review(field_spec, self.values[field_spec.key])
                if display is None:
                    continue
                row = ttk.Frame(self.body)
                row.pack(fill="x", pady=2)
                row.columnconfigure(1, weight=1)
                ttk.Label(row, text=field_spec.label, wraplength=220, justify="left",
                          anchor="nw").grid(row=0, column=0, sticky="nw", padx=(0, 16))
                ttk.Label(row, text=display, wraplength=650, justify="left",
                          anchor="nw").grid(row=0, column=1, sticky="ew")
        self.after_idle(self._sync_scroll_region)

    @staticmethod
    def _format_value_for_review(field_spec: FieldSpec, value) -> str | None:
        if field_spec.kind == "bool":
            return "Включено" if value else "Выключено"
        if field_spec.kind == "multiline":
            return value or "(пусто)"
        if field_spec.kind == "file_png":
            if not value:
                return "(оставить текущий файл)" if not field_spec.required else "(не выбран)"
            return os.path.basename(value)
        if value in (None, ""):
            return None
        return str(value)

    def _collect_step(self) -> bool:
        if self._step_index >= len(self.schema.steps):
            return True
        step = self.schema.steps[self._step_index]
        for field_spec in step.fields:
            if field_spec.key not in self._widgets:
                self.values.setdefault(field_spec.key, field_spec.resolve_default(self.values))
                continue
            field_spec, widget = self._widgets[field_spec.key]
            raw = self._read_widget(field_spec, widget)

            if field_spec.required and (raw is None or raw == "" or raw == []):
                self.error_label.config(text=f"«{field_spec.label}» — заполните это поле.")
                return False

            coerced, error = self._coerce(field_spec, raw)
            if error:
                self.error_label.config(text=f"«{field_spec.label}»: {error}.")
                return False

            if field_spec.validate:
                err = field_spec.validate(coerced, self.values)
                if err:
                    self.error_label.config(text=f"«{field_spec.label}»: {err}.")
                    return False

            self.values[field_spec.key] = coerced
        self.error_label.config(text="")
        return True

    @staticmethod
    def _read_widget(field_spec: FieldSpec, widget):
        if field_spec.kind == "multiline":
            return widget.get("1.0", "end-1c")
        if field_spec.kind in ("choice", "choice_editable"):
            label = widget._sdc_var.get()
            mapping = widget._sdc_map
            return mapping.get(label, label)
        if field_spec.kind == "bool":
            return widget._sdc_var.get()
        return widget._sdc_var.get()

    @staticmethod
    def _coerce(field_spec: FieldSpec, raw) -> tuple[object, str | None]:
        if field_spec.kind == "int":
            text = (raw or "").strip()
            if not text:
                return 0, None
            try:
                return int(text), None
            except ValueError:
                return None, "нужно целое число"
        if field_spec.kind == "float":
            text = (raw or "").strip()
            if not text:
                return 0.0, None
            try:
                return float(text.replace(",", ".")), None
            except ValueError:
                return None, "нужно число"
        if field_spec.kind == "multiline":
            text = (raw or "").strip("\n")
            return (text, None)
        if field_spec.kind == "text":
            return (raw or "").strip(), None
        return raw, None

    def _on_next(self) -> None:
        if not self._collect_step():
            return
        self._step_index += 1
        self._render_step()

    def _on_back(self) -> None:
        self._step_index = max(0, self._step_index - 1)
        self._render_step()

    def _on_finish(self) -> None:
        self.result = dict(self.values)
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()
