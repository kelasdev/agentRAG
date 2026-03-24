from __future__ import annotations

import fnmatch
import hashlib
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_IGNORES = (
    ".git/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    "*.py[cod]",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.swp",
    "*.swo",
    "*~",
)


class IgnoreMatcher:
    """Resolve ignore rules using Git when available, with a simple fallback."""

    def __init__(self, watch_path: Path):
        self.watch_path = watch_path.resolve()
        self.repo_root = self._detect_repo_root()
        self.patterns = self._load_fallback_patterns()
        self.cache: Dict[str, bool] = {}

    def _detect_repo_root(self) -> Path | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=self.watch_path,
                capture_output=True,
                text=True,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

        repo_root = Path(result.stdout.strip()).resolve()
        try:
            self.watch_path.relative_to(repo_root)
        except ValueError:
            return None
        return repo_root

    def _load_fallback_patterns(self) -> list[str]:
        patterns = list(DEFAULT_IGNORES)
        gitignore_path = self.watch_path / ".gitignore"
        if gitignore_path.exists():
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                entry = line.strip()
                if not entry or entry.startswith("#") or entry.startswith("!"):
                    continue
                patterns.append(entry.replace("\\", "/"))
        return patterns

    def refresh(self) -> None:
        self.patterns = self._load_fallback_patterns()
        self.cache.clear()

    def is_ignored(self, path: Path) -> bool:
        path = path.resolve()
        cache_key = str(path)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        ignored = self._git_is_ignored(path)
        if ignored is None:
            ignored = self._fallback_is_ignored(path)

        self.cache[cache_key] = ignored
        return ignored

    def _git_is_ignored(self, path: Path) -> bool | None:
        if self.repo_root is None:
            return None

        try:
            rel_path = path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return None

        try:
            result = subprocess.run(
                ["git", "check-ignore", "-q", "--no-index", "--", rel_path],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None

        if result.returncode == 0:
            return True
        if result.returncode == 1:
            return False
        return None

    def _fallback_is_ignored(self, path: Path) -> bool:
        try:
            relative = path.relative_to(self.watch_path).as_posix()
        except ValueError:
            return False

        for partial in self._iter_path_segments(relative, path.is_dir()):
            if any(self._match_pattern(partial, pattern) for pattern in self.patterns):
                return True
        return False

    @staticmethod
    def _iter_path_segments(relative_path: str, is_dir: bool) -> list[str]:
        parts = relative_path.split("/")
        segments: list[str] = []
        for index in range(len(parts)):
            partial = "/".join(parts[: index + 1])
            current_is_dir = index < len(parts) - 1 or is_dir
            segments.append(f"{partial}/" if current_is_dir else partial)
        return segments

    @staticmethod
    def _match_pattern(path_value: str, pattern: str) -> bool:
        directory_only = pattern.endswith("/")
        candidate = path_value
        normalized_pattern = pattern.rstrip("/")

        if directory_only and not candidate.endswith("/"):
            return False

        candidate = candidate.rstrip("/")
        anchored = normalized_pattern.startswith("/")
        if anchored:
            normalized_pattern = normalized_pattern[1:]

        candidate_parts = candidate.split("/")
        pattern_parts = normalized_pattern.split("/")

        if "*" in normalized_pattern or "?" in normalized_pattern:
            if anchored:
                return fnmatch.fnmatch(candidate, normalized_pattern)
            if len(pattern_parts) == 1:
                return any(fnmatch.fnmatch(part, normalized_pattern) for part in candidate_parts)
            return fnmatch.fnmatch(candidate, normalized_pattern) or any(
                fnmatch.fnmatch(
                    "/".join(candidate_parts[i : i + len(pattern_parts)]),
                    normalized_pattern,
                )
                for i in range(len(candidate_parts) - len(pattern_parts) + 1)
            )

        if anchored:
            return candidate == normalized_pattern or candidate.startswith(f"{normalized_pattern}/")
        return normalized_pattern in candidate_parts or candidate == normalized_pattern


class GitignoreAwareWatcher(FileSystemEventHandler):
    """Watch code changes, batch them, and trigger agentRAG ingest."""

    def __init__(
        self,
        watch_path: Path,
        recursive: bool = True,
        batch_size: int = 5,
        debounce_seconds: float = 3.0,
        dry_run: bool = False,
        allowed_extensions: set[str] | None = None,
    ):
        self.watch_path = watch_path.resolve()
        self.recursive = recursive
        self.batch_size = batch_size
        self.debounce_seconds = debounce_seconds
        self.dry_run = dry_run
        self.allowed_extensions = allowed_extensions or set()
        self.ignore_matcher = IgnoreMatcher(self.watch_path)
        self.command_cwd = self.ignore_matcher.repo_root or Path.cwd()
        self.pending_files: set[Path] = set()
        self.file_hashes: Dict[Path, str] = {}
        self.last_event_time = time.monotonic()

        self._init_file_hashes()

    def _init_file_hashes(self) -> None:
        logger.info("Scanning existing files...")
        tracked = 0
        for file_path in self.watch_path.rglob("*"):
            if not file_path.is_file():
                continue
            if self.ignore_matcher.is_ignored(file_path):
                continue
            if self.allowed_extensions and file_path.suffix.lower() not in self.allowed_extensions:
                continue
            file_hash = self._compute_hash(file_path)
            if file_hash:
                self.file_hashes[file_path] = file_hash
                tracked += 1
        logger.info("Tracked %s files", tracked)

    def _compute_hash(self, file_path: Path) -> str:
        try:
            hasher = hashlib.md5()
            with file_path.open("rb") as file_handle:
                for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return ""

    def _queue_file(self, file_path: Path, event: FileSystemEvent) -> None:
        if not file_path.exists():
            return
        if self.allowed_extensions and file_path.suffix.lower() not in self.allowed_extensions:
            return

        new_hash = self._compute_hash(file_path)
        if not new_hash:
            return

        old_hash = self.file_hashes.get(file_path)
        if new_hash == old_hash:
            return

        self.file_hashes[file_path] = new_hash
        self.pending_files.add(file_path)
        self.last_event_time = time.monotonic()
        self._log_event(event, file_path)

        if len(self.pending_files) >= self.batch_size:
            self._trigger_ingest()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        event_type = event.event_type
        src_path = Path(event.src_path).resolve()
        dest_raw = getattr(event, "dest_path", None)
        dest_path = Path(dest_raw).resolve() if dest_raw else None

        if src_path.name == ".gitignore":
            self.ignore_matcher.refresh()
        if dest_path and dest_path.name == ".gitignore":
            self.ignore_matcher.refresh()

        if event_type == "deleted":
            self.file_hashes.pop(src_path, None)
            self.pending_files.discard(src_path)
            if not self.ignore_matcher.is_ignored(src_path):
                self._log_event(event, src_path)
            return

        if event_type == "moved":
            self.file_hashes.pop(src_path, None)
            self.pending_files.discard(src_path)
            if dest_path is None or self.ignore_matcher.is_ignored(dest_path):
                return
            self._queue_file(dest_path, event)
            return

        if self.ignore_matcher.is_ignored(src_path):
            return

        self._queue_file(src_path, event)

    def _trigger_ingest(self) -> None:
        if not self.pending_files:
            return

        files_to_ingest = sorted(self.pending_files)
        self.pending_files.clear()

        logger.info("")
        logger.info("Triggering ingest for %s files...", len(files_to_ingest))

        cmd = [sys.executable, "-m", "agentrag.cli", "ingest", *[str(path) for path in files_to_ingest]]

        if self.dry_run:
            for file_path in files_to_ingest:
                logger.info("  DRY-RUN %s", file_path.relative_to(self.watch_path).as_posix())
            logger.info("Dry-run enabled, ingest command skipped")
            logger.info("")
            return

        try:
            result = subprocess.run(
                cmd,
                cwd=self.command_cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            for file_path in files_to_ingest:
                logger.info("  INGESTED %s", file_path.relative_to(self.watch_path).as_posix())
            if result.stdout.strip():
                logger.info(result.stdout.strip())
        except subprocess.CalledProcessError as exc:
            logger.error("Ingest command failed with exit code %s", exc.returncode)
            if exc.stdout.strip():
                logger.error(exc.stdout.strip())
            if exc.stderr.strip():
                logger.error(exc.stderr.strip())

        logger.info("Ingest cycle completed")
        logger.info("")

    def check_pending(self) -> None:
        if self.pending_files and (time.monotonic() - self.last_event_time) >= self.debounce_seconds:
            self._trigger_ingest()

    def _log_event(self, event: FileSystemEvent, path_for_log: Path) -> None:
        try:
            relative = path_for_log.relative_to(self.watch_path).as_posix()
        except ValueError:
            relative = str(path_for_log)

        if event.event_type == "moved" and getattr(event, "dest_path", None):
            src_display = Path(event.src_path)
            try:
                src_relative = src_display.resolve().relative_to(self.watch_path).as_posix()
            except ValueError:
                src_relative = str(src_display)
            logger.info("%-8s | %s -> %s", event.event_type.upper(), src_relative, relative)
            return

        logger.info("%-8s | %s", event.event_type.upper(), relative)


def parse_extensions(raw_value: str) -> set[str]:
    extensions: set[str] = set()
    for item in raw_value.split(","):
        value = item.strip().lower()
        if not value:
            continue
        extensions.add(value if value.startswith(".") else f".{value}")
    return extensions


def start_watching(
    path: str,
    recursive: bool = True,
    batch_size: int = 5,
    debounce_seconds: float = 3.0,
    dry_run: bool = False,
    allowed_extensions: set[str] | None = None,
) -> None:
    watch_path = Path(path).resolve()
    if not watch_path.exists():
        raise FileNotFoundError(f"Path tidak ditemukan: {watch_path}")
    if not watch_path.is_dir():
        raise NotADirectoryError(f"Path bukan direktori: {watch_path}")

    event_handler = GitignoreAwareWatcher(
        watch_path=watch_path,
        recursive=recursive,
        batch_size=batch_size,
        debounce_seconds=debounce_seconds,
        dry_run=dry_run,
        allowed_extensions=allowed_extensions,
    )
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=recursive)

    logger.info("Mulai memantau: %s", watch_path)
    logger.info("Recursive: %s", "Ya" if recursive else "Tidak")
    logger.info("Ignore rules: Git-aware" if event_handler.ignore_matcher.repo_root else "Ignore rules: fallback")
    logger.info("Batch size: %s files", batch_size)
    logger.info("Debounce: %ss", debounce_seconds)
    logger.info("Dry run: %s", "Ya" if dry_run else "Tidak")
    logger.info(
        "Extensions: %s",
        ", ".join(sorted(allowed_extensions)) if allowed_extensions else "Semua file",
    )
    logger.info("Interpreter: %s", sys.executable)
    logger.info("Tekan Ctrl+C untuk berhenti")
    logger.info("")

    observer.start()
    try:
        while True:
            time.sleep(1)
            event_handler.check_pending()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Menghentikan pemantauan...")
        event_handler._trigger_ingest()
        observer.stop()

    observer.join()
    logger.info("Pemantauan dihentikan")
