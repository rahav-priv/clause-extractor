import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Use absolute path so this works regardless of which directory python is launched from
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE, override=True)

from database import Base, engine, get_db
from extractor import extract_clauses
from models import Clause, Contract, Entity
from pdf_parser import extract_text_from_pdf

# ── Create tables ────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Contract Intelligence API",
    version="1.0.0",
    description=(
        "Extracts and classifies clauses from legal contracts using Claude AI. "
        "Upload a PDF to receive a structured breakdown of contract type, clauses, and entities. "
        "Interactive docs available at /docs."
    ),
)

PORT = int(os.getenv("CLAUSE_EXTRACTOR_PORT", 6363))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class EntityResponse(BaseModel):
    id: int
    entity_name: str
    value: Optional[Any] = None
    confidence: Optional[float] = None
    evidence: list[str] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ClauseResponse(BaseModel):
    id: int
    clause_type: str
    span_start: int
    span_end: int
    confidence: Optional[float] = None
    evidence: list[str] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)
    entities: list[EntityResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ContractSummaryResponse(BaseModel):
    id: int
    filename: str
    upload_date: Optional[str] = None
    contract_type: Optional[str] = None
    clause_count: int

    model_config = {"from_attributes": True}


class ContractFullResponse(BaseModel):
    id: int
    filename: str
    upload_date: Optional[str] = None
    raw_text: str
    contract_type: Optional[str] = None
    contract_type_confidence: Optional[float] = None
    contract_type_evidence: list[str] = Field(default_factory=list)
    contract_type_ambiguity_flags: list[str] = Field(default_factory=list)
    clauses: list[ClauseResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PaginatedExtractionsResponse(BaseModel):
    items: list[ContractSummaryResponse]
    total: int
    page: int
    limit: int
    pages: int


class DeleteResponse(BaseModel):
    message: str
    id: int


# ── Serialisers ──────────────────────────────────────────────────────────────
def _parse_json_list(val: str | None) -> list:
    """Safely parse a JSON-encoded list column."""
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


def _parse_json_value(val: str | None):
    """Safely parse a JSON-encoded value column."""
    if val is None:
        return None
    try:
        return json.loads(val)
    except Exception:
        return val


def contract_summary(c: Contract) -> dict:
    return {
        "id": c.id,
        "filename": c.filename,
        "upload_date": c.upload_date.isoformat() if c.upload_date else None,
        "contract_type": c.contract_type,
        "clause_count": len(c.clauses),
    }


def entity_dict(e: Entity) -> dict:
    return {
        "id": e.id,
        "entity_name": e.entity_name,
        "value": _parse_json_value(e.value_json),
        "confidence": e.confidence,
        "evidence": _parse_json_list(e.evidence),
        "ambiguity_flags": _parse_json_list(e.ambiguity_flags),
    }


def clause_dict(cl: Clause) -> dict:
    return {
        "id": cl.id,
        "clause_type": cl.clause_type,
        "span_start": cl.span_start,
        "span_end": cl.span_end,
        "confidence": cl.confidence,
        "evidence": _parse_json_list(cl.evidence),
        "ambiguity_flags": _parse_json_list(cl.ambiguity_flags),
        "entities": [entity_dict(e) for e in cl.entities],
    }


def contract_full(c: Contract) -> dict:
    return {
        "id": c.id,
        "filename": c.filename,
        "upload_date": c.upload_date.isoformat() if c.upload_date else None,
        "raw_text": c.raw_text,
        "contract_type": c.contract_type,
        "contract_type_confidence": c.contract_type_confidence,
        "contract_type_evidence": _parse_json_list(c.contract_type_evidence),
        "contract_type_ambiguity_flags": _parse_json_list(c.contract_type_ambiguity_flags),
        "clauses": [clause_dict(cl) for cl in c.clauses],
    }


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get(
    "/api/extractions",
    response_model=PaginatedExtractionsResponse,
    summary="List all contracts",
    description="Returns a paginated list of all uploaded contracts with their metadata.",
)
def list_extractions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    total = db.query(Contract).count()
    contracts = (
        db.query(Contract)
        .order_by(Contract.upload_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [contract_summary(c) for c in contracts],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@app.get(
    "/api/extractions/{document_id}",
    response_model=ContractFullResponse,
    summary="Get a contract with its clauses",
    description="Returns the full contract including raw text, all extracted clauses, and entities.",
    responses={404: {"description": "Contract not found"}},
)
def get_extraction(document_id: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == document_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return contract_full(c)


@app.post(
    "/api/extract",
    status_code=201,
    response_model=ContractFullResponse,
    summary="Upload and extract a contract",
    description="Accepts a PDF file, extracts its text, classifies clauses using Claude, and persists the results.",
    responses={
        400: {"description": "Unsupported file type"},
        413: {"description": "File too large (max 20 MB)"},
        422: {"description": "PDF could not be parsed or contains no extractable text"},
        500: {"description": "Claude extraction error"},
    },
)
async def extract_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = file.filename or "unknown.pdf"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("docx", "doc"):
        raise HTTPException(status_code=400, detail="DOCX files are not implemented yet")
    if ext != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    # Extract text
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {exc}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="PDF contains no extractable text (possibly a scanned image). "
                   "OCR is not yet supported.",
        )

    # Extract clauses via Claude
    try:
        extraction = extract_clauses(raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction error: {exc}")

    # Persist
    ct = extraction.get("contract_type", {})
    contract = Contract(
        filename=filename,
        upload_date=datetime.utcnow(),
        raw_text=raw_text,
        contract_type=ct.get("label"),
        contract_type_confidence=ct.get("confidence"),
        contract_type_evidence=json.dumps(ct.get("evidence", [])),
        contract_type_ambiguity_flags=json.dumps(ct.get("ambiguity_flags", [])),
    )
    db.add(contract)
    db.flush()

    for cl_data in extraction.get("clauses", []):
        clause = Clause(
            contract_id=contract.id,
            clause_type=cl_data.get("clause_type", "Other"),
            span_start=cl_data.get("span_start", 0),
            span_end=cl_data.get("span_end", 0),
            confidence=cl_data.get("confidence"),
            evidence=json.dumps(cl_data.get("evidence", [])),
            ambiguity_flags=json.dumps(cl_data.get("ambiguity_flags", [])),
        )
        db.add(clause)
        db.flush()

        for entity_name, entity_data in cl_data.get("entities", {}).items():
            if not isinstance(entity_data, dict):
                continue
            entity = Entity(
                clause_id=clause.id,
                entity_name=entity_name,
                value_json=json.dumps(entity_data.get("value")),
                confidence=entity_data.get("confidence"),
                evidence=json.dumps(entity_data.get("evidence", [])),
                ambiguity_flags=json.dumps(entity_data.get("ambiguity_flags", [])),
            )
            db.add(entity)

    db.commit()
    db.refresh(contract)
    return contract_full(contract)


@app.delete(
    "/api/extractions/{document_id}",
    response_model=DeleteResponse,
    summary="Delete a contract",
    description="Permanently deletes a contract and all its associated clauses and entities.",
    responses={404: {"description": "Contract not found"}},
)
def delete_extraction(document_id: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == document_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Extraction not found")
    db.delete(c)
    db.commit()
    return {"message": "Extraction deleted", "id": document_id}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
