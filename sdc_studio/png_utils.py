"""
Минимальная работа с PNG без внешних зависимостей.

Студия намеренно не требует Pillow: пользователю достаточно системного
Python 3 + tkinter, чтобы запустить SDC-Studio.py. Всё, что нужно от PNG -
проверить сигнатуру и прочитать ширину/высоту из чанка IHDR, а это всего
несколько байт по фиксированным смещениям (спецификация PNG, раздел 11.2.2).

Если в окружении есть Pillow - она не используется и не требуется; при
желании её можно подключить отдельно для превью в UI, но базовая
валидация текстур в этом файле работает и без неё.
"""

from __future__ import annotations

import struct

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class InvalidPngError(ValueError):
    """PNG-сигнатура или чанк IHDR не распознаны."""


def is_png(data: bytes) -> bool:
    return data[:8] == PNG_SIGNATURE


def read_png_size(data: bytes) -> tuple[int, int]:
    """Возвращает (width, height) PNG-изображения из его байт.

    Бросает InvalidPngError, если данные не похожи на PNG или слишком
    коротки, чтобы содержать чанк IHDR.
    """
    if len(data) < 24:
        raise InvalidPngError("файл слишком мал, чтобы быть PNG")
    if data[:8] != PNG_SIGNATURE:
        raise InvalidPngError("отсутствует сигнатура PNG (не PNG-файл)")
    chunk_type = data[12:16]
    if chunk_type != b"IHDR":
        raise InvalidPngError("первый чанк PNG - не IHDR, файл повреждён")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def describe_size_requirement(kind: str) -> str:
    from . import constants

    if kind == "cape":
        w, h = constants.CAPE_TEXTURE_SIZE
    else:
        w, h = constants.SKIN_TEXTURE_SIZE
    return f"{w}x{h}"
