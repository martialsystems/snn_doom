# Copyright (c) 2026 Martial Systems LLC
"""Sample keys often, latch one-shots for the next SNN tick."""
from __future__ import annotations

from snn_doom.demo.view import CANON_KEYS, keys_to_bits


class InputLatch:
    """Move is level. Fire and door are one-shots. Optional held-forward lock."""

    def __init__(self, *, fwd_lock: bool = False) -> None:
        self.held: set[str] = set()
        if fwd_lock:
            self.held.add("up")
        self.fwd_lock = bool(fwd_lock)
        self._fire = False
        self._door = False
        self.flash: dict[str, bool] = {}

    def press(self, tokens: tuple[str, ...]) -> None:
        for t in tokens:
            if t == "space":
                self._fire = True
                self.flash["muzzle"] = True
            elif t == "e":
                self._door = True
                self.flash["door"] = True
            elif t in CANON_KEYS:
                self.held.add(t)
                if t in ("up", "down", "left", "right"):
                    self.flash["face"] = True

    def release(self, tokens: tuple[str, ...]) -> None:
        for t in tokens:
            if t in ("up", "down", "left", "right"):
                if t == "up" and self.fwd_lock:
                    continue
                self.held.discard(t)
            elif t in CANON_KEYS and t not in ("space", "e"):
                self.held.discard(t)

    def clear(self) -> None:
        self.held.clear()
        if self.fwd_lock:
            self.held.add("up")
        self._fire = False
        self._door = False
        self.flash = {}

    def consume(self) -> tuple[int, dict[str, bool], set[str]]:
        pressed = set(self.held)
        if self.fwd_lock:
            pressed.add("up")
        if self._fire:
            pressed.add("space")
        if self._door:
            pressed.add("e")
        bits = keys_to_bits(pressed)
        flash = dict(self.flash)
        self._fire = False
        self._door = False
        self.flash = {}
        return bits, flash, pressed
