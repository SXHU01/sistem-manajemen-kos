# -*- coding: utf-8 -*-
"""Pembayaran (US-08/US-09, FR-12..14) — tabel 6 kolom; catat & batal lewat dialog."""
import streamlit as st

from controllers import pembayaran as c_pembayaran
from pages._shared import dialog_batal_pembayaran, dialog_catat_pembayaran
from database import models as M
from utils.format import awal_bulan, fmt_periode, fmt_rupiah, fmt_tgl, hari_ini
from utils.ui import esc, kamar_badge, meta, paginate, pill, render_pager, render_table


def render(factory):
    with factory() as sess:
        today = hari_ini()
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        penghuni_list = list(sess.query(M.Penghuni).order_by(M.Penghuni.nama).all())

        c1, c2, c3, ca = st.columns([1.6, 1.6, 1.6, 1.8])
        pilih_prop = c1.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  key="pb_prop")
        pilih_pg = c2.selectbox("Penghuni", [None] + penghuni_list,
                                format_func=lambda p: "Semua penghuni" if p is None else p.nama,
                                key="pb_pg")
        bulan_f = c3.selectbox("Bulan bayar", [None, "Bulan berjalan", "Bulan lalu"],
                               format_func=lambda s: "Semua bulan" if s is None else s,
                               key="pb_bulan")
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("💵 Catat Pembayaran", type="primary", use_container_width=True):
                dialog_catat_pembayaran(factory)

        baris = c_pembayaran.daftar(sess,
                                    properti_id=pilih_prop.id if pilih_prop else None,
                                    penghuni_id=pilih_pg.id if pilih_pg else None)
        if bulan_f == "Bulan berjalan":
            baris = [b for b in baris if b["pembayaran"].tanggal_bayar >= awal_bulan(today)]
        elif bulan_f == "Bulan lalu":
            from utils.format import tambah_bulan
            awal_lalu = tambah_bulan(awal_bulan(today), -1)
            baris = [b for b in baris if awal_lalu <= b["pembayaran"].tanggal_bayar < awal_bulan(today)]

        r = c_pembayaran.ringkasan_bulan(baris, awal_bulan(today), today)
        st.subheader("Riwayat pembayaran")
        st.markdown(f"<div class='meta-line'><b>{fmt_rupiah(r['total'])}</b> pembayaran valid bulan berjalan "
                    f"&middot; <b>{r['jumlah']}</b> transaksi &mdash; pembatalan tetap tampil di riwayat, tidak dihitung</div>",
                    unsafe_allow_html=True)

        kolom = [
            {"label": "TANGGAL BAYAR", "key": "tanggal", "width": "15%"},
            {"label": "PENGHUNI", "key": "penghuni", "width": "22%"},
            {"label": "KAMAR", "key": "kamar", "width": "15%"},
            {"label": "NOMINAL", "key": "nominal", "num": True, "width": "16%"},
            {"label": "METODE", "key": "metode", "width": "12%"},
            {"label": "STATUS", "key": "status", "width": "20%"},
        ]
        rows = [{
            "tanggal": fmt_tgl(b["pembayaran"].tanggal_bayar),
            "penghuni": f"<span class='p-name'>{esc(b['penghuni'].nama)}</span>"
                        f"<div class='pr-sub'>{fmt_periode(b['tagihan'].periode)}</div>",
            "kamar": kamar_badge(b["kamar"].nomor, b["properti"].warna),
            "nominal": fmt_rupiah(b["pembayaran"].nominal),
            "metode": esc(b["pembayaran"].metode),
            "status": pill(b["pembayaran"].status)
                      + (f"<div class='pr-sub'>{esc(b['pembayaran'].alasan_batal)}</div>"
                         if b["pembayaran"].alasan_batal else ""),
        } for b in baris]
        potongan, cur, pages, total = paginate(rows, "pembayaran")
        ada = render_table(kolom, potongan)
        render_pager("pembayaran")
        if not ada:
            st.info("Tidak ada pembayaran untuk filter ini.")

        # --- Koreksi: batalkan dengan alasan wajib (BR-19) ---
        if baris:
            with st.container(border=True):
                valid_baris = [b for b in baris if b["pembayaran"].status == "Valid"]
                if not valid_baris:
                    st.caption("Tidak ada pembayaran valid untuk dibatalkan pada filter ini.")
                    return
                pilih = st.selectbox("Pilih pembayaran untuk dibatalkan", valid_baris,
                                     format_func=lambda b: (f"{fmt_tgl(b['pembayaran'].tanggal_bayar)} · "
                                                            f"{b['penghuni'].nama} · {fmt_rupiah(b['pembayaran'].nominal)}"),
                                     key="pb_pilih")
                ket = (f"{fmt_tgl(pilih['pembayaran'].tanggal_bayar)} · {pilih['penghuni'].nama} · "
                       f"Kamar {pilih['kamar'].nomor} · {fmt_rupiah(pilih['pembayaran'].nominal)}")
                if st.button("Buka Pembatalan", key="pb_btn"):
                    dialog_batal_pembayaran(factory, pilih["pembayaran"].id, ket)
