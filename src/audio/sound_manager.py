"""
Звуковые эффекты — клики, бои, строительство
"""

import os
import pygame

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds")
_sounds = {}
_mixer_initialized = False


def _init_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            _mixer_initialized = True
        except Exception:
            pass


def _load(name: str):
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
    _init_mixer()
    s = _load("click.wav")
    if s:
        s.play()


def play_battle():
    _init_mixer()
    s = _load("battle.wav") or _load("combat.wav")
    if s:
        s.play()


def play_build():
    _init_mixer()
    s = _load("build.wav") or _load("construction.wav")
    if s:
        s.play()


def play_capture():
    _init_mixer()
    s = _load("capture.wav") or _load("victory.wav")
    if s:
        s.play()


def play_diplomacy():
    _init_mixer()
    s = _load("diplomacy.wav") or _load("click.wav")
    if s:
        s.play()


def play_error():
    _init_mixer()
    s = _load("error.wav")
    if s:
        s.play()
