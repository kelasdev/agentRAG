#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


@contextmanager
def _suppress_stderr(enabled: bool):
    if not enabled:
        yield
        return
    stderr_fd = 2
    saved_stderr_fd = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(saved_stderr_fd)


@contextmanager
def _suppress_known_unraisable_warnings(enabled: bool):
    if not enabled:
        yield
        return
    original = sys.unraisablehook

    def _hook(unraisable: SimpleNamespace) -> None:
        exc = getattr(unraisable, "exc_value", None)
        msg = str(exc) if exc else ""
        if (
            isinstance(exc, AttributeError)
            and "LlamaModel" in msg
            and "sampler" in msg
        ):
            return
        original(unraisable)

    sys.unraisablehook = _hook
    try:
        yield
    finally:
        sys.unraisablehook = original


def _test_completion(model_path: str, n_threads: int, n_ctx: int, quiet_backend: bool) -> tuple[bool, str]:
    try:
        from llama_cpp import Llama  # type: ignore

        with _suppress_stderr(quiet_backend):
            model = Llama(
                model_path=model_path,
                n_threads=n_threads,
                n_ctx=n_ctx,
                n_gpu_layers=0,
                verbose=False,
            )
            out = model.create_completion(
                prompt="Reply with: OK",
                max_tokens=8,
                temperature=0.0,
            )
        text = str(out["choices"][0]["text"]).strip().replace("\n", " ")
        return True, text[:60] if text else "no_text"
    except Exception as exc:
        return False, str(exc)


def _test_embedding(model_path: str, n_threads: int, n_ctx: int, quiet_backend: bool) -> tuple[bool, str]:
    try:
        from llama_cpp import Llama  # type: ignore

        with _suppress_stderr(quiet_backend):
            model = Llama(
                model_path=model_path,
                embedding=True,
                n_threads=n_threads,
                n_ctx=n_ctx,
                n_gpu_layers=0,
                verbose=False,
            )
            out = model.create_embedding("hello embedding")
        dim = len(out["data"][0]["embedding"])
        return True, f"dim={dim}"
    except Exception as exc:
        return False, str(exc)


def _status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test local GGUF models with llama-cpp-python (completion + embedding)."
    )
    parser.add_argument(
        "--models-dir",
        default="/home/kelasdev/models",
        help="Directory containing .gguf models (default: /home/kelasdev/models)",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="Specific model path to test (can be passed multiple times).",
    )
    parser.add_argument("--n-threads", type=int, default=4, help="llama.cpp n_threads")
    parser.add_argument("--n-ctx", type=int, default=512, help="llama.cpp n_ctx")
    parser.add_argument(
        "--quiet-backend",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Suppress backend stderr noise (default: true).",
    )
    args = parser.parse_args()

    model_paths: list[Path] = []
    if args.model:
        model_paths.extend(Path(p).expanduser() for p in args.model)
    else:
        model_paths.extend(sorted(Path(args.models_dir).expanduser().glob("*.gguf")))

    if not model_paths:
        print("No .gguf models found.")
        return 1

    print(f"Testing {len(model_paths)} model(s)\n")
    print("MODEL | COMPLETION | EMBEDDING")
    print("-" * 100)

    all_ok = True
    for path in model_paths:
        with _suppress_known_unraisable_warnings(True):
            completion_ok, completion_msg = _test_completion(
                str(path), args.n_threads, args.n_ctx, args.quiet_backend
            )
            embedding_ok, embedding_msg = _test_embedding(
                str(path), args.n_threads, args.n_ctx, args.quiet_backend
            )
        print(
            f"{path.name} | {_status(completion_ok)} ({completion_msg}) | "
            f"{_status(embedding_ok)} ({embedding_msg})"
        )
        if not (completion_ok or embedding_ok):
            all_ok = False

    print("\nLegend: model is usable if at least one required mode for your pipeline is OK.")
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
