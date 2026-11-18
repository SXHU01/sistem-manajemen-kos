# -*- coding: utf-8 -*-
"""CRUD kamar + status otomatis (FR-05/FR-06, BR-02/03/21)."""
from database import models as M
from utils.format import hari_ini, fmt_rupiah


def status(kamar: M.Kamar, today=None) -> str:
    return M.status_kamar(kamar, today or hari_ini())


def daftar(sess, properti_id: int | None = None, cari: str = "", filter_status: str | None = None):
    """Baris tabel kamar (6 kolom). Status dihitung, bukan disimpan."""
    today = hari_ini()
    q = sess.query(M.Kamar).join(M.Properti).order_by(M.Properti.id, M.Kamar.nomor)
    if properti_id:
        q = q.filter(M.Kamar.properti_id == properti_id)
    baris = []
    for k in q.all():
        st = status(k, today)
        if filter_status and st != filter_status:
            continue
        penghuni_aktif = next((s for s in k.penyewaan if s.selesai_pada is None), None)
        nama = penghuni_aktif.penghuni.nama if penghuni_aktif else ""
        baris.append({
            "kamar": k, "properti": k.properti, "status": st,
            "penghuni": nama, "punya_riwayat": len(k.penyewaan) > 0,
        })
    if cari:
        cari_l = cari.lower()
        baris = [b for b in baris if cari_l in b["kamar"].nomor.lower()
                 or cari_l in b["properti"].nama.lower() or cari_l in b["penghuni"].lower()]
    return baris


def ringkasan(baris: list) -> dict:
    """Meta data satu baris di bawah judul (v2.4): 24 kamar · 20 terisi · 3 kosong · 1 perbaikan."""
    jumlah = len(baris)
    return {
        "jumlah": jumlah,
        "terisi": sum(1 for b in baris if b["status"] == "Terisi"),
        "kosong": sum(1 for b in baris if b["status"] == "Kosong"),
        "perbaikan": sum(1 for b in baris if b["status"] == "Perbaikan"),
    }


def _validasi_nomor_harga(sess, properti_id, nomor, harga, kamar_id=None):
    nomor = (nomor or "").strip()
    if not nomor:
        return "Nomor kamar wajib diisi."
    if harga is None or int(harga) <= 0:
        return "Harga sewa harus lebih besar dari nol."
    kamar_lain = (sess.query(M.Kamar)
                  .filter(M.Kamar.properti_id == properti_id, M.Kamar.nomor == nomor,
                          M.Kamar.id != (kamar_id or 0))
                  .first())
    if kamar_lain:
        return f"Nomor kamar {nomor} sudah ada di properti ini."  # BR-03
    return ""


def buat(sess, properti_id, nomor, tipe, harga) -> tuple[bool, str]:
    pesan = _validasi_nomor_harga(sess, properti_id, nomor, harga)
    if pesan:
        return False, pesan
    sess.add(M.Kamar(properti_id=properti_id, nomor=nomor.strip(), tipe=tipe or "Standar",
                     harga_sewa=int(harga)))
    sess.commit()
    return True, ""


def ubah(sess, kamar_id, nomor, tipe, harga, perbaikan: bool) -> tuple[bool, str]:
    kamar = sess.get(M.Kamar, kamar_id)
    pesan = _validasi_nomor_harga(sess, kamar.properti_id, nomor, harga, kamar_id=kamar_id)
    if pesan:
        return False, pesan
    kamar.nomor, kamar.tipe, kamar.harga_sewa, kamar.perbaikan = nomor.strip(), tipe, int(harga), perbaikan
    sess.commit()  # BR-08: harga baru hanya berlaku untuk penyewaan baru
    return True, ""


def hapus(sess, kamar_id) -> tuple[bool, str]:
    """Integritas data PRD: kamar hanya dapat dihapus jika belum pernah memiliki penyewaan."""
    kamar = sess.get(M.Kamar, kamar_id)
    if kamar.penyewaan:
        return False, "Kamar ini sudah memiliki riwayat penyewaan dan tidak dapat dihapus."
    sess.delete(kamar)
    sess.commit()
    return True, ""
