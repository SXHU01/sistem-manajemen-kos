# -*- coding: utf-8 -*-
"""Dashboard (US-02, FR-03) — resep wajib Design System v2.4 Bagian 6:
3 kartu statistik -> tabel ringkas per properti -> tabel Tagihan & Jatuh Tempo.
Tanpa lencana kartu, tanpa progress bar, tanpa banner, tanpa tren (pindah ke Laporan)."""
import streamlit as st

from controllers import laporan as c_laporan
from database import models as M
from pages._shared import dialog_catat_pembayaran
from utils.format import fmt_periode, fmt_rupiah, hari_ini
from utils.ui import kamar_badge, meta, page_header, render_table, esc


def render(factory):
    today = hari_ini()
    with factory() as sess:
        # --- Baris judul: H1 + SATU tombol primer ---
        col_t, col_a = st.columns([3, 1])
        with col_t:
            page_header("Dashboard")
        with col_a:
            st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
            if st.button("💵 Catat Pembayaran", type="primary", use_container_width=True):
                dialog_catat_pembayaran(factory)

        # --- Tiga kartu statistik: label -> angka -> SATU baris meta ---
        okup = c_laporan.okupansi(sess, today)
        total_kamar = sum(o["total"] for o in okup.values())
        terisi = sum(o["terisi"] for o in okup.values())
        persen = round(terisi / total_kamar * 100) if total_kamar else 0
        pendapatan = c_laporan.pendapatan_bulan_berjalan(sess, today)
        target = c_laporan.target_pendapatan(sess)
        tg = c_laporan.tunggakan(sess, today)

        m1, m2, m3 = st.columns(3)
        m1.metric("Okupansi", f"{persen}%", f"{terisi} dari {total_kamar} kamar terisi",
                  delta_color="off")
        m2.metric(f"Pendapatan {fmt_periode(today)}", fmt_rupiah(pendapatan),
                  f"{round(pendapatan / target * 100) if target else 0}% dari target {fmt_rupiah(target)}",
                  delta_color="off")
        m3.metric("Tunggakan", fmt_rupiah(tg["total"]),
                  f"{tg['jumlah_penghuni']} penghuni menunggak", delta_color="inverse")

        # --- Tabel ringkas per properti (daftar kamar kosong = FR-03, sub-teks nama) ---
        st.subheader("Ringkasan per properti")
        kolom = [
            {"label": "PROPERTI", "key": "properti", "width": "34%"},
            {"label": "HUNIAN", "key": "hunian", "num": True, "width": "16%"},
            {"label": f"PENDAPATAN {fmt_periode(today).upper()}", "key": "pendapatan", "num": True, "width": "25%"},
            {"label": "TUNGGAKAN", "key": "tunggakan", "num": True, "width": "25%"},
        ]
        rows, total_hunian = [], [0, 0]
        for o in okup.values():
            p = o["properti"]
            total_hunian[0] += o["terisi"]
            total_hunian[1] += o["total"]
            sub = []
            if o["kamar_kosong"]:
                sub.append("Kosong: " + ", ".join(o["kamar_kosong"]))
            if o["kamar_perbaikan"]:
                sub.append("Perbaikan: " + ", ".join(o["kamar_perbaikan"]))
            t_prop = tg.get(p.id, {"total": 0})["total"]
            rows.append({
                "properti": (f"<span style='display:inline-flex;align-items:center;gap:10px'>"
                             f"<span class='kd kd-{p.warna}'></span><span><span class='p-name'>{esc(p.nama)}</span>"
                             f"<div class='pr-sub'>{esc(' · '.join(sub)) if sub else '&mdash;'}</div></span></span>"),
                "hunian": f"{o['terisi']}/{o['total']}",
                "pendapatan": fmt_rupiah(pendapatan_prop(sess, p, today)),
                "tunggakan": f"<span style='color:#B42318'>{fmt_rupiah(t_prop)}</span>" if t_prop else fmt_rupiah(0),
            })
        total_row = {
            "properti": "Total", "hunian": f"{total_hunian[0]}/{total_hunian[1]}",
            "pendapatan": fmt_rupiah(pendapatan),
            "tunggakan": fmt_rupiah(tg["total"]),
        }
        render_table(kolom, rows, total_row=total_row)

        # --- Tagihan & Jatuh Tempo: tab filter default "Perlu perhatian" ---
        st.subheader("Tagihan & Jatuh Tempo")
        semua = sess.query(M.Tagihan).join(M.Penyewaan).join(M.Kamar).join(M.Properti) \
            .order_by(M.Tagihan.jatuh_tempo).all()
        perhatian, lain = [], []
        for t in semua:
            stt = M.status_tagihan(t, today)
            sisa = M.sisa_tagihan(t)
            if stt in ("Sebagian", "Menunggak") and sisa > 0:
                perhatian.append((t, stt, sisa))
            lain.append((t, stt, sisa))
        tab1, tab2 = st.tabs([f"Perlu perhatian · {len(perhatian)}", f"Semua · {len(lain)}"])
        kolom_tag = [
            {"label": "PENGHUNI", "key": "penghuni", "width": "26%"},
            {"label": "KAMAR", "key": "kamar", "width": "18%"},
            {"label": "PERIODE", "key": "periode", "width": "16%"},
            {"label": "SISA", "key": "sisa", "num": True, "width": "16%"},
            {"label": "STATUS", "key": "status", "width": "24%"},
        ]

        def baris_tagihan(pasangan):
            pil_kelas = {"Menunggak": "dgr", "Sebagian": "wrn", "Belum dibayar": "cem", "Lunas": "ok"}
            hasil = []
            for t, stt, sisa in pasangan:
                k = t.penyewaan.kamar
                telat = (today - t.jatuh_tempo).days
                sub = f"<div class='p-sub'>Terlambat {telat} Hari</div>" if telat > 0 else ""
                hasil.append({
                    "penghuni": f"<div class='p-name'>{esc(t.penyewaan.penghuni.nama)}</div>{sub}",
                    "kamar": kamar_badge(k.nomor, k.properti.warna),
                    "periode": fmt_periode(t.periode),
                    "sisa": fmt_rupiah(sisa) if sisa else "<span style='color:#6B655A'>Rp 0</span>",
                    "status": (f"<span class='pill {pil_kelas[stt]}'><span class='bdot'></span>"
                               f"{esc(stt)}</span>"),
                })
            return hasil

        with tab1:
            render_table(kolom_tag, baris_tagihan(perhatian))
        with tab2:
            render_table(kolom_tag, baris_tagihan(list(reversed(lain))))


def pendapatan_prop(sess, properti, today):
    """Pendapatan bulan berjalan per properti (pembayaran valid, tanggal bayar)."""
    awal = today.replace(day=1)
    kamar_id = {k.id for k in properti.kamar}
    data = sess.query(M.Pembayaran).join(M.Tagihan).join(M.Penyewaan).filter(
        M.Pembayaran.status == "Valid",
        M.Pembayaran.tanggal_bayar >= awal,
        M.Pembayaran.tanggal_bayar <= today,
        M.Penyewaan.kamar_id.in_(kamar_id),
    ).all()
    return sum(p.nominal for p in data)
