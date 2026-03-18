"""Tests for .gitignore support in ingest"""
from pathlib import Path
import tempfile
import shutil
import pytest

from agentrag.cli import _collect_files_respecting_gitignore


def test_collect_files_respects_gitignore_patterns():
    """Test that .gitignore patterns are respected"""
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create test structure
        (test_dir / "include.py").write_text("# include")
        (test_dir / "exclude.log").write_text("# exclude")
        (test_dir / "README.md").write_text("# include")
        
        # Create .gitignore
        (test_dir / ".gitignore").write_text("*.log\n")
        
        files = _collect_files_respecting_gitignore(test_dir)
        file_names = {f.name for f in files}
        
        assert "include.py" in file_names
        assert "README.md" in file_names
        assert ".gitignore" in file_names
        assert "exclude.log" not in file_names
    finally:
        shutil.rmtree(test_dir)


def test_collect_files_respects_directory_patterns():
    """Test that directory patterns in .gitignore are respected"""
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create nested structure
        (test_dir / "src").mkdir()
        (test_dir / "src" / "main.py").write_text("# include")
        
        (test_dir / "node_modules").mkdir()
        (test_dir / "node_modules" / "package.js").write_text("// exclude")
        
        (test_dir / "__pycache__").mkdir()
        (test_dir / "__pycache__" / "cache.pyc").write_text("# exclude")
        
        # Create .gitignore
        (test_dir / ".gitignore").write_text("node_modules/\n__pycache__/\n")
        
        files = _collect_files_respecting_gitignore(test_dir)
        # Normalize to POSIX separators so assertions are OS-independent.
        relative_paths = {f.relative_to(test_dir).as_posix() for f in files}
        
        assert "src/main.py" in relative_paths
        assert "node_modules/package.js" not in relative_paths
        assert "__pycache__/cache.pyc" not in relative_paths
    finally:
        shutil.rmtree(test_dir)


def test_collect_files_excludes_git_directory():
    """Test that .git directory is always excluded"""
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create .git directory
        (test_dir / ".git").mkdir()
        (test_dir / ".git" / "config").write_text("# git config")
        
        (test_dir / "src.py").write_text("# include")
        
        files = _collect_files_respecting_gitignore(test_dir)
        # Normalize to POSIX separators so assertions are OS-independent.
        relative_paths = {f.relative_to(test_dir).as_posix() for f in files}
        
        assert "src.py" in relative_paths
        assert ".git/config" not in relative_paths
    finally:
        shutil.rmtree(test_dir)


def test_collect_files_without_gitignore():
    """Test that files are collected normally when no .gitignore exists"""
    test_dir = Path(tempfile.mkdtemp())
    try:
        (test_dir / "file1.py").write_text("# file1")
        (test_dir / "file2.txt").write_text("# file2")
        
        files = _collect_files_respecting_gitignore(test_dir)
        file_names = {f.name for f in files}
        
        assert "file1.py" in file_names
        assert "file2.txt" in file_names
    finally:
        shutil.rmtree(test_dir)


def test_collect_files_with_wildcard_patterns():
    """Test wildcard patterns in .gitignore"""
    test_dir = Path(tempfile.mkdtemp())
    try:
        (test_dir / "src").mkdir()
        (test_dir / "src" / "main.py").write_text("# include")
        (test_dir / "src" / "test.pyc").write_text("# exclude")
        (test_dir / "data.json").write_text("{}")
        
        (test_dir / ".gitignore").write_text("*.pyc\n")
        
        files = _collect_files_respecting_gitignore(test_dir)
        # Normalize to POSIX separators so assertions are OS-independent.
        relative_paths = {f.relative_to(test_dir).as_posix() for f in files}
        
        assert "src/main.py" in relative_paths
        assert "data.json" in relative_paths
        assert "src/test.pyc" not in relative_paths
    finally:
        shutil.rmtree(test_dir)


def test_ingest_command_respects_gitignore(monkeypatch):
    """Integration test: ingest command respects .gitignore"""
    from agentrag.cli import ingest_command
    from agentrag.ingest import IngestResult
    
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create test structure
        (test_dir / "include.py").write_text("def foo(): pass")
        (test_dir / "exclude.log").write_text("log content")
        
        # Create .gitignore
        (test_dir / ".gitignore").write_text("*.log\n")
        
        # Mock the actual ingest to just count files
        ingested_files = []
        
        def mock_ingest_paths(paths, **kwargs):
            ingested_files.extend(paths)
            return IngestResult(0, 0, 0, 0, 0)
        
        def mock_ingest_urls(urls, **kwargs):
            return IngestResult(0, 0, 0, 0, 0)
        
        monkeypatch.setattr("agentrag.cli.ingest_paths", mock_ingest_paths)
        monkeypatch.setattr("agentrag.cli.ingest_urls", mock_ingest_urls)
        
        # Mock settings and dependencies
        from unittest.mock import MagicMock
        mock_settings = MagicMock()
        mock_settings.qdrant_url = "http://localhost:6333"
        mock_settings.qdrant_api_key = "test"
        mock_settings.collection_name = "test"
        mock_settings.enable_dimension_preflight = False
        
        monkeypatch.setattr("agentrag.cli.get_settings", lambda: mock_settings)
        monkeypatch.setattr("agentrag.cli._check_qdrant", lambda **kw: (True, "OK", None))
        monkeypatch.setattr("agentrag.cli._build_embedder_or_exit", lambda s: MagicMock(dimensions=384))
        
        # Run ingest command
        ingest_command(target=[str(test_dir)], dry_run=True)
        
        # Verify only non-ignored files were passed to ingest_paths
        file_names = {f.name for f in ingested_files}
        assert "include.py" in file_names
        assert "exclude.log" not in file_names
        
    finally:
        shutil.rmtree(test_dir)

