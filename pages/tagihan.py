# -*- coding: utf-8 -*-
"""Tagihan (US-07, FR-10) — tabel 6 kolom sama dengan dashboard; tagihan massal lewat dialog."""
import streamlit as st

from controllers import tagihan as c_tagihan
from pages._shared import dialog_catat_pembayaran
from database import models as M
from utils import notify
from utils.format import awal_bulan, fmt_periode, fmt_rupiah, fmt_tgl, hari_ini, tambah_bulan
from utils.ui import esc, kamar_badge, meta, paginate, render_pager, render_table


@st.dialog("Buat Tagihan Massal", width="small")
def dialog_buat_massal(factory):
    """FR-10: sekali proses untuk semua penyewaan aktif; dilewati dilaporkan (BR-11/BR-12)."""
    with factory() as sess:
        today = hari_ini()
        pilihan = [tambah_bulan(awal_bulan(today), -1), awal_bulan(today), tambah_bulan(awal_bulan(today), 1)]
        periode = st.selectbox("Periode tagihan", pilihan,
                               format_func=lambda d: fmt_periode(d), index=1)
        st.caption("Tagihan dibuat untuk semua penyewaan aktif dalam rentang sewa. "
                   "Yang sudah punya tagihan periode ini dilewati dan dilaporkan.")
        err = ""
        if st.button("Buat Tagihan Sekarang", type="primary", use_container_width=True):
            try:
                hasil = c_tagihan.buat_massal(sess, periode, today)
            except Exception as e:  # rollback penuh sudah dilakukan di controller
                err = f"Proses gagal, tidak ada tagihan dibuat: {e}"
            else:
                if hasil["dibuat"]:
                    notify.toast(f"{hasil['dibuat']} tagihan {fmt_periode(periode)} dibuat.")
                if hasil["dilewati"]:
                    daftar = "; ".join(f"{n} ({a})" for n, a in hasil["dilewati"][:5])
                    notify.tambah_notifikasi(f"Tagihan {fmt_periode(periode)}: "
                                             f"{hasil['dibuat']} dibuat, {len(hasil['dilewati'])} dilewati — {daftar}")
                    st.toast(f"{len(hasil['dilewati'])} dilewati. Lihat lonceng untuk rinciannya.", icon="🔔")
                st.rerun()
        if err:
            st.error(err)


def render(factory):
    with factory() as sess:
        today = hari_ini()
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        m0 = awal_bulan(today)

        c1, c2, c3, ca = st.columns([1.4, 1.4, 1.4, 1.9])
        pilih_prop = c1.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  key="tg_prop")
        pilih_status = c2.selectbox("Status", [None, "Belum dibayar", "Sebagian", "Lunas", "Menunggak"],
                                    format_func=lambda s: "Semua status" if s is None else s,
                                    key="tg_status")
        periode_f = c3.selectbox("Periode", [None] + [tambah_bulan(m0, -i) for i in range(0, 4)],
                                 format_func=lambda d: "Semua periode" if d is None else fmt_periode(d),
                                 key="tg_periode")
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("🧾 Buat Tagihan", type="primary", use_container_width=True):
                dialog_buat_massal(factory)

        baris = c_tagihan.daftar(sess, status_filter=pilih_status,
                                 periode=periode_f,
                                 properti_id=pilih_prop.id if pilih_prop else None, today=today)
        r = c_tagihan.ringkasan(baris)
        st.subheader("Daftar tagihan")
        st.markdown(f"<div class='meta-line'>{meta(**{'tagihan': r['jumlah'], 'perlu perhatian': r['perhatian']})} "
                    f"&mdash; riwayat pembayaran per tagihan ada di detail baris</div>",
                    unsafe_allow_html=True)

        kolom = [
            {"label": "PENGHUNI", "key": "penghuni", "width": "24%"},
            {"label": "KAMAR", "key": "kamar", "width": "16%"},
            {"label": "PERIODE", "key": "periode", "width": "14%"},
            {"label": "TOTAL", "key": "total", "num": True, "width": "15%"},
            {"label": "SISA", "key": "sisa", "num": True, "width": "15%"},
            {"label": "STATUS", "key": "status", "width": "16%"},
        ]

        def buat_rows(pasangan):
            pil = {"Menunggak": "dgr", "Sebagian": "wrn", "Belum dibayar": "cem", "Lunas": "ok"}
            out = []
            for b in pasangan:
                t = b["tagihan"]
                telat = (today - t.jatuh_tempo).days
                sub = f"<div class='p-sub'>Terlambat {telat} Hari</div>" if telat > 0 else ""
                out.append({
                    "penghuni": f"<div class='p-name'>{esc(b['penghuni'].nama)}</div>{sub}",
                    "kamar": kamar_badge(t.penyewaan.kamar.nomor, b["properti"].warna),
                    "periode": fmt_periode(t.periode),
                    "total": fmt_rupiah(t.total),
                    "sisa": fmt_rupiah(b["sisa"]) if b["sisa"] else "<span style='color:#6B655A'>Rp 0</span>",
                    "status": f"<span class='pill {pil[b['status']]}'><span class='bdot'></span>{esc(b['status'])}</span>",
                })
            return out

        potongan, cur, pages, total = paginate(buat_rows(baris), "tagihan")
        ada = render_table(kolom, potongan)
        render_pager("tagihan")
        if not ada:
            st.info("Tidak ada tagihan yang cocok dengan filter.")

        # --- Detail baris: total, riwayat pembayaran, ID tagihan ---
        with st.container(border=True):
            pilih = st.selectbox("Lihat detail tagihan", baris,
                                 format_func=lambda b: (f"{b['penghuni'].nama} · Kamar {b['kamar'].nomor} · "
                                                        f"{fmt_periode(b['tagihan'].periode)} · sisa {fmt_rupiah(b['sisa'])}"),
                                 key="tg_detail")
            t = pilih["tagihan"]
            st.markdown(
                f"**ID tagihan:** TGT-{t.id:04d} · **Total:** {fmt_rupiah(t.total)} · "
                f"**Sisa:** {fmt_rupiah(pilih['sisa'])} · **Jatuh tempo:** {fmt_tgl(t.jatuh_tempo)}"
            )
            if t.pembayaran:
                for p in t.pembayaran:
                    ikon = "✅" if p.status == "Valid" else "🚫"
                    st.markdown(f"{ikon} {fmt_rupiah(p.nominal)} · {p.metode} · "
                                f"bayar {fmt_periode(p.tanggal_bayar)} · {p.status}"
                                + (f" — {p.alasan_batal}" if p.alasan_batal else ""))
            else:
                st.caption("Belum ada pembayaran untuk tagihan ini.")
            if pilih["sisa"] > 0 and st.button("💵 Catat Pembayaran untuk tagihan ini"):
                dialog_catat_pembayaran(factory)
