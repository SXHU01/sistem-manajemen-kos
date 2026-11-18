# KosManage

Manage Your Property, Simplify Your Business.

Aplikasi web untuk mengelola properti kos: kamar, penghuni, penyewaan, tagihan, pembayaran, dan laporan.

## Class Diagram

Diagram kelas KosManage berikut menggambarkan struktur kelas, atribut, operasi, serta hubungan antar kelas. Diagram ditulis menggunakan Mermaid agar dapat ditampilkan langsung oleh GitHub.

```mermaid
classDiagram
    class PropertiKos {
        +int id
        +string nama_kos
        +string alamat
        +text deskripsi
        +datetime created_at
        +tambahProperti()
        +ubahProperti()
        +lihatKamar()
    }

    class Kamar {
        +int id
        +int properti_id
        +string nomor_kamar
        +decimal harga_sewa
        +string status
        +text deskripsi
        +tambahKamar()
        +ubahKamar()
        +ubahStatus()
    }

    class Penghuni {
        +int id
        +string nama
        +string no_hp
        +text alamat
        +string email
        +datetime created_at
        +tambahPenghuni()
        +ubahPenghuni()
        +lihatRiwayatSewa()
    }

    class Penyewaan {
        +int id
        +int kamar_id
        +int penghuni_id
        +date tanggal_mulai
        +date tanggal_selesai
        +decimal harga_sewa
        +string status
        +buatPenyewaan()
        +validasiBentrokTanggal()
        +akhiriPenyewaan()
    }

    class Tagihan {
        +int id
        +int penyewaan_id
        +string periode
        +date tanggal_terbit
        +date tanggal_jatuh_tempo
        +decimal total_tagihan
        +string status
        +buatTagihan()
        +hitungSisaTagihan()
        +perbaruiStatus()
    }

    class Pembayaran {
        +int id
        +int tagihan_id
        +datetime tanggal_bayar
        +decimal jumlah_bayar
        +string metode
        +text catatan
        +catatPembayaran()
        +validasiJumlahBayar()
    }

    class Admin {
        +int id
        +string username
        +string password_hash
        +string nama
        +datetime created_at
        +login()
        +logout()
        +verifikasiPassword()
    }

    PropertiKos "1" --> "0..*" Kamar : memiliki
    Kamar "1" --> "0..*" Penyewaan : riwayat sewa
    Penghuni "1" --> "0..*" Penyewaan : memiliki riwayat
    Penyewaan "1" --> "0..*" Tagihan : menghasilkan
    Tagihan "1" --> "0..*" Pembayaran : menerima
```

**File diagram sumber:** [KosManage_ClassDiagram.drawio](KosManage_ClassDiagram.drawio) — dapat dibuka dan diedit menggunakan [diagrams.net](https://app.diagrams.net/).
