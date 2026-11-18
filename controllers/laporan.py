# -*- coding: utf-8 -*-
"""Laporan pendapatan & tunggakan (FR-16/FR-17, US-11) + ringkasan dashboard (FR-03).

Semua angka dihitung dari transaksi tersimpan — laporan wajib cocok dengan tampilan.
"""
from datetime import date

from sqlalchemy import select

from database import models as M
from utils.format import awal_bulan, fmt_rupiah, hari_ini, tambah_bulan


def _properti_aktif(sess):
    return list(sess.scalars(select(M.Properti).order_by(M.Properti.id)).all())


def okupansi(sess, today=None) -> dict:
    """FR-03: hunian per properti + daftar kamar kosong + perbaikan."""
    today = today or hari_ini()
    hasil = {}
    for p in _properti_aktif(sess):
        kamar = list(p.kamar)
        terisi = kosong = perbaikan = 0
        daftar_kosong, daftar_perbaikan = [], []
        for k in kamar:
            st = M.status_kamar(k, today)
            if st == "Terisi":
                terisi += 1
            elif st == "Kosong":
                kosong += 1
                daftar_kosong.append(k.nomor)
            else:
                perbaikan += 1
                daftar_perbaikan.append(k.nomor)
        hasil[p.id] = {
            "properti": p, "total": len(kamar), "terisi": terisi,
            "kosong": kosong, "perbaikan": perbaikan,
            "kamar_kosong": daftar_kosong, "kamar_perbaikan": daftar_perbaikan,
        }
    return hasil


def pendapatan_bulan_berjalan(sess, today=None) -> int:
    """FR-03: pembayaran valid berdasarkan tanggal bayar pada bulan berjalan."""
    today = today or hari_ini()
    awal = awal_bulan(today)
    data = sess.scalars(select(M.Pembayaran)).all()
    return sum(p.nominal for p in data
               if p.status == "Valid" and awal <= p.tanggal_bayar <= today)


def target_pendapatan(sess) -> int:
    """Target kas bulan berjalan = jumlah harga sewa semua penyewaan aktif (BR-08 salinan)."""
    today = hari_ini()
    aktif = sess.scalars(select(M.Penyewaan)).all()
    return sum(s.harga_sewa_bulan for s in aktif
               if s.selesai_pada is None and s.mulai <= today
               and (s.akhir_rencana is None or s.akhir_rencana >= today))


def tunggakan(sess, today=None) -> dict:
    """FR-03/FR-16: sisa tagihan dengan jatuh tempo sudah lewat, per properti."""
    today = today or hari_ini()
    semua = sess.scalars(select(M.Tagihan)).all()
    hasil = {p.id: {"properti": p, "total": 0, "penghuni": []} for p in _properti_aktif(sess)}
    jumlah_penghuni = set()
    for t in semua:
        st = M.status_tagihan(t, today)
        if st != "Menunggak":
            continue
        prop = t.penyewaan.kamar.properti
        hasil[prop.id]["total"] += M.sisa_tagihan(t)
        hasil[prop.id]["penghuni"].append(t)
        jumlah_penghuni.add(t.penyewaan.penghuni_id)
    hasil["total"] = sum(h["total"] for h in hasil.values())  # hanya dict per properti pada titik ini
    hasil["jumlah_penghuni"] = len(jumlah_penghuni)
    return hasil


def laporan_pendapatan(sess, dari: date, sampai: date, properti_id: int | None = None):
    """FR-16: pembayaran valid berdasar tanggal bayar, per periode & properti."""
    today = hari_ini()
    data = sess.scalars(select(M.Pembayaran)).all()
    baris = []
    for p in _properti_aktif(sess):
        if properti_id and p.id != properti_id:
            continue
        kamar_id = {k.id for k in p.kamar}
        valid = [pay for pay in data
                 if pay.status == "Valid" and dari <= pay.tanggal_bayar <= sampai
                 and pay.tagihan.penyewaan.kamar_id in kamar_id]
        baris.append({
            "properti": p, "dari": dari, "sampai": sampai,
            "total": sum(v.nominal for v in valid), "jumlah": len(valid),
        })
    total = sum(b["total"] for b in baris)
    jumlah = sum(b["jumlah"] for b in baris)
    baris.append({"properti": None, "total": total, "jumlah": jumlah,
                  "dari": dari, "sampai": sampai})
    return baris


def laporan_tunggakan(sess, today=None, properti_id: int | None = None):
    """FR-16: sisa tagihan lewat jatuh tempo per penghuni; baris Total di akhir."""
    today = today or hari_ini()
    semua = sess.scalars(select(M.Tagihan)).all()
    baris = []
    for t in semua:
        st = M.status_tagihan(t, today)
        if st != "Menunggak":
            continue
        prop = t.penyewaan.kamar.properti
        if properti_id and prop.id != properti_id:
            continue
        baris.append({
            "penghuni": t.penyewaan.penghuni, "kamar": t.penyewaan.kamar, "properti": prop,
            "periode": t.periode, "jatuh_tempo": t.jatuh_tempo, "sisa": M.sisa_tagihan(t),
            "hari_terlambat": (today - t.jatuh_tempo).days,
        })
    baris.sort(key=lambda b: b["sisa"], reverse=True)
    total = sum(b["sisa"] for b in baris)
    return baris, total


def tren_pendapatan(sess, n_bulan: int = 6, today=None):
    """Grafik tren untuk halaman Laporan (Bagian 6 v2.4) — dua warna properti tetap."""
    today = today or hari_ini()
    m0 = awal_bulan(today)
    bulan = [tambah_bulan(m0, -i) for i in range(n_bulan - 1, -1, -1)]
    data = sess.scalars(select(M.Pembayaran)).all()
    seri = {}
    for p in _properti_aktif(sess):
        kamar_id = {k.id for k in p.kamar}
        seri[p.nama] = [
            sum(x.nominal for x in data
                if x.status == "Valid" and awal_bulan(x.tanggal_bayar) == b
                and x.tagihan.penyewaan.kamar_id in kamar_id)
            for b in bulan
        ]
    return [f"{b.strftime('%b')}" for b in bulan], seri


def csv_laporan(judul: str, headers: list[str], rows: list[list[str]]) -> bytes:
    """FR-17: CSV dengan format angka & tanggal sama seperti tampilan."""
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([judul])
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")
