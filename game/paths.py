from __future__ import annotations

import os
import sys
import platform
from pathlib import Path


def is_android() -> bool:
    return "ANDROID_ARGUMENT" in os.environ


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path.cwd()
    if is_android():
        # Android: assets are in a private storage or accessible via specialized API
        # But for simple file reading, current working dir is usually mapped to assets
        return Path.cwd()
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    if is_android():
        try:
            from android.storage import app_storage_path
            return Path(app_storage_path())
        except (ImportError, Exception):
            # Fallback for some android environments
            return Path(".").resolve()
    return runtime_root()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    root = user_data_dir() if is_android() else runtime_root()
    return ensure_dir(root / "config")


def assets_dir() -> Path:
    # On Android, assets are extracted or accessible directly
    return ensure_dir(runtime_root() / "assets")


def saves_dir() -> Path:
    root = user_data_dir() if is_android() else runtime_root()
    return ensure_dir(root / "saves")
