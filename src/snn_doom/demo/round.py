# Copyright (c) 2026 Martial Systems LLC
"""Score = kills. hp==0 is lose. Double-kill is not a win. The clock does not eject the window."""
from __future__ import annotations

from dataclasses import dataclass

ROUND_TICKS = 64


@dataclass
class RoundState:
    score: int = 0
    ticks: int = 0
    limit: int = ROUND_TICKS
    e1_was: int = 1
    e2_was: int = 1
    outcome: str = "play"

    def observe(self, st: dict[str, int]) -> str:
        self.ticks += 1
        if self.e1_was and not st.get("enemy_alive"):
            self.score += 1
        if self.e2_was and not st.get("enemy2_alive"):
            self.score += 1
        self.e1_was = int(st.get("enemy_alive") or 0)
        self.e2_was = int(st.get("enemy2_alive") or 0)
        if int(st.get("hp") or 0) <= 0:
            self.outcome = "lose"
            return self.outcome
        self.outcome = "play"
        return "play"
