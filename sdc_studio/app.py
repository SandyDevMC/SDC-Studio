"""Главное окно SDC-Studio и обработчики действий пользователя."""

from __future__ import annotations

import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import constants, png_utils, schema
from .localization import LocalizationDialog
from .models import Pack, PackItem, build_pack_item_from_wizard_values
from .settings import load_settings, save_settings
from .theme import apply_ttk_theme
from .ui_items import ItemListFrame
from .ui_welcome import WelcomeFrame
from .wizard import WizardDialog

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False


class App:
    def __init__(self) -> None:
        self.root = TkinterDnD.Tk() if _DND_AVAILABLE else tk.Tk()
        self.root.title(constants.APP_TITLE)
        self.root.geometry("980x680")
        self.root.minsize(760, 540)

        saved = load_settings()
        self.dark_mode = bool(saved.get("dark_mode", False))
        self.colors = apply_ttk_theme(self.root, self.dark_mode)

        self.pack: Pack | None = None
        self.current_frame: ttk.Frame | None = None

        self._build_header()
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)
        self.root.bind("<Control-n>", lambda _e: self._on_create_pack())
        self.root.bind("<Control-o>", lambda _e: self._on_load_pack())
        self.root.bind("<Control-s>", lambda _e: self._on_save() if self.pack else None)
        self._show_welcome()

    def _build_header(self) -> None:
        self.header = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(18, 11))
        self.header.pack(fill="x", side="top")

        ttk.Label(self.header, text=constants.APP_TITLE, style="CardTitle.TLabel").pack(side="left")
        self.theme_btn = ttk.Button(self.header, command=self._toggle_theme, style="Subtle.TButton")
        self.theme_btn.pack(side="right")
        self._refresh_theme_button()

        ttk.Separator(self.root, orient="horizontal").pack(fill="x")
        self.content = ttk.Frame(self.root)
        self.content.pack(fill="both", expand=True)

    def _refresh_theme_button(self) -> None:
        self.theme_btn.config(text="Светлая тема" if self.dark_mode else "Тёмная тема")

    def _toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.colors = apply_ttk_theme(self.root, self.dark_mode)
        save_settings({"dark_mode": self.dark_mode})
        self._refresh_theme_button()
        if isinstance(self.current_frame, WelcomeFrame):
            self.current_frame.apply_theme(self.colors)
        self.root.update_idletasks()

    def run(self) -> None:
        self.root.mainloop()

    # -- переключение экранов ---------------------------------------------

    def _clear_frame(self) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def _show_welcome(self) -> None:
        self._clear_frame()
        frame = WelcomeFrame(
            self.content, on_create=self._on_create_pack, on_load=self._on_load_pack,
            dnd_available=_DND_AVAILABLE, colors=self.colors,
        )
        frame.pack(fill="both", expand=True)
        self.current_frame = frame
        if _DND_AVAILABLE:
            frame.drop_zone.drop_target_register(DND_FILES)
            frame.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

    def _show_items(self) -> None:
        assert self.pack is not None
        self._clear_frame()
        frame = ItemListFrame(
            self.content,
            on_create_item=self._on_create_item,
            on_edit_item=self._on_edit_item,
            on_delete_item=self._on_delete_item,
            on_save=self._on_save,
            on_save_as=self._on_save_as,
            on_pack_settings=self._on_pack_settings,
            on_close_pack=self._on_close_pack,
        )
        frame.pack(fill="both", expand=True)
        self.current_frame = frame
        frame.show_pack(self.pack)

    # -- экран приветствия -------------------------------------------------

    def _on_create_pack(self) -> None:
        self.pack = Pack.new_empty()
        self._show_items()

    def _on_load_pack(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть пак одежды",
            filetypes=constants.ARCHIVE_FILE_TYPES,
        )
        if path:
            self._load_pack_from_path(Path(path))

    def _on_drop(self, event) -> None:
        paths = self.root.tk.splitlist(event.data)
        if not paths:
            return
        path = Path(paths[0])
        if path.suffix.lower() not in (".cloth", ".zip"):
            messagebox.showerror(
                constants.APP_TITLE,
                "Поддерживаются только файлы .cloth и .zip.",
                parent=self.root,
            )
            return
        self._load_pack_from_path(path)

    def _load_pack_from_path(self, path: Path) -> None:
        try:
            pack, warnings = Pack.load(path)
        except (OSError, zipfile.BadZipFile) as e:
            messagebox.showerror(
                constants.APP_TITLE, f"Не удалось открыть пак:\n{e}", parent=self.root
            )
            return
        self.pack = pack
        self._show_items()
        if warnings:
            messagebox.showwarning(
                constants.APP_TITLE,
                "Пак открыт, но есть замечания:\n\n" + "\n".join(f"• {w}" for w in warnings),
                parent=self.root,
            )

    # -- экран пака: предметы ---------------------------------------------

    def _on_create_item(self) -> None:
        self._open_item_wizard(editing_folder=None)

    def _on_edit_item(self, folder: str) -> None:
        self._open_item_wizard(editing_folder=folder)

    def _on_delete_item(self, folder: str) -> None:
        assert self.pack is not None
        item = self.pack.get_by_folder(folder)
        if item is None:
            return
        if messagebox.askyesno(
            constants.APP_TITLE,
            f"Удалить предмет «{item.name}»?\n\nПапка: {folder}",
            parent=self.root,
        ):
            self.pack.remove_item(folder)
            self._show_items()

    def _open_item_wizard(self, editing_folder: str | None) -> None:
        assert self.pack is not None
        existing = self.pack.get_by_folder(editing_folder) if editing_folder else None

        context = {
            "existing_folders": self.pack.folder_names(),
            "existing_ids": self.pack.item_ids(),
            "editing_folder": editing_folder,
            "editing_id": existing.id if existing else None,
        }
        file_schema = schema.build_item_schema(context)

        initial_values: dict = {}
        field_info: dict[str, str] = {}
        if existing:
            initial_values = {
                "folder": existing.folder,
                "id": existing.id,
                "name": existing.name,
                "description": "\n".join(existing.description),
                "slot": existing.slot,
                "kind": existing.kind,
                "armor": existing.armor,
                "toughness": existing.toughness,
                "layer": existing.layer or constants.LAYER_DEFAULT,
                "use_priority": existing.priority is not None,
                "priority": existing.priority if existing.priority is not None else 20,
            }
            field_info["texture_path"] = self._describe_current_image(
                existing.texture_filename, existing.texture_bytes)
            field_info["icon_path"] = self._describe_current_image(
                existing.icon_filename, existing.icon_bytes)

        wiz = WizardDialog(
            self.root, file_schema, initial_values=initial_values, field_info=field_info,
            finish_label="Сохранить изменения" if existing else "Создать предмет",
            colors=self.colors,
        )
        self.root.wait_window(wiz)
        if wiz.result is None:
            return

        item = build_pack_item_from_wizard_values(wiz.result, existing=existing)
        if existing:
            self.pack.replace_item(editing_folder, item)
        else:
            self.pack.add_item(item)

        self._offer_localization(item)
        self._show_items()

    @staticmethod
    def _describe_current_image(filename: str, data: bytes) -> str:
        if not data:
            return f"Текущий файл: {filename} (данных нет)."
        try:
            w, h = png_utils.read_png_size(data)
            return f"Текущий файл: {filename} · {w}×{h} · {len(data):,} байт. Оставьте поле пустым, чтобы сохранить его.".replace(",", " ")
        except png_utils.InvalidPngError:
            return f"Текущий файл: {filename} · {len(data):,} байт.".replace(",", " ")

    def _offer_localization(self, item: PackItem) -> None:
        assert self.pack is not None
        if not messagebox.askyesno(
            constants.APP_TITLE,
            f"Добавить перевод для «{item.name}» сейчас?",
            parent=self.root,
        ):
            return
        dlg = LocalizationDialog(self.root, item.lang, colors=self.colors)
        self.root.wait_window(dlg)
        if dlg.result is not None:
            item.lang = dlg.result
            self.pack.replace_item(item.folder, item)

    # -- экран пака: настройки/сохранение ----------------------------------

    def _on_pack_settings(self) -> None:
        assert self.pack is not None
        context = {
            "has_manifest": self.pack.manifest_format_version is not None,
            "format_version": self.pack.manifest_format_version,
        }
        file_schema = schema.build_manifest_schema(context)
        initial_values = {
            "has_manifest": context["has_manifest"],
            "format_version": context["format_version"] or constants.PACK_FORMAT_LATEST,
        }
        wiz = WizardDialog(
            self.root, file_schema, initial_values=initial_values,
            finish_label="Сохранить настройки", colors=self.colors,
        )
        self.root.wait_window(wiz)
        if wiz.result is None:
            return
        if wiz.result.get("has_manifest"):
            self.pack.manifest_format_version = wiz.result.get("format_version") or constants.PACK_FORMAT_LATEST
        else:
            self.pack.manifest_format_version = None
        self.pack.dirty = True
        self._show_items()

    def _on_save(self) -> None:
        if self.pack is None:
            return
        if self.pack.source_path is None:
            self._on_save_as()
        else:
            self._write_pack(self.pack.source_path)

    def _on_save_as(self) -> None:
        assert self.pack is not None
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить пак как", defaultextension=".cloth",
            filetypes=constants.ARCHIVE_FILE_TYPES,
        )
        if path:
            self._write_pack(Path(path))

    def _write_pack(self, path: Path) -> None:
        assert self.pack is not None
        if not self.pack.items:
            if not messagebox.askyesno(
                constants.APP_TITLE,
                "В паке пока нет предметов. Сохранить пустой архив?",
                parent=self.root,
            ):
                return
        try:
            self.pack.save(path)
        except OSError as e:
            messagebox.showerror(constants.APP_TITLE, f"Не удалось сохранить пак:\n{e}", parent=self.root)
            return
        self._show_items()
        messagebox.showinfo(constants.APP_TITLE, f"Пак сохранён:\n{path}", parent=self.root)

    def _on_close_pack(self) -> None:
        if self.pack and self.pack.dirty:
            if not messagebox.askyesno(
                constants.APP_TITLE, "Есть несохранённые изменения. Закрыть пак без сохранения?",
                parent=self.root,
            ):
                return
        self.pack = None
        self._show_welcome()

    def _on_app_close(self) -> None:
        if self.pack and self.pack.dirty:
            if not messagebox.askyesno(
                constants.APP_TITLE, "Есть несохранённые изменения. Выйти без сохранения?",
                parent=self.root,
            ):
                return
        self.root.destroy()


def main() -> None:
    App().run()
