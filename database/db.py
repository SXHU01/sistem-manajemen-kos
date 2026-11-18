# -*- coding: utf-8 -*-
"""Instalasi, backup harian, dan data awal KosManage.

Data contoh (fixture demo) konsisten dengan Design System v2.4 Bagian 6 —
angka yang sama dipakai di mockup dan dijadikan acuan penerimaan:
  24 kamar; terisi 20; kosong 102/204/210; Perbaikan 108;
  menunggak Citra Rp 600.000 (terlambat 5 hari) + Gita Rp 1.200.000 (terlambat 3 hari) = Rp 1.800.000;
  pendapatan bulan berjalan Rp 12.450.000 dari 21 pembayaran valid (Griya 7,5 jt · Wisma 4,95 jt);
  42 tagihan, 3 perlu perhatian.
Tanggal ditautkan ke hari ini (Asia/Jakarta) sehingga cerita demo selalu relevan.
"""
import os
import shutil
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import models as M
from utils.format import awal_bulan, hari_ini, tambah_bulan

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
BACKUP_DIR = os.path.join(PROJECT_DIR, "backups")
DB_FILE = os.path.join(DATA_DIR, "kosmanage.db")


def buat_engine(db_url: str | None = None):
    """Engine SQLite. Untuk mode memory (unit test) memakai StaticPool satu koneksi."""
    if db_url is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        db_url = f"sqlite:///{DB_FILE}"
    if db_url.endswith(":memory:"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return engine


def buat_sesi(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


# ----------------------------- Backup harian (FR-18) -----------------------------

def backup_harian(engine, hari: date | None = None) -> str | None:
    """Salin database sekali per hari ke backups/, simpan 30 terakhir. Kembalikan path jika dibuat."""
    raw = engine.url.database
    if not raw or not os.path.exists(raw):
        return None  # mode memory (unit test) tidak dibackup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    hari = hari or hari_ini()
    target = os.path.join(BACKUP_DIR, f"kosmanage-{hari.isoformat()}.db")
    if not os.path.exists(target):
        shutil.copy2(raw, target)
    # retensi 30 hari
    cadangan = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("kosmanage-") and f.endswith(".db"))
    for nama_lama in cadangan[:-30]:
        os.remove(os.path.join(BACKUP_DIR, nama_lama))
    return target


# ----------------------------- Seed -----------------------------

HARGA_STANDAR = 1_500_000
HARGA_SUITE_GM = 2_000_000
HARGA_SUITE_WC = 2_100_000


def seed_admin(sess: Session):
    """Admin tunggal dari environment variable, tidak dari kode (PRD keamanan)."""
    import bcrypt
    username = os.environ.get("KOSMANAGE_ADMIN_USER", "admin")
    password = os.environ.get("KOSMANAGE_ADMIN_PASS", "kosmanage123")  # ganti lewat env di produksi
    hash_ = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    sess.add(M.Admin(username=username, password_hash=hash_))


def seed_fixture(sess: Session):
    today = hari_ini()
    m0 = awal_bulan(today)             # bulan berjalan  (Nov 2026)
    m1 = tambah_bulan(m0, -1)          # bulan lalu      (Okt 2026)
    m2 = tambah_bulan(m0, -2)          # dua bulan lalu  (Sep 2026)

    # --- Properti (BR-01: tepat dua) ---
    gm = M.Properti(nama="Griya Melati", alamat="Jl. Melati No. 12, Bandung", warna="espresso")
    wc = M.Properti(nama="Wisma Cendana", alamat="Jl. Cendana No. 8, Bandung", warna="amber")
    sess.add_all([gm, wc])
    sess.flush()

    # --- Kamar (BR-02/03) ---
    kamar = {}
    for no in range(101, 113):
        suite = no == 108
        kamar[f"GM{no}"] = M.Kamar(properti_id=gm.id, nomor=str(no),
                                   tipe="Suite" if suite else "Standar",
                                   harga_sewa=HARGA_SUITE_GM if suite else HARGA_STANDAR,
                                   perbaikan=suite)  # 108 Perbaikan
    for no in range(201, 213):
        suite = no == 205
        kamar[f"WC{no}"] = M.Kamar(properti_id=wc.id, nomor=str(no),
                                   tipe="Suite" if suite else "Standar",
                                   harga_sewa=HARGA_SUITE_WC if suite else HARGA_STANDAR)
    sess.add_all(kamar.values())
    sess.flush()

    # --- Penghuni (FR-07) ---
    def peng(nama, no, prop_kode):
        urut = int(no)
        return M.Penghuni(nama=nama, telepon=f"0812-{prop_kode}{urut:04d}".replace("GM", "10").replace("WC", "20"),
                          nomor_identitas=f"327{prop_kode == 'WC' and 2 or 1}{urut:012d}",
                          catatan="")
    daftar_gm = [
        ("Andi Wijaya", "101"), ("Bagas Darmawan", "103"), ("Dewi Anggraini", "104"),
        ("Citra Lestari", "105"), ("Eko Prasetyo", "106"), ("Fajar Nugroho", "107"),
        ("Hendra Gunawan", "109"), ("Indah Permata", "110"), ("Joko Susilo", "111"),
        ("Kartika Sari", "112"),
    ]
    daftar_wc = [
        ("Lukman Hakim", "201"), ("Maya Putri", "202"), ("Budi Santoso", "203"),
        ("Gita Ramadhani", "205"), ("Nadia Rahma", "206"), ("Oscar Pratama", "207"),
        ("Putri Amelia", "208"), ("Qori Ananda", "209"), ("Rizky Maulana", "211"),
        ("Sari Wulandari", "212"),
    ]
    penghuni = {}
    for nama, no in daftar_gm:
        penghuni[nama] = peng(nama, no, "GM")
    for nama, no in daftar_wc:
        penghuni[nama] = peng(nama, no, "WC")
    sess.add_all(penghuni.values())
    sess.flush()

    # --- Penyewaan aktif (BR-07/08: harga disalin; jatuh tempo hari 1-28 BR-09) ---
    def sewa(kamar_kunci, penghuni_nama, jt_hari=12):
        k = kamar[kamar_kunci]
        return M.Penyewaan(kamar_id=k.id, penghuni_id=penghuni[penghuni_nama].id,
                           mulai=m2, akhir_rencana=None,          # mulai dua bulan lalu, berlangsung
                           harga_sewa_bulan=k.harga_sewa,         # BR-08
                           jatuh_tempo_hari=jt_hari,
                           catatan_deposit="Deposit Rp 500.000" if penghuni_nama == "Andi Wijaya" else "")
    sewa_map = {
        "Andi Wijaya": sewa("GM101", "Andi Wijaya"),
        "Bagas Darmawan": sewa("GM103", "Bagas Darmawan"),
        "Dewi Anggraini": sewa("GM104", "Dewi Anggraini"),
        "Citra Lestari": sewa("GM105", "Citra Lestari"),
        "Eko Prasetyo": sewa("GM106", "Eko Prasetyo"),
        "Fajar Nugroho": sewa("GM107", "Fajar Nugroho"),
        "Hendra Gunawan": sewa("GM109", "Hendra Gunawan"),
        "Indah Permata": sewa("GM110", "Indah Permata"),
        "Joko Susilo": sewa("GM111", "Joko Susilo"),
        "Kartika Sari": sewa("GM112", "Kartika Sari"),
        "Lukman Hakim": sewa("WC201", "Lukman Hakim"),
        "Maya Putri": sewa("WC202", "Maya Putri"),
        "Budi Santoso": sewa("WC203", "Budi Santoso"),
        "Gita Ramadhani": sewa("WC205", "Gita Ramadhani", jt_hari=14),
        "Nadia Rahma": sewa("WC206", "Nadia Rahma"),
        "Oscar Pratama": sewa("WC207", "Oscar Pratama"),
        "Putri Amelia": sewa("WC208", "Putri Amelia"),
        "Qori Ananda": sewa("WC209", "Qori Ananda"),
        "Rizky Maulana": sewa("WC211", "Rizky Maulana"),
        "Sari Wulandari": sewa("WC212", "Sari Wulandari"),
    }
    sess.add_all(sewa_map.values())
    sess.flush()

    # --- Tagihan (BR-10..13, bulan penuh) ---
    def tagihan(nama, periode):
        s = sewa_map[nama]
        jt = tambah_bulan(periode, 1).replace(day=s.jatuh_tempo_hari)  # jatuh tempo bulan berikutnya
        return M.Tagihan(penyewaan_id=s.id, periode=periode, jatuh_tempo=jt, total=s.harga_sewa_bulan)

    tag = {}
    # Dua tagihan Sep (legacy: dibuat manual saat onboarding penghuni)
    for nama in ("Hendra Gunawan", "Indah Permata"):
        tag[f"{nama}|Sep"] = tagihan(nama, m2)
    # Semua penyewaan aktif: Okt & Nov
    for nama in sewa_map:
        tag[f"{nama}|Okt"] = tagihan(nama, m1)
        tag[f"{nama}|Nov"] = tagihan(nama, m0)
    sess.add_all(tag.values())
    sess.flush()

    # --- Pembayaran (FR-12; nominal integer; BR-15/16) ---
    def bayar(nama, periode_label, nominal, tgl, metode="Tunai", catatan=""):
        t = tag[f"{nama}|{periode_label}"]
        return M.Pembayaran(tagihan_id=t.id, tanggal_bayar=tgl, nominal=nominal,
                            metode=metode, catatan=catatan, status="Valid")

    # Sep (2 pembayaran)
    sess.add(bayar("Hendra Gunawan", "Sep", 1_500_000, m2.replace(day=28), "Tunai"))
    sess.add(bayar("Indah Permata", "Sep", 1_500_000, m2.replace(day=25), "Transfer"))

    # Okt (17 pembayaran; semua tagihan Okt lunas KECUALI Citra & Gita yang sebagian)
    okt = [day for day in range(1, 29)]
    sess.add(bayar("Andi Wijaya", "Okt", 1_500_000, m1.replace(day=okt[9]), "Transfer"))
    sess.add(bayar("Bagas Darmawan", "Okt", 1_500_000, m1.replace(day=9), "Tunai"))
    sess.add(bayar("Dewi Anggraini", "Okt", 1_500_000, m1.replace(day=11), "Transfer"))
    sess.add(bayar("Eko Prasetyo", "Okt", 1_500_000, m1.replace(day=7), "Tunai"))
    sess.add(bayar("Fajar Nugroho", "Okt", 1_500_000, m1.replace(day=6), "Transfer"))
    sess.add(bayar("Indah Permata", "Okt", 1_500_000, m1.replace(day=12), "Tunai"))
    sess.add(bayar("Joko Susilo", "Okt", 300_000, m1.replace(day=20), "Tunai", "Bayaran pertama"))
    sess.add(bayar("Kartika Sari", "Okt", 600_000, m1.replace(day=19), "Transfer"))
    sess.add(bayar("Lukman Hakim", "Okt", 1_050_000, m1.replace(day=21), "Transfer"))
    sess.add(bayar("Maya Putri", "Okt", 1_500_000, m1.replace(day=15), "Tunai"))
    sess.add(bayar("Putri Amelia", "Okt", 1_200_000, m1.replace(day=16), "Transfer"))
    sess.add(bayar("Budi Santoso", "Okt", 1_500_000, m1.replace(day=8), "Tunai"))
    sess.add(bayar("Nadia Rahma", "Okt", 1_500_000, m1.replace(day=9), "Transfer"))
    sess.add(bayar("Oscar Pratama", "Okt", 1_500_000, m1.replace(day=13), "Tunai"))
    sess.add(bayar("Qori Ananda", "Okt", 1_500_000, m1.replace(day=10), "Transfer"))
    sess.add(bayar("Rizky Maulana", "Okt", 1_500_000, m1.replace(day=14), "Tunai"))
    sess.add(bayar("Sari Wulandari", "Okt", 1_500_000, m1.replace(day=18), "Transfer"))
    # Gita (Kamar 205 Suite Rp 2.100.000): bayar sebagian 600 rb di Okt, sisanya 300 rb di Nov
    sess.add(bayar("Gita Ramadhani", "Okt", 600_000, m1.replace(day=28), "Tunai", "Bayaran pertama"))

    # Nov (21 pembayaran valid; total Rp 12.450.000 — Griya 7,5 jt · Wisma 4,95 jt)
    nov = [
        # (nama, periode tagihan, nominal, tanggal, metode)
        ("Andi Wijaya", "Nov", 750_000, 1, "Transfer"), ("Andi Wijaya", "Nov", 750_000, 8, "Tunai"),
        ("Fajar Nugroho", "Nov", 1_500_000, 5, "Transfer"),
        ("Citra Lestari", "Okt", 600_000, 2, "Tunai"), ("Citra Lestari", "Okt", 300_000, 7, "Tunai"),
        ("Hendra Gunawan", "Okt", 500_000, 3, "Tunai"), ("Hendra Gunawan", "Okt", 500_000, 8, "Transfer"),
        ("Hendra Gunawan", "Okt", 500_000, 14, "Tunai"),
        ("Joko Susilo", "Okt", 600_000, 5, "Transfer"), ("Joko Susilo", "Okt", 600_000, 12, "Tunai"),
        ("Kartika Sari", "Okt", 450_000, 6, "Tunai"), ("Kartika Sari", "Okt", 450_000, 13, "Transfer"),
        ("Nadia Rahma", "Nov", 900_000, 3, "Transfer"), ("Nadia Rahma", "Nov", 600_000, 10, "Tunai"),
        ("Qori Ananda", "Nov", 750_000, 6, "Transfer"), ("Qori Ananda", "Nov", 750_000, 12, "Tunai"),
        ("Budi Santoso", "Nov", 450_000, 4, "Tunai"), ("Budi Santoso", "Nov", 450_000, 9, "Transfer"),
        ("Gita Ramadhani", "Okt", 300_000, 11, "Tunai", "Menyusul"),
        ("Lukman Hakim", "Okt", 450_000, 10, "Transfer"),
        ("Putri Amelia", "Okt", 300_000, 9, "Tunai"),
    ]
    for row in nov:
        nama, per, nominal, d, met = row[0], row[1], row[2], row[3], row[4]
        catatan = row[5] if len(row) > 5 else ""
        d_aktual = min(d, today.day)  # tanggal bayar tidak boleh di masa depan
        sess.add(bayar(nama, per, nominal, m0.replace(day=d_aktual), met, catatan))

    # Koreksi: satu pembayaran dibatalkan (BR-19) — tetap tersimpan, tidak dihitung
    eko_tag = tag["Eko Prasetyo|Nov"]
    sess.add(M.Pembayaran(tagihan_id=eko_tag.id, tanggal_bayar=m0.replace(day=min(3, today.day)),
                          nominal=750_000,
                          metode="Transfer", status="Dibatalkan",
                          alasan_batal="Salah input nominal", dibatalkan_pada=None,
                          dibatalkan_oleh="Admin"))
    sess.flush()

    verifikasi_fixture(sess, today, m0)


def verifikasi_fixture(sess: Session, today: date, m0: date):
    """Angka fixture wajib cocok dengan kontrak Design System v2.4 (jalankan sekali saat seed)."""
    tagihan = sess.scalars(select(M.Tagihan)).all()
    assert len(tagihan) == 42, f"jumlah tagihan {len(tagihan)} != 42"

    perhatian = [t for t in tagihan if M.status_tagihan(t, today) in ("Sebagian", "Menunggak")]
    assert len(perhatian) == 3, f"perlu perhatian {len(perhatian)} != 3"

    tunggakan = sum(M.sisa_tagihan(t) for t in tagihan
                    if M.status_tagihan(t, today) == "Menunggak")
    assert tunggakan == 1_800_000, f"tunggakan {tunggakan} != 1.800.000"

    pendapatan_nov = sum(p.nominal for p in sess.scalars(select(M.Pembayaran)).all()
                         if p.status == "Valid" and p.tanggal_bayar >= m0)
    assert pendapatan_nov == 12_450_000, f"pendapatan Nov {pendapatan_nov} != 12.450.000"

    kamar = sess.scalars(select(M.Kamar)).all()
    st_gm = [M.status_kamar(k, today) for k in kamar if k.properti.nama == "Griya Melati"]
    st_wc = [M.status_kamar(k, today) for k in kamar if k.properti.nama == "Wisma Cendana"]
    assert st_gm.count("Terisi") == 10 and st_gm.count("Perbaikan") == 1 and st_gm.count("Kosong") == 1
    assert st_wc.count("Terisi") == 10 and st_wc.count("Kosong") == 2
    print("Fixture OK: 42 tagihan · 3 perlu perhatian · tunggakan Rp 1.800.000 · pendapatan Nov Rp 12.450.000")


def init_db(db_url: str | None = None) -> tuple[object, sessionmaker]:
    """Buat tabel + seed jika kosong. Dipanggil sekali saat aplikasi start / test."""
    engine = buat_engine(db_url)
    M.Base.metadata.create_all(engine)
    factory = buat_sesi(engine)
    with factory() as sess:
        ada_admin = sess.scalar(select(M.Admin).limit(1)) is not None
        ada_properti = sess.scalar(select(M.Properti).limit(1)) is not None
        if not ada_admin:
            seed_admin(sess)
        if not ada_properti:
            seed_fixture(sess)
        sess.commit()
    return engine, factory
