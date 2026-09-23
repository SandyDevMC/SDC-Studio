"""Центральное оформление SDC-Studio: светлая/тёмная тема и общие стили."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class ThemeColors:
    bg: str
    card: str
    input_bg: str
    fg: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    selection: str
    error: str


LIGHT = ThemeColors(
    bg="#f4f6f8",
    card="#ffffff",
    input_bg="#ffffff",
    fg="#1d2430",
    muted="#667085",
    border="#d0d5dd",
    accent="#5b5bd6",
    accent_hover="#4f46b8",
    selection="#dfe5ff",
    error="#b42318",
)

DARK = ThemeColors(
    bg="#111318",
    card="#1b1f27",
    input_bg="#151922",
    fg="#f2f4f7",
    muted="#98a2b3",
    border="#303744",
    accent="#8b82ff",
    accent_hover="#9a93ff",
    selection="#30365a",
    error="#ff7185",
)


def apply_ttk_theme(root: tk.Misc, dark: bool) -> ThemeColors:
    """Настраивает ttk и возвращает активную палитру."""
    colors = DARK if dark else LIGHT
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=colors.bg)

    style.configure("TFrame", background=colors.bg)
    style.configure("Card.TFrame", background=colors.card)
    style.configure("Toolbar.TFrame", background=colors.card)
    style.configure("TLabel", background=colors.bg, foreground=colors.fg)
    style.configure("Title.TLabel", background=colors.bg, foreground=colors.fg,
                    font=("TkDefaultFont", 18, "bold"))
    style.configure("Subtitle.TLabel", background=colors.bg, foreground=colors.muted,
                    font=("TkDefaultFont", 10))
    style.configure("Section.TLabel", background=colors.bg, foreground=colors.fg,
                    font=("TkDefaultFont", 12, "bold"))
    style.configure("CardTitle.TLabel", background=colors.card, foreground=colors.fg,
                    font=("TkDefaultFont", 12, "bold"))
    style.configure("CardText.TLabel", background=colors.card, foreground=colors.muted)
    style.configure("Muted.TLabel", background=colors.bg, foreground=colors.muted)
    style.configure("CardMuted.TLabel", background=colors.card, foreground=colors.muted)
    style.configure("Error.TLabel", background=colors.bg, foreground=colors.error)
    style.configure("CardError.TLabel", background=colors.card, foreground=colors.error)

    style.configure(
        "TButton",
        background=colors.card,
        foreground=colors.fg,
        bordercolor=colors.border,
        lightcolor=colors.card,
        darkcolor=colors.border,
        padding=(12, 7),
        relief="flat",
        focusthickness=1,
    )
    style.map(
        "TButton",
        background=[("active", colors.accent_hover), ("pressed", colors.accent)],
        foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
        bordercolor=[("active", colors.accent), ("pressed", colors.accent)],
    )
    style.configure(
        "Accent.TButton",
        background=colors.accent,
        foreground="#ffffff",
        bordercolor=colors.accent,
        padding=(14, 9),
        font=("TkDefaultFont", 10, "bold"),
    )
    style.map("Accent.TButton", background=[("active", colors.accent_hover), ("pressed", colors.accent)])
    style.configure(
        "Subtle.TButton",
        background=colors.bg,
        foreground=colors.fg,
        bordercolor=colors.border,
    )
    style.map("Subtle.TButton", background=[("active", colors.selection)])

    style.configure(
        "TEntry",
        fieldbackground=colors.input_bg,
        foreground=colors.fg,
        insertcolor=colors.fg,
        bordercolor=colors.border,
        lightcolor=colors.border,
        darkcolor=colors.border,
        padding=7,
    )
    style.map("TEntry", bordercolor=[("focus", colors.accent)])
    style.configure(
        "TCombobox",
        fieldbackground=colors.input_bg,
        foreground=colors.fg,
        background=colors.input_bg,
        arrowcolor=colors.muted,
        bordercolor=colors.border,
        lightcolor=colors.border,
        darkcolor=colors.border,
        padding=6,
    )
    style.map("TCombobox", fieldbackground=[("readonly", colors.input_bg)],
              foreground=[("readonly", colors.fg)], bordercolor=[("focus", colors.accent)])

    style.configure("TCheckbutton", background=colors.bg, foreground=colors.fg)
    style.map("TCheckbutton", background=[("active", colors.bg)], foreground=[("active", colors.fg)])

    style.configure(
        "Treeview",
        background=colors.card,
        fieldbackground=colors.card,
        foreground=colors.fg,
        bordercolor=colors.border,
        rowheight=30,
    )
    style.map(
        "Treeview",
        background=[("selected", colors.selection)],
        foreground=[("selected", colors.fg)],
    )
    style.configure("Treeview.Heading", background=colors.bg, foreground=colors.muted,
                    font=("TkDefaultFont", 9, "bold"), padding=(8, 7))
    style.map("Treeview.Heading", background=[("active", colors.selection)], foreground=[("active", colors.fg)])

    style.configure("Horizontal.TSeparator", background=colors.border)
    style.configure("Vertical.TSeparator", background=colors.border)
    style.configure("TScrollbar", background=colors.card, troughcolor=colors.bg,
                    bordercolor=colors.border, arrowcolor=colors.muted)

    return colors


def style_tk_text(widget: tk.Text, colors: ThemeColors, *, border: bool = True) -> None:
    widget.configure(
        background=colors.input_bg,
        foreground=colors.fg,
        insertbackground=colors.fg,
        selectbackground=colors.selection,
        selectforeground=colors.fg,
        highlightbackground=colors.border,
        highlightcolor=colors.accent,
        highlightthickness=1 if border else 0,
        relief="flat",
        padx=8,
        pady=7,
    )


def style_tk_listbox(widget: tk.Listbox, colors: ThemeColors) -> None:
    widget.configure(
        background=colors.input_bg,
        foreground=colors.fg,
        selectbackground=colors.selection,
        selectforeground=colors.fg,
        highlightbackground=colors.border,
        highlightcolor=colors.accent,
        highlightthickness=1,
        relief="flat",
        activestyle="none",
    )


def style_tk_canvas(widget: tk.Canvas, colors: ThemeColors) -> None:
    widget.configure(background=colors.bg, highlightthickness=0)
