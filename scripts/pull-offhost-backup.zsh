#!/bin/zsh

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

remote_host="${PLUGIN_HUB_BACKUP_REMOTE_HOST:-tencent-lighthouse}"
remote_dir="${PLUGIN_HUB_BACKUP_REMOTE_DIR:-/opt/plugin-hub/backups}"
destination_dir="${PLUGIN_HUB_BACKUP_DESTINATION_DIR:-$HOME/.codex/backups/plugin_hub}"
recipient_file="${PLUGIN_HUB_BACKUP_RECIPIENT_FILE:-$HOME/.config/plugin-hub/offhost-backup-recipient.txt}"
keychain_service="${PLUGIN_HUB_BACKUP_KEYCHAIN_SERVICE:-plugin-hub-offhost-backup-age-identity}"
keychain_account="${PLUGIN_HUB_BACKUP_KEYCHAIN_ACCOUNT:-plugin-hub}"
retention_count="${PLUGIN_HUB_BACKUP_RETENTION_COUNT:-30}"

age_bin="${PLUGIN_HUB_AGE_BIN:-/opt/homebrew/bin/age}"
ssh_bin="${PLUGIN_HUB_SSH_BIN:-/usr/bin/ssh}"
security_bin="${PLUGIN_HUB_SECURITY_BIN:-/usr/bin/security}"
python_bin="${PLUGIN_HUB_PYTHON_BIN:-$(command -v python3)}"

if [[ ! "$retention_count" =~ '^[0-9]+$' ]] || (( retention_count < 2 )); then
  print -u2 -- "offhost_backup_error=invalid_retention_count"
  exit 2
fi
if [[ ! -x "$age_bin" || ! -x "$ssh_bin" || ! -x "$security_bin" ]]; then
  print -u2 -- "offhost_backup_error=required_tool_missing"
  exit 2
fi
if [[ ! -s "$recipient_file" ]]; then
  print -u2 -- "offhost_backup_error=recipient_file_missing"
  exit 2
fi

umask 077
mkdir -p "$destination_dir"
chmod 0700 "$destination_dir"

lock_dir="$destination_dir/.pull.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  print -- "offhost_backup_status=already_running"
  exit 0
fi

temporary_dir=""
temporary_archive=""
temporary_metadata=""

cleanup() {
  if [[ -n "$temporary_dir" && -d "$temporary_dir" ]]; then
    rm -rf "$temporary_dir"
  fi
  if [[ -n "$temporary_archive" ]]; then
    rm -f "$temporary_archive"
  fi
  if [[ -n "$temporary_metadata" ]]; then
    rm -f "$temporary_metadata"
  fi
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

latest_manifest="$($ssh_bin "$remote_host" /bin/bash -s -- "$remote_dir" <<'REMOTE'
set -euo pipefail
backup_dir=$1
sudo -n find "$backup_dir" -maxdepth 1 -type f -name 'plugin_hub_*.manifest.json' \
  -printf '%T@ %f\n' | sort -nr | head -1 | cut -d' ' -f2-
REMOTE
)"

if [[ -z "$latest_manifest" || "$latest_manifest" == */* || "$latest_manifest" != plugin_hub_*.manifest.json ]]; then
  print -u2 -- "offhost_backup_error=invalid_remote_manifest_name"
  exit 1
fi

database_file="${latest_manifest%.manifest.json}.db"
archive_file="${database_file%.db}.tar.age"
metadata_file="${database_file%.db}.offhost.json"
final_archive="$destination_dir/$archive_file"
final_metadata="$destination_dir/$metadata_file"
recipient="$(awk 'NF && $1 !~ /^#/ {print $1; exit}' "$recipient_file")"

if [[ -z "$recipient" || "$recipient" != age1* ]]; then
  print -u2 -- "offhost_backup_error=invalid_age_recipient"
  exit 2
fi

verify_archive() {
  local archive_path=$1
  local identity
  local identity_file
  local restore_dir

  temporary_dir="$(mktemp -d /tmp/plugin-hub-offhost-verify.XXXXXX)"
  chmod 0700 "$temporary_dir"
  identity_file="$temporary_dir/identity.txt"
  restore_dir="$temporary_dir/restore"
  mkdir "$restore_dir"
  chmod 0700 "$restore_dir"

  identity="$($security_bin find-generic-password \
    -s "$keychain_service" -a "$keychain_account" -w)"
  if [[ -z "$identity" || "$identity" != AGE-SECRET-KEY-* ]]; then
    unset identity
    print -u2 -- "offhost_backup_error=age_identity_unavailable"
    return 1
  fi
  print -r -- "$identity" > "$identity_file"
  unset identity
  chmod 0600 "$identity_file"

  "$age_bin" --decrypt -i "$identity_file" "$archive_path" | \
    /usr/bin/tar -xf - -C "$restore_dir"

  "$python_bin" - "$restore_dir/$database_file" "$restore_dir/$latest_manifest" <<'PY'
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

database_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
connection = sqlite3.connect(
    f"{database_path.resolve().as_uri()}?mode=ro&immutable=1",
    uri=True,
)
try:
    connection.execute("PRAGMA query_only=ON")
    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    foreign_key_issues = len(connection.execute("PRAGMA foreign_key_check").fetchall())
    counts = {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in ("collection_runs", "raw_source_items", "canonical_voc_units")
    }
finally:
    connection.close()

assert manifest["backup_file"] == database_path.name
assert manifest["sha256"] == digest
assert manifest["bytes"] == database_path.stat().st_size
assert manifest["quick_check_ok"] is True
assert quick_check == "ok"
assert foreign_key_issues == 0
for table, count in counts.items():
    assert manifest["table_counts"][table] == count
print(
    "offhost_restore_verification=pass "
    f"file={database_path.name} "
    f"counts={counts['collection_runs']}/{counts['raw_source_items']}/{counts['canonical_voc_units']} "
    "quick_check=ok foreign_key_issues=0"
)
PY

  rm -rf "$temporary_dir"
  temporary_dir=""
}

if [[ -f "$final_archive" && -f "$final_metadata" ]]; then
  verify_archive "$final_archive"
  print -- "offhost_backup_status=already_present archive=$archive_file"
  exit 0
fi

temporary_archive="$destination_dir/.$archive_file.tmp"
temporary_metadata="$destination_dir/.$metadata_file.tmp"

$ssh_bin "$remote_host" /bin/bash -s -- "$remote_dir" "$database_file" "$latest_manifest" <<'REMOTE' | \
  "$age_bin" --recipient "$recipient" --output "$temporary_archive"
set -euo pipefail
backup_dir=$1
database_file=$2
manifest_file=$3

if [[ "$database_file" == */* || "$manifest_file" == */* ]]; then
  exit 2
fi

sudo -n python3 - "$backup_dir/$database_file" "$backup_dir/$manifest_file" <<'PY'
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

database_path = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
connection = sqlite3.connect(
    f"{database_path.resolve().as_uri()}?mode=ro&immutable=1",
    uri=True,
)
try:
    connection.execute("PRAGMA query_only=ON")
    quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
    table_counts = {
        table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for table in manifest["table_counts"]
    }
finally:
    connection.close()

assert manifest["backup_file"] == database_path.name
assert manifest["sha256"] == digest
assert manifest["bytes"] == database_path.stat().st_size
assert manifest["quick_check_ok"] is True
assert quick_check == "ok"
assert manifest["table_counts"] == table_counts
print(f"remote_backup_verification=pass file={database_path.name}", file=sys.stderr)
PY

sudo -n tar -C "$backup_dir" -cf - -- "$database_file" "$manifest_file"
REMOTE

chmod 0600 "$temporary_archive"
verify_archive "$temporary_archive"

encrypted_sha256="$(shasum -a 256 "$temporary_archive" | awk '{print $1}')"
encrypted_bytes="$(stat -f '%z' "$temporary_archive")"
fetched_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

"$python_bin" - "$temporary_metadata" "$remote_host" "$database_file" \
  "$archive_file" "$encrypted_sha256" "$encrypted_bytes" "$fetched_at" <<'PY'
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
payload = {
    "archive_file": sys.argv[4],
    "encrypted_bytes": int(sys.argv[6]),
    "encrypted_sha256": sys.argv[5],
    "fetched_at": sys.argv[7],
    "remote_host": sys.argv[2],
    "source_backup_file": sys.argv[3],
    "verification": "decrypt_manifest_hash_quick_check_counts_fk",
}
output.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
PY
chmod 0600 "$temporary_metadata"
mv "$temporary_archive" "$final_archive"
temporary_archive=""
mv "$temporary_metadata" "$final_metadata"
temporary_metadata=""

find "$destination_dir" -maxdepth 1 -type f -name 'plugin_hub_*.tar.age' -print | \
  sort -r | tail -n "+$((retention_count + 1))" | while IFS= read -r expired_archive; do
    [[ -n "$expired_archive" ]] || continue
    expired_base="${expired_archive%.tar.age}"
    rm -f "$expired_archive" "$expired_base.offhost.json"
  done

print -- "offhost_backup_status=created archive=$archive_file encrypted_bytes=$encrypted_bytes retention=$retention_count"
