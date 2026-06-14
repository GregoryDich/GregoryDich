# DiD Simulation Results (WS4 Validation)

> Simulated to validate identification strategy. Not evidence.

- Panel: 60 occupations x 232 weeks
- True beta = 0.4

## TWFE Estimate
- beta_hat = 0.3957 (SE = 0.0217)
- 95% CI: [0.3532, 0.4383]
- Bias: 1.1%

## Event Study
- Pre-trend test p = 0.109 (not rejected)
- Avg post-treatment coef = 0.0249

Conclusion: identification strategy recovers the true treatment effect and pre-trends are flat.
