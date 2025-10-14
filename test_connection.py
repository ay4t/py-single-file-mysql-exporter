#!/usr/bin/env python3
"""
Script untuk test koneksi ke database MariaDB
Gunakan script ini untuk memverifikasi kredensial database sebelum melakukan ekspor
"""

import sys
import argparse

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Error: Library mysql-connector-python tidak ditemukan.")
    print("Install dengan: pip install mysql-connector-python")
    sys.exit(1)


def test_connection(host, user, password, database, port):
    """
    Test koneksi ke database MariaDB.
    
    Args:
        host: Alamat host server
        user: Username database
        password: Password database
        database: Nama database
        port: Port server
    """
    print("="*70)
    print("MariaDB Connection Test")
    print("="*70)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Database: {database}")
    print("="*70)
    print()
    
    try:
        print("Mencoba koneksi ke database...")
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port
        )
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✓ Koneksi berhasil!")
            print(f"✓ Server version: {db_info}")
            
            cursor = connection.cursor()
            
            # Test query untuk mendapatkan informasi database
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            print(f"✓ Connected to database: {db_name}")
            
            # Hitung jumlah tabel
            cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
            tables = cursor.fetchall()
            print(f"✓ Jumlah tabel: {len(tables)}")
            
            # Hitung jumlah views
            cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
            views = cursor.fetchall()
            print(f"✓ Jumlah views: {len(views)}")
            
            # Hitung jumlah procedures
            cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = '{database}'")
            procedures = cursor.fetchall()
            print(f"✓ Jumlah procedures: {len(procedures)}")
            
            # Hitung jumlah functions
            cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = '{database}'")
            functions = cursor.fetchall()
            print(f"✓ Jumlah functions: {len(functions)}")
            
            # Hitung jumlah triggers
            cursor.execute("SHOW TRIGGERS")
            triggers = cursor.fetchall()
            print(f"✓ Jumlah triggers: {len(triggers)}")
            
            cursor.close()
            connection.close()
            
            print()
            print("="*70)
            print("Test koneksi berhasil! Anda dapat melanjutkan ekspor database.")
            print("="*70)
            return True
            
    except Error as e:
        print(f"✗ Error saat koneksi: {e}")
        print()
        print("="*70)
        print("Test koneksi gagal! Periksa kembali kredensial database Anda.")
        print("="*70)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Test koneksi ke database MariaDB'
    )
    
    parser.add_argument('--host', required=True, help='Alamat host server MariaDB')
    parser.add_argument('--user', required=True, help='Username database')
    parser.add_argument('--password', required=True, help='Password database')
    parser.add_argument('--database', required=True, help='Nama database')
    parser.add_argument('--port', type=int, default=3306, help='Port server (default: 3306)')
    
    args = parser.parse_args()
    
    success = test_connection(
        args.host,
        args.user,
        args.password,
        args.database,
        args.port
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
