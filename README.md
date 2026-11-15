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
  locked in `locked_thresholds.json`, and Round 2 was scored once. No rule or threshold was changed after Round 1.

## Headline results (Round 2, held out)
| | Amharic | Oromo |
|---|---|---|
| Dangerous translations | 31 / 100 | 27 / 100 |
| Caught by gate | 25 (81%) | 25 (93%) |
| False warnings | 30 | 37 |
| Sentences flagged | 55% | 62% |
| chrF-only at same recall: false warnings | 36 | 46 |

chrF carries a moderate safety signal (AUROC about 0.70-0.77) but is too weak alone.
The gate beats chrF-only only slightly on false warnings. See `docs/ONE_PAGE_WRITEUP.pdf` and
`docs/FULL_REPORT.pdf` for details and limitations.

## Files
- `medtranslate_guard.py` - the whole pipeline (translate, score, rating sheets, stats, gate, figures)
- **Round 1 (repo root):** `sentences.csv`, `translations_scored.csv`, `translations_rated.csv`,
  `rating_sheets/`, `figures/`, `results_summary.md`, `provenance.json`
- `locked_thresholds.json` - thresholds locked on 2026-11-14 (shared by both rounds)
- **Round 2 (`round2/`):** `sentences.csv`, `translations_scored.csv`, `translations_rated.csv`,
  `rating_sheets/`, `figures/`, `results_summary.md`, `provenance.json`
- `docs/` - one-page write-up and full report

## Run
Open the script in Colab (a GPU helps), put the data files next to it, and run it. It resumes from where you are.
For one-off checks:

```python
import medtranslate_guard as mg
mg.check_instruction("Take one lozenge every two hours.", lang="amharic")
```

To re-score Round 2 from the saved translations and ratings (thresholds stay locked):

```python
import medtranslate_guard as mg
R2 = "round2"
mg.SENTENCES_FILE = f"{R2}/sentences.csv"
mg.SCORED_FILE    = f"{R2}/translations_scored.csv"
mg.RATED_FILE     = f"{R2}/translations_rated.csv"
mg.SHEET_DIR      = f"{R2}/rating_sheets"
mg.FIG_DIR        = f"{R2}/figures"
mg.PROVENANCE_FILE= f"{R2}/provenance.json"
mg.SUMMARY_FILE   = f"{R2}/results_summary.md"
mg.RETEST_N = 0
_orig = mg.add_chrf
mg.add_chrf = lambda df, verbose=False: _orig(df, verbose=False)
mg.main()
```

## Credits
NLLB-200 distilled 600M (Meta AI), sentence-transformers `all-MiniLM-L6-v2`, sacreBLEU (chrF), scikit-learn.
All sentences, reference translations and safety ratings were created by our team. No external datasets and no real patient data.

## Limitations
Deliberately hard test set (not real-world rates); Oromo has a single rater I rate it alone and also am a team member;
Amharic rater agreement dropped in Round 2 (weighted kappa 0.41 vs 0.73); back-translation uses the same model.
