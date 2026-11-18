# -*- coding: utf-8 -*-
"""Pembayaran: catat penuh/sebagian, batalkan dengan alasan (FR-12..14, BR-15..19)."""
from datetime import date

from database import models as M
from utils.format import fmt_rupiah, hari_ini, sekarang


def catat(sess, tagihan: M.Tagihan, tanggal_bayar: date, nominal: int,
          metode: str = "Tunai", catatan: str = "") -> tuple[bool, str]:
    """Catat pembayaran penuh atau sebagian.

    BR-16: total valid tidak boleh melebihi total tagihan (sisa disebut di pesan).
    BR-17: nominal nol/negatif ditolak.
    """
    if nominal is None or int(nominal) <= 0:
        return False, "Nominal pembayaran harus lebih besar dari nol."  # BR-17
    nominal = int(nominal)
    if tanggal_bayar > hari_ini():
        return False, "Tanggal bayar tidak boleh di masa depan."
    sisa = M.sisa_tagihan(tagihan)
    if nominal > sisa:
        return False, f"Melebihi sisa tagihan {fmt_rupiah(sisa)}."  # BR-16
    sess.add(M.Pembayaran(tagihan_id=tagihan.id, tanggal_bayar=tanggal_bayar,
                          nominal=nominal, metode=metode, catatan=catatan or ""))
    sess.commit()  # transaksi tunggal; klik ganda tervalidasi ulang karena sisa berkurang
    return True, ""


def batal(sess, pembayaran_id: int, alasan: str, oleh: str) -> tuple[bool, str]:
    """BR-19/FR-14: pembatalan wajib beralasan; record tetap tersimpan, tidak dihitung."""
    p = sess.get(M.Pembayaran, pembayaran_id)
    if p is None:
        return False, "Pembayaran tidak ditemukan."
    if not (alasan or "").strip():
        return False, "Alasan pembatalan wajib diisi."
    if p.status == "Dibatalkan":
        return False, "Pembayaran ini sudah dibatalkan."
    p.status = "Dibatalkan"
    p.alasan_batal = alasan.strip()
    p.dibatalkan_pada = sekarang()
    p.dibatalkan_oleh = oleh
    sess.commit()
    return True, ""


def daftar(sess, properti_id: int | None = None, penghuni_id: int | None = None,
           dari: date | None = None, sampai: date | None = None, hanya_valid: bool = False):
    """Riwayat pembayaran (FR-15): filter properti, penghuni, rentang tanggal."""
    q = (sess.query(M.Pembayaran).join(M.Tagihan).join(M.Penyewaan)
         .join(M.Kamar).join(M.Properti)
         .order_by(M.Pembayaran.tanggal_bayar.desc(), M.Pembayaran.id.desc()))
    if properti_id:
        q = q.filter(M.Kamar.properti_id == properti_id)
    if penghuni_id:
        q = q.filter(M.Penyewaan.penghuni_id == penghuni_id)
    if dari:
        q = q.filter(M.Pembayaran.tanggal_bayar >= dari)
    if sampai:
        q = q.filter(M.Pembayaran.tanggal_bayar <= sampai)
    baris = []
    for p in q.all():
        if hanya_valid and p.status != "Valid":
            continue
        baris.append({
            "pembayaran": p, "tagihan": p.tagihan, "penyewaan": p.tagihan.penyewaan,
            "penghuni": p.tagihan.penyewaan.penghuni, "kamar": p.tagihan.penyewaan.kamar,
            "properti": p.tagihan.penyewaan.kamar.properti,
        })
    return baris


def ringkasan_bulan(baris: list, awal_bln, akhir_bln) -> dict:
    """Meta data halaman: Rp 12.450.000 · 21 pembayaran · Nov 2026 (hanya valid)."""
    dalam_periode = [b for b in baris
                     if b["pembayaran"].status == "Valid"
                     and awal_bln <= b["pembayaran"].tanggal_bayar <= akhir_bln]
    return {
        "total": sum(b["pembayaran"].nominal for b in dalam_periode),
        "jumlah": len(dalam_periode),
    }
