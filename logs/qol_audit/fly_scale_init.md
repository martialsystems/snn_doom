# QoL audit: fly_scale_init

Verdict: REJECT_BREAKS_LAW (score 0.42)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 158,727 neurons, 400,000 edges. Headroom after spend: -158,700.

## Score

- observable: 0.00 x 0.30 = 0.00
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 1.00 x 0.15 = 0.15
- cost: 0.50 x 0.15 = 0.07
- cap_named: 0.00 x 0.10 = 0.00
- spec_not_waste: 0.00 x 0.10 = 0.00

## Observables

- none: no player-visible delta becomes internal only (not actionable)

## Parity risk

- tick_tape: frame_ok is on every tape step (live green: True, listed: True)

## Reasons

- Fly-scale 166,700 is refused until extra units have a named job.
- Estimated 158727 neurons plus baseline 7973 exceeds cap 8000 (headroom -158700).
- fly cell types are not features
- Text matches a waste pattern and there is no player-actionable observable.
- Cheaper legal alternative: named leftover job under the 8000 cap (est. 27 neurons) (27 neurons).
- cluster FLYSPARE: sparse-init 166700 MaleCNS leftover cells so the net is more Doom
- fly cell types are not features
- zeroing FLYSPARE must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.scale_166k
- doom.v1_cap
- doom.teacher_specifiable
- doom.host_cosmetics

## Cheaper alternative

- named leftover job under the 8000 cap (est. 27 neurons) (27 neurons). 27 < 158727

Ablation contract: zeroing FLYSPARE must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: fly cell types are not features
Bake-off need: False
Fly-scale refused: True

