"""Learned classifier for MedTranslate Guard (a team member's model).

Combined TF-IDF + 19 engineered features, logistic regression, trained on Round 1 only
(150 rows: 100 Amharic + 50 Afaan Oromo; label 2 = dangerous). The decision threshold was chosen on
Round 1 cross-validation and is stored inside the model file. Nothing here retrains or re-tunes it.

The saved .joblib holds only the scikit-learn pipeline. The feature extraction below is copied unchanged
from the training notebook and MUST stay identical, otherwise predictions silently change.

Requires scikit-learn==1.6.1 (the version the model was saved with; newer versions cannot load it).

    import ml_classifier as ml
    ml.check_instruction_ml("Take one tablet with water.", mt, back_translation, "amharic")
"""
import re
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parent / "models" / "combined_binary_translation_model.joblib"

NEGATION_WORDS = {
    "not", "no", "never", "without",
    "don't", "doesn't", "didn't",
    "cannot", "can't", "shouldn't",
    "mustn't", "avoid",
}

UNITS = {
    "mg", "ml", "mcg", "g", "gram", "grams",
    "tablet", "tablets", "capsule", "capsules",
    "drop", "drops", "puff", "puffs",
    "hour", "hours", "day", "days",
    "week", "weeks", "month", "months",
    "dose", "doses", "teaspoon",
}

KEY_TERMS = {
    "tablet", "tablets", "capsule", "capsules",
    "syrup", "cream", "drops", "drop",
    "inhaler", "puff", "puffs",
    "medicine", "medication", "dose", "doses",
    "eye", "eyes", "skin", "mouth",
    "child", "children", "pregnant",
    "allergic", "doctor", "clinic",
}

_chrf_metric = None
_labse = None
_package = None


def _chrf():
    global _chrf_metric
    if _chrf_metric is None:
        from sacrebleu.metrics import CHRF
        _chrf_metric = CHRF()
    return _chrf_metric


def get_labse():
    """LaBSE sentence encoder (about 1.9 GB download on first use)."""
    global _labse
    if _labse is None:
        from sentence_transformers import SentenceTransformer
        _labse = SentenceTransformer("sentence-transformers/LaBSE")
    return _labse


def load_package(path=MODEL_PATH):
    """Returns the saved dict: model, threshold, feature_names, model_type, target_mapping."""
    global _package
    if _package is None:
        _package = joblib.load(path)
    return _package


# ---------------------------------------------------------------- features (copied from the training notebook)
def tokenize(text):
    return re.findall(r"[a-zA-Z]+", str(text).lower())


def extract_numbers(text):
    return re.findall(r"\d+(?:\.\d+)?", str(text))


def count_negations(text):
    return sum(word in NEGATION_WORDS for word in tokenize(text))


def extract_terms(text, vocabulary):
    return set(tokenize(text)).intersection(vocabulary)


def calculate_features(row):
    english = str(row["english"])
    mt = str(row["machine_translation"])
    bt = str(row["back_translation"])
    language = str(row["language"]).lower()

    features = {}

    en_nums = Counter(extract_numbers(english))
    bt_nums = Counter(extract_numbers(bt))
    features["num_match"] = sum((en_nums & bt_nums).values())
    features["num_missing"] = sum((en_nums - bt_nums).values())
    features["num_extra"] = sum((bt_nums - en_nums).values())

    en_neg = count_negations(english)
    bt_neg = count_negations(bt)
    features["neg_mismatch"] = int((en_neg > 0) != (bt_neg > 0))
    features["neg_count_diff"] = abs(en_neg - bt_neg)
    features["neg_dropped"] = int(en_neg > bt_neg)
    features["neg_added"] = int(bt_neg > en_neg)

    features["unit_match"] = int(extract_terms(english, UNITS) == extract_terms(bt, UNITS))

    en_terms = extract_terms(english, KEY_TERMS)
    bt_terms = extract_terms(bt, KEY_TERMS)
    features["key_term_diff"] = len(en_terms.symmetric_difference(bt_terms))

    en_words = set(tokenize(english))
    bt_words = set(tokenize(bt))
    union = en_words.union(bt_words)
    features["word_jaccard"] = len(en_words.intersection(bt_words)) / len(union) if union else 0

    try:
        features["chrf_en_bt"] = _chrf().sentence_score(bt, [english]).score / 100
    except Exception:
        features["chrf_en_bt"] = 0

    features["len_ratio_mt"] = len(mt) / max(len(english), 1)
    features["len_ratio_bt"] = len(bt) / max(len(english), 1)

    is_amharic = int(language == "amharic")
    features["is_amharic"] = is_amharic
    latin_chars = len(re.findall(r"[a-zA-Z]", mt))
    all_letters = len(re.findall(r"[^\W\d_]", mt, flags=re.UNICODE))
    features["latin_in_amharic"] = latin_chars / max(all_letters, 1) if is_amharic else 0
    features["amharic_unapproved_tablet_term"] = int(is_amharic and "ጡባዊ" in mt)
    features["amharic_accepted_tablet_term"] = int(is_amharic and "ታብሌት" in mt)
    return features


# ---------------------------------------------------------------- prediction
def build_model_input(df):
    """df needs columns: language, english, machine_translation, back_translation.
    Returns the 20-column frame the saved pipeline expects (model_text + 19 features)."""
    pkg = load_package()
    df = df.reset_index(drop=True).copy()
    df["language"] = df["language"].astype(str).str.lower().str.strip()
    for col in ["english", "machine_translation", "back_translation"]:
        df[col] = df[col].fillna("").astype(str)

    X = pd.DataFrame([calculate_features(r) for _, r in df.iterrows()])

    labse = get_labse()
    enc = lambda col: labse.encode(df[col].tolist(), convert_to_numpy=True,
                                   normalize_embeddings=True, show_progress_bar=False)
    en, mt, bt = enc("english"), enc("machine_translation"), enc("back_translation")
    X["sim_en_mt"] = np.sum(en * mt, axis=1)
    X["sim_en_bt"] = np.sum(en * bt, axis=1)

    X = X[pkg["feature_names"]]                      # same 19 features, same order as training
    model_text = ("LANGUAGE " + df["language"]
                  + " ENGLISH " + df["english"]
                  + " MACHINE_TRANSLATION " + df["machine_translation"]
                  + " BACK_TRANSLATION " + df["back_translation"])
    X.insert(0, "model_text", model_text)
    return X


def predict_df(df):
    """Adds ml_proba (probability of 'dangerous') and ml_flag (proba >= the saved threshold)."""
    pkg = load_package()
    X = build_model_input(df)
    proba = pkg["model"].predict_proba(X)[:, 1]
    out = df.reset_index(drop=True).copy()
    out["ml_proba"] = proba
    out["ml_flag"] = proba >= pkg["threshold"]
    return out


def check_instruction_ml(english, machine_translation, back_translation, language):
    """One sentence. Returns a small dict; 'no flag' never means 'safe'."""
    row = pd.DataFrame([{"language": language, "english": english,
                         "machine_translation": machine_translation,
                         "back_translation": back_translation}])
    r = predict_df(row).iloc[0]
    return {"dangerous_probability": round(float(r.ml_proba), 3),
            "threshold": round(float(load_package()["threshold"]), 3),
            "flag": bool(r.ml_flag),
            "note": "Prototype, not medical advice. No flag never means safe."}
