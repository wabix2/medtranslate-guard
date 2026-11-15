# -*- coding: utf-8 -*-
"""
Can we trust machine translation of medicine instructions?  (Amharic + Afaan Oromo)
Veritas AI International High School Hackathon 2026 - AI + Languages track

THIS PROJECT IS A PROTOTYPE AND IS NOT MEDICAL ADVICE.

Pipeline (re-run this one script after each stage; it figures out where you are):
  1. translate + chrF       -> translations_scored.csv      (never overwritten once it exists)
  2. blind rating sheets    -> rating_sheets/*.csv          (one file per rater, shuffled, no chrF,
                                                             no back-translation, no references)
  3. after rating           -> merge, rater agreement, "is chrF blind to danger?" stats,
                               dev sweep for gate thresholds
  4. set THRESHOLDS below   -> thresholds are LOCKED, test set is scored once,
                               figures + results_summary.md are written
"""
import os, re, sys, json, hashlib, subprocess, datetime, platform
import numpy as np
import pandas as pd

try:
    import sacrebleu, sentence_transformers, sklearn, matplotlib  # noqa: F401
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "sacrebleu",
                    "sentence-transformers", "matplotlib", "scikit-learn"])

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
SENTENCES_FILE = "sentences.csv"          # id, english, category, split, oromo_core, amharic_ref, oromo_ref
SCORED_FILE = "translations_scored.csv"
RATED_FILE = "translations_rated.csv"
SHEET_DIR = "rating_sheets"
FIG_DIR = "figures"
LOCK_FILE = "locked_thresholds.json"
PROVENANCE_FILE = "provenance.json"
SUMMARY_FILE = "results_summary.md"
MODEL = "facebook/nllb-200-distilled-600M"
CODES = {"amharic": "amh_Ethi", "oromo": "gaz_Latn"}
SEED = 42
RETEST_N = 15                              # Oromo sentences re-rated later (self-consistency)
DISCLAIMER = "This project is a prototype and is not medical advice."
ERROR_TYPES = ["number", "unit", "negation", "condition", "timing", "wrong_word",
               "hallucination", "omission", "other"]

# Chosen on the DEV split only and locked in locked_thresholds.json on 2026-11-14.
# Changing these now is blocked by lock_thresholds().
THRESHOLDS = {"amharic": (0.6, 0.7), "oromo": (0.6, 0.4)}      # (sim_threshold, coverage_threshold)


# ----------------------------------------------------------------------------
# DATA HELPERS
# ----------------------------------------------------------------------------
def lang_rows(df, lang):
    if lang == "oromo":
        return df["oromo_core"].isin(["Y", "N"])
    return pd.Series(True, index=df.index)


def load_sentences():
    df = pd.read_csv(SENTENCES_FILE, keep_default_na=False, dtype=str)
    df = df.loc[:, [c for c in df.columns if not c.startswith("Unnamed")]]
    for col in ["amharic_ref", "oromo_ref"]:
        if col not in df.columns:
            df[col] = ""
    return df


def check_references(df):
    missing_am = int((df["amharic_ref"].str.strip() == "").sum())
    rows = lang_rows(df, "oromo")
    missing_om = int((df.loc[rows, "oromo_ref"].str.strip() == "").sum())
    if missing_am or missing_om:
        raise ValueError(f"Write all references before translating. Missing Amharic: {missing_am}, missing Oromo: {missing_om}")


_CACHE = {}


def get_model():
    if "model" not in _CACHE:
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tok = AutoTokenizer.from_pretrained(MODEL)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL).to(device)
        try:                                   # silences the max_length / max_new_tokens warning
            model.generation_config.max_length = None
        except Exception:
            pass
        _CACHE["model"] = (tok, model, device)
    return _CACHE["model"]


def get_emb():
    if "emb" not in _CACHE:
        from sentence_transformers import SentenceTransformer
        _CACHE["emb"] = SentenceTransformer("all-MiniLM-L6-v2")
    return _CACHE["emb"]


def translate(texts, src, tgt, batch=16):
    tok, model, device = get_model()
    tok.src_lang = src
    out = []
    for i in range(0, len(texts), batch):
        enc = tok(texts[i:i + batch], return_tensors="pt", padding=True).to(device)
        gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(tgt),
                             max_new_tokens=128, num_beams=4)
        out += tok.batch_decode(gen, skip_special_tokens=True)
    return out


# ----------------------------------------------------------------------------
# chrF (with punctuation normalised so "." vs the Amharic full stop "።" cannot move the score)
# ----------------------------------------------------------------------------
def norm_chrf(text):
    t = str(text).replace("።", ".").replace("፣", ",").replace("፤", ";").replace("፧", "?").replace("፡", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"[.!?]+$", "", t).strip()


def add_chrf(df, verbose=True):
    import sacrebleu
    for name in CODES:
        rows = lang_rows(df, name)
        hyp = df.loc[rows, f"{name}_mt"].map(norm_chrf).tolist()
        ref = df.loc[rows, f"{name}_ref"].map(norm_chrf).tolist()
        df[f"{name}_chrf"] = np.nan
        df.loc[rows, f"{name}_chrf"] = [sacrebleu.sentence_chrf(h, [r]).score for h, r in zip(hyp, ref)]
        if verbose:
            for part in ["dev", "test"]:
                m = rows & (df["split"] == part)
                score = sacrebleu.corpus_chrf(df.loc[m, f"{name}_mt"].map(norm_chrf).tolist(),
                                              [df.loc[m, f"{name}_ref"].map(norm_chrf).tolist()]).score
                print(name, part, "chrF:", round(score, 2))
    return df


def run_translation(force=False):
    if os.path.exists(SCORED_FILE) and not force:
        raise FileExistsError(f"{SCORED_FILE} exists. Not re-translating (raters may already be using it).")
    df = load_sentences()
    check_references(df)
    for name, code in CODES.items():
        rows = lang_rows(df, name)
        mt = translate(df.loc[rows, "english"].tolist(), "eng_Latn", code)
        back = translate(mt, code, "eng_Latn")
        df[f"{name}_mt"] = ""
        df[f"{name}_back"] = ""
        df.loc[rows, f"{name}_mt"] = mt
        df.loc[rows, f"{name}_back"] = back
    df = add_chrf(df)
    df.to_csv(SCORED_FILE, index=False)
    return df


def write_provenance(df):
    if os.path.exists(PROVENANCE_FILE):
        return
    refs = "\n".join(df["amharic_ref"].tolist() + df["oromo_ref"].tolist())
    info = {"model": MODEL, "num_beams": 4, "max_new_tokens": 128, "seed": SEED,
            "refs_sha256": hashlib.sha256(refs.encode("utf-8")).hexdigest(),
            "refs_hash_note": "computed from the references stored in translations_scored.csv",
            "scored_file_modified_utc": datetime.datetime.fromtimestamp(
                os.path.getmtime(SCORED_FILE), datetime.timezone.utc).isoformat(),
            "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "python": platform.python_version()}
    for lib in ["torch", "transformers", "sacrebleu", "sentence_transformers", "sklearn", "pandas"]:
        try:
            info[lib] = __import__(lib).__version__
        except Exception:
            pass
    with open(PROVENANCE_FILE, "w") as f:
        json.dump(info, f, indent=2)


# ----------------------------------------------------------------------------
# BLIND RATING SHEETS  (one file per rater: English + translation only, shuffled)
# ----------------------------------------------------------------------------
RATER_README = f"""RATING INSTRUCTIONS  (read fully before you start)

You see an English medicine instruction and a machine translation. You do NOT see the
reference translation, any score, or any back-translation. Rate ONLY the translation.
Do not discuss ratings with the other rater until BOTH of you have finished.

rating column (type 0, 1 or 2):
  0 = SAFE      a patient would do the right thing
  1 = CONFUSING awkward or unclear, but the meaning is NOT wrong
  2 = DANGEROUS wrong number, unit, drug, timing or condition, OR a lost "do not" / "stop"

error_type column (only needed for 1 and 2) - choose one of:
  {", ".join(ERROR_TYPES)}

note column: free text (e.g. a correct loanword or synonym that you think a metric would punish).

{DISCLAIMER}
"""


def make_rating_sheets():
    df = pd.read_csv(SCORED_FILE, keep_default_na=False, dtype=str)
    os.makedirs(SHEET_DIR, exist_ok=True)
    with open(os.path.join(SHEET_DIR, "README_for_raters.txt"), "w", encoding="utf-8") as f:
        f.write(RATER_README)

    def sheet(path, lang, seed, ids=None):
        if os.path.exists(path):
            return
        d = df[lang_rows(df, lang)]
        if ids is not None:
            d = d[d["id"].isin(ids)]
        d = d.sample(frac=1, random_state=seed)
        out = d[["id", "english", f"{lang}_mt"]].copy()
        out["rating"] = ""
        out["error_type"] = ""
        out["note"] = ""
        out.to_csv(path, index=False, encoding="utf-8-sig")
        print("created", path)

    sheet(os.path.join(SHEET_DIR, "amharic_rater1.csv"), "amharic", SEED + 1)
    sheet(os.path.join(SHEET_DIR, "amharic_rater2.csv"), "amharic", SEED + 2)
    sheet(os.path.join(SHEET_DIR, "oromo_rater.csv"), "oromo", SEED + 3)
    oro_ids = df.loc[lang_rows(df, "oromo"), "id"]
    retest_ids = set(oro_ids.sample(n=min(RETEST_N, len(oro_ids)), random_state=SEED).tolist())
    sheet(os.path.join(SHEET_DIR, "oromo_retest.csv"), "oromo", SEED + 4, ids=retest_ids)


def _read_rating(path, col, err_col):
    if not os.path.exists(path):
        return None
    s = pd.read_csv(path, keep_default_na=False, dtype=str)
    raw = s["rating"].str.strip()
    val = pd.to_numeric(raw, errors="coerce")
    bad = raw.ne("") & ~val.isin([0, 1, 2])
    if bad.any():
        raise ValueError(f"{path}: rating must be 0, 1 or 2. Fix ids: {s.loc[bad, 'id'].tolist()}")
    return pd.DataFrame({"id": s["id"], col: val, err_col: s["error_type"].str.strip().str.lower()})


def load_rated():
    df = pd.read_csv(SCORED_FILE, keep_default_na=False, dtype=str)
    for col in ["amharic_chrf", "oromo_chrf"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    sheets = [("amharic_rater1.csv", "amharic_rating_r1", "amharic_err_r1"),
              ("amharic_rater2.csv", "amharic_rating_r2", "amharic_err_r2"),
              ("oromo_rater.csv", "oromo_rating", "oromo_err"),
              ("oromo_retest.csv", "oromo_rating_retest", "oromo_err_retest")]
    for fname, col, err in sheets:
        r = _read_rating(os.path.join(SHEET_DIR, fname), col, err)
        if r is None:
            df[col], df[err] = np.nan, ""
        else:
            df = df.merge(r, on="id", how="left")
            df[err] = df[err].fillna("")
    df["amharic_rating"] = df[["amharic_rating_r1", "amharic_rating_r2"]].max(axis=1)   # conservative: worst of two raters
    pick1 = df["amharic_rating_r1"].fillna(-1) >= df["amharic_rating_r2"].fillna(-1)
    df["amharic_error_type"] = np.where(pick1, df["amharic_err_r1"], df["amharic_err_r2"])
    df["oromo_error_type"] = df["oromo_err"]
    df.to_csv(RATED_FILE, index=False)
    return df


def rating_progress(df):
    out = {"amharic r1": (df["amharic_rating_r1"].notna().sum(), len(df)),
           "amharic r2": (df["amharic_rating_r2"].notna().sum(), len(df)),
           "oromo": (df["oromo_rating"].notna().sum(), int(lang_rows(df, "oromo").sum())),
           "oromo retest": (df["oromo_rating_retest"].notna().sum(), RETEST_N)}
    return {k: f"{a}/{b}" for k, (a, b) in out.items()}


def amharic_agreement(df):
    from sklearn.metrics import cohen_kappa_score
    d = df.dropna(subset=["amharic_rating_r1", "amharic_rating_r2"])
    if len(d) < 2:
        return {"n": len(d)}
    a, b = d["amharic_rating_r1"].astype(int), d["amharic_rating_r2"].astype(int)
    def kap(w):
        try:
            return round(float(cohen_kappa_score(a, b, weights=w)), 3)
        except Exception:
            return float("nan")
    return {"n": len(d), "exact_agreement": round(float((a == b).mean()), 3),
            "kappa": kap(None), "weighted_kappa": kap("linear"),
            "safe_vs_dangerous_disagreements(0 vs 2)": int(((a - b).abs() == 2).sum())}


def oromo_consistency(df):
    from sklearn.metrics import cohen_kappa_score
    d = df.dropna(subset=["oromo_rating", "oromo_rating_retest"])
    if len(d) < 2:
        return {"n": len(d)}
    a, b = d["oromo_rating"].astype(int), d["oromo_rating_retest"].astype(int)
    try:
        k = round(float(cohen_kappa_score(a, b, weights="linear")), 3)
    except Exception:
        k = float("nan")
    return {"n": len(d), "same_rating_both_times": round(float((a == b).mean()), 3), "weighted_kappa": k}


# ----------------------------------------------------------------------------
# GATE RULES  (each rule returns human-readable reasons, so every warning is explainable)
# ----------------------------------------------------------------------------
WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
         "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fourteen": "14"}
# "stop" is deliberately NOT a negation: "Do not stop" must differ from "Stop".
NEG_EN = re.compile(r"\b(?:not|never|no|don't|won't|cannot|can't)\b|n't\b", re.I)
COND_GROUPS = {"if/when": r"\b(?:if|when|unless|whenever)\b", "only": r"\b(?:only|just|solely)\b", "before": r"\bbefore\b",
               "after": r"\bafter\b", "until": r"\buntil\b", "while/during": r"\b(?:while|during)\b"}
GEEZ = dict(zip("፩፪፫፬፭፮፯፰፱፲", range(1, 11)))
AM_NEG_PREFIX = ("አይ", "አት", "አያ", "አል")      # አይ-ውሰዱ, አት-ውሰድ, አያ-ቁሙ, አል-ወሰደም
AM_NEG_EXCEPT = {"አይን", "አይኖች", "አይነት", "አይነቶች", "አልኮል", "አልኮሆል", "አትክልት", "አትክልቶች", "አልጋ", "አያት"}
HALF_TARGET = {"amharic": ["ግማሽ", "ተኩል"], "oromo": ["walakkaa"]}
NUM_WORDS = {
    "amharic": {"አንድ": "1", "ሁለት": "2", "ሶስት": "3", "ሦስት": "3", "አራት": "4", "አምስት": "5", "ስድስት": "6",
                "ሰባት": "7", "ስምንት": "8", "ዘጠኝ": "9", "አስር": "10", "አሥር": "10"},
    "oromo": {"tokko": "1", "lama": "2", "sadii": "3", "afur": "4", "shan": "5", "jaha": "6", "torba": "7",
              "saddeet": "8", "sagal": "9", "kudhan": "10"},
}
STOP = set("a an the of to in on at with and or for your you this that it is are be as if when my his her".split())
SYN = {"pill": "tablet", "pills": "tablet", "medication": "medicine", "medicines": "medicine", "drug": "medicine",
       "drugs": "medicine", "millilitre": "ml", "millilitres": "ml", "milliliter": "ml", "milliliters": "ml",
       "milligram": "mg", "milligrams": "mg", "litre": "liter", "litres": "liter", "liters": "liter",
       "daily": "day", "weekly": "week", "monthly": "month", "droplet": "drop", "droplets": "drop"}
# High-stakes words: if one is in the English source it must survive the round trip (catches "rash" -> "stroke").
KEY_TERMS = {
    "rash": r"rash", "fever": r"fever|temperature", "pain": r"pain|ache", "dizzy": r"dizz\w*|vertigo",
    "breathing": r"breath\w*", "allergy": r"allerg\w*", "pregnancy": r"pregnan\w*", "kidney": r"kidney\w*",
    "alcohol": r"alcohol", "empty stomach": r"empty stomach|fasting", "food": r"food|meals?|eat\w*",
    "left": r"left", "right": r"right", "eye": r"eyes?", "ear": r"ears?", "mouth": r"mouth|oral\w*",
    "skin": r"skin", "swallow": r"swallow\w*", "crush": r"crush\w*", "chew": r"chew\w*",
    "dissolve": r"dissolv\w*", "shake": r"shake", "tongue": r"tongue", "bedtime": r"bedtime|bed|sleep\w*|night",
    "morning": r"morning", "evening": r"evening|night", "baby": r"baby|babies|infants?",
    "child": r"child|children|kids?", "adult": r"adults?",
}
UNIT_WORDS = ["ml", "mg", "tablet", "capsule", "drop", "teaspoon", "tablespoon", "spoon", "sachet", "liter",
              "hour", "minute", "day", "week", "month"]
ART_UNITS = (r"(?:tablet|capsule|drop|teaspoon|tablespoon|spoonful|spoon|sachet|puff|ml|mg|pill|dose|"
             r"hour|week|month|minute)")


def _clean(text):
    return str(text).replace("’", "'").replace("‘", "'")


def _freq(m):
    unit = m.group(2) or {"daily": "day", "weekly": "week", "monthly": "month"}[m.group(3)]
    return f" frq{m.group(1)}/{unit} "


def quantities(text):
    """Numbers, 'half', and canonical frequencies (twice a day == twice daily; every other day != every day)."""
    t = _clean(text).lower()
    t = re.sub(r"\bat once\b", "together", t)
    t = re.sub(r"\bevery other day\b", " frqeod ", t)
    for w, d in WORDS.items():
        t = re.sub(rf"\b{w}\b", d, t)
    t = re.sub(r"\btwice\b", "2 times", t)
    t = re.sub(r"\bthrice\b", "3 times", t)
    t = re.sub(r"\bonce\b", "1 times", t)
    t = re.sub(r"(\d+)\s*times?\s*(?:(?:a|per|each|every)\s+(day|week|month)\b|(daily|weekly|monthly)\b)", _freq, t)
    t = re.sub(r"\b(?:every|each|per)\s+(day|week|month)\b", lambda m: f" frq1/{m.group(1)} ", t)
    t = re.sub(r"\b(daily|weekly|monthly)\b", lambda m: f" frq1/{SYN[m.group(1)]} ", t)
    t = re.sub(r"\ba\s+day\b", " frq1/day ", t)
    t = re.sub(rf"\b(?:a|an)\s+(?={ART_UNITS}s?\b)", "1 ", t)
    return sorted(re.findall(r"frq\d+/[a-z]+|frqeod|\d+(?:\.\d+)?|half|quarter|hundred|thousand|million", t))


def _is_number(q):
    return re.fullmatch(r"\d+(?:\.\d+)?", q) is not None


def target_numbers(text, lang):
    t = "".join(str(GEEZ[c]) if c in GEEZ else c for c in str(text))
    nums = set(re.findall(r"\d+(?:\.\d+)?", t))
    low = t.lower().replace("torban", "") if lang == "oromo" else t
    for w, d in NUM_WORDS[lang].items():
        if w in low:
            nums.add(d)
    return nums


def has_neg_target(text, lang):
    if lang == "oromo":
        return re.search(r"\bhin\b", str(text), re.I) is not None
    toks = re.findall(r"[\u1200-\u137F]+", str(text))
    return any(tok.startswith(AM_NEG_PREFIX) and tok not in AM_NEG_EXCEPT for tok in toks)


def repeats(text):
    w = str(text).split()
    return len(w) > 6 and len(set(w)) / len(w) < 0.5


def stem(word):
    word = SYN.get(word, word)
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return SYN.get(word, word)


def token_set(text):
    return {stem(w) for w in re.findall(r"[a-z]+", _clean(text).lower()) if w not in STOP}


def layer1_reasons(english, mt, lang):
    """Checks on the target-language text itself (no back-translation)."""
    if not str(mt).strip():
        return ["empty output"]
    r = []
    if repeats(mt):
        r.append("repetition loop")
    qs = quantities(english)
    need = [q for q in qs if _is_number(q) and q != "1"]      # a bare "1" is often implicit in singular forms
    have = target_numbers(mt, lang)
    if any(q not in have for q in need):
        r.append("number missing")
    if "half" in qs and not any(h in str(mt).lower() for h in HALF_TARGET[lang]):
        r.append("'half' missing")
    if NEG_EN.search(_clean(english)) and not has_neg_target(mt, lang):
        r.append("negation missing")
    return r


def layer2_rule_reasons(english, back):
    """Exact matching after translating back to English."""
    r = []
    if quantities(english) != quantities(back):
        r.append("number/frequency changed")
    if bool(NEG_EN.search(_clean(english))) != bool(NEG_EN.search(_clean(back))):
        r.append("negation changed")
    return r


def layer3_rule_reasons(english, back):
    """Units, durations, conditions and high-stakes key words that must survive the round trip."""
    s, b = token_set(english), token_set(back)
    r = []
    lost = [u for u in UNIT_WORDS if u in s and u not in b]
    if lost:
        r.append("unit lost: " + "/".join(lost))
    e, k = _clean(english).lower(), _clean(back).lower()
    cl = [g for g, p in COND_GROUPS.items() if re.search(p, e) and not re.search(p, k)]
    if cl:
        r.append("condition lost: " + "/".join(cl))
    kt = [g for g, p in KEY_TERMS.items() if re.search(rf"\b(?:{p})\b", e) and not re.search(rf"\b(?:{p})\b", k)]
    if kt:
        r.append("key term lost: " + "/".join(kt))
    return r


def row_gate(english, mt, back, lang):
    why1 = layer1_reasons(english, mt, lang)
    why2 = layer2_rule_reasons(english, back)
    why3 = layer3_rule_reasons(english, back)
    s, b = token_set(english), token_set(back)
    cov = len(s & b) / len(s) if s else 1.0
    return {"f1": bool(why1), "why1": "; ".join(why1), "f2r": bool(why2), "why2": "; ".join(why2),
            "f3r": bool(why3), "why3": "; ".join(why3), "cov": cov}


def add_features(df, lang):
    """Compute every rule once per sentence; thresholds are applied later (fast sweeps)."""
    df = df.copy()
    rows = lang_rows(df, lang)
    for c in ["f1", "f2r", "f3r"]:
        df[f"{lang}_{c}"] = False
    for c in ["why1", "why2", "why3"]:
        df[f"{lang}_{c}"] = ""
    df[f"{lang}_cov"] = np.nan
    df[f"{lang}_sim"] = np.nan
    d = df[rows]
    if len(d) == 0:
        return df
    feats = [row_gate(r["english"], r[f"{lang}_mt"], r[f"{lang}_back"], lang) for _, r in d.iterrows()]
    for k in feats[0]:
        df.loc[rows, f"{lang}_{k}"] = [f[k] for f in feats]
    emb = get_emb()
    a = emb.encode(d["english"].tolist(), normalize_embeddings=True)
    b = emb.encode(d[f"{lang}_back"].tolist(), normalize_embeddings=True)
    df.loc[rows, f"{lang}_sim"] = (a * b).sum(axis=1)
    for c in ["f1", "f2r", "f3r"]:
        df[f"{lang}_{c}"] = df[f"{lang}_{c}"].astype(bool)
    return df


def gate_flags(d, lang, sim_t, cov_t):
    f1 = d[f"{lang}_f1"]
    f2 = d[f"{lang}_f2r"] | (d[f"{lang}_sim"] < sim_t)
    f3 = d[f"{lang}_f3r"] | (d[f"{lang}_cov"] < cov_t)
    return f1, f2, f3


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def chrf_matched_flags(d, lang, bad, target_unflagged):
    """Fair baseline: block the lowest-chrF sentences until chrF misses no more dangerous ones than our gate."""
    order = d[f"{lang}_chrf"].rank(method="first").astype(int)
    for k in range(len(d) + 1):
        flagged = order <= k
        if int((bad & ~flagged).sum()) <= target_unflagged:
            return flagged
    return flagged


def _row(name, d, bad, f):
    n_bad = int(bad.sum())
    missed = int((bad & ~f).sum())
    lo, hi = wilson(n_bad - missed, n_bad)
    return {"gate": name, "n": len(d), "dangerous_total": n_bad, "dangerous_unflagged": missed,
            "false_warnings": int((~bad & f).sum()), "flag_rate": round(float(f.mean()), 3),
            "recall_of_dangerous": round((n_bad - missed) / n_bad, 3) if n_bad else np.nan,
            "recall_95ci": f"{lo:.2f}-{hi:.2f}" if n_bad else ""}


def gate_table(d, lang, sim_t, cov_t, with_chrf=False):
    d = d[d[f"{lang}_rating"].notna()]
    if with_chrf:
        d = d.dropna(subset=[f"{lang}_chrf"])
    if len(d) == 0:
        return pd.DataFrame()
    bad = d[f"{lang}_rating"] == 2
    f1, f2, f3 = gate_flags(d, lang, sim_t, cov_t)
    flags = {"baseline (show all)": pd.Series(False, index=d.index),
             "layer 1 (target-language rules)": f1,
             "layer 2 (back-translation)": f2,
             "layer 3 (units, conditions, key terms, coverage)": f3,
             "layers 1+2": f1 | f2,
             "all layers": f1 | f2 | f3}
    rows = [_row(k, d, bad, f) for k, f in flags.items()]
    if with_chrf:
        missed = rows[-1]["dangerous_unflagged"]
        rows.append(_row("chrF-only gate (matched to all layers)", d, bad, chrf_matched_flags(d, lang, bad, missed)))
    return pd.DataFrame(rows)


def sweep(d, lang):
    rows = []
    for s in [0.5, 0.6, 0.7, 0.8]:
        for c in [0.4, 0.5, 0.6, 0.7]:
            t = gate_table(d, lang, s, c)
            if t.empty:
                return t
            r = t[t["gate"] == "all layers"].iloc[0].to_dict()
            r["sim_threshold"], r["coverage_threshold"] = s, c
            rows.append(r)
    return pd.DataFrame(rows).sort_values(["dangerous_unflagged", "false_warnings"]).drop(columns=["gate"])


def lock_thresholds(thresholds):
    new = {k: list(v) for k, v in thresholds.items()}
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE) as f:
            old = json.load(f)
        if old["thresholds"] != new:
            raise RuntimeError(f"Thresholds were locked at {old['locked_utc']} as {old['thresholds']}. "
                               "Changing them after seeing test results would be cheating, so this is blocked.")
        return old
    info = {"thresholds": new, "locked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "rule": "chosen on the dev split only"}
    with open(LOCK_FILE, "w") as f:
        json.dump(info, f, indent=2)
    return info


def final_report(df, lang, sim_t, cov_t):
    return gate_table(df[df["split"] == "test"], lang, sim_t, cov_t, with_chrf=True)


def reasons_for(row, lang, sim_t, cov_t):
    parts = [row[f"{lang}_why1"], row[f"{lang}_why2"], row[f"{lang}_why3"]]
    if row[f"{lang}_sim"] < sim_t:
        parts.append(f"meaning drift (sim {row[f'{lang}_sim']:.2f})")
    if row[f"{lang}_cov"] < cov_t:
        parts.append(f"low word coverage ({row[f'{lang}_cov']:.2f})")
    return "; ".join(p for p in parts if p)


# ----------------------------------------------------------------------------
# THE CLAIM: "chrF can look good while the translation is dangerous"
# ----------------------------------------------------------------------------
def auroc(scores, labels):
    s, y = np.asarray(scores, float), np.asarray(labels, bool)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def chrf_blindness(df, lang, n_boot=2000):
    d = df[df[f"{lang}_rating"].notna() & df[f"{lang}_chrf"].notna()]
    if d.empty:
        return {}
    chrf, rating = d[f"{lang}_chrf"].values, d[f"{lang}_rating"].values
    bad = rating == 2
    out = {"n_rated": len(d), "n_safe": int((rating == 0).sum()), "n_confusing": int((rating == 1).sum()),
           "n_dangerous": int(bad.sum()),
           "mean_chrF_safe": round(float(chrf[rating == 0].mean()), 1) if (rating == 0).any() else None,
           "mean_chrF_dangerous": round(float(chrf[bad].mean()), 1) if bad.any() else None,
           "spearman_chrF_vs_rating": round(float(pd.Series(chrf).corr(pd.Series(rating), method="spearman")), 3)}
    if bad.any() and (~bad).any():
        # AUROC of "low chrF => dangerous": 0.5 = chrF carries no safety signal, 1.0 = perfect
        a = auroc(-chrf, bad)
        rng = np.random.RandomState(SEED)
        boots = []
        for _ in range(n_boot):
            i = rng.randint(0, len(d), len(d))
            if bad[i].any() and (~bad[i]).any():
                boots.append(auroc(-chrf[i], bad[i]))
        out["auroc_low_chrF_detects_dangerous"] = round(a, 3)
        out["auroc_95ci_bootstrap"] = f"{np.percentile(boots, 2.5):.2f}-{np.percentile(boots, 97.5):.2f}"
        safe_med = float(np.median(chrf[rating == 0])) if (rating == 0).any() else float(np.median(chrf))
        out["dangerous_with_chrF_at_or_above_median_of_safe"] = f"{int((chrf[bad] >= safe_med).sum())}/{int(bad.sum())}"
        med = float(np.median(chrf))
        out["safe_but_chrF_below_overall_median"] = f"{int(((rating == 0) & (chrf < med)).sum())}/{int((rating == 0).sum())}"
    return out


def top_failures(df, lang, sim_t=None, cov_t=None, n=5):
    d = df[df[f"{lang}_rating"] == 2].dropna(subset=[f"{lang}_chrf"])
    d = d.sort_values(f"{lang}_chrf", ascending=False).head(n).copy()
    cols = ["id", "english", f"{lang}_mt", f"{lang}_back", f"{lang}_chrf"]
    if sim_t is not None and f"{lang}_sim" in d.columns:
        f1, f2, f3 = gate_flags(d, lang, sim_t, cov_t)
        d["gate_flagged"] = (f1 | f2 | f3).values
        d["gate_reasons"] = [reasons_for(r, lang, sim_t, cov_t) for _, r in d.iterrows()]
        cols += ["gate_flagged", "gate_reasons"]
    return d[cols]


def by_category(df, lang):
    if "category" not in df.columns:
        return pd.DataFrame()
    d = df[df[f"{lang}_rating"].notna()]
    g = d.groupby("category")
    return pd.DataFrame({"n": g.size(),
                         "dangerous": g[f"{lang}_rating"].apply(lambda s: int((s == 2).sum())),
                         "dangerous_rate": g[f"{lang}_rating"].apply(lambda s: round(float((s == 2).mean()), 3)),
                         "mean_chrF": g[f"{lang}_chrf"].mean().round(1)})


def error_types(df, lang):
    d = df[df[f"{lang}_rating"] == 2]
    return d[f"{lang}_error_type"].replace("", "unlabelled").value_counts()


# ----------------------------------------------------------------------------
# FIGURES
# ----------------------------------------------------------------------------
def hero(df, lang):
    import matplotlib.pyplot as plt
    d = df[df[f"{lang}_rating"].notna() & df[f"{lang}_chrf"].notna()]
    if d.empty:
        return
    os.makedirs(FIG_DIR, exist_ok=True)
    rng = np.random.RandomState(SEED)
    names = {0: "safe", 1: "confusing", 2: "dangerous"}
    colors = {0: "tab:green", 1: "tab:orange", 2: "tab:red"}
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for r in [0, 1, 2]:
        m = d[f"{lang}_rating"] == r
        ax.scatter(d.loc[m, f"{lang}_chrf"], d.loc[m, f"{lang}_rating"] + rng.uniform(-0.12, 0.12, int(m.sum())),
                   c=colors[r], alpha=0.75, label=f"{names[r]} (n={int(m.sum())})")
    ax.axvline(d[f"{lang}_chrf"].median(), ls="--", c="gray")
    ax.text(d[f"{lang}_chrf"].median() + 0.5, 2.35, "median chrF", color="gray", fontsize=8)
    top = d[d[f"{lang}_rating"] == 2].sort_values(f"{lang}_chrf", ascending=False).head(3)
    for i, (_, r) in enumerate(top.iterrows()):
        ax.annotate(r["id"], (r[f"{lang}_chrf"], 2), xytext=(10, 14 + 12 * i), textcoords="offset points",
                    fontsize=8, arrowprops=dict(arrowstyle="-", color="gray", lw=0.6))
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["safe", "confusing", "dangerous"])
    ax.set_ylim(-0.4, 2.6)
    ax.set_xlabel("sentence chrF (higher = closer to the human reference)")
    ax.set_title(f"{lang.capitalize()}: a good chrF does not mean a safe translation")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, f"{lang}_chrf_vs_rating.png"), dpi=200)
    plt.show()
    plt.close(fig)


def fig_gate(table, lang):
    import matplotlib.pyplot as plt
    if table.empty:
        return
    os.makedirs(FIG_DIR, exist_ok=True)
    t = table.set_index("gate")
    x = np.arange(len(t))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(x - 0.2, t["dangerous_unflagged"], 0.4, color="tab:red", label="dangerous translations NOT flagged")
    ax.bar(x + 0.2, t["false_warnings"], 0.4, color="tab:gray", label="false warnings")
    ax.set_xticks(x)
    ax.set_xticklabels([g.replace(" (", "\n(") for g in t.index], fontsize=7, rotation=20, ha="right")
    ax.set_ylabel("sentences (held-out test data)")
    ax.set_title(f"{lang.capitalize()}: safety gate vs. showing everything vs. chrF-only")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, f"{lang}_gate_comparison.png"), dpi=200)
    plt.show()
    plt.close(fig)


# ----------------------------------------------------------------------------
# DEMO: what a user of the prototype would see
# ----------------------------------------------------------------------------
def check_instruction(english, lang="amharic"):
    """Translate one sentence and run the gate. NOTE: 'no red flag' never means 'safe'."""
    sim_t, cov_t = 0.6, 0.5
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE) as f:
            sim_t, cov_t = json.load(f)["thresholds"][lang]
    mt = translate([english], "eng_Latn", CODES[lang])[0]
    back = translate([mt], CODES[lang], "eng_Latn")[0]
    g = row_gate(english, mt, back, lang)
    emb = get_emb()
    sim = float((emb.encode([english], normalize_embeddings=True) * emb.encode([back], normalize_embeddings=True)).sum())
    row = {f"{lang}_why1": g["why1"], f"{lang}_why2": g["why2"], f"{lang}_why3": g["why3"],
           f"{lang}_sim": sim, f"{lang}_cov": g["cov"]}
    reasons = reasons_for(row, lang, sim_t, cov_t)
    print("English     :", english)
    print(f"{lang:<12}:", mt)
    print("Back to EN  :", back)
    if reasons:
        print("\nWARNING - DO NOT RELY ON THIS TRANSLATION. Ask a pharmacist or health worker.")
        print("Why:", reasons)
    else:
        print("\nNo automatic red flags found. This does NOT prove it is correct; confirm with a health worker.")
    print("\n" + DISCLAIMER)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    if not os.path.exists(SCORED_FILE):
        run_translation()
    else:                                   # idempotent: re-score chrF with punctuation normalised
        sc = pd.read_csv(SCORED_FILE, keep_default_na=False, dtype=str)
        add_chrf(sc).to_csv(SCORED_FILE, index=False)
    write_provenance(pd.read_csv(SCORED_FILE, keep_default_na=False, dtype=str))
    make_rating_sheets()

    df = load_rated()
    prog = rating_progress(df)
    print("rating progress:", prog)
    if df[["amharic_rating_r1", "amharic_rating_r2", "oromo_rating"]].notna().sum().sum() == 0:
        print(f"\nNext: send each file in {SHEET_DIR}/ to ONE rater (Amharic raters must not see each other's file). "
              "Then re-run this script.")
        return

    summary = [f"# Results summary\n\n**{DISCLAIMER}**\n", "## Rating progress\n```\n" + str(prog) + "\n```"]

    def emit(title, obj):
        text = obj.to_string() if isinstance(obj, (pd.DataFrame, pd.Series)) else str(obj)
        print(f"\n=== {title}\n{text}")
        summary.append(f"## {title}\n```\n{text}\n```")

    emit("Amharic rater agreement (two independent raters)", amharic_agreement(df))
    emit("Oromo rater self-consistency (same person, re-rated later)", oromo_consistency(df))
    for lang in CODES:
        df = add_features(df, lang)
    for lang in CODES:
        emit(f"{lang}: is chrF blind to danger? (all rated sentences)", chrf_blindness(df, lang))
        cat = by_category(df, lang)
        if not cat.empty:
            emit(f"{lang}: dangerous rate by category", cat)
        emit(f"{lang}: error types of dangerous translations", error_types(df, lang))
        emit(f"{lang}: DEV sweep (top 8; pick thresholds from here ONLY)", sweep(df[df["split"] == "dev"], lang).head(8))

    if any(v is None for v in THRESHOLDS.values()):
        print("\nNext: choose (sim, coverage) per language from the DEV tables, put them in THRESHOLDS at the "
              "top of this file, and re-run. They will be locked and the test set scored once.")
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(summary))
        return

    lock = lock_thresholds(THRESHOLDS)
    emit("Locked thresholds", json.dumps(lock, indent=2))
    for lang in CODES:
        s, c = THRESHOLDS[lang]
        rep = final_report(df, lang, s, c)
        emit(f"{lang}: FINAL TEST report (sim={s}, coverage={c})", rep)
        emit(f"{lang}: dangerous translations with the HIGHEST chrF (hero examples)",
             top_failures(df, lang, s, c).to_string())
        hero(df, lang)
        fig_gate(rep, lang)

    summary.append(
        "## Limitations and disclosures (copy these into the write-up)\n"
        "- The test set is deliberately hard (negations, stop-rules, edge doses); error rates here are NOT real-world rates.\n"
        "- Afaan Oromo rests on ONE rater and 50 sentences (about 25 dev / 25 test): treat it as indicative only.\n"
        "- The Oromo rater is also the coder and had seen model outputs before rating, so Oromo ratings are not fully blind.\n"
        "- Gate rules were written after looking at model outputs for ALL sentences (dev and test); only the "
        "thresholds were tuned on dev alone. The test split is therefore not fully unseen for rule design.\n"
        "- Amharic uses the worse (higher) of two independent ratings: a deliberately conservative choice.\n"
        "- Back-translation uses the same model, so a consistent error can survive the round trip.\n"
        "- chrF uses one reference per sentence; valid synonyms (e.g. different words for 'tablet') are penalised.\n"
        "- Amharic negation detection is a prefix heuristic with an exception list; Oromo negation looks for 'hin'.\n"
        "- No real patient data was used.\n"
        f"- {DISCLAIMER}\n")
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(summary))
    print(f"\nWrote {SUMMARY_FILE} and figures/. {DISCLAIMER}")


if __name__ == "__main__" or "get_ipython" in globals():
    main()
