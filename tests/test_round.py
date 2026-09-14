# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from snn_doom.demo.round import RoundState


def test_both_sprites_dead_is_play() -> None:
    rnd = RoundState(limit=64)
    st = {"enemy_alive": 0, "enemy2_alive": 0, "hp": 3, "player_hit": 0}
    assert rnd.observe(st) == "play"
    assert rnd.score == 2


def test_tick_clock_does_not_win_while_sprites_live() -> None:
    rnd = RoundState(limit=2)
    live = {"enemy_alive": 1, "enemy2_alive": 1, "hp": 3, "player_hit": 0}
    assert rnd.observe(live) == "play"
    assert rnd.observe(live) == "play"
    one = {"enemy_alive": 0, "enemy2_alive": 1, "hp": 3, "player_hit": 0}
    rnd2 = RoundState(limit=1)
    assert rnd2.observe(one) == "play"
    assert rnd2.score == 1


def test_death_loses() -> None:
    rnd = RoundState(limit=64)
    st = {"enemy_alive": 1, "enemy2_alive": 1, "hp": 0, "player_hit": 1}
    assert rnd.observe(st) == "lose"
    assert rnd.score == 0


def test_player_hit_without_hp_zero_is_play() -> None:
    rnd = RoundState(limit=64)
    st = {"enemy_alive": 1, "enemy2_alive": 1, "hp": 2, "player_hit": 1}
    assert rnd.observe(st) == "play"
