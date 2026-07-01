"""Tests for the change detection module.

Verifies that ``ChangeDetector`` correctly computes SHA-256 hashes, tracks
file state in its registry, and returns the correct ``ChangeStatus`` for
new, modified, and unchanged files.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from atlasiq.backend.core.exceptions import DocumentNotFoundError
from atlasiq.ingestion.change_detector import ChangeDetector, ChangeStatus

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def detector() -> ChangeDetector:
    """Provide a fresh ChangeDetector with an empty registry."""
    return ChangeDetector()


# ── Hash computation ─────────────────────────────────────────────────────────


class TestHashComputation:
    """Tests for SHA-256 hash computation."""

    def test_hash_matches_hashlib(self, detector: ChangeDetector, tmp_path: Path) -> None:
        """Computed hash should match Python's hashlib.sha256 directly."""
        content = b"Hello, AtlasIQ!"
        file = tmp_path / "test.txt"
        file.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert detector._compute_hash(file) == expected

    def test_hash_is_deterministic(self, detector: ChangeDetector, tmp_path: Path) -> None:
        """Hashing the same file twice should produce the same result."""
        file = tmp_path / "stable.txt"
        file.write_text("consistent content", encoding="utf-8")
        hash1 = detector._compute_hash(file)
        hash2 = detector._compute_hash(file)
        assert hash1 == hash2

    def test_different_content_different_hash(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """Files with different content should produce different hashes."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_text("content A", encoding="utf-8")
        file_b.write_text("content B", encoding="utf-8")
        assert detector._compute_hash(file_a) != detector._compute_hash(file_b)

    def test_empty_file_hash(self, detector: ChangeDetector, tmp_path: Path) -> None:
        """An empty file should have the known SHA-256 hash of empty bytes."""
        file = tmp_path / "empty.txt"
        file.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert detector._compute_hash(file) == expected

    def test_hash_is_64_char_hex(self, detector: ChangeDetector, tmp_path: Path) -> None:
        """SHA-256 hex digest should be exactly 64 lowercase hex characters."""
        file = tmp_path / "check.txt"
        file.write_text("data", encoding="utf-8")
        h = detector._compute_hash(file)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_large_file_hash(self, detector: ChangeDetector, tmp_path: Path) -> None:
        """Hashing a file larger than the chunk size should still work."""
        file = tmp_path / "large.bin"
        # Write 256 KB of data (larger than the 64 KB chunk size)
        file.write_bytes(b"x" * 256 * 1024)
        expected = hashlib.sha256(b"x" * 256 * 1024).hexdigest()
        assert detector._compute_hash(file) == expected

    def test_hash_nonexistent_file_raises(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """Hashing a missing file should raise DocumentNotFoundError."""
        missing = tmp_path / "ghost.pdf"
        with pytest.raises(DocumentNotFoundError, match="file not found"):
            detector._compute_hash(missing)


# ── Change detection (check) ────────────────────────────────────────────────


class TestCheckStatus:
    """Tests for the check() method's decision logic."""

    def test_new_file_returns_new(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """A file not in the registry should return NEW."""
        file = tmp_path / "fresh.txt"
        file.write_text("brand new", encoding="utf-8")
        assert detector.check(file) == ChangeStatus.NEW

    def test_unchanged_file_returns_unchanged(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """A file registered and not modified should return UNCHANGED."""
        file = tmp_path / "stable.txt"
        file.write_text("original", encoding="utf-8")
        detector.register(file)
        assert detector.check(file) == ChangeStatus.UNCHANGED

    def test_modified_file_returns_modified(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """A file registered then modified should return MODIFIED."""
        file = tmp_path / "changing.txt"
        file.write_text("version 1", encoding="utf-8")
        detector.register(file)
        file.write_text("version 2", encoding="utf-8")
        assert detector.check(file) == ChangeStatus.MODIFIED

    def test_empty_registry_always_new(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """A fresh detector with no registrations should return NEW for all."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_text("A", encoding="utf-8")
        file_b.write_text("B", encoding="utf-8")
        assert detector.check(file_a) == ChangeStatus.NEW
        assert detector.check(file_b) == ChangeStatus.NEW


# ── Registration ─────────────────────────────────────────────────────────────


class TestRegister:
    """Tests for the register() method."""

    def test_register_returns_hash(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """register() should return the SHA-256 hex digest."""
        file = tmp_path / "doc.txt"
        content = b"register me"
        file.write_bytes(content)
        returned_hash = detector.register(file)
        expected = hashlib.sha256(content).hexdigest()
        assert returned_hash == expected

    def test_register_then_check_unchanged(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """After register(), check() should return UNCHANGED."""
        file = tmp_path / "tracked.txt"
        file.write_text("tracked", encoding="utf-8")
        detector.register(file)
        assert detector.check(file) == ChangeStatus.UNCHANGED

    def test_re_register_updates_hash(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """Re-registering after modification should update the stored hash."""
        file = tmp_path / "updated.txt"
        file.write_text("v1", encoding="utf-8")
        detector.register(file)
        file.write_text("v2", encoding="utf-8")
        assert detector.check(file) == ChangeStatus.MODIFIED
        detector.register(file)
        assert detector.check(file) == ChangeStatus.UNCHANGED

    def test_register_nonexistent_file_raises(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """Registering a missing file should raise DocumentNotFoundError."""
        missing = tmp_path / "nope.pdf"
        with pytest.raises(DocumentNotFoundError, match="file not found"):
            detector.register(missing)


# ── Multiple file tracking ───────────────────────────────────────────────────


class TestMultipleFiles:
    """Tests verifying that multiple files are tracked independently."""

    def test_independent_tracking(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """Modifying file A should not affect the status of file B."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_text("A original", encoding="utf-8")
        file_b.write_text("B original", encoding="utf-8")
        detector.register(file_a)
        detector.register(file_b)

        # Modify only file A
        file_a.write_text("A modified", encoding="utf-8")

        assert detector.check(file_a) == ChangeStatus.MODIFIED
        assert detector.check(file_b) == ChangeStatus.UNCHANGED

    def test_many_files_tracked(
        self, detector: ChangeDetector, tmp_path: Path
    ) -> None:
        """The detector should handle tracking many files correctly."""
        files = []
        for i in range(20):
            f = tmp_path / f"file_{i}.txt"
            f.write_text(f"content {i}", encoding="utf-8")
            detector.register(f)
            files.append(f)

        # All should be UNCHANGED
        for f in files:
            assert detector.check(f) == ChangeStatus.UNCHANGED

        # Modify one
        files[10].write_text("changed content", encoding="utf-8")
        assert detector.check(files[10]) == ChangeStatus.MODIFIED
        assert detector.check(files[0]) == ChangeStatus.UNCHANGED
        assert detector.check(files[19]) == ChangeStatus.UNCHANGED
