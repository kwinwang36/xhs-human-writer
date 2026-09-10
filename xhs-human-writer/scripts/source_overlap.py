#!/usr/bin/env python3
"""Find long exact character overlaps between a draft and reference texts.

This is a review aid, not a plagiarism detector or legal threshold.
"""

from __future__ import annotations

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


def normalize(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def collect_sources(paths: list[Path]) -> list[Path]:
    collected: list[Path] = []
    for path in paths:
        if path.is_dir():
            collected.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file() and candidate.suffix.lower() in TEXT_SUFFIXES
            )
        elif path.is_file():
            collected.append(path)
        else:
            raise FileNotFoundError(f"Reference path not found: {path}")
    return collected


def longest_overlap(draft: str, source: str) -> tuple[int, str]:
    draft_normalized = normalize(draft)
    source_normalized = normalize(source)
    match = SequenceMatcher(None, draft_normalized, source_normalized, autojunk=False).find_longest_match()
    return match.size, draft_normalized[match.a : match.a + match.size]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="Draft Markdown or text file")
    parser.add_argument("references", nargs="+", type=Path, help="Reference files or directories")
    parser.add_argument(
        "--min-chars",
        type=int,
        default=18,
        help="Minimum normalized contiguous characters to flag (default: 18)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_chars < 8:
        raise ValueError("--min-chars must be at least 8 to limit noisy matches")
    if not args.draft.is_file():
        raise FileNotFoundError(f"Draft file not found: {args.draft}")

    draft_text = args.draft.read_text(encoding="utf-8")
    sources = collect_sources(args.references)
    if not sources:
        print("No reference text files found.")
        return 2

    flagged = []
    for source_path in sources:
        size, excerpt = longest_overlap(draft_text, source_path.read_text(encoding="utf-8"))
        if size >= args.min_chars:
            flagged.append((size, source_path, excerpt))

    if not flagged:
        print(f"No exact normalized overlap of {args.min_chars}+ characters found across {len(sources)} source(s).")
        return 0

    print("Potential overlaps for manual review:")
    for size, source_path, excerpt in sorted(flagged, reverse=True, key=lambda item: item[0]):
        print(f"- {source_path}: {size} chars: {excerpt}")
    print("These matches are heuristics, not a plagiarism or legal determination.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
