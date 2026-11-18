# -*- coding: utf-8 -*-
"""Kamar (US-04, FR-05/06) — tabel 6 kolom + dialog Ubah; hapus hanya tanpa riwayat."""
import streamlit as st

from controllers import kamar as c_kamar
from database import models as M
from utils import notify
from utils.format import fmt_rupiah, hari_ini
from utils.ui import (esc, kamar_badge, meta, paginate, pill, render_pager,
                      render_table)

PROPERTI_KEY = "kamar_filter_properti"
STATUS_KEY = "kamar_filter_status"
CARI_KEY = "kamar_cari"


@st.dialog("Tambah Kamar", width="small")
def dialog_tambah(factory, pilihan_properti):
    with factory() as sess:
        prop = st.selectbox("Properti", pilihan_properti,
                            format_func=lambda p: p.nama, key="dlg_kamar_prop")
        nomor = st.text_input("Nomor kamar", key="dlg_kamar_nomor")
        tipe = st.selectbox("Tipe", ["Standar", "Suite"], key="dlg_kamar_tipe")
        harga = st.number_input("Harga sewa per bulan", min_value=0, step=50_000, key="dlg_kamar_harga")
        err = ""
        if st.button("Simpan Kamar", type="primary", use_container_width=True):
            ok, pesan = c_kamar.buat(sess, prop.id, nomor, tipe, int(harga))
            if ok:
                notify.toast(f"Kamar {nomor} ditambahkan.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)


@st.dialog("Ubah Kamar", width="small")
def dialog_ubah(factory, kamar_id: int, keterangan: str):
    """Ubah data + tandai Perbaikan (BR-21). Hapus hanya untuk kamar tanpa riwayat."""
    with factory() as sess:
        k = sess.get(M.Kamar, kamar_id)
        st.caption(keterangan)
        nomor = st.text_input("Nomor kamar", value=k.nomor)
        tipe = st.selectbox("Tipe", ["Standar", "Suite"],
                            index=["Standar", "Suite"].index(k.tipe) if k.tipe in ("Standar", "Suite") else 0)
        harga = st.number_input("Harga sewa per bulan", min_value=0, step=50_000, value=k.harga_sewa)
        perbaikan = st.checkbox("Sedang perbaikan (tidak dapat disewa)", value=k.perbaikan)
        c1, c2 = st.columns(2)
        err = ""
        if c1.button("Simpan", type="primary", use_container_width=True):
            ok, pesan = c_kamar.ubah(sess, kamar_id, nomor, tipe, int(harga), perbaikan)
            if ok:
                notify.toast(f"Kamar {nomor} diperbarui.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)
        if c2.button("Hapus", use_container_width=True):
            ok, pesan = c_kamar.hapus(sess, kamar_id)
            if ok:
                notify.toast(f"Kamar {kamar_id} dihapus.")
                st.rerun()
            st.error(pesan)


def render(factory):
    with factory() as sess:
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        properti_aktif = st.session_state.get("properti_aktif_id")

        # --- Kontrol konteks: dropdown, bukan panel filter ---
        c1, c2, c3, ca = st.columns([1.6, 1.2, 1.6, 1.6])
        pilih_prop = c1.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  index=(properti_aktif or 0) and next(
                                      (i for i, p in enumerate([None] + properti_list)
                                       if p and p.id == properti_aktif), 0),
                                  key=PROPERTI_KEY)
        pilih_status = c2.selectbox("Status", [None, "Terisi", "Kosong", "Perbaikan"],
                                    format_func=lambda s: "Semua status" if s is None else s,
                                    key=STATUS_KEY)
        cari = c3.text_input("Cari nomor / penghuni", key=CARI_KEY)
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("➕ Tambah Kamar", type="primary", use_container_width=True):
                dialog_tambah(factory, properti_list)

        baris = c_kamar.daftar(sess, properti_id=pilih_prop.id if pilih_prop else None,
                               cari=cari, filter_status=pilih_status)
        r = c_kamar.ringkasan(baris)
        # judul digambar setelah filter agar meta mengikuti filter — pola judul + meta v2.4
        st.subheader("Daftar kamar")
        st.markdown(f"<div class='meta-line'>{meta(**{'kamar': r['jumlah'], 'terisi': r['terisi'], 'kosong': r['kosong'], 'perbaikan': r['perbaikan']})} &mdash; status dihitung dari penyewaan aktif</div>",
                    unsafe_allow_html=True)

        kolom = [
            {"label": "KAMAR", "key": "kamar", "width": "16%"},
            {"label": "TIPE", "key": "tipe", "width": "12%"},
            {"label": "HARGA SEWA", "key": "harga", "num": True, "width": "16%"},
            {"label": "STATUS", "key": "status", "width": "14%"},
            {"label": "PENGHUNI", "key": "penghuni", "width": "26%"},
            {"label": "PROPERTI", "key": "properti", "width": "16%"},
        ]
        rows = [{
            "kamar": kamar_badge(b["kamar"].nomor, b["properti"].warna),
            "tipe": esc(b["kamar"].tipe),
            "harga": fmt_rupiah(b["kamar"].harga_sewa),
            "status": pill(b["status"]),
            "penghuni": f"<span class='p-name'>{esc(b['penghuni'])}</span>" if b["penghuni"] else "<span style='color:#6B655A'>&mdash;</span>",
            "properti": esc(b["properti"].nama),
        } for b in baris]

        potongan, cur, pages, total = paginate(rows, "kamar")
        ada = render_table(kolom, potongan)
        render_pager("kamar")
        if not ada:
            st.info("Tidak ada kamar yang cocok dengan filter.")

        # --- Detail baris: pilih kamar, lalu ubah (mekanisme dialog, v2.4) ---
        if baris:
            with st.container(border=True):
                pilih = st.selectbox("Pilih kamar untuk diubah",
                                     baris, format_func=lambda b: f"Kamar {b['kamar'].nomor} · {b['properti'].nama}",
                                     key="kamar_pilih_ubah")
                keterangan = (f"Kamar {pilih['kamar'].nomor} · {pilih['properti'].nama} · "
                              f"{fmt_rupiah(pilih['kamar'].harga_sewa)} · {pilih['status']}"
                              + ("" if pilih["punya_riwayat"] else " · belum punya riwayat sewa (bisa dihapus)"))
                if st.button("Buka Ubah Kamar", key="kamar_btn_ubah"):
                    dialog_ubah(factory, pilih["kamar"].id, keterangan)
