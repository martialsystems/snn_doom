# QoL audit: view_32

Verdict: ACCEPT_WITH_CAP (score 0.88)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 3,200 neurons, 9,000 edges. Headroom after spend: -3,173.

## Score

- observable: 1.00 x 0.30 = 0.30
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 1.00 x 0.15 = 0.15
- cost: 0.50 x 0.15 = 0.07
- cap_named: 0.50 x 0.10 = 0.05
- spec_not_waste: 1.00 x 0.10 = 0.10

## Observables

- decoded_frame: 16 columns becomes 32 columns (actionable)

## Parity risk

- ray_parity: RAY or column-count change can desync 16 distances (live green: True, listed: True)
- ammo_zero_cannot_kill: ammo/fire datapath shares the heading sprite latch (live green: True, listed: True)
- tick_tape: frame_ok is on every tape step (live green: True, listed: True)

## Reasons

- Estimated 3200 neurons plus baseline 7973 exceeds cap 8000 (headroom -3173).
- Job is real; shrink to leftover units or mux an existing ALU.
- Cheaper legal alternative: shared COS/SIN ROM plus column offset (est. 1800 neurons) (1800 neurons).
- cluster VIEW32: VIEW goes from 16 columns to 32 columns, teacher-exact distances, WTA readout
- delta names teacher state or apply_* 
- zeroing VIEW32 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.v1_cap

## Cheaper alternative

- shared COS/SIN ROM plus column offset (est. 1800 neurons) (1800 neurons). 1800 < 3200

Ablation contract: zeroing VIEW32 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: delta names teacher state or apply_* 
Bake-off need: False
Fly-scale refused: False

