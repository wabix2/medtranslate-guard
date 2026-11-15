"""Evaluate the learned classifier ONCE on held-out Round 2.

The model was trained on Round 1 only and its threshold was chosen on Round 1 cross-validation, so Round 2
is unseen by it. Nothing is retrained or re-tuned here. Whatever the result is, report it.

Run from the repo root (needs scikit-learn==1.6.1, sentence-transformers, sacrebleu; the first run downloads
LaBSE, about 1.9 GB; a GPU is not required):
    python analysis/ml_round2_eval.py

Needs round2/gate_features.csv (from analysis/round2_analysis.py) to compare against the rule gate.
Writes round2/ml_predictions.csv and round2/ml_results.md
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ml_classifier as ml

R2 = ROOT / "round2"
LANGS = ["amharic", "oromo"]
T = json.load(open(ROOT / "locked_thresholds.json"))["thresholds"]    # rule-gate thresholds: [sim_t, cov_t]
B = 5000


def auroc(scores, labels):
    s, y = np.asarray(scores, float), np.asarray(labels, bool)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum())
                 / (len(pos) * len(neg)))


def matched_fw(chrf, bad, target_missed):
    """chrF-only baseline: flag the lowest-chrF sentences until it misses no more dangerous ones than target."""
    order = np.argsort(chrf, kind="stable")
    cum = np.concatenate([[0], np.cumsum(bad[order])])
    k = np.where(bad.sum() - cum <= target_missed)[0][0]
    return k - cum[k]                                                   # false warnings


def rule_gate_flags(gf, lang):
    """Same definition as the rule gate elsewhere in the repo: layer 1 OR 2 OR 3 with the locked thresholds."""
    sim_t, cov_t = T[lang]
    f1 = gf[f"{lang}_f1"].astype(bool)
    f2 = gf[f"{lang}_f2r"].astype(bool) | (gf[f"{lang}_sim"] < sim_t)
    f3 = gf[f"{lang}_f3r"].astype(bool) | (gf[f"{lang}_cov"] < cov_t)
    return f1 | f2 | f3


def stats(bad, ml_flag, gate, proba, chrf):
    missed_ml = (bad & ~ml_flag).sum()
    fw_chrf = matched_fw(chrf, bad, missed_ml)
    fw_ml = (~bad & ml_flag).sum()
    a_ml, a_chrf = auroc(proba, bad), auroc(-chrf, bad)
    return dict(ml_recall=(bad.sum() - missed_ml) / bad.sum(), ml_flag_rate=ml_flag.mean(), ml_fw=fw_ml,
                gate_recall=(bad & gate).sum() / bad.sum(), gate_flag_rate=gate.mean(), gate_fw=(~bad & gate).sum(),
                chrf_fw=fw_chrf, chrf_minus_ml=fw_chrf - fw_ml,
                auroc_ml=a_ml, auroc_chrf=a_chrf, auroc_diff=a_ml - a_chrf)


def main():
    raw = pd.read_csv(R2 / "translations_rated.csv")
    gate_feat = pd.read_csv(R2 / "gate_features.csv").set_index("id")
    pkg = ml.load_package()
    print("Model:", pkg["model_type"], "| locked threshold:", round(pkg["threshold"], 4))

    rng = np.random.default_rng(0)
    preds, cells = [], {}
    for lang in LANGS:
        d = raw[raw[f"{lang}_rating"].notna() & raw[f"{lang}_chrf"].notna()].copy()
        if lang == "oromo" and "oromo_core" in d:
            d = d[d["oromo_core"].isin(["Y", "N"])]
        inp = pd.DataFrame({"id": d["id"].values, "language": lang, "english": d["english"].values,
                            "machine_translation": d[f"{lang}_mt"].values,
                            "back_translation": d[f"{lang}_back"].values})
        out = ml.predict_df(inp)
        out["rating"] = d[f"{lang}_rating"].values
        out["chrf"] = d[f"{lang}_chrf"].values
        out["gate_flag"] = rule_gate_flags(gate_feat.loc[out["id"]], lang).to_numpy()
        preds.append(out)

        bad = (out["rating"] == 2).to_numpy()
        mlf, gate = out["ml_flag"].to_numpy(), out["gate_flag"].to_numpy()
        p, chrf = out["ml_proba"].to_numpy(), out["chrf"].to_numpy(float)
        pt = stats(bad, mlf, gate, p, chrf)
        bt = []
        for _ in range(B):
            i = rng.integers(0, len(out), len(out))
            if bad[i].any() and (~bad[i]).any():
                bt.append(stats(bad[i], mlf[i], gate[i], p[i], chrf[i]))
        bt = pd.DataFrame(bt)
        ci = lambda c, f: "{} to {}".format(*[f.format(x) for x in np.nanpercentile(bt[c], [2.5, 97.5])])
        n_bad = int(bad.sum())
        cells[lang] = {
            "Dangerous translations": f"{n_bad} / {len(out)}",
            "Learned model: recall of dangerous": f"{pt['ml_recall']:.0%} (95% CI {ci('ml_recall', '{:.0%}')})",
            "Learned model: sentences flagged": f"{pt['ml_flag_rate']:.0%} (95% CI {ci('ml_flag_rate', '{:.0%}')})",
            "Learned model: false warnings": f"{pt['ml_fw']} (95% CI {ci('ml_fw', '{:.0f}')})",
            "Rule gate (for reference): recall / flagged / false warnings":
                f"{pt['gate_recall']:.0%} / {pt['gate_flag_rate']:.0%} / {pt['gate_fw']}",
            "chrF-only at the learned model's recall: false warnings": f"{pt['chrf_fw']} (95% CI {ci('chrf_fw', '{:.0f}')})",
            "chrF-only minus learned model (paired)": f"{pt['chrf_minus_ml']:+d} (95% CI {ci('chrf_minus_ml', '{:+.0f}')})",
            "AUROC, learned model probability": f"{pt['auroc_ml']:.2f} (95% CI {ci('auroc_ml', '{:.2f}')})",
            "AUROC, chrF": f"{pt['auroc_chrf']:.2f} (95% CI {ci('auroc_chrf', '{:.2f}')})",
            "AUROC difference, learned minus chrF (paired)": f"{pt['auroc_diff']:+.2f} (95% CI {ci('auroc_diff', '{:+.2f}')})",
        }

    pd.concat(preds).to_csv(R2 / "ml_predictions.csv", index=False)
    lines = [f"Learned model, Round 2 held out. Threshold locked at {pkg['threshold']:.4f} (chosen on Round 1 CV).\n",
             "| | Amharic | Oromo |", "|---|---|---|"]
    lines += [f"| {k} | {cells['amharic'][k]} | {cells['oromo'][k]} |" for k in cells["amharic"]]
    (R2 / "ml_results.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
