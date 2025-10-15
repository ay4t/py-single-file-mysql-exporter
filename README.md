# MariaDB Database Exporter

Script Python untuk mengekspor database MariaDB/MySQL dan mengirim backup via email. Berinteraksi langsung dengan database tanpa menggunakan `mysqldump`.

## Keunggulan

- ✅ **Tidak pakai mysqldump** - Sering error saat import, script ini lebih reliable
- ✅ **Memory Efficient** - Batch processing untuk tabel besar
- ✅ **Complete Export** - Tables, views, procedures, functions, triggers
- ✅ **Flexible Modes** - Structure only, data only, atau full
- ✅ **Progress Feedback** - Real-time progress di console
- ✅ **Email Backup** - Kirim backup via email untuk proteksi external

## Files

- `mariadb_exporter.py` - Main script untuk ekspor database
- `email_backup_sender.py` - Script untuk kirim backup via email
- `test_connection.py` - Utility untuk test koneksi database

## Quick Start

```bash
# 1. Install dependency
pip install mysql-connector-python

# 2. Test koneksi (dengan password)
python test_connection.py --host localhost --user root --password "pass" --database mydb

# 3. Jalankan backup (tanpa password untuk localhost)
python mariadb_exporter.py --host localhost --user root --database mydb --export-method full

# Atau dengan password
python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full
```

## Penggunaan

### Sintaks Dasar

```bash
python mariadb_exporter.py --host <HOST> --user <USER> --database <DATABASE> [OPTIONS]
```

### Parameter Wajib

- `--host`: Alamat host server MariaDB (contoh: localhost, 192.168.1.100)
- `--user`: Nama pengguna database
- `--database`: Nama database yang akan diekspor

### Parameter Opsional

- `--password`: Kata sandi database (default: kosong/no password)
- `--port`: Port server MariaDB (default: 3306)
- `--export-method`: Mode ekspor (default: full)
  - `structure`: Hanya ekspor struktur tabel (DDL)
  - `data`: Hanya ekspor data tabel (DML)
  - `full`: Ekspor struktur dan data
- `--batch-size`: Jumlah baris per batch INSERT (default: 5000)
- `--output-dir`: Direktori output (default: direktori saat ini)

## Contoh Penggunaan

### 1. Ekspor Full - Localhost Tanpa Password

```bash
python mariadb_exporter.py \
  --host localhost \
  --user root \
  --database my_app_db \
  --export-method full \
  --output-dir /backup/mysql
```

### 2. Ekspor Full - Dengan Password

```bash
python mariadb_exporter.py \
  --host localhost \
  --user root \
  --password "your_password" \
  --database my_app_db \
  --export-method full \
  --output-dir /backup/mysql
```

### 3. Ekspor Struktur Saja

```bash
python mariadb_exporter.py \
  --host localhost \
  --user root \
  --database my_app_db \
  --export-method structure
```

### 4. Ekspor Data Saja dengan Batch Size Custom

```bash
python mariadb_exporter.py \
  --host 192.168.1.100 \
  --user dbuser \
  --password "secure_pass" \
  --database production_db \
  --export-method data \
  --batch-size 10000 \
  --output-dir ./exports
```

### 5. Ekspor dari Remote Server dengan Port Custom

```bash
python mariadb_exporter.py \
  --host db.example.com \
  --port 3307 \
  --user admin \
  --password "admin_pass" \
  --database ecommerce_db \
  --export-method full
```

## Output Files

Script menghasilkan file SQL dengan timestamp:

- `<database>_structure_<timestamp>.sql` - Struktur tabel (DDL)
- `<database>_data_<timestamp>.sql` - Data tabel (DML) *[mode full: merged ke structure]*
- `<database>_views_<timestamp>.sql` - Views
- `<database>_routines_<timestamp>.sql` - Procedures & Functions
- `<database>_triggers_<timestamp>.sql` - Triggers

## Restore Database

```bash
# 1. Buat database baru
mysql -u root -p -e "CREATE DATABASE new_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. Restore semua file
mysql -u root -p new_db < database_structure_20241014_061300.sql
mysql -u root -p new_db < database_views_20241014_061300.sql
mysql -u root -p new_db < database_routines_20241014_061300.sql
mysql -u root -p new_db < database_triggers_20241014_061300.sql
```

## Automated Backup (Cron)

```bash
# Buat script create-auto-backup.sh
cat > create-auto-backup.sh << 'EOF'
#!/bin/bash

# Konfigurasi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${SCRIPT_DIR}/exports/${TIMESTAMP}"

# Buat direktori backup
mkdir -p "$BACKUP_DIR"

# Jalankan ekspor
python3 "${SCRIPT_DIR}/mariadb_exporter.py" \
  --host localhost \
  --user backup_user \
  --password "your_password" \
  --database production_db \
  --export-method full \
  --output-dir "$BACKUP_DIR"

# Compress dengan timestamp lengkap
cd "$BACKUP_DIR" && tar -czf "../backup_${TIMESTAMP}.tar.gz" *.sql && rm *.sql

# Hapus direktori kosong
rmdir "$BACKUP_DIR" 2>/dev/null

# Hapus backup > 30 hari
find "${SCRIPT_DIR}/exports" -name "*.tar.gz" -mtime +30 -delete

# Log hasil backup
echo "[${TIMESTAMP}] Backup completed successfully"
EOF

chmod +x create-auto-backup.sh

# Setup crontab untuk backup otomatis 2x sehari (jam 00:00 dan 12:00)
# Edit crontab
crontab -e

# Tambahkan baris berikut (sesuaikan path):
# 0 0,12 * * * /home/user/py-single-file-mysql-exporter/create-auto-backup.sh >> /home/user/mysql_backup.log 2>&1

# Verifikasi crontab
crontab -l
```

**Penjelasan Cron Schedule:**
- `0 0,12 * * *` = Jam 00:00 dan 12:00 setiap hari
- `0 0 * * *` = Jam 00:00 setiap hari (1x sehari)
- `0 */6 * * *` = Setiap 6 jam (4x sehari)
- `0 0 * * 0` = Jam 00:00 setiap Minggu (1x seminggu)

## Email Backup (External Backup)

Script `email_backup_sender.py` untuk mengirim backup via email sebagai proteksi jika server terkena serangan hacker.

### Setup Gmail App Password

1. Buka https://myaccount.google.com/apppasswords
2. Pilih "Mail" dan device "Other (Custom name)"
3. Generate password (16 karakter)
4. Simpan password tersebut

### Kirim Backup Terbaru via Email

```bash
# Kirim backup terbaru dari folder exports
python email_backup_sender.py \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-email@gmail.com \
  --smtp-password "your-app-password" \
  --recipient webmaster@company.com \
  --backup-dir ./exports \
  --latest 1
```

### Kirim File Backup Spesifik

```bash
python email_backup_sender.py \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-email@gmail.com \
  --smtp-password "your-app-password" \
  --recipient webmaster@company.com \
  --files exports/backup_20241015_120000.tar.gz
```

### Automated Backup + Email (Cron)

```bash
# Buat script backup-and-email.sh
cat > backup-and-email.sh << 'EOF'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${SCRIPT_DIR}/exports/${TIMESTAMP}"

# 1. Jalankan backup
mkdir -p "$BACKUP_DIR"
python3 "${SCRIPT_DIR}/mariadb_exporter.py" \
  --host localhost \
  --user root \
  --database production_db \
  --export-method full \
  --output-dir "$BACKUP_DIR"

# 2. Compress
cd "$BACKUP_DIR" && tar -czf "../backup_${TIMESTAMP}.tar.gz" *.sql && rm *.sql
rmdir "$BACKUP_DIR" 2>/dev/null

# 3. Kirim via email
python3 "${SCRIPT_DIR}/email_backup_sender.py" \
  --smtp-host smtp.gmail.com \
  --smtp-port 587 \
  --smtp-user your-email@gmail.com \
  --smtp-password "$SMTP_PASSWORD" \
  --recipient webmaster@company.com \
  --backup-dir "${SCRIPT_DIR}/exports" \
  --latest 1

# 4. Hapus backup lokal > 7 hari (karena sudah ada di email)
find "${SCRIPT_DIR}/exports" -name "*.tar.gz" -mtime +7 -delete

echo "[${TIMESTAMP}] Backup and email sent successfully"
EOF

chmod +x backup-and-email.sh

# Setup environment variable untuk password
export SMTP_PASSWORD="your-app-password"

# Tambah ke crontab
# 0 0,12 * * * SMTP_PASSWORD="xxx" /path/to/backup-and-email.sh >> /var/log/backup.log 2>&1
```

### Parameter Email Sender

**Required:**
- `--smtp-host`: SMTP server (smtp.gmail.com, smtp.office365.com, dll)
- `--smtp-user`: Email pengirim
- `--smtp-password`: App Password (bukan password email biasa)
- `--recipient`: Email penerima (webmaster)
- `--files` atau `--backup-dir`: File yang akan dikirim

**Optional:**
- `--smtp-port`: Port SMTP (default: 587)
- `--use-ssl`: Gunakan SSL port 465 (default: TLS port 587)
- `--subject`: Subject email (default: "Database Backup - {timestamp}")
- `--body`: Custom email body
- `--latest`: Jumlah file terbaru (default: 1)

### SMTP Server Populer

| Provider | SMTP Host | Port TLS | Port SSL |
|----------|-----------|----------|----------|
| Gmail | smtp.gmail.com | 587 | 465 |
| Outlook/Office365 | smtp.office365.com | 587 | 465 |
| Yahoo | smtp.mail.yahoo.com | 587 | 465 |
| Custom/cPanel | mail.yourdomain.com | 587 | 465 |

**⚠️ Catatan:**
- Gmail membatasi attachment max 25MB
- Gunakan App Password, bukan password email biasa
- Simpan SMTP password di environment variable, jangan hardcode

## Best Practices

### 1. Buat Dedicated Backup User

```sql
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT SELECT, SHOW VIEW, TRIGGER ON database_name.* TO 'backup_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Gunakan Environment Variables

```bash
export DB_PASSWORD="your_password"
python mariadb_exporter.py --host localhost --user root --password "$DB_PASSWORD" --database mydb
```

### 3. Pilih Batch Size yang Tepat

- Tabel < 10K rows: `--batch-size 10000`
- Tabel 10K-100K rows: `--batch-size 5000` (default)
- Tabel 100K-1M rows: `--batch-size 2000`
- Tabel > 1M rows: `--batch-size 1000`

## Troubleshooting

| Error | Solusi |
|-------|--------|
| `Library mysql-connector-python tidak ditemukan` | `pip install mysql-connector-python` |
| `Access denied for user` | Cek username/password dan privilege (SELECT, SHOW VIEW, TRIGGER) |
| `Can't connect to MySQL server` | Pastikan MariaDB running, cek host/port/firewall |
| `Memory Error` | Kurangi `--batch-size` (misal: 1000 atau 500) |
| `Connection timeout` | Database terlalu lambat, gunakan `--batch-size` lebih kecil |

## Technical Details

### Cara Kerja
- **Structure**: `SHOW CREATE TABLE` untuk setiap tabel
- **Data**: Batch processing dengan `LIMIT/OFFSET`, format `INSERT INTO ... VALUES`
- **Views**: `SHOW CREATE VIEW` dengan `DROP VIEW IF EXISTS`
- **Routines**: `SHOW CREATE PROCEDURE/FUNCTION` dengan `DELIMITER $$`
- **Triggers**: `SHOW CREATE TRIGGER` dengan `DELIMITER $$`

### Data Type Handling
- NULL → `NULL`
- Numbers → unquoted
- Strings → quoted & escaped
- Binary → hexadecimal (`0x...`)

### Safety Features
- `DROP IF EXISTS` untuk idempotency
- `SET FOREIGN_KEY_CHECKS=0` saat restore
- Transaction wrapping untuk data export
- Proper character encoding (utf8mb4)

## License

MIT License - Free to use and modify

---

**Created for reliable database backup automation** 🚀
