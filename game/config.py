from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Tuple
from game.paths import config_dir


CONFIG_DIR = config_dir()


@dataclass
class VideoSettings:
    width: int = 1920
    height: int = 1080
    fullscreen: bool = False
    vsync: bool = True


@dataclass
class AudioSettings:
    master_volume: float = 0.8
    music_volume: float = 0.7
    sfx_volume: float = 0.9


@dataclass
class GameSettings:
    difficulty: str = "normal"
    ai_style: str = "balanced"
    show_fps: bool = True


DEFAULT_BINDINGS: Dict[str, Tuple[str, ...]] = {
    "pause": ("p",),
    "save": ("f5",),
    "load": ("f9",),
    "select_all": ("a",),
    "camera_up": ("w",),
    "camera_down": ("s",),
    "camera_left": ("a",),
    "camera_right": ("d",),
    "zoom_in": ("=", "+"),
    "zoom_out": ("-", "_"),
    "build_base": ("b",),
    "build_turret": ("t",),
    "build_factory": ("f",),
    "build_airfield": ("g",),
    "train_infantry": ("1",),
    "train_tank": ("2",),
    "train_aircraft": ("3",),
    "group_assign": ("left ctrl", "right ctrl"),
    "group_select_1": ("1",),
    "group_select_2": ("2",),
    "group_select_3": ("3",),
    "toggle_help": ("h",),
    "upgrade_tech": ("u",),
}


def load_video_settings() -> VideoSettings:
    path = CONFIG_DIR / "video.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return VideoSettings(**data)
        except Exception:
            pass
    settings = VideoSettings()
    try:
        path.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return settings


def load_audio_settings() -> AudioSettings:
    path = CONFIG_DIR / "audio.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AudioSettings(**data)
        except Exception:
            pass
    settings = AudioSettings()
    try:
        path.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return settings


def load_game_settings() -> GameSettings:
    path = CONFIG_DIR / "game.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return GameSettings(**data)
        except Exception:
            pass
    settings = GameSettings()
    try:
        path.write_text(json.dumps(settings.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return settings


def load_key_bindings() -> Dict[str, Tuple[str, ...]]:
    path = CONFIG_DIR / "bindings.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {k: tuple(v) for k, v in data.items()}
        except Exception:
            pass
    try:
        path.write_text(json.dumps(DEFAULT_BINDINGS, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return DEFAULT_BINDINGS.copy()
