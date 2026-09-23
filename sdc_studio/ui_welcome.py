"""Стартовый экран SDC-Studio."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import constants
from .theme import ThemeColors, style_tk_canvas


class WelcomeFrame(ttk.Frame):
    def __init__(self, parent, *, on_create, on_load, dnd_available: bool, colors: ThemeColors):
        super().__init__(parent, padding=(32, 28))
        self.on_create = on_create
        self.on_load = on_load
        self.dnd_available = dnd_available
        self.colors = colors

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="Создавайте паки одежды без ручного JSON",
                  style="Title.TLabel", anchor="center").grid(row=0, column=0, sticky="ew", pady=(6, 2))
        ttk.Label(
            self,
            text="Sandy's Dynamic Clothing · создание и редактирование .cloth/.zip",
            style="Subtitle.TLabel", anchor="center",
        ).grid(row=1, column=0, sticky="ew")

        card = ttk.Frame(self, style="Card.TFrame", padding=(28, 26))
        card.grid(row=2, column=0, sticky="nsew", pady=(22, 10))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        ttk.Label(card, text="Начало работы", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Создайте новый пак или откройте уже существующий. Все изменения сохраняются в обычный архив .cloth.",
            style="CardText.TLabel", wraplength=720, justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(6, 18))

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)
        ttk.Button(actions, text="Создать новый пак", command=self.on_create,
                   style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 7), ipady=7)
        ttk.Button(actions, text="Открыть готовый пак", command=self.on_load,
                   style="TButton").grid(row=0, column=1, sticky="ew", padx=(7, 0), ipady=7)

        zone = tk.Frame(card, bg=colors.card, highlightbackground=colors.border,
                        highlightcolor=colors.border, highlightthickness=1)
        zone.grid(row=3, column=0, sticky="nsew", pady=(24, 0))
        zone.grid_propagate(False)
        zone.bind("<Button-1>", lambda _e: self.on_load())
        zone.grid_rowconfigure(0, weight=1)
        zone.grid_columnconfigure(0, weight=1)
        self.drop_zone = zone

        self.drop_label = tk.Label(
            zone,
            text=self._drop_zone_text(),
            bg=colors.card,
            fg=colors.muted,
            font=("TkDefaultFont", 10),
            justify="center",
            wraplength=680,
            cursor="hand2",
        )
        self.drop_label.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.drop_label.bind("<Button-1>", lambda _e: self.on_load())
        self.drop_label.bind("<Configure>", self._fit_drop_text)

    def _drop_zone_text(self) -> str:
        if self.dnd_available:
            return "Перетащите сюда файл .cloth или .zip\nили нажмите здесь, чтобы выбрать его вручную"
        return "Перетаскивание отключено: установите tkinterdnd2, чтобы включить его.\nИли нажмите здесь, чтобы выбрать .cloth / .zip вручную."

    def _fit_drop_text(self, _event=None) -> None:
        self.drop_label.configure(wraplength=max(260, self.drop_label.winfo_width() - 36))

    def apply_theme(self, colors: ThemeColors) -> None:
        self.colors = colors
        self.drop_zone.configure(bg=colors.card, highlightbackground=colors.border, highlightcolor=colors.border)
        self.drop_label.configure(bg=colors.card, fg=colors.muted)
