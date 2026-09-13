# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.demo.round import RoundState


def test_clear_sprites_wins() -> None:
    rnd = RoundState(limit=64)
    st = {"enemy_alive": 0, "enemy2_alive": 0, "hp": 3, "player_hit": 0}
    assert rnd.observe(st) == "win"
    assert rnd.score == 2


def test_survive_limit_wins() -> None:
    rnd = RoundState(limit=2)
    live = {"enemy_alive": 1, "enemy2_alive": 1, "hp": 3, "player_hit": 0}
    assert rnd.observe(live) == "play"
    assert rnd.observe(live) == "win"


def test_death_loses() -> None:
    rnd = RoundState(limit=64)
    st = {"enemy_alive": 1, "enemy2_alive": 1, "hp": 0, "player_hit": 1}
    assert rnd.observe(st) == "lose"
    assert rnd.score == 0
