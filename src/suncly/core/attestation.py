"""The attestation use case: URL in, signed evidence and report out (schema §4).

This is the core library the CLI and the later HTTP API call (schema §6).
Every decision lives here or deeper; the CLI only parses arguments, answers
prompts and prints.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from suncly.core import signing
from suncly.core.cards import CardService, select_interface
from suncly.core.config import DEFAULT_BUDGET_FACTOR, Config
from suncly.core.contract_builder import (
    ContractService,
    contract_file_from_draft,
    draft_from_contract_file,
    require_test_cases,
    same_content,
    uncovered_skills,
)
from suncly.core.evidence import assemble_bundle, evidence_document_hash
from suncly.core.judge import JudgeService, model_judge_settings
from suncly.core.orchestrator import Orchestrator, OrchestratorSettings
from suncly.core.policy_engine import PolicyEngine, aggregate
from suncly.domain.card import ParsedCard
from suncly.domain.contract_file import ContractFile, render_contract_file
from suncly.domain.errors import ApprovalRequiredError, SandboxDeclarationMissingError
from suncly.domain.evidence import EvidenceBundle
from suncly.domain.models import (
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    Contract,
    Decision,
    RiskLevel,
    Run,
    TestCase,
)
from suncly.ports.card_fetcher import CardFetcher
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.drafter import (
    ContractDrafter,
    Draft,
    DraftSettings,
    DraftTestCase,
    NotTestableSkill,
)
from suncly.ports.model_judge import ModelJudge
from suncly.ports.progress import NoProgress, ProgressListener
from suncly.ports.report import ReportWriter
from suncly.ports.run_executor import RunExecutor
from suncly.ports.signer import Signer, SigningKeys
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage

#: Default ``agent.owner`` and ``agent.risk_level`` when the caller gives none
#: (OQ-P2, OQ-P5: NEEDS DECISION). ``high`` is the most restrictive level.
DEFAULT_OWNER = "unspecified"
DEFAULT_RISK_LEVEL = RiskLevel.HIGH

#: The proposals in effect, listed in every report (docs/IMPLEMENTATION_NOTES.md).
PROPOSALS_IN_EFFECT = (
    "OQ-A2: the sandbox is the endpoint the user declared with --sandbox; Suncly cannot verify it",
    (
        "OQ-A3: the Runner redacts its credential, Authorization and cookie headers and known "
        "token patterns before a transcript leaves it"
    ),
    (
        "OQ-A4: the Runner speaks A2A 1.0 over JSON-RPC, follows tasks by polling GetTask, uses no "
        "push notifications and never answers an interrupted state"
    ),
    "OQ-A7: card_hash is SHA-256 of the RFC 8785 form of the card without `signatures`",
    (
        "OQ-A8: signatures are Ed25519 over the RFC 8785 payload, encoded `ed25519:<base64url>`; "
        "signing_key_id is a SHA-256 fingerprint of the public key"
    ),
    "OQ-D1: cost is counted in attempts; every attempt costs 1, including retries",
    (
        "OQ-D3: run.attempt is the repetition number; (attestation_id, test_case_id, attempt) is "
        "unique"
    ),
    (
        "OQ-D7: input is {text} or {parts}; criteria hold the Layer 1 checks and the model "
        "checks for Layer 2, each with a name, the criterion, the answer shape and the pass "
        "rule (docs/API.md)"
    ),
    "OQ-D9: a card hash seen before reuses its card_version and its approved contract",
    (
        "OQ-D10: latency_ms runs from sending the message to the final task state; null without a "
        "response"
    ),
    "OQ-F3: an unreachable agent gives inconclusive runs; a timeout fails the latency check",
    "OQ-F5: a card that cannot be re-fetched at the end makes the attestation failed",
    "OQ-F7: failed and invalidated attestations are signed with no decision in the payload",
    "OQ-PO5: decision.policy_version is the placeholder 'unconfigured' until a policy exists",
    "OQ-R1: a minimal Orchestrator runs inside the process",
    (
        "OQ-R2: test cases come from the deterministic drafter or a contract file; no model is "
        "involved"
    ),
    "OQ-R6: the file report is the first version of the Report adapter",
)


class DraftPresentation(BaseModel):
    """What a human sees before approving a contract."""

    model_config = ConfigDict(frozen=True)

    card_name: str
    card_hash: str
    contract_version: int
    source: str
    test_cases: list[DraftTestCase]
    not_testable: list[NotTestableSkill]
    uncovered_skills: list[str]


ApprovalPrompt = Callable[[DraftPresentation], str | None]
"""Asks a human for approval; returns the approver's identifier, or ``None`` to refuse."""


@dataclass(frozen=True)
class AttestRequest:
    card_url: str
    sandbox_declared: bool
    runs: int
    budget_limit: Decimal | None = None
    owner: str = DEFAULT_OWNER
    risk_level: RiskLevel = DEFAULT_RISK_LEVEL
    approve_as: str | None = None
    approval_prompt: ApprovalPrompt | None = None
    contract_file: ContractFile | None = None
    export_draft: bool = False
    trigger: AttestationTrigger = AttestationTrigger.MANUAL


OutcomeKind = Literal["completed", "failed", "invalidated", "draft_exported"]


@dataclass(frozen=True)
class AttestOutcome:
    kind: OutcomeKind
    attestation: Attestation | None = None
    decision: Decision | None = None
    bundle: EvidenceBundle | None = None
    report_dir: Path | None = None
    exported_contract_file: str | None = None
    planned_runs: int = 0


@dataclass
class Services:
    """Everything the use case reaches the world through. Built once by the CLI."""

    config: Config
    store: EvidenceStore
    transcripts: TranscriptStorage
    fetcher: CardFetcher
    drafter: ContractDrafter
    executor: RunExecutor
    keys: SigningKeys
    clock: Clock
    ids: IdGenerator
    report_writer: ReportWriter
    progress: ProgressListener = field(default_factory=NoProgress)
    model_judge: ModelJudge | None = None
    """Layer 2's way to the pinned model; ``None`` when no judge endpoint is configured."""


class AttestationService:
    def __init__(self, services: Services) -> None:
        self._s = services

    def attest(self, request: AttestRequest) -> AttestOutcome:
        s = self._s
        if not request.sandbox_declared:
            raise SandboxDeclarationMissingError(
                "Nothing ran: the endpoint is not declared a sandbox or dry-run endpoint.",
                "Suncly only tests sandboxes, so that nothing real is booked, paid or deleted "
                "(DR-006).",
                "If this agent's endpoint is a sandbox, run again with --sandbox.",
            )
        # A judge configured only in part is refused before anything runs (DR-004).
        model_settings = model_judge_settings(s.config)
        signer = self._signer()

        cards = CardService(s.fetcher, s.store, s.clock, s.ids)
        fetched, parsed = cards.fetch_and_parse(request.card_url)
        cards.require_attestable(parsed)
        interface = select_interface(parsed)
        s.progress.on_event(
            "card_fetched",
            name=parsed.card.name,
            card_hash=parsed.card_hash,
            skills=len(parsed.card.skills),
            target_url=interface.url,
        )
        agent = cards.ensure_agent(request.card_url, parsed, request.owner, request.risk_level)
        card_version = cards.ensure_card_version(agent, fetched, parsed)

        if request.contract_file is not None:
            draft = draft_from_contract_file(request.contract_file, parsed)
            source = "contract file"
        else:
            draft = s.drafter.draft(
                parsed.card,
                DraftSettings(
                    latency_limit_ms=s.config.latency_limit_ms,
                    max_test_cases_per_skill=s.config.max_test_cases_per_skill,
                ),
            )
            source = s.drafter.name
        if request.export_draft:
            require_test_cases(draft, "export")
            exported = render_contract_file(contract_file_from_draft(draft, parsed))
            return AttestOutcome(kind="draft_exported", exported_contract_file=exported)

        contracts = ContractService(s.store, s.clock, s.ids)
        contract, test_cases = self._approved_contract(
            contracts, card_version.id, draft, parsed, source, request
        )

        planned = request.runs * len(test_cases)
        budget_limit = (
            request.budget_limit
            if request.budget_limit is not None
            else Decimal(DEFAULT_BUDGET_FACTOR * planned)
        )
        attestation = Attestation(
            id=s.ids.new_id(),
            contract_id=contract.id,
            card_version_id=card_version.id,
            trigger=request.trigger,
            status=AttestationStatus.QUEUED,
            started_at=s.clock.now(),
            budget_limit=budget_limit,
            cost_total=Decimal(0),
        )
        s.store.add_attestation(attestation)
        s.progress.on_event(
            "plan",
            attestation_id=attestation.id,
            test_cases=len(test_cases),
            runs=request.runs,
            planned_runs=planned,
            budget_limit=str(budget_limit),
            contract_version=contract.version,
            approved_by=contract.approved_by,
        )

        judge = JudgeService(
            s.store,
            s.transcripts,
            s.clock,
            s.ids,
            model_judge=s.model_judge,
            model_settings=model_settings,
        )
        orchestrator = Orchestrator(
            executor=s.executor,
            store=s.store,
            judge=judge,
            fetcher=s.fetcher,
            clock=s.clock,
            ids=s.ids,
            progress=s.progress,
            settings=OrchestratorSettings(
                runs=request.runs,
                concurrency=s.config.concurrency,
                max_retries=s.config.max_retries,
                run_timeout_s=s.config.run_timeout_s,
                poll_interval_s=s.config.poll_interval_s,
            ),
        )
        orchestration = orchestrator.execute(
            attestation,
            test_cases,
            interface,
            request.card_url,
            parsed.card_hash,
            request.sandbox_declared,
        )
        attestation = orchestration.attestation
        runs = [r.run for r in orchestration.recorded]
        transcript_hashes = {
            str(run.id): evidence_document_hash(s.transcripts, run.transcript_ref) for run in runs
        }

        decision: Decision | None = None
        kind: OutcomeKind
        if attestation.status is AttestationStatus.RUNNING:
            engine = PolicyEngine(s.store, s.clock, s.ids, signer)
            decision, attestation, _ = engine.decide_and_sign(
                attestation, contract, parsed.card_hash, test_cases, runs, transcript_hashes
            )
            kind = "completed"
            s.progress.on_event(
                "decision",
                outcome=decision.outcome.value,
                policy_version=decision.policy_version,
                signing_key_id=attestation.signing_key_id,
            )
        else:
            attestation = self._sign_without_decision(
                attestation, contract, parsed, test_cases, runs, transcript_hashes, signer
            )
            kind = "failed" if attestation.status is AttestationStatus.FAILED else "invalidated"

        bundle = assemble_bundle(
            store=s.store,
            transcripts=s.transcripts,
            attestation_id=attestation.id,
            clock=s.clock,
            card_url=request.card_url,
            target_url=interface.url,
            planned_runs=orchestration.planned_runs,
            not_executed=orchestration.not_executed,
            card_recheck=orchestration.card_recheck,
            sandbox_declared=request.sandbox_declared,
            drafter_name=source,
            signer_public_key=signer.public_key,
            proposals=PROPOSALS_IN_EFFECT,
            layer_2_configured=judge.layer_2_configured,
        )
        report_dir = s.report_writer.write(bundle)
        s.progress.on_event("report_written", path=str(report_dir))
        return AttestOutcome(
            kind=kind,
            attestation=attestation,
            decision=decision,
            bundle=bundle,
            report_dir=report_dir,
            planned_runs=orchestration.planned_runs,
        )

    # -- keys -------------------------------------------------------------------

    def _signer(self) -> Signer:
        """The deployment key, created on first use so a run never ends unsignable."""
        signer = self._s.keys.current()
        if signer is None:
            signer = self._s.keys.create()
            self._s.progress.on_event("key_created", key_id=signer.key_id)
        return signer

    # -- contracts ------------------------------------------------------------

    def _approved_contract(
        self,
        contracts: ContractService,
        card_version_id: UUID,
        draft: Draft,
        parsed: ParsedCard,
        source: str,
        request: AttestRequest,
    ) -> tuple[Contract, list[TestCase]]:
        """Reuse the approved contract with these test cases, or get a new version approved."""
        approved = contracts.latest_approved(card_version_id)
        if approved is not None and same_content(approved[1], draft.test_cases):
            self._s.progress.on_event(
                "contract_reused",
                version=approved[0].version,
                approved_by=approved[0].approved_by,
            )
            return approved
        existing = contracts.latest_draft_with_content(card_version_id, draft)
        contract, test_cases = existing or contracts.create_draft(card_version_id, draft)
        presentation = DraftPresentation(
            card_name=parsed.card.name,
            card_hash=parsed.card_hash,
            contract_version=contract.version,
            source=source,
            test_cases=draft.test_cases,
            not_testable=draft.not_testable,
            uncovered_skills=uncovered_skills(parsed.card, test_cases),
        )
        approver = request.approve_as
        if approver is None and request.approval_prompt is not None:
            approver = request.approval_prompt(presentation)
        if approver is None or not approver.strip():
            raise ApprovalRequiredError(
                "Nothing ran: the contract is not approved.",
                f"Contract version {contract.version} for '{parsed.card.name}' is a draft, and "
                "nothing runs against a contract until a human approves it (schema §2).",
                "Run again and confirm the draft at the prompt, or pass "
                "--approve-as <your identifier>.",
            )
        contract = contracts.approve(contract, approver)
        self._s.progress.on_event(
            "contract_approved", version=contract.version, approved_by=contract.approved_by
        )
        return contract, test_cases

    # -- signing without a decision (OQ-F7, the documents' proposal) ---------

    def _sign_without_decision(
        self,
        attestation: Attestation,
        contract: Contract,
        parsed: ParsedCard,
        test_cases: Sequence[TestCase],
        runs: Sequence[Run],
        transcript_hashes: dict[str, str],
        signer: Signer,
    ) -> Attestation:
        """Sign a failed or invalidated attestation; the payload's decision is ``null``."""
        payload = signing.build_payload(
            attestation=attestation,
            card_hash=parsed.card_hash,
            contract=contract,
            results=aggregate(test_cases, runs),
            transcript_hashes=transcript_hashes,
            decision=None,
        )
        signature, key_id = signing.sign_payload(signer, payload)
        signed = signing.with_signature(attestation, signature, key_id)
        self._s.store.update_attestation(signed)
        self._s.progress.on_event(
            "signed_without_decision", status=signed.status.value, signing_key_id=key_id
        )
        return signed
