#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<'EOF'
Penggunaan: create-auto-backup.sh [opsi]

Opsi:
  -c, --config PATH   Path file konfigurasi tambahan (opsional)
  -k, --keep-sql      Pertahankan file *.sql setelah proses kompresi
  -h, --help          Tampilkan bantuan ini

Konfigurasi dapat diberikan melalui variabel lingkungan atau file .backup.env
di direktori yang sama dengan skrip ini. Contoh variabel yang didukung:
  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, EXPORT_METHOD,
  OUTPUT_ROOT, RETENTION_DAYS, PYTHON_BIN, ADDITIONAL_ARGS,
  LOG_FILE, KEEP_SQL, PROMPT_DB_PASSWORD

Contoh file .backup.env:
  DB_NAME="prod_database"
  DB_USER="backup_user"
  DB_PASSWORD="password_yang_aman"
  OUTPUT_ROOT="$HOME/db_backups"
  RETENTION_DAYS=14

EOF
}

log() {
  local message="$*"
  local timestamp
  timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
  printf '[%s] %s\n' "$timestamp" "$message"
  if [[ -n "${LOG_FILE:-}" ]]; then
    mkdir -p "$(dirname "$LOG_FILE")"
    printf '[%s] %s\n' "$timestamp" "$message" >> "$LOG_FILE"
  fi
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Perintah '$1' tidak ditemukan. Silakan instal terlebih dahulu."
    exit 1
  fi
}

CONFIG_FILE=""
KEEP_SQL="${KEEP_SQL:-false}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--config)
      [[ $# -lt 2 ]] && { printf 'Error: opsi %s memerlukan argumen.\n' "$1" >&2; usage; exit 1; }
      CONFIG_FILE="$2"
      shift 2
      ;;
    -k|--keep-sql)
      KEEP_SQL="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Opsi tidak dikenal: %s\n\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ENV_FILE="${SCRIPT_DIR}/.backup.env"

# shellcheck disable=SC1090
if [[ -f "$DEFAULT_ENV_FILE" ]]; then
  source "$DEFAULT_ENV_FILE"
fi

if [[ -n "$CONFIG_FILE" ]]; then
  if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
  else
    log "File konfigurasi tambahan tidak ditemukan: $CONFIG_FILE"
    exit 1
  fi
fi

PYTHON_BIN="${PYTHON_BIN:-}"
EXPORTER_SCRIPT="${EXPORTER_SCRIPT:-$SCRIPT_DIR/mariadb_exporter.py}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-}"
EXPORT_METHOD="${EXPORT_METHOD:-full}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$SCRIPT_DIR/exports}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
ADDITIONAL_ARGS="${ADDITIONAL_ARGS:-}"
LOG_FILE="${LOG_FILE:-$OUTPUT_ROOT/backup.log}"
PROMPT_DB_PASSWORD="${PROMPT_DB_PASSWORD:-false}"

if [[ -z "$DB_NAME" ]]; then
  log "Variabel DB_NAME wajib diisi. Atur melalui environment atau file konfigurasi."
  exit 1
fi

# Tentukan interpreter Python
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$SCRIPT_DIR/venv/bin/python" ]]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    log "Interpreter Python tidak ditemukan. Set variabel PYTHON_BIN atau instal Python lebih dulu."
    exit 1
  fi
fi

if ! [[ -x "$PYTHON_BIN" ]]; then
  log "Interpreter Python tidak dapat dieksekusi: $PYTHON_BIN"
  exit 1
fi

if ! [[ -f "$EXPORTER_SCRIPT" ]]; then
  log "Skript exporter tidak ditemukan: $EXPORTER_SCRIPT"
  exit 1
fi

require_cmd tar
require_cmd find

if [[ -z "$DB_PASSWORD" ]]; then
  if [[ "${PROMPT_DB_PASSWORD,,}" == "true" ]]; then
    if [[ -t 0 ]]; then
      read -rsp "Masukkan password untuk user '${DB_USER}': " DB_PASSWORD
      echo
    else
      log "Tidak dapat meminta password (non-interaktif). Set variabel DB_PASSWORD terlebih dahulu."
      exit 1
    fi
  else
    log "DB_PASSWORD belum di-set. Untuk non-interaktif, set variabel DB_PASSWORD."
    exit 1
  fi
fi

mkdir -p "$OUTPUT_ROOT"
mkdir -p "$(dirname "$LOG_FILE")"

BACKUP_DIR=""
ARCHIVE_PATH=""

cleanup() {
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    log "Backup gagal. Membersihkan artefak sementara..."
    if [[ -n "${BACKUP_DIR:-}" && -d "$BACKUP_DIR" ]]; then
      rm -rf "$BACKUP_DIR"
    fi
    if [[ -n "${ARCHIVE_PATH:-}" && -f "$ARCHIVE_PATH" ]]; then
      rm -f "$ARCHIVE_PATH"
    fi
  fi
}
trap cleanup EXIT

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${OUTPUT_ROOT}/${TIMESTAMP}"
ARCHIVE_PATH="${OUTPUT_ROOT}/backup_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

log "Memulai proses backup. Output sementara: $BACKUP_DIR"

declare -a exporter_cmd=("$PYTHON_BIN" "$EXPORTER_SCRIPT" \
  --host "$DB_HOST" \
  --port "$DB_PORT" \
  --user "$DB_USER" \
  --database "$DB_NAME" \
  --export-method "$EXPORT_METHOD" \
  --output-dir "$BACKUP_DIR")

if [[ -n "$DB_PASSWORD" ]]; then
  exporter_cmd+=(--password "$DB_PASSWORD")
fi

if [[ -n "$ADDITIONAL_ARGS" ]]; then
  read -r -a extra_args <<< "$ADDITIONAL_ARGS"
  exporter_cmd+=("${extra_args[@]}")
fi

log "Menjalankan exporter Python..."
"${exporter_cmd[@]}"

log "Exporter selesai. Menyiapkan kompresi hasil backup..."

shopt -s nullglob
sql_files=("$BACKUP_DIR"/*.sql)
shopt -u nullglob

if (( ${#sql_files[@]} == 0 )); then
  log "Tidak ditemukan file SQL di $BACKUP_DIR. Periksa log exporter untuk detail."
  exit 1
fi

sql_files_basename=()
for path in "${sql_files[@]}"; do
  sql_files_basename+=("$(basename "$path")")
done

tar -czf "$ARCHIVE_PATH" -C "$BACKUP_DIR" "${sql_files_basename[@]}"
log "Arsip backup dibuat: $ARCHIVE_PATH"

if [[ "${KEEP_SQL,,}" == "true" ]]; then
  log "KEEP_SQL diaktifkan. File SQL disimpan di: $BACKUP_DIR"
else
  rm -f "${sql_files[@]}"
  if ! rmdir "$BACKUP_DIR" 2>/dev/null; then
    log "Tidak dapat menghapus direktori $BACKUP_DIR (mungkin tidak kosong)."
  else
    log "Direktori sementara dihapus: $BACKUP_DIR"
  fi
fi

if [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  mapfile -t old_archives < <(find "$OUTPUT_ROOT" -maxdepth 1 -type f -name 'backup_*.tar.gz' -mtime +"$RETENTION_DAYS" -print)
  for archive in "${old_archives[@]}"; do
    log "Menghapus arsip lama: $archive"
    rm -f "$archive"
  done
fi

log "Backup selesai dengan sukses."