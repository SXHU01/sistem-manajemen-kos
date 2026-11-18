# -*- coding: utf-8 -*-
"""Riwayat transaksi (US-10, FR-15) — filter properti/penghuni/rentang tanggal + CSV (FR-17)."""
import streamlit as st

from controllers import laporan as c_laporan
from controllers import pembayaran as c_pembayaran
from database import models as M
from utils.format import awal_bulan, fmt_periode, fmt_rupiah, fmt_tgl, hari_ini
from utils.ui import esc, kamar_badge, paginate, pill, render_pager, render_table


def render(factory):
    with factory() as sess:
        today = hari_ini()
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        penghuni_list = list(sess.query(M.Penghuni).order_by(M.Penghuni.nama).all())

        c1, c2, c3, c4 = st.columns(4)
        pilih_prop = c1.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  key="rw_prop")
        pilih_pg = c2.selectbox("Penghuni", [None] + penghuni_list,
                                format_func=lambda p: "Semua penghuni" if p is None else p.nama,
                                key="rw_pg")
        dari = c3.date_input("Dari tanggal", value=awal_bulan(today), format="DD/MM/YYYY", key="rw_dari")
        sampai = c4.date_input("Sampai tanggal", value=today, format="DD/MM/YYYY", key="rw_sampai")

        baris = c_pembayaran.daftar(sess,
                                    properti_id=pilih_prop.id if pilih_prop else None,
                                    penghuni_id=pilih_pg.id if pilih_pg else None,
                                    dari=dari, sampai=sampai)
        total_valid = sum(b["pembayaran"].nominal for b in baris if b["pembayaran"].status == "Valid")
        st.subheader("Riwayat transaksi")
        st.markdown(f"<div class='meta-line'><b>{len(baris)}</b> transaksi &middot; "
                    f"<b>{fmt_rupiah(total_valid)}</b> pembayaran valid &middot; "
                    f"{fmt_tgl(dari)} — {fmt_tgl(sampai)}</div>", unsafe_allow_html=True)

        kolom = [
            {"label": "TANGGAL", "key": "tanggal", "width": "14%"},
            {"label": "PENGHUNI", "key": "penghuni", "width": "20%"},
            {"label": "KAMAR", "key": "kamar", "width": "14%"},
            {"label": "PERIODE TAGIHAN", "key": "periode", "width": "16%"},
            {"label": "NOMINAL", "key": "nominal", "num": True, "width": "15%"},
            {"label": "STATUS", "key": "status", "width": "21%"},
        ]
        rows = [{
            "tanggal": fmt_tgl(b["pembayaran"].tanggal_bayar),
            "penghuni": esc(b["penghuni"].nama),
            "kamar": kamar_badge(b["kamar"].nomor, b["properti"].warna),
            "periode": fmt_periode(b["tagihan"].periode),
            "nominal": fmt_rupiah(b["pembayaran"].nominal),
            "status": pill(b["pembayaran"].status)
                      + (f"<div class='pr-sub'>{esc(b['pembayaran'].metode)}"
                         + (f" — {esc(b['pembayaran'].alasan_batal)}" if b["pembayaran"].alasan_batal else "")
                         + "</div>"),
        } for b in baris]
        potongan, cur, pages, total = paginate(rows, "riwayat")
        ada = render_table(kolom, potongan)
        render_pager("riwayat")
        if not ada:
            st.info("Tidak ada transaksi untuk filter ini.")

        # FR-17: CSV dengan angka & tanggal sama seperti tampilan
        csv_rows = [[fmt_tgl(b["pembayaran"].tanggal_bayar), b["penghuni"].nama,
                     f"Kamar {b['kamar'].nomor}", b["properti"].nama,
                     fmt_periode(b["tagihan"].periode), fmt_rupiah(b["pembayaran"].nominal),
                     b["pembayaran"].metode, b["pembayaran"].status]
                    for b in baris]
        csv = c_laporan.csv_laporan("Riwayat Transaksi KosManage",
                                    ["Tanggal", "Penghuni", "Kamar", "Properti",
                                     "Periode", "Nominal", "Metode", "Status"], csv_rows)
        st.download_button("⬇️ Unduh CSV", csv, file_name=f"riwayat-{fmt_tgl(dari)}-{fmt_tgl(sampai)}.csv",
                           mime="text/csv", use_container_width=True)
