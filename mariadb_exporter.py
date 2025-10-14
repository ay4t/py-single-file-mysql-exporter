#!/usr/bin/env python3
"""
MariaDB Database Exporter
Script untuk mengekspor struktur (DDL) dan/atau data (DML) dari database MariaDB.
Script ini berinteraksi langsung dengan database tanpa menggunakan mysqldump.
"""

import argparse
import sys
import os
from datetime import datetime
from typing import List, Tuple, Optional, Any

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Error: Library mysql-connector-python tidak ditemukan.")
    print("Install dengan: pip install mysql-connector-python")
    sys.exit(1)


class MariaDBExporter:
    """Class untuk menangani ekspor database MariaDB."""
    
    def __init__(self, host: str, user: str, password: str, database: str, 
                 port: int, batch_size: int, output_dir: str):
        """
        Inisialisasi MariaDB Exporter.
        
        Args:
            host: Alamat host server MariaDB
            user: Nama pengguna database
            password: Kata sandi pengguna
            database: Nama database yang akan diekspor
            port: Port server MariaDB
            batch_size: Jumlah baris per batch untuk ekspor data
            output_dir: Direktori output untuk file SQL
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.batch_size = batch_size
        self.output_dir = output_dir
        self.connection = None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Pastikan output directory ada
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def connect(self) -> bool:
        """
        Membuat koneksi ke database MariaDB.
        
        Returns:
            True jika koneksi berhasil, False jika gagal
        """
        try:
            print(f"Menghubungkan ke database {self.database} di {self.host}:{self.port}...")
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                use_unicode=True
            )
            
            if self.connection.is_connected():
                print("Koneksi berhasil!")
                return True
            return False
            
        except Error as e:
            print(f"Error saat menghubungkan ke database: {e}")
            return False
    
    def disconnect(self):
        """Menutup koneksi database."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Koneksi database ditutup.")
    
    def get_tables(self) -> List[str]:
        """
        Mendapatkan daftar semua tabel (bukan VIEW) dari database.
        
        Returns:
            List nama tabel
        """
        cursor = self.connection.cursor()
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    
    def get_views(self) -> List[str]:
        """
        Mendapatkan daftar semua VIEW dari database.
        
        Returns:
            List nama view
        """
        cursor = self.connection.cursor()
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        views = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return views
    
    def get_procedures(self) -> List[str]:
        """
        Mendapatkan daftar semua stored procedures.
        
        Returns:
            List nama procedure
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = '{self.database}'")
        procedures = [row[1] for row in cursor.fetchall()]  # row[1] adalah nama procedure
        cursor.close()
        return procedures
    
    def get_functions(self) -> List[str]:
        """
        Mendapatkan daftar semua functions.
        
        Returns:
            List nama function
        """
        cursor = self.connection.cursor()
        cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = '{self.database}'")
        functions = [row[1] for row in cursor.fetchall()]  # row[1] adalah nama function
        cursor.close()
        return functions
    
    def get_triggers(self) -> List[str]:
        """
        Mendapatkan daftar semua triggers.
        
        Returns:
            List nama trigger
        """
        cursor = self.connection.cursor()
        cursor.execute("SHOW TRIGGERS")
        triggers = [row[0] for row in cursor.fetchall()]  # row[0] adalah nama trigger
        cursor.close()
        return triggers
    
    def escape_value(self, value: Any) -> str:
        """
        Escape dan format nilai untuk SQL INSERT.
        
        Args:
            value: Nilai yang akan di-escape
            
        Returns:
            String nilai yang sudah di-format untuk SQL
        """
        if value is None:
            return "NULL"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bytes):
            # Handle binary data
            return f"0x{value.hex()}"
        else:
            # String dan tipe lainnya
            value_str = str(value)
            # Escape karakter khusus
            value_str = value_str.replace('\\', '\\\\')
            value_str = value_str.replace("'", "\\'")
            value_str = value_str.replace('"', '\\"')
            value_str = value_str.replace('\n', '\\n')
            value_str = value_str.replace('\r', '\\r')
            value_str = value_str.replace('\t', '\\t')
            return f"'{value_str}'"
    
    def export_tables_structure(self) -> str:
        """
        Mengekspor struktur (DDL) semua tabel ke file SQL.
        
        Returns:
            Path file output
        """
        output_file = os.path.join(
            self.output_dir, 
            f"{self.database}_structure_{self.timestamp}.sql"
        )
        
        print(f"\n=== Mengekspor Struktur Tabel ===")
        tables = self.get_tables()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Structure Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"SET NAMES utf8mb4;\n")
            f.write(f"SET FOREIGN_KEY_CHECKS=0;\n\n")
            
            cursor = self.connection.cursor()
            
            for table in tables:
                print(f"Mengekspor struktur tabel `{table}`...")
                
                f.write(f"-- Structure for table {table}\n")
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                result = cursor.fetchone()
                if result:
                    create_table_sql = result[1]
                    f.write(f"{create_table_sql};\n\n")
            
            cursor.close()
            f.write(f"SET FOREIGN_KEY_CHECKS=1;\n")
        
        print(f"Struktur tabel berhasil diekspor ke: {output_file}")
        return output_file
    
    def export_tables_data(self) -> str:
        """
        Mengekspor data (DML) semua tabel ke file SQL dengan batching.
        
        Returns:
            Path file output
        """
        output_file = os.path.join(
            self.output_dir, 
            f"{self.database}_data_{self.timestamp}.sql"
        )
        
        print(f"\n=== Mengekspor Data Tabel ===")
        tables = self.get_tables()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Data Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"SET NAMES utf8mb4;\n")
            f.write(f"SET FOREIGN_KEY_CHECKS=0;\n")
            f.write(f"START TRANSACTION;\n\n")
            
            cursor = self.connection.cursor()
            
            for table in tables:
                print(f"Mengekspor data tabel `{table}`...")
                
                f.write(f"-- Data for table {table}\n")
                
                # Hitung total baris
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                total_rows = cursor.fetchone()[0]
                
                if total_rows == 0:
                    print(f"  Tabel `{table}` kosong, dilewati.")
                    f.write(f"-- Table {table} is empty\n\n")
                    continue
                
                # Dapatkan nama kolom
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                columns = [row[0] for row in cursor.fetchall()]
                columns_str = ', '.join([f"`{col}`" for col in columns])
                
                # Ekspor data dengan batching
                offset = 0
                batch_num = 1
                total_batches = (total_rows + self.batch_size - 1) // self.batch_size
                
                while offset < total_rows:
                    print(f"  Batch {batch_num}/{total_batches} (offset: {offset})...")
                    
                    cursor.execute(
                        f"SELECT * FROM `{table}` LIMIT {self.batch_size} OFFSET {offset}"
                    )
                    rows = cursor.fetchall()
                    
                    if rows:
                        # Format data menjadi INSERT statement
                        values_list = []
                        for row in rows:
                            values = ', '.join([self.escape_value(val) for val in row])
                            values_list.append(f"({values})")
                        
                        insert_sql = f"INSERT INTO `{table}` ({columns_str}) VALUES\n"
                        insert_sql += ',\n'.join(values_list)
                        insert_sql += ';\n'
                        
                        f.write(insert_sql)
                    
                    offset += self.batch_size
                    batch_num += 1
                
                f.write('\n')
                print(f"  Selesai: {total_rows} baris diekspor.")
            
            cursor.close()
            
            f.write(f"COMMIT;\n")
            f.write(f"SET FOREIGN_KEY_CHECKS=1;\n")
        
        print(f"Data tabel berhasil diekspor ke: {output_file}")
        return output_file
    
    def export_views(self) -> str:
        """
        Mengekspor semua VIEW ke file SQL.
        
        Returns:
            Path file output
        """
        output_file = os.path.join(
            self.output_dir, 
            f"{self.database}_views_{self.timestamp}.sql"
        )
        
        print(f"\n=== Mengekspor Views ===")
        views = self.get_views()
        
        if not views:
            print("Tidak ada view yang ditemukan.")
            return output_file
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Views Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            cursor = self.connection.cursor()
            
            for view in views:
                print(f"Mengekspor view `{view}`...")
                
                f.write(f"-- View: {view}\n")
                f.write(f"DROP VIEW IF EXISTS `{view}`;\n")
                
                cursor.execute(f"SHOW CREATE VIEW `{view}`")
                result = cursor.fetchone()
                if result:
                    create_view_sql = result[1]
                    f.write(f"{create_view_sql};\n\n")
            
            cursor.close()
        
        print(f"Views berhasil diekspor ke: {output_file}")
        return output_file
    
    def export_routines(self) -> str:
        """
        Mengekspor semua stored procedures dan functions ke file SQL.
        
        Returns:
            Path file output
        """
        output_file = os.path.join(
            self.output_dir, 
            f"{self.database}_routines_{self.timestamp}.sql"
        )
        
        print(f"\n=== Mengekspor Routines (Procedures & Functions) ===")
        procedures = self.get_procedures()
        functions = self.get_functions()
        
        if not procedures and not functions:
            print("Tidak ada routine yang ditemukan.")
            return output_file
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Routines Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            cursor = self.connection.cursor()
            
            # Export Procedures
            for procedure in procedures:
                print(f"Mengekspor procedure `{procedure}`...")
                
                f.write(f"-- Procedure: {procedure}\n")
                f.write(f"DROP PROCEDURE IF EXISTS `{procedure}`;\n")
                f.write(f"DELIMITER $$\n")
                
                cursor.execute(f"SHOW CREATE PROCEDURE `{procedure}`")
                result = cursor.fetchone()
                if result:
                    create_proc_sql = result[2]  # Index 2 berisi Create Procedure
                    f.write(f"{create_proc_sql}$$\n")
                
                f.write(f"DELIMITER ;\n\n")
            
            # Export Functions
            for function in functions:
                print(f"Mengekspor function `{function}`...")
                
                f.write(f"-- Function: {function}\n")
                f.write(f"DROP FUNCTION IF EXISTS `{function}`;\n")
                f.write(f"DELIMITER $$\n")
                
                cursor.execute(f"SHOW CREATE FUNCTION `{function}`")
                result = cursor.fetchone()
                if result:
                    create_func_sql = result[2]  # Index 2 berisi Create Function
                    f.write(f"{create_func_sql}$$\n")
                
                f.write(f"DELIMITER ;\n\n")
            
            cursor.close()
        
        print(f"Routines berhasil diekspor ke: {output_file}")
        return output_file
    
    def export_triggers(self) -> str:
        """
        Mengekspor semua triggers ke file SQL.
        
        Returns:
            Path file output
        """
        output_file = os.path.join(
            self.output_dir, 
            f"{self.database}_triggers_{self.timestamp}.sql"
        )
        
        print(f"\n=== Mengekspor Triggers ===")
        triggers = self.get_triggers()
        
        if not triggers:
            print("Tidak ada trigger yang ditemukan.")
            return output_file
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Triggers Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            cursor = self.connection.cursor()
            
            for trigger in triggers:
                print(f"Mengekspor trigger `{trigger}`...")
                
                f.write(f"-- Trigger: {trigger}\n")
                f.write(f"DROP TRIGGER IF EXISTS `{trigger}`;\n")
                f.write(f"DELIMITER $$\n")
                
                cursor.execute(f"SHOW CREATE TRIGGER `{trigger}`")
                result = cursor.fetchone()
                if result:
                    create_trigger_sql = result[2]  # Index 2 berisi SQL Original Statement
                    f.write(f"{create_trigger_sql}$$\n")
                
                f.write(f"DELIMITER ;\n\n")
            
            cursor.close()
        
        print(f"Triggers berhasil diekspor ke: {output_file}")
        return output_file
    
    def merge_full_export(self, structure_file: str, data_file: str) -> str:
        """
        Menggabungkan file struktur dan data menjadi satu file untuk mode full.
        
        Args:
            structure_file: Path file struktur
            data_file: Path file data
            
        Returns:
            Path file hasil penggabungan
        """
        print(f"\n=== Menggabungkan File Struktur dan Data ===")
        
        # Baca konten file data
        with open(data_file, 'r', encoding='utf-8') as f:
            data_content = f.read()
        
        # Append ke file struktur
        with open(structure_file, 'a', encoding='utf-8') as f:
            f.write('\n\n')
            f.write('-- ' + '='*70 + '\n')
            f.write('-- DATA SECTION\n')
            f.write('-- ' + '='*70 + '\n\n')
            f.write(data_content)
        
        # Hapus file data sementara
        os.remove(data_file)
        print(f"File data sementara dihapus: {data_file}")
        
        print(f"File full export berhasil dibuat: {structure_file}")
        return structure_file
    
    def export(self, export_method: str):
        """
        Melakukan ekspor database sesuai method yang dipilih.
        
        Args:
            export_method: Mode ekspor ('structure', 'data', atau 'full')
        """
        try:
            if not self.connect():
                sys.exit(1)
            
            print(f"\n{'='*70}")
            print(f"Memulai ekspor database: {self.database}")
            print(f"Mode ekspor: {export_method}")
            print(f"Batch size: {self.batch_size}")
            print(f"Output directory: {self.output_dir}")
            print(f"{'='*70}")
            
            structure_file = None
            data_file = None
            
            # Langkah 1 & 2: Ekspor struktur dan/atau data
            if export_method in ['structure', 'full']:
                structure_file = self.export_tables_structure()
            
            if export_method in ['data', 'full']:
                data_file = self.export_tables_data()
            
            # Langkah 3: Merge untuk mode full
            if export_method == 'full' and structure_file and data_file:
                structure_file = self.merge_full_export(structure_file, data_file)
            
            # Langkah 4, 5, 6: Ekspor views, routines, dan triggers (selalu dijalankan)
            self.export_views()
            self.export_routines()
            self.export_triggers()
            
            print(f"\n{'='*70}")
            print(f"Ekspor selesai!")
            print(f"{'='*70}\n")
            
        except Error as e:
            print(f"\nError saat melakukan ekspor: {e}")
            sys.exit(1)
        
        finally:
            self.disconnect()


def parse_arguments():
    """
    Parse argumen command-line.
    
    Returns:
        Namespace objek berisi argumen yang di-parse
    """
    parser = argparse.ArgumentParser(
        description='MariaDB Database Exporter - Ekspor struktur dan/atau data database MariaDB',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  # Ekspor full (struktur + data)
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full
  
  # Ekspor tanpa password (localhost tanpa password)
  python mariadb_exporter.py --host localhost --user root --database mydb --export-method full
  
  # Ekspor struktur saja
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method structure
  
  # Ekspor data saja dengan batch size custom
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method data --batch-size 10000
        """
    )
    
    parser.add_argument(
        '--host',
        required=True,
        help='Alamat host server MariaDB (contoh: localhost, 192.168.1.100)'
    )
    
    parser.add_argument(
        '--user',
        required=True,
        help='Nama pengguna untuk koneksi database'
    )
    
    parser.add_argument(
        '--password',
        default='',
        help='Kata sandi pengguna database (opsional, kosongkan jika tidak ada password)'
    )
    
    parser.add_argument(
        '--database',
        required=True,
        help='Nama database yang akan diekspor'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=3306,
        help='Port server MariaDB (default: 3306)'
    )
    
    parser.add_argument(
        '--export-method',
        choices=['structure', 'data', 'full'],
        default='full',
        help='''Mode ekspor:
  - structure: Hanya ekspor struktur tabel (DDL)
  - data: Hanya ekspor data tabel (DML)
  - full: Ekspor struktur dan data (default)
        '''
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=5000,
        help='Jumlah baris data yang diekspor dalam satu perintah INSERT (default: 5000)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Direktori untuk menyimpan file SQL hasil ekspor (default: direktori saat ini)'
    )
    
    return parser.parse_args()


def main():
    """Fungsi utama program."""
    args = parse_arguments()
    
    # Validasi batch size
    if args.batch_size < 1:
        print("Error: batch-size harus lebih besar dari 0")
        sys.exit(1)
    
    # Buat instance exporter dan jalankan
    exporter = MariaDBExporter(
        host=args.host,
        user=args.user,
        password=args.password,
        database=args.database,
        port=args.port,
        batch_size=args.batch_size,
        output_dir=args.output_dir
    )
    
    exporter.export(args.export_method)


if __name__ == '__main__':
    main()
