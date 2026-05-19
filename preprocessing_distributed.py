import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim
import pymongo
import pandas as pd

# =========================================================
# 1. KONFIGURASI JARINGAN & PEMBAGIAN TUGAS
# =========================================================
WIFI_IP_MASTER = "192.168.110.222" # IP Master Carlos

# CARLOS: Nyalakan baris ini, matikan baris teman
target_apps = ["GoPay", "ShopeePay", "General"] 

# TEMAN CARLOS: Nyalakan baris ini, matikan baris Carlos
# target_apps = ["DANA", "E-Wallet Discussion"] 

# =========================================================
# 2. INISIALISASI SPARK KLASTER (FIX PYTHON PATH)
# =========================================================
if 'SPARK_HOME' in os.environ:
    del os.environ['SPARK_HOME']

# PERUBAHAN KRUSIAL: Memanggil "python" secara universal, bukan path absolut
os.environ['PYSPARK_PYTHON'] = "python"
os.environ['PYSPARK_DRIVER_PYTHON'] = "python"
os.environ['HADOOP_HOME'] = "C:\\hadoop"
sys.path.append("C:\\hadoop\\bin")

spark = SparkSession.builder \
    .appName("Capstone_Distributed_ETL") \
    .master(f"spark://{WIFI_IP_MASTER}:7077") \
    .config("spark.executor.memory", "2g") \
    .getOrCreate()

print(f"✅ Terhubung ke Spark Master: {WIFI_IP_MASTER}")

# =========================================================
# 3. EXTRACTION: Ambil Data dari MongoDB Master
# =========================================================
try:
    print(f"🔗 Menghubungi MongoDB di {WIFI_IP_MASTER}...")
    client = pymongo.MongoClient(f"mongodb://{WIFI_IP_MASTER}:27017/")
    db = client["capstone_db"]
    col_dirty = db["dirty_ewallet_data"]
    
    query = {"app_name": {"$in": target_apps}}
    cursor = col_dirty.find(query)
    
    pdf = pd.DataFrame(list(cursor))
    if pdf.empty:
        print("⚠️ Tidak ada data ditemukan untuk kategori ini.")
    else:
        if '_id' in pdf.columns: pdf = pdf.drop(columns=['_id'])
        df_spark = spark.createDataFrame(pdf)

        # =========================================================
        # 4. TRANSFORMATION: Preprocessing Paralel
        # =========================================================
        print(f"✨ Memproses {df_spark.count()} data secara terdistribusi...")
        df_clean = df_spark \
            .dropna(subset=["content"]) \
            .dropDuplicates(["content", "app_name"]) \
            .withColumn("clean_content", lower(col("content"))) \
            .withColumn("clean_content", regexp_replace(col("clean_content"), r"[^\w\s]", "")) \
            .withColumn("clean_content", regexp_replace(col("clean_content"), r"\d+", "")) \
            .withColumn("clean_content", trim(col("clean_content"))) \
            .filter(col("clean_content") != "")

        # =========================================================
        # 5. LOADING: Kirim Kembali ke MongoDB Master
        # =========================================================
        records_clean = df_clean.toPandas().to_dict('records')
        if records_clean:
            db["clean_ewallet_data"].insert_many(records_clean)
            print(f"🚀 SUKSES! {len(records_clean)} data bersih tersimpan di Master.")

    client.close()
except Exception as e:
    print(f"❌ Terjadi kesalahan: {e}")
finally:
    spark.stop()