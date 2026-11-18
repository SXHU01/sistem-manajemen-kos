# -*- coding: utf-8 -*-
"""Laporan (US-11, FR-16/17) — tab Pendapatan/Tunggakan + satu grafik tren + Unduh CSV.

Grafik hanya ada di halaman ini (v2.4: tren dan perbandingan target = tugas Laporan).
Dua warna properti tetap: espresso / kuning tua (palet grafik v2.4).
"""
import streamlit as st

from controllers import laporan as c_laporan
from database import models as M
from utils.format import awal_bulan, fmt_periode, fmt_rupiah, fmt_tgl, hari_ini, tambah_bulan
from utils.ui import esc, kamar_badge, render_table

WARNA_PROPERTI = {"Griya Melati": "#2E2A24", "Wisma Cendana": "#D98E04"}


def render(factory):
    with factory() as sess:
        today = hari_ini()
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())

        c1, c2, ca = st.columns([2.2, 2.2, 1.8])
        tab_pendapatan = c1.segmented_control("Laporan", ["Pendapatan", "Tunggakan"], default="Pendapatan",
                                              key="lap_tab") if hasattr(st, "segmented_control") else None
        if tab_pendapatan is None:
            tab_pendapatan = c1.radio("Laporan", ["Pendapatan", "Tunggakan"], horizontal=True,
                                      key="lap_tab_radio")
        bulan_f = c2.selectbox("Periode", [awal_bulan(today)] + [tambah_bulan(awal_bulan(today), -i)
                                                                for i in range(1, 4)],
                               format_func=lambda d: fmt_periode(d), key="lap_periode")
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)

        st.subheader("Tren pendapatan · 6 bulan terakhir")
        bulan_labels, seri = c_laporan.tren_pendapatan(sess, n_bulan=6, today=today)
        _grafik_tren(bulan_labels, seri, properti_list)

        if tab_pendapatan == "Pendapatan":
            _tabel_pendapatan(sess, c_laporan, bulan_f, today)
        else:
            _tabel_tunggakan(sess, c_laporan, today)


def _grafik_tren(bulan_labels, seri, properti_list):
    try:
        import plotly.graph_objects as go
        fig = go.Figure()
        for p in properti_list:
            nama = p.nama
            if nama in seri:
                fig.add_bar(name=nama, x=bulan_labels, y=seri[nama],
                            marker_color=WARNA_PROPERTI.get(nama, "#9A9484"))
        fig.update_layout(barmode="group", height=300, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="#FBF9F3", paper_bgcolor="#FBF9F3",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1),
                          font=dict(family="Plus Jakarta Sans, sans-serif", color="#26221C"))
        fig.update_yaxes(tickformat=",", gridcolor="#DDD8CB")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        # Cadangan: grafik CSS sederhana dengan palet yang sama
        maks = max(max(v) for v in seri.values()) or 1
        for nama, nilai in seri.items():
            warna = WARNA_PROPERTI.get(nama, "#9A9484")
            st.caption(nama)
            kolom = st.columns(len(nilai))
            for col, v in zip(kolom, nilai):
                col.markdown(
                    f"<div style='background:{warna};height:{max(8, int(v / maks * 160))}px;"
                    f"border-radius:6px 6px 0 0'></div>", unsafe_allow_html=True)


def _tabel_pendapatan(sess, c_laporan, bulan_f, today):
    import calendar
    awal = bulan_f
    akhir = awal.replace(day=calendar.monthrange(awal.year, awal.month)[1])
    baris = c_laporan.laporan_pendapatan(sess, awal, akhir)
    st.markdown(f"<div class='meta-line'>berdasarkan tanggal bayar &middot; {fmt_tgl(awal)} — {fmt_tgl(akhir)}</div>",
                unsafe_allow_html=True)
    kolom = [
        {"label": "PROPERTI", "key": "properti", "width": "30%"},
        {"label": "PERIODE", "key": "periode", "width": "20%"},
        {"label": "PEMBAYARAN VALID", "key": "total", "num": True, "width": "25%"},
        {"label": "JUMLAH PEMBAYARAN", "key": "jumlah", "num": True, "width": "25%"},
    ]
    rows = [{
        "properti": (f"<span class='kd kd-{b['properti'].warna}'></span> {esc(b['properti'].nama)}"
                     if b["properti"] else "Total"),
        "periode": fmt_periode(awal),
        "total": fmt_rupiah(b["total"]),
        "jumlah": str(b["jumlah"]),
    } for b in baris]
    total_row = rows[-1]
    render_table(kolom, rows[:-1], total_row=total_row)

    csv_rows = [[b["properti"].nama if b["properti"] else "Total", fmt_periode(awal),
                 fmt_rupiah(b["total"]), str(b["jumlah"])] for b in baris]
    csv = c_laporan.csv_laporan(f"Laporan Pendapatan {fmt_periode(awal)}",
                                ["Properti", "Periode", "Pembayaran Valid", "Jumlah Pembayaran"], csv_rows)
    st.download_button("⬇️ Unduh CSV Pendapatan", csv,
                       file_name=f"laporan-pendapatan-{fmt_periode(awal).replace(' ', '-')}.csv",
                       mime="text/csv")


def _tabel_tunggakan(sess, c_laporan, today):
    baris, total = c_laporan.laporan_tunggakan(sess, today)
    st.markdown(f"<div class='meta-line'>sisa tagihan dengan jatuh tempo sudah lewat &middot; "
                f"per hari ini</div>", unsafe_allow_html=True)
    kolom = [
        {"label": "PENGHUNI", "key": "penghuni", "width": "24%"},
        {"label": "KAMAR", "key": "kamar", "width": "16%"},
        {"label": "PERIODE", "key": "periode", "width": "14%"},
        {"label": "JATUH TEMPO", "key": "jatuh_tempo", "width": "16%"},
        {"label": "TERLAMBAT", "key": "terlambat", "num": True, "width": "12%"},
        {"label": "SISA", "key": "sisa", "num": True, "width": "18%"},
    ]
    rows = [{
        "penghuni": f"<span class='p-name'>{esc(b['penghuni'].nama)}</span>",
        "kamar": kamar_badge(b["kamar"].nomor, b["properti"].warna),
        "periode": fmt_periode(b["periode"]),
        "jatuh_tempo": fmt_tgl(b["jatuh_tempo"]),
        "terlambat": f"{b['hari_terlambat']} hari",
        "sisa": f"<span style='color:#B42318'>{fmt_rupiah(b['sisa'])}</span>",
    } for b in baris]
    render_table(kolom, rows, total_row={"penghuni": "Total", "kamar": "", "periode": "",
                                         "jatuh_tempo": "", "terlambat": "",
                                         "sisa": fmt_rupiah(total)} if rows else None)
    if not rows:
        st.info("Tidak ada tunggakan. Semua tagihan yang lewat jatuh tempo sudah lunas.")

    csv_rows = [[b["penghuni"].nama, f"Kamar {b['kamar'].nomor}", b["properti"].nama,
                 fmt_periode(b["periode"]), fmt_tgl(b["jatuh_tempo"]),
                 f"{b['hari_terlambat']} hari", fmt_rupiah(b["sisa"])] for b in baris]
    csv_rows.append(["Total", "", "", "", "", "", fmt_rupiah(total)])
    csv = c_laporan.csv_laporan("Laporan Tunggakan KosManage",
                                ["Penghuni", "Kamar", "Properti", "Periode",
                                 "Jatuh Tempo", "Terlambat", "Sisa"], csv_rows)
    st.download_button("⬇️ Unduh CSV Tunggakan", csv,
                       file_name=f"laporan-tunggakan-{fmt_tgl(today).replace(' ', '-')}.csv",
                       mime="text/csv")
