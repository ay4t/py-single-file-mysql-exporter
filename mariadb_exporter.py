#!/usr/bin/env python3
"""
MariaDB Database Exporter
Script untuk mengekspor struktur (DDL) dan/atau data (DML) dari database MariaDB.
Script ini berinteraksi langsung dengan database tanpa menggunakan mysqldump.
"""

import argparse
import sys
import os
import re
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
                 port: int, batch_size: int, output_dir: str,
                 include_views: bool = True, include_routines: bool = True, 
                 include_triggers: bool = True):
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
            include_views: Flag untuk mengekspor views (default: True)
            include_routines: Flag untuk mengekspor procedures dan functions (default: True)
            include_triggers: Flag untuk mengekspor triggers (default: True)
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.batch_size = batch_size
        self.output_dir = output_dir
        self.include_views = include_views
        self.include_routines = include_routines
        self.include_triggers = include_triggers
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
                    # Hapus klausa AUTO_INCREMENT menggunakan regex
                    create_table_sql = re.sub(r' AUTO_INCREMENT=\d+', '', create_table_sql)
                    f.write(f"{create_table_sql};\n\n")
            
            cursor.close()
            f.write(f"SET FOREIGN_KEY_CHECKS=1;\n")
        
        print(f"Struktur tabel berhasil diekspor ke: {output_file}")
        return output_file
    
    def export_tables_data(self, append_to_file: str = None) -> str:
        """
        Mengekspor data (DML) semua tabel ke file SQL dengan batching.
        
        Args:
            append_to_file: Jika diisi, data akan di-append ke file ini (untuk mode full)
        
        Returns:
            Path file output
        """
        if append_to_file:
            output_file = append_to_file
            file_mode = 'a'  # Append mode
        else:
            output_file = os.path.join(
                self.output_dir, 
                f"{self.database}_data_{self.timestamp}.sql"
            )
            file_mode = 'w'  # Write mode
        
        print(f"\n=== Mengekspor Data Tabel ===")
        tables = self.get_tables()
        
        with open(output_file, file_mode, encoding='utf-8') as f:
            if append_to_file:
                # Mode full: append dengan separator
                f.write(f"\n\n")
                f.write(f"-- " + "="*70 + "\n")
                f.write(f"-- DATA SECTION\n")
                f.write(f"-- " + "="*70 + "\n\n")
            else:
                # Mode data only: header lengkap
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
                
                # Dapatkan nama kolom dan filter kolom GENERATED
                cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                all_columns_info = cursor.fetchall()
                
                columns = []
                for col_info in all_columns_info:
                    # Kolom 'Extra' (indeks 5) berisi info seperti 'VIRTUAL GENERATED'
                    if 'GENERATED' not in col_info[5]:
                        columns.append(col_info[0])
                
                columns_str = ', '.join([f"`{col}`" for col in columns])
                select_columns_str = ', '.join([f"`{col}`" for col in columns])

                # Ekspor data dengan batching
                offset = 0
                batch_num = 1
                total_batches = (total_rows + self.batch_size - 1) // self.batch_size
                
                while offset < total_rows:
                    print(f"  Batch {batch_num}/{total_batches} (offset: {offset})...")
                    
                    # Gunakan daftar kolom yang sudah difilter untuk SELECT
                    query = f"SELECT {select_columns_str} FROM `{table}` LIMIT {self.batch_size} OFFSET {offset}"
                    cursor.execute(query)
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
        
        try:
            views = self.get_views()
            print(f"Ditemukan {len(views)} view(s): {views}")
        except Exception as e:
            print(f"Error saat mengambil daftar views: {e}")
            views = []
        
        # Selalu buat file, bahkan jika kosong
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Views Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Total Views: {len(views)}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            if not views:
                f.write(f"-- No views found in this database\n")
                print("Tidak ada view yang ditemukan.")
            else:
                cursor = self.connection.cursor()
                
                for view in views:
                    print(f"Mengekspor view `{view}`...")
                    
                    try:
                        f.write(f"-- View: {view}\n")
                        f.write(f"DROP VIEW IF EXISTS `{view}`;\n")
                        
                        cursor.execute(f"SHOW CREATE VIEW `{view}`")
                        result = cursor.fetchone()
                        if result:
                            create_view_sql = result[1]
                            f.write(f"{create_view_sql};\n\n")
                    except Exception as e:
                        print(f"  Error saat mengekspor view `{view}`: {e}")
                        f.write(f"-- ERROR: Could not export view {view}: {e}\n\n")
                
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
        
        try:
            procedures = self.get_procedures()
            print(f"Ditemukan {len(procedures)} procedure(s): {procedures}")
        except Exception as e:
            print(f"Error saat mengambil daftar procedures: {e}")
            procedures = []
        
        try:
            functions = self.get_functions()
            print(f"Ditemukan {len(functions)} function(s): {functions}")
        except Exception as e:
            print(f"Error saat mengambil daftar functions: {e}")
            functions = []
        
        # Selalu buat file, bahkan jika kosong
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Routines Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Total Procedures: {len(procedures)}\n")
            f.write(f"-- Total Functions: {len(functions)}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            if not procedures and not functions:
                f.write(f"-- No routines found in this database\n")
                print("Tidak ada routine yang ditemukan.")
            else:
                cursor = self.connection.cursor()
                
                # Export Procedures
                for procedure in procedures:
                    print(f"Mengekspor procedure `{procedure}`...")
                    
                    try:
                        f.write(f"-- Procedure: {procedure}\n")
                        f.write(f"DROP PROCEDURE IF EXISTS `{procedure}`;\n")
                        f.write(f"DELIMITER $$\n")
                        
                        cursor.execute(f"SHOW CREATE PROCEDURE `{procedure}`")
                        result = cursor.fetchone()
                        if result:
                            create_proc_sql = result[2]  # Index 2 berisi Create Procedure
                            f.write(f"{create_proc_sql}$$\n")
                        
                        f.write(f"DELIMITER ;\n\n")
                    except Exception as e:
                        print(f"  Error saat mengekspor procedure `{procedure}`: {e}")
                        f.write(f"-- ERROR: Could not export procedure {procedure}: {e}\n\n")
                
                # Export Functions
                for function in functions:
                    print(f"Mengekspor function `{function}`...")
                    
                    try:
                        f.write(f"-- Function: {function}\n")
                        f.write(f"DROP FUNCTION IF EXISTS `{function}`;\n")
                        f.write(f"DELIMITER $$\n")
                        
                        cursor.execute(f"SHOW CREATE FUNCTION `{function}`")
                        result = cursor.fetchone()
                        if result:
                            create_func_sql = result[2]  # Index 2 berisi Create Function
                            f.write(f"{create_func_sql}$$\n")
                        
                        f.write(f"DELIMITER ;\n\n")
                    except Exception as e:
                        print(f"  Error saat mengekspor function `{function}`: {e}")
                        f.write(f"-- ERROR: Could not export function {function}: {e}\n\n")
                
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
        
        try:
            triggers = self.get_triggers()
            print(f"Ditemukan {len(triggers)} trigger(s): {triggers}")
        except Exception as e:
            print(f"Error saat mengambil daftar triggers: {e}")
            triggers = []
        
        # Selalu buat file, bahkan jika kosong
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- MariaDB Database Triggers Export\n")
            f.write(f"-- Database: {self.database}\n")
            f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Total Triggers: {len(triggers)}\n\n")
            f.write(f"SET NAMES utf8mb4;\n\n")
            
            if not triggers:
                f.write(f"-- No triggers found in this database\n")
                print("Tidak ada trigger yang ditemukan.")
            else:
                cursor = self.connection.cursor()
                
                for trigger in triggers:
                    print(f"Mengekspor trigger `{trigger}`...")
                    
                    try:
                        f.write(f"-- Trigger: {trigger}\n")
                        f.write(f"DROP TRIGGER IF EXISTS `{trigger}`;\n")
                        f.write(f"DELIMITER $$\n")
                        
                        cursor.execute(f"SHOW CREATE TRIGGER `{trigger}`")
                        result = cursor.fetchone()
                        if result:
                            create_trigger_sql = result[2]  # Index 2 berisi SQL Original Statement
                            f.write(f"{create_trigger_sql}$$\n")
                        
                        f.write(f"DELIMITER ;\n\n")
                    except Exception as e:
                        print(f"  Error saat mengekspor trigger `{trigger}`: {e}")
                        f.write(f"-- ERROR: Could not export trigger {trigger}: {e}\n\n")
                
                cursor.close()
        
        print(f"Triggers berhasil diekspor ke: {output_file}")
        return output_file
    
    def merge_full_export(self, structure_file: str, data_file: str) -> str:
        """
        Menggabungkan file struktur dan data menjadi satu file untuk mode full.
        Menggunakan shell command untuk performa maksimal, fallback ke Python streaming.
        
        Args:
            structure_file: Path file struktur
            data_file: Path file data
            
        Returns:
            Path file hasil penggabungan
        """
        print(f"\n=== Menggabungkan File Struktur dan Data ===")
        
        import subprocess
        import platform
        
        # Coba gunakan shell command untuk performa maksimal
        if platform.system() != 'Windows':
            try:
                # Tambahkan separator
                with open(structure_file, 'a', encoding='utf-8') as f:
                    f.write('\n\n')
                    f.write('-- ' + '='*70 + '\n')
                    f.write('-- DATA SECTION\n')
                    f.write('-- ' + '='*70 + '\n\n')
                
                # Gunakan cat untuk append (paling cepat)
                result = subprocess.run(
                    ['cat', data_file],
                    stdout=open(structure_file, 'ab'),
                    stderr=subprocess.PIPE,
                    check=True
                )
                print(f"File berhasil digabungkan (menggunakan shell command).")
            except Exception as e:
                print(f"Shell command gagal, fallback ke Python streaming: {e}")
                self._merge_with_streaming(structure_file, data_file)
        else:
            # Windows: gunakan Python streaming
            self._merge_with_streaming(structure_file, data_file)
        
        # Hapus file data sementara
        os.remove(data_file)
        print(f"File data sementara dihapus: {data_file}")
        
        print(f"File full export berhasil dibuat: {structure_file}")
        return structure_file
    
    def _merge_with_streaming(self, structure_file: str, data_file: str):
        """
        Fallback method untuk merge menggunakan Python streaming.
        """
        CHUNK_SIZE = 1024 * 1024  # 1 MB
        
        with open(structure_file, 'a', encoding='utf-8') as f_out:
            f_out.write('\n\n')
            f_out.write('-- ' + '='*70 + '\n')
            f_out.write('-- DATA SECTION\n')
            f_out.write('-- ' + '='*70 + '\n\n')
            
            with open(data_file, 'r', encoding='utf-8') as f_in:
                while True:
                    chunk = f_in.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f_out.write(chunk)
    
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
            
            if export_method == 'full':
                # Mode full: write data langsung ke structure file (optimal)
                print(f"Mode full: menulis data langsung ke file struktur (no merge needed)")
                data_file = self.export_tables_data(append_to_file=structure_file)
                # Tidak perlu merge karena sudah langsung ditulis
            elif export_method == 'data':
                # Mode data only: buat file terpisah
                data_file = self.export_tables_data()
            
            # Langkah 4, 5, 6: Ekspor views, routines, dan triggers (jika diaktifkan)
            if self.include_views:
                self.export_views()
            if self.include_routines:
                self.export_routines()
            if self.include_triggers:
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
  
  # Ekspor tanpa views
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full --no-views
  
  # Ekspor tanpa routines (procedures & functions)
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full --no-routines
  
  # Ekspor tanpa triggers
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full --no-triggers
  
  # Ekspor hanya tabel (tanpa views, routines, dan triggers)
  python mariadb_exporter.py --host localhost --user root --password "pass" --database mydb --export-method full --no-views --no-routines --no-triggers
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
    
    parser.add_argument(
        '--no-views',
        action='store_true',
        help='Jangan ekspor views (default: ekspor views)'
    )
    
    parser.add_argument(
        '--no-routines',
        action='store_true',
        help='Jangan ekspor stored procedures dan functions (default: ekspor routines)'
    )
    
    parser.add_argument(
        '--no-triggers',
        action='store_true',
        help='Jangan ekspor triggers (default: ekspor triggers)'
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
        output_dir=args.output_dir,
        include_views=not args.no_views,
        include_routines=not args.no_routines,
        include_triggers=not args.no_triggers
    )
    
    exporter.export(args.export_method)


if __name__ == '__main__':
    main()
