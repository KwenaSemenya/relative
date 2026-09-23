"""SQLAlchemy schema.

Claims, proof points and evidence requests carry short ids that are unique
within their kit ("t1", "pp_hardware") rather than globally, so a kit reads the
same in the database as it does in the API payload. That makes their primary
keys composite.
"""

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Narrative(Base):
    """One row. Seeded from HQ and never edited in the product."""

    __tablename__ = "narrative"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    label: Mapped[str] = mapped_column(Text)
    sensitive_reviewer: Mapped[str] = mapped_column(Text)
    never_say: Mapped[list[str]] = mapped_column(ARRAY(Text))

    pillars: Mapped[list["Pillar"]] = relationship(
        back_populates="narrative", order_by="Pillar.ordinal", lazy="selectin"
    )


class Pillar(Base):
    __tablename__ = "pillar"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    narrative_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("narrative.id", ondelete="CASCADE")
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)

    narrative: Mapped[Narrative] = relationship(back_populates="pillars")


class Kit(Base):
    __tablename__ = "kit"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    brief: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(Text)
    sensitive_market: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    proof_points: Mapped[list["ProofPoint"]] = relationship(
        back_populates="kit",
        order_by="ProofPoint.ordinal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="kit",
        order_by="Claim.ordinal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    evidence_requests: Mapped[list["EvidenceRequest"]] = relationship(
        back_populates="kit",
        order_by="EvidenceRequest.ordinal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ProofPoint(Base):
    __tablename__ = "proof_point"

    kit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("kit.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

    kit: Mapped[Kit] = relationship(back_populates="proof_points")


class Claim(Base):
    __tablename__ = "claim"
    __table_args__ = (
        ForeignKeyConstraint(
            ["kit_id", "evidence_proof_point_id"],
            ["proof_point.kit_id", "proof_point.id"],
            ondelete="SET NULL",
        ),
        # A claim cites exactly one source, or none at all. Citing nothing is
        # why a claim gets flagged, so the two must agree.
        CheckConstraint(
            "(evidence_kind = 'proof_point' AND evidence_proof_point_id IS NOT NULL)"
            " OR (evidence_kind = 'pillar' AND pillar_id IS NOT NULL)"
            " OR (evidence_kind IS NULL AND evidence_proof_point_id IS NULL)",
            name="claim_evidence_consistent",
        ),
        CheckConstraint(
            "(flag_state = 'flagged') = (flag_reason IS NOT NULL)",
            name="claim_flag_has_reason",
        ),
    )

    kit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("kit.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(16), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)

    # The pillar this claim serves. Always recorded, even when the claim is
    # flagged and cites nothing.
    pillar_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("pillar.id", ondelete="RESTRICT"), nullable=True
    )

    evidence_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_proof_point_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    flag_state: Mapped[str] = mapped_column(String(16), default="clean")
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_state: Mapped[str] = mapped_column(String(16), default="pending")
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    kit: Mapped[Kit] = relationship(back_populates="claims")


class ClaudeCall(Base):
    """Every Claude call the product makes, kept so it can be read back.

    `kit_id` is null when the call belongs to a request that never produced a
    kit — a refused brief is the case that most needs a record, so the log
    cannot depend on a kit existing. `run_id` groups the calls of one request,
    which is what makes a refusal retrievable at all.
    """

    __tablename__ = "claude_call"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    kit_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kit.id", ondelete="CASCADE"), nullable=True, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(Text)
    system: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSONB)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class EvidenceRequest(Base):
    __tablename__ = "evidence_request"

    kit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("kit.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    need: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)

    kit: Mapped[Kit] = relationship(back_populates="evidence_requests")
