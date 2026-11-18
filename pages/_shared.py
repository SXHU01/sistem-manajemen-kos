# -*- coding: utf-8 -*-
"""Dialog bersama antar halaman (satu tombol primer per halaman tetap terjaga)."""
import streamlit as st

from controllers import pembayaran as c_pembayaran
from database import models as M
from utils.format import fmt_periode, fmt_rupiah, hari_ini
from utils import notify


def tagihan_terbuka_options(sess) -> list[dict]:
    """Semua tagihan dengan sisa > 0, urut paling mendesak (menunggak dulu)."""
    today = hari_ini()
    opsi = []
    for t in sess.query(M.Tagihan).all():
        sisa = M.sisa_tagihan(t)
        if sisa <= 0:
            continue
        stt = M.status_tagihan(t, today)
        opsi.append({
            "tagihan": t, "sisa": sisa, "status": stt,
            "label": (f"{t.penyewaan.penghuni.nama} · Kamar {t.penyewaan.kamar.nomor} · "
                      f"{fmt_periode(t.periode)} · sisa {fmt_rupiah(sisa)} · {stt}"),
        })
    urutan = {"Menunggak": 0, "Sebagian": 1, "Belum dibayar": 2}
    opsi.sort(key=lambda o: urutan.get(o["status"], 3))
    return opsi


@st.dialog("Catat Pembayaran", width="small")
def dialog_catat_pembayaran(factory):
    """FR-12/BR-16/BR-17. Error validasi tampil di dalam dialog, di bawah field-nya."""
    with factory() as sess:
        opsi = tagihan_terbuka_options(sess)
        if not opsi:
            st.caption("Semua tagihan lunas. Tidak ada yang perlu dibayar.")
            if st.button("Tutup", use_container_width=True):
                st.rerun()
            return
        pilih = st.selectbox("Tagihan", opsi, format_func=lambda o: o["label"],
                             index=0, key="dlg_tagihan")
        t = pilih["tagihan"]
        st.caption(f"Total tagihan {fmt_rupiah(t.total)} · sisa {fmt_rupiah(pilih['sisa'])} "
                   f"(batas pembayaran)")
        c1, c2 = st.columns(2)
        tanggal = c1.date_input("Tanggal bayar", value=hari_ini(), format="DD/MM/YYYY", key="dlg_tgl")
        nominal = c2.number_input("Nominal", min_value=0, step=50_000,
                                  value=pilih["sisa"], key="dlg_nominal")
        metode = st.radio("Metode", ["Tunai", "Transfer"], horizontal=True, key="dlg_metode")
        catatan = st.text_input("Catatan (opsional)", key="dlg_catatan")
        err = ""
        if st.button("Simpan Pembayaran", type="primary", use_container_width=True):
            ok, pesan = c_pembayaran.catat(sess, t, tanggal, int(nominal), metode, catatan)
            if ok:
                notify.toast(f"Pembayaran {fmt_rupiah(int(nominal))} tercatat.")
                sisa_baru = M.sisa_tagihan(t)
                if sisa_baru == 0:
                    notify.toast("Tagihan lunas.", "ok")
                st.rerun()
            err = pesan
        if err:
            st.error(err)


@st.dialog("Batalkan Pembayaran", width="small")
def dialog_batal_pembayaran(factory, pembayaran_id: int, keterangan: str):
    """FR-14/BR-19: alasan wajib; record tetap tampil di riwayat."""
    with factory() as sess:
        st.caption(f"Pembayaran yang dipilih: {keterangan}")
        st.caption("Pembayaran yang dibatalkan tetap tersimpan dan tidak lagi dihitung.")
        alasan = st.text_area("Alasan pembatalan (wajib)", key="dlg_alasan")
        err = ""
        if st.button("Batalkan Pembayaran", type="primary", use_container_width=True):
            ok, pesan = c_pembayaran.batal(sess, pembayaran_id, alasan, "Admin")
            if ok:
                notify.toast("Pembayaran dibatalkan. Riwayat tetap tersimpan.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)
