#!/usr/bin/env python3
"""Count the number of tokens in a log file.

Usage:
    python3 count_tokens.py <log_file> [log_file ...]

The log files in this repo are JSON arrays of message strings, but this script
also handles plain-text logs. Token counting uses tiktoken if available, and
otherwise falls back to a character-based estimate (~4 chars/token).
"""

import json
import sys


def _get_counter():
    """Return (count_fn, name). Prefer a real tokenizer, fall back to estimate."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return (lambda text: len(enc.encode(text)), "tiktoken/cl100k_base")
    except Exception:
        # Rough heuristic: English text averages ~4 characters per token.
        return (lambda text: (len(text) + 3) // 4, "estimate (~4 chars/token)")


def extract_text(path):
    """Read a log file and return its text content as a single string."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw  # plain-text log

    if isinstance(data, list):
        return "\n".join(
            item if isinstance(item, str) else json.dumps(item) for item in data
        )
    if isinstance(data, dict):
        return json.dumps(data)
    return str(data)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1

    count, method = _get_counter()
    print(f"Token counting method: {method}\n")

    grand_total = 0
    for path in argv[1:]:
        try:
            text = extract_text(path)
        except OSError as e:
            print(f"{path}: ERROR - {e}")
            continue
        tokens = count(text)
        grand_total += tokens
        print(f"{path}: {tokens:,} tokens ({len(text):,} chars)")

    if len(argv) > 2:
        print(f"\nTotal: {grand_total:,} tokens")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

    # # Usage
    # python3 count_tokens.py logs/current_global-memory_164202_170626.log
    # python3 count_tokens.py logs/*.log   # multiple files + grand total