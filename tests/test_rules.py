# -*- coding: utf-8 -*-
"""Unit test aturan bisnis BR-01..BR-21 + kontrak fixture demo (PRD Bagian 9: maintainability).

Jalankan dari folder kosmanage-app:  python -m tests.test_rules
Urutan: cek kontrak fixture (data awal) dulu, baru mutasi data untuk aturan bisnis.
"""
import calendar
from datetime import timedelta

from sqlalchemy import select

from database import models as M
from database.db import init_db
from controllers import auth as c_auth
from controllers import kamar as c_kamar
from controllers import pembayaran as c_pembayaran
from controllers import sewa as c_sewa
from controllers import tagihan as c_tagihan
from controllers import laporan as c_laporan
from utils.format import awal_bulan, fmt_rupiah, hari_ini, tambah_bulan

GAGAL = []


def cek(judul, kondisi, detail=""):
    print(f"[{'LULUS' if kondisi else 'GAGAL'}] {judul}" + (f" — {detail}" if detail and not kondisi else ""))
    if not kondisi:
        GAGAL.append(judul)


def main():
    engine, factory = init_db("sqlite:///:memory:")
    today = hari_ini()
    m0 = awal_bulan(today)
    m1 = tambah_bulan(m0, -1)

    with factory() as sess:
        # ================= KONTRAK FIXTURE (data awal, sebelum mutasi) =================
        properti = list(sess.scalars(select(M.Properti)).all())
        cek("BR-01 tepat dua properti", len(properti) == 2)
        gm, wc = properti
        semua_tag = sess.scalars(select(M.Tagihan)).all()
        cek("Fixture: 42 tagihan", len(semua_tag) == 42, str(len(semua_tag)))
        perhatian = [t for t in semua_tag if M.status_tagihan(t, today) in ("Sebagian", "Menunggak")]
        cek("Fixture: 3 perlu perhatian", len(perhatian) == 3, str(len(perhatian)))
        tunggakan = sum(M.sisa_tagihan(t) for t in semua_tag
                        if M.status_tagihan(t, today) == "Menunggak")
        cek("Fixture: tunggakan Rp 1.800.000 (Citra 600 rb + Gita 1,2 jt)",
            tunggakan == 1_800_000, fmt_rupiah(tunggakan))
        pendapatan = sum(p.nominal for p in sess.scalars(select(M.Pembayaran)).all()
                         if p.status == "Valid" and p.tanggal_bayar >= m0)
        cek("Fixture: pendapatan bulan berjalan Rp 12.450.000", pendapatan == 12_450_000,
            fmt_rupiah(pendapatan))
        okupansi = c_laporan.okupansi(sess, today)
        gm_ok, wc_ok = okupansi[gm.id], okupansi[wc.id]
        cek("FR-03 okupansi 20/24, kosong 102/204/210, perbaikan 108",
            gm_ok["terisi"] == 10 and gm_ok["perbaikan"] == 1 and gm_ok["kamar_kosong"] == ["102"]
            and wc_ok["terisi"] == 10 and wc_ok["kamar_kosong"] == ["204", "210"],
            f"GM={gm_ok['terisi']}/12 {gm_ok['kamar_kosong']} · WC={wc_ok['terisi']}/12 {wc_ok['kamar_kosong']}")

        # ================= ATURAN BISNIS (mutasi data) =================
        kamar_101 = sess.query(M.Kamar).filter_by(nomor="101").first()
        kamar_102 = sess.query(M.Kamar).filter_by(nomor="102").first()
        kamar_108 = sess.query(M.Kamar).filter_by(nomor="108").first()
        kamar_103 = sess.query(M.Kamar).filter_by(nomor="103").first()
        kamar_205 = sess.query(M.Kamar).filter_by(nomor="205").first()
        andi = sess.query(M.Penghuni).filter_by(nama="Andi Wijaya").first()
        bagas = sess.query(M.Penghuni).filter_by(nama="Bagas Darmawan").first()

        # BR-03: nomor kamar unik per properti
        ok, pesan = c_kamar.buat(sess, gm.id, "101", "Standar", 1_500_000)
        cek("BR-03 nomor kamar ganda ditolak dengan pesan menyebut nomor",
            not ok and "101" in pesan, pesan)

        # BR-21: kamar Perbaikan tidak dapat disewa
        ok, pesan = c_sewa.buat(sess, kamar_108.id, bagas.id, today, None, 1_500_000, 12)
        cek("BR-21 kamar Perbaikan ditolak", not ok and "Perbaikan" in pesan, pesan)

        # BR-04: sewa bertumpang tindih pada kamar sama
        ok, pesan = c_sewa.buat(sess, kamar_101.id, bagas.id, today, None, 1_500_000, 12)
        cek("BR-04 sewa bertumpang tindih ditolak, pesan sebut rentang",
            not ok and "sudah disewa" in pesan, pesan)

        # BR-06: satu penghuni hanya satu sewa aktif (di kamar kosong 102)
        ok, pesan = c_sewa.buat(sess, kamar_102.id, andi.id, today, None, 1_500_000, 12)
        cek("BR-06 penghuni ganda aktif ditolak", not ok and "penyewaan aktif" in pesan, pesan)

        # BR-09: jatuh tempo 1..28
        ok, pesan = c_sewa.buat(sess, kamar_205.id, bagas.id, today, None, 2_100_000, 29)
        cek("BR-09 jatuh tempo >28 ditolak", not ok and "1 dan 28" in pesan, pesan)

        # FR-09/BR-20: akhiri sewa Bagas -> tagihan terbuka dilaporkan, tidak dihapus
        sewa_bagas = next(s for s in bagas.penyewaan if s.selesai_pada is None)
        n_tag_sebelum = len(sewa_bagas.tagihan)
        ok, pesan, terbuka = c_sewa.akhiri(sess, sewa_bagas.id, today)
        cek("FR-09 pengakhiran menyebut tagihan terbuka", ok and len(terbuka) > 0,
            f"terbuka={len(terbuka)}")
        cek("BR-20 tagihan tetap ada setelah pengakhiran",
            len(sewa_bagas.tagihan) == n_tag_sebelum)

        # BR-05: sewa baru diperbolehkan setelah pengakhiran (kamar & penghuni bebas)
        ok, pesan = c_sewa.buat(sess, kamar_103.id, bagas.id, today + timedelta(days=1),
                                None, 1_500_000, 12)
        cek("BR-05 sewa baru setelah pengakhiran diperbolehkan", ok, pesan)

        # FR-10/BR-11: tagihan massal; yang sudah punya dilewati, yang baru dibuat
        hasil = c_tagihan.buat_massal(sess, m0, today)
        cek("FR-10/BR-11 massal: 1 sewa baru mendapat tagihan, 19 dilewati",
            hasil["dibuat"] == 1 and len(hasil["dilewati"]) == 19,
            f"dibuat={hasil['dibuat']} dilewati={len(hasil['dilewati'])}")

        # BR-12: periode sebelum mulai sewa ditolak
        sewa_andi = next(s for s in andi.penyewaan if s.selesai_pada is None)
        ok, pesan = c_tagihan.buat_tagihan(sess, sewa_andi, tambah_bulan(m0, -6), today)
        cek("BR-12 periode di luar rentang ditolak", not ok and "sebelum tanggal mulai" in pesan, pesan)

        # BR-20: periode setelah tanggal selesai tidak dibuat
        ok, pesan = c_tagihan.buat_tagihan(sess, sewa_bagas, tambah_bulan(m0, 2), today)
        cek("BR-20 tagihan setelah tanggal selesai tidak dibuat",
            not ok and "tidak dibuat" in pesan, pesan)

        # BR-13/BR-14: nominal penuh & prorata (objek transient, tidak disimpan)
        sewa_test = M.Penyewaan(kamar_id=kamar_205.id, penghuni_id=andi.id,
                                mulai=m0.replace(day=15), akhir_rencana=None,
                                harga_sewa_bulan=1_500_000, jatuh_tempo_hari=12)
        n_hari = c_tagihan.nominal_tagihan(sewa_test, m0)
        harapan = round(1_500_000 * (calendar.monthrange(m0.year, m0.month)[1] - 14)
                        / calendar.monthrange(m0.year, m0.month)[1])
        cek("BR-14 prorata bulan pertama harian", n_hari == harapan, f"{n_hari} != {harapan}")
        cek("BR-13 bulan penuh = harga sewa",
            c_tagihan.nominal_tagihan(sewa_test, tambah_bulan(m0, 1)) == 1_500_000)
        sewa_sama = M.Penyewaan(kamar_id=kamar_205.id, penghuni_id=andi.id,
                                mulai=m0.replace(day=10), akhir_rencana=m0.replace(day=20),
                                harga_sewa_bulan=1_500_000, jatuh_tempo_hari=12)
        n_sama = c_tagihan.nominal_tagihan(sewa_sama, awal_bulan(sewa_sama.mulai))
        cek("BR-14 mulai & akhir sebulan, prorata seluruh periode",
            n_sama == round(1_500_000 * 11 / calendar.monthrange(m0.year, m0.month)[1]), f"{n_sama}")

        # BR-16/BR-17: pembayaran berlebih & nol ditolak
        tag_gita = (sess.query(M.Tagihan).join(M.Penyewaan)
                    .filter(M.Penyewaan.penghuni.has(M.Penghuni.nama == "Gita Ramadhani"),
                            M.Tagihan.periode == m1).first())
        sisa_gita = M.sisa_tagihan(tag_gita)
        ok, pesan = c_pembayaran.catat(sess, tag_gita, today, sisa_gita + 1)
        cek("BR-16 melebihi sisa ditolak, sisa disebut di pesan",
            not ok and fmt_rupiah(sisa_gita) in pesan, pesan)
        ok, pesan = c_pembayaran.catat(sess, tag_gita, today, 0)
        cek("BR-17 nominal nol ditolak", not ok and "lebih besar dari nol" in pesan, pesan)

        # BR-19: pembatalan wajib alasan; record tetap tersimpan, tidak dihitung
        pay_fajar = (sess.query(M.Pembayaran).join(M.Tagihan).join(M.Penyewaan)
                     .filter(M.Penyewaan.penghuni.has(M.Penghuni.nama == "Fajar Nugroho"),
                             M.Pembayaran.status == "Valid").first())
        ok, pesan = c_pembayaran.batal(sess, pay_fajar.id, "", "Admin")
        cek("BR-19 pembatalan tanpa alasan ditolak", not ok and "wajib" in pesan, pesan)
        tag_fajar = pay_fajar.tagihan
        sisa_sebelum = M.sisa_tagihan(tag_fajar)
        ok, pesan = c_pembayaran.batal(sess, pay_fajar.id, "Salah input nominal", "Admin")
        cek("BR-19 pembatalan berhasil, record tetap ada dan tidak dihitung",
            ok and pay_fajar.status == "Dibatalkan"
            and M.sisa_tagihan(tag_fajar) == sisa_sebelum + pay_fajar.nominal)

        # BR-18: empat status tagihan
        sess.add(sewa_test)  # simpan agar bisa jadi induk tagihan uji status
        sess.flush()
        t_baru = M.Tagihan(penyewaan_id=sewa_test.id, periode=tambah_bulan(m0, 1),
                           jatuh_tempo=tambah_bulan(m0, 2), total=1_500_000)
        sess.add(t_baru)
        sess.commit()
        cek("BR-18 Belum dibayar (valid = 0)", M.status_tagihan(t_baru, today) == "Belum dibayar")
        sess.add(M.Pembayaran(tagihan_id=t_baru.id, tanggal_bayar=today, nominal=500_000, status="Valid"))
        sess.commit()
        sess.expire_all()  # muat ulang relasi pembayaran (expire_on_commit=False)
        cek("BR-18 Sebagian (0 < valid < total)", M.status_tagihan(t_baru, today) == "Sebagian")
        cek("BR-18 Menunggak (belum lunas, lewat jatuh tempo)",
            M.status_tagihan(t_baru, tambah_bulan(m0, 2).replace(day=13)) == "Menunggak")
        sess.add(M.Pembayaran(tagihan_id=t_baru.id, tanggal_bayar=today, nominal=1_000_000, status="Valid"))
        sess.commit()
        sess.expire_all()
        cek("BR-18 Lunas (valid = total)", M.status_tagihan(t_baru, today) == "Lunas")

        # FR-01/FR-02: autentikasi
        with factory() as sess_auth:
            for _ in range(5):
                ok, pesan = c_auth.login(sess_auth, "admin", "passwordsalah")
            cek("FR-01 lima gagal login mengunci akun 5 menit", not ok and "dikunci" in pesan, pesan)
            ok, pesan = c_auth.login(sess_auth, "admin", "kosmanage123")
            cek("FR-01 akun terkunci menolak password benar", not ok and "terkunci" in pesan, pesan)
            cek("FR-02 idle 61 menit berakhir", c_auth.sesi_kadaluarsa(
                c_auth.sekarang() - timedelta(minutes=61)))
            cek("FR-02 idle 5 menit masih aktif", not c_auth.sesi_kadaluarsa(
                c_auth.sekarang() - timedelta(minutes=5)))

    print()
    if GAGAL:
        print(f"{len(GAGAL)} TES GAGAL: {GAGAL}")
        raise SystemExit(1)
    print("SEMUA TES LULUS")


if __name__ == "__main__":
    main()
