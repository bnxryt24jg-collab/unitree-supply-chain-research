"""Machine-readable contract for the research dataset."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EntityType(str, Enum):
    COMPANY = "company"
    FUND = "fund"
    PERSON = "person"
    GOVERNMENT = "government"
    EDUCATION = "education_or_research"


class ListedStatus(str, Enum):
    LISTED = "listed"
    UNLISTED = "unlisted"


class RelationType(str, Enum):
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    PARTNER = "partner"
    INVESTOR_OR_INVESTEE = "investor_or_investee"
    PEER = "peer"


class RelationSubtype(str, Enum):
    CONFIRMED_SUPPLIER = "confirmed_supplier"
    CANDIDATE_SUPPLIER = "candidate_supplier"
    DIRECT_BUYER = "direct_buyer"
    PARENT_GROUP = "parent_group"
    END_USER = "end_user"
    REJECTED_BID = "rejected_bid"
    DIRECT_SHAREHOLDER = "direct_shareholder"
    FUND_LOOKTHROUGH = "fund_lookthrough"
    STRATEGIC_PLACEMENT = "strategic_placement"
    FORMAL_AGREEMENT = "formal_agreement"
    GOVERNMENT_AGREEMENT = "government_agreement"
    ECOSYSTEM_COMPATIBILITY = "ecosystem_compatibility"
    FINANCIAL_COMPARABLE = "financial_comparable"
    PRODUCT_COMPETITOR = "product_competitor"
    TECHNOLOGY_BENCHMARK = "technology_benchmark"


class Status(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    UNKNOWN = "unknown"


class ClaimSupport(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    UNSUPPORTED = "unsupported"
    CONFLICTED = "conflicted"


class RelevanceTier(str, Enum):
    CORE = "core"
    SUPPLEMENTARY = "supplementary"
    CANDIDATE = "candidate"


class Uncertainty(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceType(str, Enum):
    PRIMARY_REGULATORY = "primary_regulatory"
    PRIMARY_OFFICIAL = "primary_official"
    PRIMARY_PROCUREMENT = "primary_procurement"
    AUTHORITATIVE_MEDIA = "authoritative_media"
    GENERAL_MEDIA = "general_media"
    COMMERCIAL_DATABASE = "commercial_database"
    INDUSTRY_RESEARCH = "industry_research"


class EvidenceRef(BaseModel):
    source_type: SourceType
    source_name: str
    url: str
    published_date: date | None = None
    retrieved_date: date = Field(default=date(2026, 9, 22))
    evidence_locator: str
    origin_id: str
    note: str | None = None


class ConfidenceBreakdown(BaseModel):
    direct_support: float = Field(ge=0, le=100)
    source_authority: float = Field(ge=0, le=100)
    independent_corroboration: float = Field(ge=0, le=100)
    entity_direction_certainty: float = Field(ge=0, le=100)
    timeliness: float = Field(ge=0, le=100)
    weighted_score: float = Field(ge=0, le=100)
    applied_caps: list[str] = Field(default_factory=list)
    final_score: float = Field(ge=0, le=100)


class Relationship(BaseModel):
    relationship_id: str
    subject_entity_id: str
    object_entity_id: str
    relation_type: RelationType
    relation_subtype: RelationSubtype
    status: Status
    claim_support: ClaimSupport
    effective_start: date | None = None
    effective_end: date | None = None
    is_indirect: bool = False
    uncertainty: Uncertainty
    entity_direction_certainty: float = Field(ge=0, le=100)
    natural_statement: str
    evidence: list[EvidenceRef] = Field(min_length=1)
    relevance_tier: RelevanceTier
    confidence_score: float | None = Field(default=None, ge=0, le=100)
    confidence_breakdown: ConfidenceBreakdown | None = None
    needs_human_validation: bool = False

    @model_validator(mode="after")
    def validate_claim_semantics(self) -> "Relationship":
        if self.status == Status.FACT and self.claim_support in {
            ClaimSupport.UNSUPPORTED,
            ClaimSupport.CONFLICTED,
        }:
            raise ValueError("fact requires direct or indirect claim support")
        if self.claim_support == ClaimSupport.UNSUPPORTED and self.relevance_tier != RelevanceTier.CANDIDATE:
            raise ValueError("unsupported claims must use candidate relevance tier")
        if self.relevance_tier == RelevanceTier.CORE and self.claim_support in {
            ClaimSupport.UNSUPPORTED,
            ClaimSupport.CONFLICTED,
        }:
            raise ValueError("core relations require resolved supporting evidence")
        return self


class Entity(BaseModel):
    entity_id: str
    name: str
    name_en: str | None = None
    entity_type: EntityType = EntityType.COMPANY
    listed: ListedStatus
    exchange: str | None = None
    ticker: str | None = None
    unified_social_credit_code: str | None = None
    aliases: list[str] = Field(default_factory=list)
    role_in_graph: str
    notes: str | None = None


class SupplyChainGraph(BaseModel):
    meta: dict
    entities: list[Entity]
    relationships: list[Relationship]
