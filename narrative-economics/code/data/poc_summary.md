# Proof of Concept Results (SIMULATED)

> Numbers are simulated to validate the instrument, not evidence.

- Events: X- = 3020, X+ = 512

## Naive Hawkes MLE
- n_hat(X-) = 0.958 [90% CI 0.914, 0.973], true 0.85
- n_hat(X+) = 0.726 [90% CI 0.657, 0.782], true 0.55
- H6: SUPPORTED

## Shock-aware Hawkes MLE (de-biased, WS5.1)
- n_hat(X-) = 0.856 [90% CI 0.826, 0.879], true 0.85
- n_hat(X+) = 0.511 [90% CI 0.444, 0.575], true 0.55
- gamma decay: X- = 1.8061 (t1/2 = 0.4d), X+ = 1.4692 (t1/2 = 0.5d)
- H6: SUPPORTED

## Bias reduction
- X-: 13% -> 1%
- X+: 32% -> 7%

## Exp-growth R0 proxy
- X- = 1.55, X+ = 1.34
