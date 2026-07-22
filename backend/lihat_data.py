import sqlite3
from dotenv import load_dotenv
from encryption import decrypt_text

def lihat_data():
    # Load variabel environment (terutama ENCRYPTION_KEY dari .env)
    load_dotenv()
    
    # Hubungkan ke database SQLite
    try:
        conn = sqlite3.connect('riwayat_klasifikasi.db')
        cur = conn.cursor()
        
        # Ambil data dari database
        cur.execute('SELECT id, teks_terenkripsi, label, timestamp FROM riwayat_klasifikasi ORDER BY timestamp DESC')
        rows = cur.fetchall()
        
        if not rows:
            print("Database masih kosong.")
            return

        print("="*80)
        print(f"{'ID':<5} | {'Waktu':<20} | {'Label':<10} | {'Teks Asli'}")
        print("="*80)
        
        for row in rows:
            id_db, teks_terenkripsi, label, timestamp = row
            try:
                # Dekripsi teks asli
                teks_asli = decrypt_text(teks_terenkripsi)
            except Exception as e:
                teks_asli = f"[ERROR DEKRIPSI: {e}]"
            
            print(f"{id_db:<5} | {timestamp:<20} | {label:<10} | {teks_asli}")
            
    except sqlite3.Error as e:
        print(f"Error membaca database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    lihat_data()
