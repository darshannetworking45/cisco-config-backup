"""Cisco Configuration Backup and Deduplication Engine."""

from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("config_backup")


@dataclass
class BackupRecord:
    device: str
    timestamp: str
    sha256: str
    filename: str
    line_count: int


class BackupManager:
    """Manages file-based configuration archives with cryptographic deduplication."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_index.json"
        self.index: Dict[str, List[Dict]] = self._load_index()

    def _load_index(self) -> Dict[str, List[Dict]]:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

    def backup_device(self, device_name: str, config_text: str, timestamp: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Saves a configuration snapshot. If the cryptographic hash matches the previous
        backup, skips disk write to save space and reduce audit noise.
        """
        device_dir = self.backup_dir / device_name
        device_dir.mkdir(parents=True, exist_ok=True)

        cleaned_text = config_text.strip()
        sha256 = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

        records = self.index.get(device_name, [])
        if records:
            last = records[-1]
            if last["sha256"] == sha256:
                return False, f"Config for {device_name} is unchanged (SHA: {sha256[:8]}). Skipping save."

        ts_str = (timestamp or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{device_name}_{ts_str}.cfg"
        filepath = device_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cleaned_text + "\n")

        rec = BackupRecord(
            device=device_name,
            timestamp=ts_str,
            sha256=sha256,
            filename=filename,
            line_count=len(cleaned_text.splitlines())
        )
        if device_name not in self.index:
            self.index[device_name] = []
        self.index[device_name].append(rec.__dict__)
        self._save_index()

        return True, f"Saved backup to {filename} ({rec.line_count} lines)"

    def compare_backups(self, device_name: str, idx1: int = -2, idx2: int = -1) -> str:
        """Returns unified diff between two backup revisions."""
        records = self.index.get(device_name, [])
        if len(records) < 2:
            return f"Insufficient backups for device {device_name} (found {len(records)})"

        file1 = self.backup_dir / device_name / records[idx1]["filename"]
        file2 = self.backup_dir / device_name / records[idx2]["filename"]

        with open(file1, "r", encoding="utf-8") as f:
            lines1 = f.readlines()
        with open(file2, "r", encoding="utf-8") as f:
            lines2 = f.readlines()

        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=records[idx1]["filename"],
            tofile=records[idx2]["filename"]
        )
        return "".join(diff)

    def rotate_backups(self, device_name: str, keep_last: int = 5) -> int:
        """Enforces retention policy by purging older archives."""
        records = self.index.get(device_name, [])
        if len(records) <= keep_last:
            return 0
        to_delete = records[:-keep_last]
        kept = records[-keep_last:]

        deleted_count = 0
        for rec in to_delete:
            p = self.backup_dir / device_name / rec["filename"]
            if p.exists():
                p.unlink()
                deleted_count += 1

        self.index[device_name] = kept
        self._save_index()
        return deleted_count
