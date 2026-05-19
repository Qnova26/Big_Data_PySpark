import pymongo
import asyncio
import random
from playwright.async_api import async_playwright

client = pymongo.MongoClient("mongodb://127.0.0.1:27017/")
db = client["capstone_db"]
collection = db["Data_Quora"]

ANSWER_SELECTORS = [
    "div.q-box.qu-userSelect--text span",
    "div[class*='q-text'] span",
    "div.puppeteer_test_answer_content span",
    "div[data-testid='answer'] span",
]

async def _collect_raw_texts(page) -> list:
    found = []
    for sel in ANSWER_SELECTORS:
        try:
            elements = await page.query_selector_all(sel)
            for el in elements:
                # Mengambil teks apa adanya (mentah)
                txt = await el.inner_text()
                if len(txt) > 30: 
                    found.append(txt)
        except Exception:
            continue
    return found

async def scrape_quora_posts(urls: list, target_per_page: int = 500):
    all_records = []
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )

        for url in urls:
            print(f"\nMembuka: {url}")
            page = await context.new_page()
            
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception:
                await page.close()
                continue
            
            await asyncio.sleep(random.randint(5, 10))
            
            page_texts = set()
            scroll_step = 1000
            
            for scroll_i in range(1, 100):
                try:
                    await page.evaluate(f"window.scrollBy(0, {scroll_step})")
                    new_texts = await _collect_raw_texts(page)
                    page_texts.update(new_texts)
                    if len(page_texts) >= target_per_page: break
                    await asyncio.sleep(random.uniform(2.0, 4.0))
                except Exception:
                    break
            
            collected = list(page_texts)[:target_per_page]
            for text in collected:
                # Simpan mentah-mentah (raw text)
                all_records.append({
                    "raw_text": text,
                    "source_url": url
                })
            await page.close()
        await browser.close()
        
    if all_records:
        print("\nMenyimpan ke MongoDB (Data_Quora)...")
        collection.delete_many({})
        collection.insert_many(all_records)
        print(f"SUKSES! {len(all_records)} data RAW Quora tersimpan.")

# --- Bagian Eksekusi ---
if __name__ == "__main__":
    print("🚀 Memulai Ekstraksi Quora (RAW MODE)...")
    
    # Daftar URL Asli Tim Capstone Carlos
    quora_urls = [
        # ── Pertanyaan spesifik ──────────────────────────────────────────────
        "https://www.quora.com/What-is-the-best-e-wallet-in-Southeast-Asia",
        "https://www.quora.com/Which-e-wallet-is-the-safest-to-use",
        "https://www.quora.com/What-are-the-advantages-of-using-an-e-wallet",
        "https://www.quora.com/How-do-e-wallets-work",
        "https://www.quora.com/Is-GoPay-or-OVO-better-in-Indonesia",
        "https://www.quora.com/What-is-the-difference-between-GoPay-OVO-and-Dana",
        "https://www.quora.com/How-secure-are-digital-wallets",
        "https://www.quora.com/What-are-the-best-e-wallets-available-in-Indonesia",

        # ── Topik / tag ──────────────────────────────────────────────────────
        "https://www.quora.com/topic/E-Wallets",
        "https://www.quora.com/topic/Digital-Wallets",
        "https://www.quora.com/topic/Mobile-Payments",
        "https://www.quora.com/topic/GoPay",
        "https://www.quora.com/topic/OVO-Indonesia",
        "https://www.quora.com/topic/Dana-e-wallet",
    ]
    
    # Jalankan proses Asynchronous
    asyncio.run(scrape_quora_posts(quora_urls, target_per_page=500))
    client.close()