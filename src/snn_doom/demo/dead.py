# Copyright (c) 2026 Martial Systems LLC
"""HOST_DEAD: host splash when latched hp hits 0. 0 neurons. Not FRAME_READOUT."""
from __future__ import annotations

from typing import Any

from snn_doom.teacher.maps import spawn
from snn_doom.teacher.state import GameState

SPLASH = "YOU DIED"
RESTART_HINT = "R restart"


class HostDead:
    """Latch hp==0, gate keys, restart from spawn. Does not paint 16x18."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self.dead = False
        self.restart = False
        self.artists: dict[str, Any] = {}

    def observe_hp(self, hp: int) -> bool:
        if self.enabled and int(hp) == 0:
            self.dead = True
        return self.dead

    def gate_bits(self, bits: int) -> int:
        return 0 if self.dead else int(bits)

    def note_tokens(self, tokens: tuple[str, ...]) -> None:
        if self.dead and any(t in ("r", "restart") for t in tokens):
            self.restart = True

    def hide(self) -> None:
        self.dead = False
        self.restart = False
        self._set_visible(False)

    def show(self) -> None:
        self._set_visible(True)

    def _set_visible(self, on: bool) -> None:
        for key in ("ax_dead", "ax_dead_btn"):
            ax = self.artists.get(key)
            if ax is not None:
                ax.set_visible(on)

    def attach(self, fig, artists: dict[str, Any]) -> None:
        if not self.enabled or fig is None:
            return
        from matplotlib.widgets import Button

        ax = fig.add_axes((0.2, 0.32, 0.6, 0.4))
        ax.set_facecolor("#400000")
        ax.set_title("HOST_DEAD", color="#ffcccc", fontsize=10, fontfamily="monospace")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(
            0.5,
            0.68,
            SPLASH,
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="#ffe8e8",
            fontsize=28,
            fontfamily="monospace",
        )
        ax.text(
            0.5,
            0.38,
            RESTART_HINT,
            ha="center",
            va="center",
            transform=ax.transAxes,
            color="#e0c0c0",
            fontsize=12,
            fontfamily="monospace",
        )
        bax = fig.add_axes((0.38, 0.36, 0.24, 0.08))
        btn = Button(bax, "Restart", color="#802020", hovercolor="#a03030")
        btn.label.set_color("#fff0f0")
        btn.on_clicked(lambda _evt: setattr(self, "restart", True))
        ax.set_visible(False)
        bax.set_visible(False)
        self.artists = {"ax_dead": ax, "ax_dead_btn": bax, "dead_btn": btn}
        artists["ax_dead"] = ax
        artists["ax_dead_btn"] = bax
        artists["dead_btn"] = btn

    def tty_banner(self) -> str:
        if not self.dead:
            return ""
        return f"HOST_DEAD\n{SPLASH}\n{RESTART_HINT}"


def restore_spawn(machine, state0: GameState | None = None) -> dict[str, int]:
    """pipeline.reset to DEFAULT_* spawn. No new LIF graph."""
    s0 = state0 if state0 is not None else spawn()
    machine.reset(s0)
    return machine.read_state()
