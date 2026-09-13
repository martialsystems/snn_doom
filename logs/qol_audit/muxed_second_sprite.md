# QoL audit: muxed_second_sprite

Verdict: ACCEPT_WITH_CAP (score 0.91)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 40 neurons, 90 edges. Headroom after spend: -13.

## Score

- observable: 1.00 x 0.30 = 0.30
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 0.70 x 0.15 = 0.10
- cost: 1.00 x 0.15 = 0.15
- cap_named: 0.50 x 0.10 = 0.05
- spec_not_waste: 1.00 x 0.10 = 0.10

## Observables

- teacher_state.ex2: stationary statue at (2,2) becomes X-then-Y chase each pose (actionable)
- decoded_frame: COLOR_ENEMY blob only if heading visits (2,2) becomes second moving column blob; contact still decrements HP (actionable)

## Parity risk

- held_fwd_tape: walking e2 can enter a heading column; held-fwd requires hitscan 0 and frame L1 0 (live green: True, listed: True)
- tick_tape: e2 pose bits and frames are on the multi-tick tape (live green: True, listed: True)

## Reasons

- Estimated 40 neurons plus baseline 7973 exceeds cap 8000 (headroom -13).
- Job is real; shrink to leftover units or mux an existing ALU.
- cluster ENEMY2: reuse e1 ALU through a mux so e2 takes one extra pose window
- apply_enemy2 exists and is not called from tick(); teacher can express the delta
- zeroing ENEMY2 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.v1_cap

## Cheaper alternative

- duplicate enemy ALU (est. 86 neurons) (86 neurons). not cheaper than the proposal

Ablation contract: zeroing ENEMY2 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: apply_enemy2 exists and is not called from tick(); teacher can express the delta
Bake-off need: False
Fly-scale refused: False

