"""
Константы, отражающие реальную схему архива одежды мода Sandy's Dynamic Clothing.

Все значения здесь синхронизированы с исходниками мода
(com.sandydev.dcs.clothing.*: ClothingKind, ClothingLayer, ClothingSlots,
ClothingArchiveParser, ClothingPackFormat) по состоянию на момент разработки
студии. Если мод в будущем расширит схему (новые слоты, новый layer,
новая версия формата пака) - обычно достаточно поправить константы тут и,
при необходимости, sdc_studio/schema.py, не трогая остальной код студии.
"""

from __future__ import annotations

import re

APP_TITLE = "SDC-Studio"
APP_VERSION = "0.2.0"

# --- item.json -------------------------------------------------------------

# com.sandydev.dcs.clothing.ClothingArchiveParser.ID_PATTERN
ID_PATTERN = re.compile(r"^[a-z0-9_.-]+$")

# com.sandydev.dcs.clothing.ClothingArchiveParser.REQUIRED_TEXTURE_SIZE
SKIN_TEXTURE_SIZE = (64, 64)
# com.sandydev.dcs.clothing.ClothingArchiveParser.REQUIRED_CAPE_WIDTH/HEIGHT
CAPE_TEXTURE_SIZE = (64, 32)

DEFAULT_TEXTURE_FILENAME = "texture.png"
DEFAULT_ICON_FILENAME = "icon.png"

# com.sandydev.dcs.clothing.ClothingKind
KIND_CHOICES = [
    ("skin", "Обычная одежда (skin) - накладывается на скин игрока"),
    ("cape", "Плащ (cape) - отдельная текстура 64x32, слой/приоритет игнорируется"),
]
KIND_DEFAULT = "skin"

# com.sandydev.dcs.clothing.ClothingLayer, в порядке возрастания priority
LAYER_CHOICES = [
    ("under", "under - нижнее бельё (приоритет 10)"),
    ("shirt", "shirt - рубашка (20)"),
    ("base", "base - основной слой, по умолчанию (30)"),
    ("vest", "vest - жилет (40)"),
    ("jacket", "jacket - куртка/пиджак (50)"),
    ("coat", "coat - пальто (60)"),
    ("outer", "outer - самый верхний слой (70)"),
]
LAYER_DEFAULT = "base"

# com.sandydev.dcs.clothing.ClothingSlots.DEFAULT_SLOTS + head/hands/back
# (первые - собственные регистрации мода, последние три - базовые слоты Curios)
SLOT_CHOICES = [
    "face", "neck", "body", "jacket", "legs", "accessory",
    "head", "hands", "back", "feet",
]

# Известные коды локалей Minecraft, которые чаще всего используют паки.
# Список не исчерпывающий - поле локали в студии всегда редактируемое.
KNOWN_LOCALES = [
    ("en_us", "English (US)"),
    ("ru_ru", "Русский"),
    ("de_de", "Deutsch"),
    ("fr_fr", "Français"),
    ("es_es", "Español"),
    ("pt_br", "Português (Brasil)"),
    ("uk_ua", "Українська"),
    ("pl_pl", "Polski"),
    ("zh_cn", "中文 (简体)"),
    ("ja_jp", "日本語"),
    ("ko_kr", "한국어"),
    ("tr_tr", "Türkçe"),
]

# com.sandydev.dcs.clothing.ClothingArchiveParser.LOCALE_PATTERN
LOCALE_PATTERN = re.compile(r"^[a-z0-9_]+$")

LANG_FOLDER = "lang"
MANIFEST_ENTRY_NAME = "manifest.json"

# --- manifest.json -----------------------------------------------------------

# com.sandydev.dcs.clothing.ClothingPackFormat
PACK_FORMAT_CHOICES = [
    ("1.1", "1.1 - текущий формат .cloth (рекомендуется)"),
    ("1.0", "1.0 - устаревший формат, для старых .zip-паков"),
]
PACK_FORMAT_LATEST = "1.1"

# --- archive-level мягкие лимиты (см. ClothingArchiveSecurity) -------------
# Студия не обязана воспроизводить их байт-в-байт (это забота загрузчика в
# игре), но предупреждает автора пака заранее, чтобы он не удивлялся, почему
# мод отказался грузить архив.
MAX_ARCHIVE_FILE_SIZE = 64 * 1024 * 1024
MAX_ENTRY_SIZE = 32 * 1024 * 1024

ARCHIVE_FILE_TYPES = [
    ("Пак одежды (*.cloth)", "*.cloth"),
    ("Zip-архив (*.zip)", "*.zip"),
    ("Все файлы", "*.*"),
]
PNG_FILE_TYPES = [("PNG изображение", "*.png"), ("Все файлы", "*.*")]
