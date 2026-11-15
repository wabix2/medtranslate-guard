# Results summary

**This project is a prototype and is not medical advice.**


## Rating progress
```
{'amharic r1': '100/100', 'amharic r2': '100/100', 'oromo': '100/100', 'oromo retest': '0/0'}
```

## Amharic rater agreement (two independent raters)
```
{'n': 100, 'exact_agreement': 0.57, 'kappa': 0.315, 'weighted_kappa': 0.412, 'safe_vs_dangerous_disagreements(0 vs 2)': 7}
```

## Oromo rater self-consistency (same person, re-rated later)
```
{'n': 0}
```

## amharic: is chrF blind to danger? (all rated sentences)
```
{'n_rated': 100, 'n_safe': 33, 'n_confusing': 36, 'n_dangerous': 31, 'mean_chrF_safe': 42.1, 'mean_chrF_dangerous': 28.3, 'spearman_chrF_vs_rating': -0.333, 'auroc_low_chrF_detects_dangerous': 0.695, 'auroc_95ci_bootstrap': '0.58-0.80', 'dangerous_with_chrF_at_or_above_median_of_safe': '0/31', 'safe_but_chrF_below_overall_median': '14/33'}
```

## amharic: dangerous rate by category
```
                     n  dangerous  dangerous_rate  mean_chrF
category                                                    
frequency_duration  13          2           0.154       37.8
negation_warning    30          6           0.200       37.4
quantity            24          8           0.333       34.2
route_condition     33         15           0.455       34.1
```

## amharic: error types of dangerous translations
```
amharic_error_type
wrong_term         12
wrong_word          5
route               4
gibberish           4
condition           2
quantity            2
other               1
missing_content     1
```

## amharic: DEV sweep (top 8; pick thresholds from here ONLY)
```
Empty DataFrame
Columns: []
Index: []
```

## oromo: is chrF blind to danger? (all rated sentences)
```
{'n_rated': 100, 'n_safe': 33, 'n_confusing': 40, 'n_dangerous': 27, 'mean_chrF_safe': 50.2, 'mean_chrF_dangerous': 31.5, 'spearman_chrF_vs_rating': -0.455, 'auroc_low_chrF_detects_dangerous': 0.769, 'auroc_95ci_bootstrap': '0.67-0.86', 'dangerous_with_chrF_at_or_above_median_of_safe': '3/27', 'safe_but_chrF_below_overall_median': '8/33'}
```

## oromo: dangerous rate by category
```
                     n  dangerous  dangerous_rate  mean_chrF
category                                                    
frequency_duration  13          2           0.154       48.5
negation_warning    30          4           0.133       49.9
quantity            24         10           0.417       32.2
route_condition     33         11           0.333       41.3
```

## oromo: error types of dangerous translations
```
oromo_error_type
wrong_instruction    6
wrong_sentances      6
wrong_grammer        3
wrong_instraction    3
wrong_sentance       3
wrong_word           2
confusing_grammer    1
wrong_sentence       1
worng_instruction    1
wrong_sentences      1
```

## oromo: DEV sweep (top 8; pick thresholds from here ONLY)
```
Empty DataFrame
Columns: []
Index: []
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
                                               gate    n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci
0                               baseline (show all)  100               31                   31               0       0.00                0.000   0.00-0.11
1                   layer 1 (target-language rules)  100               31                   28               6       0.09                0.097   0.03-0.25
2                        layer 2 (back-translation)  100               31                   20               8       0.19                0.355   0.21-0.53
3  layer 3 (units, conditions, key terms, coverage)  100               31                    9              24       0.46                0.710   0.53-0.84
4                                        layers 1+2  100               31                   18              12       0.25                0.419   0.26-0.59
5                                        all layers  100               31                    6              30       0.55                0.806   0.64-0.91
6            chrF-only gate (matched to all layers)  100               31                    6              36       0.61                0.806   0.64-0.91
```

## amharic: dangerous translations with the HIGHEST chrF (hero examples)
```
      id                                                            english                                     amharic_mt                                                               amharic_back  amharic_chrf  gate_flagged                                                        gate_reasons
33  S134           Do not lie down for 30 minutes after taking this tablet.      ይህን ጡባዊ ከወሰዱ በኋላ ለ30 ደቂቃ ያህል መተኛት የለብዎትም.   After taking this tablet, you should not sleep for more than 30 minutes.     43.085429          True                          negation missing; low word coverage (0.62)
93  S194  If you cannot swallow the tablet, ask a health worker what to do.  ጡባዊውን መብላት ካልቻሉ ምን ማድረግ እንዳለባቸው ለጤና ባለሙያ ጠይቁ።  if you can't eat the tablet, ask your healthcare professional what to do.     42.865674          True  negation missing; key term lost: swallow; low word coverage (0.50)
71  S172                  Use the inhaler twice a day, morning and evening.               መርፌውን በቀን ሁለት ጊዜ ጠዋት እና ማታ ይጠቀሙ።                   use the syringe twice a day in the morning and at night.     42.557513          True                  meaning drift (sim 0.59); low word coverage (0.67)
70  S171                                  Take one lozenge every two hours.                         በየሁለት ሰዓቱ አንድ ሾርባ ውሰድ።                                             Take one soup every two hours.     40.989989          True                                            meaning drift (sim 0.57)
64  S165                                          Break the tablet in half.                               ጡባዊውን በሁለት ይሰብሩ።                                                   break the tablet in two.     39.600385          True  'half' missing; number/frequency changed; low word coverage (0.67)
```

## oromo: FINAL TEST report (sim=0.6, coverage=0.4)
```
                                               gate    n  dangerous_total  dangerous_unflagged  false_warnings  flag_rate  recall_of_dangerous recall_95ci
0                               baseline (show all)  100               27                   27               0       0.00                0.000   0.00-0.12
1                   layer 1 (target-language rules)  100               27                   22               2       0.07                0.185   0.08-0.37
2                        layer 2 (back-translation)  100               27                    5              23       0.45                0.815   0.63-0.92
3  layer 3 (units, conditions, key terms, coverage)  100               27                    6              31       0.52                0.778   0.59-0.89
4                                        layers 1+2  100               27                    5              23       0.45                0.815   0.63-0.92
5                                        all layers  100               27                    2              37       0.62                0.926   0.77-0.98
6            chrF-only gate (matched to all layers)  100               27                    2              46       0.71                0.926   0.77-0.98
```

## oromo: dangerous translations with the HIGHEST chrF (hero examples)
```
      id                                                    english                                                                           oromo_mt                                               oromo_back  oromo_chrf  gate_flagged                                                                             gate_reasons
13  S114                            Put 20 drops in a little water.                                      Bishaan xiqqoo keessa dhibbaa 20 galfachiisi.      Insert 20 percent of it in a small amount of water.   55.423106          True                                                unit lost: drop; low word coverage (0.25)
95  S196  Hold your breath for ten seconds after using the inhaler.  Inhaalatarricha erga fayyadamtee booda sa'aatii kudhaniif hafuura ofitti qabadhu.  Hold your breath for ten hours after using the inhaler.   54.333311         False                                                                                         
24  S125     Do not take this medicine if you have a stomach ulcer.                                          Yoo dhukkubsate qoricha kana hin fudhatu.             If he is ill, he will not take the medicine.   50.384924          True                                                                 meaning drift (sim 0.36)
51  S152                    Keep the medicine in a cool, dry place.                              Qoricha kana bakka ho'aafi ho'aa ta'e tokkotti kaa'i.                 Keep the medicine in a warm, warm place.   44.412301         False                                                                                         
2   S103                               Use three drops in each ear.                                    Gurraachoo sadii gurraachoo tokkotti fayyadami.                  Use three shades of black on one shade.   42.987137          True  number/frequency changed; unit lost: drop; key term lost: ear; meaning drift (sim 0.34)
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
