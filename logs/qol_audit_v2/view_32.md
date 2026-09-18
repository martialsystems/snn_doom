# QoL audit: view_32

Verdict: ACCEPT (score 1.00)

Baseline: 7,973 neurons, 41,811 edges, cap 12,000.
Ask: 880 neurons, 0 edges. Headroom after spend: 3,147.

## Score

- observable: 1.00 x 0.30 = 0.30
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 1.00 x 0.15 = 0.15
- cost: 1.00 x 0.15 = 0.15
- cap_named: 1.00 x 0.10 = 0.10
- spec_not_waste: 1.00 x 0.10 = 0.10

## Observables

- decoded_frame: 16 columns becomes 32 columns (actionable)

## Parity risk

- ray_parity: RAY or column-count change can desync 16 distances (live green: True, listed: True)
- ammo_zero_cannot_kill: ammo/fire datapath shares the heading sprite latch (live green: True, listed: True)
- tick_tape: frame_ok is on every tape step (live green: True, listed: True)

## Reasons

- Named job, teacher-specifiable, under cap, cheaper legal alt does not dominate.
- cluster VIEW32: VIEW goes from 16 columns to 32 columns, teacher-exact distances, WTA readout
- delta names teacher state or apply_* 
- zeroing VIEW32 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- none

## Cheaper alternative

- per-column COS/SIN ROMs (est. 3200 neurons) (3200 neurons). not cheaper than the proposal

Ablation contract: zeroing VIEW32 must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: delta names teacher state or apply_* 
Bake-off need: False
Fly-scale refused: False

