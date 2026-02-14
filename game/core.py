from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import os

import pygame

from game.ai import AIBrain
from game.audio import AudioSystem
from game.config import GameSettings, load_audio_settings, load_game_settings, load_key_bindings, load_video_settings
from game.effects import WeatherSystem, spawn_explosion, spawn_command_feedback
from game.entities import Building, Entity, ResourceNode, Unit, create_building, create_unit, random_resource_node
from game.fog import FogOfWar
from game.fonts import get_font
from game.paths import is_android
from game.save import load_game, restore_buildings, restore_resources, restore_units, save_game, serialize_building, serialize_resource, serialize_unit
from game.spatial import SpatialHash
from game.ui import HUD, MiniMap, Toolbar


class Game:
    def __init__(self) -> None:
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        pygame.init()
        self.video_settings = load_video_settings()
        self.audio_settings = load_audio_settings()
        self.game_settings = load_game_settings()
        self.bindings = load_key_bindings()
        
        # 自动适配分辨率（如果首次运行）
        if self.video_settings.width == 1920 and self.video_settings.height == 1080:
             info = pygame.display.Info()
             if info.current_w < 1920 or info.current_h < 1080:
                 self.video_settings.width = int(info.current_w * 0.85)
                 self.video_settings.height = int(info.current_h * 0.85)

        if is_android():
            self.video_settings.fullscreen = True

        flags = pygame.SCALED | pygame.RESIZABLE
        if self.video_settings.fullscreen:
            flags |= pygame.FULLSCREEN
        
        if is_android():
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.video_settings.width, self.video_settings.height), flags)
            
        pygame.display.set_caption("战线指挥")
        self._set_icon()
        self.clock = pygame.time.Clock()
        self.audio = AudioSystem(
            self.audio_settings.master_volume,
            self.audio_settings.music_volume,
            self.audio_settings.sfx_volume,
        )
        self.current_music = ""
        self.map_size = (4000, 2400)
        self.camera = pygame.Vector2(0, 0)
        self.scale = 1.0
        self.state = "menu"
        self.hud = HUD(self.screen.get_size())
        self.mini_map = MiniMap(self.map_size, self.screen.get_size())
        self.toolbar = Toolbar(self.screen.get_size())
        self.drag_select_start: Optional[pygame.Vector2] = None
        self.drag_select_end: Optional[pygame.Vector2] = None
        self.help_visible = True
        self.spatial = SpatialHash(120)
        self.placement_mode: Optional[str] = None # Building type to place
        self.command_mode: bool = False # For touch devices to issue commands
        self.tutorial_lines = [
            "鼠标左键拖拽框选单位，右键移动/攻击",
            "Shift+右键设置路径点，Ctrl+数字设置编队",
            "B/T/F/G 建造基地/炮塔/工厂/机场",
            "1/2/3 训练步兵/坦克/飞机  U 科技升级",
        ]
        if is_android():
            self.tutorial_lines = [
                "拖拽框选单位",
                "点击【指令模式】后点击地图进行移动/攻击",
                "使用下方工具栏进行建造和生产",
            ]
        self.reset_game()

    def _set_icon(self) -> None:
        if is_android():
            return
        try:
            path = Path("assets/icon.png")
            if path.exists():
                icon = pygame.image.load(str(path))
                pygame.display.set_icon(icon)
                return
        except Exception:
            pass
            
        icon = pygame.Surface((32, 32))
        icon.fill((30, 30, 40))
        pygame.draw.rect(icon, (220, 180, 60), (4, 4, 24, 24), border_radius=4)
        pygame.draw.circle(icon, (255, 255, 255), (16, 16), 8)
        pygame.display.set_icon(icon)

    def reset_game(self) -> None:
        self.units: List[Unit] = []
        self.buildings: List[Building] = []
        self.resources: Dict[str, float] = {"gold": 600, "oil": 400, "steel": 400}
        self.ai_resources: Dict[str, float] = {"gold": 600, "oil": 400, "steel": 400}
        self.tech_level = 1
        self.ai_tech_level = 1
        self.tech_timer = 0.0
        self.resource_nodes: List[ResourceNode] = [random_resource_node(self.map_size) for _ in range(16)]
        self.projectiles: List[Entity] = []
        self.particles = []
        self.weather = WeatherSystem(self.map_size)
        self.fog = FogOfWar(self.map_size)
        self.ai = AIBrain(self.game_settings.difficulty, self.game_settings.ai_style, self.map_size)
        self.turret_cooldowns: Dict[int, float] = {}
        self.base = create_building("base", pygame.Vector2(480, self.map_size[1] / 2), 0)
        self.ai_base = create_building("base", pygame.Vector2(self.map_size[0] - 480, self.map_size[1] / 2), 1)
        self.buildings.extend([self.base, self.ai_base])
        self.group_assignments: Dict[int, List[int]] = {1: [], 2: [], 3: []}
        self.state = "menu"
        self.current_music = ""

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST:
                    if self.state == "playing":
                        self.state = "paused"
                elif event.type == pygame.VIDEORESIZE:
                    self.video_settings.width = event.w
                    self.video_settings.height = event.h
                    self.screen = pygame.display.set_mode(event.size, pygame.SCALED | pygame.RESIZABLE)
                    self.hud = HUD(self.screen.get_size())
                    self.mini_map = MiniMap(self.map_size, self.screen.get_size())
                    self.toolbar = Toolbar(self.screen.get_size())
                else:
                    self.handle_event(event)
            if self.state == "playing":
                self.update(dt)
            self.draw()
        pygame.quit()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_AC_BACK:
                if self.state == "playing":
                    self.state = "paused"
                return
            if event.key == pygame.K_F11:
                self.video_settings.fullscreen = not self.video_settings.fullscreen
                flags = pygame.SCALED | pygame.RESIZABLE
                if self.video_settings.fullscreen:
                    flags |= pygame.FULLSCREEN
                self.screen = pygame.display.set_mode((self.video_settings.width, self.video_settings.height), flags)
                return
            if self._matches(event, "pause"):
                self.state = "paused" if self.state == "playing" else "playing"
            if self._matches(event, "toggle_help"):
                self.help_visible = not self.help_visible
            if self._matches(event, "save"):
                self.save()
                self.hud.flash("存档成功")
            if self._matches(event, "load"):
                self.load()
                self.hud.flash("读档成功")
            
            # Cancel placement on ESC
            if event.key == pygame.K_ESCAPE and self.placement_mode:
                self.placement_mode = None
                return

            if self.state == "menu" and event.key == pygame.K_SPACE:
                self.ai = AIBrain(self.game_settings.difficulty, self.game_settings.ai_style, self.map_size)
                self.state = "playing"
            elif self.state == "gameover" and event.key == pygame.K_SPACE:
                self.reset_game()
                self.ai = AIBrain(self.game_settings.difficulty, self.game_settings.ai_style, self.map_size)
                self.state = "playing"
            if self.state == "menu":
                if event.key == pygame.K_1:
                    self.game_settings.difficulty = "easy"
                elif event.key == pygame.K_2:
                    self.game_settings.difficulty = "normal"
                elif event.key == pygame.K_3:
                    self.game_settings.difficulty = "hard"
                elif event.key == pygame.K_4:
                    self.game_settings.ai_style = "rush"
                elif event.key == pygame.K_5:
                    self.game_settings.ai_style = "balanced"
                elif event.key == pygame.K_6:
                    self.game_settings.ai_style = "turtle"
            if self.state == "playing":
                self.handle_hotkeys(event)
        if self.state != "playing":
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # 1. Check Toolbar FIRST (so we can switch modes or cancel placement)
            action = self.toolbar.action_for(event.pos)
            if action:
                self.handle_toolbar_action(action)
                return

            # 2. Check Minimap click
            minimap_target = self.mini_map.handle_click(event.pos)
            if minimap_target:
                self.camera = minimap_target - pygame.Vector2(self.screen.get_width() / 2 / self.scale, self.screen.get_height() / 2 / self.scale)
                self.camera.x = max(0, min(self.map_size[0] - self.screen.get_width() / self.scale, self.camera.x))
                self.camera.y = max(0, min(self.map_size[1] - self.screen.get_height() / self.scale, self.camera.y))
                return

            # 3. Handle placement click
            if self.placement_mode:
                mouse_world = self.screen_to_world(pygame.Vector2(event.pos))
                self.try_build(self.placement_mode, mouse_world)
                self.placement_mode = None
                return
            
            # 4. Handle Command Mode (Android Right Click equivalent)
            if self.command_mode:
                self.issue_command(pygame.Vector2(event.pos), 0)
                self.command_mode = False
                return

            # 5. Double click selection / Drag Selection
            now = pygame.time.get_ticks()
            if hasattr(self, 'last_click_time') and now - self.last_click_time < 300:
                world_pos = self.screen_to_world(pygame.Vector2(event.pos))
                self.select_same_type_on_screen(world_pos)
                self.drag_select_start = None # Cancel drag
            else:
                self.drag_select_start = pygame.Vector2(event.pos)
                self.drag_select_end = pygame.Vector2(event.pos)
            
            self.last_click_time = now

        elif event.type == pygame.MOUSEMOTION and self.drag_select_start:
            self.drag_select_end = pygame.Vector2(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_select_start and self.drag_select_end:
                self.select_units_in_rect(self.drag_select_start, self.drag_select_end)
            self.drag_select_start = None
            self.drag_select_end = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Cancel placement on Right Click
            if self.placement_mode:
                self.placement_mode = None
                return
            self.issue_command(pygame.Vector2(event.pos), pygame.key.get_mods())
        elif event.type == pygame.MOUSEWHEEL:
            self.scale = max(0.6, min(1.5, self.scale + event.y * 0.05))

    def handle_hotkeys(self, event: pygame.event.Event) -> None:
        if self._matches(event, "build_base"):
            self.placement_mode = "base"
        elif self._matches(event, "build_turret"):
            self.placement_mode = "turret"
        elif self._matches(event, "build_factory"):
            self.placement_mode = "factory"
        elif self._matches(event, "build_airfield"):
            self.placement_mode = "airfield"
        elif self._matches(event, "train_infantry"):
            if not self.any_units_selected():
                self.try_train("infantry")
        elif self._matches(event, "train_tank"):
            if not self.any_units_selected():
                self.try_train("tank")
        elif self._matches(event, "train_aircraft"):
            if not self.any_units_selected():
                self.try_train("aircraft")
        elif self._matches(event, "zoom_in"):
            self.scale = max(0.6, min(1.5, self.scale + 0.05))
        elif self._matches(event, "zoom_out"):
            self.scale = max(0.6, min(1.5, self.scale - 0.05))
        elif self._matches(event, "upgrade_tech"):
            self.try_upgrade_tech()
        if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            index = int(event.unicode) if event.unicode.isdigit() else 1
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.group_assignments[index] = [unit.entity_id for unit in self.units if unit.selected]
            else:
                self.select_group(index)

    def _matches(self, event: pygame.event.Event, action: str) -> bool:
        keys = self.bindings.get(action, ())
        name = pygame.key.name(event.key)
        return name in keys

    def screen_to_world(self, pos: pygame.Vector2) -> pygame.Vector2:
        return pos / self.scale + self.camera

    def world_to_screen(self, pos: pygame.Vector2) -> pygame.Vector2:
        return (pos - self.camera) * self.scale

    def update(self, dt: float) -> None:
        self.update_camera(dt)
        self.hud.update(dt)
        self.weather.update(dt)
        self.audio.set_listener(self.camera + pygame.Vector2(self.screen.get_width() / 2, self.screen.get_height() / 2))
        self.apply_resource_income(dt)
        self.ai.update(dt, self.ai_resources, self.units, self.buildings, self.base, self.tech_multiplier(self.ai_tech_level))
        self.update_buildings(dt)
        self.update_units(dt)
        self.resolve_combat(dt)
        self.cleanup(dt)
        self.update_music()
        self.ai_try_upgrade(dt)
        if not self.base.alive or not self.ai_base.alive:
            self.state = "gameover"

    def update_camera(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        speed = 700 * dt
        if keys[pygame.K_w]:
            self.camera.y -= speed
        if keys[pygame.K_s]:
            self.camera.y += speed
        if keys[pygame.K_a]:
            self.camera.x -= speed
        if keys[pygame.K_d]:
            self.camera.x += speed
        self.camera.x = max(0, min(self.map_size[0] - self.screen.get_width() / self.scale, self.camera.x))
        self.camera.y = max(0, min(self.map_size[1] - self.screen.get_height() / self.scale, self.camera.y))

    def apply_resource_income(self, dt: float) -> None:
        base_income = {"gold": 4, "oil": 3, "steel": 3}
        for key in self.resources:
            self.resources[key] += base_income[key] * dt
            self.ai_resources[key] += base_income[key] * dt
        for building in self.buildings:
            if building.role == "refinery":
                node = self.find_nearest_resource(building.position)
                if node:
                    harvested = node.harvest(12 * dt)
                    target_resources = self.resources if building.team == 0 else self.ai_resources
                    target_resources[node.resource_type] += harvested

    def find_nearest_resource(self, position: pygame.Vector2) -> Optional[ResourceNode]:
        candidates = [n for n in self.resource_nodes if n.alive]
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.position.distance_to(position))

    def update_buildings(self, dt: float) -> None:
        for building in self.buildings:
            produced = building.update(dt)
            if produced:
                spawn = building.position + pygame.Vector2(60, 0) * (1 if building.team == 0 else -1)
                tech = self.tech_multiplier(self.tech_level if building.team == 0 else self.ai_tech_level)
                self.units.append(create_unit(produced, spawn, building.team, tech))
                self.audio.play("confirm", building.position)

    def update_units(self, dt: float) -> None:
        for unit in self.units:
            unit.update(dt)

    def resolve_combat(self, dt: float) -> None:
        self.spatial.clear()
        for entity in self.units + self.buildings:
            if not entity.alive: continue
            self.spatial.insert(entity.entity_id, entity.position.x, entity.position.y, entity.radius + 10)
        entities_by_id = {e.entity_id: e for e in self.units + self.buildings if e.alive}
        
        for unit in self.units:
            if not unit.alive: continue
            # Fix friendly fire target
            if unit.target and (unit.target.team == unit.team or not unit.target.alive):
                unit.target = None
            
            # Auto acquire target if idle or moving without target
            if not unit.target:
                # Search radius slightly larger than attack range for auto-aggro
                scan_range = unit.attack_range + 100
                potential_targets = []
                for eid in self.spatial.query(unit.position.x, unit.position.y, scan_range):
                    if eid not in entities_by_id: continue
                    e = entities_by_id[eid]
                    if e.team != unit.team and e.team != -1:
                        # Check visibility if it's player unit (team 0) looking for targets
                        if unit.team == 0 and not self.fog.is_visible(e.position):
                            continue
                        potential_targets.append(e)
                
                if potential_targets:
                    unit.target = min(potential_targets, key=lambda e: unit.position.distance_to(e.position))

        for building in self.buildings:
            if building.role != "turret":
                continue
            self.turret_cooldowns[building.entity_id] = max(0.0, self.turret_cooldowns.get(building.entity_id, 0) - dt)
            enemies = [entities_by_id[eid] for eid in self.spatial.query(building.position.x, building.position.y, 220)]
            enemies = [e for e in enemies if e.team != building.team and e.team != -1]
            if enemies and self.turret_cooldowns[building.entity_id] == 0:
                target = min(enemies, key=lambda e: building.position.distance_to(e.position))
                target.take_damage(26)
                self.audio.play("shoot", building.position)
                self.turret_cooldowns[building.entity_id] = 0.7

    def cleanup(self, dt: float) -> None:
        # Handle unit deaths
        dead_units = [u for u in self.units if not u.alive]
        for unit in dead_units:
            self.particles.extend(spawn_explosion(unit.position))
            self.audio.play("explosion", unit.position)
        self.units = [u for u in self.units if u.alive]
            
        # Handle building destruction
        dead_buildings = [b for b in self.buildings if not b.alive and b != self.base and b != self.ai_base]
        for building in dead_buildings:
             self.particles.extend(spawn_explosion(building.position))
        self.buildings = [b for b in self.buildings if b.alive or b == self.base or b == self.ai_base]
                
        # Update particles
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.lifetime > 0]
        
        self.resource_nodes = [n for n in self.resource_nodes if n.alive]
        
        # Update Fog
        friendlies = [e for e in self.units + self.buildings if e.team == 0]
        self.fog.update(friendlies)

    def draw(self) -> None:
        self.screen.fill((12, 18, 28))
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "gameover":
            self.draw_gameover()
        else:
            self.draw_world()
            self.draw_ui()
            if self.state == "paused":
                self.draw_pause_overlay()
        pygame.display.flip()

    def draw_menu(self) -> None:
        font = get_font(38, bold=True)
        sub = get_font(24)
        tiny = get_font(14)
        center = self.screen.get_rect().center
        title = font.render("战线指挥", True, (230, 230, 240))
        self.screen.blit(title, (center[0] - title.get_width() / 2, center[1] - 120))
        tips = [
            "按 1/2/3 选择难度，按 4/5/6 选择AI战术",
            "空格开始游戏，P 暂停",
        ]
        y = center[1] - 40
        for line in tips:
            text = sub.render(line, True, (200, 200, 210))
            self.screen.blit(text, (center[0] - text.get_width() / 2, y))
            y += 34
        info = sub.render(f"当前难度: {self.game_settings.difficulty}  AI: {self.game_settings.ai_style}", True, (180, 180, 180))
        self.screen.blit(info, (center[0] - info.get_width() / 2, y + 20))
        
        # Copyright
        copy = tiny.render("© 2025 SpaceTeam (Scorpe Group). All Rights Reserved.", True, (100, 100, 120))
        self.screen.blit(copy, (self.screen.get_width() - copy.get_width() - 10, self.screen.get_height() - 20))

    def draw_gameover(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        font = get_font(64, bold=True)
        sub = get_font(32)
        
        is_win = self.base.alive
        msg = "VICTORY" if is_win else "DEFEAT"
        color = (255, 200, 50) if is_win else (220, 60, 60)
        
        text = font.render(msg, True, color)
        rect = text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2 - 60))
        self.screen.blit(text, rect)
        
        hint = sub.render("Press SPACE to Restart", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2 + 40))
        self.screen.blit(hint, hint_rect)

    def draw_pause_overlay(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        
        font = get_font(48, bold=True)
        sub = get_font(24)
        
        text = font.render("PAUSED", True, (230, 230, 240))
        rect = text.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2 - 40))
        
        hint = sub.render("Press P to Resume", True, (180, 180, 190))
        hint_rect = hint.get_rect(center=(self.screen.get_width() / 2, self.screen.get_height() / 2 + 30))
        
        self.screen.blit(overlay, (0, 0))
        self.screen.blit(text, rect)
        self.screen.blit(hint, hint_rect)

    def draw_world(self) -> None:
        # Render culling: Viewport rectangle in world coordinates
        # Add some margin to avoid popping
        view_w = self.screen.get_width() / self.scale
        view_h = self.screen.get_height() / self.scale
        view_rect = pygame.Rect(
            self.camera.x - 100, 
            self.camera.y - 100, 
            view_w + 200, 
            view_h + 200
        )

        grid_color = (20, 28, 36)
        # Optimize grid drawing: only draw visible lines
        start_x = max(0, int((view_rect.x // 120) * 120))
        end_x = min(self.map_size[0], int((view_rect.right // 120 + 1) * 120))
        for x in range(start_x, end_x, 120):
            sx = int((x - self.camera.x) * self.scale)
            pygame.draw.line(self.screen, grid_color, (sx, 0), (sx, self.screen.get_height()))
            
        start_y = max(0, int((view_rect.y // 120) * 120))
        end_y = min(self.map_size[1], int((view_rect.bottom // 120 + 1) * 120))
        for y in range(start_y, end_y, 120):
            sy = int((y - self.camera.y) * self.scale)
            pygame.draw.line(self.screen, grid_color, (0, sy), (self.screen.get_width(), sy))
            
        for node in self.resource_nodes:
            if view_rect.collidepoint(node.position.x, node.position.y):
                node.draw(self.screen, self.camera, self.scale)
        for building in self.buildings:
            if not view_rect.collidepoint(building.position.x, building.position.y):
                continue
            if building.team == 1 and not self.fog.is_visible(building.position):
                continue
            building.draw(self.screen, self.camera, self.scale)
        for unit in self.units:
            if not view_rect.collidepoint(unit.position.x, unit.position.y):
                continue
            if unit.team == 1 and not self.fog.is_visible(unit.position):
                continue
            unit.draw(self.screen, self.camera, self.scale)
        for particle in self.particles:
            # Simple culling for particles
            if view_rect.collidepoint(particle.position.x, particle.position.y):
                particle.draw(self.screen, self.camera, self.scale)
        
        # Draw Fog Overlay
        friendlies = [e for e in self.units + self.buildings if e.team == 0]
        self.fog.draw_screen_space(self.screen, friendlies, self.camera, self.scale)

        self.weather.draw(self.screen, self.camera, self.scale)
        if self.drag_select_start and self.drag_select_end:
            rect = pygame.Rect(self.drag_select_start, self.drag_select_end - self.drag_select_start)
            rect.normalize()
            pygame.draw.rect(self.screen, (120, 180, 220), rect, 1)

        # Draw Placement Preview
        if self.placement_mode:
            mouse_pos = pygame.mouse.get_pos()
            # Snap to grid? Maybe just follow mouse
            # Draw semi-transparent building
            preview_surface = pygame.Surface((80, 80), pygame.SRCALPHA)
            preview_surface.fill((60, 160, 220, 128)) # Semi-transparent blue
            pygame.draw.rect(preview_surface, (255, 255, 255, 128), preview_surface.get_rect(), 2)
            
            # Center on mouse
            draw_pos = (mouse_pos[0] - 40 * self.scale, mouse_pos[1] - 40 * self.scale)
            scaled_preview = pygame.transform.scale(preview_surface, (int(80 * self.scale), int(80 * self.scale)))
            self.screen.blit(scaled_preview, draw_pos)
            
            # Draw range circle for turret
            if self.placement_mode == "turret":
                pygame.draw.circle(self.screen, (255, 255, 255, 60), mouse_pos, int(220 * self.scale), 1)

    def draw_ui(self) -> None:
        fps = self.clock.get_fps()
        self.hud.draw(self.screen, self.resources, fps, self.help_visible, self.tutorial_lines)
        self.mini_map.draw(
            self.screen,
            [(u.position, u.team) for u in self.units],
            [(b.position, b.team) for b in self.buildings],
            self.camera,
            (self.screen.get_width() / self.scale, self.screen.get_height() / self.scale),
        )
        self.toolbar.draw(self.screen, pygame.mouse.get_pos(), self.command_mode)

    def select_units_in_rect(self, start: pygame.Vector2, end: pygame.Vector2) -> None:
        rect = pygame.Rect(start, end - start)
        rect.normalize()
        for unit in self.units:
            if unit.team != 0:
                continue
            screen_pos = self.world_to_screen(unit.position)
            unit.selected = rect.collidepoint(screen_pos.x, screen_pos.y)

    def select_same_type_on_screen(self, world_pos: pygame.Vector2) -> None:
        # Find unit under cursor
        target = None
        min_dist = 40
        for unit in self.units:
            if unit.team == 0 and unit.position.distance_to(world_pos) < min_dist:
                target = unit
                min_dist = unit.position.distance_to(world_pos)
        
        if not target:
            return
            
        # Select all of same role on screen
        view_rect = pygame.Rect(self.camera.x, self.camera.y, self.screen.get_width() / self.scale, self.screen.get_height() / self.scale)
        for unit in self.units:
            if unit.team == 0 and unit.role == target.role and view_rect.collidepoint(unit.position.x, unit.position.y):
                unit.selected = True

    def select_group(self, group: int) -> None:
        target_ids = set(self.group_assignments.get(group, []))
        for unit in self.units:
            unit.selected = unit.entity_id in target_ids

    def issue_command(self, screen_pos: pygame.Vector2, mods: int) -> None:
        world_pos = self.screen_to_world(screen_pos)
        target = self.find_enemy_at(world_pos, 30)
        
        # Feedback effect
        color = (255, 60, 60) if target else (60, 255, 120)
        self.particles.extend(spawn_command_feedback(world_pos, color))
        
        for unit in self.units:
            if not unit.selected:
                continue
            if mods & pygame.KMOD_SHIFT:
                unit.waypoints.append(world_pos.copy())
            else:
                unit.waypoints = [world_pos.copy()]
                unit.target = target

    def try_build(self, building_type: str, position: pygame.Vector2) -> None:
        cost = {"base": (220, 120, 160), "turret": (120, 40, 120), "factory": (160, 80, 120), "airfield": (180, 90, 140), "refinery": (130, 60, 90)}
        gold, oil, steel = cost[building_type]
        if self.resources["gold"] < gold or self.resources["oil"] < oil or self.resources["steel"] < steel:
            self.hud.flash("资源不足")
            return
        self.resources["gold"] -= gold
        self.resources["oil"] -= oil
        self.resources["steel"] -= steel
        self.buildings.append(create_building(building_type, position, 0))
        if building_type == "factory":
            self.buildings.append(create_building("refinery", position + pygame.Vector2(80, 0), 0))

    def try_train(self, unit_type: str) -> None:
        cost = {"infantry": (60, 20, 10), "tank": (120, 60, 40), "aircraft": (140, 80, 50)}
        gold, oil, steel = cost[unit_type]
        if self.resources["gold"] < gold or self.resources["oil"] < oil or self.resources["steel"] < steel:
            self.hud.flash("资源不足")
            return
        self.resources["gold"] -= gold
        self.resources["oil"] -= oil
        self.resources["steel"] -= steel
        spawn = self.base.position + pygame.Vector2(80, random.uniform(-60, 60))
        self.units.append(create_unit(unit_type, spawn, 0, self.tech_multiplier(self.tech_level)))

    def handle_toolbar_action(self, action: str) -> None:
        if action.startswith("build_"):
            self.placement_mode = action.split("_")[1]
            return
            
        if action == "train_infantry":
            self.try_train("infantry")
        elif action == "train_tank":
            self.try_train("tank")
        elif action == "train_aircraft":
            self.try_train("aircraft")
        elif action == "upgrade_tech":
            self.try_upgrade_tech()
        elif action == "toggle_command_mode":
            self.command_mode = not self.command_mode

    def find_enemy_at(self, position: pygame.Vector2, radius: float) -> Optional[Entity]:
        enemies = [e for e in self.units + self.buildings if e.team == 1 and e.position.distance_to(position) <= radius]
        if enemies:
            return min(enemies, key=lambda e: e.position.distance_to(position))
        return None

    def any_units_selected(self) -> bool:
        return any(unit.selected for unit in self.units)

    def update_music(self) -> None:
        threat = any(unit.team == 1 and unit.position.distance_to(self.base.position) < 500 for unit in self.units)
        desired = "battle.wav" if threat else "calm.wav"
        if desired != self.current_music:
            self.audio.play_music(desired, loop=-1)
            self.current_music = desired

    def save(self) -> None:
        payload = {
            "resources": self.resources,
            "ai_resources": self.ai_resources,
            "tech_level": self.tech_level,
            "ai_tech_level": self.ai_tech_level,
            "units": [serialize_unit(u) for u in self.units],
            "buildings": [serialize_building(b) for b in self.buildings],
            "resources_nodes": [serialize_resource(r) for r in self.resource_nodes],
            "camera": [self.camera.x, self.camera.y],
            "scale": self.scale,
            "difficulty": self.game_settings.difficulty,
            "ai_style": self.game_settings.ai_style,
        }
        save_game("autosave", payload)

    def load(self) -> None:
        payload = load_game("autosave")
        self.resources = payload["resources"]
        self.ai_resources = payload["ai_resources"]
        self.tech_level = payload.get("tech_level", 1)
        self.ai_tech_level = payload.get("ai_tech_level", 1)
        self.units = restore_units(payload["units"])
        self.buildings = restore_buildings(payload["buildings"])
        self.resource_nodes = restore_resources(payload["resources_nodes"])
        self.camera = pygame.Vector2(payload["camera"][0], payload["camera"][1])
        self.scale = payload["scale"]
        self.game_settings.difficulty = payload.get("difficulty", "normal")
        self.game_settings.ai_style = payload.get("ai_style", "balanced")
        self.base = next((b for b in self.buildings if b.team == 0 and b.role == "base"), self.base)
        self.ai_base = next((b for b in self.buildings if b.team == 1 and b.role == "base"), self.ai_base)

    def tech_multiplier(self, level: int) -> float:
        return 1.0 + 0.12 * (level - 1)

    def try_upgrade_tech(self) -> None:
        cost = 180 * self.tech_level
        if self.resources["gold"] < cost or self.resources["oil"] < cost or self.resources["steel"] < cost:
            self.hud.flash("科技升级资源不足")
            return
        self.resources["gold"] -= cost
        self.resources["oil"] -= cost
        self.resources["steel"] -= cost
        self.tech_level += 1
        self.hud.flash(f"科技等级提升到 {self.tech_level}")

    def ai_try_upgrade(self, dt: float) -> None:
        self.tech_timer += dt
        if self.tech_timer < 30:
            return
        self.tech_timer = 0
        cost = 170 * self.ai_tech_level
        if all(self.ai_resources[r] >= cost for r in self.ai_resources):
            for key in self.ai_resources:
                self.ai_resources[key] -= cost
            self.ai_tech_level += 1
