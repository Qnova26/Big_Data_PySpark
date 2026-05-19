import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, lower, trim

# --- 1. KONFIGURASI JARINGAN & ENVIRONMENT ---
MASTER_IP = "10.62.96.30" # Ganti dengan IP IPv4 Laptop Master kamu!
MONGO_URI = f"mongodb://{MASTER_IP}:27017/capstone_db"

if 'SPARK_HOME' in os.environ:
    del os.environ['SPARK_HOME']
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

print("Memulai Mesin Spark Terdistribusi...")

# --- 2. INISIALISASI CLUSTER SPARK ---
# Perhatikan parameter .master() yang menunjuk ke URL Spark Cluster
spark = SparkSession.builder \
    .appName("Distributed_Ewallet_Preprocessing") \
    .master(f"spark://{MASTER_IP}:7077") \
    .config("spark.executor.memory", "2g") \
    .config("spark.executor.cores", "2") \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.3.0") \
    .getOrCreate()

print(f"Terhubung ke Cluster Spark di {MASTER_IP}!")

# --- 3. FUNGSI PREPROCESSING TEXT ---
def clean_text_pipeline(df, column_name):
    """Membersihkan teks (Lowercasing, Hapus Tanda Baca, Trim Whitespace)"""
    return df.withColumn("clean_content", lower(col(column_name))) \
             .withColumn("clean_content", regexp_replace(col("clean_content"), r"[^a-zA-Z0-9\s]", "")) \
             .withColumn("clean_content", trim(col("clean_content")))

# --- 4. EXTRACT: Menarik Data Mentah dari Data Lake (MongoDB) ---
print("Membaca data mentah dari MongoDB...")
df_ps = spark.read.format("mongodb").option("collection", "Data_PlayStore").load()
df_yt = spark.read.format("mongodb").option("collection", "Data_YouTube").load()
df_qu = spark.read.format("mongodb").option("collection", "Data_Quora").load()

# --- 5. SCHEMA ALIGNMENT (Mengambil Kolom Inti Saja) ---
# PlayStore memiliki r['content'], YouTube memiliki comment['text'], Quora memiliki raw_text
print("Menyelaraskan Struktur Kolom (Schema Evolution)...")
df_ps_std = df_ps.select(
    col("source_app_name").alias("app_name"), 
    col("content").alias("raw_text")
)

df_yt_std = df_yt.select(
    col("source_url").alias("app_name"), # Kita gunakan URL sebagai identifier video
    col("text").alias("raw_text")
)

df_qu_std = df_qu.select(
    col("source_url").alias("app_name"), 
    col("raw_text")
)

# --- 6. TRANSFORM: Penggabungan dan Pembersihan ---
print("MENGIRIM TUGAS KE WORKER NODE...")
# Menyatukan ketiga tabel
df_master = df_ps_std.union(df_yt_std).union(df_qu_std)

# Menjalankan pembersihan (Proses ini yang akan dipecah dan dikerjakan oleh Laptop Worker)
df_clean = clean_text_pipeline(df_master, "raw_text")

# Membuang baris yang setelah dibersihkan menjadi kosong
df_clean = df_clean.filter(col("clean_content") != "")

# --- 7. LOAD: Menyimpan Data Bersih ke MongoDB ---
print("Menyimpan Data Bersih ke MongoDB (Collection: Clean_Data)...")
df_clean.write.format("mongodb") \
    .option("collection", "Clean_Data") \
    .mode("overwrite") \
    .save()

print("PREPROCESSING TERDISTRIBUSI SELESAI!")
spark.stop()