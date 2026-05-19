import pymongo
from youtube_comment_downloader import YoutubeCommentDownloader

print("Memulai Ekstraksi YouTube (RAW MODE)...")

client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]
collection = db["Data_YouTube"]

downloader = YoutubeCommentDownloader()
urls = [
    "https://www.youtube.com/watch?v=sPbHjVND7fM",
    "https://www.youtube.com/watch?v=3nizazXJGMg",
    "https://www.youtube.com/watch?v=Xxnrd52GY6k"
]
all_comments = []

for url in urls:
    print(f"Menyedot komentar mentah dari: {url}")
    comments = downloader.get_comments_from_url(url, sort_by=0)
    count = 0
    for comment in comments:
        # Menyimpan SELURUH isi dictionary dari API YouTube secara utuh
        comment['source_url'] = url # Menambahkan identitas sumber
        all_comments.append(comment)
        count += 1
        if count >= 500: break

if all_comments:
    print("Menyimpan ke MongoDB (Data_YouTube)...")
    collection.delete_many({})
    collection.insert_many(all_comments)
    print(f"SUKSES! {len(all_comments)} data RAW YouTube tersimpan.")

client.close()