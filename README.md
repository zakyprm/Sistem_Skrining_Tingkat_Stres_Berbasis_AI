# Sistem Skrining Tingkat Stres Santri Berbasis AI

Aplikasi berbasis web untuk mendeteksi dan mengklasifikasi tingkat stres pada santri berdasarkan teks curhatan (teks narasi) yang ditulis oleh santri. Sistem ini menggunakan model kecerdasan buatan **IndoBERT** untuk mengolah teks berbahasa Indonesia dan mengklasifikasikannya ke dalam tiga kategori: **Normal**, **Sedang**, dan **Tinggi**.

Aplikasi ini ditujukan untuk digunakan oleh:
1. **Santri (Pengguna Akhir):** Menginputkan keluhan atau curhatan secara anonim untuk mengetahui tingkat stres mereka saat ini.
2. **Ustadz / Konselor:** Melihat riwayat klasifikasi keseluruhan santri sebagai bahan evaluasi melalui dashboard khusus.

---

## ✨ Fitur Utama

- **Deteksi Stres Otomatis:** Menggunakan model _Deep Learning_ IndoBERT yang telah di-_fine-tuning_ khusus untuk mengenali pola bahasa curhatan terkait stres.
- **Visualisasi Hasil (Gauge Chart):** Menampilkan skor kepercayaan (_confidence score_) model dalam bentuk grafik interaktif yang mudah dipahami.
- **Keamanan Privasi (End-to-End):** Teks curhatan yang dimasukkan oleh santri akan **dienkripsi** (AES) sebelum disimpan ke dalam database. Sistem hanya mencatat hasil prediksi dan _confidence score_ tanpa pernah menampilkan kembali teks aslinya.
- **Dashboard Riwayat Konselor:** Panel khusus dengan autentikasi (JWT) bagi konselor untuk memantau ringkasan dan riwayat klasifikasi stres.
- **Filter & Pagination:** Fitur filter berdasarkan rentang tanggal dan navigasi halaman pada riwayat klasifikasi.

---

## 🛠️ Teknologi yang Digunakan

**Backend:**
- [Python 3.10+](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) - Framework API backend
- [Transformers (Hugging Face)](https://huggingface.co/docs/transformers/index) - Library pemrosesan model IndoBERT
- [PyTorch](https://pytorch.org/) - Backend komputasi Deep Learning
- [aiosqlite](https://github.com/omnilib/aiosqlite) - Database SQLite asinkron
- [PyCryptodome](https://www.pycryptodome.org/) - Enkripsi AES

**Frontend:**
- HTML5, CSS3 (Vanilla), JavaScript
- [Chart.js](https://www.chartjs.org/) - Visualisasi grafik Gauge
- [SweetAlert2](https://sweetalert2.github.io/) - Pop-up notifikasi UI

---

## 📋 Persyaratan Sistem

Sebelum menjalankan aplikasi, pastikan Anda telah menginstal:
1. Python versi 3.10 atau yang lebih baru.
2. [Git LFS (Large File Storage)](https://git-lfs.github.com/) - **WAJIB**, karena model IndoBERT berukuran besar (sekitar 475MB) dan disimpan menggunakan LFS.

---

## 🚀 Cara Instalasi & Menjalankan Aplikasi

### 1. Clone Repository (dengan Git LFS)
Pastikan Git LFS sudah terinstal sebelum melakukan clone agar file model terunduh dengan sempurna.
```bash
git lfs install
git clone https://github.com/zakyprm/Sistem_Skrining_Tingkat_Stres_Berbasis_AI.git
cd Sistem_Skrining_Tingkat_Stres_Berbasis_AI
```

### 2. Buat Virtual Environment
Dianjurkan untuk menggunakan *virtual environment* agar dependensi tidak bentrok.
```bash
python -m venv .venv

# Aktivasi di Windows:
.venv\Scripts\activate

# Aktivasi di Linux/Mac:
source .venv/bin/activate
```

### 3. Instal Dependensi
Masuk ke direktori backend dan instal kebutuhan pustaka Python.
```bash
cd backend
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables
Salin file `.env.example` menjadi `.env` lalu ganti nilai rahasia di dalamnya (seperti `SECRET_KEY` untuk token JWT).
```bash
# Windows
copy .env.example .env

# Linux / Mac
cp .env.example .env
```
*Buka file `.env` di teks editor dan pastikan untuk mengisi `SECRET_KEY` dengan string yang panjang dan acak.*

### 5. Inisialisasi Akun Konselor Pertama
Database akan dibuat secara otomatis saat aplikasi dijalankan, tetapi Anda perlu membuat satu akun awal (Ustadz/Konselor) untuk bisa mengakses dashboard riwayat.
Jalankan script ini **satu kali saja**:
```bash
python seed_user.py
```
*(Ikuti instruksi di layar untuk mengatur Username dan Password)*

### 6. Jalankan Server FastAPI
Jalankan backend server menggunakan Uvicorn:
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Akses Aplikasi via Browser
Buka browser dan akses tautan berikut:
- **Halaman Santri (Deteksi Stres):** [http://localhost:8000/](http://localhost:8000/)
- **Halaman Login Konselor:** [http://localhost:8000/login.html](http://localhost:8000/login.html)
- **Dokumentasi API Otomatis (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Struktur Direktori

```text
Sistem_Skrining_Tingkat_Stres_Berbasis_AI/
├── backend/
│   ├── app.py                   # Entry point aplikasi FastAPI
│   ├── auth.py                  # Logika autentikasi dan JWT
│   ├── database.py              # Koneksi dan skema database SQLite (users & riwayat)
│   ├── encryption.py            # Modul enkripsi (AES) untuk teks curhatan
│   ├── preprocessing.py         # Pembersihan teks (case folding, stopwords, stemming)
│   ├── seed_user.py             # Script untuk membuat akun Konselor
│   ├── model_final_indobert_stres/ # Folder berisi model IndoBERT (dilacak via Git LFS)
│   ├── requirements.txt         # Daftar pustaka Python yang dibutuhkan
│   └── .env.example             # Template file environment
├── frontend/
│   ├── index.html               # Halaman input curhatan santri
│   ├── script.js                # Logika frontend santri (Hit API & Gauge Chart)
│   ├── style.css                # Desain antarmuka santri
│   ├── login.html               # Halaman login Ustadz/Konselor
│   ├── riwayat.html             # Dashboard riwayat Ustadz/Konselor
│   └── ...
└── .gitignore                   # Konfigurasi file yang diabaikan oleh Git
```

---

## ⚠️ Catatan Penting
- **Git LFS:** Jika setelah clone aplikasi gagal melakukan prediksi atau error memuat model (ukuran file model hanya beberapa KB), itu berarti Git LFS tidak terinstal dengan benar saat clone. Jalankan `git lfs pull` untuk menarik file aslinya.
- **Keamanan Data:** File database SQLite (`riwayat_klasifikasi.db`) dan file `.env` telah dimasukkan ke dalam `.gitignore` sehingga tidak akan terunggah ke GitHub, demi menjaga privasi dan keamanan.
