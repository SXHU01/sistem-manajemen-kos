# KosManage — Sistem Pengelola Dua Properti Kos

Source aplikasi admin KosManage sesuai **PRD v1.1** (Python · Streamlit · SQLAlchemy · SQLite · MVC · zona waktu Asia/Jakarta) dan **Design System v2.4** (konten primer dulu: maksimal 3 kartu · 2 tabel · 6 kolom · 1 tombol primer per halaman; banner dihapus → toast + lonceng; detail per baris via dialog).

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Login default: **admin / kosmanage123** — ganti lewat environment variable sebelum dipakai serius:

```bash
export KOSMANAGE_ADMIN_USER=admin
export KOSMANAGE_ADMIN_PASS="password-minimal-8-karakter"
```

Database SQLite dibuat otomatis di `data/kosmanage.db` dan diisi data contoh yang konsisten dengan Design System v2.4 Bagian 6: 24 kamar (terisi 20, kosong 102/204/210, Perbaikan 108), menunggak Citra Rp 600.000 + Gita Rp 1.200.000 = Rp 1.800.000, pendapatan bulan berjalan Rp 12.450.000 dari 21 pembayaran valid, 42 tagihan dengan 3 perlu perhatian. Tanggal ditautkan ke hari ini (Asia/Jakarta) sehingga cerita demo selalu relevan. Untuk mulai kosong, hapus `data/kosmanage.db` lalu jalankan ulang (tanpa data contoh, seed properti & admin tetap dibuat).

## Struktur (MVC sesuai PRD Bagian 9)

```
app.py                  # view entry: login gate, sidebar, navigasi (FR-01/02)
.streamlit/config.toml  # token tema (espresso/cream, mode terang)
utils/
  theme.py              # token Design System v2.4 -> CSS (spasi 24/48, nowrap, pills)
  format.py             # rupiah/tanggal/periode + zona waktu Asia/Jakarta
  ui.py                 # pola halaman: judul + meta + tabel HTML + pagination
  notify.py             # toast sesaat + lonceng notifikasi (angka hitung)
database/
  models.py             # model SQLAlchemy + hitungan status/sisa (BR-18, FR-06)
  db.py                 # init, backup harian (FR-18), seed fixture + verifikasi angka
  restore.py            # satu perintah memulihkan dari backup
controllers/            # aturan bisnis, murni Python (dapat diunit-test)
  auth.py               # bcrypt, kunci 5 menit setelah 5 gagal, idle 60 menit
  kamar.py penghuni.py sewa.py tagihan.py pembayaran.py laporan.py
pages/                  # 9 halaman sesuai resep Design System v2.4
tests/test_rules.py     # unit test BR-01..BR-21 + kontrak fixture
```

## Uji

```bash
python -m tests.test_rules
```

## Backup & pemulihan (FR-18)

Backup harian otomatis ke `backups/` saat aplikasi start (retensi 30 hari). Pulihkan:

```bash
python -m database.restore backups/kosmanage-2026-11-17.db
```

## Catatan implementasi

- **Uang** disimpan sebagai integer rupiah tanpa desimal (integritas data PRD).
- **Tidak ada hapus permanen** pada penyewaan/tagihan/pembayaran; koreksi = pembatalan beralasan (BR-19). Kamar/penghuni hanya bisa dihapus jika belum punya penyewaan.
- **Status kamar** dihitung dari penyewaan aktif, kecuali ditandai Perbaikan (FR-06, BR-21).
- **Prorata** bulan pertama/terakhir harian, dibulatkan ke rupiah (BR-14); jatuh tempo per sewa tanggal 1–28 (BR-09).
- **Pembayaran berlebih ditolak** dengan pesan menyebut sisa tagihan (BR-16); klik ganda tervalidasi ulang karena sisa berkurang sebelum commit.
- **CSV** diekspor dengan format rupiah/tanggal yang sama seperti tampilan (FR-17).
- **Grafik tren** hanya di halaman Laporan dengan dua warna properti tetap (espresso/kuning tua); jika plotly tidak tersedia, dipakai grafik CSS cadangan dengan palet yang sama.
- Angka pada meta di bawah judul halaman selalu dihitung dari database, bukan teks tetap.
