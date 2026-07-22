"""Debug — test with EXACT training preprocessing & tokenizer params"""
import torch, json, re
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from pathlib import Path

MODEL_DIR = Path("model_final_indobert_stres")

with open(MODEL_DIR / "label_map.json") as f:
    label_map = json.load(f)

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
model.eval()

# EXACT training preprocessing
def cleaning_lanjutan(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z\s]', '', text)  # Hanya huruf dan spasi
    text = re.sub(r'\s+', ' ', text).strip()
    return text

test_texts = [
    "hari ini saya merasa sangat bahagia karena bisa bermain bersama teman teman di pondok dan belajar dengan tenang",
    "alhamdulillah saya merasa nyaman di pondok ini teman teman baik dan ustadz sangat perhatian kepada kami semua",
    "aku sangat tertekan akhir akhir ini tidak bisa tidur dan selalu merasa cemas setiap hari di pondok pesantren",
    "saya sering menangis sendiri di kamar karena merasa tidak kuat lagi dengan tekanan hafalan dan tugas setiap hari",
]

print("=== EXACT training params: max_length=128, padding=max_length ===\n")
for t in test_texts:
    cleaned = cleaning_lanjutan(t)
    inputs = tokenizer(cleaned, return_tensors="pt", truncation=True,
                       max_length=128, padding="max_length")
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1)[0]
    pred = torch.argmax(probs).item()
    all_probs = [round(x, 4) for x in probs.tolist()]
    lbl = label_map.get(str(pred), "?")
    print(f"Input  : {t[:70]}...")
    print(f"Cleaned: {cleaned[:70]}...")
    print(f"Probs  : R={all_probs[0]}  S={all_probs[1]}  T={all_probs[2]}")
    print(f"Result : {lbl} ({all_probs[pred]*100:.1f}%)")
    print()

print("\n=== WRONG params (our current code): max_length=512, padding=True ===\n")
for t in test_texts:
    cleaned = cleaning_lanjutan(t)
    inputs = tokenizer(cleaned, return_tensors="pt", truncation=True,
                       max_length=512, padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1)[0]
    pred = torch.argmax(probs).item()
    all_probs = [round(x, 4) for x in probs.tolist()]
    lbl = label_map.get(str(pred), "?")
    print(f"Input  : {t[:70]}...")
    print(f"Probs  : R={all_probs[0]}  S={all_probs[1]}  T={all_probs[2]}")
    print(f"Result : {lbl} ({all_probs[pred]*100:.1f}%)")
    print()
