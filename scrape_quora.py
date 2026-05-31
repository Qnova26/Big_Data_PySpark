import pymongo
import asyncio
import random
from playwright.async_api import async_playwright

client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]
collection = db["Data_Quora"]

async def _collect_posts_with_time(page) -> list:
    """
    Mengekstrak teks dan waktu secara bersamaan menggunakan eksekusi JavaScript di dalam DOM Quora.
    """
    script = """
    () => {
        const results = [];
        // Mencari kotak kontainer yang membungkus seluruh postingan/jawaban
        const containers = document.querySelectorAll('div.puppeteer_test_answer, div.q-box.qu-borderBottom, div.q-box.qu-mb--sm');
        
        for (const container of containers) {
            // 1. Ekstrak Teks Jawaban
            const textEl = container.querySelector('.q-box.qu-userSelect--text, .puppeteer_test_answer_content');
            if (!textEl) continue;
            
            const text = textEl.innerText.trim();
            if (text.length < 30) continue; // Abaikan teks yang terlalu pendek
            
            // 2. Ekstrak Waktu (Timestamp)
            let timeStr = null;
            // Waktu Quora biasanya disembunyikan di tag <a> atau <span>
            const timeElements = container.querySelectorAll('a, span');
            
            for (const el of timeElements) {
                const txt = el.innerText.trim();
                
                // Deteksi pola waktu Quora: "Answered Jan 23", "Updated 2022", "1y", "2mo", "4h"
                if (txt.includes('Answered') || txt.includes('Updated') || txt.includes('Posted') || 
                    /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d+/.test(txt) || 
                    /^\d+[mhdwys]$/.test(txt)) {
                    timeStr = txt;
                    break;
                }
            }
            
            results.push({
                raw_text: text,
                created_at: timeStr || "Unknown" // Beri label Unknown jika benar-benar tidak ada
            });
        }
        return results;
    }
    """
    try:
        # Eksekusi JS dan ambil hasilnya berupa list of dictionaries
        return await page.evaluate(script)
    except Exception as e:
        print(f"Error saat ekstrak DOM: {e}")
        return []

async def scrape_quora_posts(urls: list, target_per_page: int = 500):
    all_records = []
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )

        for url in urls:
            print(f"\n🌐 Membuka: {url}")
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception:
                await page.close()
                continue
            
            await asyncio.sleep(random.randint(5, 10))
            
            # Menggunakan dictionary untuk mencegah duplikasi data berdasarkan raw_text
            page_data = {} 
            scroll_step = 1000
            
            for scroll_i in range(1, 100):
                try:
                    await page.evaluate(f"window.scrollBy(0, {scroll_step})")
                    
                    # Ambil data (Teks + Waktu)
                    new_posts = await _collect_posts_with_time(page)
                    
                    for post in new_posts:
                        # Masukkan ke dict, raw_text sebagai key agar otomatis unik
                        page_data[post['raw_text']] = post['created_at']
                        
                    print(f"  [Scroll {scroll_i}] Terkumpul: {len(page_data)}/{target_per_page} dokumen unik")
                    
                    if len(page_data) >= target_per_page: 
                        break
                        
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                except Exception:
                    break
            
            # Format ulang data sebelum dimasukkan ke list utama
            collected_texts = list(page_data.keys())[:target_per_page]
            for text in collected_texts:
                all_records.append({
                    "raw_text": text,
                    "created_at": page_data[text], # Waktu diselipkan di sini!
                    "source_url": url
                })
                
            await page.close()
        await browser.close()
        
    if all_records:
        print("\n💾 Menyimpan ke MongoDB (Data_Quora)...")
        collection.delete_many({}) # Bersihkan data lama
        collection.insert_many(all_records)
        print(f"✅ SUKSES! {len(all_records)} data RAW Quora (Teks + Waktu) tersimpan.")

# --- Bagian Eksekusi ---
if __name__ == "__main__":
    print("🚀 Memulai Ekstraksi Quora (RAW MODE + TIMESTAMP)...")
    
    # Daftar URL Asli
    quora_urls = [
        "https://www.quora.com/What-is-the-best-e-wallet-in-Southeast-Asia",
        "https://www.quora.com/Which-e-wallet-is-the-safest-to-use",
        "https://www.quora.com/What-are-the-advantages-of-using-an-e-wallet",
        "https://www.quora.com/How-do-e-wallets-work",
        "https://www.quora.com/Is-GoPay-or-OVO-better-in-Indonesia",
        "https://www.quora.com/What-is-the-difference-between-GoPay-OVO-and-Dana",
        "https://www.quora.com/How-secure-are-digital-wallets",
        "https://www.quora.com/What-are-the-best-e-wallets-available-in-Indonesia",
        "https://www.quora.com/topic/E-Wallets",
        "https://www.quora.com/topic/Digital-Wallets",
        "https://www.quora.com/topic/Mobile-Payments",
        "https://www.quora.com/topic/GoPay",
        "https://www.quora.com/topic/OVO-Indonesia",
        "https://www.quora.com/topic/Dana-e-wallet",
    ]
    
    asyncio.run(scrape_quora_posts(quora_urls, target_per_page=500))
    client.close()