#!/usr/bin/env python3
"""Unit tests for pipeline/drive.py's file-matching logic, using a fake
client (same public interface as DriveClient) instead of real credentials
or network access — there's no live GCP project to test against yet
(Phase 3's GCP setup is a manual step for the human operator, see
DRIVE_SETUP.md). This only verifies the control flow this module actually
wrote: folder/file lookup, "not uploaded yet" handling, and which
canonical filename maps to which section. It does not exercise the real
Google API calls inside DriveClient itself (well-trodden library code,
lower risk than the by-hand logic here).

Run: python test_drive.py
"""
from pathlib import Path

from pipeline.config import load_config
from pipeline.drive import DriveError, download_section_file, download_month, find_month_folder


class FakeClient:
    """In-memory stand-in for DriveClient. folders: {(name, parent_id): id}.
    files: {(name, parent_id): id}. downloaded: list of (file_id, dest_path)
    for assertions."""

    def __init__(self, folders: dict, files: dict):
        self.folders = folders
        self.files = files
        self.downloaded = []

    def find_folder_id(self, name, parent_id=None):
        return self.folders.get((name, parent_id))

    def find_file_id(self, name, parent_id):
        return self.files.get((name, parent_id))

    def download(self, file_id, dest_path):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(f"fake content for {file_id}", encoding="utf-8")
        self.downloaded.append((file_id, dest_path))


def _assert(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print(f"  OK: {msg}")


def test_month_folder_missing_root():
    client = FakeClient(folders={}, files={})
    try:
        find_month_folder(client, "2026-07")
        raise AssertionError("expected DriveError when DHCUploads root is missing")
    except DriveError as e:
        _assert("not found" in str(e), "raises DriveError when DHCUploads root folder is missing")


def test_month_folder_missing_month():
    client = FakeClient(folders={("DHCUploads", None): "root123"}, files={})
    result = find_month_folder(client, "2026-07")
    _assert(result is None, "returns None (not an error) when the month subfolder doesn't exist yet")


def test_download_section_file_happy_path():
    cfg = load_config()
    client = FakeClient(
        folders={("DHCUploads", None): "root123", ("2026-07", "root123"): "month456"},
        files={("ECR.xlsx", "month456"): "file789"},
    )
    dest_dir = Path("test_scratch_dl")
    path = download_section_file(client, "2026-07", "ecr", dest_dir, cfg)
    _assert(path == dest_dir / "2026-07" / "ECR.xlsx", "downloads to the expected canonical path")
    _assert(client.downloaded == [("file789", path)], "calls download() with the right file id and destination")
    _assert(path.read_text() == "fake content for file789", "downloaded file has the expected (fake) content")
    path.unlink()
    path.parent.rmdir()
    dest_dir.rmdir()


def test_download_section_file_not_uploaded():
    cfg = load_config()
    client = FakeClient(
        folders={("DHCUploads", None): "root123", ("2026-07", "root123"): "month456"},
        files={},  # ECR.xlsx not present
    )
    path = download_section_file(client, "2026-07", "ecr", Path("test_scratch_dl"), cfg)
    _assert(path is None, "returns None (not an error) when the section's file hasn't been uploaded yet")
    _assert(client.downloaded == [], "does not attempt a download when the file is missing")


def test_download_month_mixed_availability():
    cfg = load_config()
    client = FakeClient(
        folders={("DHCUploads", None): "root123", ("2026-07", "root123"): "month456"},
        files={
            ("ECR.xlsx", "month456"): "f1",
            ("POSB.xlsx", "month456"): "f2",
            # pli/rpli/booking files intentionally absent
        },
    )
    dest_dir = Path("test_scratch_dl2")
    results = download_month(client, "2026-07", dest_dir, cfg)
    _assert(set(results) == set(cfg["sections"]), "returns an entry for every configured section")
    _assert(results["ecr"] is not None and results["posb"] is not None,
            "sections with an uploaded file get a real path")
    _assert(results["pli"] is None and results["rpli"] is None,
            "sections without an uploaded file get None, not an error")
    _assert(len(client.downloaded) == 2, "only downloads the files that actually exist")
    # cleanup
    for p in dest_dir.rglob("*"):
        if p.is_file():
            p.unlink()
    for p in sorted(dest_dir.rglob("*"), reverse=True):
        if p.is_dir():
            p.rmdir()
    dest_dir.rmdir()


def test_download_month_no_month_folder():
    cfg = load_config()
    client = FakeClient(folders={("DHCUploads", None): "root123"}, files={})
    results = download_month(client, "2026-07", Path("test_scratch_dl3"), cfg)
    _assert(all(v is None for v in results.values()),
            "every section is None when the month folder doesn't exist at all yet")


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        print(f"{t.__name__}:")
        t()
    print(f"\n{len(tests)} test(s) passed.")


if __name__ == "__main__":
    main()
