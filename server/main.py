import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
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
app = FastAPI(title="Contract Intelligence API", version="1.0.0")

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
def _j(val: str | None) -> list:
    """Safely parse a JSON-encoded list column."""
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


def _jv(val: str | None):
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
        "value": _jv(e.value_json),
        "confidence": e.confidence,
        "evidence": _j(e.evidence),
        "ambiguity_flags": _j(e.ambiguity_flags),
    }


def clause_dict(cl: Clause) -> dict:
    return {
        "id": cl.id,
        "clause_type": cl.clause_type,
        "span_start": cl.span_start,
        "span_end": cl.span_end,
        "confidence": cl.confidence,
        "evidence": _j(cl.evidence),
        "ambiguity_flags": _j(cl.ambiguity_flags),
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
        "contract_type_evidence": _j(c.contract_type_evidence),
        "contract_type_ambiguity_flags": _j(c.contract_type_ambiguity_flags),
        "clauses": [clause_dict(cl) for cl in c.clauses],
    }


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/api/extractions", response_model=PaginatedExtractionsResponse)
def list_extractions(
    page: int = 1,
    limit: int = 20,
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


@app.get("/api/extractions/{document_id}", response_model=ContractFullResponse)
def get_extraction(document_id: int, db: Session = Depends(get_db)):
    c = db.query(Contract).filter(Contract.id == document_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return contract_full(c)


@app.post("/api/extract", status_code=201, response_model=ContractFullResponse)
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


@app.delete("/api/extractions/{document_id}", response_model=DeleteResponse)
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
