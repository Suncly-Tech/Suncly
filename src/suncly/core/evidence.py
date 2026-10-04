"""Assembling the evidence bundle of one attestation from the stores."""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

from suncly.core import signing
from suncly.core.coverage import not_tested
from suncly.core.policy_engine import aggregate
from suncly.domain.canonical import sha256_hex
from suncly.domain.card import parse_agent_card
from suncly.domain.errors import StoreError
from suncly.domain.evidence import CardRecheck, EvidenceBundle, NotExecutedRun, RunEvidence
from suncly.domain.models import JsonObject
from suncly.ports.clock import Clock
from suncly.ports.store import EvidenceStore
from suncly.ports.transcripts import TranscriptStorage


def evidence_document_hash(transcripts: TranscriptStorage, transcript_ref: str) -> str:
    """The hash of a stored evidence document, as the signature payload carries it."""
    return sha256_hex(transcripts.get(transcript_ref))


def load_evidence_document(transcripts: TranscriptStorage, transcript_ref: str) -> JsonObject:
    loaded = json.loads(transcripts.get(transcript_ref))
    if not isinstance(loaded, dict):
        raise StoreError(f"The evidence document {transcript_ref} is not a JSON object.")
    return loaded


def assemble_bundle(
    *,
    store: EvidenceStore,
    transcripts: TranscriptStorage,
    attestation_id: UUID,
    clock: Clock,
    card_url: str | None,
    target_url: str | None,
    planned_runs: int | None,
    not_executed: Sequence[NotExecutedRun],
    card_recheck: CardRecheck,
    sandbox_declared: bool,
    drafter_name: str | None,
    signer_public_key: bytes | None,
    proposals: Sequence[str],
) -> EvidenceBundle:
    """Load everything about an attestation and derive results and coverage."""
    attestation = store.get_attestation(attestation_id)
    if attestation is None:
        raise StoreError(f"Attestation {attestation_id} does not exist.")
    contract = store.get_contract(attestation.contract_id)
    card_version = store.get_card_version(attestation.card_version_id)
    if contract is None or card_version is None:
        raise StoreError(f"Attestation {attestation_id} references records that do not exist.")
    agent = store.get_agent(card_version.agent_id)
    if agent is None:
        raise StoreError(f"Card version {card_version.id} references an agent that does not exist.")
    parsed = parse_agent_card(card_version.raw_json)
    test_cases = store.list_test_cases(contract.id)
    runs = store.list_runs(attestation.id)
    decisions = store.list_decisions(attestation.id)

    run_evidence = [
        RunEvidence(
            run=run,
            document=load_evidence_document(transcripts, run.transcript_ref),
            document_hash=evidence_document_hash(transcripts, run.transcript_ref),
        )
        for run in runs
    ]
    results = aggregate(test_cases, runs)
    used_target = target_url or parsed.card.supported_interfaces[0].url
    coverage = not_tested(
        parsed=parsed,
        test_cases=test_cases,
        results=results,
        not_executed=not_executed,
        planned_runs=planned_runs,
        target_url=used_target,
        sandbox_declared=sandbox_declared,
    )
    policy_decision = decisions[0] if decisions else None
    payload: JsonObject | None = None
    if attestation.is_signed:
        payload = signing.build_payload(
            attestation=attestation,
            card_hash=card_version.card_hash,
            contract=contract,
            results=results,
            transcript_hashes={str(r.run.id): r.document_hash for r in run_evidence},
            decision=policy_decision,
        )
    return EvidenceBundle(
        generated_at=clock.now(),
        agent=agent,
        card_version=card_version,
        parsed_card=parsed,
        card_url=card_url,
        contract=contract,
        test_cases=test_cases,
        attestation=attestation,
        runs=run_evidence,
        decisions=decisions,
        results=results,
        planned_runs=planned_runs,
        not_executed=list(not_executed),
        card_recheck=card_recheck,
        not_tested=coverage,
        sandbox_declared=sandbox_declared,
        drafter_name=drafter_name,
        signer_public_key=signing.b64url(signer_public_key) if signer_public_key else None,
        signature_payload=payload,
        proposals=list(proposals),
    )
