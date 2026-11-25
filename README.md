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
