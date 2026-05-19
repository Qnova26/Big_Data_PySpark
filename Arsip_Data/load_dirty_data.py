import os
import sys
from pyspark.sql import SparkSession
import pymongo
import pandas as pd
import numpy as np # Ditambahkan untuk menangani NaN

# =========================================================
# AUTO-PATHING: Mencari lokasi absolut file CSV
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(BASE_DIR, "master_dataset_ewallet.csv")

# =========================================================
# PERSIAPAN ENVIRONMENT
# =========================================================
if 'SPARK_HOME' in os.environ:
    del os.environ['SPARK_HOME']
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
os.environ['HADOOP_HOME'] = "C:\\hadoop"
sys.path.append("C:\\hadoop\\bin")

# Menggunakan localhost
WIFI_IP = "127.0.0.1"  
DB_URI = f"mongodb://{WIFI_IP}:27017/"

spark = SparkSession.builder \
    .appName("Ewallet_Load_Dirty_Data") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

print("Spark Session dimulai!")

# =========================================================
# BACA FILE CSV KOTOR (SUPER MENTAH)
# =========================================================
print(f"Membaca file dari: {csv_path} ...")
# Pastikan membaca dari csv_path, bukan sekadar nama filenya
df_dirty = spark.read.csv(csv_path, header=True, inferSchema=True, multiLine=True, escape='"')

jumlah_data = df_dirty.count()
print(f"Total data yang akan dimasukkan: {jumlah_data} baris")

# =========================================================
# SIMPAN KE MONGODB (Koleksi: dirty_ewallet_data)
# =========================================================
print("Memasukkan data ke MongoDB, mohon tunggu...")
try:
    # 1. Ubah ke pandas DataFrame
    df_pandas = df_dirty.toPandas()
    
    # 2. FIX ELT: Ubah semua nilai NaN menjadi None agar diterima PyMongo sebagai 'null'
    df_pandas = df_pandas.replace({np.nan: None})
    
    # 3. Ubah ke bentuk dictionary
    records = df_pandas.to_dict('records')
    
    if records:
        client = pymongo.MongoClient(DB_URI)
        db = client["capstone_db"]
        
        collection = db["dirty_ewallet_data"]
        collection.delete_many({}) # Idempotensi: Hapus data lama agar tidak dobel
        
        collection.insert_many(records)
        client.close()
        print("data mentah berhasil masuk ke MongoDB")
    else:
        print("CSV kosong!")
except Exception as e:
    print(f"Gagal menyimpan: {e}")
finally:
    spark.stop()