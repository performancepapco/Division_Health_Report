"""Google Drive integration — pulls canonical section files from
DHCUploads/<YYYY-MM>/ (the folder Apps Script moves/renames uploads into,
see docs/DRIVE_SETUP.md) for a given month.

Service-account auth only, no OAuth flow, no user interaction. The
service account is shared VIEW-ONLY on exactly one folder (DHCUploads) —
it can't see or touch anything else in Drive.

Credentials come from one of:
  - GDRIVE_SA_KEY       env var, the raw JSON key content (how GitHub
                        Actions secrets get injected — see
                        .github/workflows/*.yml)
  - GDRIVE_SA_KEY_FILE  env var, a path to the key file on disk (local
                        testing)
GDRIVE_SA_KEY takes precedence if both are set. Neither is ever logged or
written anywhere by this module.

The Drive API calls are isolated behind DriveClient so the file-matching
logic (which canonical filename belongs to which section, per
pipeline_config.yaml) can be unit-tested with a fake client — see
test_drive.py — without needing real credentials or network access.
"""
import json
import os
from pathlib import Path

DHCUPLOADS_FOLDER_NAME = "DHCUploads"
FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveError(Exception):
    pass


class DriveClient:
    """Thin wrapper around the Drive v3 API — the only class that actually
    talks to Google. Everything else in this module takes a DriveClient
    (or a fake with the same interface) as a parameter, so it's testable
    without network access."""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_env(cls) -> "DriveClient":
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        raw = os.environ.get("GDRIVE_SA_KEY")
        if raw:
            info = json.loads(raw)
            creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        else:
            key_file = os.environ.get("GDRIVE_SA_KEY_FILE")
            if not key_file:
                raise DriveError(
                    "No credentials found — set GDRIVE_SA_KEY (JSON content, used in CI) "
                    "or GDRIVE_SA_KEY_FILE (path to the key file, for local testing)."
                )
            creds = service_account.Credentials.from_service_account_file(key_file, scopes=scopes)
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return cls(service)

    def find_folder_id(self, name: str, parent_id: str | None = None) -> str | None:
        q = f"mimeType='{FOLDER_MIME}' and name='{_escape(name)}' and trashed=false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        resp = self._service.files().list(q=q, fields="files(id,name)", pageSize=10).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    def find_file_id(self, name: str, parent_id: str) -> str | None:
        q = f"name='{_escape(name)}' and '{parent_id}' in parents and trashed=false"
        resp = self._service.files().list(
            q=q, fields="files(id,name,modifiedTime)", pageSize=10, orderBy="modifiedTime desc"
        ).execute()
        files = resp.get("files", [])
        return files[0]["id"] if files else None

    def download(self, file_id: str, dest_path: Path) -> None:
        from googleapiclient.http import MediaIoBaseDownload

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        request = self._service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()


def _escape(name: str) -> str:
    # Drive query strings escape single quotes by doubling the backslash.
    return name.replace("'", r"\'")


def find_month_folder(client: DriveClient, month_iso: str) -> str | None:
    root_id = client.find_folder_id(DHCUPLOADS_FOLDER_NAME)
    if not root_id:
        raise DriveError(
            f"Folder '{DHCUPLOADS_FOLDER_NAME}' not found — either it hasn't been shared "
            f"with the service account yet, or the name doesn't match exactly."
        )
    return client.find_folder_id(month_iso, parent_id=root_id)


def download_section_file(client: DriveClient, month_iso: str, section_name: str,
                           dest_dir: Path, cfg: dict) -> Path | None:
    """Downloads the one canonical file for a single section/month. Returns
    None (not an error) if the month folder or that section's file doesn't
    exist yet — an upload simply hasn't happened, which is routine, not
    exceptional."""
    section_cfg = cfg["sections"][section_name]
    filename = section_cfg["canonical_filename"]

    month_folder_id = find_month_folder(client, month_iso)
    if not month_folder_id:
        return None
    file_id = client.find_file_id(filename, month_folder_id)
    if not file_id:
        return None

    dest = dest_dir / month_iso / filename
    client.download(file_id, dest)
    return dest


def download_month(client: DriveClient, month_iso: str, dest_dir: Path, cfg: dict) -> dict:
    """Downloads every canonical file available for a month. Returns
    {section_name: Path or None} — None means that section hasn't been
    uploaded yet for this month, which callers (e.g. the daily cron) should
    treat as "skip this section this run", not a failure."""
    month_folder_id = find_month_folder(client, month_iso)
    if not month_folder_id:
        return {name: None for name in cfg["sections"]}

    out = {}
    for section_name, section_cfg in cfg["sections"].items():
        filename = section_cfg["canonical_filename"]
        file_id = client.find_file_id(filename, month_folder_id)
        if not file_id:
            out[section_name] = None
            continue
        dest = dest_dir / month_iso / filename
        client.download(file_id, dest)
        out[section_name] = dest
    return out
