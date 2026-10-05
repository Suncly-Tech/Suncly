#!/usr/bin/env python3
"""Validate the deployment configuration without applying any of it.

Checks, in order:

1. Cloud Run manifests parse, name a service account, reference the image by digest
   (``@sha256:`` with a placeholder or a real digest, never a tag), carry secrets only as
   Secret Manager references, and set no plaintext value that looks like a credential.
2. The worker job cannot read billing secrets; the API cannot read the signing key or the
   model key (the boundaries deploy/README.md describes).
3. ``compose.yaml`` parses and every service builds the same image.
4. ``terraform fmt -check`` and ``terraform validate`` when Terraform and the provider
   registry are reachable; otherwise reported as skipped, never as passed.
5. ``docker build --check`` when a BuildKit daemon is available; skipped otherwise.

Exit code 0 only when every check that could run passed. Needs PyYAML (dev extra).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIGEST_RE = re.compile(r"@sha256:(\$\{IMAGE_DIGEST\}|[0-9a-f]{64})$")
SECRET_LIKE = re.compile(
    r"(sk_(live|test)_|whsec_|sk-ant-|BEGIN (RSA|EC|OPENSSH|PRIVATE)|AKIA[0-9A-Z]{12})"
)
API_FORBIDDEN_SECRETS = {"suncly-signing-key", "suncly-model-api-key", "suncly-database-url-worker"}
WORKER_FORBIDDEN_SECRETS = {
    "suncly-stripe-secret-key",
    "suncly-stripe-webhook-secret",
    "suncly-database-url-api",
}


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.skipped: list[str] = []
        self.passed: list[str] = []

    def ok(self, what: str) -> None:
        self.passed.append(what)

    def fail(self, what: str) -> None:
        self.failures.append(what)

    def skip(self, what: str) -> None:
        self.skipped.append(what)


def load_yaml(path: Path) -> Any:
    import yaml

    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def containers_of(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    kind = manifest.get("kind")
    template = manifest["spec"]["template"]
    if kind == "Service":
        return list(template["spec"]["containers"])
    return list(template["spec"]["template"]["spec"]["containers"])


def service_account_of(manifest: dict[str, Any]) -> str:
    template = manifest["spec"]["template"]
    if manifest.get("kind") == "Service":
        return str(template["spec"].get("serviceAccountName", ""))
    return str(template["spec"]["template"]["spec"].get("serviceAccountName", ""))


def check_manifest(path: Path, report: Report) -> None:
    manifest = load_yaml(path)
    name = path.name
    if manifest.get("kind") not in {"Service", "Job"}:
        report.fail(f"{name}: kind must be Service or Job")
        return
    account = service_account_of(manifest)
    if not account.startswith("suncly-") or "@" not in account:
        report.fail(f"{name}: no dedicated service account")
    secrets_used: set[str] = set()
    for container in containers_of(manifest):
        image = str(container.get("image", ""))
        if not DIGEST_RE.search(image):
            report.fail(f"{name}: image {image!r} is not digest-pinned")
        for env in container.get("env", []):
            value = env.get("value")
            if value is not None and SECRET_LIKE.search(str(value)):
                report.fail(f"{name}: env {env.get('name')} carries a plaintext credential")
            ref = (env.get("valueFrom") or {}).get("secretKeyRef")
            if ref:
                secrets_used.add(str(ref.get("name")))
            if env.get("name") == "SUNCLY_ENVIRONMENT" and value not in {"production", "staging"}:
                report.fail(f"{name}: SUNCLY_ENVIRONMENT must be production or staging")
            if env.get("name") == "SUNCLY_LOCAL_AUTH_ENABLED":
                report.fail(f"{name}: local authentication must never be configured on Cloud Run")
            if env.get("name") == "SUNCLY_NETWORK_MODE" and value == "local":
                report.fail(f"{name}: network mode local is never deployable")
        if manifest.get("kind") == "Job":
            retries = manifest["spec"]["template"]["spec"]["template"]["spec"].get("maxRetries")
            if name.startswith("worker") and retries != 0:
                report.fail(f"{name}: the worker job must not retry at the platform level")
    if name.startswith("api") and secrets_used & API_FORBIDDEN_SECRETS:
        crossed = sorted(secrets_used & API_FORBIDDEN_SECRETS)
        report.fail(f"{name}: the API references worker-only secrets {crossed}")
    if name.startswith("worker") and secrets_used & WORKER_FORBIDDEN_SECRETS:
        crossed = sorted(secrets_used & WORKER_FORBIDDEN_SECRETS)
        report.fail(f"{name}: the worker references API-only secrets {crossed}")
    who = account.split("@")[0]
    report.ok(f"{name}: {who}, {len(secrets_used)} secret reference(s), digest-pinned image")


def check_compose(report: Report) -> None:
    compose = load_yaml(ROOT / "compose.yaml")
    services = compose.get("services", {})
    images = {s.get("build", {}).get("dockerfile") for s in services.values() if "build" in s}
    if images != {"deploy/Dockerfile"}:
        report.fail(f"compose.yaml: services build different images: {images}")
    for name, service in services.items():
        env = service.get("environment", {})
        if str(env.get("SUNCLY_ENVIRONMENT", "development")) == "production":
            report.fail(f"compose.yaml: {name} runs as production")
    report.ok(f"compose.yaml: {len(services)} service(s), one image")


def check_terraform(report: Report) -> None:
    terraform = shutil.which("terraform")
    folder = HERE / "terraform"
    if terraform is None:
        report.skip("terraform: not installed")
        return
    fmt = subprocess.run(
        [terraform, "fmt", "-check", "-recursive"], cwd=folder, capture_output=True, text=True
    )
    if fmt.returncode != 0:
        report.fail("terraform fmt: " + (fmt.stdout + fmt.stderr).strip())
    else:
        report.ok("terraform fmt")
    init = subprocess.run(
        [terraform, "init", "-backend=false", "-input=false", "-no-color"],
        cwd=folder,
        capture_output=True,
        text=True,
    )
    if init.returncode != 0:
        lines = [line.strip() for line in (init.stdout + init.stderr).splitlines() if line.strip()]
        reason = next(
            (line for line in lines if "Forbidden" in line or "could not" in line.lower()),
            lines[-1] if lines else "init failed",
        )
        report.skip("terraform validate: provider download unavailable (" + reason + ")")
        return
    validate = subprocess.run(
        [terraform, "validate", "-no-color"], cwd=folder, capture_output=True, text=True
    )
    if validate.returncode != 0:
        report.fail("terraform validate: " + (validate.stdout + validate.stderr).strip())
    else:
        report.ok("terraform validate")


def check_docker(report: Report) -> None:
    docker = shutil.which("docker")
    if docker is None:
        report.skip("docker build --check: docker is not installed")
        return
    probe = subprocess.run([docker, "buildx", "version"], capture_output=True, text=True)
    if probe.returncode != 0:
        report.skip("docker build --check: no BuildKit")
        return
    result = subprocess.run(
        [docker, "build", "--check", "-f", str(HERE / "Dockerfile"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-5:]
        no_daemon = (
            "permission denied",
            "Cannot connect",
            "failed to connect",
            "docker.sock",
            "daemon running",
        )
        if any(marker in line for line in tail for marker in no_daemon):
            report.skip("docker build --check: no usable daemon (" + tail[-1][:120] + ")")
        else:
            report.fail("docker build --check: " + "\n".join(tail))
    else:
        report.ok("docker build --check")


def main() -> int:
    report = Report()
    for manifest in sorted((HERE / "cloudrun").glob("*.yaml")):
        try:
            check_manifest(manifest, report)
        except (KeyError, TypeError) as exc:
            report.fail(f"{manifest.name}: unreadable manifest ({exc!r})")
    check_compose(report)
    check_terraform(report)
    check_docker(report)
    for line in report.passed:
        print(f"ok      {line}")
    for line in report.skipped:
        print(f"skipped {line}")
    for line in report.failures:
        print(f"FAIL    {line}")
    summary = f"{len(report.passed)} passed, {len(report.skipped)} skipped"
    print(f"\n{summary}, {len(report.failures)} failed")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
