# Can We Trust Machine Translation of Medicine Instructions? (Amharic + Afaan Oromo)

Veritas AI International High School Hackathon 2026, AI + Languages track.

> **This project is a prototype and is not medical advice.** "No red flag" never means "safe".
> Always confirm medicine instructions with a pharmacist or health worker.

## Question
1. Does the standard automatic score (chrF) tell us whether a machine translation of a medicine instruction is safe?
2. Can simple, explainable automatic checks warn a user before they rely on a dangerous translation?

## What we did
- 200 short English medicine instructions in two rounds (S01-S100, S101-S200), four categories:
  frequency/duration, negation/warnings, quantity, route/condition.
- Translated with NLLB-200 distilled 600M (4 beams) into Amharic (200) and Afaan Oromo (150), then translated back to English.
- Human reference translations, sentence-level chrF.
- Blind safety ratings (0 safe, 1 confusing, 2 dangerous). Two independent Amharic raters (worse rating used), one Oromo rater.
- A three-layer rule-based safety gate with human-readable reasons. Thresholds were chosen on Round 1 only,
  locked in `locked_thresholds.json`, and Round 2 was scored once.

## Headline results (Round 2, held out)
| | Amharic | Oromo |
|---|---|---|
| Dangerous translations | 31 / 100 | 27 / 100 |
| Caught by gate | 25 (81%) | 25 (93%) |
| False warnings | 30 | 37 |
| Sentences flagged | 55% | 62% |
| chrF-only at same recall: false warnings | 36 | 46 |

chrF carries a moderate safety signal (AUROC about 0.7-0.77) but is too weak alone.
The gate beats chrF-only only slightly on false warnings. See the write-up for limitations.

## Files
- `medtranslate_guard.py` - the whole pipeline (translate, score, rating sheets, stats, gate, figures)
- `sentences.csv`, `round2/sentences.csv` - source sentences and references
- `rating_sheets/`, `round2/rating_sheets/` - blind rating sheets (rated)
- `translations_scored.csv`, `round2/translations_scored.csv` - machine translations and chrF
- `locked_thresholds.json`, `provenance.json` - lock file and run provenance
- `results_summary.md`, `figures/`, `round2/figures/` - results

## Run
Open the script in Colab (GPU helps), put the CSV files next to it, and run it. It resumes from where you are.
For one-off checks use `check_instruction("Take one tablet every other day.", lang="amharic")`.

## Limitations
Deliberately hard test set (not real-world rates); Oromo has a single rater who is also a team member;
Amharic rater agreement dropped in Round 2; back-translation uses the same model; no real patient data.
