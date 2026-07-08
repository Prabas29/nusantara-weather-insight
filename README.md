# ETL Weather

Pipeline ETL (Extract, Transform, Load) sederhana untuk data cuaca kota Jakarta, menggunakan [Open-Meteo API](https://open-meteo.com/) sebagai sumber data dan PostgreSQL sebagai data warehouse.

Dibuat sebagai bagian dari Bootcamp Data Analyst (Day 25 - ETL).

## Alur Proses

1. **Extract** — mengambil data forecast cuaca per jam (hourly) dan per hari (daily) dari Open-Meteo API.
2. **Transform** — membersihkan data: standarisasi tipe data, mapping kode cuaca ke deskripsi, kategorisasi suhu/curah hujan, penghapusan duplikat, penanganan missing value.
3. **Load** — menyimpan data ke PostgreSQL dengan dua lapis schema:
   - `staging` — data mentah hasil extract (`stg_weather_hourly`, `stg_weather_daily`)
   - `warehouse` — data bersih hasil transform (`fact_weather_hourly`, `fact_weather_daily`)
4. **Delta Load** — pada run berikutnya, hanya menambahkan data baru (berdasarkan timestamp terakhir di warehouse) tanpa menimpa ulang seluruh tabel.

## Persyaratan

- Python 3.12+
- PostgreSQL yang sudah berjalan (default: `localhost:5432`)
- Database dengan nama sesuai `.env` (default: `weather_dw`)

## Setup

1. Clone/buka project ini, lalu install dependency (sudah otomatis dijalankan di notebook, atau install manual):
   ```bash
   pip install requests pandas sqlalchemy psycopg2-binary python-dotenv
   ```
2. Salin `.env.example` menjadi `.env`, lalu isi dengan kredensial database kamu:
   ```bash
   cp .env.example .env
   ```
   ```
   DB_USER=postgres
   DB_PASSWORD=<password_kamu>
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=weather_dw
   ```
   > `.env` tidak ikut ter-commit ke Git (lihat `.gitignore`) — jangan pernah menaruh kredensial asli langsung di notebook atau kode.
3. Jalankan `etl_process.ipynb` dari awal hingga akhir.

## Struktur File

| File | Keterangan |
|---|---|
| `etl_process.ipynb` | Notebook utama berisi seluruh proses extract, transform, load |
| `.env.example` | Template variabel environment untuk koneksi database |
| `.env` | Kredensial database asli (tidak di-commit) |
| `.gitignore` | Mengecualikan file sensitif/tidak relevan dari Git (`.env`, image, cache notebook, dll) |

## Catatan

- Lokasi default yang diambil: Jakarta (`-6.2088, 106.8456`), forecast 7 hari ke depan.
- Untuk kota/lokasi lain, ubah `latitude`/`longitude` pada cell yang membangun `url` request ke Open-Meteo API.
