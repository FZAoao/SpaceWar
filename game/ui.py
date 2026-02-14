from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pygame
from game.fonts import get_font


@dataclass
class Button:
    rect: pygame.Rect
    label: str

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, active: bool = False) -> None:
        color = (80, 160, 220) if active else (50, 80, 120)
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        text = font.render(self.label, True, (230, 230, 230))
        surface.blit(text, (self.rect.centerx - text.get_width() / 2, self.rect.centery - text.get_height() / 2))

    def hit(self, point: Tuple[int, int]) -> bool:
        return self.rect.collidepoint(point)


class HUD:
    def __init__(self, screen_size: Tuple[int, int]) -> None:
        self.font = get_font(18)
        self.title_font = get_font(28, bold=True)
        self.small_font = get_font(14)
        self.screen_size = screen_size
        self.message: str = ""
        self.message_timer: float = 0.0
        self._panel_surface = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._panel_size = (0, 0)
        self.theme = {
            "panel_bg": (16, 22, 34, 200),
            "panel_border": (80, 120, 180),
            "text_primary": (230, 230, 230),
            "text_secondary": (190, 200, 215),
            "accent": (255, 210, 100),
        }

    def flash(self, message: str, duration: float = 2.0) -> None:
        self.message = message
        self.message_timer = duration

    def update(self, dt: float) -> None:
        self.message_timer = max(0.0, self.message_timer - dt)

    def draw(self, surface: pygame.Surface, resources: Dict[str, float], fps: float, help_visible: bool, tutorial_lines: List[str]) -> None:
        header = f"金币 {int(resources['gold'])}  石油 {int(resources['oil'])}  钢铁 {int(resources['steel'])}"
        panel_rect = pygame.Rect(16, 12, 520, 120)
        self._draw_panel(surface, panel_rect)
        surface.blit(self.title_font.render(header, True, self.theme["text_primary"]), (panel_rect.x + 16, panel_rect.y + 12))
        surface.blit(self.font.render(f"FPS {fps:.0f}", True, self.theme["text_secondary"]), (panel_rect.x + 16, panel_rect.y + 52))
        surface.blit(self.small_font.render("U 科技升级  F5 存档  F9 读档", True, self.theme["text_secondary"]), (panel_rect.x + 16, panel_rect.y + 82))
        if self.message_timer > 0:
            surface.blit(self.title_font.render(self.message, True, self.theme["accent"]), (panel_rect.x + 16, panel_rect.y + 86))
        if help_visible:
            help_box = pygame.Rect(16, surface.get_height() - 320, 560, 232)
            self._draw_panel(surface, help_box)
            y = help_box.y + 12
            for line in tutorial_lines:
                surface.blit(self.font.render(line, True, self.theme["text_secondary"]), (help_box.x + 14, y))
                y += 22

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if rect.size != self._panel_size:
            self._panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            self._panel_size = rect.size
        self._panel_surface.fill(self.theme["panel_bg"])
        surface.blit(self._panel_surface, rect.topleft)
        pygame.draw.rect(surface, self.theme["panel_border"], rect, 2, border_radius=8)


class MiniMap:
    def __init__(self, map_size: Tuple[int, int], screen_size: Tuple[int, int]) -> None:
        self.map_size = map_size
        self.rect = pygame.Rect(screen_size[0] - 240, screen_size[1] - 180, 220, 160)
        self.frame_color = (90, 130, 200)
        self.bg_color = (16, 22, 34)

    def draw(self, surface: pygame.Surface, units: List[Tuple[pygame.Vector2, int]], buildings: List[Tuple[pygame.Vector2, int]], camera_pos: pygame.Vector2, view_size: Tuple[int, int]) -> None:
        pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=6)
        pygame.draw.rect(surface, self.frame_color, self.rect, 2, border_radius=6)
        scale_x = self.rect.width / self.map_size[0]
        scale_y = self.rect.height / self.map_size[1]
        for pos, team in buildings:
            color = (70, 170, 230) if team == 0 else (230, 80, 80)
            x = self.rect.x + pos.x * scale_x
            y = self.rect.y + pos.y * scale_y
            pygame.draw.rect(surface, color, pygame.Rect(int(x - 3), int(y - 3), 6, 6))
        for pos, team in units:
            color = (100, 220, 140) if team == 0 else (240, 120, 120)
            x = self.rect.x + pos.x * scale_x
            y = self.rect.y + pos.y * scale_y
            pygame.draw.circle(surface, color, (int(x), int(y)), 2)
        view_rect = pygame.Rect(
            self.rect.x + camera_pos.x * scale_x,
            self.rect.y + camera_pos.y * scale_y,
            view_size[0] * scale_x,
            view_size[1] * scale_y,
        )
        pygame.draw.rect(surface, (240, 240, 240), view_rect, 1)

    def handle_click(self, mouse_pos: Tuple[int, int]) -> Optional[pygame.Vector2]:
        if not self.rect.collidepoint(mouse_pos):
            return None
        rel_x = mouse_pos[0] - self.rect.x
        rel_y = mouse_pos[1] - self.rect.y
        world_x = rel_x / self.rect.width * self.map_size[0]
        world_y = rel_y / self.rect.height * self.map_size[1]
        return pygame.Vector2(world_x, world_y)


class Toolbar:
    def __init__(self, screen_size: Tuple[int, int]) -> None:
        self.rect = pygame.Rect(16, screen_size[1] - 64, screen_size[0] - 32, 48)
        self.buttons: List[Button] = []
        self.font = get_font(16, bold=True)
        self._layout()

    def _layout(self) -> None:
        labels = ["基地", "炮塔", "工厂", "机场", "|", "步兵", "坦克", "飞机", "|", "科技升级", "|", "指令模式"]
        x = self.rect.x + 10
        for label in labels:
            if label == "|":
                x += 10
                continue
            w = max(72, self.font.size(label)[0] + 24)
            if label == "指令模式":
                w = max(90, self.font.size(label)[0] + 24)
            self.buttons.append(Button(pygame.Rect(x, self.rect.y + 6, w, self.rect.height - 12), label))
            x += w + 8

    def draw(self, surface: pygame.Surface, hover_pos: Tuple[int, int] | None = None, command_mode: bool = False) -> None:
        pygame.draw.rect(surface, (16, 22, 34), self.rect, border_radius=6)
        pygame.draw.rect(surface, (80, 120, 180), self.rect, 2, border_radius=6)
        for b in self.buttons:
            active = hover_pos is not None and b.hit(hover_pos)
            if b.label == "指令模式" and command_mode:
                active = True
                # Highlight command mode button strongly
                pygame.draw.rect(surface, (220, 60, 60), b.rect, border_radius=6)
                text = self.font.render(b.label, True, (255, 255, 255))
                surface.blit(text, (b.rect.centerx - text.get_width() / 2, b.rect.centery - text.get_height() / 2))
                continue
            b.draw(surface, self.font, active=active)

    def action_for(self, point: Tuple[int, int]) -> str | None:
        for b in self.buttons:
            if b.hit(point):
                mapping = {
                    "基地": "build_base",
                    "炮塔": "build_turret",
                    "工厂": "build_factory",
                    "机场": "build_airfield",
                    "步兵": "train_infantry",
                    "坦克": "train_tank",
                    "飞机": "train_aircraft",
                    "科技升级": "upgrade_tech",
                    "指令模式": "toggle_command_mode",
                }
                return mapping.get(b.label)
        return None
