"""
QLoRA fine-tuning of Llama 3.2 3B Instruct on AIIA framework data.

Usage:
    python3 train_aiia.py
"""

import os
import sys
import argparse
import json
import gc
from pathlib import Path

env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().strip().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    set_seed,
)
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig


def parse_args():
    parser = argparse.ArgumentParser(description="QLoRA fine-tune AIIA model")
    parser.add_argument("--model", default="meta-llama/Llama-3.2-3B-Instruct")
    parser.add_argument("--data", default="../../llmteacher/data/processed_datasets/ourai/aiia_train.jsonl")
    parser.add_argument("--output-dir", default="../../llmteacher/data/models/aiia_v1")
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=-1)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    set_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"AIIA FRAMEWORK TRAINING v1")
    print(f"{'='*60}")
    print(f"Model: {args.model}")
    print(f"Data: {args.data}")
    print(f"Output: {output_dir.resolve()}")
    print(f"LoRA rank={args.lora_r}, alpha={args.lora_alpha}")
    print(f"Batch size={args.batch_size}, grad_accum={args.grad_accum}")
    print(f"Max seq length={args.max_seq_length}")
    print(f"{'='*60}\n")

    if not torch.cuda.is_available():
        print("ERROR: CUDA not available!")
        sys.exit(1)
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB\n")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model,
        token=os.environ["HF_TOKEN"],
        trust_remote_code=True,
    )
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    print("Loading model with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        token=os.environ["HF_TOKEN"],
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model.config.gradient_checkpointing = True
    model.enable_input_require_grads()

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )

    print(f"\nLoading dataset from {args.data}...")
    dataset = load_dataset("json", data_files=args.data, split="train")
    print(f"Training examples: {len(dataset)}")

    sft_config = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        warmup_steps=10,
        lr_scheduler_type="cosine",
        bf16=True,
        logging_steps=5,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=3,
        optim="adamw_8bit",
        report_to="none",
        seed=args.seed,
        max_length=args.max_seq_length,
        dataset_text_field="text",
    )
    if args.max_steps > 0:
        sft_config.max_steps = args.max_steps

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    trainer.model.print_trainable_parameters()

    print(f"\nStarting training...")
    trainer.train()

    final_path = output_dir / "final_adapter"
    trainer.save_model(str(final_path))
    tokenizer.save_pretrained(str(final_path))

    print(f"\nMerging LoRA weights...")
    merged_model = trainer.model.merge_and_unload()
    merged_path = output_dir / "merged"
    merged_model.save_pretrained(str(merged_path))
    tokenizer.save_pretrained(str(merged_path))

    config_path = output_dir / "train_config.json"
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)

    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE!")
    print(f"Adapter: {final_path.resolve()}")
    print(f"Merged model: {merged_path.resolve()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
