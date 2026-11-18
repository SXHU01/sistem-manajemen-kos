# -*- coding: utf-8 -*-
"""Penghuni (US-05, FR-07) — tabel 5 kolom; ID & catatan tampil di sel nama (v2.4)."""
import streamlit as st

from controllers import penghuni as c_penghuni
from database import models as M
from utils import notify
from utils.format import fmt_tgl
from utils.ui import esc, kamar_badge, meta, paginate, pill, render_pager, render_table


@st.dialog("Tambah Penghuni", width="small")
def dialog_tambah(factory):
    with factory() as sess:
        nama = st.text_input("Nama lengkap", key="dlg_pg_nama")
        telepon = st.text_input("Nomor telepon", key="dlg_pg_telp")
        nomor_identitas = st.text_input("Nomor identitas (KTP/SIM)", key="dlg_pg_id")
        catatan = st.text_area("Catatan (opsional)", key="dlg_pg_catatan")
        err = ""
        if st.button("Simpan Penghuni", type="primary", use_container_width=True):
            ok, pesan = c_penghuni.buat(sess, nama, telepon, nomor_identitas, catatan)
            if ok:
                notify.toast(f"Penghuni {nama.strip()} ditambahkan.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)


@st.dialog("Ubah Penghuni", width="small")
def dialog_ubah(factory, penghuni_id: int, keterangan: str):
    with factory() as sess:
        p = sess.get(M.Penghuni, penghuni_id)
        st.caption(keterangan)
        nama = st.text_input("Nama lengkap", value=p.nama)
        telepon = st.text_input("Nomor telepon", value=p.telepon)
        nomor_identitas = st.text_input("Nomor identitas (KTP/SIM)", value=p.nomor_identitas)
        catatan = st.text_area("Catatan (opsional)", value=p.catatan)
        c1, c2 = st.columns(2)
        err = ""
        if c1.button("Simpan", type="primary", use_container_width=True):
            ok, pesan = c_penghuni.ubah(sess, penghuni_id, nama, telepon, nomor_identitas, catatan)
            if ok:
                notify.toast("Data penghuni diperbarui.")
                st.rerun()
            err = pesan
        if err:
            st.error(err)
        if c2.button("Hapus", use_container_width=True):
            ok, pesan = c_penghuni.hapus(sess, penghuni_id)
            if ok:
                notify.toast("Penghuni dihapus.")
                st.rerun()
            st.error(pesan)


def render(factory):
    with factory() as sess:
        properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())

        c1, c2, ca = st.columns([2.2, 2.2, 1.8])
        cari = c1.text_input("Cari nama / telepon", key="pg_cari")
        pilih_prop = c2.selectbox("Properti", [None] + properti_list,
                                  format_func=lambda p: "Semua properti" if p is None else p.nama,
                                  key="pg_prop")
        with ca:
            st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
            if st.button("➕ Tambah Penghuni", type="primary", use_container_width=True):
                dialog_tambah(factory)

        baris = c_penghuni.daftar(sess, cari=cari,
                                  properti_id=pilih_prop.id if pilih_prop else None)
        aktif = sum(1 for b in baris if b["kamar"] is not None)
        st.subheader("Daftar penghuni")
        st.markdown(f"<div class='meta-line'>{meta(**{'penghuni': len(baris), 'menyewa': aktif})}</div>",
                    unsafe_allow_html=True)

        kolom = [
            {"label": "NAMA", "key": "nama", "width": "34%"},
            {"label": "TELEPON", "key": "telepon", "width": "18%"},
            {"label": "KAMAR AKTIF", "key": "kamar", "width": "18%"},
            {"label": "MULAI SEWA", "key": "mulai", "width": "14%"},
            {"label": "STATUS", "key": "status", "width": "16%"},
        ]
        rows = [{
            "nama": f"<span class='p-name'>{esc(b['penghuni'].nama)}</span>"
                    f"<div class='pr-sub'>{esc(b['penghuni'].telepon or '—')}"
                    + (f" · {esc(b['penghuni'].catatan)}" if b["penghuni"].catatan else "") + "</div>",
            "telepon": esc(b["penghuni"].telepon or "—"),
            "kamar": kamar_badge(b["kamar"].nomor, b["kamar"].properti.warna) if b["kamar"]
                     else "<span style='color:#6B655A'>&mdash;</span>",
            "mulai": fmt_tgl(b["mulai"]) if b["mulai"] else "—",
            "status": pill("Berlangsung") if b["kamar"] else pill("Belum menyewa"),
        } for b in baris]
        potongan, cur, pages, total = paginate(rows, "penghuni")
        ada = render_table(kolom, potongan)
        render_pager("penghuni")
        if not ada:
            st.info("Tidak ada penghuni yang cocok dengan filter.")

        if baris:
            with st.container(border=True):
                pilih = st.selectbox("Pilih penghuni untuk diubah", baris,
                                     format_func=lambda b: b["penghuni"].nama, key="pg_pilih")
                ket = (pilih["penghuni"].nama
                       + (f" · menyewa Kamar {pilih['kamar'].nomor}" if pilih["kamar"] else "")
                       + ("" if pilih["punya_riwayat"] else " · belum punya riwayat sewa (bisa dihapus)"))
                if st.button("Buka Ubah Penghuni", key="pg_btn"):
                    dialog_ubah(factory, pilih["penghuni"].id, ket)
