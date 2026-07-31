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
script_dir="${0:A:h}"

age_bin="${PLUGIN_HUB_AGE_BIN:-/opt/homebrew/bin/age}"
ssh_bin="${PLUGIN_HUB_SSH_BIN:-/usr/bin/ssh}"
security_bin="${PLUGIN_HUB_SECURITY_BIN:-/usr/bin/security}"
python_bin="${PLUGIN_HUB_PYTHON_BIN:-$(command -v python3 || true)}"
base64_bin="${PLUGIN_HUB_BASE64_BIN:-/usr/bin/base64}"
validator_script="${PLUGIN_HUB_BACKUP_VALIDATOR_SCRIPT:-$script_dir/verify-offhost-backup.py}"

if [[ ! "$retention_count" =~ '^[0-9]+$' ]] || (( retention_count < 2 )); then
  print -u2 -- "offhost_backup_error=invalid_retention_count"
  exit 2
fi
if [[ ! -x "$age_bin" || ! -x "$ssh_bin" || ! -x "$security_bin" || ! -x "$python_bin" || ! -x "$base64_bin" ]]; then
  print -u2 -- "offhost_backup_error=required_tool_missing"
  exit 2
fi
if [[ ! -f "$validator_script" || ! -r "$validator_script" ]]; then
  print -u2 -- "offhost_backup_error=validator_script_missing"
  exit 2
fi
if [[ ! -s "$recipient_file" ]]; then
  print -u2 -- "offhost_backup_error=recipient_file_missing"
  exit 2
fi

validator_payload="$("$base64_bin" < "$validator_script" | /usr/bin/tr -d '\n')"
if [[ -z "$validator_payload" ]]; then
  print -u2 -- "offhost_backup_error=validator_script_empty"
  exit 2
fi

umask 077
mkdir -p "$destination_dir"
chmod 0700 "$destination_dir"

lock_file="$destination_dir/.pull.lock"
if [[ -d "$lock_file" ]]; then
  print -u2 -- "offhost_backup_error=legacy_lock_directory_detected path=$lock_file"
  exit 75
fi
exec 9>"$lock_file"
if ! /usr/bin/lockf -s -t 0 9; then
  print -u2 -- "offhost_backup_error=already_running"
  exit 75
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

  "$python_bin" "$validator_script" --context restore \
    "$restore_dir/$database_file" "$restore_dir/$latest_manifest"

  rm -rf "$temporary_dir"
  temporary_dir=""
}

verify_metadata() {
  local archive_path=$1
  local metadata_path=$2

  "$python_bin" - "$archive_path" "$metadata_path" "$archive_file" \
    "$database_file" "$remote_host" <<'PY_METADATA'
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


archive_path = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
expected_archive_file = sys.argv[3]
expected_database_file = sys.argv[4]
expected_remote_host = sys.argv[5]
verification_contract = "decrypt_manifest_hash_quick_check_counts_fk"

payload = json.loads(metadata_path.read_text(encoding="utf-8"))
require(isinstance(payload, dict), "metadata_object_required")
require(payload["archive_file"] == expected_archive_file, "metadata_archive_file_mismatch")
require(
    payload["source_backup_file"] == expected_database_file,
    "metadata_source_backup_file_mismatch",
)
require(payload["remote_host"] == expected_remote_host, "metadata_remote_host_mismatch")
require(payload["verification"] == verification_contract, "metadata_verification_mismatch")
require(
    isinstance(payload["encrypted_bytes"], int)
    and not isinstance(payload["encrypted_bytes"], bool),
    "metadata_encrypted_bytes_invalid",
)
require(
    payload["encrypted_bytes"] == archive_path.stat().st_size,
    "metadata_encrypted_bytes_mismatch",
)
encrypted_sha256 = payload["encrypted_sha256"]
require(
    isinstance(encrypted_sha256, str) and len(encrypted_sha256) == 64,
    "metadata_encrypted_sha256_invalid",
)
require(
    hashlib.sha256(archive_path.read_bytes()).hexdigest() == encrypted_sha256,
    "metadata_encrypted_sha256_mismatch",
)
fetched_at = payload["fetched_at"]
require(isinstance(fetched_at, str), "metadata_fetched_at_invalid")
datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
print(f"offhost_metadata_verification=pass archive={expected_archive_file}")
PY_METADATA
}

if [[ -f "$final_archive" && -f "$final_metadata" ]]; then
  verify_archive "$final_archive"
  verify_metadata "$final_archive" "$final_metadata"
  print -- "offhost_backup_status=already_present archive=$archive_file"
  exit 0
fi

temporary_archive="$destination_dir/.$archive_file.tmp"
temporary_metadata="$destination_dir/.$metadata_file.tmp"

$ssh_bin "$remote_host" /bin/bash -s -- "$remote_dir" "$database_file" "$latest_manifest" \
  "$validator_payload" <<'REMOTE' | \
  "$age_bin" --recipient "$recipient" --output "$temporary_archive"
set -euo pipefail
backup_dir=$1
database_file=$2
manifest_file=$3
validator_payload=$4

if [[ "$database_file" == */* || "$manifest_file" == */* ]]; then
  exit 2
fi

temporary_validator="$(mktemp)"
cleanup_remote() {
  rm -f "$temporary_validator"
}
trap cleanup_remote EXIT INT TERM
printf '%s' "$validator_payload" | base64 --decode > "$temporary_validator"
chmod 0600 "$temporary_validator"

sudo -n python3 "$temporary_validator" --context remote \
  "$backup_dir/$database_file" "$backup_dir/$manifest_file"

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
verify_metadata "$temporary_archive" "$temporary_metadata"
mv "$temporary_metadata" "$final_metadata"
temporary_metadata=""
mv "$temporary_archive" "$final_archive"
temporary_archive=""

expired_verified_archives="$("$python_bin" - "$destination_dir" "$retention_count" <<'PY_RETENTION'
import hashlib
import json
import sys
from pathlib import Path

destination = Path(sys.argv[1])
retention_count = int(sys.argv[2])
verification_contract = "decrypt_manifest_hash_quick_check_counts_fk"
verified: list[Path] = []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

for archive in sorted(destination.glob("plugin_hub_*.tar.age"), reverse=True):
    metadata = archive.with_name(f"{archive.name.removesuffix('.tar.age')}.offhost.json")
    try:
        payload = json.loads(metadata.read_text())
        if not isinstance(payload, dict):
            raise ValueError("metadata_object_required")
        encrypted_bytes = payload.get("encrypted_bytes")
        encrypted_sha256 = payload.get("encrypted_sha256")
        if (
            payload.get("archive_file") != archive.name
            or isinstance(encrypted_bytes, bool)
            or not isinstance(encrypted_bytes, int)
            or encrypted_bytes != archive.stat().st_size
            or not isinstance(encrypted_sha256, str)
            or len(encrypted_sha256) != 64
            or sha256_file(archive) != encrypted_sha256
            or payload.get("verification") != verification_contract
        ):
            raise ValueError("metadata_or_archive_verification_failed")
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"offhost_backup_warning=unverified_archive_retained archive={archive.name} "
            f"reason={type(exc).__name__}",
            file=sys.stderr,
        )
        continue
    verified.append(archive)

for archive in verified[retention_count:]:
    print(archive.name)
PY_RETENTION
)"

while IFS= read -r expired_archive_name; do
  [[ -n "$expired_archive_name" ]] || continue
  expired_archive="$destination_dir/$expired_archive_name"
  expired_metadata="$destination_dir/${expired_archive_name%.tar.age}.offhost.json"
  rm -f "$expired_archive" "$expired_metadata"
done <<< "$expired_verified_archives"

print -- "offhost_backup_status=created archive=$archive_file encrypted_bytes=$encrypted_bytes retention=$retention_count"
