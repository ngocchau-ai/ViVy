"""Run the C01 known-answer suite against one named backend. No silent fallback.

    python -m training.run_known_answer --backend llama-server \\
        --run-id c01-llama-live-001 \\
        --output evidence/VIVY-C01-KNOWN-ANSWER-llama-001.json

Exit codes:
    0  receipt written and safety set complete
    2  suite ran but safety set incomplete / no scored cases
    3  infrastructure (timeout / unavailable / wrong_alias) — NOT a model FAIL
    4  usage / write-guard error

Changelog:
    24/09/2026 (Claude Code — P1 C01): Initial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from training.backend_baseline import run_known_answer_suite, write_suite_receipt
from training.backend_registry import (
    enumerate_backends,
    get_backend,
    make_llama_server_fn,
    make_unitary_fn,
    probe_health,
    prompt_sha256,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True,
                        choices=["llama-server", "native-cautreo", "unitary-llm-client"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-alias", default=None,
                        help="override model alias; wrong alias yields WRONG_ALIAS, never a fallback")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--allow-replace", action="store_true")
    parser.add_argument("--list-backends", action="store_true")
    args = parser.parse_args(argv)

    if args.list_backends:
        for item in enumerate_backends():
            ident = item.identity.to_dict()
            print(json.dumps({"role": item.role, "describe": item.describe, "identity": ident},
                             ensure_ascii=False))
        return 0

    if args.backend == "native-cautreo":
        print("native-cautreo has no live HTTP path in this harness; "
              "cite VIVY-CAUTREO-GEMMA4-CHAT-188 and keep the gap isolated (§2.1).",
              file=sys.stderr)
        return 4

    registered = get_backend(args.backend)
    health = probe_health(args.backend, timeout_s=min(5.0, args.timeout_s))
    if args.backend == "llama-server":
        fn = make_llama_server_fn(
            base_url=args.base_url, model_alias=args.model_alias,
            timeout_s=args.timeout_s,
        )
        model_alias = args.model_alias or registered.identity.model_alias
    else:
        fn = make_unitary_fn(
            base_url=args.base_url, model=args.model_alias,
            timeout_s=args.timeout_s,
        )
        model_alias = args.model_alias or registered.identity.model_alias

    from training.backend_baseline import BackendIdentity
    identity = BackendIdentity(
        backend_id=registered.identity.backend_id,
        model_alias=model_alias,
        model_hash=str(health.get("model_hash") or registered.identity.model_hash or ""),
        config_hash=registered.identity.config_hash,
        base_url=args.base_url or registered.identity.base_url,
        extra={
            **dict(registered.identity.extra),
            "health": health,
            "prompt_hash_sample": prompt_sha256("What is 2 + 2? Reply with just the number."),
        },
    )

    report = run_known_answer_suite(identity, fn)
    suite_prompts = "\n".join(r.case_id for r in report.results)
    report_fingerprint = hashlib.sha256(suite_prompts.encode("utf-8")).hexdigest()

    write_suite_receipt(
        report, args.output, run_id=args.run_id, allow_replace=args.allow_replace,
    )
    print(json.dumps({
        "output": str(args.output),
        "status": report.status,
        "known_answer_accuracy": report.known_answer_accuracy,
        "n_scored": report.n_scored,
        "n_pass": report.n_pass,
        "safety_set_accuracy": report.safety_set_accuracy,
        "n_safety": report.n_safety,
        "n_safety_pass": report.n_safety_pass,
        "verdict_counts": report.verdict_counts,
        "backend": report.backend,
        "suite_fingerprint": report_fingerprint,
        "scope_limit": report.scope_limit,
    }, ensure_ascii=False, indent=2))

    if report.status == "NO_SCORED_CASES":
        return 2
    if report.status == "INFRA_INCOMPLETE":
        return 3
    if report.status == "SAFETY_SET_FAIL":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
