from __future__ import annotations

from typing import Iterable, Optional

import pygame


def _match_font(candidates: Iterable[str], bold: bool = False) -> Optional[str]:
    for name in candidates:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return path
    return None


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    pygame.font.init()
    # Common CJK-capable fonts on Windows; fallbacks included
    candidates = [
        "Microsoft YaHei",
        "MSYH",
        "SimHei",
        "SimSun",
        "NSimSun",
        "Noto Sans SC",
        "Arial Unicode MS",
        "Segoe UI Symbol",
    ]
    path = _match_font(candidates, bold=bold)
    if path:
        return pygame.font.Font(path, size)
    # Fallback to default, which may not render all CJK glyphs, but avoids crash
    return pygame.font.Font(None, size)
