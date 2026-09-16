# QoL audit: host_radar

Verdict: REJECT_WASTE (score 0.47)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 0 neurons, 0 edges. Headroom after spend: 27.

## Score

- observable: 0.00 x 0.30 = 0.00
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 0.80 x 0.15 = 0.12
- cost: 1.00 x 0.15 = 0.15
- cap_named: 0.00 x 0.10 = 0.00
- spec_not_waste: 0.00 x 0.10 = 0.00

## Observables

- none: no player-visible delta becomes internal only (not actionable)

## Parity risk

- door: door occupancy pulse is a 2-step we_ram window (live green: True, listed: False)
- tick_tape: frame_ok is on every tape step (live green: True, listed: True)

## Reasons

- Host overlay that fakes engine work is banned on the demo path.
- teacher_delta does not name a teacher field or apply_* function
- Text matches a waste pattern and there is no player-actionable observable.
- No player-actionable observable: turn, fire, door, or flee has nothing new to do.
- cluster HOSTRADAR: Python blit a HOST_RADAR panel from REGISTER_FILE and RAM bits
- teacher_delta does not name a teacher field or apply_* function
- zeroing HOSTRADAR must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.demo_path
- doom.teacher_specifiable
- doom.host_cosmetics

## Cheaper alternative

- leave HOST_RADAR in demo/radar.py (0 neurons) (0 neurons). not cheaper than the proposal

Ablation contract: zeroing HOSTRADAR must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: teacher_delta does not name a teacher field or apply_* function
Bake-off need: False
Fly-scale refused: False

