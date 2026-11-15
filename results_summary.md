# Results summary

**This project is a prototype and is not medical advice.**


## Rating progress
```
{'amharic r1': '100/100', 'amharic r2': '100/100', 'oromo': '50/50', 'oromo retest': '15/15'}
```

## Amharic rater agreement (two independent raters)
```
{'n': 100, 'exact_agreement': 0.79, 'kappa': 0.634, 'weighted_kappa': 0.728, 'safe_vs_dangerous_disagreements(0 vs 2)': 2}
```

## Oromo rater self-consistency (same person, re-rated later)
```
{'n': 15, 'same_rating_both_times': 0.733, 'weighted_kappa': 0.63}
```

## amharic: is chrF blind to danger? (all rated sentences)
```
{'n_rated': 100, 'n_safe': 50, 'n_confusing': 23, 'n_dangerous': 27, 'mean_chrF_safe': 54.1, 'mean_chrF_dangerous': 31.7, 'spearman_chrF_vs_rating': -0.461, 'auroc_low_chrF_detects_dangerous': 0.716, 'auroc_95ci_bootstrap': '0.60-0.82', 'dangerous_with_chrF_at_or_above_median_of_safe': '6/27', 'safe_but_chrF_below_overall_median': '14/50'}
```

## amharic: dangerous rate by category
```
                     n  dangerous  dangerous_rate  mean_chrF
category                                                    
frequency_duration  37          6           0.162       54.2
negation_warning    20          4           0.200       40.6
quantity            26         10           0.385       32.5
route_condition     17          7           0.412       43.3
```

## amharic: error types of dangerous translations
```
amharic_error_type
wrong_term         17
gibberish           2
route               2
wrong_word          2
missing_content     1
hallucination       1
omission            1
negation            1
```

## amharic: DEV sweep (top 8; pick thresholds from here ONLY)
```
     n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci  sim_threshold  coverage_threshold
3   52               13                    5               4      0.231                0.615   0.36-0.82            0.5                 0.7
7   52               13                    5               4      0.231                0.615   0.36-0.82            0.6                 0.7
11  52               13                    5               4      0.231                0.615   0.36-0.82            0.7                 0.7
15  52               13                    5               4      0.231                0.615   0.36-0.82            0.8                 0.7
12  52               13                    7               3      0.173                0.462   0.23-0.71            0.8                 0.4
13  52               13                    7               3      0.173                0.462   0.23-0.71            0.8                 0.5
14  52               13                    7               3      0.173                0.462   0.23-0.71            0.8                 0.6
0   52               13                    8               2      0.135                0.385   0.18-0.64            0.5                 0.4
```

## oromo: is chrF blind to danger? (all rated sentences)
```
{'n_rated': 50, 'n_safe': 20, 'n_confusing': 21, 'n_dangerous': 9, 'mean_chrF_safe': 61.1, 'mean_chrF_dangerous': 34.6, 'spearman_chrF_vs_rating': -0.571, 'auroc_low_chrF_detects_dangerous': 0.753, 'auroc_95ci_bootstrap': '0.55-0.93', 'dangerous_with_chrF_at_or_above_median_of_safe': '1/9', 'safe_but_chrF_below_overall_median': '5/20'}
```

## oromo: dangerous rate by category
```
                     n  dangerous  dangerous_rate  mean_chrF
category                                                    
frequency_duration  13          1           0.077       57.1
negation_warning    12          0           0.000       51.0
quantity            13          5           0.385       39.4
route_condition     12          3           0.250       46.9
```

## oromo: error types of dangerous translations
```
oromo_error_type
wrong_word                                                                                     3
wrong_sentances                                                                                3
wrong_word wrong_sentances                                                                     1
completely diffrent meaning than the english                                                   1
completly diffrent meaning, it say take one hour in the morning and one hour in the evining    1
```

## oromo: DEV sweep (top 8; pick thresholds from here ONLY)
```
     n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci  sim_threshold  coverage_threshold
0   25                5                    0               5       0.40                  1.0   0.57-1.00            0.5                 0.4
4   25                5                    0               5       0.40                  1.0   0.57-1.00            0.6                 0.4
8   25                5                    0               6       0.44                  1.0   0.57-1.00            0.7                 0.4
12  25                5                    0               6       0.44                  1.0   0.57-1.00            0.8                 0.4
1   25                5                    0               7       0.48                  1.0   0.57-1.00            0.5                 0.5
2   25                5                    0               7       0.48                  1.0   0.57-1.00            0.5                 0.6
5   25                5                    0               7       0.48                  1.0   0.57-1.00            0.6                 0.5
6   25                5                    0               7       0.48                  1.0   0.57-1.00            0.6                 0.6
```

## Locked thresholds
```
{
  "thresholds": {
    "amharic": [
      0.6,
      0.7
    ],
    "oromo": [
      0.6,
      0.4
    ]
  },
  "locked_utc": "2026-11-14T13:56:07.449964+00:00",
  "rule": "chosen on the dev split only"
}
```

## amharic: FINAL TEST report (sim=0.6, coverage=0.7)
```
                                               gate   n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci
0                               baseline (show all)  48               14                   14               0      0.000                0.000   0.00-0.22
1                   layer 1 (target-language rules)  48               14                   14               0      0.000                0.000   0.00-0.22
2                        layer 2 (back-translation)  48               14                   11               2      0.104                0.214   0.08-0.48
3  layer 3 (units, conditions, key terms, coverage)  48               14                    8               4      0.208                0.429   0.21-0.67
4                                        layers 1+2  48               14                   11               2      0.104                0.214   0.08-0.48
5                                        all layers  48               14                    8               5      0.229                0.429   0.21-0.67
6            chrF-only gate (matched to all layers)  48               14                    8               5      0.229                0.429   0.21-0.67
```

## amharic: dangerous translations with the HIGHEST chrF (hero examples)
```
     id                                                english                                     amharic_mt                                           amharic_back  amharic_chrf  gate_flagged                                                  gate_reasons
69  S70                        Take the tablets for two weeks.                        ጡባዊዎቹን ለሁለት ሳምንታት ይውሰዱ።                        take the tablets for two weeks.     57.989838         False                                                              
74  S75                        Take one tablet before bedtime.                       ከመተኛትዎ በፊት አንድ ጡባዊ ይውሰዱ.                       Take a pill before going to bed.     56.150168          True                                      low word coverage (0.60)
89  S90             Do not stop taking this medicine suddenly.                    ይህን መድሃኒት በድንገት መውሰድዎን አቁሙ።                    stop taking this medicine suddenly.     55.604322          True  negation missing; negation changed; low word coverage (0.67)
16  S17  Take the tablets for 7 days, even if you feel better.  ጡባዊዎቹን ለ 7 ቀናት ይውሰዱ, ምንም እንኳን የተሻለ ስሜት ቢሰማዎት.  Take the tablets for 7 days, even if you feel better.     54.574543         False                                                              
97  S98          Dissolve the tablet in water before drinking.                  ከመጠጣትዎ በፊት ጡባዊውን በውሃ ውስጥ ይሟሉ.           Before drinking, fill the tablet with water.     51.123804          True                                       key term lost: dissolve
```

## oromo: FINAL TEST report (sim=0.6, coverage=0.4)
```
                                               gate   n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci
0                               baseline (show all)  25                4                    4               0       0.00                  0.0   0.00-0.49
1                   layer 1 (target-language rules)  25                4                    2               0       0.08                  0.5   0.15-0.85
2                        layer 2 (back-translation)  25                4                    0               7       0.44                  1.0   0.51-1.00
3  layer 3 (units, conditions, key terms, coverage)  25                4                    0               9       0.52                  1.0   0.51-1.00
4                                        layers 1+2  25                4                    0               7       0.44                  1.0   0.51-1.00
5                                        all layers  25                4                    0              10       0.56                  1.0   0.51-1.00
6            chrF-only gate (matched to all layers)  25                4                    0              12       0.64                  1.0   0.51-1.00
```

## oromo: dangerous translations with the HIGHEST chrF (hero examples)
```
     id                                                 english                                                       oromo_mt                                                oromo_back  oromo_chrf  gate_flagged                                                                                                                                         gate_reasons
2   S03                                Take two 500 mg tablets.                               Daabiloota 500 mg lama fudhadhu.                                 Take two doses of 500 mg.   63.769366          True                                                                                                                                    unit lost: tablet
11  S12                          Use one puff from the inhaler.                       Inhaalaator irraa fagoo tokko fayyadami.                            Use a remote from the inhaler.   56.275948          True                                                                                                                             number/frequency changed
17  S18  Take one tablet in the morning and one in the evening.  Ganama sa'aatii tokko, galgala immoo sa'aatii tokko fudhadhu.  Spend an hour in the morning and an hour in the evening.   53.703386          True                                                                                                          unit lost: tablet; meaning drift (sim 0.45)
42  S43               Take one tablet only if you have a fever.                     Qilleensa tokko yoo qabdan qofa fudhadhaa.                               Take a breath of fresh air.   29.990102          True  number/frequency changed; unit lost: tablet; condition lost: if/when/only; key term lost: fever; meaning drift (sim 0.25); low word coverage (0.17)
47  S48              This ointment is for use on the skin only.            Dandeettiin kun maqaarratti qofa kan hojjetamu dha.                        This ability is used only by name.   28.989939          True                                                                              key term lost: skin; meaning drift (sim 0.29); low word coverage (0.25)
```

## Limitations and disclosures (copy these into the write-up)
- The test set is deliberately hard (negations, stop-rules, edge doses); error rates here are NOT real-world rates.
- Afaan Oromo rests on ONE rater and 50 sentences (about 25 dev / 25 test): treat it as indicative only.
- The Oromo rater is also the coder and had seen model outputs before rating, so Oromo ratings are not fully blind.
- Gate rules were written after looking at model outputs for ALL sentences (dev and test); only the thresholds were tuned on dev alone. The test split is therefore not fully unseen for rule design.
- Amharic uses the worse (higher) of two independent ratings: a deliberately conservative choice.
- Back-translation uses the same model, so a consistent error can survive the round trip.
- chrF uses one reference per sentence; valid synonyms (e.g. different words for 'tablet') are penalised.
- Amharic negation detection is a prefix heuristic with an exception list; Oromo negation looks for 'hin'.
- No real patient data was used.
- This project is a prototype and is not medical advice.
