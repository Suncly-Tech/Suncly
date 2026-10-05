"""Request and response bodies of the HTTP API (docs/API.md).

Field names are the data model's. No body ever carries an organization id,
an approver or a reviewer: those come from the URL and the verified token.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from suncly.domain.behavioral import BehavioralSuite
from suncly.domain.contract_file import ContractFile
from suncly.domain.models import AttestationTrigger, DecisionOutcome, RiskLevel
from suncly.domain.policy import PolicyConfiguration
from suncly.domain.tenancy import CredentialReference, Role

JsonObject = dict[str, Any]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateOrganization(Body):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=200)


class AddMember(Body):
    subject: str = Field(min_length=1, max_length=256)
    email: str | None = Field(default=None, max_length=320)
    role: Role


class RegisterAgent(Body):
    name: str = Field(min_length=1, max_length=200)
    card_url: str = Field(min_length=1, max_length=2048)
    risk_level: RiskLevel = RiskLevel.HIGH
    owner: str = Field(default="unspecified", min_length=1, max_length=200)
    sandbox_declared: bool
    sandbox_idempotent: bool = False
    credential: CredentialReference = Field(
        default_factory=lambda: CredentialReference(provider="none")
    )
    bring_your_own_model_key: bool = False


class DraftContract(Body):
    source: Literal["deterministic", "model", "suite", "contract_file"] = "deterministic"
    suite: BehavioralSuite | None = None
    contract_file: ContractFile | None = None


class StartAttestation(Body):
    registration_id: UUID
    contract_id: UUID
    runs: int = Field(default=5, ge=1, le=200)
    budget_limit: Decimal | None = Field(default=None, ge=0)
    trigger: Literal["ci", "manual"] = "manual"

    @property
    def trigger_value(self) -> AttestationTrigger:
        return AttestationTrigger(self.trigger)


class ResolveDecision(Body):
    outcome: DecisionOutcome
    rationale: str = Field(min_length=20, max_length=5000)


class CreatePolicy(Body):
    configuration: PolicyConfiguration


class SetSpendingLimit(Body):
    period_limit_minor: int = Field(ge=0)


class StartCheckout(Body):
    plan_id: str = Field(min_length=1, max_length=64)


class CreateSchedule(Body):
    registration_id: UUID
    interval_hours: int = Field(ge=1, le=24 * 90)
    runs: int = Field(default=5, ge=1, le=200)
    budget_limit: Decimal = Field(ge=0)


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str = ""
    next_step: str = ""
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
