# QoL audit: analog_tau_demo

Verdict: REJECT_BREAKS_LAW (score 0.35)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 0 neurons, 0 edges. Headroom after spend: 27.

## Score

- observable: 0.00 x 0.30 = 0.00
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 0.00 x 0.15 = 0.00
- cost: 1.00 x 0.15 = 0.15
- cap_named: 0.00 x 0.10 = 0.00
- spec_not_waste: 0.00 x 0.10 = 0.00

## Observables

- none: no player-visible delta becomes internal only (not actionable)

## Parity risk

- tick_tape: any stitch edit can drift sequencer re-arm (live green: True, listed: True)

## Reasons

- Analog tau belongs in bake-off, not the digital demo stitch.
- analog tau is bake-off only; demo path is digital tau=0
- Text matches a waste pattern and there is no player-actionable observable.
- cluster ANALOG: switch demo LIF to analog tau=0.8 BPTT for smoother motion
- analog tau is bake-off only; demo path is digital tau=0
- zeroing ANALOG must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.demo_path
- doom.teacher_specifiable
- doom.host_cosmetics

## Cheaper alternative

- digital tau=0 (0 neurons) (0 neurons). not cheaper than the proposal

Ablation contract: zeroing ANALOG must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: analog tau is bake-off only; demo path is digital tau=0
Bake-off need: True
Fly-scale refused: False

