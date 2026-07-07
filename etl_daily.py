"""
ETL harian: tarik data cuaca 38 provinsi dari Open-Meteo, load ke Neon (cloud Postgres).
Bisa dijalankan lewat Windows Task Scheduler (lokal) ATAU GitHub Actions (cloud, 24/7).
Kredensial dibaca dari environment variables (PGUSER dst) jika ada — dipakai GitHub Actions;
kalau tidak ada, fallback ke etl_config.py lokal (tidak di-commit ke git).
Semua proses & error dicatat ke etl_log.txt di folder yang sama.
"""
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
import pandas as pd
import requests


class _Cfg:
    pass


cfg = _Cfg()
if os.environ.get("PGPASSWORD"):
    cfg.USER = os.environ.get("PGUSER", "postgres")
    cfg.PASSWORD = os.environ["PGPASSWORD"]
    cfg.HOST = os.environ.get("PGHOST", "localhost")
    cfg.PORT = os.environ.get("PGPORT", "5432")
    cfg.DATABASE = os.environ.get("PGDATABASE", "weather_dw")
else:
    import etl_config as _local_cfg
    cfg.USER = _local_cfg.USER
    cfg.PASSWORD = _local_cfg.PASSWORD
    cfg.HOST = _local_cfg.HOST
    cfg.PORT = _local_cfg.PORT
    cfg.DATABASE = _local_cfg.DATABASE

LOG_FILE = Path(__file__).parent / "etl_log.txt"


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def db_url():
    return (
        f"postgresql+psycopg2://{cfg.USER}:{cfg.PASSWORD}"
        f"@{cfg.HOST}:{cfg.PORT}/{cfg.DATABASE}?sslmode=require"
    )


def load_data(df, table_name, schema, if_exists='replace'):
    engine = create_engine(db_url())
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.commit()
        df.to_sql(table_name, engine, schema=schema, if_exists=if_exists, index=False)
        log(f"Load ke {schema}.{table_name} berhasil! ({len(df)} baris)")
    finally:
        engine.dispose()


def extract_api(url, retries=3, backoff=5):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException,) as e:
            last_err = e
            log(f"  Percobaan {attempt}/{retries} gagal ({e}), retry dalam {backoff}s...")
            time.sleep(backoff)
    raise last_err


CITIES = {
    'Banda Aceh':      (5.5483, 95.3238),
    'Medan':           (3.5952, 98.6722),
    'Padang':          (-0.9471, 100.4172),
    'Pekanbaru':       (0.5071, 101.4478),
    'Tanjung Pinang':  (0.9186, 104.4562),
    'Jambi':           (-1.6101, 103.6131),
    'Palembang':       (-2.9761, 104.7754),
    'Pangkal Pinang':  (-2.1316, 106.1169),
    'Bengkulu':        (-3.7928, 102.2608),
    'Bandar Lampung':  (-5.4292, 105.2610),
    'Jakarta':         (-6.2088, 106.8456),
    'Bandung':         (-6.9175, 107.6191),
    'Semarang':        (-6.9932, 110.4203),
    'Yogyakarta':      (-7.7956, 110.3695),
    'Surabaya':        (-7.2575, 112.7521),
    'Serang':          (-6.1149, 106.1503),
    'Denpasar':        (-8.6705, 115.2126),
    'Mataram':         (-8.5833, 116.1167),
    'Kupang':          (-10.1772, 123.6070),
    'Pontianak':       (-0.0263, 109.3425),
    'Palangka Raya':   (-2.2096, 113.9213),
    'Banjarmasin':     (-3.3186, 114.5944),
    'Samarinda':       (-0.5022, 117.1536),
    'Tanjung Selor':   (2.8385, 117.3644),
    'Manado':          (1.4748, 124.8421),
    'Palu':            (-0.8917, 119.8707),
    'Makassar':        (-5.1477, 119.4327),
    'Kendari':         (-3.9985, 122.5129),
    'Gorontalo':       (0.5435, 123.0568),
    'Mamuju':          (-2.6784, 118.8879),
    'Ambon':           (-3.6954, 128.1814),
    'Sofifi':          (0.7387, 127.4744),
    'Jayapura':        (-2.5330, 140.7181),
    'Manokwari':       (-0.8615, 134.0620),
    'Sorong':          (-0.8763, 131.2558),
    'Nabire':          (-3.3667, 135.4833),
    'Wamena':          (-4.0847, 138.9440),
    'Merauke':         (-8.4700, 140.3300),
}

WEATHER_CODE_MAP = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Moderate drizzle',
    55: 'Dense drizzle', 61: 'Slight rain', 63: 'Moderate rain', 65: 'Heavy rain',
    80: 'Slight showers', 81: 'Moderate showers', 82: 'Violent showers', 95: 'Thunderstorm'
}


def run():
    log("=== ETL harian dimulai ===")

    all_hourly = []
    all_daily = []

    for i, (city, (lat, lon)) in enumerate(CITIES.items(), 1):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,weather_code"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,sunrise,sunset"
            "&timezone=Asia%2FJakarta"
            "&forecast_days=7"
        )
        data = extract_api(url)

        df_city = pd.DataFrame(data['hourly'])
        df_city['latitude'] = data['latitude']
        df_city['longitude'] = data['longitude']
        df_city['city'] = city
        all_hourly.append(df_city)

        df_daily_city = pd.DataFrame(data['daily'])
        df_daily_city['city'] = city
        all_daily.append(df_daily_city)

        log(f"[{i}/{len(CITIES)}] {city} - extracted")
        time.sleep(0.3)

    df = pd.concat(all_hourly, ignore_index=True)
    df_daily = pd.concat(all_daily, ignore_index=True)
    log(f"Extract selesai. Hourly: {len(df)} baris, Daily: {len(df_daily)} baris")

    df_clean = df.copy()
    df_clean['time'] = pd.to_datetime(df_clean['time'])
    df_clean['date'] = df_clean['time'].dt.date
    df_clean['hour'] = df_clean['time'].dt.hour
    df_clean['is_daytime'] = df_clean['hour'].between(6, 18).astype(int)
    df_clean['weather_description'] = df_clean['weather_code'].map(WEATHER_CODE_MAP).fillna('Unknown')
    df_clean['temp_category'] = pd.cut(
        df_clean['temperature_2m'], bins=[-999, 20, 28, 35, 999],
        labels=['Dingin', 'Nyaman', 'Hangat', 'Panas']
    )
    df_clean['precipitation'] = df_clean['precipitation'].fillna(0)
    df_clean['precipitation_probability'] = df_clean['precipitation_probability'].fillna(0)
    df_clean['wind_speed_10m'] = df_clean['wind_speed_10m'].fillna(df_clean['wind_speed_10m'].median())
    df_clean = df_clean.drop_duplicates(subset=['time', 'city'])
    df_clean['etl_loaded_at'] = pd.Timestamp.now()

    df_daily_clean = df_daily.copy()
    df_daily_clean['time'] = pd.to_datetime(df_daily_clean['time'])
    df_daily_clean['sunrise'] = pd.to_datetime(df_daily_clean['sunrise'])
    df_daily_clean['sunset'] = pd.to_datetime(df_daily_clean['sunset'])
    df_daily_clean['daylight_hours'] = (
        (df_daily_clean['sunset'] - df_daily_clean['sunrise']).dt.total_seconds() / 3600
    ).round(2)
    df_daily_clean['temp_range'] = (
        df_daily_clean['temperature_2m_max'] - df_daily_clean['temperature_2m_min']
    ).round(2)
    df_daily_clean['rain_category'] = pd.cut(
        df_daily_clean['precipitation_sum'], bins=[-1, 0, 5, 20, 999],
        labels=['Tidak Hujan', 'Hujan Ringan', 'Hujan Sedang', 'Hujan Lebat']
    )
    df_daily_clean['precipitation_sum'] = df_daily_clean['precipitation_sum'].fillna(0)
    df_daily_clean['etl_loaded_at'] = pd.Timestamp.now()

    log("Transform selesai. Mulai load ke Neon...")

    load_data(df, 'stg_weather_hourly', schema='staging', if_exists='replace')
    load_data(df_daily, 'stg_weather_daily', schema='staging', if_exists='replace')
    load_data(df_clean, 'fact_weather_hourly', schema='warehouse', if_exists='replace')
    load_data(df_daily_clean, 'fact_weather_daily', schema='warehouse', if_exists='replace')

    log("=== ETL harian selesai (sukses) ===")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        log("!!! ETL GAGAL !!!")
        log(traceback.format_exc())
        sys.exit(1)
