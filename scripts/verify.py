#!/usr/bin/env python3
"""Fail-closed verifier for a dedicated JSP intake wrapper.

This script does not alter or vendor the pinned upstream proof. It clones the
specified revision, checks source hashes, compiles the required custom modules,
compiles the local wrapper/audit, replays the upstream and local modules with
Lean's bundled kernel checker, and enforces a small axiom allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "UPSTREAM.lock.json").read_text(encoding="utf-8"))
GENERATED = ROOT / "verification" / "generated"
WORK = ROOT / ".work" / "upstream"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path, log_name: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    GENERATED.mkdir(parents=True, exist_ok=True)
    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - start
    out = f"$ {' '.join(cmd)}\n\n{proc.stdout}\n\nexit={proc.returncode}\nelapsed_seconds={elapsed:.3f}\n"
    (GENERATED / log_name).write_text(out, encoding="utf-8")
    if proc.returncode != 0:
        print(out, file=sys.stderr)
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc


def strip_lean_comments_and_strings(text: str) -> str:
    # Enough for a fail-closed scan of these tiny local wrappers. Nested block
    # comments are handled; escaped string characters are skipped.
    out: list[str] = []
    i = 0
    depth = 0
    in_string = False
    while i < len(text):
        if in_string:
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == '"':
                in_string = False
            i += 1
            continue
        if depth:
            if text.startswith("/-", i):
                depth += 1
                i += 2
            elif text.startswith("-/", i):
                depth -= 1
                i += 2
            else:
                i += 1
            continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            i = len(text) if j < 0 else j + 1
            out.append("\n")
            continue
        if text.startswith("/-", i):
            depth = 1
            i += 2
            continue
        if text[i] == '"':
            in_string = True
            i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def static_audit() -> dict[str, object]:
    lean_files = [ROOT / LOCK["local"]["wrapper"], ROOT / "Audit.lean"]
    patterns = {
        "sorry": re.compile(r"\bsorry\b"),
        "admit": re.compile(r"\badmit\b"),
        "custom_axiom": re.compile(r"(?m)^\s*axiom\s+"),
        "native_decide": re.compile(r"\bnative_decide\b"),
        "unsafe": re.compile(r"(?m)^\s*unsafe\s+"),
        "implemented_by": re.compile(r"\bimplemented_by\b"),
        "ofReduceBool": re.compile(r"\bLean\.ofReduceBool\b"),
    }
    findings: list[dict[str, str]] = []
    for path in lean_files:
        code = strip_lean_comments_and_strings(path.read_text(encoding="utf-8"))
        for name, pattern in patterns.items():
            if pattern.search(code):
                findings.append({"file": path.name, "pattern": name})
    if findings:
        raise SystemExit(f"prohibited local proof construct(s): {findings}")
    result = {
        "status": "pass",
        "files": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in lean_files],
        "prohibited_findings": findings,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    (GENERATED / "static-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def clone_or_reset(clean: bool) -> Path:
    if clean and WORK.exists():
        shutil.rmtree(WORK)
    WORK.parent.mkdir(parents=True, exist_ok=True)
    if not (WORK / ".git").exists():
        run([
            "git", "-c", "core.autocrlf=false", "clone", "--filter=blob:none", "--no-checkout",
            LOCK["upstream"]["repository"], str(WORK)
        ], ROOT, "01-clone.log")
    run(["git", "config", "core.autocrlf", "false"], WORK, "02-git-config.log")
    run(["git", "fetch", "--force", "origin", LOCK["upstream"]["commit"]], WORK, "03-fetch.log")
    run(["git", "checkout", "--force", "--detach", LOCK["upstream"]["commit"]], WORK, "04-checkout.log")
    run(["git", "clean", "-ffd"], WORK, "05-clean.log")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORK, text=True).strip()
    if head != LOCK["upstream"]["commit"]:
        raise SystemExit(f"upstream HEAD mismatch: {head}")
    return WORK / LOCK["upstream"]["workspace"]


def check_upstream(workspace: Path) -> list[dict[str, object]]:
    toolchain = (workspace / "lean-toolchain").read_text(encoding="utf-8").strip()
    if toolchain != LOCK["upstream"]["toolchain"]:
        raise SystemExit(f"toolchain mismatch: {toolchain}")
    records = []
    for item in LOCK["upstream"]["source_files"]:
        path = workspace / item["path"]
        if not path.is_file():
            raise SystemExit(f"missing pinned source: {item['path']}")
        actual = sha256(path)
        if actual != item["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {item['path']}: {actual}")
        records.append({"path": item["path"], "sha256": actual, "bytes": path.stat().st_size})
    manifest_path = workspace / "lake-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mathlib_entries = [p for p in manifest.get("packages", []) if p.get("name") == "mathlib"]
    if len(mathlib_entries) != 1:
        raise SystemExit(f"expected exactly one mathlib manifest entry, found {len(mathlib_entries)}")
    actual_mathlib = mathlib_entries[0].get("rev")
    if actual_mathlib != LOCK["upstream"]["mathlib_commit"]:
        raise SystemExit(f"mathlib revision mismatch: {actual_mathlib}")

    comparator = workspace / LOCK["upstream"]["comparator_path"]
    if not comparator.is_file():
        raise SystemExit(f"missing comparator configuration: {comparator}")
    comparator_data = json.loads(comparator.read_text(encoding="utf-8"))
    expected_comparator = LOCK["upstream"]["comparator"]
    if comparator_data.get("solution_module") != LOCK["upstream"]["target_module"]:
        raise SystemExit("comparator solution_module mismatch")
    if comparator_data.get("theorem_names") != expected_comparator["theorem_names"]:
        raise SystemExit(
            f"comparator theorem_names mismatch: {comparator_data.get('theorem_names')}"
        )
    if set(comparator_data.get("permitted_axioms", [])) != set(expected_comparator["permitted_axioms"]):
        raise SystemExit("comparator permitted_axioms mismatch")
    if bool(comparator_data.get("enable_nanoda")) != bool(expected_comparator["enable_nanoda"]):
        raise SystemExit("comparator enable_nanoda mismatch")

    upstream_audit = {
        "toolchain": toolchain,
        "mathlib_commit": actual_mathlib,
        "sources": records,
        "comparator": comparator_data,
    }
    GENERATED.mkdir(parents=True, exist_ok=True)
    (GENERATED / "upstream-audit.json").write_text(
        json.dumps(upstream_audit, indent=2) + "\n", encoding="utf-8"
    )
    return records


def module_name(path: str) -> str:
    assert path.endswith(".lean")
    return path[:-5].replace("/", ".")


def compile_module(workspace: Path, source_rel: str, log_index: int) -> None:
    output = workspace / ".lake" / "build" / "lib" / "lean" / source_rel[:-5]
    output = output.with_suffix(".olean")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "lake", "env", "lean", "-j1", "-M8192", "-R", ".", "-o",
        str(output.relative_to(workspace)), source_rel
    ], workspace, f"{log_index:02d}-compile-{module_name(source_rel)}.log", env={**os.environ, "LEAN_NUM_THREADS": "1"})


def parse_axioms(text: str, declarations: Iterable[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    allowed = set(LOCK["verification"]["allowed_axioms"])
    for decl in declarations:
        pattern = re.compile(r"'" + re.escape(decl) + r"' depends on axioms:\s*\[([^]]*)\]", re.S)
        match = pattern.search(text)
        if match:
            normalized = re.sub(r"\.\{[^{}]*\}", "", match.group(1))
            atoms = [x.strip() for x in normalized.split(",") if x.strip()]
        elif f"'{decl}' does not depend on any axioms" in text:
            atoms = []
        else:
            raise SystemExit(f"missing axiom report for {decl}")
        extra = set(atoms) - allowed
        if extra:
            raise SystemExit(f"unpermitted axioms for {decl}: {sorted(extra)}")
        result[decl] = atoms
    return result


def verify(clean: bool, no_cache: bool) -> dict[str, object]:
    static = static_audit()
    workspace = clone_or_reset(clean)
    sources = check_upstream(workspace)

    if not no_cache:
        run(["lake", "exe", "cache", "get"], workspace, "06-cache.log", env={**os.environ, "LEAN_NUM_THREADS": "1"})

    # Build the pinned target module through Lake so its transitive custom
    # dependencies (e.g. the Util incidence-geometry library) are built too.
    run(["lake", "build", LOCK["upstream"]["target_module"]], workspace,
        "07-build-target.log", env=dict(os.environ))
    idx = 8

    wrapper_name = LOCK["local"]["wrapper"]
    shutil.copy2(ROOT / wrapper_name, workspace / wrapper_name)
    shutil.copy2(ROOT / "Audit.lean", workspace / "Audit.lean")
    compile_module(workspace, wrapper_name, idx)
    idx += 1
    compile_module(workspace, "Audit.lean", idx)
    audit_log = (GENERATED / f"{idx:02d}-compile-Audit.log").read_text(encoding="utf-8")
    idx += 1

    declarations = LOCK["local"]["theorems"] + LOCK["upstream"]["theorems"]
    axioms = parse_axioms(audit_log, declarations)

    replayed = []
    for mod in [LOCK["upstream"]["target_module"], LOCK["local"]["module"]]:
        run(["lake", "env", "leanchecker", "--verbose", mod], workspace,
            f"{idx:02d}-replay-{mod}.log", env={**os.environ, "LEAN_NUM_THREADS": "1"})
        replayed.append(mod)
        idx += 1

    result = {
        "status": "pass",
        "problem_id": LOCK["problem_id"],
        "verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "upstream_commit": LOCK["upstream"]["commit"],
        "toolchain": LOCK["upstream"]["toolchain"],
        "mathlib_commit_expected": LOCK["upstream"]["mathlib_commit"],
        "sources": sources,
        "static_audit": static,
        "axioms": axioms,
        "replayed_modules": replayed,
        "same_kernel_replay": True,
        "independent_checker": False,
        "nanoda_comparator_enabled_upstream": LOCK["upstream"]["comparator"]["enable_nanoda"],
        "limitations": [
            "Imported Mathlib and dependency cache artifacts are trusted.",
            "leanchecker uses Lean's own kernel; it is not an independently implemented checker.",
            "This contributor-run result is not official prize verification or an award decision."
        ]
    }
    (GENERATED / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="delete the pinned upstream checkout before verifying")
    parser.add_argument("--no-cache", action="store_true", help="skip Mathlib cache retrieval")
    parser.add_argument("--static-only", action="store_true", help="run local source audit without cloning or Lean")
    args = parser.parse_args()
    GENERATED.mkdir(parents=True, exist_ok=True)
    if args.static_only:
        result = static_audit()
        print(json.dumps(result, indent=2))
    else:
        result = verify(args.clean, args.no_cache)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
