from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    raw_text = Column(Text, nullable=False)
    contract_type = Column(String, nullable=True)
    contract_type_confidence = Column(Float, nullable=True)
    contract_type_evidence = Column(Text, nullable=True)        # JSON array string
    contract_type_ambiguity_flags = Column(Text, nullable=True) # JSON array string

    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    clause_type = Column(String, nullable=False)
    span_start = Column(Integer, nullable=True)
    span_end = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    evidence = Column(Text, nullable=True)        # JSON array string
    ambiguity_flags = Column(Text, nullable=True) # JSON array string

    contract = relationship("Contract", back_populates="clauses")
    entities = relationship("Entity", back_populates="clause", cascade="all, delete-orphan")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    clause_id = Column(Integer, ForeignKey("clauses.id"), nullable=False)
    entity_name = Column(String, nullable=False)
    value_json = Column(Text, nullable=True)      # JSON-encoded value
    confidence = Column(Float, nullable=True)
    evidence = Column(Text, nullable=True)        # JSON array string
    ambiguity_flags = Column(Text, nullable=True) # JSON array string

    clause = relationship("Clause", back_populates="entities")
