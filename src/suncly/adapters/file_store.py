"""The file Evidence store: zero configuration, works offline.

One JSON file per record under one root. Append-only records (``run`` and
``decision``) are created with exclusive-create and made read-only, and the
run key is the file name, so a second record with the same key cannot be
written even by accident. The rules of ``domain/rules.py`` are checked before
every write, exactly as the Postgres store does.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError

from suncly.domain import rules
from suncly.domain.errors import StoreError
from suncly.domain.models import (
    Agent,
    Attestation,
    CardVersion,
    Contract,
    ContractStatus,
    Decision,
    Run,
    RunKey,
    TestCase,
)

M = TypeVar("M", bound=BaseModel)


class FileEvidenceStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.RLock()
        for name in ("agents", "card_versions", "contracts", "attestations", "runs", "decisions"):
            (root / name).mkdir(parents=True, exist_ok=True)

    # -- helpers -----------------------------------------------------------------

    def _read(self, path: Path, model: type[M]) -> M | None:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            return model.model_validate_json(text)
        except ValidationError as exc:
            raise StoreError(
                f"The record {path} is not a valid {model.__name__}.", f"Validation reported: {exc}"
            ) from exc

    @staticmethod
    def _write_new(path: Path, record: BaseModel, *, read_only: bool) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(record.model_dump_json(indent=2))
        except FileExistsError as exc:
            raise StoreError(
                "A record with this key already exists.",
                f"{path.name} is already recorded; evidence is never overwritten (DR-002).",
            ) from exc
        if read_only:
            path.chmod(0o444)

    @staticmethod
    def _replace(path: Path, record: BaseModel) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def _iter(self, folder: Path, model: type[M]) -> Iterator[M]:
        if not folder.is_dir():
            return
        for path in sorted(folder.glob("*.json")):
            record = self._read(path, model)
            if record is not None:
                yield record

    # -- agent -------------------------------------------------------------------

    def get_agent(self, agent_id: UUID) -> Agent | None:
        return self._read(self._root / "agents" / f"{agent_id}.json", Agent)

    def add_agent(self, agent: Agent) -> None:
        with self._lock:
            self._write_new(self._root / "agents" / f"{agent.id}.json", agent, read_only=False)

    # -- card_version ------------------------------------------------------------

    def get_card_version(self, card_version_id: UUID) -> CardVersion | None:
        return self._read(self._root / "card_versions" / f"{card_version_id}.json", CardVersion)

    def find_card_version(self, agent_id: UUID, card_hash: str) -> CardVersion | None:
        matches = [
            cv
            for cv in self._iter(self._root / "card_versions", CardVersion)
            if cv.agent_id == agent_id and cv.card_hash == card_hash
        ]
        return min(matches, key=lambda cv: cv.fetched_at, default=None)

    def add_card_version(self, card_version: CardVersion) -> None:
        with self._lock:
            if self.get_agent(card_version.agent_id) is None:
                raise StoreError(
                    f"card_version references agent {card_version.agent_id}, which does not exist."
                )
            self._write_new(
                self._root / "card_versions" / f"{card_version.id}.json",
                card_version,
                read_only=True,
            )

    # -- contract and test_case --------------------------------------------------

    def _contract_dir(self, contract_id: UUID) -> Path:
        return self._root / "contracts" / str(contract_id)

    def get_contract(self, contract_id: UUID) -> Contract | None:
        return self._read(self._contract_dir(contract_id) / "contract.json", Contract)

    def list_contracts(self, card_version_id: UUID) -> list[Contract]:
        contracts = [
            c
            for c in (
                self.get_contract(UUID(p.name))
                for p in (self._root / "contracts").iterdir()
                if p.is_dir()
            )
            if c is not None and c.card_version_id == card_version_id
        ]
        return sorted(contracts, key=lambda c: (c.version, c.created_at))

    def add_contract(self, contract: Contract, test_cases: list[TestCase]) -> None:
        with self._lock:
            if self.get_card_version(contract.card_version_id) is None:
                raise StoreError(
                    f"contract references card_version {contract.card_version_id}, "
                    "which does not exist."
                )
            if any(tc.contract_id != contract.id for tc in test_cases):
                raise StoreError("Every test case must belong to the contract being added.")
            folder = self._contract_dir(contract.id)
            if folder.exists():
                raise StoreError(f"Contract {contract.id} already exists.")
            folder.mkdir(parents=True)
            _TestCases(test_cases=test_cases).write(folder / "test_cases.json")
            self._write_new(folder / "contract.json", contract, read_only=False)

    def list_test_cases(self, contract_id: UUID) -> list[TestCase]:
        record = self._read(self._contract_dir(contract_id) / "test_cases.json", _TestCases)
        return list(record.test_cases) if record else []

    def _transition(
        self, contract_id: UUID, new_status: ContractStatus, **changes: object
    ) -> Contract:
        with self._lock:
            contract = self.get_contract(contract_id)
            if contract is None:
                raise StoreError(f"Contract {contract_id} does not exist.")
            rules.check_contract_transition(contract, new_status)
            data = contract.model_dump()
            data.update(changes)
            data["status"] = new_status
            updated = Contract.model_validate(data)
            self._replace(self._contract_dir(contract_id) / "contract.json", updated)
            return updated

    def approve_contract(
        self, contract_id: UUID, approved_by: str, approved_at: datetime
    ) -> Contract:
        return self._transition(
            contract_id, ContractStatus.APPROVED, approved_by=approved_by, approved_at=approved_at
        )

    def reject_contract(self, contract_id: UUID) -> Contract:
        return self._transition(contract_id, ContractStatus.REJECTED)

    def supersede_contract(self, contract_id: UUID) -> Contract:
        return self._transition(contract_id, ContractStatus.SUPERSEDED)

    # -- attestation -------------------------------------------------------------

    def get_attestation(self, attestation_id: UUID) -> Attestation | None:
        return self._read(self._root / "attestations" / f"{attestation_id}.json", Attestation)

    def list_attestations(self, card_version_id: UUID) -> list[Attestation]:
        return sorted(
            (
                a
                for a in self._iter(self._root / "attestations", Attestation)
                if a.card_version_id == card_version_id
            ),
            key=lambda a: a.started_at,
        )

    def add_attestation(self, attestation: Attestation) -> None:
        with self._lock:
            rules.check_attestation_insert(attestation, self.get_contract(attestation.contract_id))
            self._write_new(
                self._root / "attestations" / f"{attestation.id}.json", attestation, read_only=False
            )

    def update_attestation(self, attestation: Attestation) -> None:
        with self._lock:
            old = self.get_attestation(attestation.id)
            if old is None:
                raise StoreError(f"Attestation {attestation.id} does not exist.")
            rules.check_attestation_update(
                old, attestation, bool(self.list_decisions(attestation.id))
            )
            self._replace(self._root / "attestations" / f"{attestation.id}.json", attestation)

    # -- run (append-only) -------------------------------------------------------

    def _run_path(self, key: RunKey) -> Path:
        return (
            self._root / "runs" / str(key.attestation_id) / f"{key.test_case_id}-{key.attempt}.json"
        )

    def add_run(self, run: Run) -> None:
        with self._lock:
            attestation = self.get_attestation(run.attestation_id)
            test_case = (
                next(
                    (
                        tc
                        for tc in self.list_test_cases(attestation.contract_id)
                        if tc.id == run.test_case_id
                    ),
                    None,
                )
                if attestation is not None
                else None
            )
            existing = {r.key for r in self.list_runs(run.attestation_id)}
            rules.check_run_insert(run, attestation, test_case, existing)
            self._write_new(self._run_path(run.key), run, read_only=True)

    def list_runs(self, attestation_id: UUID) -> list[Run]:
        return sorted(
            self._iter(self._root / "runs" / str(attestation_id), Run),
            key=lambda r: (str(r.test_case_id), r.attempt),
        )

    # -- decision (append-only) --------------------------------------------------

    def add_decision(self, decision: Decision) -> None:
        with self._lock:
            existing = self.list_decisions(decision.attestation_id)
            rules.check_decision_insert(
                decision, self.get_attestation(decision.attestation_id), existing
            )
            folder = self._root / "decisions" / str(decision.attestation_id)
            self._write_new(
                folder / f"{len(existing) + 1:04d}-{decision.id}.json", decision, read_only=True
            )

    def list_decisions(self, attestation_id: UUID) -> list[Decision]:
        return list(self._iter(self._root / "decisions" / str(attestation_id), Decision))

    def close(self) -> None:
        return None


class _TestCases(BaseModel):
    test_cases: list[TestCase]

    def write(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        path.chmod(0o444)
