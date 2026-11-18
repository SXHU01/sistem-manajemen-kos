# -*- coding: utf-8 -*-
"""Penyewaan: buat & akhiri (FR-08/FR-09, BR-04..09, BR-20/21)."""
from database import models as M
from utils.format import fmt_tgl, hari_ini


def daftar(sess, properti_id: int | None = None):
    """Baris penyewaan: aktif dulu (terbaru), lalu selesai."""
    today = hari_ini()
    q = sess.query(M.Penyewaan).join(M.Kamar).join(M.Properti).order_by(M.Penyewaan.id.desc())
    if properti_id:
        q = q.filter(M.Kamar.properti_id == properti_id)
    baris = []
    for s in q.all():
        berlangsung = s.selesai_pada is None
        baris.append({
            "penyewaan": s, "kamar": s.kamar, "penghuni": s.penghuni, "properti": s.kamar.properti,
            "aktif": berlangsung,
            "status": "Berlangsung" if berlangsung else "Selesai",
        })
    baris.sort(key=lambda b: (not b["aktif"],))
    return baris


def _rentang_teks(mulai, akhir=None):
    if akhir is None:
        return f"{fmt_tgl(mulai)} sampai selesai"
    return f"{fmt_tgl(mulai)} sampai {fmt_tgl(akhir)}"


def buat(sess, kamar_id, penghuni_id, mulai, akhir_rencana, harga,
         jatuh_tempo_hari, deposit="") -> tuple[bool, str]:
    """Validasi lengkap sebelum simpan. Semua pesan sesuai acceptance criteria PRD."""
    kamar = sess.get(M.Kamar, kamar_id)
    penghuni = sess.get(M.Penghuni, penghuni_id)
    if kamar is None or penghuni is None:
        return False, "Kamar dan penghuni wajib dipilih."
    if harga is None or int(harga) <= 0:
        return False, "Harga sewa per bulan harus lebih besar dari nol."
    if not (1 <= int(jatuh_tempo_hari) <= 28):
        return False, "Tanggal jatuh tempo harus antara tanggal 1 dan 28."  # BR-09
    if kamar.perbaikan:
        return False, f"Kamar {kamar.nomor} sedang ditandai Perbaikan dan tidak dapat disewa."  # BR-21
    if akhir_rencana is not None and akhir_rencana < mulai:
        return False, "Tanggal akhir rencana tidak boleh sebelum tanggal mulai."

    # BR-04: tidak boleh dua penyewaan aktif bertumpang tindih pada kamar yang sama
    for lain in kamar.penyewaan:
        if lain.selesai_pada is not None:
            continue  # sudah diakhiri -> kamar bebas mulai tanggal selesai
        if lain.akhir_rencana is None or lain.akhir_rencana >= mulai:
            return False, (f"Kamar {kamar.nomor} sudah disewa pada "
                           f"{_rentang_teks(lain.mulai, lain.akhir_rencana)}. Pilih tanggal lain.")

    # BR-06: satu penghuni hanya satu penyewaan aktif
    for lain in penghuni.penyewaan:
        if lain.selesai_pada is None:
            return False, (f"Penghuni {penghuni.nama} masih memiliki penyewaan aktif "
                           f"di Kamar {lain.kamar.nomor}. Akhiri dulu penyewaan tersebut.")

    sess.add(M.Penyewaan(kamar_id=kamar_id, penghuni_id=penghuni_id, mulai=mulai,
                         akhir_rencana=akhir_rencana, harga_sewa_bulan=int(harga),
                         jatuh_tempo_hari=int(jatuh_tempo_hari), catatan_deposit=deposit or ""))
    sess.commit()
    return True, ""


def tagihan_terbuka(penyewaan: M.Penyewaan, today=None) -> list[M.Tagihan]:
    """Ringkasan tagihan masih terbuka (sisa > 0) — tampil sebelum konfirmasi pengakhiran (FR-09)."""
    return [t for t in penyewaan.tagihan if M.sisa_tagihan(t) > 0]


def akhiri(sess, penyewaan_id, tanggal_selesai) -> tuple[bool, str, list]:
    """Pengakhiran: menyimpan tanggal selesai; tagihan TIDAK dihapus (BR-20).

    Tagihan untuk periode setelah tanggal selesai memang tidak dibuat lagi
    (dicegah di controllers.tagihan.periode_valid)."""
    s = sess.get(M.Penyewaan, penyewaan_id)
    if s is None:
        return False, "Penyewaan tidak ditemukan.", []
    if s.selesai_pada is not None:
        return False, "Penyewaan ini sudah diakhiri.", []
    if tanggal_selesai < s.mulai:
        return False, "Tanggal selesai tidak boleh sebelum tanggal mulai."
    terbuka = tagihan_terbuka(s)
    s.selesai_pada = tanggal_selesai
    sess.commit()
    return True, "", terbuka
