# Encoding bake-off

Seed 0. Rubric: 0.35 accuracy, 0.20 stability, 0.15 noise, 0.15 neuron frugality, 0.15 spike frugality.

| Role | Encoding | Acc | Stab | Noise | Neurons | Spikes/step | Score | Gate |
|------|----------|----:|-----:|------:|--------:|------------:|------:|------|
| CLOCK | rate | 0.875 | 0.875 | 0.844 | 10 | 1.00 | 0.892 | fail |
| CLOCK | population | 0.875 | 0.875 | 0.828 | 34 | 1.00 | 0.899 | fail |
| CLOCK | dual_rail | 1.000 | 1.000 | 0.984 | 8 | 1.00 | 0.978 | pass |
| CLOCK | bistable | 0.125 | 0.125 | 0.203 | 2 | 1.00 | 0.324 | fail |
| CLOCK | wta | 0.891 | 0.875 | 0.875 | 8 | 0.02 | 0.917 | fail |
| CLOCK | oscillator | 1.000 | 1.000 | 0.906 | 8 | 1.00 | 0.967 | pass |
| BIT_LATCH | rate | 0.500 | 1.000 | 0.500 | 6 | 0.07 | 0.748 | fail |
| BIT_LATCH | population | 0.500 | 1.000 | 0.542 | 18 | 0.07 | 0.754 | fail |
| BIT_LATCH | dual_rail | 1.000 | 1.000 | 0.979 | 8 | 1.39 | 0.970 | pass |
| BIT_LATCH | bistable | 1.000 | 1.000 | 0.979 | 8 | 1.39 | 0.970 | pass |
| BIT_LATCH | wta | 0.500 | 0.000 | 0.521 | 2 | 1.00 | 0.478 | fail |
| BIT_LATCH | oscillator | 0.500 | 1.000 | 0.479 | 6 | 0.07 | 0.745 | fail |
| REGISTER_FILE | rate | 0.000 | 0.000 | 0.000 | 77 | 0.00 | 0.294 | fail |
| REGISTER_FILE | population | 0.000 | 0.000 | 0.000 | 77 | 0.00 | 0.294 | fail |
| REGISTER_FILE | dual_rail | 1.000 | 1.000 | 0.875 | 104 | 4.00 | 0.968 | pass |
| REGISTER_FILE | bistable | 1.000 | 1.000 | 0.875 | 104 | 4.00 | 0.968 | pass |
| REGISTER_FILE | wta | 1.000 | 1.000 | 0.625 | 104 | 4.00 | 0.930 | pass |
| REGISTER_FILE | oscillator | 0.000 | 0.000 | 0.000 | 77 | 0.00 | 0.294 | fail |
| ADDER_COMPARE | rate | 0.050 | 0.000 | 0.050 | 62 | 0.00 | 0.320 | fail |
| ADDER_COMPARE | population | 0.050 | 0.000 | 0.050 | 142 | 0.00 | 0.314 | fail |
| ADDER_COMPARE | dual_rail | 1.000 | 1.000 | 1.000 | 129 | 46.41 | 0.936 | pass |
| ADDER_COMPARE | bistable | 1.000 | 1.000 | 1.000 | 129 | 46.41 | 0.936 | pass |
| ADDER_COMPARE | wta | 0.050 | 0.000 | 0.050 | 62 | 0.00 | 0.320 | fail |
| ADDER_COMPARE | oscillator | 0.050 | 0.000 | 0.050 | 62 | 0.00 | 0.320 | fail |
| RAM | rate | 0.000 | 0.000 | 0.000 | 71 | 0.00 | 0.295 | fail |
| RAM | population | 0.000 | 0.000 | 0.000 | 71 | 0.00 | 0.295 | fail |
| RAM | dual_rail | 1.000 | 1.000 | 1.000 | 142 | 9.00 | 0.980 | pass |
| RAM | bistable | 1.000 | 1.000 | 1.000 | 142 | 9.00 | 0.980 | pass |
| RAM | wta | 1.000 | 1.000 | 1.000 | 142 | 9.00 | 0.980 | pass |
| RAM | oscillator | 0.000 | 0.000 | 0.000 | 71 | 0.00 | 0.295 | fail |
| SEQUENCER | rate | 0.000 | 0.000 | 0.000 | 32 | 0.04 | 0.297 | fail |
| SEQUENCER | population | 0.000 | 0.000 | 0.000 | 32 | 0.04 | 0.297 | fail |
| SEQUENCER | dual_rail | 1.000 | 1.000 | 1.000 | 8 | 1.00 | 0.981 | pass |
| SEQUENCER | bistable | 0.125 | 0.125 | 0.125 | 16 | 1.00 | 0.377 | fail |
| SEQUENCER | wta | 1.000 | 1.000 | 1.000 | 8 | 1.00 | 0.981 | pass |
| SEQUENCER | oscillator | 1.000 | 1.000 | 1.000 | 8 | 1.00 | 0.981 | pass |
| RAY_COLUMN | rate | 0.100 | 0.000 | 0.100 | 154 | 1.00 | 0.337 | fail |
| RAY_COLUMN | population | 0.100 | 0.000 | 0.100 | 218 | 1.00 | 0.333 | fail |
| RAY_COLUMN | dual_rail | 0.000 | 0.000 | 0.000 | 1000 | 228.67 | 0.191 | fail |
| RAY_COLUMN | bistable | 0.000 | 0.000 | 0.000 | 1000 | 228.67 | 0.191 | fail |
| RAY_COLUMN | wta | 0.100 | 0.000 | 0.100 | 154 | 1.00 | 0.337 | fail |
| RAY_COLUMN | oscillator | 0.100 | 0.000 | 0.100 | 154 | 1.00 | 0.337 | fail |
| FRAME_READOUT | rate | 0.100 | 0.000 | 0.100 | 384 | 1.00 | 0.321 | fail |
| FRAME_READOUT | population | 1.000 | 1.000 | 1.000 | 1696 | 352.00 | 0.842 | pass |
| FRAME_READOUT | dual_rail | 1.000 | 1.000 | 1.000 | 1696 | 352.00 | 0.842 | pass |
| FRAME_READOUT | bistable | 0.100 | 0.000 | 0.100 | 384 | 1.00 | 0.321 | fail |
| FRAME_READOUT | wta | 1.000 | 1.000 | 1.000 | 1696 | 352.00 | 0.842 | pass |
| FRAME_READOUT | oscillator | 0.100 | 0.000 | 0.100 | 384 | 1.00 | 0.321 | fail |

## Winners

- CLOCK: dual_rail
- BIT_LATCH: dual_rail
- REGISTER_FILE: dual_rail
- ADDER_COMPARE: dual_rail
- RAM: dual_rail
- SEQUENCER: dual_rail
- RAY_COLUMN: none
- FRAME_READOUT: population
