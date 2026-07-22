"""
encryption.py — Modul enkripsi/dekripsi teks narasi santri
Menggunakan Fernet (AES-128-CBC) dari library cryptography.

Sesuai PRD:
- BR-09: Teks narasi HARUS dienkripsi sebelum disimpan ke database
- NFR-01: Kunci enkripsi dari environment variable, tidak boleh hardcode
"""

import os
import sys

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    """
    Ambil instance Fernet dari ENCRYPTION_KEY environment variable.
    Jika ENCRYPTION_KEY tidak di-set, raise RuntimeError agar server gagal start.
    """
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        print(
            "[FATAL] ENCRYPTION_KEY belum di-set di environment variable.\n"
            "        Jalankan perintah berikut untuk membuat kunci baru:\n"
            "        python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "        Lalu tambahkan ke file .env: ENCRYPTION_KEY=<kunci>"
        )
        sys.exit(1)

    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        print(f"[FATAL] ENCRYPTION_KEY tidak valid: {e}")
        sys.exit(1)


# Singleton Fernet instance (diinisialisasi saat modul pertama kali di-import)
_fernet: Fernet | None = None


def _ensure_fernet() -> Fernet:
    """Lazy-init Fernet instance."""
    global _fernet
    if _fernet is None:
        _fernet = _get_fernet()
    return _fernet


def validate_encryption_key() -> None:
    """
    Validasi bahwa ENCRYPTION_KEY tersedia dan valid.
    Dipanggil saat startup untuk fail-fast (NFR-01).
    """
    _ensure_fernet()
    print("   [OK] ENCRYPTION_KEY valid")


def encrypt_text(plaintext: str) -> bytes:
    """
    Enkripsi teks narasi menjadi bytes terenkripsi.

    Args:
        plaintext: Teks narasi asli

    Returns:
        bytes: Teks terenkripsi (Fernet token)
    """
    f = _ensure_fernet()
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_text(ciphertext: bytes) -> str:
    """
    Dekripsi bytes terenkripsi kembali menjadi teks narasi.

    Args:
        ciphertext: Teks terenkripsi (Fernet token)

    Returns:
        str: Teks narasi asli
    """
    f = _ensure_fernet()
    return f.decrypt(ciphertext).decode("utf-8")
