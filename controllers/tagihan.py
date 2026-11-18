# -*- coding: utf-8 -*-
"""Tagihan: satuan & massal (FR-10, BR-10..14, BR-20)."""
from database import models as M
from utils.format import (awal_bulan, fmt_periode, fmt_rupiah, hari_dalam_bulan,
                          hari_ini, tambah_bulan)


def nominal_tagihan(sewa: M.Penyewaan, periode: "date") -> int:
    """Nominal tagihan untuk satu periode.

    BR-13: bulan penuh = harga sewa per bulan (disalin saat sewa dibuat, BR-08).
    BR-14: bulan pertama/terakhir prorata harian, dibulatkan ke rupiah terdekat.
    Jika mulai dan berakhir di bulan yang sama, prorata untuk seluruh periode itu.
    """
    harga = sewa.harga_sewa_bulan
    n_hari = hari_dalam_bulan(periode)
    awal_per = awal_bulan(periode)
    akhir_per = awal_per.replace(day=n_hari)

    sama_bulan = (sewa.akhir_rencana is not None
                  and awal_bulan(sewa.akhir_rencana) == awal_per
                  and awal_bulan(sewa.mulai) == awal_per)
    if sama_bulan:  # mulai dan berakhir di bulan yang sama
        terpakai = (sewa.akhir_rencana - sewa.mulai).days + 1
        return round(harga * terpakai / n_hari)

    bulan_mulai = awal_bulan(sewa.mulai)
    if awal_per == bulan_mulai and sewa.mulai.day > 1:  # bulan pertama
        terpakai = n_hari - sewa.mulai.day + 1
        return round(harga * terpakai / n_hari)

    if sewa.akhir_rencana is not None and awal_per == awal_bulan(sewa.akhir_rencana) \
            and sewa.akhir_rencana.day < n_hari:  # bulan terakhir
        terpakai = sewa.akhir_rencana.day
        return round(harga * terpakai / n_hari)

    return harga


def periode_valid(sewa: M.Penyewaan, periode: "date", today=None) -> tuple[bool, str]:
    """BR-12: periode harus dalam rentang sewa. BR-20: tidak melewati tanggal selesai."""
    awal_per = awal_bulan(periode)
    if awal_per < awal_bulan(sewa.mulai):
        return False, f"Periode {fmt_periode(periode)} sebelum tanggal mulai sewa."
    if sewa.selesai_pada is not None and awal_per > awal_bulan(sewa.selesai_pada):
        return False, (f"Periode {fmt_periode(periode)} setelah tanggal selesai "
                       f"({fmt_periode(sewa.selesai_pada)}); tagihan tidak dibuat.")  # BR-20
    if sewa.akhir_rencana is not None and awal_per > awal_bulan(sewa.akhir_rencana):
        return False, f"Periode {fmt_periode(periode)} melewati akhir rencana sewa."
    return True, ""


def buat_tagihan(sess, sewa: M.Penyewaan, periode: "date", today=None) -> tuple[bool, str]:
    """Buat satu tagihan. Mengembalikan pesan jika ditolak/dilewati."""
    valid, pesan = periode_valid(sewa, periode, today)
    if not valid:
        return False, pesan
    ada = (sess.query(M.Tagihan)
           .filter(M.Tagihan.penyewaan_id == sewa.id, M.Tagihan.periode == awal_bulan(periode))
           .first())
    if ada:
        return False, f"{sewa.penghuni.nama} — sudah punya tagihan {fmt_periode(periode)}."  # BR-11
    today = today or hari_ini()
    jt = tambah_bulan(awal_bulan(periode), 1).replace(day=sewa.jatuh_tempo_hari)
    sess.add(M.Tagihan(penyewaan_id=sewa.id, periode=awal_bulan(periode),
                       jatuh_tempo=jt, total=nominal_tagihan(sewa, periode)))
    sess.commit()
    return True, ""


def buat_massal(sess, periode: "date", today=None) -> dict:
    """FR-10: tagihan untuk semua penyewaan aktif dalam sekali proses.

    Mengembalikan {'dibuat': n, 'dilewati': [(nama, alasan), ...]} untuk toast + lonceng.
    Transaksi tunggal: commit sekali di akhir (keandalan PRD; klik ganda tetap
    terkendali oleh cek BR-11 sebelum menambah record)."""
    today = today or hari_ini()
    awal_per = awal_bulan(periode)
    dibuat, dilewati = 0, []
    try:
        sewa_aktif = sess.query(M.Penyewaan).filter(M.Penyewaan.selesai_pada.is_(None)).all()
        for s in sewa_aktif:
            valid, pesan = periode_valid(s, awal_per, today)
            if not valid:
                dilewati.append((s.penghuni.nama, pesan))
                continue
            ada = (sess.query(M.Tagihan)
                   .filter(M.Tagihan.penyewaan_id == s.id, M.Tagihan.periode == awal_per)
                   .first())
            if ada:
                dilewati.append((s.penghuni.nama,
                                 f"sudah punya tagihan {fmt_periode(awal_per)}"))  # BR-11
                continue
            jt = tambah_bulan(awal_per, 1).replace(day=s.jatuh_tempo_hari)
            sess.add(M.Tagihan(penyewaan_id=s.id, periode=awal_per, jatuh_tempo=jt,
                               total=nominal_tagihan(s, awal_per)))
            dibuat += 1
        sess.commit()
    except Exception:
        sess.rollback()  # rollback penuh (keandalan PRD)
        raise
    return {"dibuat": dibuat, "dilewati": dilewati}


def daftar(sess, status_filter: str | None = None, periode: "date | None" = None,
           properti_id: int | None = None, today=None):
    """Baris tabel tagihan: Penghuni, Kamar, Periode, Sisa, Status, Aksi (6 kolom v2.4)."""
    today = today or hari_ini()
    q = (sess.query(M.Tagihan).join(M.Penyewaan).join(M.Kamar).join(M.Properti)
         .order_by(M.Tagihan.jatuh_tempo.desc(), M.Tagihan.id.desc()))
    if properti_id:
        q = q.filter(M.Kamar.properti_id == properti_id)
    if periode is not None:
        q = q.filter(M.Tagihan.periode == awal_bulan(periode))
    baris = []
    for t in q.all():
        st = M.status_tagihan(t, today)
        if status_filter and st != status_filter:
            continue
        baris.append({"tagihan": t, "penyewaan": t.penyewaan, "kamar": t.penyewaan.kamar,
                      "penghuni": t.penyewaan.penghuni, "properti": t.penyewaan.kamar.properti,
                      "status": st, "sisa": M.sisa_tagihan(t)})
    return baris


def ringkasan(baris: list) -> dict:
    """Meta data: 42 tagihan · 3 perlu perhatian."""
    return {
        "jumlah": len(baris),
        "perhatian": sum(1 for b in baris if b["status"] in ("Sebagian", "Menunggak")),
    }
