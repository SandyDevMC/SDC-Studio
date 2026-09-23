"""Экран содержимого пака."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .models import Pack


class ItemListFrame(ttk.Frame):
    def __init__(
        self, parent, *,
        on_create_item, on_edit_item, on_delete_item,
        on_save, on_save_as, on_pack_settings, on_close_pack,
    ):
        super().__init__(parent, padding=(20, 16))
        self.on_create_item = on_create_item
        self.on_edit_item = on_edit_item
        self.on_delete_item = on_delete_item
        self.on_save = on_save
        self.on_save_as = on_save_as
        self.on_pack_settings = on_pack_settings
        self.on_close_pack = on_close_pack

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(header, style="Section.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Закрыть пак", command=self.on_close_pack,
                   style="Subtle.TButton").grid(row=0, column=1, padx=(8, 0))

        toolbar = ttk.Frame(self)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(toolbar, text="+ Создать предмет", command=self.on_create_item,
                   style="Accent.TButton").pack(side="left")
        self.edit_btn = ttk.Button(toolbar, text="Редактировать", command=self._on_edit_clicked, state="disabled")
        self.edit_btn.pack(side="left", padx=(8, 0))
        self.delete_btn = ttk.Button(toolbar, text="Удалить", command=self._on_delete_clicked, state="disabled")
        self.delete_btn.pack(side="left", padx=(6, 0))

        ttk.Button(toolbar, text="Настройки пака", command=self.on_pack_settings,
                   style="Subtle.TButton").pack(side="right")
        ttk.Button(toolbar, text="Сохранить как…", command=self.on_save_as,
                   style="Subtle.TButton").pack(side="right", padx=(0, 6))
        ttk.Button(toolbar, text="Сохранить", command=self.on_save).pack(side="right", padx=(0, 6))

        table = ttk.Frame(self)
        table.grid(row=2, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)

        columns = ("folder", "id", "name", "slot", "lang")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("folder", text="Папка")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Имя")
        self.tree.heading("slot", text="Слот")
        self.tree.heading("lang", text="Переводы")
        self.tree.column("folder", width=220, minwidth=140, stretch=True)
        self.tree.column("id", width=170, minwidth=120, stretch=True)
        self.tree.column("name", width=240, minwidth=160, stretch=True)
        self.tree.column("slot", width=110, minwidth=90, stretch=False)
        self.tree.column("lang", width=150, minwidth=110, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.empty_label = ttk.Label(
            table,
            text="В этом паке пока нет предметов. Создайте первый предмет кнопкой выше.",
            anchor="center", justify="center", style="Muted.TLabel",
        )

        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, style="Muted.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")
        ttk.Label(footer, text="Ctrl+S — сохранить · двойной клик — редактировать",
                  style="Muted.TLabel").grid(row=0, column=1, sticky="e")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self._on_edit_clicked())
        self.tree.bind("<Return>", lambda _e: self._on_edit_clicked())

    def show_pack(self, pack: Pack) -> None:
        name = pack.source_path.name if pack.source_path else "Новый пак (ещё не сохранён)"
        star = " *" if pack.dirty else ""
        self.title_label.config(text=f"{name}{star}")

        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in sorted(pack.items, key=lambda it: it.folder):
            langs = ", ".join(sorted(item.lang.keys())) or "—"
            self.tree.insert("", "end", iid=item.folder,
                             values=(item.folder, item.id, item.name, item.slot, langs))

        count = len(pack.items)
        self.status_label.config(text=f"{count} {_plural_items(count)} в паке.")
        self.edit_btn.config(state="disabled")
        self.delete_btn.config(state="disabled")
        if count:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def selected_folder(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _on_select(self, _event=None) -> None:
        has_selection = bool(self.tree.selection())
        state = "normal" if has_selection else "disabled"
        self.edit_btn.config(state=state)
        self.delete_btn.config(state=state)

    def _on_edit_clicked(self) -> None:
        folder = self.selected_folder()
        if folder:
            self.on_edit_item(folder)

    def _on_delete_clicked(self) -> None:
        folder = self.selected_folder()
        if folder:
            self.on_delete_item(folder)


def _plural_items(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "предмет"
    if 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return "предмета"
    return "предметов"
