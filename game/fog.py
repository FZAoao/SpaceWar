import pygame
from typing import List, Tuple
from game.entities import Entity

class FogOfWar:
    def __init__(self, map_size: Tuple[int, int], resolution_scale: float = 0.1) -> None:
        self.map_size = map_size
        self.scale = resolution_scale
        # Surface for logic checks (low res)
        self.fog_surface = pygame.Surface((int(map_size[0] * self.scale), int(map_size[1] * self.scale)))
        # Surface for drawing (high res, scaled up)
        self.render_surface = pygame.Surface(map_size)
        self.render_surface.set_colorkey((255, 255, 255)) # Transparent where we can see
        
    def update(self, friendlies: List[Entity]) -> None:
        # Fill with darkness
        self.fog_surface.fill((0, 0, 0))
        
        # Punch holes for friendlies
        # White = visible
        for entity in friendlies:
            # Scale position and radius
            pos = (int(entity.position.x * self.scale), int(entity.position.y * self.scale))
            radius = int(320 * self.scale) # Vision radius ~320
            pygame.draw.circle(self.fog_surface, (255, 255, 255), pos, radius)

    def is_visible(self, position: pygame.Vector2) -> bool:
        # Check if a point is visible
        x = int(position.x * self.scale)
        y = int(position.y * self.scale)
        if 0 <= x < self.fog_surface.get_width() and 0 <= y < self.fog_surface.get_height():
            return self.fog_surface.get_at((x, y))[0] > 128
        return False

    def draw(self, surface: pygame.Surface, camera: pygame.Vector2, scale: float) -> None:
        # Create a view of the fog scaled to the screen
        # Optimization: We can just draw a black overlay and punch holes in screen space?
        # Actually, let's just scale up the low-res fog surface to the screen size
        
        # 1. Get the sub-surface of the fog that matches the camera view
        #    Camera (x, y) -> Fog (x*scale, y*scale)
        #    Screen (w, h) -> Fog (w*scale/game_scale, h*scale/game_scale) ?? No.
        
        # Easier approach for "Mini-game":
        # Just use the low-res surface, scale it up to cover the WHOLE map, then blit the relevant part?
        # Or better: construct screen-space fog.
        
        # Let's stick to the simplest visual approach that works with camera.
        # We can construct the "Darkness" mask in screen space directly.
        pass

    def draw_screen_space(self, surface: pygame.Surface, friendlies: List[Entity], camera: pygame.Vector2, scale: float) -> None:
        # Create a darkness surface covering the screen
        overlay = pygame.Surface(surface.get_size())
        overlay.fill((0, 0, 0)) # Black = Fog
        
        # Punch holes (White = Visible)
        for entity in friendlies:
            screen_pos = (entity.position - camera) * scale
            # Draw gradient circle for soft edges? Simple circle first.
            radius = 320 * scale
            pygame.draw.circle(overlay, (255, 255, 255), (int(screen_pos.x), int(screen_pos.y)), int(radius))
            
        # Set white as transparent
        overlay.set_colorkey((255, 255, 255))
        overlay.set_alpha(200) # Fog darkness level
        surface.blit(overlay, (0, 0))

