"""
Test a fine-tuned OurAI model with sample prompts.

Usage:
    python3 test_ourai.py --adapter ../llmteacher/data/models/ourai_v1/final_adapter
    python3 test_ourai.py --merged ../llmteacher/data/models/ourai_v1/merged
    python3 test_ourai.py --base-only  # test the base model without fine-tuning
"""

import os
import sys
import argparse
import json
from pathlib import Path

# Load HF_TOKEN from .env if present (gitignored)
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().strip().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


TEST_PROMPTS = [
    "list files in the current directory",
    "read the file test.txt",
    "search for 'error' in log files",
    "create a new file called hello.py with a Python hello world script",
    "save a tip for debugging with strace",
    "replace line 5 in config.txt with 'enabled=true'",
    "compare two files a.txt and b.txt",
    "what tools are available?",
]


def build_prompt(system, user):
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def main():
    parser = argparse.ArgumentParser(description="Test OurAI fine-tuned model")
    parser.add_argument("--adapter", help="Path to saved adapter (uses PEFT)")
    parser.add_argument("--merged", help="Path to merged model")
    parser.add_argument("--base-only", action="store_true",
                        help="Test base model without fine-tuning")
    parser.add_argument("--model", default="meta-llama/Llama-3.2-3B-Instruct",
                        help="Base model name")
    parser.add_argument("--prompt", help="Single prompt to test (instead of defaults)")
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    if not (args.adapter or args.merged or args.base_only):
        parser.print_help()
        print("\nSpecify --adapter, --merged, or --base-only")
        sys.exit(1)

    # System prompt for OurAI agent
    system_prompt = """You are an AI assistant for the OurAI framework. You help users by using XML-based tools.

AVAILABLE TOOLS:
- <ReadFile><fileName>path</fileName></ReadFile>: Read file content
- <WriteFile><fileName>path</fileName><contentOfFile>content</contentOfFile></WriteFile>: Write file
- <AppendFile><fileName>path</fileName><contentOfFile>content</contentOfFile></AppendFile>: Append to file
- <CreateFile><fileName>path</fileName><contentOfFile>content</contentOfFile></CreateFile>: Create file (fails if exists)
- <TreeView><path>.</path><depth>3</depth></TreeView>: Show directory tree
- <List><path>.</path></List>: List files
- <Find><pattern>*.py</pattern><path>.</path></Find>: Find files by name
- <Grep><pattern>search</pattern><fileName>file</fileName><recursive>true</recursive></Grep>: Search content
- <Sed><pattern>old</pattern><replacement>new</replacement><fileName>file</fileName></Sed>: Find/replace
- <ReplaceLine><fileName>file</fileName><fromLine>1</fromLine><replacement>new</replacement></ReplaceLine>: Replace lines
- <Diff><file1>a</file1><file2>b</file2></Diff>: Compare files
- <Head><fileName>file</fileName><lines>10</lines></Head>: First N lines
- <Tail><fileName>file</fileName><lines>10</lines></Tail>: Last N lines
- <Sort><fileName>file</fileName></Sort>: Sort lines
- <ExecuteScript><fileName>script.py</fileName></ExecuteScript>: Run script
- <Terminal><arg1>command</arg1></Terminal>: Run command
- <listTools/>: List all tools
- <WWW><url>url</url></WWW>: Fetch web page
- <SaveTip><title>name</title><content>text</content></SaveTip>: Save a tip
- <GetTip><title>name</title></GetTip>: Retrieve a tip
- <ListTips/>: List all tips
- <DeleteTip><title>name</title></DeleteTip>: Delete a tip

Use these XML tools to accomplish tasks. Always use proper XML syntax."""

    print(f"\n{'='*60}")
    print("OURAI MODEL TEST")
    print(f"{'='*60}\n")

    if args.base_only:
        print(f"Loading base model: {args.model}")
    elif args.adapter:
        print(f"Loading adapter from: {args.adapter}")
    elif args.merged:
        print(f"Loading merged model from: {args.merged}")

    # Load tokenizer (always from base model, since merged dir doesn't have tokenizer files)
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, token=os.environ["HF_TOKEN"] if "HF_TOKEN" in os.environ else None,
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token

    # Load model
    if args.base_only:
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            token=os.environ["HF_TOKEN"],
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )
    elif args.adapter:
        from peft import PeftModel
        base_model = AutoModelForCausalLM.from_pretrained(
            args.model,
            token=os.environ["HF_TOKEN"],
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )
        model = PeftModel.from_pretrained(base_model, args.adapter)
    elif args.merged:
        model = AutoModelForCausalLM.from_pretrained(
            args.merged,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )

    model.eval()

    prompts = [args.prompt] if args.prompt else TEST_PROMPTS

    for user_input in prompts:
        prompt_text = build_prompt(system_prompt, user_input)

        print(f"\n{'─'*60}")
        print(f"USER: {user_input}")
        print(f"{'─'*60}")

        inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=args.max_tokens,
                temperature=args.temperature,
                top_p=0.9,
                top_k=50,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
            )

        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        print(f"ASSISTANT: {response.strip()}")
        print()

    model_name = args.adapter or args.merged or args.model
    print(f"\n{'='*60}")
    print(f"Done testing: {model_name}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
