#!/usr/bin/env python3
"""
Email Backup Sender
Script untuk mengirim file backup database via email sebagai attachment.
Berguna untuk backup external jika server terkena serangan.
"""

import os
import sys
import argparse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime
from typing import List, Optional


class EmailBackupSender:
    """Class untuk mengirim backup via email."""
    
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, 
                 smtp_password: str, use_tls: bool = True):
        """
        Inisialisasi Email Sender.
        
        Args:
            smtp_host: SMTP server host (contoh: smtp.gmail.com)
            smtp_port: SMTP server port (587 untuk TLS, 465 untuk SSL)
            smtp_user: Email pengirim
            smtp_password: Password email atau App Password
            use_tls: Gunakan TLS (default: True)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
    
    def send_backup(self, recipient: str, subject: str, backup_files: List[str], 
                   body: Optional[str] = None) -> bool:
        """
        Mengirim email dengan attachment file backup.
        
        Args:
            recipient: Email penerima (webmaster)
            subject: Subject email
            backup_files: List path file backup yang akan dikirim
            body: Isi email (opsional)
            
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            # Buat message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Body email
            if body is None:
                body = self._generate_default_body(backup_files)
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach files
            total_size = 0
            for file_path in backup_files:
                if not os.path.exists(file_path):
                    print(f"Warning: File tidak ditemukan: {file_path}")
                    continue
                
                file_size = os.path.getsize(file_path)
                total_size += file_size
                
                print(f"Melampirkan file: {os.path.basename(file_path)} ({self._format_size(file_size)})")
                
                with open(file_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(file_path)}'
                )
                msg.attach(part)
            
            print(f"\nTotal ukuran attachment: {self._format_size(total_size)}")
            
            # Cek ukuran total (warning jika > 25MB untuk Gmail)
            if total_size > 25 * 1024 * 1024:
                print("⚠️  Warning: Total ukuran > 25MB, mungkin ditolak oleh Gmail!")
                print("   Pertimbangkan untuk compress atau split file.")
            
            # Kirim email
            print(f"\nMengirim email ke {recipient}...")
            
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            print("✓ Email berhasil dikirim!")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("✗ Error: Autentikasi gagal. Periksa username/password.")
            print("  Untuk Gmail, gunakan App Password: https://myaccount.google.com/apppasswords")
            return False
        except smtplib.SMTPException as e:
            print(f"✗ Error SMTP: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def _generate_default_body(self, backup_files: List[str]) -> str:
        """Generate default email body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"""Database Backup Report
{'='*50}

Timestamp: {timestamp}
Total Files: {len(backup_files)}

File List:
"""
        for i, file_path in enumerate(backup_files, 1):
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                body += f"{i}. {os.path.basename(file_path)} ({self._format_size(size)})\n"
            else:
                body += f"{i}. {os.path.basename(file_path)} (NOT FOUND)\n"
        
        body += f"""
{'='*50}

Backup ini dikirim otomatis untuk keamanan external.
Simpan file ini di tempat yang aman.

Jika Anda tidak mengharapkan email ini, segera hubungi administrator.
"""
        return body
    
    def _format_size(self, size_bytes: int) -> str:
        """Format ukuran file ke human-readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def find_latest_backups(backup_dir: str, count: int = 1) -> List[str]:
    """
    Cari file backup terbaru di direktori.
    
    Args:
        backup_dir: Direktori backup
        count: Jumlah file terbaru yang dicari
        
    Returns:
        List path file backup
    """
    if not os.path.exists(backup_dir):
        print(f"Error: Direktori tidak ditemukan: {backup_dir}")
        return []
    
    # Cari semua file .tar.gz atau .sql
    backup_files = []
    for file in os.listdir(backup_dir):
        if file.endswith(('.tar.gz', '.sql', '.zip')):
            full_path = os.path.join(backup_dir, file)
            backup_files.append((full_path, os.path.getmtime(full_path)))
    
    # Sort by modification time (terbaru dulu)
    backup_files.sort(key=lambda x: x[1], reverse=True)
    
    # Ambil N file terbaru
    return [f[0] for f in backup_files[:count]]


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Email Backup Sender - Kirim file backup via email',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:

  # Kirim file backup spesifik
  python email_backup_sender.py \\
    --smtp-host smtp.gmail.com \\
    --smtp-port 587 \\
    --smtp-user your-email@gmail.com \\
    --smtp-password "your-app-password" \\
    --recipient webmaster@company.com \\
    --files backup_20241015_120000.tar.gz

  # Kirim backup terbaru dari direktori
  python email_backup_sender.py \\
    --smtp-host smtp.gmail.com \\
    --smtp-port 587 \\
    --smtp-user your-email@gmail.com \\
    --smtp-password "your-app-password" \\
    --recipient webmaster@company.com \\
    --backup-dir ./exports \\
    --latest 1

  # Gunakan environment variables untuk keamanan
  export SMTP_PASSWORD="your-app-password"
  python email_backup_sender.py \\
    --smtp-host smtp.gmail.com \\
    --smtp-user your-email@gmail.com \\
    --smtp-password "$SMTP_PASSWORD" \\
    --recipient webmaster@company.com \\
    --backup-dir ./exports \\
    --latest 1

Setup Gmail App Password:
1. Buka https://myaccount.google.com/apppasswords
2. Pilih "Mail" dan device "Other"
3. Generate password
4. Gunakan password tersebut (bukan password Gmail biasa)
        """
    )
    
    # SMTP Configuration
    parser.add_argument(
        '--smtp-host',
        required=True,
        help='SMTP server host (contoh: smtp.gmail.com, smtp.office365.com)'
    )
    
    parser.add_argument(
        '--smtp-port',
        type=int,
        default=587,
        help='SMTP server port (default: 587 untuk TLS, 465 untuk SSL)'
    )
    
    parser.add_argument(
        '--smtp-user',
        required=True,
        help='Email pengirim (SMTP username)'
    )
    
    parser.add_argument(
        '--smtp-password',
        required=True,
        help='Password email atau App Password'
    )
    
    parser.add_argument(
        '--use-ssl',
        action='store_true',
        help='Gunakan SSL instead of TLS (port 465)'
    )
    
    # Email Configuration
    parser.add_argument(
        '--recipient',
        required=True,
        help='Email penerima (webmaster)'
    )
    
    parser.add_argument(
        '--subject',
        default='Database Backup - {timestamp}',
        help='Subject email (gunakan {timestamp} untuk auto timestamp)'
    )
    
    parser.add_argument(
        '--body',
        help='Isi email (opsional, akan auto-generate jika tidak diisi)'
    )
    
    # Backup Files
    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument(
        '--files',
        nargs='+',
        help='File backup yang akan dikirim (bisa multiple files)'
    )
    
    group.add_argument(
        '--backup-dir',
        help='Direktori backup (gunakan dengan --latest)'
    )
    
    parser.add_argument(
        '--latest',
        type=int,
        default=1,
        help='Jumlah file backup terbaru yang akan dikirim (default: 1)'
    )
    
    return parser.parse_args()


def main():
    """Fungsi utama."""
    args = parse_arguments()
    
    # Replace {timestamp} di subject
    subject = args.subject.replace(
        '{timestamp}', 
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Tentukan file yang akan dikirim
    if args.files:
        backup_files = args.files
    else:
        print(f"Mencari {args.latest} file backup terbaru di: {args.backup_dir}")
        backup_files = find_latest_backups(args.backup_dir, args.latest)
        
        if not backup_files:
            print("Error: Tidak ada file backup ditemukan!")
            sys.exit(1)
        
        print(f"File ditemukan:")
        for f in backup_files:
            print(f"  - {f}")
        print()
    
    # Validasi file exists
    valid_files = []
    for f in backup_files:
        if os.path.exists(f):
            valid_files.append(f)
        else:
            print(f"Warning: File tidak ditemukan: {f}")
    
    if not valid_files:
        print("Error: Tidak ada file valid untuk dikirim!")
        sys.exit(1)
    
    # Buat sender dan kirim email
    print("="*60)
    print("Email Backup Sender")
    print("="*60)
    print(f"SMTP Server: {args.smtp_host}:{args.smtp_port}")
    print(f"From: {args.smtp_user}")
    print(f"To: {args.recipient}")
    print(f"Subject: {subject}")
    print(f"Files: {len(valid_files)}")
    print("="*60)
    print()
    
    sender = EmailBackupSender(
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        smtp_user=args.smtp_user,
        smtp_password=args.smtp_password,
        use_tls=not args.use_ssl
    )
    
    success = sender.send_backup(
        recipient=args.recipient,
        subject=subject,
        backup_files=valid_files,
        body=args.body
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
