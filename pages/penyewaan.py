# -*- coding: utf-8 -*-
"""Penyewaan (US-06, FR-08/09) — tabel 6 kolom; buat & akhiri lewat dialog konfirmasi."""
import streamlit as st

from controllers import sewa as c_sewa
from database import models as M
from utils import notify
from utils.format import fmt_periode, fmt_rupiah, fmt_tgl, hari_ini
from utils.ui import esc, kamar_badge, meta, pill, render_table


@st.dialog("Buat Penyewaan", width="small")
def dialog_buat(factory, kamar_list, penghuni_list):
    with factory() as sess:
        st.caption("Harga sewa dan jatuh tempo disalin ke penyewaan saat dibuat (BR-08).")
        p_kamar = st.selectbox("Kamar", kamar_list,
                               format_func=lambda k: f"Kamar {k.nomor} · {k.properti.nama} · {fmt_rupiah(k.harga_sewa)}")
        p_pg = st.selectbox("Penghuni", penghuni_list, format_func=lambda p: p.nama)
        c1, c2 = st.columns(2)
        mulai = c1.date_input("Tanggal mulai", value=hari_ini(), format="DD/MM/YYYY")
        akhir = c2.date_input("Akhir rencana (opsional)", value=None, format="DD/MM/YYYY")
        harga = st.number_input("Harga sewa per bulan", min_value=0, step=50_000,
                                value=p_kamar.harga_sewa)
        jt = st.number_input("Tanggal jatuh tempo tagihan (1-28)", min_value=1, max_value=28, value=12)
        deposit = st.text_input("Catatan deposit (opsional)")
        err = ""
        if st.button("Simpan Penyewaan", type="primary", use_container_width=True):
            ok, pesan = c_sewa.buat(sess, p_kamar.id, p_pg.id, mulai,
                                    akhir, int(harga), int(jt), deposit)
            if ok:
                notify.toast(f"Penyewaan Kamar {p_kamar.nomor} untuk {p_pg.nama} dibuat.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)


@st.dialog("Akhiri Penyewaan", width="small")
def dialog_akhiri(factory, penyewaan_id: int, keterangan: str):
    """FR-09: tampilkan ringkasan tagihan terbuka SEBELUM konfirmasi."""
    with factory() as sess:
        s = sess.get(M.Penyewaan, penyewaan_id)
        st.caption(keterangan)
        tanggal = st.date_input("Tanggal selesai sebenarnya", value=hari_ini(), format="DD/MM/YYYY")
        terbuka = c_sewa.tagihan_terbuka(s)
        if terbuka:
            st.warning(f"Ada {len(terbuka)} tagihan masih terbuka yang tetap harus dilunasi:")
            for t in terbuka:
                st.markdown(f"- {fmt_periode(t.periode)} · sisa {fmt_rupiah(M.sisa_tagihan(t))}")
        else:
            st.caption("Semua tagihan penyewaan ini sudah lunas.")
        err = ""
        if st.button("Akhiri Penyewaan", type="primary", use_container_width=True):
            ok, pesan, _terbuka = c_sewa.akhiri(sess, penyewaan_id, tanggal)
            if ok:
                kamar = s.kamar
                notify.toast(f"Penyewaan Kamar {kamar.nomor} diakhiri. "
                             f"Kamar bebas disewa mulai {fmt_tgl(tanggal)}.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)


def render(factory):
    with factory() as sess:
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        today = hari_ini()

        c1, c2, ca = st.columns([2.2, 2.2, 1.8])
        pilih_prop = c1.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  key="sw_prop")
        status_f = c2.selectbox("Status", [None, "Berlangsung", "Selesai"],
                                format_func=lambda s: "Semua status" if s is None else s,
                                key="sw_status")
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("➕ Buat Penyewaan", type="primary", use_container_width=True):
                kamar_list = [k for k in sess.query(M.Kamar).all()
                              if not k.perbaikan]  # BR-21: kamar Perbaikan tidak dapat disewa
                penghuni_list = list(sess.query(M.Penghuni).order_by(M.Penghuni.nama).all())
                dialog_buat(factory, kamar_list, penghuni_list)

        baris = c_sewa.daftar(sess, properti_id=pilih_prop.id if pilih_prop else None)
        if status_f:
            baris = [b for b in baris if b["status"] == status_f]
        aktif = sum(1 for b in baris if b["aktif"])
        st.subheader("Daftar penyewaan")
        st.markdown(f"<div class='meta-line'>{meta(**{'penyewaan': len(baris), 'berlangsung': aktif})} "
                    f"&mdash; harga sewa disalin saat dibuat (BR-08)</div>",
                    unsafe_allow_html=True)

        kolom = [
            {"label": "PENGHUNI", "key": "penghuni", "width": "22%"},
            {"label": "KAMAR", "key": "kamar", "width": "16%"},
            {"label": "MULAI", "key": "mulai", "width": "14%"},
            {"label": "AKHIR RENCANA", "key": "akhir", "width": "16%"},
            {"label": "HARGA SEWA", "key": "harga", "num": True, "width": "16%"},
            {"label": "STATUS", "key": "status", "width": "16%"},
        ]
        rows = [{
            "penghuni": f"<span class='p-name'>{esc(b['penghuni'].nama)}</span>",
            "kamar": kamar_badge(b["kamar"].nomor, b["properti"].warna),
            "mulai": fmt_tgl(b["penyewaan"].mulai),
            "akhir": (fmt_tgl(b["penyewaan"].akhir_rencana) if b["penyewaan"].akhir_rencana
                      else "<span style='color:#6B655A'>Berlangsung terus</span>"),
            "harga": fmt_rupiah(b["penyewaan"].harga_sewa_bulan),
            "status": pill(b["status"]),
        } for b in baris]
        render_table(kolom, rows)
        if not rows:
            st.info("Belum ada penyewaan untuk filter ini.")

        if baris:
            with st.container(border=True):
                aktif_baris = [b for b in baris if b["aktif"]]
                pilih = st.selectbox("Pilih penyewaan untuk diakhiri", aktif_baris or baris,
                                     format_func=lambda b: (f"{b['penghuni'].nama} · Kamar {b['kamar'].nomor} "
                                                            f"· mulai {fmt_tgl(b['penyewaan'].mulai)}"),
                                     key="sw_pilih")
                ket = (f"{pilih['penghuni'].nama} · Kamar {pilih['kamar'].nomor} · "
                       f"{fmt_rupiah(pilih['penyewaan'].harga_sewa_bulan)}/bulan")
                if pilih["aktif"] and st.button("Buka Pengakhiran Penyewaan", key="sw_btn"):
                    dialog_akhiri(factory, pilih["penyewaan"].id, ket)
                elif not pilih["aktif"]:
                    st.caption("Penyewaan ini sudah selesai. Buat penyewaan baru untuk periode berikutnya (BR-05).")
