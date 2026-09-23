"""
Декларативная схема "вопросов" для файлов пака.

Идея: мастер (wizard.py) ничего не знает про item.json или manifest.json
конкретно - он просто умеет пройти список StepSpec с полями FieldSpec любого
из зарегистрированных ниже "kind" виджетов и вернуть словарь введённых
значений. Сами файлы (что именно спросить, в каком порядке, как
провалидировать и как собрать итоговый JSON) описаны декларативно в этом
модуле как FileSchema и зарегистрированы в FILE_SCHEMAS.

Это и есть тот самый механизм "новые настройки под отдельные файлы", о
котором просил автор: сегодня в реестре два файла - item.json и
manifest.json. Если мод (или чей-то аддон) заведёт третий тип файла со своими
полями - его описание пишется точно так же, отдельным ITEM_SCHEMA-подобным
блоком в этом файле (или в новом модуле, импортированном сюда), и
регистрируется через register_schema(...). Ни wizard.py, ни экраны в ui_*.py
менять не нужно - они работают с любым FileSchema одинаково.

Поддерживаемые сегодня kind у FieldSpec:
  text            - однострочный ввод
  multiline       - многострочный ввод, при сохранении режется по строкам в list[str]
  int             - целое число
  float           - дробное число
  choice          - выпадающий список, только предустановленные значения
  choice_editable - выпадающий список с возможностью ввести своё значение
  file_png        - выбор PNG-файла с диска (валидируется как PNG сразу)
  bool            - да/нет

default и validate могут быть как значением, так и вызываемым объектом
callable(values: dict) -> значение/ошибка - это позволяет полям поздних
шагов подставлять значения по умолчанию на основе уже введённых на ранних
шагах (например id по умолчанию берётся из уже введённого имени папки).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import constants, png_utils


@dataclass
class FieldSpec:
    key: str
    label: str
    kind: str
    required: bool = False
    default: Any = None
    choices: list[tuple[str, str]] | None = None
    help: str = ""
    # validate(value, values) -> сообщение об ошибке или None
    validate: Callable[[Any, dict], str | None] | None = None
    # visible_if(values) -> показывать ли поле, судя по уже введённым на более ранних
    # шагах значениям (например layer/priority скрыты, если type == cape). None = всегда видимо.
    visible_if: Callable[[dict], bool] | None = None

    def resolve_default(self, values: dict) -> Any:
        if callable(self.default):
            return self.default(values)
        return self.default


@dataclass
class StepSpec:
    title: str
    fields: list[FieldSpec]
    # необязательное описание шага, показывается сверху шага в мастере
    intro: str = ""


@dataclass
class FileSchema:
    key: str
    title: str
    steps: list[StepSpec]
    # build(values) -> итоговый словарь для сериализации в JSON (для отладки/предпросмотра;
    # реальную сборку item.json/manifest.json делает models.py, чтобы сохранить незнакомые поля)
    build: Callable[[dict], dict] | None = None


# key -> callable(context: dict) -> FileSchema
# context передаётся из вызывающего кода (например текущий Pack), чтобы схема
# могла провалидировать уникальность id/папки и т.п. на момент вызова.
FILE_SCHEMAS: dict[str, Callable[[dict], FileSchema]] = {}


def register_schema(key: str, factory: Callable[[dict], FileSchema]) -> None:
    FILE_SCHEMAS[key] = factory


# --- общие валидаторы -------------------------------------------------------

def _slugify(text: str) -> str:
    out = []
    for ch in text.strip().lower().replace(" ", "_"):
        out.append(ch if (ch.isalnum() and ch.isascii()) or ch in "_-." else "_")
    slug = "".join(out).strip("_") or "item"
    return slug


def _validate_folder(value: str, values: dict, context: dict) -> str | None:
    value = (value or "").strip()
    if not value:
        return "Имя папки не может быть пустым"
    if "/" in value or "\\" in value:
        return "Имя папки не должно содержать '/' или '\\'"
    existing = context.get("existing_folders", set())
    editing = context.get("editing_folder")
    if value != editing and value in existing:
        return f"Папка '{value}' уже используется другим предметом в этом паке"
    return None


def _validate_id(value: str, values: dict, context: dict) -> str | None:
    value = (value or "").strip()
    if not value:
        return "id не может быть пустым"
    if not constants.ID_PATTERN.match(value):
        return "Разрешены только строчные латинские буквы, цифры, '_', '-', '.'"
    existing = context.get("existing_ids", set())
    editing = context.get("editing_id")
    if value != editing and value in existing:
        return f"id '{value}' уже используется другим предметом в этом паке"
    return None


def _validate_png_field(path: str, values: dict, *, size_check: bool) -> str | None:
    """path - пустая строка допустима (в режиме редактирования значит "оставить как есть"),
    отсутствие файла при создании нового предмета ловит required-проверка в wizard.py."""
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        return f"Не удалось прочитать файл: {e}"
    if not png_utils.is_png(data):
        return "Файл не является корректным PNG"
    if size_check:
        kind = values.get("kind", constants.KIND_DEFAULT)
        expected = constants.CAPE_TEXTURE_SIZE if kind == "cape" else constants.SKIN_TEXTURE_SIZE
        try:
            w, h = png_utils.read_png_size(data)
        except png_utils.InvalidPngError as e:
            return str(e)
        if (w, h) != expected:
            return (f"Размер текстуры {w}x{h}, а для типа '{kind}' нужен "
                    f"{expected[0]}x{expected[1]}")
    return None


# --- item.json ---------------------------------------------------------------

def build_item_schema(context: dict) -> FileSchema:
    """context: {"existing_folders": set[str], "existing_ids": set[str],
    "editing_folder": str|None, "editing_id": str|None}"""

    def id_default(values):
        if context.get("editing_id"):
            return context["editing_id"]
        return _slugify(values.get("folder", "") or values.get("name", ""))

    steps = [
        StepSpec(
            title="Папка предмета",
            intro="Как будет называться папка предмета внутри архива пака.",
            fields=[
                FieldSpec(
                    key="folder", label="Имя папки в архиве", kind="text", required=True,
                    default=context.get("editing_folder") or "",
                    help="Например: sandys_jacket. Влияет только на структуру архива, "
                         "игру не касается напрямую - id ниже важнее.",
                    validate=lambda v, values: _validate_folder(v, values, context),
                ),
            ],
        ),
        StepSpec(
            title="Основное",
            fields=[
                FieldSpec(
                    key="id", label="id предмета", kind="text", required=True,
                    default=id_default,
                    help="Уникальный id (латиница, цифры, '_', '-', '.'). Используется модом "
                         "как путь регистрации предмета.",
                    validate=lambda v, values: _validate_id(v, values, context),
                ),
                FieldSpec(key="name", label="Отображаемое имя", kind="text", required=True, default=""),
                FieldSpec(key="description", label="Описание (тултип)", kind="multiline", default="",
                           help="Каждая строка станет отдельной строкой тултипа."),
            ],
        ),
        StepSpec(
            title="Слот и тип",
            fields=[
                FieldSpec(key="slot", label="Слот Curios", kind="choice_editable", required=True,
                           default="body",
                           choices=[(s, s) for s in constants.SLOT_CHOICES],
                           help="Можно выбрать из списка или ввести свой слот."),
                FieldSpec(key="kind", label="Тип предмета", kind="choice", required=True,
                           default=constants.KIND_DEFAULT,
                           choices=constants.KIND_CHOICES),
            ],
        ),
        StepSpec(
            title="Броня",
            fields=[
                FieldSpec(key="armor", label="Броня (armor)", kind="int", default=0),
                FieldSpec(key="toughness", label="Твёрдость брони (toughness)", kind="float", default=0.0),
            ],
        ),
        StepSpec(
            title="Порядок наложения",
            intro="Не применяется к плащам (type = cape) - у них наложение на скин отсутствует.",
            fields=[
                FieldSpec(key="layer", label="Слой (layer)", kind="choice",
                           default=constants.LAYER_DEFAULT,
                           choices=constants.LAYER_CHOICES,
                           help="Обычный способ задать порядок наложения одежды на скин. "
                                "Игнорируется, если включён ручной priority ниже.",
                           visible_if=lambda values: values.get("kind") != "cape"),
                FieldSpec(key="use_priority", label="Задать priority вручную вместо layer", kind="bool",
                           default=False,
                           visible_if=lambda values: values.get("kind") != "cape"),
                FieldSpec(key="priority", label="Priority (0-100+)", kind="int", default=20,
                           help="Учитывается только если включено 'Задать priority вручную' выше.",
                           visible_if=lambda values: values.get("kind") != "cape"),
            ],
        ),
        StepSpec(
            title="Текстура",
            intro="Требуемый размер зависит от типа: skin - 64x64, cape - 64x32.",
            fields=[
                FieldSpec(key="texture_path", label="Файл texture.png", kind="file_png",
                           required=not context.get("editing_folder"),
                           help="Выберите PNG-файл с диска - он будет скопирован в пак.",
                           validate=lambda v, values: _validate_png_field(v, values, size_check=True)),
            ],
        ),
        StepSpec(
            title="Иконка",
            fields=[
                FieldSpec(key="icon_path", label="Файл icon.png", kind="file_png",
                           required=not context.get("editing_folder"),
                           help="Иконка предмета в инвентаре - любой корректный PNG.",
                           validate=lambda v, values: _validate_png_field(v, values, size_check=False)),
            ],
        ),
    ]
    return FileSchema(key="item.json", title="Предмет одежды (item.json)", steps=steps)


register_schema("item.json", build_item_schema)


# --- manifest.json -------------------------------------------------------

def build_manifest_schema(context: dict) -> FileSchema:
    steps = [
        StepSpec(
            title="Настройки пака",
            intro="manifest.json необязателен: без него мод использует последнюю версию формата.",
            fields=[
                FieldSpec(key="has_manifest", label="Добавить manifest.json в пак", kind="bool",
                           default=context.get("has_manifest", False)),
                FieldSpec(key="format_version", label="Версия формата (format_version)", kind="choice",
                           default=context.get("format_version") or constants.PACK_FORMAT_LATEST,
                           choices=constants.PACK_FORMAT_CHOICES,
                           help="Учитывается только если manifest.json добавлен."),
            ],
        ),
    ]
    return FileSchema(key="manifest.json", title="Настройки пака (manifest.json)", steps=steps)


register_schema("manifest.json", build_manifest_schema)
