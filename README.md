# KosManage Sistem Pengelola Dua Properti Kos

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

## Screenshot Aplikasi

### Dashboard

![Dashboard KosManage](docs/screenshots/dashboard.png)

## Class Diagram

Diagram berikut menggambarkan model data SQLAlchemy pada `database/models.py` beserta modul controller yang menjalankan aturan bisnis. Kotak controller diberi stereotipe `<<module>>` karena implementasinya berupa modul fungsi, bukan class Python.

```mermaid
classDiagram
    direction TB

    class Properti {
        +int id
        +str nama
        +str alamat
        +str warna
    }

    class Kamar {
        +int id
        +int properti_id
        +str nomor
        +str tipe
        +int harga_sewa
        +bool perbaikan
    }

    class Penghuni {
        +int id
        +str nama
        +str telepon
        +str nomor_identitas
        +str catatan
    }

    class Penyewaan {
        +int id
        +int kamar_id
        +int penghuni_id
        +date mulai
        +date akhir_rencana
        +int harga_sewa_bulan
        +int jatuh_tempo_hari
        +date selesai_pada
        +str catatan_deposit
    }

    class Tagihan {
        +int id
        +int penyewaan_id
        +date periode
        +date jatuh_tempo
        +int total
    }

    class Pembayaran {
        +int id
        +int tagihan_id
        +date tanggal_bayar
        +int nominal
        +str metode
        +str catatan
        +str status
        +str alasan_batal
        +datetime dibatalkan_pada
        +str dibatalkan_oleh
    }

    class Admin {
        +int id
        +str username
        +str password_hash
        +int gagal_login
        +datetime terkunci_sampai
    }

    class ModelRules {
        <<module functions>>
        +total_valid(tagihan) int
        +sisa_tagihan(tagihan) int
        +status_tagihan(tagihan, today) str
        +status_kamar(kamar, today) str
        +sewa_aktif(penyewaan, today) bool
    }

    class KamarController {
        <<module>>
        +daftar(...)
        +buat(...)
        +ubah(...)
        +hapus(...)
        +status(...)
    }

    class PenghuniController {
        <<module>>
        +daftar(...)
        +buat(...)
        +ubah(...)
        +hapus(...)
    }

    class SewaController {
        <<module>>
        +daftar(...)
        +buat(...)
        +akhiri(...)
        +tagihan_terbuka(...)
    }

    class TagihanController {
        <<module>>
        +nominal_tagihan(...)
        +periode_valid(...)
        +buat_tagihan(...)
        +buat_massal(...)
        +daftar(...)
    }

    class PembayaranController {
        <<module>>
        +catat(...)
        +batal(...)
        +daftar(...)
        +ringkasan_bulan(...)
    }

    class AuthController {
        <<module>>
        +login(...)
        +sesi_kadaluarsa(...)
    }

    class LaporanController {
        <<module>>
        +okupansi(...)
        +pendapatan_bulan_berjalan(...)
        +tunggakan(...)
        +laporan_pendapatan(...)
        +laporan_tunggakan(...)
        +tren_pendapatan(...)
    }

    Properti "1" --> "0..*" Kamar : memiliki
    Kamar "1" --> "0..*" Penyewaan : riwayat sewa
    Penghuni "1" --> "0..*" Penyewaan : riwayat sewa
    Penyewaan "1" --> "0..*" Tagihan : menghasilkan
    Tagihan "1" --> "0..*" Pembayaran : menerima

    ModelRules ..> Kamar : menghitung status
    ModelRules ..> Tagihan : menghitung sisa/status
    KamarController ..> Kamar : mengelola
    PenghuniController ..> Penghuni : mengelola
    SewaController ..> Penyewaan : mengelola
    TagihanController ..> Tagihan : mengelola
    PembayaranController ..> Pembayaran : mengelola
    AuthController ..> Admin : autentikasi
    LaporanController ..> Properti : laporan
    LaporanController ..> Pembayaran : laporan pendapatan
    LaporanController ..> Tagihan : laporan tunggakan
```

**Keterangan relasi:**
- Satu `Properti` memiliki banyak `Kamar`; setiap kamar berada pada satu properti.
- `Kamar` dan `Penghuni` masing-masing dapat memiliki banyak riwayat `Penyewaan`.
- Satu `Penyewaan` dapat menghasilkan beberapa `Tagihan`, dan satu tagihan dapat menerima beberapa `Pembayaran`.
- `harga_sewa_bulan` disimpan pada `Penyewaan` sebagai salinan harga ketika sewa dibuat.
- Status kamar dan status tagihan dihitung melalui fungsi aturan domain, bukan disimpan sebagai atribut tersendiri.

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
