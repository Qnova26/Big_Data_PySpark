import streamlit as st
import pandas as pd
from pymongo import MongoClient
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# 1. Konfigurasi Halaman Streamlit (Tema Modern & Lebar)
st.set_page_config(page_title="E-Wallet Analytics Portal", layout="wide", initial_sidebar_state="expanded")

# Modifikasi CSS Ringan untuk Estetika Modern Minimalis
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { font-weight: 700; color: #1e293b; }
    h2, h3 { font-weight: 600; color: #334155; }
    .stMetric { background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# 2. Inisialisasi Koneksi MongoDB
# KARENA INI PENDEKATAN 2 (DOUBLE WRITE), KITA LANGSUNG TEMBAK LOCALHOST TEMANMU
@st.cache_resource
def init_connection():
    # Menggunakan string koneksi langsung ke localhost
    return MongoClient("mongodb://localhost:27017/")

try:
    client = init_connection()
except Exception as e:
    st.error(f"Gagal terhubung ke MongoDB Lokal. Pastikan layanan MongoDB berjalan: {e}")
    st.stop()

# 3. Fungsi Pengambilan & Penyusunan Struktur Data Menggunakan Pandas
@st.cache_data(ttl=600) 
def load_data_from_mongo():
    db = client.capstone_db
    # NAMA KOLEKSI HARUS COCOK DENGAN YANG ADA DI SPARK (.option("collection", "Clean_Data"))
    collection = db.Clean_Data 
    
    # Menarik dokumen dengan penyesuaian nama kolom baru
    cursor = collection.find({}, {"_id": 0, "app_name": 1, "raw_text": 1, "clean_content": 1, "rating": 1, "created_at": 1, "engagement": 1})
    df = pd.DataFrame(list(cursor))
    
    if df.empty:
        return df
        
    # Konversi tipe data menggunakan Pandas standar
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['date_clean'] = df['created_at'].dt.date
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df['engagement'] = pd.to_numeric(df['engagement'], errors='coerce').fillna(0)
    
    # Rekonstruksi Label Sentimen berdasarkan skor (Score 4-5: Positif, 3: Netral, 1-2: Negatif)
    # Jika rating kosong (misal dari YouTube/Quora), sementara kita isi "Belum Dilabeli"
    df['label_sentimen'] = df['rating'].apply(
        lambda x: 'Positif' if x >= 4 else ('Netral' if x == 3 else ('Negatif' if x <= 2 else 'Belum Dilabeli'))
    )
    
    # Kalkulasi Metrik Karakteristik Teks Langsung di Sisi Pandas
    df['clean_content_str'] = df['clean_content'].fillna("").astype(str)
    df['char_count'] = df['clean_content_str'].str.len()
    df['word_count'] = df['clean_content_str'].apply(lambda x: len(x.split()))
    df['avg_word_len'] = df.apply(lambda r: r['char_count'] / r['word_count'] if r['word_count'] > 0 else 0, axis=1)
    
    return df

df_raw = load_data_from_mongo()

if df_raw.empty:
    st.warning("Koneksi berhasil, namun tidak ada dokumen yang ditemukan di koleksi Clean_Data.")
    st.stop()

# 4. IMPLEMENTASI PANEL KONTROL INTERAKTIF (SIDEBAR)
st.sidebar.title("Panel Kontrol")
st.sidebar.markdown("Sesuaikan filter untuk memperbarui visualisasi seluruh grafik secara instan.")
st.sidebar.divider()

# Filter Pilihan Nama Aplikasi Dompet Digital
all_apps = ["Semua Aplikasi"] + sorted(df_raw['app_name'].dropna().unique().tolist())
selected_app = st.sidebar.selectbox("Pilih Aplikasi/Sumber:", all_apps)

# Filter Rentang Waktu / Tanggal Ulasan (Hanya ambil yang tanggalnya tidak kosong)
valid_dates = df_raw['date_clean'].dropna()
if not valid_dates.empty:
    min_date = valid_dates.min()
    max_date = valid_dates.max()
    selected_dates = st.sidebar.date_input("Rentang Tanggal Analisis:", [min_date, max_date], min_value=min_date, max_value=max_date)
else:
    selected_dates = []
    st.sidebar.info("Tidak ada data temporal (tanggal) yang valid.")

# Logika Pemfilteran Data Berdasarkan Input Pengguna di Sidebar
df_filtered = df_raw.copy()

if selected_app != "Semua Aplikasi":
    df_filtered = df_filtered[df_filtered['app_name'] == selected_app]

if len(selected_dates) == 2:
    df_filtered = df_filtered[(df_filtered['date_clean'] >= selected_dates[0]) & (df_filtered['date_clean'] <= selected_dates[1])]

# Indikator Status Koleksi pada Sisi Bawah Sidebar
st.sidebar.divider()
st.sidebar.metric("Volume Data Aktif", f"{len(df_filtered):,}")
st.sidebar.caption("Sistem Database: Local MongoDB (Replica)")


# 5. STRUKTUR UTAMA DAN SISTEM NAVIGASI (TABBAR)
st.title("Portal Analisis Sentimen & Karakteristik Teks")
st.markdown("Eksplorasi wawasan opini publik mengenai layanan dompet digital secara *real-time*.")
st.divider()

tab_overview, tab_metrics, tab_explorer = st.tabs([
    "Ringkasan & Tren Sentimen", 
    "Karakteristik Komponen Teks", 
    "Penjelajah Dokumen Bersih"
])

# ── TAB 1: RINGKASAN & TREN SENTIMEN ──────────────────────────────────────
with tab_overview:
    st.subheader("Distribusi Sentimen dan Tren Opini Publik")
    
    # Hanya hitung yang punya label valid (Bukan 'Belum Dilabeli')
    df_labeled = df_filtered[df_filtered['label_sentimen'] != 'Belum Dilabeli']
    total_active = len(df_labeled)
    
    pos_c = len(df_labeled[df_labeled['label_sentimen'] == 'Positif'])
    neu_c = len(df_labeled[df_labeled['label_sentimen'] == 'Netral'])
    neg_c = len(df_labeled[df_labeled['label_sentimen'] == 'Negatif'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ulasan Sentimen Positif", f"{pos_c:,}", delta=f"{(pos_c/total_active*100):.1f}%" if total_active > 0 else "0%")
    m2.metric("Ulasan Sentimen Netral", f"{neu_c:,}", delta=f"{(neu_c/total_active*100):.1f}%" if total_active > 0 else "0%", delta_color="off")
    m3.metric("Ulasan Sentimen Negatif", f"{neg_c:,}", delta=f"-{(neg_c/total_active*100):.1f}%" if total_active > 0 else "0%")
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Proporsi Pembagian Rasio Sentimen</p>", unsafe_allow_html=True)
        sentiment_summary = df_labeled['label_sentimen'].value_counts().reset_index()
        sentiment_summary.columns = ['Sentimen', 'Total']
        
        if not sentiment_summary.empty:
            fig_pie = px.pie(sentiment_summary, values='Total', names='Sentimen', 
                            hole=0.45, 
                            color='Sentimen',
                            color_discrete_map={'Positif':'#34d399', 'Netral':'#94a3b8', 'Negatif':'#f87171'})
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Tidak ada data dengan rating/sentimen yang valid di filter ini.")

    with col2:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Tren Fluktuasi Volume Sentimen Harian</p>", unsafe_allow_html=True)
        trend_summary = df_labeled.groupby(['date_clean', 'label_sentimen']).size().reset_index(name='Jumlah')
        
        if not trend_summary.empty:
            fig_line = px.line(trend_summary, x='date_clean', y='Jumlah', color='label_sentimen', markers=True,
                            color_discrete_map={'Positif':'#34d399', 'Netral':'#94a3b8', 'Negatif':'#f87171'})
            fig_line.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                                xaxis_title="", yaxis_title="Jumlah Dokumen")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Rentang waktu atau filter yang Anda pilih tidak memiliki rekaman tren harian.")

# ── TAB 2: KARAKTERISTIK KOMPONEN TEKS ───────────────────────────
with tab_metrics:
    st.subheader("Struktur Kebahasaan Konten Ulasan Pengguna")
    
    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        fig_hist1 = px.histogram(df_filtered, x="char_count", nbins=40,
                                title="Distribusi Sebaran Total Karakter Teks",
                                color_discrete_sequence=['#38bdf8'])
        fig_hist1.update_layout(margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", 
                                bargap=0.1, xaxis_title="Panjang Karakter", yaxis_title="Frekuensi Kemunculan")
        st.plotly_chart(fig_hist1, use_container_width=True)

    with r1_col2:
        fig_hist2 = px.histogram(df_filtered, x="word_count", nbins=40,
                                title="Distribusi Kerapatan Jumlah Kata Dokumen",
                                color_discrete_sequence=['#818cf8'])
        fig_hist2.update_layout(margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", 
                                bargap=0.1, xaxis_title="Jumlah Kata", yaxis_title="Frekuensi Kemunculan")
        st.plotly_chart(fig_hist2, use_container_width=True)

    st.divider()
    
    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        sample_limit = min(1200, len(df_filtered))
        if sample_limit > 0:
            df_scatter_sample = df_filtered.sample(sample_limit, random_state=42)
            fig_scatter = px.scatter(df_scatter_sample, x="word_count", y="char_count", color="avg_word_len",
                                    title="Analisis Korelasi Ragam Jumlah Kata vs Panjang Karakter",
                                    color_continuous_scale='purpor', opacity=0.7)
            fig_scatter.update_layout(margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                                    xaxis_title="Word Count (Kata)", yaxis_title="Char Count (Karakter)",
                                    coloraxis_colorbar=dict(title="Rerata Huruf"))
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Kuantitas data tidak mencukupi untuk memetakan grafik sebaran.")

    # MENYELESAIKAN BAGIAN YANG TERPOTONG DARI KODEMU (WORDCLOUD)
    with r2_col2:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Awan Kata (Word Cloud) dari Ulasan Terpopuler</p>", unsafe_allow_html=True)
        
        # Mengambil teks yang engagement (like) nya tinggi
        top_engaged = df_filtered.sort_values(by='engagement', ascending=False).head(500)
        text_corpus = " ".join(top_engaged['clean_content_str'].tolist())
        
        if len(text_corpus.strip()) > 0:
            wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis', max_words=100).generate(text_corpus)
            fig_wc, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig_wc)
        else:
            st.info("Tidak cukup teks untuk menghasilkan Word Cloud.")

# ── TAB 3: PENJELAJAH DOKUMEN BERSIH ───────────────────────────
with tab_explorer:
    st.subheader("Data Tabular Mentah & Bersih")
    st.markdown("Pratinjau detail dokumen hasil pembersihan *pipeline* Apache Spark.")
    
    # Menampilkan tabel data lengkap yang sudah difilter
    display_df = df_filtered[['app_name', 'created_at', 'rating', 'engagement', 'raw_text', 'clean_content_str']]
    st.dataframe(display_df.head(500), use_container_width=True, height=500)