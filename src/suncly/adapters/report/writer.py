"""Writes one report folder per attestation (DR-007).

The folder is self-contained: ``result.json`` (the evidence bundle and the
signed payload), the redacted transcripts byte for byte as stored, a Markdown
report and an offline HTML report. ``suncly verify`` works from it alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from suncly.adapters.report.html import render_html
from suncly.adapters.report.markdown import render_markdown
from suncly.adapters.report.view import build_view
from suncly.domain.evidence import EvidenceBundle
from suncly.domain.models import JsonObject
from suncly.ports.transcripts import TranscriptStorage

RESULT_FORMAT = "suncly-result/1"


def result_document(bundle: EvidenceBundle) -> JsonObject:
    """``result.json``: the bundle without the inline transcripts, which are files next to it."""
    document = bundle.model_dump(mode="json", exclude={"runs": {"__all__": {"document"}}})
    document["format"] = RESULT_FORMAT
    return document


class FolderReportWriter:
    def __init__(self, reports_dir: Path, transcripts: TranscriptStorage) -> None:
        self._reports_dir = reports_dir
        self._transcripts = transcripts

    def write(self, bundle: EvidenceBundle) -> Path:
        folder = self._reports_dir / str(bundle.attestation.id)
        transcripts_dir = folder / "transcripts"
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        for evidence in bundle.runs:
            data = self._transcripts.get(evidence.run.transcript_ref)
            (transcripts_dir / f"{evidence.run.id}.json").write_bytes(data)
        (folder / "result.json").write_text(
            json.dumps(result_document(bundle), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        view = build_view(bundle)
        (folder / "report.md").write_text(render_markdown(view), encoding="utf-8")
        (folder / "report.html").write_text(render_html(view), encoding="utf-8")
        return folder


def read_report_folder(folder: Path) -> tuple[JsonObject, dict[str, bytes]]:
    """Load ``result.json`` and the transcript files of a report folder, for verification."""
    result_path = folder / "result.json"
    loaded = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{result_path} is not a JSON object")
    transcripts: dict[str, bytes] = {}
    for path in sorted((folder / "transcripts").glob("*.json")):
        transcripts[path.stem] = path.read_bytes()
    return loaded, transcripts
