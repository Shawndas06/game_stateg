"""
sound_manager.py — воспроизведение звуковых эффектов.

Реализует:
- Ленивую инициализацию pygame.mixer и кэш загруженных звуков.
- Функции воспроизведения: play_click, play_build, play_capture, play_diplomacy, play_battle, play_error.
- Звуки ищутся в assets/sounds/ (click.wav, capture.wav, build.wav и т.д.); при отсутствии файла воспроизведение просто не выполняется.
"""

import os
import pygame

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds")
_sounds = {}
_mixer_initialized = False


def _init_mixer():
    """Однократная инициализация микшера Pygame (частота, каналы, буфер)."""
    global _mixer_initialized
    if not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            _mixer_initialized = True
        except Exception:
            pass


def _load(name: str):
    """Загрузить звуковой файл по имени (с кэшем). Возвращает pygame.mixer.Sound или None."""
    if name in _sounds:
        return _sounds[name]
    path = os.path.join(SOUNDS_DIR, name)
    if os.path.exists(path):
        try:
            s = pygame.mixer.Sound(path)
            _sounds[name] = s
            return s
        except Exception:
            pass
    return None


def play_click():
    """Звук клика по кнопке."""
    _init_mixer()
    s = _load("click.wav")
    if s:
        s.play()


def play_battle():
    """Звук боя (battle.wav или combat.wav)."""
    _init_mixer()
    s = _load("battle.wav") or _load("combat.wav")
    if s:
        s.play()


def play_build():
    """Звук начала строительства (build.wav или construction.wav)."""
    _init_mixer()
    s = _load("build.wav") or _load("construction.wav")
    if s:
        s.play()


def play_capture():
    """Звук захвата крепости (capture.wav или victory.wav)."""
    _init_mixer()
    s = _load("capture.wav") or _load("victory.wav")
    if s:
        s.play()


def play_diplomacy():
    """Звук дипломатического действия (diplomacy.wav или click.wav)."""
    _init_mixer()
    s = _load("diplomacy.wav") or _load("click.wav")
    if s:
        s.play()


def play_error():
    """Звук ошибки (error.wav)."""
    _init_mixer()
    s = _load("error.wav")
    if s:
        s.play()
