import pandas as pd
import os

print("Memulai proses integrasi Data ELT (Super Mentah)...")

# 1. Load data yang sudah ada (PlayStore & YouTube)
if os.path.exists("raw_dataset_ewallet.csv"):
    df_main = pd.read_csv("raw_dataset_ewallet.csv", low_memory=False)
    print(f"Dataset Utama (PlayStore+YT) dimuat: {len(df_main)} baris | {len(df_main.columns)} kolom.")
else:
    print("Dataset utama belum ditemukan!")
    df_main = pd.DataFrame()

# 2. Load data Quora
if os.path.exists("dataset_quora_ewallet.csv"):
    df_quora = pd.read_csv("dataset_quora_ewallet.csv", low_memory=False)
    print(f"Dataset Quora dimuat: {len(df_quora)} baris | {len(df_quora.columns)} kolom.")
else:
    print("Dataset Quora belum ditemukan!")
    df_quora = pd.DataFrame()

# 3. Penggabungan Otomatis (Pandas Outer Join)
# Pandas akan otomatis menumpuk data. Jika ada kolom yang tidak cocok, otomatis diisi NaN (Kosong).
df_merged_final = pd.concat([df_main, df_quora], ignore_index=True)

# 4. Simpan sebagai Master Dataset
output_name = "master_dataset_ewallet.csv"
df_merged_final.to_csv(output_name, index=False, encoding="utf-8-sig")

print("\n" + "="*50)
print("PENGGABUNGAN SUKSES!")
print("="*50)
print(f"Total baris akhir : {len(df_merged_final)} baris")
print(f"Total kolom akhir : {len(df_merged_final.columns)} kolom (Super Mentah)")
print(f"\nDistribusi Sumber Data:\n{df_merged_final['source'].value_counts()}")