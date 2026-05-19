import pymongo
from google_play_scraper import Sort, reviews

print("Memulai Ekstraksi Play Store (RAW MODE)...")

client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]
collection = db["Data_PlayStore"]

apps = {
    'DANA': 'id.dana',
    'GoPay': 'com.gojek.gopay',
    'OVO': 'com.grb.ovo',
    'ShopeePay': 'com.shopee.id'
}
target_per_app = 5000
all_reviews = []

for name, app_id in apps.items():
    print(f"Menyedot ulasan mentah untuk {name}...")
    result, _ = reviews(
        app_id, lang='id', country='id',
        sort=Sort.NEWEST, count=target_per_app
    )
    for r in result:
        # Menyimpan SELURUH isi dictionary dari API secara utuh
        r['source_app_name'] = name # Menambahkan identitas aplikasi
        all_reviews.append(r)

if all_reviews:
    print("Menyimpan ke MongoDB (Data_PlayStore)...")
    collection.delete_many({})
    collection.insert_many(all_reviews)
    print(f"SUKSES! {len(all_reviews)} data RAW Play Store tersimpan.")

client.close()