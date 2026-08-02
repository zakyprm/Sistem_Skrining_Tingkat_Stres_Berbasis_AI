"""
database.py — Modul database SQLite untuk riwayat klasifikasi
Menggunakan aiosqlite untuk akses async.

Sesuai PRD:
- BR-08: Simpan setiap hasil klasifikasi ke database
- BR-11: Query riwayat dengan pagination
- BR-13: Endpoint riwayat TIDAK mengembalikan teks narasi
- BR-14: Filter rentang tanggal
- BR-15: Inisialisasi tabel otomatis saat startup
- NFR-05: SQLite berbasis file
- AUTH: Tabel users untuk autentikasi Ustadz/Konselor
"""

import os
from datetime import datetime
from pathlib import Path

import aiosqlite

# Database file path — di folder yang sama dengan app.py
DB_DIR = Path(os.environ.get("DB_DIR", Path(__file__).parent))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "riwayat_klasifikasi.db"

async def init_db() -> None:
    """
    Inisialisasi database: buat tabel jika belum ada (BR-15, AUTH).
    Dipanggil saat startup dari lifespan.
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Tabel riwayat klasifikasi santri
        await db.execute("""
            CREATE TABLE IF NOT EXISTS riwayat_klasifikasi (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                teks_terenkripsi    BLOB NOT NULL,
                label               VARCHAR(20) NOT NULL,
                confidence_rendah   REAL NOT NULL,
                confidence_sedang   REAL NOT NULL,
                confidence_tinggi   REAL NOT NULL,
                timestamp           DATETIME NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Index pada timestamp untuk query terurut & filter tanggal
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_riwayat_timestamp
            ON riwayat_klasifikasi(timestamp DESC)
        """)
        # Index pada label untuk query ringkasan
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_riwayat_label
            ON riwayat_klasifikasi(label)
        """)
        # Tabel users untuk autentikasi Ustadz/Konselor (AUTH)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role         TEXT NOT NULL DEFAULT 'konselor',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    print("   [OK] Database initialized")


async def simpan_klasifikasi(
    teks_terenkripsi: bytes,
    label: str,
    confidence_rendah: float,
    confidence_sedang: float,
    confidence_tinggi: float,
) -> int | None:
    """
    Simpan satu hasil klasifikasi ke database (BR-08).

    Returns:
        int: ID baris yang baru disimpan, atau None jika gagal
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                """
                INSERT INTO riwayat_klasifikasi
                    (teks_terenkripsi, label, confidence_rendah, confidence_sedang, confidence_tinggi, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    teks_terenkripsi,
                    label,
                    confidence_rendah,
                    confidence_sedang,
                    confidence_tinggi,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan ke database: {e}")
        return None


async def get_user_by_username(username: str) -> dict | None:
    """
    Cari user berdasarkan username (AUTH).
    Digunakan oleh endpoint POST /login untuk verifikasi kredensial.

    Returns:
        dict: { id, username, password_hash, role } atau None jika tidak ditemukan
    """
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (username,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)


async def get_riwayat(
    limit: int = 20,
    offset: int = 0,
    tanggal_mulai: str | None = None,
    tanggal_selesai: str | None = None,
) -> dict:
    """
    Ambil daftar riwayat klasifikasi, terurut terbaru (BR-11).
    TIDAK mengembalikan teks_terenkripsi (BR-13).

    Args:
        limit: Jumlah data per halaman
        offset: Offset untuk pagination
        tanggal_mulai: Filter tanggal awal (format: YYYY-MM-DD)
        tanggal_selesai: Filter tanggal akhir (format: YYYY-MM-DD)

    Returns:
        dict: { total: int, data: list[dict] }
    """
    conditions = []
    params = []

    if tanggal_mulai:
        conditions.append("timestamp >= ?")
        params.append(f"{tanggal_mulai} 00:00:00")

    if tanggal_selesai:
        conditions.append("timestamp <= ?")
        params.append(f"{tanggal_selesai} 23:59:59")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row

        # Count total
        count_query = f"SELECT COUNT(*) as cnt FROM riwayat_klasifikasi {where_clause}"
        async with db.execute(count_query, params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0

        # Fetch data — tanpa teks_terenkripsi (BR-13)
        data_query = f"""
            SELECT id, label, confidence_rendah, confidence_sedang, confidence_tinggi, timestamp
            FROM riwayat_klasifikasi
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        data_params = params + [limit, offset]
        async with db.execute(data_query, data_params) as cursor:
            rows = await cursor.fetchall()
            data = [
                {
                    "id": row[0],
                    "label": row[1],
                    "confidence_normal": row[2],
                    "confidence_sedang": row[3],
                    "confidence_tinggi": row[4],
                    "timestamp": row[5],
                }
                for row in rows
            ]

    return {"total": total, "data": data}


async def get_ringkasan(
    tanggal_mulai: str | None = None,
    tanggal_selesai: str | None = None,
) -> dict:
    """
    Hitung jumlah klasifikasi per label (untuk summary cards di dashboard).

    Returns:
        dict: { Normal: int, Sedang: int, Tinggi: int, total: int }
    """
    conditions = []
    params = []

    if tanggal_mulai:
        conditions.append("timestamp >= ?")
        params.append(f"{tanggal_mulai} 00:00:00")

    if tanggal_selesai:
        conditions.append("timestamp <= ?")
        params.append(f"{tanggal_selesai} 23:59:59")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        query = f"""
            SELECT label, COUNT(*) as jumlah
            FROM riwayat_klasifikasi
            {where_clause}
            GROUP BY label
        """
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    result = {"Normal": 0, "Sedang": 0, "Tinggi": 0}
    for row in rows:
        if row[0] in result:
            result[row[0]] = row[1]

    result["total"] = sum(result.values())
    return result
