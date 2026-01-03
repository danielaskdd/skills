#!/usr/bin/env python3
"""
ABOUTME: Parses natural language audit criteria into structured JSON rules
ABOUTME: Supports LLM-based parsing for complex rules or simple keyword extraction
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Default audit rules that are always included
DEFAULT_RULES = [
    {
        "id": "R001",
        "description": "Check for typos and spelling errors",
        "severity": "medium",
        "category": "grammar",
        "keywords": []
    },
    {
        "id": "R002",
        "description": "Check for grammar errors and sentence structure issues",
        "severity": "medium",
        "category": "grammar",
        "keywords": []
    },
    {
        "id": "R003",
        "description": "Check for unclear references (ambiguous pronouns, vague terms like 'it', 'this', 'that' without clear antecedents)",
        "severity": "high",
        "category": "clarity",
        "keywords": ["it", "this", "that", "they", "those", "these"]
    },
    {
        "id": "R004",
        "description": "Check for logical inconsistencies (contradictions between stated facts and conclusions)",
        "severity": "high",
        "category": "logic",
        "keywords": []
    }
]


def parse_rules_with_llm(input_text: str, api_key: Optional[str] = None, start_id: int = 5) -> list:
    """
    Use LLM to parse natural language audit criteria into structured rules.

    Args:
        input_text: Natural language description of audit criteria
        api_key: API key for LLM service (Gemini or OpenAI)

    Returns:
        List of structured rule dictionaries
    """
    # Try Gemini first
    google_key = api_key or os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel("gemini-3-flash")

            prompt = f"""You are an audit rule parser. Convert the following natural language audit criteria into structured JSON rules.

Each rule should have:
- id: A unique identifier (e.g., "R005", "R006", ...)
- description: Clear description of what to check
- severity: "high", "medium", or "low"
- category: One of: "grammar", "clarity", "logic", "compliance", "format", "semantic_risk", "other"
- keywords: List of keywords that might indicate a violation (can be empty)

Input criteria:
{input_text}

Return ONLY a valid JSON array of rule objects. No explanation, just the JSON array.
"""
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Clean up response if needed
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            custom_rules = json.loads(response_text.strip())
            return custom_rules

        except ImportError:
            print("Warning: google-generativeai not installed. Trying OpenAI instead.", file=sys.stderr)
        except Exception as e:
            print(f"Warning: LLM parsing failed: {e}. Trying fallback.", file=sys.stderr)

    # Try OpenAI as fallback
    openai_key = api_key or os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)

            prompt = f"""You are an audit rule parser. Convert the following natural language audit criteria into structured JSON rules.

Each rule should have:
- id: A unique identifier (e.g., "R005", "R006", ...)
- description: Clear description of what to check
- severity: "high", "medium", or "low"
- category: One of: "grammar", "clarity", "logic", "compliance", "format", "semantic_risk", "other"
- keywords: List of keywords that might indicate a violation (can be empty)

Input criteria:
{input_text}

Return ONLY a valid JSON array of rule objects. No explanation, just the JSON array.
"""
            response = client.chat.completions.create(
                model="gpt-5.2",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            response_text = response.choices[0].message.content.strip()

            # Clean up response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            custom_rules = json.loads(response_text.strip())
            return custom_rules

        except ImportError:
            print("Warning: openai not installed. Trying simple parsing.", file=sys.stderr)
        except Exception as e:
            print(f"Warning: LLM parsing failed: {e}. Using simple parsing.", file=sys.stderr)

    # Fallback: Simple keyword-based parsing
    return parse_rules_simple(input_text, start_id=start_id)


def parse_rules_simple(input_text: str, start_id: int = 5) -> list:
    """
    Simple rule parsing without LLM.
    Extracts keywords and creates basic rules from input text.

    Args:
        input_text: Natural language description of audit criteria

    Returns:
        List of structured rule dictionaries
    """
    rules = []
    lines = input_text.strip().split('\n')

    rule_id = start_id

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common prefixes
        for prefix in ["- ", "* ", "• ", "check for ", "verify ", "ensure "]:
            if line.lower().startswith(prefix):
                line = line[len(prefix):]

        # Determine severity based on keywords
        severity = "medium"
        if any(word in line.lower() for word in ["critical", "must", "required", "mandatory"]):
            severity = "high"
        elif any(word in line.lower() for word in ["optional", "minor", "suggest"]):
            severity = "low"

        # Determine category
        category = "other"
        if any(word in line.lower() for word in ["spell", "typo", "grammar"]):
            category = "grammar"
        elif any(word in line.lower() for word in ["unclear", "ambiguous", "vague"]):
            category = "clarity"
        elif any(word in line.lower() for word in ["logic", "contradict", "inconsisten"]):
            category = "logic"
        elif any(word in line.lower() for word in ["compli", "legal", "regulat"]):
            category = "compliance"
        elif any(word in line.lower() for word in ["format", "style", "layout"]):
            category = "format"
        elif any(word in line.lower() for word in ["amount", "currency", "date", "number"]):
            category = "semantic_risk"

        rules.append({
            "id": f"R{rule_id:03d}",
            "description": line,
            "severity": severity,
            "category": category,
            "keywords": []
        })
        rule_id += 1

    return rules


def merge_rules(default_rules: list, custom_rules: list) -> list:
    """
    Merge default rules with custom rules, avoiding duplicates.

    Args:
        default_rules: List of default rule dictionaries
        custom_rules: List of custom rule dictionaries

    Returns:
        Merged list of rules
    """
    all_rules = list(default_rules)
    existing_descriptions = {r["description"].lower() for r in default_rules}

    for rule in custom_rules:
        if rule["description"].lower() not in existing_descriptions:
            all_rules.append(rule)
            existing_descriptions.add(rule["description"].lower())

    return all_rules


def main():
    parser = argparse.ArgumentParser(
        description="Parse natural language audit criteria into structured JSON rules"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Natural language audit criteria text"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="File containing audit criteria (one per line or paragraph)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="rules.json",
        help="Output JSON file path (default: rules.json)"
    )
    parser.add_argument(
        "--no-defaults",
        action="store_true",
        help="Don't include default rules"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM for advanced parsing (requires API key)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key for LLM service"
    )

    args = parser.parse_args()

    if args.llm:
        google_key = args.api_key or os.getenv("GOOGLE_API_KEY")
        openai_key = args.api_key or os.getenv("OPENAI_API_KEY")
        has_gemini = False
        has_openai = False
        try:
            import google.generativeai  # noqa: F401
            has_gemini = True
        except ImportError:
            pass
        try:
            import openai  # noqa: F401
            has_openai = True
        except ImportError:
            pass

        usable_gemini = bool(google_key and has_gemini)
        usable_openai = bool(openai_key and has_openai)

        if not usable_gemini and not usable_openai:
            if not (google_key or openai_key):
                print("Error: --llm requires GOOGLE_API_KEY or OPENAI_API_KEY (or --api-key).", file=sys.stderr)
            else:
                print("Error: No supported LLM client installed.", file=sys.stderr)
            print("Install one of:", file=sys.stderr)
            print("  pip install google-generativeai", file=sys.stderr)
            print("  pip install openai", file=sys.stderr)
            sys.exit(1)

    # Get input text
    input_text = ""
    if args.input:
        input_text = args.input
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        input_text = file_path.read_text(encoding="utf-8")

    # Parse custom rules
    custom_rules = []
    if input_text:
        start_id = 1 if args.no_defaults else 5
        if args.llm:
            custom_rules = parse_rules_with_llm(input_text, args.api_key, start_id=start_id)
        else:
            custom_rules = parse_rules_simple(input_text, start_id=start_id)

    # Merge with defaults
    if args.no_defaults:
        all_rules = custom_rules
    else:
        all_rules = merge_rules(DEFAULT_RULES, custom_rules)

    # Output
    output_data = {
        "version": "1.0",
        "total_rules": len(all_rules),
        "rules": all_rules
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Generated {len(all_rules)} rules:")
    for rule in all_rules:
        print(f"  [{rule['id']}] ({rule['severity']}) {rule['description'][:60]}...")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
