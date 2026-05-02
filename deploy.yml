"""
ml/evaluation/evaluate.py
--------------------------
Evaluate a trained classifier checkpoint against a held-out test set.

Usage:
    python ml/evaluation/evaluate.py \
        --model-path ml/models/classifier_v3.pt \
        --data-dir data/training
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)

LABEL_LIST = [
    "Engineering", "Marketing", "Finance", "Healthcare",
    "Design", "Data Science", "Operations", "Sales",
    "Legal", "Human Resources", "Education", "Other",
]
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}


def evaluate(args):
    logging.basicConfig(level=logging.INFO)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info("Loading model from %s …", args.model_path)
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=len(LABEL_LIST)
    )
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.to(device).eval()

    # Load test data
    test_df = pd.read_csv(Path(args.data_dir) / "test.tsv", sep="\t")
    texts = (test_df["title"] + " [SEP] " + test_df["description"].fillna("")).tolist()
    true_labels = [LABEL2ID.get(l, LABEL2ID["Other"]) for l in test_df["category"]]

    # Batch inference
    pred_labels = []
    batch_size = 32
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            enc = tokenizer(
                batch_texts, truncation=True, padding=True,
                max_length=256, return_tensors="pt"
            ).to(device)
            logits = model(**enc).logits
            preds = logits.argmax(dim=-1).cpu().tolist()
            pred_labels.extend(preds)

    # Metrics
    acc = accuracy_score(true_labels, pred_labels)
    f1_macro = f1_score(true_labels, pred_labels, average="macro")
    f1_weighted = f1_score(true_labels, pred_labels, average="weighted")

    report = classification_report(true_labels, pred_labels, target_names=LABEL_LIST)
    cm = confusion_matrix(true_labels, pred_labels)

    print("\n" + "═" * 60)
    print("  JobPulse Classifier — Evaluation Report")
    print("═" * 60)
    print(f"  Model:          {args.model_path}")
    print(f"  Test samples:   {len(true_labels)}")
    print(f"  Accuracy:       {acc:.4f}")
    print(f"  F1 (macro):     {f1_macro:.4f}")
    print(f"  F1 (weighted):  {f1_weighted:.4f}")
    print("─" * 60)
    print(report)

    # Save results
    out = {
        "model_path": str(args.model_path),
        "test_samples": len(true_labels),
        "accuracy": round(acc, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_weighted": round(f1_weighted, 4),
        "confusion_matrix": cm.tolist(),
    }
    out_path = Path(args.output) if args.output else Path("ml/evaluation/results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="ml/models/classifier_v3.pt")
    parser.add_argument("--data-dir", default="data/training")
    parser.add_argument("--output", default=None)
    evaluate(parser.parse_args())
