import pymongo
import pandas as pd

# 1. Buka Koneksi Lokal (Laptop Master)
client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]

# TARGET SEKARANG: Data yang sudah dibersihkan oleh kalian berdua
collection = db["clean_ewallet_data"]

# 2. Cek Total Data Bersih
total_data = collection.count_documents({})
print(f"Total data bersih di database: {total_data} baris")

if total_data > 0:
    print("Mengekstraksi 1000 sampel acak untuk pelabelan manual...")
    
    # Ambil 1000 data secara acak menggunakan metode aggregate
    pipeline = [{"$sample": {"size": 1000}}]
    sampel_data = list(collection.aggregate(pipeline))
    
    # Buang kolom _id bawaan MongoDB agar rapi
    for doc in sampel_data:
        doc.pop('_id', None)

    # Ubah menjadi DataFrame
    df = pd.DataFrame(sampel_data)
    
    # TAMBAHAN: Buat kolom kosong untuk tempat kamu mengisi label
    df['label_sentimen'] = ""
    
    # Simpan ke CSV (Menggunakan utf-8-sig agar rapi jika dibuka di Excel/Google Sheets)
    df.to_csv("tugas_labeling_manual.csv", index=False, encoding='utf-8-sig')
    print("✅ BERHASIL! File 'tugas_labeling_manual.csv' sudah siap dikerjakan.")
else:
    print("❌ Koleksi clean_ewallet_data kosong! Cek kembali MongoDB-mu.")

client.close()