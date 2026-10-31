# Cisco Configuration Backup

Stores timestamped device configuration snapshots, records their SHA-256 digests, compares saved versions, and removes older snapshots according to a retention limit.

## Main entry points

- `src.backup.BackupRecord`
- `src.backup.BackupManager` (`backup_device, compare_backups, rotate_backups`)

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The project uses the Python standard library; no third-party package is required.

## Scope

The manager writes local files. Device access and configuration collection are expected to be handled by the caller.
