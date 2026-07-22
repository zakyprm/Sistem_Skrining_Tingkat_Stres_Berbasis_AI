"""
app.py — Backend FastAPI untuk Klasifikasi Tingkat Stres Santri
Menggunakan model IndoBERT fine-tuned + Gemini API untuk pesan edukatif.

Sesuai PRD:
- BR-01: Endpoint POST /predict
- BR-03: Model di-load sekali saat startup
- BR-07: CORS dikonfigurasi untuk frontend lokal
- BR-08: Simpan hasil klasifikasi ke database
- BR-09: Teks narasi dienkripsi sebelum disimpan
- BR-11: GET /riwayat — daftar log klasifikasi dengan pagination
- BR-12: Dashboard riwayat konselor
- BR-13: Endpoint riwayat tidak mengembalikan teks narasi
- BR-14: Filter rentang tanggal
- BR-15: Inisialisasi database otomatis saat startup
"""

import json
import gc
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

import torch
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from dotenv import load_dotenv

from preprocessing import clean_text, validate_input
from encryption import encrypt_text, validate_encryption_key
from database import init_db, simpan_klasifikasi, get_riwayat, get_ringkasan, get_user_by_username
from auth import create_access_token, verify_password, get_current_user

# Load environment variables
load_dotenv()

# ─── Paths ───────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent / "model_final_indobert_stres"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# ─── Global references (diisi saat startup) ─────────────────────────
model = None
tokenizer = None
label_map = None
device = None
gemini_model = None  # Gemini client

# ─── Pesan reflektif per level (hangat, persuasif-edukatif, non-judgmental) ──
PESAN_FALLBACK = {
    "Normal": (
        "Dari tulisanmu, terlihat bahwa kamu sedang dalam kondisi yang cukup baik "
        "saat ini. Itu sesuatu yang patut disyukuri. Tetaplah menjaga ritme "
        "istirahat dan aktivitasmu agar keseimbangan ini terus terjaga. "
        "Sesekali, luangkan waktu untuk hal-hal kecil yang membuatmu senang "
        "— karena merawat diri sendiri adalah bentuk ibadah juga."
    ),
    "Sedang": (
        "Tulisanmu menunjukkan bahwa ada beberapa hal yang mungkin sedang membebani "
        "pikiranmu. Perasaan seperti ini wajar dan tidak perlu kamu pendam sendiri. "
        "Cobalah berbagi cerita dengan teman yang kamu percaya, atau luangkan "
        "sejenak untuk menarik napas dan memberi jeda pada dirimu. Ingat, "
        "meminta bantuan bukan berarti lemah — itu justru bentuk keberanian."
    ),
    "Tinggi": (
        "Kami menyadari dari tulisanmu bahwa kamu mungkin sedang menanggung beban "
        "yang cukup berat. Kamu tidak harus melewati ini sendirian — ada orang-orang "
        "di sekitarmu yang siap mendengarkan dan membantu. Menghubungi seseorang "
        "yang kamu percaya adalah langkah pertama yang sangat berani. Di bawah ini "
        "ada beberapa kontak yang bisa kamu hubungi kapan saja."
    ),
}

# ─── Info rujukan (muncul saat level Tinggi) ─────────────────────────
RUJUKAN = {
    "kontak_internal": (
        "Konselor/Ustadz Pendamping Pondok — "
        "Silakan hubungi pengurus pondok untuk informasi konselor yang tersedia."
    ),
    "kontak_eksternal": (
        " Biro Psikologi Psy Up: 089507520507 (SETIAP HARI: 08.00 - 20.00 WIB)"
    ),
}


# ─── Gemini: Generate pesan edukatif variatif ────────────────────────
GEMINI_SYSTEM_PROMPT = """Kamu adalah konselor pendamping yang hangat dan penuh empati di sebuah pondok pesantren. 
Tugasmu adalah menulis SATU paragraf pesan edukatif singkat (3-5 kalimat) untuk seorang santri 
berdasarkan hasil skrining tingkat stres dari analisis tulisannya.

ATURAN KETAT:
- Gunakan bahasa Indonesia yang hangat, persuasif, dan TIDAK menghakimi.
- Gunakan kata "kamu" (bukan "Anda") agar terasa dekat.
- Ini BUKAN diagnosis klinis — selalu gunakan kata "indikasi" atau "menunjukkan".
- JANGAN pernah menyebut detail tulisan santri karena kamu tidak memiliki aksesnya.
- Variasikan saran dan gaya bahasa setiap kali diminta — jangan monoton.
- Untuk level TINGGI: sertakan dorongan untuk mencari bantuan, tapi tetap lembut.
- Untuk level NORMAL: berikan apresiasi dan dorongan positif.
- Untuk level SEDANG: berikan saran self-care konkret yang bervariasi.
- Akhiri dengan kalimat yang memberi harapan atau kekuatan.
- JANGAN gunakan emoji.
- Tulis HANYA paragraf pesannya saja, tanpa pembuka atau penutup tambahan."""


async def generate_gemini_message(label: str, confidence: dict) -> str | None:
    """
    Generate pesan edukatif variatif menggunakan Gemini API.
    Hanya mengirim label & confidence — BUKAN teks curhatan santri (privasi).
    Returns None jika gagal (akan fallback ke pesan statis).
    """
    if gemini_model is None:
        return None

    try:
        confidence_str = ", ".join(
            f"{k}: {v*100:.1f}%" for k, v in confidence.items()
        )
        user_prompt = (
            f"Hasil skrining: Tingkat stres = {label}.\n"
            f"Distribusi kepercayaan model: {confidence_str}.\n\n"
            f"Tulis pesan edukatif untuk santri dengan hasil ini."
        )

        response = await gemini_model.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config={
                "system_instruction": GEMINI_SYSTEM_PROMPT,
                "temperature": 0.9,
                "max_output_tokens": 300,
            },
        )

        generated_text = response.text.strip()

        # Validasi: pastikan tidak kosong dan tidak terlalu panjang
        if generated_text and 20 < len(generated_text) < 1000:
            return generated_text

        return None

    except Exception as e:
        print(f"[WARN] Gemini API error: {e}")
        return None


# ─── Lifespan: load model sekali saat startup ───────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model dan tokenizer sekali saat server start (BR-03, BR-15)."""
    global model, tokenizer, label_map, device, gemini_model

    print("[INFO] Memuat model IndoBERT...")

    # Validasi ENCRYPTION_KEY (NFR-01) — fail fast jika tidak ada
    validate_encryption_key()

    # Inisialisasi database (BR-15)
    await init_db()

    # Tentukan device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   Device: {device}")

    # Load label map
    label_map_path = MODEL_DIR / "label_map.json"
    with open(label_map_path, "r", encoding="utf-8") as f:
        label_map = json.load(f)
    print(f"   Label map: {label_map}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    print("   [OK] Tokenizer loaded")

    # Load model
    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR),
        num_labels=len(label_map),
    )
    model.to(device)
    model.eval()
    print("   [OK] Model loaded & set to eval mode")

    # Setup Gemini API (opsional — fallback ke pesan statis jika tidak ada key)
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_api_key)
            gemini_model = client.aio.models
            print("   [OK] Gemini API connected")
        except Exception as e:
            print(f"   [WARN] Gemini API setup failed: {e}")
            gemini_model = None
    else:
        print("   [INFO] GEMINI_API_KEY not set — using static messages")
        gemini_model = None

    print("[READY] Server siap menerima request!")

    yield  # Server berjalan

    # Cleanup saat shutdown
    del model, tokenizer, label_map
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("[STOP] Model unloaded, server shutdown.")


# ─── App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="API Klasifikasi Stres Santri",
    description="Endpoint untuk klasifikasi tingkat stres berbasis narasi teks menggunakan IndoBERT.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (BR-07) — izinkan frontend lokal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development: izinkan semua origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schema ──────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    teks: str


class ConfidenceScores(BaseModel):
    Normal: float
    Sedang: float
    Tinggi: float


class RujukanInfo(BaseModel):
    kontak_internal: str
    kontak_eksternal: str


class PredictResponse(BaseModel):
    label: str
    confidence: ConfidenceScores
    pesan: str
    tampilkan_rujukan: bool
    rujukan: RujukanInfo | None = None


class ErrorResponse(BaseModel):
    error: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Endpoint Prediksi ──────────────────────────────────────────────
@app.post(
    "/predict",
    response_model=PredictResponse,
    responses={400: {"model": ErrorResponse}},
)
async def predict(request: PredictRequest):
    """
    Menerima teks narasi dan mengembalikan klasifikasi tingkat stres.
    
    Alur: validasi -> preprocessing -> tokenisasi -> inference -> response.
    Teks TIDAK disimpan (BR-05).
    """
    raw_text = request.teks

    # ── Validasi input (BR-06) ──
    is_valid, error_msg = validate_input(raw_text)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # ── Preprocessing (BR-02) ──
    cleaned_text = clean_text(raw_text)

    # Validasi ulang setelah cleaning (bisa jadi teks jadi pendek setelah dibersihkan)
    is_valid_cleaned, error_msg_cleaned = validate_input(cleaned_text)
    if not is_valid_cleaned:
        # Hapus variabel teks dari memori
        del raw_text, cleaned_text
        raise HTTPException(
            status_code=400,
            detail="Setelah dibersihkan, teks terlalu pendek untuk dianalisis. "
                   "Mohon tulis narasi yang lebih panjang."
        )

    try:
        # ── Tokenisasi (identik dengan training: max_length=128, padding='max_length') ──
        inputs = tokenizer(
            cleaned_text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding="max_length",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # ── Inference (no grad untuk efisiensi) ──
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            print(f"[DEBUG] Logits mentah: {logits[0].cpu().tolist()}")
            
        # ── Softmax -> probabilitas per kelas ──
        probabilities = torch.nn.functional.softmax(logits, dim=-1)
        probs = probabilities[0].cpu().tolist()

        # ── Tentukan label ──
        predicted_idx = torch.argmax(probabilities, dim=-1).item()
        predicted_label = label_map[str(predicted_idx)]

        # ── Confidence scores ──
        confidence = {
            label_map[str(i)]: round(probs[i], 4)
            for i in range(len(label_map))
        }

        # ── Generate pesan edukatif (Gemini atau fallback) ──
        pesan = None
        if gemini_model is not None:
            pesan = await generate_gemini_message(predicted_label, confidence)
        
        # Fallback ke pesan statis jika Gemini tidak tersedia/gagal
        if pesan is None:
            pesan = PESAN_FALLBACK[predicted_label]

        # ── Bangun response ──
        tampilkan_rujukan = predicted_label == "Tinggi"
        response = PredictResponse(
            label=predicted_label,
            confidence=ConfidenceScores(**confidence),
            pesan=pesan,
            tampilkan_rujukan=tampilkan_rujukan,
            rujukan=RujukanInfo(**RUJUKAN) if tampilkan_rujukan else None,
        )

        # ── Simpan ke database (BR-08, BR-09) ──
        # Dilakukan setelah response dibangun agar tidak memblokir
        try:
            encrypted_text = encrypt_text(raw_text)
            await simpan_klasifikasi(
                teks_terenkripsi=encrypted_text,
                label=predicted_label,
                confidence_rendah=confidence.get("Normal", 0.0),
                confidence_sedang=confidence.get("Sedang", 0.0),
                confidence_tinggi=confidence.get("Tinggi", 0.0),
            )
        except Exception as e:
            # NFR-04: Kegagalan simpan tidak boleh membuat app crash
            print(f"[ERROR] Gagal menyimpan ke database: {e}")

        return response

    finally:
        del raw_text, cleaned_text
        gc.collect()


# ─── Endpoint Login (AUTH) ──────────────────────────────────────────────
@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login untuk Ustadz/Konselor.
    Mengembalikan JWT access token jika kredensial valid.
    """
    user = await get_user_by_username(request.username)
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Username atau password salah",
        )
    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return LoginResponse(access_token=token)


# ─── Endpoint Riwayat Klasifikasi (BR-11, BR-13, BR-14) ──────────────────────
@app.get("/riwayat")
async def riwayat(
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah data per halaman"),
    offset: int = Query(default=0, ge=0, description="Offset untuk pagination"),
    tanggal_mulai: Optional[str] = Query(default=None, description="Filter tanggal awal (YYYY-MM-DD)"),
    tanggal_selesai: Optional[str] = Query(default=None, description="Filter tanggal akhir (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Daftar log riwayat klasifikasi terurut dari terbaru.
    Tidak mengembalikan teks narasi (BR-13).
    Memerlukan autentikasi JWT (AUTH).
    """
    data = await get_riwayat(
        limit=limit,
        offset=offset,
        tanggal_mulai=tanggal_mulai,
        tanggal_selesai=tanggal_selesai,
    )
    return data


# ─── Endpoint Ringkasan (pendukung BR-12) ───────────────────────────
@app.get("/ringkasan")
async def ringkasan(
    tanggal_mulai: Optional[str] = Query(default=None, description="Filter tanggal awal (YYYY-MM-DD)"),
    tanggal_selesai: Optional[str] = Query(default=None, description="Filter tanggal akhir (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
):
    """Ringkasan jumlah klasifikasi per label. Memerlukan autentikasi JWT (AUTH)."""
    data = await get_ringkasan(
        tanggal_mulai=tanggal_mulai,
        tanggal_selesai=tanggal_selesai,
    )
    return data


# ─── Health check ────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Cek apakah server dan model siap."""
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "gemini_active": gemini_model is not None,
        "device": str(device) if device else "unknown",
    }


# ─── Serve Frontend (static files + index.html at root) ─────────────
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
