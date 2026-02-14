from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame
from game.paths import assets_dir


ASSET_DIR = assets_dir()


def _ensure_tone(path: Path, frequency: float) -> None:
    if path.exists():
        return
    sample_rate = 22050
    duration = 0.25
    samples = int(sample_rate * duration)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(samples):
            value = int(14000 * math.sin(2 * math.pi * frequency * i / sample_rate))
            frames.extend(struct.pack("<h", value))
        wf.writeframes(frames)


def _ensure_music(path: Path, frequency: float) -> None:
    if path.exists():
        return
    sample_rate = 22050
    duration = 3.0
    samples = int(sample_rate * duration)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(samples):
            value = int(8000 * math.sin(2 * math.pi * frequency * i / sample_rate))
            packed = struct.pack("<h", value)
            frames.extend(packed + packed)
        wf.writeframes(frames)


class AudioSystem:
    def __init__(self, master_volume: float, music_volume: float, sfx_volume: float) -> None:
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.mixer.init()
        self.master_volume = master_volume
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self.listener = pygame.Vector2(0, 0)
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self._load_assets()
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def _load_assets(self) -> None:
        _ensure_tone(ASSET_DIR / "shoot.wav", 440)
        _ensure_tone(ASSET_DIR / "explosion.wav", 120)
        _ensure_tone(ASSET_DIR / "confirm.wav", 660)
        _ensure_music(ASSET_DIR / "calm.wav", 220)
        _ensure_music(ASSET_DIR / "battle.wav", 180)
        self.sounds["shoot"] = pygame.mixer.Sound(str(ASSET_DIR / "shoot.wav"))
        self.sounds["explosion"] = pygame.mixer.Sound(str(ASSET_DIR / "explosion.wav"))
        self.sounds["confirm"] = pygame.mixer.Sound(str(ASSET_DIR / "confirm.wav"))

    def set_listener(self, position: pygame.Vector2) -> None:
        self.listener = position

    def play(self, name: str, position: Optional[pygame.Vector2] = None, max_distance: float = 1000) -> None:
        sound = self.sounds.get(name)
        if not sound:
            return
        volume_left = self.master_volume * self.sfx_volume
        volume_right = self.master_volume * self.sfx_volume
        if position is not None:
            delta = position - self.listener
            distance = min(max_distance, delta.length())
            attenuation = max(0.1, 1 - distance / max_distance)
            pan = max(-1.0, min(1.0, delta.x / max_distance))
            volume_left *= attenuation * (1 - max(0, pan))
            volume_right *= attenuation * (1 + min(0, pan))
        channel = sound.play()
        if channel:
            channel.set_volume(volume_left, volume_right)

    def play_music(self, track: str, loop: int = -1) -> None:
        path = ASSET_DIR / track
        if not path.exists():
            return
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play(loop)
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def stop_music(self) -> None:
        pygame.mixer.music.stop()
