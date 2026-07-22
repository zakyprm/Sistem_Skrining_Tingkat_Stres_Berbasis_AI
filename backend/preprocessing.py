"""
preprocessing.py
Fungsi preprocessing teks untuk klasifikasi stres santri.
Pipeline ini IDENTIK dengan preprocessing saat training model IndoBERT.
Sesuai PRD BR-02: preprocessing identik dengan pipeline training.

Sumber: Cell 5 notebook training — fungsi cleaning_lanjutan()
"""

import re


def clean_text(text: str) -> str:
    """
    Membersihkan teks input sebelum tokenisasi.
    IDENTIK dengan fungsi cleaning_lanjutan() di notebook training.

    Pipeline:
    1. Konversi ke string & lowercase
    2. Hapus semua karakter kecuali huruf a-z dan spasi
    3. Normalisasi whitespace

    PENTING: Kata negasi (tidak, bukan, belum, jangan, dll.) DIPERTAHANKAN.
    """
    if not text:
        return ""

    # 1. Konversi ke string & lowercase
    text = str(text).lower()

    # 2. Hapus semua karakter kecuali huruf dan spasi
    #    (identik dengan training: re.sub(r'[^a-z\s]', '', text))
    text = re.sub(r'[^a-z\s]', '', text)

    # 3. Normalisasi whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def count_words(text: str) -> int:
    """Menghitung jumlah kata dalam teks."""
    if not text or not text.strip():
        return 0
    return len(text.strip().split())


def validate_input(text: str) -> tuple[bool, str]:
    """
    Validasi input teks.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Teks tidak boleh kosong."

    word_count = count_words(text)
    if word_count < 10:
        return False, (
            f"Teks terlalu pendek ({word_count} kata). "
            "Mohon tulis minimal 10 kata agar analisis lebih bermakna."
        )

    return True, ""
