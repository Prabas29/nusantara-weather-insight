import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine

# ============================================================
# Konfigurasi halaman
# ============================================================
st.set_page_config(
    page_title="Nusantara Weather Insight",
    page_icon="🌤️",
    layout="wide"
)

# Konfigurasi database — dibaca dari st.secrets saat deploy (Streamlit Cloud),
# fallback ke nilai lokal saat dijalankan di komputer sendiri (tidak ada secrets.toml)
try:
    DB = st.secrets["postgres"]
except (FileNotFoundError, KeyError):
    DB = {}

USER     = DB.get("user", "postgres")
PASSWORD = DB.get("password", "")
HOST     = DB.get("host", "localhost")
PORT     = DB.get("port", "5432")
DATABASE = DB.get("database", "weather_dw")

if not PASSWORD:
    st.error(
        "Password database belum diset. Buat file `.streamlit/secrets.toml` "
        "(lokal) berisi kredensial Postgres-mu, lihat `.streamlit/secrets.toml.example`."
    )
    st.stop()

# ============================================================
# Palet warna (konsisten di semua chart)
# ============================================================
# Kategorikal — urutan tetap, tiap kota selalu dapat warna yang sama
CATEGORICAL = ['#2a78d6', '#1baf7a', '#eda100', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834', '#008300']

# Status — dipakai untuk kategori hujan (semakin deras, semakin "kritis")
RAIN_COLOR = {
    'Tidak Hujan':  '#0ca30c',   # good
    'Hujan Ringan': '#fab219',   # warning
    'Hujan Sedang': '#ec835a',   # serious
    'Hujan Lebat':  '#d03b3b',   # critical
}
RAIN_ORDER = ['Tidak Hujan', 'Hujan Ringan', 'Hujan Sedang', 'Hujan Lebat']

# ============================================================
# CSS ringan untuk tampilan stat card
# ============================================================
st.markdown("""
<style>
.stat-card {
    background: rgba(127,127,127,0.08);
    border: 1px solid rgba(127,127,127,0.18);
    border-radius: 10px;
    padding: 16px 18px;
    height: 100%;
}
.stat-label { font-size: 0.82rem; opacity: 0.7; margin-bottom: 4px; }
.stat-value { font-size: 1.7rem; font-weight: 600; line-height: 1.2; }
.stat-delta { font-size: 0.8rem; margin-top: 4px; opacity: 0.85; }
</style>
""", unsafe_allow_html=True)


def stat_card(label, value, delta=None, delta_good_if_up=True):
    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta >= 0 else "▼"
        is_good = (delta >= 0) == delta_good_if_up
        color = "#0ca30c" if is_good else "#d03b3b"
        delta_html = f'<div class="stat-delta" style="color:{color}">{arrow} {abs(delta):.1f} dari kemarin</div>'
    st.markdown(
        f'<div class="stat-card"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>{delta_html}</div>',
        unsafe_allow_html=True
    )


@st.cache_data(ttl=3600)
def get_data():
    db_url = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    engine = create_engine(db_url)

    df_hourly = pd.read_sql("SELECT * FROM warehouse.fact_weather_hourly", engine)
    df_daily  = pd.read_sql("SELECT * FROM warehouse.fact_weather_daily",  engine)

    engine.dispose()
    return df_hourly, df_daily


# ============================================================
# Header
# ============================================================
st.title("🌤️ Nusantara Weather Insight")
st.caption("Pantauan cuaca 38 provinsi di Indonesia · Sumber data: Open-Meteo API")

# Load data
df_hourly, df_daily = get_data()

df_hourly['time'] = pd.to_datetime(df_hourly['time'])
df_daily['time']  = pd.to_datetime(df_daily['time'])

daftar_kota = sorted(df_daily['city'].unique())

kota_terpilih = st.sidebar.selectbox("🏙️ Pilih Kota/Provinsi", daftar_kota)
st.sidebar.caption("Filter ini berlaku untuk tab **Ringkasan Kota**.")

df_hourly_kota = df_hourly[df_hourly['city'] == kota_terpilih].sort_values('time').reset_index(drop=True)
df_daily_kota  = df_daily[df_daily['city'] == kota_terpilih].sort_values('time').reset_index(drop=True)

tab_ringkasan, tab_banding, tab_data = st.tabs([
    "📍 Ringkasan Kota", "🌧️ Perbandingan Antar Kota", "📋 Data Lengkap"
])

# ============================================================
# TAB 1 — Ringkasan per kota
# ============================================================
with tab_ringkasan:
    st.subheader(f"Ringkasan Hari Ini — {kota_terpilih}")

    suhu_sekarang = df_hourly_kota['temperature_2m'].iloc[-1]
    suhu_kemarin  = df_hourly_kota['temperature_2m'].iloc[-25]
    kelembaban    = df_hourly_kota['relative_humidity_2m'].iloc[-1]
    angin         = df_hourly_kota['wind_speed_10m'].iloc[-1]
    hujan_hari    = df_daily_kota['precipitation_sum'].iloc[0]
    kategori_hari = df_daily_kota['rain_category'].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_card("🌡️ Suhu Sekarang", f"{suhu_sekarang:.1f}°C", delta=suhu_sekarang - suhu_kemarin)
    with col2:
        stat_card("💧 Kelembaban", f"{kelembaban:.0f}%")
    with col3:
        stat_card(
            "🌧️ Curah Hujan Hari Ini",
            f"{hujan_hari:.1f} mm",
        )
        st.markdown(
            f'<span style="background:{RAIN_COLOR.get(kategori_hari, "#888")}22;'
            f'color:{RAIN_COLOR.get(kategori_hari, "#888")};padding:2px 8px;border-radius:6px;'
            f'font-size:0.78rem;font-weight:600;">{kategori_hari}</span>',
            unsafe_allow_html=True
        )
    with col4:
        stat_card("💨 Kecepatan Angin", f"{angin:.1f} km/h")

    st.divider()
    st.subheader("Tren Suhu 7 Hari")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=df_daily_kota['time'], y=df_daily_kota['temperature_2m_max'],
            name='Suhu Maks', line=dict(color='#e34948', width=2), mode='lines+markers',
            marker=dict(size=8, line=dict(width=2, color='#fcfcfb'))
        ))
        fig_temp.add_trace(go.Scatter(
            x=df_daily_kota['time'], y=df_daily_kota['temperature_2m_min'],
            name='Suhu Min', line=dict(color='#2a78d6', width=2), mode='lines+markers',
            marker=dict(size=8, line=dict(width=2, color='#fcfcfb')),
            fill='tonexty', fillcolor='rgba(42,120,214,0.08)'
        ))
        fig_temp.update_layout(
            title='Suhu Maks & Min Harian (°C)',
            xaxis_title=None, yaxis_title='°C',
            height=380, margin=dict(t=90, b=10),
            legend=dict(orientation='h', yanchor='top', y=1.12, x=0)
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with col_right:
        weather_count = (
            df_hourly_kota['weather_description'].value_counts().reset_index()
        )
        weather_count.columns = ['Kondisi', 'Jumlah']

        # batasi maks 6 kategori, sisanya digabung jadi "Lainnya" biar donut tidak ramai
        if len(weather_count) > 6:
            top = weather_count.iloc[:5]
            other_total = weather_count.iloc[5:]['Jumlah'].sum()
            weather_count = pd.concat([
                top, pd.DataFrame([{'Kondisi': 'Lainnya', 'Jumlah': other_total}])
            ], ignore_index=True)

        fig_donut = px.pie(
            weather_count, values='Jumlah', names='Kondisi',
            title='Distribusi Kondisi Cuaca', hole=0.55,
            color_discrete_sequence=CATEGORICAL
        )
        fig_donut.update_traces(textposition='outside', textinfo='percent+label', showlegend=False)
        fig_donut.update_layout(height=360, margin=dict(t=50, b=10))
        st.plotly_chart(fig_donut, use_container_width=True)

    st.divider()
    st.subheader("Detail Cuaca")

    col_a, col_b = st.columns(2)

    with col_a:
        fig_rain = px.bar(
            df_daily_kota, x='time', y='precipitation_sum',
            title='Curah Hujan Harian (mm)',
            color='precipitation_sum', color_continuous_scale='Blues',
            labels={'time': 'Tanggal', 'precipitation_sum': 'Curah Hujan (mm)'}
        )
        fig_rain.update_traces(marker_line_width=0)
        fig_rain.update_layout(height=320, coloraxis_showscale=False, margin=dict(t=50, b=10))
        st.plotly_chart(fig_rain, use_container_width=True)

    with col_b:
        hari_ini = df_hourly_kota[df_hourly_kota['time'].dt.date == df_hourly_kota['time'].dt.date.iloc[0]]
        fig_hourly = px.line(
            hari_ini, x='time', y='temperature_2m',
            title='Suhu Per Jam Hari Ini (°C)',
            labels={'time': 'Jam', 'temperature_2m': 'Suhu (°C)'},
            color_discrete_sequence=['#e34948']
        )
        fig_hourly.update_traces(line=dict(width=2))
        fig_hourly.update_layout(height=320, margin=dict(t=50, b=10))
        st.plotly_chart(fig_hourly, use_container_width=True)

# ============================================================
# TAB 2 — Perbandingan antar kota
# ============================================================
with tab_banding:
    st.subheader("Perbandingan Curah Hujan Antar Kota")
    st.caption("Pilih kategori untuk melihat kota mana saja yang mengalaminya.")

    kategori_terpilih = st.multiselect(
        "Filter Kategori Hujan", options=RAIN_ORDER, default=RAIN_ORDER
    )
    df_kota_filtered = df_daily[df_daily['rain_category'].isin(kategori_terpilih)]

    # Ranking total curah hujan — dipakai untuk mengurutkan kota di heatmap
    rekap_kota = (
        df_kota_filtered.groupby('city')['precipitation_sum']
        .sum().reset_index().sort_values('precipitation_sum', ascending=False)
    )
    urutan_kota = rekap_kota['city'].tolist()

    st.markdown("**Curah Hujan per Kota per Tanggal (mm)**")
    st.caption("Kota diurutkan dari yang paling basah ke paling kering. Warna gelap = curah hujan lebih tinggi.")

    heatmap_data = df_kota_filtered.pivot(index='city', columns='time', values='precipitation_sum')
    heatmap_data = heatmap_data.reindex(urutan_kota)

    fig_heat = px.imshow(
        heatmap_data,
        color_continuous_scale='Blues',
        aspect='auto',
        labels=dict(x='Tanggal', y='Kota', color='Curah Hujan (mm)'),
        x=[d.strftime('%d %b') for d in heatmap_data.columns]
    )
    fig_heat.update_layout(
        height=max(420, len(urutan_kota) * 22),
        margin=dict(t=20, b=10),
        yaxis=dict(tickfont=dict(size=11))
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("**Total Curah Hujan per Kota (7 Hari)**")
    rekap_kota.columns = ['Kota', 'Total Curah Hujan (mm)']
    fig_rank = px.bar(
        rekap_kota, x='Total Curah Hujan (mm)', y='Kota', orientation='h',
        color='Total Curah Hujan (mm)', color_continuous_scale='Blues'
    )
    fig_rank.update_layout(
        height=max(420, len(urutan_kota) * 20),
        showlegend=False, coloraxis_showscale=False,
        margin=dict(t=10, b=10),
        yaxis=dict(categoryorder='total ascending', tickfont=dict(size=11))
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    st.markdown(
        f"**Kota & tanggal untuk kategori: "
        f"{', '.join(kategori_terpilih) if kategori_terpilih else '-'}**"
    )

    df_detail = df_kota_filtered[[
        'city', 'time', 'precipitation_sum', 'rain_category'
    ]].sort_values(['rain_category', 'city', 'time']).copy()
    df_detail.columns = ['Kota', 'Tanggal', 'Curah Hujan (mm)', 'Kategori Hujan']
    df_detail['Tanggal'] = df_detail['Tanggal'].dt.strftime('%d %b %Y')

    st.dataframe(
        df_detail, use_container_width=True, hide_index=True,
        column_config={
            "Kategori Hujan": st.column_config.TextColumn("Kategori Hujan"),
        }
    )

# ============================================================
# TAB 3 — Data lengkap
# ============================================================
with tab_data:
    st.subheader(f"Data Forecast Harian — {kota_terpilih}")

    df_display = df_daily_kota[[
        'time', 'temperature_2m_max', 'temperature_2m_min',
        'precipitation_sum', 'wind_speed_10m_max', 'rain_category'
    ]].copy()
    df_display.columns = [
        'Tanggal', 'Suhu Maks (°C)', 'Suhu Min (°C)',
        'Curah Hujan (mm)', 'Angin Maks (km/h)', 'Kategori Hujan'
    ]
    df_display['Tanggal'] = df_display['Tanggal'].dt.strftime('%d %b %Y')
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Semua Kota — Data Harian")
    df_all = df_daily[[
        'city', 'time', 'temperature_2m_max', 'temperature_2m_min',
        'precipitation_sum', 'wind_speed_10m_max', 'rain_category'
    ]].sort_values(['city', 'time']).copy()
    df_all.columns = [
        'Kota', 'Tanggal', 'Suhu Maks (°C)', 'Suhu Min (°C)',
        'Curah Hujan (mm)', 'Angin Maks (km/h)', 'Kategori Hujan'
    ]
    df_all['Tanggal'] = df_all['Tanggal'].dt.strftime('%d %b %Y')
    st.dataframe(df_all, use_container_width=True, hide_index=True)

st.divider()
st.caption("Dashboard dibuat dengan Streamlit · Data: Open-Meteo API")
