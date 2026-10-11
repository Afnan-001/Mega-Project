from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

MAIN_DIR = Path(__file__).resolve().parents[1]
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from llm import LLM

# Load Environment Variables
load_dotenv()

DATA_DIR = MAIN_DIR / "outputs" / "data"
DEFAULT_INPUT = DATA_DIR / "concepts.json"
DEFAULT_OUTPUT = DATA_DIR / "clean_concepts.json"

PROMPT_TEMPLATE = """You are an expert technical domain terminology editor.

Your task is to refine a list of raw extracted concept strings from textbook material into grammatically, syntactically, and conceptually correct technical concept terms.

Rules:
1. Subject-Independent: Apply general rules of technical writing and domain terminology regardless of the subject field.
2. Fix OCR & Formatting Errors: Rejoin broken words split by spaces (e.g., "tr anslation scheme" -> "Translation Scheme", "activ ation records" -> "Activation Record").
3. Delete Fragment Noise: Remove incomplete/truncated word fragments, broken tokens, and non-technical gibberish (e.g., "tran", "tra", "transf", "ont", "ab out", "ac kno").
4. Canonicalize Terminology: Standardize singular/plural duplicates into consistent, clean canonical technical terms (e.g., "transition diagrams" -> "Transition Diagram").
5. Proper Capitalization: Use standard Title Case or recognized technical capitalization (e.g., "SQL", "ACID", "Transfer Function", "Basic Block").
6. Remove Generic Filler: Exclude non-technical conversational filler or exercise instructions.
7. Return Format: Return ONLY a valid JSON array of strings containing the cleaned concepts (e.g., ["Actual Parameter", "Transfer Function", "Transition Diagram"]). Do NOT include markdown commentary or extra text outside the JSON array.

RAW CONCEPTS TO CLEAN:
{raw_concepts_json}
"""


def clean_concepts_batch(llm: LLM, raw_batch: list[str]) -> list[str]:
    combined_json = json.dumps(raw_batch, ensure_ascii=False)
    usr_msg = PROMPT_TEMPLATE.format(raw_concepts_json=combined_json)

    for attempt in range(3):
        try:
            content = llm.get_response(usr_msg=usr_msg)
            content = content.strip()

            if "```" in content:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
                if match:
                    content = match.group(1).strip()

            cleaned = json.loads(content)
            if isinstance(cleaned, list):
                return [c.strip() for c in cleaned if isinstance(c, str) and c.strip()]
        except Exception as e:
            print(f"  [WARN] Batch retry {attempt+1}/3 failed: {e}")
            time.sleep(1)

    return []


def clean_concepts(
    input_file: Path,
    output_file: Path,
    batch_size: int = 50,
    limit: int = 0,
) -> list[str]:
    print("=" * 60)
    print("  Subject-Independent LLM Concept Cleaner")
    print("=" * 60)
    print(f"[INPUT]  File : {input_file}")
    print(f"[OUTPUT] File : {output_file}")
    print(f"[CONFIG] Batch Size : {batch_size}")

    if not input_file.exists():
        raise FileNotFoundError(f"Input concepts file not found: {input_file}")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "concepts" in data:
        raw_list = data["concepts"]
    elif isinstance(data, list):
        raw_list = data
    else:
        raise ValueError("Invalid JSON format in input concepts file.")

    if limit > 0:
        raw_list = raw_list[:limit]

    total_items = len(raw_list)
    print(f"[INFO] Total Raw Concepts to Clean: {total_items}")

    llm = LLM(
        sys_msg="You are an expert AI editor specialized in technical terminology refinement.",
        temperature=0.0,
    )

    cleaned_set: set[str] = set()
    total_batches = (total_items + batch_size - 1) // batch_size

    for i in range(0, total_items, batch_size):
        batch_num = (i // batch_size) + 1
        batch_raw = raw_list[i : i + batch_size]

        print(f"[PROGRESS] Cleaning batch {batch_num}/{total_batches} ({len(batch_raw)} items)...", end="\r", flush=True)

        batch_cleaned = clean_concepts_batch(llm, batch_raw)
        for term in batch_cleaned:
            cleaned_set.add(term)

        time.sleep(0.2)

    sorted_cleaned = sorted(list(cleaned_set), key=lambda s: s.lower())

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"concepts": sorted_cleaned}, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Cleaned {total_items} raw concepts into {len(sorted_cleaned)} unique technical terms!")
    print(f"[OUTPUT] Saved to: {output_file}")
    print("=" * 60)

    return sorted_cleaned


def main():
    parser = argparse.ArgumentParser(
        description="LLM-based subject-independent concept term cleaner."
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to input concepts JSON file (default: outputs/data/concepts.json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to output clean concepts JSON file (default: outputs/data/clean_concepts.json)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=50,
        help="Batch size per LLM request (default: 50)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="Limit number of raw concepts to process (0 = process all)"
    )

    args = parser.parse_args()

    clean_concepts(
        input_file=args.input,
        output_file=args.output,
        batch_size=args.batch_size,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
