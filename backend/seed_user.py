"""
seed_user.py — Script untuk membuat akun Ustadz/Konselor pertama

Jalankan SATU KALI via terminal sebelum menggunakan dashboard riwayat:
    python seed_user.py

Script ini TIDAK dapat diakses dari UI aplikasi (tidak ada endpoint registrasi).
"""

import sqlite3
import getpass
from pathlib import Path
import bcrypt

DB_PATH = Path(__file__).parent / "riwayat_klasifikasi.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////home/site/wwwroot/database.db")

def seed_user():
    print("=" * 50)
    print("  Setup Akun Ustadz/Konselor")
    print("=" * 50)
    print(f"  Database: {DB_PATH}")
    print()

    username = input("Username  : ").strip()
    if not username:
        print("[ERROR] Username tidak boleh kosong.")
        return

    password = getpass.getpass("Password  : ")
    if len(password) < 6:
        print("[ERROR] Password minimal 6 karakter.")
        return

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed, "konselor"),
        )
        conn.commit()
        conn.close()
        print()
        print(f"[OK] Akun '{username}' (role: konselor) berhasil dibuat.")
        print("     Sekarang bisa login di /login.html")
    except sqlite3.IntegrityError:
        print(f"\n[ERROR] Username '{username}' sudah ada di database.")
    except Exception as e:
        print(f"\n[ERROR] Gagal membuat akun: {e}")


if __name__ == "__main__":
    seed_user()
