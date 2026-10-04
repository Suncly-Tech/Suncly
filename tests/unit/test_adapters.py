"""The small adapters: key files, transcript storage, card fetcher, report writer, subprocess executor."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import UUID

import pytest

from suncly.adapters.file_keys import FileSigningKeys
from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
from suncly.adapters.local_transcripts import LocalTranscriptStorage
from suncly.adapters.report.view import build_view
from suncly.adapters.report.writer import FolderReportWriter, read_report_folder, result_document
from suncly.adapters.subprocess_executor import SubprocessRunExecutor
from suncly.core.attestation import AttestationService, AttestRequest
from suncly.core.signing import b64url, key_id_for, payload_bytes, verify_payload
from suncly.domain.errors import CardFetchError, StoreError
from suncly.mock_agents.behaviours import DeadPort
from suncly.ports.run_executor import RunJob
from tests.conftest import ServicesFactory
from tests.fakes import StaticFetcher, card_text

CARD_URL = "https://agent.example.com/.well-known/agent-card.json"


def a_job(**overrides: object) -> RunJob:
    data: dict[str, object] = {
        "attestation_id": UUID(int=1),
        "test_case_id": UUID(int=2),
        "attempt": 1,
        "message_id": "m",
        "input": {"text": "x"},
        "target_url": "https://a.example.com/rpc",
        "protocol_binding": "JSONRPC",
        "protocol_version": "1.0",
        "timeout_s": 1.0,
        "poll_interval_s": 0.1,
        "sandbox_declared": True,
    }
    data.update(overrides)
    return RunJob.model_validate(data)


# -- keys ------------------------------------------------------------------------------


def test_file_keys_create_current_and_public_lookup(tmp_path: Path) -> None:
    keys = FileSigningKeys(tmp_path / "keys")
    assert keys.current() is None
    signer = keys.create()
    current = keys.current()
    assert current is not None and current.key_id == signer.key_id
    assert keys.public_key_for(signer.key_id) == signer.public_key
    assert keys.public_key_for("ed25519-nope") is None
    assert key_id_for(signer.public_key) == signer.key_id
    signature = "ed25519:" + b64url(signer.sign(payload_bytes({"x": 1})))
    assert verify_payload(signer.public_key, {"x": 1}, signature)
    assert "PRIVATE" not in repr(signer) and len(signer.sign(b"p")) == 64
    private = tmp_path / "keys" / f"{signer.key_id}.key.pem"
    assert private.exists()
    if os.name != "nt":
        assert stat.S_IMODE(private.stat().st_mode) == 0o600
    second = keys.create()
    current = keys.current()
    assert current is not None and current.key_id == second.key_id != signer.key_id


# -- transcripts -----------------------------------------------------------------------


def test_local_transcripts_are_write_once_and_stay_inside_the_root(tmp_path: Path) -> None:
    storage = LocalTranscriptStorage(tmp_path / "t")
    ref = storage.put("a/b.json", b"1")
    assert ref == "a/b.json" and storage.exists(ref) and storage.get(ref) == b"1"
    with pytest.raises(StoreError, match="DR-002"):
        storage.put("a/b.json", b"2")
    for bad in (
        "../escape.json",
        "/abs.json",
        "a//b.json",
        "a/./b.json",
        "",
        "C:/x.json",
        "a\b.json",
    ):
        with pytest.raises(StoreError, match="safe segments"):
            storage.put(bad, b"x")
    with pytest.raises(StoreError, match="missing"):
        storage.get("nope.json")


# -- card fetcher ----------------------------------------------------------------------


class CardServer:
    """Serves a card, a redirect, an error, or a huge body depending on the path."""

    def __init__(self) -> None:
        card = card_text()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return None

            def do_GET(self) -> None:
                if self.path == "/card":
                    body = card.encode()
                    self.send_response(200)
                elif self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/card")
                    self.end_headers()
                    return
                elif self.path == "/redirect-insecure":
                    self.send_response(302)
                    self.send_header("Location", "http://agent.example.com/card")
                    self.end_headers()
                    return
                elif self.path == "/huge":
                    body = b"[" + b"1," * 600_000 + b"1]"
                    self.send_response(200)
                elif self.path == "/binary":
                    body = b"\xff\xfe"
                    self.send_response(200)
                else:
                    body = b"missing"
                    self.send_response(404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __exit__(self, *exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()


def test_card_fetcher_fetches_follows_safe_redirects_and_refuses_the_rest() -> None:
    fetcher = HttpxCardFetcher(timeout_s=5.0, max_bytes=1_000_000)
    with CardServer() as base:
        fetched = fetcher.fetch(base + "/card")
        assert (
            json.loads(fetched.raw_json)["name"] == "Test Agent" and fetched.url == base + "/card"
        )
        assert fetcher.fetch(base + "/redirect").raw_json == fetched.raw_json
        with pytest.raises(CardFetchError, match="not https"):
            fetcher.fetch(base + "/redirect-insecure")
        with pytest.raises(CardFetchError, match="HTTP 404"):
            fetcher.fetch(base + "/missing")
        with pytest.raises(CardFetchError, match="not UTF-8"):
            fetcher.fetch(base + "/binary")
        with pytest.raises(CardFetchError, match="size limit"):
            HttpxCardFetcher(timeout_s=5.0, max_bytes=1000).fetch(base + "/huge")
    with pytest.raises(CardFetchError, match="must use https"):
        fetcher.fetch("http://agent.example.com/card")
    with DeadPort() as dead, pytest.raises(CardFetchError, match="could not be fetched"):
        fetcher.fetch(dead.url.replace("/rpc", "/card"))


# -- report writer ---------------------------------------------------------------------


def test_report_folder_is_self_contained_and_offline(
    services_factory: ServicesFactory, tmp_path: Path
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    services.report_writer = FolderReportWriter(tmp_path / "out", services.transcripts)
    outcome = AttestationService(services).attest(
        AttestRequest(card_url=CARD_URL, sandbox_declared=True, runs=2, approve_as="t")
    )
    assert outcome.attestation is not None and outcome.bundle is not None
    folder = outcome.report_dir
    assert folder is not None and folder == tmp_path / "out" / str(outcome.attestation.id)
    html = (folder / "report.html").read_text(encoding="utf-8")
    assert "<script" not in html and "src=" not in html and 'href="http' not in html
    assert "Decision: flag. No policy is configured, so a human must review this result." in html
    assert "What was NOT tested" in html and "Proposals in effect" in html
    markdown = (folder / "report.md").read_text(encoding="utf-8")
    assert "| pass | fail | inconclusive |" in markdown and "suncly verify" in markdown
    result, transcripts = read_report_folder(folder)
    assert result["format"] == "suncly-result/1"
    assert len(transcripts) == 2 and all("document" not in r for r in result["runs"])
    document = result_document(outcome.bundle)
    assert set(document["signature_payload"]) == {
        "payload_version",
        "attestation_id",
        "card_hash",
        "contract",
        "results",
        "transcript_hashes",
        "decision",
    }
    view = build_view(outcome.bundle)
    assert (view.pass_total, view.fail_total, view.inconclusive_total) == (2, 0, 0)
    assert all(row.transcript_file.startswith("transcripts/") for row in view.runs)


# -- subprocess executor ----------------------------------------------------------------


def test_subprocess_executor_reports_a_missing_interpreter_as_a_crash() -> None:
    executor = SubprocessRunExecutor(python=str(Path("definitely") / "not-python"))
    result = executor.execute(a_job())
    assert result.crashed and "could not start" in (result.error or "")


def test_subprocess_executor_treats_garbage_output_and_timeouts_as_crashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def garbage(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=b"not json", stderr=b"")

    monkeypatch.setattr(subprocess, "run", garbage)
    result = SubprocessRunExecutor().execute(a_job())
    assert result.crashed and "unreadable result" in (result.error or "")

    def silent(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=[], returncode=3, stdout=b"", stderr=b"secret stderr"
        )

    monkeypatch.setattr(subprocess, "run", silent)
    result = SubprocessRunExecutor().execute(a_job())
    assert (
        result.crashed
        and "code 3" in (result.error or "")
        and "secret stderr" not in (result.error or "")
    )

    def slow(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd="python", timeout=1.0)

    monkeypatch.setattr(subprocess, "run", slow)
    result = SubprocessRunExecutor().execute(a_job())
    assert result.crashed and "was killed" in (result.error or "")


def test_local_transcripts_survive_concurrent_writes_on_a_fresh_root(tmp_path: Path) -> None:
    """Regression: resolving not-yet-existing paths on Windows under concurrent mkdir gave
    wrong paths, so a transcript could land outside its folder while its run was recorded."""
    from concurrent.futures import ThreadPoolExecutor
    from uuid import uuid4

    for _ in range(25):
        storage = LocalTranscriptStorage(tmp_path / str(uuid4()) / "transcripts")
        attestation = uuid4()
        keys = [f"{attestation}/{uuid4()}-{attempt}.json" for _ in range(3) for attempt in (1, 2)]
        with ThreadPoolExecutor(max_workers=3) as pool:
            refs = list(pool.map(storage.put, keys, [b"{}"] * len(keys)))
        assert refs == keys
        assert all(storage.exists(key) for key in keys)
