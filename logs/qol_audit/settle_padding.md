# QoL audit: settle_padding

Verdict: REJECT_WASTE (score 0.48)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 3 neurons, 6 edges. Headroom after spend: 24.

## Score

- observable: 0.00 x 0.30 = 0.00
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 0.70 x 0.15 = 0.10
- cost: 0.50 x 0.15 = 0.07
- cap_named: 1.00 x 0.10 = 0.10
- spec_not_waste: 0.00 x 0.10 = 0.00

## Observables

- none: no player-visible delta becomes internal only (not actionable)

## Parity risk

- held_fwd_tape: CLOCK/SETTLE edits change steps per tick and can desync held-fwd (live green: True, listed: True)
- tick_tape: frame_ok is on every tape step (live green: True, listed: True)

## Reasons

- teacher_delta does not name a teacher field or apply_* function
- Text matches a waste pattern and there is no player-actionable observable.
- No player-actionable observable: turn, fire, door, or flee has nothing new to do.
- Cheaper legal alternative: keep SETTLE 29 (0 neurons) (0 neurons).
- cluster CLOCKPAD: pad SETTLE from 29 to 32 just in case carry chains starve
- teacher_delta does not name a teacher field or apply_* function
- zeroing CLOCKPAD must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.teacher_specifiable
- doom.host_cosmetics

## Cheaper alternative

- keep SETTLE 29 (0 neurons) (0 neurons). 0 < 3

Ablation contract: zeroing CLOCKPAD must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: teacher_delta does not name a teacher field or apply_* function
Bake-off need: False
Fly-scale refused: False

