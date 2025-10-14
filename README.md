# MariaDB Database Exporter

Script Python single-file untuk mengekspor database MariaDB/MySQL. Berinteraksi langsung dengan database tanpa menggunakan `mysqldump`.

## Keunggulan

- ✅ **Tidak pakai mysqldump** - Sering error saat import, script ini lebih reliable
- ✅ **Memory Efficient** - Batch processing untuk tabel besar
- ✅ **Complete Export** - Tables, views, procedures, functions, triggers
- ✅ **Flexible Modes** - Structure only, data only, atau full
- ✅ **Progress Feedback** - Real-time progress di console

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
# Buat script backup.sh
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/mysql/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

python3 /path/to/mariadb_exporter.py \
  --host localhost \
  --user backup_user \
  --password "your_password" \
  --database production_db \
  --export-method full \
  --output-dir "$BACKUP_DIR"

# Compress
cd "$BACKUP_DIR" && tar -czf "../backup_$(date +%Y%m%d).tar.gz" *.sql && rm *.sql

# Hapus backup > 30 hari
find /backup/mysql -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x backup.sh

# Tambah ke crontab (backup jam 2 pagi setiap hari)
# 0 2 * * * /path/to/backup.sh >> /var/log/mysql_backup.log 2>&1
```

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
