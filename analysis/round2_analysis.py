"""Round 2 analysis on the LOCKED thresholds. Nothing is re-tuned and nothing is re-translated.

Run from the repo root:  python analysis/round2_analysis.py
Writes to round2/: gate_features.csv, ci_results.md, rater_robustness.csv,
                   ablation.csv, category_recall.csv, examples.md, figures/tradeoff_curve.png
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import medtranslate_guard as mg

R2 = ROOT / "round2"
(R2 / "figures").mkdir(exist_ok=True)
T = json.load(open(ROOT / "locked_thresholds.json"))["thresholds"]   # {lang: [sim_t, cov_t]}
LANGS = ["amharic", "oromo"]

# ---------------------------------------------------------------- 0. features (rules + embedding similarity)
feat = pd.read_csv(R2 / "translations_rated.csv")
for lang in LANGS:
    feat = mg.add_features(feat, lang)
feat.to_csv(R2 / "gate_features.csv", index=False)
text_cols = [c for c in feat.columns if "_why" in c or c.endswith("_error_type")]
feat[text_cols] = feat[text_cols].fillna("")


def gate_layers(d, lang):
    f1, f2, f3 = mg.gate_flags(d, lang, *T[lang])
    return f1.to_numpy(), f2.to_numpy(), f3.to_numpy()


def matched_fw(chrf, bad, target_missed):
    """chrF-only baseline: flag the lowest-chrF sentences until it misses no more dangerous ones than the gate."""
    order = np.argsort(chrf, kind="stable")
    cum = np.concatenate([[0], np.cumsum(bad[order])])
    k = np.where(bad.sum() - cum <= target_missed)[0][0]
    return k, k - cum[k]                                   # flagged count, false warnings


def stats(chrf, bad, gate):
    missed = (bad & ~gate).sum()
    _, fw_chrf = matched_fw(chrf, bad, missed)
    fw_gate = (~bad & gate).sum()
    return dict(recall=(bad.sum() - missed) / bad.sum(), flag_gate=gate.mean(),
                fw_gate=fw_gate, fw_chrf=fw_chrf, diff=fw_chrf - fw_gate)


# ---------------------------------------------------------------- 1. confidence intervals, gate vs chrF-only
rng = np.random.default_rng(0)
B = 5000
cells = {}
for lang in LANGS:
    d = feat[feat[f"{lang}_rating"].notna() & feat[f"{lang}_chrf"].notna()].copy()
    gate = np.logical_or.reduce(gate_layers(d, lang))
    bad = (d[f"{lang}_rating"] == 2).to_numpy()
    chrf = d[f"{lang}_chrf"].to_numpy(float)
    p = stats(chrf, bad, gate)
    bt = pd.DataFrame([stats(chrf[i], bad[i], gate[i])
                       for i in (rng.integers(0, len(d), len(d)) for _ in range(B)) if bad[i].any()])
    ci = lambda c, f="{:.0f}": "{} to {}".format(*[f.format(x) for x in np.percentile(bt[c], [2.5, 97.5])])
    blind = mg.chrf_blindness(feat, lang)
    cells[lang] = {
        "Recall of dangerous": f"{p['recall']:.0%} (95% CI {ci('recall', '{:.0%}')})",
        "Sentences flagged": f"{p['flag_gate']:.0%} (95% CI {ci('flag_gate', '{:.0%}')})",
        "False warnings, gate": f"{p['fw_gate']} (95% CI {ci('fw_gate')})",
        "False warnings, chrF-only at same recall": f"{p['fw_chrf']} (95% CI {ci('fw_chrf')})",
        "Paired difference (chrF minus gate)": f"{p['diff']:+d} (95% CI {ci('diff', '{:+.0f}')}); "
                                              f"gate no worse in {(bt['diff'] >= 0).mean():.0%} of resamples",
        "chrF AUROC": f"{blind['auroc_low_chrF_detects_dangerous']} (95% CI {blind['auroc_95ci_bootstrap']})",
    }
lines = ["| | Amharic | Oromo |", "|---|---|---|"]
lines += [f"| {k} | {cells['amharic'][k]} | {cells['oromo'][k]} |" for k in cells["amharic"]]
(R2 / "ci_results.md").write_text("\n".join(lines))
print("\n".join(lines))

# ---------------------------------------------------------------- 2. rater robustness (Amharic)
rng = np.random.default_rng(1)
d = feat[feat["amharic_chrf"].notna()]
gate = np.logical_or.reduce(gate_layers(d, "amharic"))
chrf = d["amharic_chrf"].to_numpy(float)
rows = []
for name, col in {"worse-of (reported)": "amharic_rating", "rater 1 only": "amharic_rating_r1",
                  "rater 2 only": "amharic_rating_r2"}.items():
    ok = d[col].notna().to_numpy()
    g, c, b = gate[ok], chrf[ok], (d[col] == 2).to_numpy()[ok]
    p = stats(c, b, g)
    bt = pd.DataFrame([stats(c[i], b[i], g[i])
                       for i in (rng.integers(0, len(g), len(g)) for _ in range(3000)) if b[i].any()])
    q = lambda k: tuple(np.percentile(bt[k], [2.5, 97.5]).round(2))
    rows.append({"ratings": name, "n": int(ok.sum()), "dangerous": int(b.sum()), "recall": round(p["recall"], 2),
                 "recall_ci": q("recall"), "fw_gate": p["fw_gate"], "fw_chrf": p["fw_chrf"],
                 "diff_ci": q("diff"), "chrf_auroc": round(mg.auroc(-c, b), 2)})
rob = pd.DataFrame(rows)
rob.to_csv(R2 / "rater_robustness.csv", index=False)
print("\n", rob.to_string(index=False))

# ---------------------------------------------------------------- 3. layer ablation + trade-off curve
NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "once": 1, "twice": 2, "half": 0.5, "quarter": 0.25}
NEG = re.compile(r"\b(not|never|no|without|avoid|don't|do not|cannot|can't|stop)\b")


def nums(t):
    t = t.lower()
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)} | {v for w, v in NUMW.items() if re.search(rf"\b{w}\b", t)}


def trivial_flag(en, back):
    """Deliberately simple baseline: numbers or negation differ after the round trip. No thresholds."""
    return nums(en) != nums(back) or bool(NEG.search(en.lower())) != bool(NEG.search(back.lower()))


def chrf_curve(chrf, bad):
    order = np.argsort(chrf, kind="stable")
    caught = np.concatenate([[0], np.cumsum(bad[order])])
    return np.arange(len(chrf) + 1) / len(chrf), caught / bad.sum()


fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
ablation = []
for ax, lang in zip(axes, LANGS):
    d = feat[feat[f"{lang}_rating"].notna()].copy()
    bad = (d[f"{lang}_rating"] == 2).to_numpy()
    chrf = d[f"{lang}_chrf"].to_numpy(float)
    f1, f2, f3 = gate_layers(d, lang)
    triv = np.array([trivial_flag(e, b) for e, b in zip(d["english"], d[f"{lang}_back"])])
    pts = {"layer 1": f1, "layer 2": f2, "layer 3": f3, "all layers": f1 | f2 | f3, "trivial rule": triv}
    for name, f in pts.items():
        ablation.append({"language": lang, "gate": name, "flag_rate": round(f.mean(), 2),
                         "recall": round((bad & f).sum() / bad.sum(), 2), "missed": int((bad & ~f).sum()),
                         "false_warnings": int((~bad & f).sum())})
    x, y = chrf_curve(chrf, bad)
    ax.plot(x, y, color="gray", label="chrF-only (sweep)")
    ax.plot([0, 1], [0, 1], ":", color="lightgray", label="flag at random")
    for name, f in pts.items():
        ax.scatter(f.mean(), (bad & f).sum() / bad.sum(), s=90 if name == "all layers" else 35,
                   marker="*" if name == "all layers" else "o", zorder=3, label=name)
    ax.set(title=lang.capitalize(), xlabel="Share of sentences flagged", ylabel="Share of dangerous caught")
    ax.legend(fontsize=7, loc="lower right")
plt.tight_layout()
plt.savefig(R2 / "figures" / "tradeoff_curve.png", dpi=200)
pd.DataFrame(ablation).to_csv(R2 / "ablation.csv", index=False)
print("\n", pd.DataFrame(ablation).to_string(index=False))

# ---------------------------------------------------------------- 4. recall by category + examples
md = ["# Gate examples (Round 2, locked thresholds)",
      "First example per category in file order (not hand-picked).\n"]
cat_rows = []
for lang in LANGS:
    sim_t, cov_t = T[lang]
    d = feat[feat[f"{lang}_rating"].notna()].copy().reset_index(drop=True)
    d["flag"] = np.logical_or.reduce(gate_layers(d, lang))
    d["bad"] = d[f"{lang}_rating"] == 2

    def why(r):
        out = [str(r[f"{lang}_why{i}"]) for i in (1, 2, 3) if r[f"{lang}_why{i}"]]
        if r[f"{lang}_sim"] < sim_t:
            out.append(f"back-translation similarity {r[f'{lang}_sim']:.2f} < {sim_t}")
        if r[f"{lang}_cov"] < cov_t:
            out.append(f"key-word coverage {r[f'{lang}_cov']:.2f} < {cov_t}")
        return "; ".join(out) or "(no flag)"

    d["reason"] = d.apply(why, axis=1)
    t = d[d.bad].groupby("category").agg(dangerous=("flag", "size"), caught=("flag", "sum")).reset_index()
    t.insert(0, "language", lang)
    cat_rows.append(t)
    for status, mask in [("CAUGHT", d.bad & d.flag), ("MISSED", d.bad & ~d.flag)]:
        md.append(f"\n## {lang.capitalize()}: dangerous translations {status}\n")
        md.append("| id | category | English | Back-translation | Rater error type | Gate reason |\n|---|---|---|---|---|---|")
        for _, r in d[mask].groupby("category").head(1).iterrows():
            back = r[f"{lang}_back"]
            back = back if len(back) < 140 else back[:140] + " [...]"
            md.append(f"| {r['id']} | {r['category']} | {r['english']} | {back} | "
                      f"{r[f'{lang}_error_type']} | {r['reason']} |")
pd.concat(cat_rows).to_csv(R2 / "category_recall.csv", index=False)
(R2 / "examples.md").write_text("\n".join(md))
print("\nDone. Outputs written to", R2)
