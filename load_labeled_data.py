import pandas as pd
import pymongo

# Ganti dengan nama file CSV hasil download dari Google Sheets kamu
NAMA_FILE_CSV = "data_label_1000_final.csv"

print(f"Membaca {NAMA_FILE_CSV}...")
df = pd.read_csv(NAMA_FILE_CSV)

# Pastikan tidak ada data kosong di kolom label (jika ada yang terlewat)
df = df.dropna(subset=['label_sentimen'])

# Ubah ke format dictionary untuk MongoDB
records = df.to_dict('records')

print("Menyimpan ke MongoDB (Koleksi: ground_truth_1000)...")
client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]
collection = db["ground_truth_1000"]

# Bersihkan koleksi jika sebelumnya sudah ada
collection.delete_many({})
collection.insert_many(records)

print(f"✅ MANTAP! {len(records)} Data Emas berhasil masuk ke MongoDB!")
client.close()