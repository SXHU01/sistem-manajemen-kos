# -*- coding: utf-8 -*-
"""CRUD penghuni (FR-07). Hapus hanya jika belum pernah menyewa (integritas data PRD)."""
from database import models as M
from utils.format import hari_ini


def daftar(sess, cari: str = "", properti_id: int | None = None):
    today = hari_ini()
    q = sess.query(M.Penghuni).order_by(M.Penghuni.nama)
    baris = []
    for p in q.all():
        sewa_aktif = next((s for s in p.penyewaan if s.selesai_pada is None
                           and s.mulai <= today
                           and (s.akhir_rencana is None or s.akhir_rencana >= today)), None)
        if properti_id and (sewa_aktif is None or sewa_aktif.kamar.properti_id != properti_id):
            continue
        if cari and cari.lower() not in p.nama.lower() and cari not in p.telepon:
            continue
        baris.append({
            "penghuni": p,
            "kamar": sewa_aktif.kamar if sewa_aktif else None,
            "mulai": sewa_aktif.mulai if sewa_aktif else None,
            "punya_riwayat": len(p.penyewaan) > 0,
        })
    return baris


def _validasi(nama: str, telepon: str) -> str:
    if not (nama or "").strip():
        return "Nama wajib diisi."
    telepon = (telepon or "").strip()
    if telepon and not telepon.replace("-", "").replace(" ", "").isdigit():
        return "Nomor telepon hanya berisi angka."
    return ""


def buat(sess, nama, telepon, nomor_identitas, catatan) -> tuple[bool, str]:
    pesan = _validasi(nama, telepon)
    if pesan:
        return False, pesan
    sess.add(M.Penghuni(nama=nama.strip(), telepon=telepon.strip(),
                        nomor_identitas=(nomor_identitas or "").strip(), catatan=catatan or ""))
    sess.commit()
    return True, ""


def ubah(sess, penghuni_id, nama, telepon, nomor_identitas, catatan) -> tuple[bool, str]:
    p = sess.get(M.Penghuni, penghuni_id)
    pesan = _validasi(nama, telepon)
    if pesan:
        return False, pesan
    p.nama, p.telepon = nama.strip(), telepon.strip()
    p.nomor_identitas = (nomor_identitas or "").strip()
    p.catatan = catatan or ""
    sess.commit()
    return True, ""


def hapus(sess, penghuni_id) -> tuple[bool, str]:
    p = sess.get(M.Penghuni, penghuni_id)
    if p.penyewaan:
        return False, "Penghuni ini sudah memiliki riwayat penyewaan dan tidak dapat dihapus."
    sess.delete(p)
    sess.commit()
    return True, ""
