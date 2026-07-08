# Nusantara Weather Insight

Pipeline ETL (Extract, Transform, Load) dan dashboard cuaca untuk 38 provinsi di Indonesia, menggunakan [Open-Meteo API](https://open-meteo.com/) sebagai sumber data dan PostgreSQL (Neon, cloud) sebagai data warehouse.

Awalnya dibuat sebagai bagian dari Bootcamp Data Analyst (Day 25 - ETL), lalu dikembangkan menjadi pipeline harian otomatis + dashboard interaktif.

## Komponen

| File/Folder | Keterangan |
|---|---|
| `etl_process.ipynb` | Notebook eksplorasi ETL — extract, transform, load, delta load |
| `etl_daily.py` | Script ETL harian untuk 38 provinsi, dijalankan otomatis via GitHub Actions atau Task Scheduler |
| `dashboard.py` | Dashboard Streamlit untuk visualisasi data cuaca (tren per jam, kategori hujan, dsb) |
| `.github/workflows/etl.yml` | GitHub Actions — menjalankan `etl_daily.py` setiap hari jam 06:00 WIB |
| `.devcontainer/` | Konfigurasi Dev Container untuk development di VS Code/Codespaces |
| `requirements.txt` | Dependency Python untuk dashboard & ETL |

## Alur Proses

1. **Extract** — mengambil data forecast cuaca per jam (hourly) dan per hari (daily) dari Open-Meteo API untuk 38 ibu kota provinsi.
2. **Transform** — standarisasi tipe data, mapping kode cuaca ke deskripsi, kategorisasi suhu/curah hujan, penghapusan duplikat, penanganan missing value.
3. **Load** — disimpan ke PostgreSQL dengan dua lapis schema:
   - `staging` — data mentah hasil extract (`stg_weather_hourly`, `stg_weather_daily`)
   - `warehouse` — data bersih hasil transform (`fact_weather_hourly`, `fact_weather_daily`)
4. **Delta Load** (notebook) — pada run berikutnya hanya menambahkan data baru berdasarkan timestamp terakhir di warehouse.
5. **Automasi** — `etl_daily.py` dijadwalkan lewat GitHub Actions (`cron: 0 23 * * *` UTC = 06:00 WIB) agar warehouse selalu ter-update tanpa campur tangan manual.
6. **Visualisasi** — `dashboard.py` membaca dari warehouse dan menampilkannya sebagai dashboard interaktif (Streamlit).

## Kredensial Database

Kredensial **tidak pernah** ditulis langsung di kode. Setiap komponen membaca kredensial dengan cara berbeda sesuai konteksnya:

- **`etl_process.ipynb`** — dibaca dari environment variable `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE`. Set dulu sebelum menjalankan notebook:
  ```bash
  export PGPASSWORD=xxxx   # Mac/Linux
  set PGPASSWORD=xxxx      # Windows cmd
  ```
  Referensi lengkap ada di `.env.example`.
- **`etl_daily.py`** — pakai environment variable yang sama jika ada (dipakai GitHub Actions lewat `secrets.*`); kalau tidak ada, fallback ke `etl_config.py` lokal (tidak di-commit, buat sendiri dengan isi `USER`, `PASSWORD`, `HOST`, `PORT`, `DATABASE`).
- **`dashboard.py`** — pakai `st.secrets["postgres"]` (Streamlit secrets). Untuk lokal, salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml` dan isi kredensialmu. Untuk deploy di Streamlit Cloud, isi lewat menu *Secrets* di dashboard Streamlit Cloud.

Semua file kredensial asli (`.env`, `etl_config.py`, `.streamlit/secrets.toml`) sudah masuk `.gitignore` — jangan pernah di-commit.

## Setup Lokal

1. Install dependency:
   ```bash
   pip install -r requirements.txt
   ```
2. Siapkan kredensial sesuai komponen yang mau dijalankan (lihat bagian di atas).
3. Jalankan salah satu:
   ```bash
   # Notebook eksplorasi
   jupyter notebook etl_process.ipynb

   # ETL harian manual
   python etl_daily.py

   # Dashboard
   streamlit run dashboard.py
   ```

## Catatan

- Data mencakup 38 ibu kota provinsi se-Indonesia (lihat dict `CITIES` di `etl_daily.py`).
- Log proses ETL harian ditulis ke `etl_log.txt` (tidak di-commit) dan diunggah sebagai artifact di GitHub Actions.
- Notebook `etl_process.ipynb` hanya memproses satu kota (default: Jakarta) untuk keperluan eksplorasi; pipeline produksi multi-kota ada di `etl_daily.py`.
