Learned model, Round 2 held out. Threshold locked at 0.3559 (chosen on Round 1 CV).

| | Amharic | Oromo |
|---|---|---|
| Dangerous translations | 31 / 100 | 27 / 100 |
| Learned model: recall of dangerous | 61% (95% CI 44% to 78%) | 56% (95% CI 36% to 74%) |
| Learned model: sentences flagged | 42% (95% CI 32% to 52%) | 29% (95% CI 20% to 38%) |
| Learned model: false warnings | 23 (95% CI 15 to 31) | 14 (95% CI 7 to 21) |
| Rule gate (for reference): recall / flagged / false warnings | 81% / 55% / 30 | 93% / 62% / 37 |
| chrF-only at the learned model's recall: false warnings | 31 (95% CI 12 to 42) | 14 (95% CI 4 to 27) |
| chrF-only minus learned model (paired) | +8 (95% CI -12 to +21) | +0 (95% CI -12 to +14) |
| AUROC, learned model probability | 0.73 (95% CI 0.62 to 0.83) | 0.73 (95% CI 0.61 to 0.83) |
| AUROC, chrF | 0.69 (95% CI 0.59 to 0.79) | 0.77 (95% CI 0.66 to 0.86) |
| AUROC difference, learned minus chrF (paired) | +0.03 (95% CI -0.11 to +0.17) | -0.04 (95% CI -0.16 to +0.06) |