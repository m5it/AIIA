"""
Prepare OurAI chat history as Llama 3.2 Instruct training data.

Reads .dbk files from history/, parses conversations,
formats into Llama 3.2 chat template, outputs JSONL.

Usage:
    python prepare_ourai_data.py
    python prepare_ourai_data.py --output ../llmteacher/data/processed_datasets/ourai_train.jsonl
    python prepare_ourai_data.py --history-dir history/ --max-sessions 10
"""

import json
import os
import argparse
from pathlib import Path
from collections import OrderedDict


LLAMA_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system}<|eot_id|><|start_header_id|>user<|end_header_id|>

{user}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{assistant}<|eot_id|>"""


def parse_session(lines):
    """Parse a list of JSON lines (one session) into structured turns."""
    turns = []
    current_turn = None

    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        role = obj.get("role", "")
        content = obj.get("content", "")
        thinking = obj.get("thinking", "")
        name = obj.get("name", "")

        if role == "system":
            current_turn = {"system": content, "messages": []}

        elif role == "user":
            if current_turn is not None:
                current_turn["messages"].append({"role": "user", "content": content})

        elif role == "assistant":
            assistant_text = content
            if thinking:
                assistant_text = f"{assistant_text}\n\n[Thinking: {thinking}]"
            if current_turn is not None:
                current_turn["messages"].append({"role": "assistant", "content": assistant_text})

        elif role == "tool":
            if current_turn is not None:
                result = f"[Tool Result: {name}] {content[:500]}"
                if len(content) > 500:
                    result += "..."
                current_turn["messages"].append({"role": "tool_result", "content": result})

    if current_turn and current_turn["messages"]:
        turns.append(current_turn)

    return turns


def convert_to_training_examples(session_turns):
    """Convert parsed session turns into Llama-format training examples.

    Groups messages into (user → assistant) exchanges.
    Tool results are prefixed as user-like input so model learns to expect them.
    """
    examples = []
    system_prompt = None

    for session in session_turns:
        system_prompt = session.get("system", "")
        msgs = session.get("messages", [])

        # Build examples from user/assistant pairs
        i = 0
        while i < len(msgs):
            msg = msgs[i]
            if msg["role"] == "user":
                user_text = msg["content"]
                i += 1

                # Collect assistant responses and tool results that follow
                assistant_parts = []
                while i < len(msgs) and msgs[i]["role"] in ("assistant", "tool_result"):
                    m = msgs[i]
                    if m["role"] == "assistant":
                        assistant_parts.append(m["content"])
                    elif m["role"] == "tool_result":
                        assistant_parts.append(f"\n{m['content']}")
                    i += 1

                if assistant_parts:
                    assistant_text = "\n".join(assistant_parts)
                    example = LLAMA_TEMPLATE.format(
                        system=system_prompt,
                        user=user_text,
                        assistant=assistant_text,
                    )
                    examples.append(example)
            else:
                i += 1

    return examples


def read_history_files(history_dir):
    """Read all .dbk files and group by session."""
    sessions = OrderedDict()
    history_path = Path(history_dir)

    for fpath in sorted(history_path.glob("*.dbk")):
        content = fpath.read_text(encoding="utf-8", errors="replace")
        lines = content.strip().split("\n")

        # Determine session ID from filename or first line
        session_id = fpath.stem

        for line in lines:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = obj.get("sessionId", session_id)
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(line)

    return sessions


def main():
    parser = argparse.ArgumentParser(description="Prepare OurAI chat history for Llama fine-tuning")
    parser.add_argument("--history-dir", default="history",
                        help="Directory containing .dbk history files (default: history/)")
    parser.add_argument("--output", default="../llmteacher/data/processed_datasets/ourai_train.jsonl",
                        help="Output JSONL path (default: ../llmteacher/data/processed_datasets/ourai_train.jsonl)")
    parser.add_argument("--max-sessions", type=int, default=None,
                        help="Max sessions to process (default: all)")
    parser.add_argument("--no-wandb", action="store_true",
                        help="Exclude W&B/progress metadata")
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    history_dir = base_dir / args.history_dir
    output_path = Path(args.output)

    print(f"Reading history from: {history_dir.resolve()}")
    print(f"Output to: {output_path.resolve()}")

    sessions = read_history_files(history_dir)
    print(f"Found {len(sessions)} sessions")

    if args.max_sessions:
        session_ids = list(sessions.keys())[:args.max_sessions]
    else:
        session_ids = list(sessions.keys())

    all_examples = []
    for sid in session_ids:
        lines = sessions[sid]
        parsed = parse_session(lines)
        examples = convert_to_training_examples(parsed)
        all_examples.extend(examples)
        if examples:
            print(f"  Session {sid}: {len(examples)} training examples")

    print(f"\nTotal training examples: {len(all_examples)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps({"text": ex}, ensure_ascii=False) + "\n")

    # Also write a plain text version for easy inspection
    txt_path = output_path.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(ex + "\n\n" + "=" * 80 + "\n\n")

    print(f"Saved {len(all_examples)} examples to {output_path}")
    print(f"Saved readable version to {txt_path}")

    # Stats
    total_chars = sum(len(ex) for ex in all_examples)
    print(f"Total characters: {total_chars:,}")
    print(f"Avg example length: {total_chars // max(len(all_examples), 1):,} chars")


if __name__ == "__main__":
    main()
