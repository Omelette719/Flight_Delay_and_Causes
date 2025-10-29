import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- Konfigurasi halaman ---
st.set_page_config(
    page_title="Flight Delay Analytics",
    page_icon="✈️",
    layout="wide"
)
px.defaults.template = "plotly_dark"

# ===============================================================
# KONTEXT STUDI KASUS
# ===============================================================
st.title("Flight Delay Analytics Dashboard")
st.markdown("""
Dashboard ini dibuat untuk menganalisis **penyebab keterlambatan penerbangan** 
berdasarkan berbagai faktor seperti maskapai, cuaca, keamanan, dan kondisi sistem nasional udara (NAS).
Melalui visualisasi data, kita dapat memahami **tren keterlambatan**, **maskapai paling efisien**, 
dan **komponen delay terbesar** — guna mendukung pengambilan keputusan yang lebih tepat di industri penerbangan.
""")

# ===============================================================
# MUAT DAN CLEANING DATA
# ===============================================================
st.subheader("Data Loading & Cleaning")

uploaded_file = st.file_uploader("Unggah dataset Flight_delay.csv", type=["csv"])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # --- Cek dan ubah tipe data ---
    # --- Cek dan ubah tipe data (pastikan format hari-bulan-tahun) ---
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
    numeric_cols = [
        'DepTime', 'ArrTime', 'CRSArrTime', 'ActualElapsedTime', 'CRSElapsedTime',
        'AirTime', 'ArrDelay', 'Distance', 'TaxiIn', 'TaxiOut',
        'CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Penanganan nilai kosong ---
    df.fillna({
        'CarrierDelay': 0,
        'WeatherDelay': 0,
        'NASDelay': 0,
        'SecurityDelay': 0,
        'LateAircraftDelay': 0,
        'ArrDelay': 0
    }, inplace=True)

    # --- Feature Engineering ---
    df['TotalDelayMinutes'] = (
        df['CarrierDelay'] + df['WeatherDelay'] + df['NASDelay'] + df['SecurityDelay'] + df['LateAircraftDelay']
    )
    df['OnTime'] = np.where(df['ArrDelay'] <= 15, 1, 0)
    df['Delay_per_100_miles'] = (df['ArrDelay'] / df['Distance']) * 100
    df['Month'] = df['Date'].dt.month

    # --- Anomali menggunakan IQR ---
    q1, q3 = df['ArrDelay'].quantile([0.25, 0.75])
    iqr = q3 - q1
    upper_limit = q3 + 1.5 * iqr
    anomalies = df[df['ArrDelay'] > upper_limit]

    # --- Tampilkan info dasar ---
    st.write("**Jumlah baris:**", df.shape[0])
    st.write("**Jumlah kolom:**", df.shape[1])
    st.dataframe(df.head())

    st.markdown("**Data sudah dibersihkan dan siap divisualisasikan.**")

    # ===============================================================
    # PERTANYAAN BISNIS / ANALITIS
    # ===============================================================
    st.subheader("Business Questions")
    st.markdown("""
    1. Maskapai mana yang memiliki **rata-rata keterlambatan tertinggi** dan apa penyebab utamanya?  
    2. Bagaimana **tren keterlambatan penerbangan** berdasarkan waktu (bulan/hari)?  
    3. Seberapa besar kontribusi **tipe delay (Carrier, Weather, NAS, Security, Late Aircraft)** terhadap total delay?
    """)

    # ===============================================================
    # SIDEBAR FILTER
    # ===============================================================
    st.sidebar.header("Filter Data")
    min_date, max_date = df['Date'].min(), df['Date'].max()
    date_range = st.sidebar.date_input("Rentang tanggal", [min_date, max_date])
    selected_carriers = st.sidebar.multiselect("Pilih Maskapai", sorted(df['Airline'].unique()))
    selected_origin = st.sidebar.multiselect("Bandara Asal", sorted(df['Origin'].unique()))
    selected_dest = st.sidebar.multiselect("Bandara Tujuan", sorted(df['Dest'].unique()))

    # Filter data
    filtered = df.copy()
    if len(date_range) == 2:
        filtered = filtered[(filtered['Date'] >= pd.to_datetime(date_range[0])) &
                            (filtered['Date'] <= pd.to_datetime(date_range[1]))]
    if selected_carriers:
        filtered = filtered[filtered['Airline'].isin(selected_carriers)]
    if selected_origin:
        filtered = filtered[filtered['Origin'].isin(selected_origin)]
    if selected_dest:
        filtered = filtered[filtered['Dest'].isin(selected_dest)]

    # ===============================================================
    # KPI SECTION (Metrik Baru)
    # ===============================================================
    st.subheader("Key Performance Indicators (KPI)")

    avg_delay = filtered['ArrDelay'].mean()
    pct_ontime = filtered['OnTime'].mean() * 100
    avg_distance = filtered['Distance'].mean()
    total_flights = filtered.shape[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Flights", f"{total_flights:,}")
    c2.metric("Rata-rata Delay (menit)", f"{avg_delay:.2f}")
    c3.metric("% Tepat Waktu", f"{pct_ontime:.2f}%")
    c4.metric("Rata-rata Jarak (mil)", f"{avg_distance:.0f}")

    # ===============================================================
    # 6️VISUALISASI UTAMA
    # ===============================================================

    # --- Bar Chart: Delay per Airline ---
    st.subheader("Rata-rata Delay per Maskapai")
    avg_delay_airline = (
        filtered.groupby('Airline')['ArrDelay'].mean().reset_index().sort_values(by='ArrDelay', ascending=False)
    )
    fig_bar = px.bar(
        avg_delay_airline,
        x='Airline', y='ArrDelay',
        color='ArrDelay',
        color_continuous_scale='Reds',
        title="Rata-rata Arrival Delay per Maskapai"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Line Chart: Trend Delay per Bulan ---
    st.subheader("Tren Keterlambatan per Bulan")
    trend = filtered.groupby('Month')['ArrDelay'].mean().reset_index()
    fig_line = px.line(trend, x='Month', y='ArrDelay', markers=True, title="Rata-rata Delay Bulanan")
    st.plotly_chart(fig_line, use_container_width=True)

    # --- Pie Chart: Proporsi Jenis Delay ---
    st.subheader("Komposisi Jenis Delay")
    delay_cols = ['CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay']
    delay_sum = filtered[delay_cols].sum().reset_index()
    delay_sum.columns = ['DelayType', 'TotalMinutes']
    fig_pie = px.pie(delay_sum, names='DelayType', values='TotalMinutes', title="Proporsi Delay Berdasarkan Penyebab")
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- Heatmap: Rata-rata Delay per Origin-Destination ---
    st.subheader("Heatmap Rata-rata Delay (Origin vs Destination)")
    heat = filtered.groupby(['Origin', 'Dest'])['ArrDelay'].mean().reset_index()
    fig_heat = px.density_heatmap(
        heat, x='Origin', y='Dest', z='ArrDelay', color_continuous_scale='Viridis',
        title="Rata-rata Delay berdasarkan Rute"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # ===============================================================
    # 7️ANOMALI DETEKSI
    # ===============================================================
    st.subheader("Deteksi Anomali (Delay Ekstrem)")
    st.write(f"Jumlah anomali ditemukan: **{anomalies.shape[0]} penerbangan**")
    st.dataframe(anomalies[['Date', 'Airline', 'Origin', 'Dest', 'ArrDelay']].head(10))

    # ===============================================================
    # 8️ACTIONABLE INSIGHTS
    # ===============================================================
    st.subheader("Actionable Insights & Recommendations")
    st.markdown("""
    - Maskapai dengan rata-rata delay tertinggi perlu **evaluasi operasional dan perawatan pesawat.**
    - Bulan tertentu menunjukkan tren delay tinggi, dapat dijadikan fokus **peningkatan jadwal dan kapasitas.**
    - Proporsi terbesar berasal dari *CarrierDelay* dan *LateAircraftDelay*, artinya **optimalisasi rotasi pesawat** akan berdampak besar.
    """)

    # ===============================================================
    # 9️DOWNLOAD DATA TERFILTER
    # ===============================================================
    st.download_button(
        "⬇Unduh Data Terfilter (CSV)",
        data=filtered.to_csv(index=False).encode('utf-8'),
        file_name='filtered_flight_delay.csv',
        mime='text/csv'
    )

else:
    st.warning("Silakan unggah file `Flight_delay.csv` terlebih dahulu.")


