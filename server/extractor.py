"""Clause extraction via Anthropic Claude API.

The contract is pre-split into numbered sections (paragraphs) on the server.
Claude receives the sections with integer indices and returns which index maps
to which clause type — no excerpt matching, no span guessing.  Spans are exact
because they come from the pre-parser, not from Claude.
"""
import json
import os
import re

import anthropic
from dotenv import load_dotenv
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE, override=True)

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CONTRACT_TYPES = [
    "NDA", "MSA", "SOW", "Purchasing", "Employment", "Contractor",
    "SaaS/License", "DPA", "Partnership", "Unknown_Type",
]

CLAUSE_TYPES = [
    # Parties & dates
    "Parties", "Agreement Date", "Effective Date", "Expiration Date",
    # Purpose & scope
    "Purpose", "Scope of Services", "Statements of Work", "Delivery",
    # Commercial
    "Governing Law", "Payment Terms", "Price Restrictions", "Most Favored Nation",
    # Term & termination
    "Renewal Term", "Termination for Convenience", "Post-Termination Services",
    # Liability & indemnity
    "Indemnification", "Cap on Liability", "Uncapped Liability", "Warranties",
    # Risk & compliance
    "Force Majeure",
    # Confidentiality — broken into distinct sub-types for NDA-heavy contracts
    "Confidentiality / NDA",                 # general obligation to keep info secret
    "Definition of Confidential Information", # what counts as confidential
    "Exclusions from Confidential Information", # carve-outs (public domain, independently developed, etc.)
    "Obligations of Receiving Party",        # specific duties: no disclosure, limited use, etc.
    "Data Privacy / GDPR",
    # IP
    "IP Ownership Assignment", "License Grant", "Source Code Escrow",
    # Restrictions
    "Non-Compete", "No-Solicit of Employees",
    # Governance
    "Dispute Resolution", "Change of Control", "Audit Rights", "SLA / Service Levels",
    # Remedies & enforcement
    "Remedies", "Injunctive Relief",
    # Boilerplate (present in almost every contract)
    "Entire Agreement", "Amendment", "Severability", "Notices", "Assignment", "Waiver",
    "Unknown_Type",
]

SYSTEM_PROMPT = (
    "You are a contract intelligence system that analyzes legal contracts and "
    "extracts structured information. You always return valid JSON with no "
    "additional text, markdown, or code blocks."
)


def _parse_sections(text: str) -> list[dict]:
    """Split the contract into sections for AI classification.

    Strategy
    --------
    - **Numbered headings** (e.g. "1. Title", "2.1 Sub-clause") → kept as a
      complete unit (heading + all body text until the next numbered heading).
    - **Unnumbered content** (preamble before section 1, or contracts with no
      numbering at all) → further split by blank lines so each paragraph becomes
      its own section.  A prose contract gets the same granularity as a numbered
      one.

    Returns a list of dicts  { index, heading, span_start, span_end }  in
    document order.  Spans are exact character offsets into `text`.
    """
    heading_re = re.compile(r'^\d+(?:\.\d+)*\.?\s+\S[^\n]*', re.MULTILINE)
    matches = list(heading_re.finditer(text))

    sections: list[dict] = []

    def _add_paragraphs(blk_start: int, blk_end: int) -> None:
        """Split unnumbered content by individual lines.

        Unnumbered preamble text (titles, parties, dates) typically has no blank
        lines between its lines, so we split on every newline to give each line
        its own section.  This lets Claude assign the document title, the
        agreement-date sentence, and each party line independently.
        Sections produced here are flagged numbered=False so the merge step
        knows they are candidates for combining.
        """
        block = text[blk_start:blk_end]
        pos = 0
        for m in re.finditer(r'\n', block):
            chunk = block[pos:m.start()]
            if chunk.strip():
                sections.append({
                    "index": len(sections),
                    "heading": chunk.strip()[:120],
                    "span_start": blk_start + pos,
                    "span_end": blk_start + m.start(),
                    "numbered": False,
                })
            pos = m.end()
        tail = block[pos:]
        if tail.strip():
            sections.append({
                "index": len(sections),
                "heading": tail.strip()[:120],
                "span_start": blk_start + pos,
                "span_end": blk_end,
                "numbered": False,
            })

    # ── Unnumbered preamble ───────────────────────────────────────────────────
    first_start = matches[0].start() if matches else len(text)
    if first_start > 0:
        _add_paragraphs(0, first_start)

    # ── Numbered sections (kept whole) ───────────────────────────────────────
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = match.group().split('\n')[0].strip()[:120]
        sections.append({
            "index": len(sections),
            "heading": heading,
            "span_start": start,
            "span_end": end,
            "numbered": True,   # never merged with adjacent sections
        })

    # ── Fallback: no structure found → whole document ─────────────────────────
    if not sections:
        sections.append({
            "index": 0,
            "heading": "(Full document)",
            "span_start": 0,
            "span_end": len(text),
        })

    return sections


def _build_prompt(contract_text: str, sections: list[dict]) -> str:
    ct_list = ", ".join(CONTRACT_TYPES)
    cl_list = ", ".join(CLAUSE_TYPES)

    # Each section is shown with its full text so Claude can classify and extract entities
    section_blocks = []
    for s in sections:
        body = contract_text[s["span_start"]:s["span_end"]].strip()
        section_blocks.append(f'[{s["index"]}] {s["heading"]}\n{body}')

    sections_block = "\n\n---\n\n".join(section_blocks)

    return f"""Analyze the following contract sections and return a single JSON object.

CONTRACT SECTIONS:
{sections_block}

REQUIRED OUTPUT STRUCTURE:
{{
  "contract_type": {{
    "label": "<one of: {ct_list}>",
    "confidence": <float 0.0–1.0>,
    "evidence": ["verbatim phrase 1", "verbatim phrase 2"],
    "ambiguity_flags": []
  }},
  "clauses": [
    {{
      "section_index": <integer — the [index] of the section above>,
      "clause_type": "<one of: {cl_list}>",
      "confidence": <float 0.0–1.0>,
      "evidence": ["verbatim phrase"],
      "ambiguity_flags": [],
      "entities": {{
        "<entity_name>": {{
          "value": <string | number | object>,
          "confidence": <float 0.0–1.0>,
          "evidence": ["verbatim phrase"],
          "ambiguity_flags": []
        }}
      }}
    }}
  ]
}}

RULES:
1. Return ONLY the JSON object — no markdown, no explanation.
2. Use section_index to reference which section each clause comes from.
3. A CLAUSE is a self-contained provision that sets a rule, right, obligation, or condition
   between the parties. Only include sections that meet this definition.
4. Do NOT include sections that are not clauses — document titles
   (e.g. "NON-DISCLOSURE AGREEMENT (NDA)"), signature blocks, blank separators, or any text
   that does not itself impose a rule, right, obligation, or condition.
5. Use "Unknown_Type" ONLY for sections that ARE clauses (meet rule 3) but do not match any of the
   listed clause types. Do not use "Unknown_Type" for non-clause text — omit those sections entirely.
6. Each section should appear at most once in the clauses list.
7. confidence is your estimated probability (0.0–1.0) that the label is correct.
8. evidence must be 1–3 phrases copied verbatim (or near-verbatim) from the contract.
9. For entities extract all structured data: amounts (normalize to numeric + ISO currency),
   dates (ISO 8601), durations, percentages, party names, jurisdiction names, etc.
10. For NDA contracts use the specific confidentiality sub-types rather than the generic
    "Confidentiality / NDA" when a section clearly matches one:
    - "Definition of Confidential Information" for sections that define what is confidential
    - "Exclusions from Confidential Information" for carve-outs / exceptions
    - "Obligations of Receiving Party" for sections listing the recipient's duties"""


def extract_clauses(contract_text: str) -> dict:
    """Call Claude to classify sections and extract entities.

    Returns a dict with keys:
        contract_type: { label, confidence, evidence, ambiguity_flags }
        clauses: [ { clause_type, span_start, span_end, confidence, evidence,
                     ambiguity_flags, entities: { name: {...} } } ]

    span_start / span_end are exact character offsets from the pre-parser —
    they always cover a complete paragraph, never split mid-sentence.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to the .env file in the project root."
        )

    # ── Pre-parse into sections (spans are exact, no guessing needed) ────────
    sections = _parse_sections(contract_text)
    section_map = {s["index"]: s for s in sections}

    message = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(contract_text, sections)}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
        else:
            raise ValueError(f"Could not parse JSON from Claude response: {raw[:300]}")

    # ── Map section_index → exact span from the pre-parser ───────────────────
    clauses = result.get("clauses", [])
    for clause in clauses:
        idx = clause.pop("section_index", None)
        section = section_map.get(idx)
        if section:
            clause["span_start"] = section["span_start"]
            clause["span_end"] = section["span_end"]
            clause["_numbered"] = section.get("numbered", False)
        else:
            clause["span_start"] = 0
            clause["span_end"] = 0
            clause["_numbered"] = False

    # ── Sort into document order ──────────────────────────────────────────────
    clauses.sort(key=lambda c: c.get("span_start", 0))

    # ── Merge consecutive clauses of the same type ────────────────────────────
    # Only merges unnumbered preamble lines (e.g. "Client:" + "Service Provider:" → Parties,
    # or a sentence wrapped across two PDF lines).
    #
    # Never merges if:
    #   - Either clause comes from a numbered section  (numbered=True)
    #   - There is a blank line in the text gap between the two spans
    if clauses:
        merged: list[dict] = [clauses[0]]
        for clause in clauses[1:]:
            prev = merged[-1]
            same_type = clause["clause_type"] == prev["clause_type"]
            either_numbered = prev.get("_numbered", False) or clause.get("_numbered", False)
            gap = contract_text[prev.get("span_end", 0): clause.get("span_start", 0)]
            has_blank_line = bool(re.search(r'\n[ \t]*\n', gap))
            adjacent = clause.get("span_start", 0) <= prev.get("span_end", 0) + 2

            if same_type and adjacent and not either_numbered and not has_blank_line:
                # Extend the previous clause to cover this one too
                prev["span_end"] = clause["span_end"]
                # Merge evidence (deduplicate, keep up to 3)
                seen: set[str] = set(prev.get("evidence", []))
                for e in clause.get("evidence", []):
                    if e not in seen and len(prev.get("evidence", [])) < 3:
                        prev.setdefault("evidence", []).append(e)
                        seen.add(e)
                # Merge entities (later section wins on key conflict)
                prev.setdefault("entities", {}).update(clause.get("entities", {}))
            else:
                merged.append(clause)

        # Strip internal bookkeeping flag before returning
        for c in merged:
            c.pop("_numbered", None)
        result["clauses"] = merged

    return result
