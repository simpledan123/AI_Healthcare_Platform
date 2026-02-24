# 02_AI_Model_Development/hf_finetuning/scripts/train_pain_area_classifier.py
import os
import argparse
import numpy as np

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
from sklearn.metrics import accuracy_score, f1_score


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "macro_f1": f1_score(labels, preds, average="macro"),
    }


def main(
    model_name: str,
    train_csv: str,
    valid_csv: str,
    output_dir: str,
    epochs: int,
    lr: float,
    batch_size: int,
    max_length: int,
):
    ds = load_dataset(
        "csv",
        data_files={"train": train_csv, "validation": valid_csv},
    )

    # 라벨 목록 생성
    labels = sorted(list(set(ds["train"]["label"]) | set(ds["validation"]["label"])))
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def preprocess(batch):
        enc = tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=max_length,
        )
        enc["labels"] = [label2id[l] for l in batch["label"]]
        return enc

    ds = ds.map(preprocess, batched=True, remove_columns=ds["train"].column_names)

    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(labels),
        label2id=label2id,
        id2label=id2label,
    )

    os.makedirs(output_dir, exist_ok=True)

    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        num_train_epochs=epochs,
        learning_rate=lr,
        eval_strategy="steps",
        eval_steps=100,
        save_steps=100,
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        save_total_limit=2,
        report_to=[],  # wandb 등 끔
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    trainer.train()

    best_dir = os.path.join(output_dir, "best")
    trainer.save_model(best_dir)
    tokenizer.save_pretrained(best_dir)

    print(f"[OK] saved best model to: {best_dir}")
    print("Set env like:")
    print(f"export PAIN_AREA_MODEL_DIR={best_dir}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", type=str, default="klue/roberta-base")
    p.add_argument("--train_csv", type=str, required=True)
    p.add_argument("--valid_csv", type=str, required=True)
    p.add_argument("--output_dir", type=str, default="artifacts/pain_area_classifier")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--batch_size", type=int, default=16)
    p.add_argument("--max_length", type=int, default=128)
    args = p.parse_args()

    main(
        model_name=args.model_name,
        train_csv=args.train_csv,
        valid_csv=args.valid_csv,
        output_dir=args.output_dir,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        max_length=args.max_length,
    )