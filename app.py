import streamlit as st
import pandas as pd
from pymongo import MongoClient
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer

# 1. Konfigurasi Halaman Streamlit (Tema Modern & Lebar)
st.set_page_config(page_title="E-Wallet Analytics Portal", layout="wide", initial_sidebar_state="expanded")

# Modifikasi CSS untuk Tema Dark Mode / Light Mode agar Teks Tetap Terlihat
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1 { font-weight: 700; color: #f8fafc; }
    h2, h3 { font-weight: 600; color: #cbd5e1; }
    
    /* Perbaikan Kotak Metric untuk kompatibilitas Dark Mode */
    [data-testid="stMetric"] { 
        background-color: #1e293b; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #334155; 
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-weight: 600; }
    [data-testid="stMetricValue"] { color: #f1f5f9 !important; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# 2. Inisialisasi Koneksi MongoDB Lokal
@st.cache_resource
def init_connection():
    return MongoClient("mongodb://localhost:27017/")

try:
    client = init_connection()
except Exception as e:
    st.error(f"Gagal terhubung ke MongoDB Lokal. Pastikan layanan MongoDB sudah berjalan: {e}")
    st.stop()

# 3. Fungsi Pengambilan & Penyusunan Struktur Data Menggunakan Pandas
@st.cache_data(ttl=600)
def load_data_from_mongo():
    db = client.capstone_db
    collection = db.Clean_Data 
    
    cursor = collection.find({}, {"_id": 0, "app_name": 1, "created_at": 1, "rating": 1, "engagement": 1, "clean_content": 1, "raw_text": 1})
    df = pd.DataFrame(list(cursor))
    
    if df.empty:
        return df
        
    def extract_date(val):
        if isinstance(val, dict) and '$date' in val:
            return val['$date']
        return val
        
    if 'created_at' in df.columns:
        df['created_at'] = df['created_at'].apply(extract_date)
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df['date_clean'] = df['created_at'].dt.date
    else:
        df['date_clean'] = pd.NaT
    
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
    df['engagement'] = pd.to_numeric(df['engagement'], errors='coerce').fillna(0)
    
    df['label_sentimen'] = df['rating'].apply(
        lambda x: 'Positif' if x >= 4 else ('Netral' if x == 3 else ('Negatif' if 1 <= x <= 2 else 'Tanpa Rating'))
    )
    
    # PERBAIKAN: Baris "dropna(subset=['date_clean'])" dihapus agar Quora (yang tidak ada tanggal) tidak ikut terhapus.
    
    def deteksi_platform(row):
        app_name_lower = str(row['app_name']).lower()
        rating_val = row['rating']
        
        if 'youtube' in app_name_lower:
            return 'YouTube'
        elif 1 <= rating_val <= 5: 
            return 'PlayStore/AppStore'
        else:
            return 'Quora'

    df['platform_type'] = df.apply(deteksi_platform, axis=1)
    
    df['clean_content_str'] = df['clean_content'].fillna("").astype(str)
    df['char_count'] = df['clean_content_str'].str.len()
    df['word_count'] = df['clean_content_str'].apply(lambda x: len(x.split()))
    df['avg_word_len'] = df.apply(lambda r: r['char_count'] / r['word_count'] if r['word_count'] > 0 else 0, axis=1)
    
    df = df[df['clean_content_str'].str.strip() != ""]
    return df

df_raw = load_data_from_mongo()

if df_raw.empty:
    st.warning("Koneksi berhasil, namun tidak ada dokumen yang ditemukan di dalam koleksi Clean_Data MongoDB.")
    st.stop()

# 4. IMPLEMENTASI PANEL KONTROL INTERAKTIF (SIDEBAR)
st.sidebar.title("⚙️ Panel Kontrol Analisis")
st.sidebar.markdown("Sesuaikan filter untuk memperbarui wawasan seluruh grafik secara instan.")
st.sidebar.divider()

all_platforms = ["Semua Platform"] + sorted(df_raw['platform_type'].unique().tolist())
selected_platform = st.sidebar.selectbox("Pilih Platform Diskusi:", all_platforms)

valid_dates = df_raw['date_clean'].dropna()
if not valid_dates.empty:
    min_date = valid_dates.min()
    max_date = valid_dates.max()
    selected_dates = st.sidebar.date_input("Rentang Waktu Ulasan:", [min_date, max_date], min_value=min_date, max_value=max_date)
else:
    selected_dates = ()

df_filtered = df_raw.copy()
if selected_platform != "Semua Platform":
    df_filtered = df_filtered[df_filtered['platform_type'] == selected_platform]

# PERBAIKAN: Jaga agar data Quora (NaT) tidak hilang saat menggunakan filter rentang tanggal
if len(selected_dates) == 2:
    mask = df_filtered['date_clean'].isna() | ((df_filtered['date_clean'] >= selected_dates[0]) & (df_filtered['date_clean'] <= selected_dates[1]))
    df_filtered = df_filtered[mask]

st.sidebar.divider()
st.sidebar.metric("Volume Dokumen Aktif", f"{len(df_filtered):,}")
st.sidebar.caption("Terkoneksi dengan Node MongoDB Lokal")


# 5. STRUKTUR UTAMA DAN SISTEM NAVIGASI (TABBAR)
st.title("📊 Portal Analisis Sentimen & Wawasan E-Wallet")
st.markdown("Eksplorasi opini publik, sentimen tren harian, hingga karakteristik kebahasaan secara terintegrasi.")
st.divider()

tab_trend, tab_context, tab_engagement, tab_explorer = st.tabs([
    "📈 Tren Sentimen & Platform", 
    "📝 Analisis Konteks (N-Gram)", 
    "🔥 Korelasi Interaksi",
    "📂 Tabel Eksplorasi"
])

# ── TAB 1: TREN SENTIMEN & PLATFORM ──────────────────────────────────────
with tab_trend:
    st.subheader("Distribusi Sentimen dan Reputasi Berbasis Waktu")
    
    valid_rating_df = df_filtered[df_filtered['rating'] > 0]
    
    if not valid_rating_df.empty:
        avg_rating_val = valid_rating_df['rating'].mean()
        avg_rating_text = f"{avg_rating_val:.2f} / 5.0"
    else:
        avg_rating_text = "N/A (Media Sosial)"
        
    total_eng = df_filtered['engagement'].sum()
    neg_count = len(df_filtered[df_filtered['label_sentimen'] == 'Negatif'])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Rata-rata Rating (Kepuasan)", avg_rating_text)
    m2.metric("Total Interaksi Publik", f"{total_eng:,.0f} Likes/Votes")
    m3.metric("Ulasan Sentimen Negatif Store", f"{neg_count:,}")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Segmentasi Sumber Opini Platform</p>", unsafe_allow_html=True)
        
        fitur_fokus = st.checkbox("Fokus Analisis Media Sosial (Sembunyikan PlayStore/AppStore)", value=False)
        df_pie_source = df_filtered.copy()
        if fitur_fokus:
            df_pie_source = df_pie_source[df_pie_source['platform_type'] != 'PlayStore/AppStore']
            
        platform_summary = df_pie_source['platform_type'].value_counts().reset_index()
        platform_summary.columns = ['Platform', 'Total']
        
        if not platform_summary.empty:
            fig_pie = px.pie(platform_summary, values='Total', names='Platform', hole=0.45,
                            color_discrete_sequence=px.colors.sequential.Teal)
            fig_pie.update_traces(textinfo='percent+value+label', textposition='auto')
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Tidak ada data platform yang tersedia.")

    with col2:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Fluktuasi Rata-rata Rating Harian (Khusus PlayStore)</p>", unsafe_allow_html=True)
        valid_trend_df = valid_rating_df.dropna(subset=['date_clean'])
        if not valid_trend_df.empty:
            trend_rating = valid_trend_df.groupby('date_clean')['rating'].mean().reset_index()
            fig_line = px.line(trend_rating, x='date_clean', y='rating', markers=True,
                            color_discrete_sequence=['#f59e0b'])
            fig_line.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                                xaxis_title="Tanggal", yaxis_title="Rata-rata Rating")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Tidak ada data rating numerik dengan tanggal valid untuk tren harian.")

# ── TAB 2: ANALISIS KONTEKS (N-GRAM) & TEKS ───────────────────────────
with tab_context:
    st.subheader("Struktur Kebahasaan & Ekstraksi Topik Utama")
    
    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Konteks Frasa Dominan (Top 15 Bigram)</p>", unsafe_allow_html=True)
        
        corpus = df_filtered['clean_content_str'].tolist()
        if len(corpus) > 5:
            vectorizer = CountVectorizer(ngram_range=(2, 2), max_features=15)
            X = vectorizer.fit_transform(corpus)
            bigram_sum = X.sum(axis=0).A1
            bigram_df = pd.DataFrame({'Frasa Konteks': vectorizer.get_feature_names_out(), 'Frekuensi': bigram_sum})
            bigram_df = bigram_df.sort_values(by='Frekuensi', ascending=True)
            
            fig_bigram = px.bar(bigram_df, x='Frekuensi', y='Frasa Konteks', orientation='h',
                                color='Frekuensi', color_continuous_scale='Blues')
            fig_bigram.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
            st.plotly_chart(fig_bigram, use_container_width=True)
        else:
            st.info("Kuantitas teks tidak mencukupi untuk analisis Bigram.")

    with r1_col2:
        st.markdown("<p style='font-weight: 600; font-size: 1.1rem;'>Awan Kata (Word Cloud) dari Dokumen Aktif</p>", unsafe_allow_html=True)
        
        combined_text = " ".join(df_filtered['clean_content_str'].tolist())
        if combined_text.strip():
            fig_wc, ax_wc = plt.subplots(figsize=(6, 4))
            wc_generator = WordCloud(width=800, height=500, 
                                    background_color='rgba(255, 255, 255, 0)', 
                                    mode="RGBA",
                                    colormap='viridis', max_words=100, 
                                    collocations=False).generate(combined_text)
            
            ax_wc.imshow(wc_generator, interpolation='bilinear')
            ax_wc.axis('off')
            fig_wc.patch.set_alpha(0.0)
            ax_wc.patch.set_alpha(0.0)
            st.pyplot(fig_wc, clear_figure=True, transparent=True)
        else:
            st.info("Tidak ada data teks bersih yang tersedia untuk membangun Word Cloud.")

# ── TAB 3: KORELASI INTERAKSI (ENGAGEMENT) ───────────────────────────
with tab_engagement:
    st.subheader("Dampak Panjang Teks terhadap Daya Tarik Audiens")
    st.markdown("Menganalisis perilaku audiens: Apakah opini yang detail (jumlah kata banyak) memicu reaksi interaksi yang tinggi?")
    
    sample_limit = min(1500, len(df_filtered))
    if sample_limit > 0:
        df_scatter = df_filtered.sample(sample_limit, random_state=42)
        fig_scatter = px.scatter(df_scatter, x="word_count", y="engagement", color="rating",
                                size_max=15, opacity=0.7,
                                title="Sebaran Jumlah Kata vs Total Engagement",
                                color_continuous_scale='RdYlGn')
        fig_scatter.update_layout(margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                                xaxis_title="Panjang Ulasan (Jumlah Kata)", yaxis_title="Skor Interaksi (Likes/Votes)",
                                coloraxis_colorbar=dict(title="Rating"))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Data tidak mencukupi untuk analisis korelasi.")

# ── TAB 4: PENJELAJAH DOKUMEN BERSIH ──────────────────────────────────────
with tab_explorer:
    st.subheader("Eksplorasi Data Tabular Hasil Preprocessing")
    st.markdown("Berikut adalah 500 baris sampel data bersih yang siap dieksplorasi:")
    
    visible_columns = ['platform_type', 'app_name', 'created_at', 'rating', 'engagement', 'raw_text', 'clean_content_str']
    st.dataframe(df_filtered[visible_columns].head(500), use_container_width=True, height=500)