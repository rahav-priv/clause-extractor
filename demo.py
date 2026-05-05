"""
Contract Intelligence — End-to-End Demo
----------------------------------------
Uploads a PDF contract to the running server, extracts clauses via Claude,
and prints a structured summary of the results.

Usage:
    python demo.py                              # uses test_contracts/msa_1.pdf
    python demo.py test_contracts/nda_1.pdf
    python demo.py path/to/any_contract.pdf
"""

import sys
import json
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing dependency: pip install requests")
    sys.exit(1)

API_BASE = "http://localhost:6363"
DEFAULT_PDF = Path("test_contracts/msa_1.pdf")

CONFIDENCE_COLORS = {
    "high":   "\033[92m",   # green
    "medium": "\033[93m",   # yellow
    "low":    "\033[91m",   # red
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "cyan":   "\033[96m",
    "blue":   "\033[94m",
}

def colorize(text, color):
    return f"{CONFIDENCE_COLORS.get(color, '')}{text}{CONFIDENCE_COLORS['reset']}"

def confidence_label(score):
    if score is None:
        return ""
    pct = int(score * 100)
    color = "high" if pct >= 85 else "medium" if pct >= 65 else "low"
    return colorize(f"{pct}%", color)

def print_separator(char="─", width=60):
    print(colorize(char * width, "dim"))

def check_server():
    try:
        r = requests.get(f"{API_BASE}/api/extractions", timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def upload_contract(pdf_path: Path) -> dict:
    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"{API_BASE}/api/extract",
            files={"file": (pdf_path.name, f, "application/pdf")},
            timeout=120,
        )
    if response.status_code != 201:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        print(f"Upload failed ({response.status_code}): {detail}")
        sys.exit(1)
    return response.json()

def print_entity(name, data, indent=6):
    value = data.get("value")
    confidence = data.get("confidence")
    evidence = data.get("evidence", [])

    value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
    conf_str = f"  {confidence_label(confidence)}" if confidence is not None else ""
    print(f"{' ' * indent}{colorize(name, 'cyan')}: {value_str}{conf_str}")

    if evidence:
        for phrase in evidence[:1]:
            print(f"{' ' * (indent + 2)}{colorize(repr(phrase), 'dim')}")

def run_demo(pdf_path: Path):
    print()
    print(colorize("═" * 60, "blue"))
    print(colorize("  Contract Intelligence — End-to-End Demo", "bold"))
    print(colorize("═" * 60, "blue"))
    print()

    # Check server
    print(f"  Checking server at {API_BASE} ...", end=" ", flush=True)
    if not check_server():
        print(colorize("OFFLINE", "low"))
        print("\n  Start the backend first:")
        print("    .\\docker_run.ps1")
        sys.exit(1)
    print(colorize("OK", "high"))

    # Upload
    print(f"  Uploading: {colorize(str(pdf_path), 'cyan')}")
    print()
    start = time.time()
    result = upload_contract(pdf_path)
    elapsed = time.time() - start

    # Contract type
    ct_label = result.get("contract_type", "Unknown")
    ct_conf = result.get("contract_type_confidence")
    ct_evidence = result.get("contract_type_evidence", [])
    clauses = result.get("clauses", [])

    print_separator("═")
    print(f"  File:             {colorize(result.get('filename', pdf_path.name), 'bold')}")
    print(f"  Contract Type:    {colorize(ct_label, 'bold')}  {confidence_label(ct_conf)}")
    if ct_evidence:
        print(f"  Evidence:         {colorize(repr(ct_evidence[0]), 'dim')}")
    print(f"  Clauses found:    {colorize(str(len(clauses)), 'bold')}")
    print(f"  Extraction time:  {elapsed:.1f}s")
    print_separator("═")
    print()

    # Clauses
    for i, clause in enumerate(clauses, 1):
        clause_type = clause.get("clause_type", "Unknown")
        confidence = clause.get("confidence")
        evidence = clause.get("evidence", [])
        ambiguity = clause.get("ambiguity_flags", [])
        entities = clause.get("entities", [])

        print(f"  {colorize(str(i).rjust(2), 'dim')}  {colorize(clause_type, 'bold')}  {confidence_label(confidence)}")

        if evidence:
            print(f"      {colorize(repr(evidence[0]), 'dim')}")

        if ambiguity:
            print(f"      {colorize('⚠ ' + ambiguity[0], 'medium')}")

        if entities:
            for entity in entities:
                print_entity(entity.get("entity_name", ""), entity)

        print()

    # Summary
    print_separator()
    print(f"  Done. Contract ID: {colorize(str(result.get('id')), 'cyan')}")
    print(f"  View in UI: {colorize('http://localhost:5173', 'blue')}")
    contract_id = result.get('id')
    print(f"  Full JSON:  {colorize(f'{API_BASE}/api/extractions/{contract_id}', 'blue')}")
    print_separator()
    print()


if __name__ == "__main__":
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF

    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    if pdf_path.suffix.lower() != ".pdf":
        print(f"Expected a PDF file, got: {pdf_path.suffix}")
        sys.exit(1)

    run_demo(pdf_path)
