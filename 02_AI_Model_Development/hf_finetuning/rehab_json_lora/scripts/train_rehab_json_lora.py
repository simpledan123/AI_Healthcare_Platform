# 02_AI_Model_Development/hf_finetuning/rehab_json_lora/scripts/train_rehab_json_lora.py
import os
import sys
import argparse
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, PROJECT_ROOT)

import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, TaskType, get_peft_model


def infer_target_modules(model) -> List[str]:
    """
    모델 아키텍처에 따라 LoRA 타깃 모듈을 자동 추정.
    - LLaMA/Qwen 계열: q_proj, v_proj
    - GPT2 계열: c_attn
    - GPT-NeoX 계열: query_key_value
    """
    module_names = set()
    for name, _ in model.named_modules():
        module_names.add(name.split(".")[-1])

    if "q_proj" in module_names and "v_proj" in module_names:
        return ["q_proj", "v_proj"]
    if "c_attn" in module_names:
        return ["c_attn"]
    if "query_key_value" in module_names:
        return ["query_key_value"]

    raise ValueError(
        "target_modules 자동 추정 실패. --target_modules q_proj,v_proj 처럼 직접 지정하세요."
    )


class CausalSFTDataCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.pad_id = tokenizer.pad_token_id

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        max_len = max(len(f["input_ids"]) for f in features)

        input_ids, attention_mask, labels = [], [], []
        for f in features:
            pad_len = max_len - len(f["input_ids"])
            input_ids.append(f["input_ids"] + [self.pad_id] * pad_len)
            attention_mask.append(f["attention_mask"] + [0] * pad_len)
            labels.append(f["labels"] + [-100] * pad_len)

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def main(
    model_name: str,
    train_jsonl: str,
    valid_jsonl: str,
    output_dir: str,
    max_length: int,
    epochs: int,
    lr: float,
    batch_size: int,
    grad_accum: int,
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
    target_modules_arg: Optional[str],
    trust_remote_code: bool,
):
    ds = load_dataset("json", data_files={"train": train_jsonl, "validation": valid_jsonl})

    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        use_fast=True,
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token is None:
        # GPT2 계열 등 pad_token이 없는 경우 대비
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=trust_remote_code,
    )
    if model.config.pad_token_id is None:
        model.config.pad_token_id = tokenizer.pad_token_id

    # LoRA 타깃 모듈 결정
    if target_modules_arg:
        target_modules = [x.strip() for x in target_modules_arg.split(",") if x.strip()]
    else:
        target_modules = infer_target_modules(model)

    lora_cfg = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=target_modules,
    )
    model = get_peft_model(model, lora_cfg)

    # prompt만 -100 마스킹, response만 학습
    eos_id = tokenizer.eos_token_id

    def tokenize_fn(ex):
        prompt = ex["prompt"]
        response = ex["response"]

        prompt_ids = tokenizer(prompt, add_special_tokens=False).input_ids
        resp_ids = tokenizer(response, add_special_tokens=False).input_ids
        if eos_id is not None:
            resp_ids = resp_ids + [eos_id]

        input_ids = prompt_ids + resp_ids
        labels = ([-100] * len(prompt_ids)) + resp_ids
        attention_mask = [1] * len(input_ids)

        # truncate
        if len(input_ids) > max_length:
            input_ids = input_ids[:max_length]
            labels = labels[:max_length]
            attention_mask = attention_mask[:max_length]

        return {"input_ids": input_ids, "labels": labels, "attention_mask": attention_mask}

    ds_tok = ds.map(tokenize_fn, remove_columns=ds["train"].column_names)

    data_collator = CausalSFTDataCollator(tokenizer)

    os.makedirs(output_dir, exist_ok=True)
    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=max(1, batch_size),
        gradient_accumulation_steps=grad_accum,
        num_train_epochs=epochs,
        learning_rate=lr,
        fp16=torch.cuda.is_available(),
        evaluation_strategy="steps",
        eval_steps=200,
        save_steps=200,
        logging_steps=50,
        save_total_limit=2,
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds_tok["train"],
        eval_dataset=ds_tok["validation"],
        data_collator=data_collator,
    )

    trainer.train()

    adapter_dir = os.path.join(output_dir, "adapter")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    print(f"[OK] saved adapter to: {adapter_dir}")
    print("환경변수 예시:")
    print(f"export REHAB_LOCAL_LORA_DIR={adapter_dir}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", type=str, default="gpt2")
    p.add_argument("--train_jsonl", type=str, required=True)
    p.add_argument("--valid_jsonl", type=str, required=True)
    p.add_argument("--output_dir", type=str, default="artifacts/rehab_json_lora")
    p.add_argument("--max_length", type=int, default=768)

    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--batch_size", type=int, default=2)
    p.add_argument("--grad_accum", type=int, default=8)

    p.add_argument("--lora_r", type=int, default=8)
    p.add_argument("--lora_alpha", type=int, default=16)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    p.add_argument("--target_modules", type=str, default=None)
    p.add_argument("--trust_remote_code", action="store_true")

    args = p.parse_args()

    main(
        model_name=args.model_name,
        train_jsonl=args.train_jsonl,
        valid_jsonl=args.valid_jsonl,
        output_dir=args.output_dir,
        max_length=args.max_length,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules_arg=args.target_modules,
        trust_remote_code=args.trust_remote_code,
    )