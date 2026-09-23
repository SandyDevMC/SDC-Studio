"""
В памяти студии пак одежды - это Pack: необязательный manifest.json плюс
список PackItem (один на папку с item.json). Это ровно то же дерево,
которое ClothingArchiveParser читает в моде, только с одним сознательным
упрощением: студия предполагает "одна папка - один предмет" (как во всех
трёх примерах из мода - sandys_classics_pack, sandys_frak, sandys_trousers),
а не редкий вариант "один item.json - JSON-массив из нескольких предметов".
Такой массив при загрузке не роняет студию, но помечается предупреждением
и пропускается - см. Pack.load().

Всё, что записывает сама студия, всегда в "простом" формате и полностью
грузится реальным парсером мода без предупреждений.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import constants, png_utils


@dataclass
class PackItem:
    folder: str
    id: str
    name: str
    description: list[str] = field(default_factory=list)
    slot: str = "body"
    kind: str = constants.KIND_DEFAULT           # "skin" | "cape"
    armor: int = 0
    toughness: float = 0.0
    layer: str | None = constants.LAYER_DEFAULT   # None, если используется priority
    priority: int | None = None                   # расширенный ручной режим вместо layer
    texture_filename: str = constants.DEFAULT_TEXTURE_FILENAME
    icon_filename: str = constants.DEFAULT_ICON_FILENAME
    texture_bytes: bytes = b""
    icon_bytes: bytes = b""
    # locale (en_us, ru_ru, ...) -> {"name": str|None, "description": [str, ...]}
    lang: dict[str, dict] = field(default_factory=dict)
    # любые незнакомые студии поля из исходного item.json (например устаревшее
    # "translations") сохраняются как есть и не теряются при повторном сохранении,
    # если автор пака их не трогает через мастер.
    extra_fields: dict = field(default_factory=dict)

    def texture_size_requirement(self) -> tuple[int, int]:
        return constants.CAPE_TEXTURE_SIZE if self.kind == "cape" else constants.SKIN_TEXTURE_SIZE

    def to_item_json(self) -> dict:
        """Собирает item.json ровно в том виде, который ожидает ClothingArchiveParser."""
        obj = dict(self.extra_fields)
        obj["id"] = self.id
        obj["name"] = self.name
        if self.description:
            obj["description"] = list(self.description)
        else:
            obj.pop("description", None)
        obj["slot"] = self.slot
        if self.kind != constants.KIND_DEFAULT:
            obj["type"] = self.kind
        else:
            obj.pop("type", None)
        if self.armor:
            obj["armor"] = self.armor
        else:
            obj.pop("armor", None)
        if self.toughness:
            obj["toughness"] = self.toughness
        else:
            obj.pop("toughness", None)
        # layer и priority взаимоисключающи - как в реальном item.json.
        obj.pop("layer", None)
        obj.pop("priority", None)
        if self.kind != "cape":
            if self.priority is not None:
                obj["priority"] = self.priority
            elif self.layer and self.layer != constants.LAYER_DEFAULT:
                obj["layer"] = self.layer
        if self.texture_filename != constants.DEFAULT_TEXTURE_FILENAME:
            obj["texture"] = self.texture_filename
        else:
            obj.pop("texture", None)
        if self.icon_filename != constants.DEFAULT_ICON_FILENAME:
            obj["icon"] = self.icon_filename
        else:
            obj.pop("icon", None)
        return obj


@dataclass
class Pack:
    items: list[PackItem] = field(default_factory=list)
    manifest_format_version: str | None = None  # None = manifest.json отсутствует (нормально)
    source_path: Path | None = None
    dirty: bool = False

    # -- запросы -------------------------------------------------------

    def folder_names(self) -> set[str]:
        return {it.folder for it in self.items}

    def item_ids(self) -> set[str]:
        return {it.id for it in self.items}

    def get_by_folder(self, folder: str) -> PackItem | None:
        for it in self.items:
            if it.folder == folder:
                return it
        return None

    # -- мутации ---------------------------------------------------------

    def add_item(self, item: PackItem) -> None:
        self.items.append(item)
        self.dirty = True

    def replace_item(self, old_folder: str, item: PackItem) -> None:
        for i, it in enumerate(self.items):
            if it.folder == old_folder:
                self.items[i] = item
                self.dirty = True
                return
        raise KeyError(old_folder)

    def remove_item(self, folder: str) -> None:
        before = len(self.items)
        self.items = [it for it in self.items if it.folder != folder]
        if len(self.items) != before:
            self.dirty = True

    # -- сохранение --------------------------------------------------------

    def save(self, path: Path) -> None:
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if self.manifest_format_version:
                zf.writestr(
                    constants.MANIFEST_ENTRY_NAME,
                    json.dumps({"format_version": self.manifest_format_version}, ensure_ascii=False, indent=2),
                )
            for it in self.items:
                prefix = f"{it.folder}/" if it.folder else ""
                zf.writestr(prefix + "item.json", json.dumps(it.to_item_json(), ensure_ascii=False, indent=2))
                zf.writestr(prefix + it.texture_filename, it.texture_bytes)
                zf.writestr(prefix + it.icon_filename, it.icon_bytes)
                for locale, entry in it.lang.items():
                    payload = {}
                    if entry.get("name"):
                        payload["name"] = entry["name"]
                    if entry.get("description"):
                        payload["description"] = list(entry["description"])
                    if payload:
                        zf.writestr(f"{prefix}lang/{locale}.json", json.dumps(payload, ensure_ascii=False, indent=2))
        self.source_path = path
        self.dirty = False

    # -- загрузка -----------------------------------------------------

    @staticmethod
    def new_empty() -> "Pack":
        return Pack()

    @staticmethod
    def load(path: Path) -> tuple["Pack", list[str]]:
        """Читает .cloth/.zip. Возвращает (Pack, список предупреждений).

        Ошибка на одном предмете не прерывает загрузку остальных - ровно как
        в ClothingLoader на стороне мода: одна битая папка не должна мешать
        редактировать весь остальной пак.
        """
        warnings: list[str] = []
        pack = Pack(source_path=path)

        with zipfile.ZipFile(path, "r") as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]

            manifest_entry = next(
                (n for n in names if n.lower() == constants.MANIFEST_ENTRY_NAME), None
            )
            if manifest_entry:
                try:
                    manifest = json.loads(zf.read(manifest_entry).decode("utf-8"))
                    version = manifest.get("format_version")
                    if version in ("1.0", "1.1"):
                        pack.manifest_format_version = version
                    elif version is not None:
                        warnings.append(
                            f"manifest.json: неизвестная format_version '{version}' - проигнорирована"
                        )
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
                    warnings.append(f"manifest.json не удалось разобрать: {e}")

            item_json_entries = [n for n in names if Path(n).name.lower() == "item.json"]
            if not item_json_entries:
                warnings.append("В архиве не найдено ни одного item.json")
                return pack, warnings

            for entry_name in item_json_entries:
                folder = str(Path(entry_name).parent)
                folder = "" if folder == "." else folder
                try:
                    raw = json.loads(zf.read(entry_name).decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    warnings.append(f"{entry_name}: некорректный JSON ({e}) - предмет пропущен")
                    continue

                if isinstance(raw, list):
                    warnings.append(
                        f"{entry_name}: содержит массив из нескольких предметов - "
                        "такой формат студия пока не редактирует, папка пропущена"
                    )
                    continue
                if not isinstance(raw, dict):
                    warnings.append(f"{entry_name}: корень должен быть объектом - предмет пропущен")
                    continue

                try:
                    item, item_warnings = Pack._parse_item(zf, names, folder, raw, entry_name)
                except ValueError as e:
                    warnings.append(f"{entry_name}: {e} - предмет пропущен")
                    continue
                warnings.extend(item_warnings)
                pack.items.append(item)

        pack.dirty = False
        return pack, warnings

    @staticmethod
    def _parse_item(zf: zipfile.ZipFile, all_names: list[str], folder: str, raw: dict, entry_name: str):
        warnings: list[str] = []

        item_id = raw.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("отсутствует обязательное поле 'id'")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("отсутствует обязательное поле 'name'")
        slot = raw.get("slot")
        if not isinstance(slot, str) or not slot.strip():
            raise ValueError("отсутствует обязательное поле 'slot'")

        description = raw.get("description", [])
        if isinstance(description, str):
            description = [description]
        elif not isinstance(description, list):
            description = []

        kind = raw.get("type", constants.KIND_DEFAULT)
        if kind not in ("skin", "cape"):
            warnings.append(f"{entry_name}: неизвестный type '{kind}', принято как 'skin'")
            kind = "skin"

        armor = raw.get("armor", 0)
        try:
            armor = max(0, int(armor))
        except (TypeError, ValueError):
            armor = 0
        toughness = raw.get("toughness", 0.0)
        try:
            toughness = max(0.0, float(toughness))
        except (TypeError, ValueError):
            toughness = 0.0

        priority = None
        layer = None
        if kind != "cape":
            if "priority" in raw:
                try:
                    priority = int(raw["priority"])
                except (TypeError, ValueError):
                    layer = constants.LAYER_DEFAULT
            else:
                layer = raw.get("layer", constants.LAYER_DEFAULT)
                if layer not in dict(constants.LAYER_CHOICES):
                    warnings.append(f"{entry_name}: неизвестный layer '{layer}', принято как 'base'")
                    layer = constants.LAYER_DEFAULT

        texture_filename = raw.get("texture") or constants.DEFAULT_TEXTURE_FILENAME
        icon_filename = raw.get("icon") or constants.DEFAULT_ICON_FILENAME

        texture_bytes = Pack._read_sibling(zf, all_names, folder, texture_filename)
        if texture_bytes is None:
            raise ValueError(f"не найден файл текстуры '{texture_filename}'")
        icon_bytes = Pack._read_sibling(zf, all_names, folder, icon_filename)
        if icon_bytes is None:
            raise ValueError(f"не найден файл иконки '{icon_filename}'")

        lang = {}
        lang_prefix = f"{folder}/{constants.LANG_FOLDER}/" if folder else f"{constants.LANG_FOLDER}/"
        for n in all_names:
            if not n.startswith(lang_prefix):
                continue
            rest = n[len(lang_prefix):]
            if "/" in rest or not rest.lower().endswith(".json"):
                continue
            locale = rest[: -len(".json")].lower()
            if not constants.LOCALE_PATTERN.match(locale):
                warnings.append(f"{n}: имя файла перевода не похоже на код локали - пропущен")
                continue
            try:
                section = json.loads(zf.read(n).decode("utf-8"))
                lang[locale] = {
                    "name": section.get("name"),
                    "description": section.get("description", []) if isinstance(section.get("description"), list) else [],
                }
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                warnings.append(f"{n}: не удалось разобрать перевод ({e}) - пропущен")

        known_keys = {
            "id", "name", "description", "slot", "type", "armor", "toughness",
            "layer", "priority", "texture", "icon", "translations",
        }
        extra_fields = {k: v for k, v in raw.items() if k not in known_keys}

        item = PackItem(
            folder=folder,
            id=item_id,
            name=name,
            description=[str(x) for x in description],
            slot=slot,
            kind=kind,
            armor=armor,
            toughness=toughness,
            layer=layer,
            priority=priority,
            texture_filename=texture_filename,
            icon_filename=icon_filename,
            texture_bytes=texture_bytes,
            icon_bytes=icon_bytes,
            lang=lang,
            extra_fields=extra_fields,
        )
        return item, warnings

    @staticmethod
    def _read_sibling(zf: zipfile.ZipFile, all_names: list[str], folder: str, filename: str) -> bytes | None:
        candidate = f"{folder}/{filename}" if folder else filename
        if candidate in all_names:
            return zf.read(candidate)
        # Как и в ClothingArchiveParser.readSibling: ищем файл с таким именем
        # где угодно в архиве, если рядом с item.json его нет.
        for n in all_names:
            if Path(n).name.lower() == filename.lower():
                return zf.read(n)
        return None


def build_pack_item_from_wizard_values(values: dict, *, existing: PackItem | None = None) -> PackItem:
    """Превращает словарь значений, собранный WizardDialog по item.json-схеме
    (см. schema.build_item_schema), в PackItem.

    Не зависит от tkinter - вся логика тут проверяется юнит-тестами напрямую,
    без необходимости поднимать GUI. app.py вызывает эту функцию после того,
    как пользователь нажал "Готово" в мастере.

    existing - предмет, который редактируется (для сохранения текстуры/иконки/
    lang/прочих полей, если пользователь их не менял в этом проходе мастера).
    None - создаётся новый предмет с нуля.
    """
    description_text = values.get("description") or ""
    description = description_text.split("\n") if description_text.strip() else []

    kind = values.get("kind", constants.KIND_DEFAULT)
    layer: str | None = None
    priority: int | None = None
    if kind != "cape":
        if values.get("use_priority"):
            priority = values.get("priority", 20)
        else:
            layer = values.get("layer", constants.LAYER_DEFAULT)

    texture_filename = existing.texture_filename if existing else constants.DEFAULT_TEXTURE_FILENAME
    texture_bytes = existing.texture_bytes if existing else b""
    if values.get("texture_path"):
        texture_bytes = Path(values["texture_path"]).read_bytes()

    icon_filename = existing.icon_filename if existing else constants.DEFAULT_ICON_FILENAME
    icon_bytes = existing.icon_bytes if existing else b""
    if values.get("icon_path"):
        icon_bytes = Path(values["icon_path"]).read_bytes()

    return PackItem(
        folder=values["folder"],
        id=values["id"],
        name=values["name"],
        description=description,
        slot=values["slot"],
        kind=kind,
        armor=values.get("armor", 0),
        toughness=values.get("toughness", 0.0),
        layer=layer,
        priority=priority,
        texture_filename=texture_filename,
        icon_filename=icon_filename,
        texture_bytes=texture_bytes,
        icon_bytes=icon_bytes,
        lang=dict(existing.lang) if existing else {},
        extra_fields=dict(existing.extra_fields) if existing else {},
    )
