"""The Report adapter port (schema §2: Adapters, Report)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from suncly.domain.evidence import EvidenceBundle


class ReportWriter(Protocol):
    """Renders the evidence of one attestation for a reviewer."""

    def write(self, bundle: EvidenceBundle) -> Path:
        """Write the report and return its folder."""
        ...
