# QoL audit: spare_latches

Verdict: REJECT_WASTE (score 0.60)

Baseline: 7,973 neurons, 41,811 edges, cap 8,000.
Ask: 20 neurons, 40 edges. Headroom after spend: 7.

## Score

- observable: 0.00 x 0.30 = 0.00
- named_job_ablation: 1.00 x 0.20 = 0.20
- parity: 1.00 x 0.15 = 0.15
- cost: 1.00 x 0.15 = 0.15
- cap_named: 1.00 x 0.10 = 0.10
- spec_not_waste: 0.00 x 0.10 = 0.00

## Observables

- hidden_bits: not in STATE_FIELDS becomes spare0,spare1 (not actionable)

## Parity risk

- tick_tape: any stitch edit can drift sequencer re-arm (live green: True, listed: True)

## Reasons

- teacher_delta does not name a teacher field or apply_* function
- Text matches a waste pattern and there is no player-actionable observable.
- No player-actionable observable: turn, fire, door, or flee has nothing new to do.
- cluster SPARE: add spare latches for capacity for later
- teacher_delta does not name a teacher field or apply_* function
- zeroing SPARE must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape

## Gates failed

- doom.teacher_specifiable
- doom.host_cosmetics

## Cheaper alternative

- spend leftover units on a named job (est. 27 neurons) (27 neurons). not cheaper than the proposal

Ablation contract: zeroing SPARE must kill only the new job; CLOCK/LATCH/REG/ALU/RAM/RAY/READOUT/DOOR rows in logs/ablation.json must keep their isolation shape
Teacher specifiable: teacher_delta does not name a teacher field or apply_* function
Bake-off need: False
Fly-scale refused: False

