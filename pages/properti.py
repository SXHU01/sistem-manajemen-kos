# -*- coding: utf-8 -*-
"""Properti (US-03, FR-04, BR-01) — tepat dua kartu, tanpa tambah/hapus."""
import streamlit as st

from database import models as M
from utils import notify
from utils.format import fmt_rupiah, hari_ini
from utils.ui import esc, page_header


@st.dialog("Ubah Properti", width="small")
def dialog_ubah_properti(factory, properti_id: int, nama: str, alamat: str):
    """FR-04: hanya nama dan alamat yang boleh diubah."""
    with factory() as sess:
        p = sess.get(M.Properti, properti_id)
        nama_baru = st.text_input("Nama properti", value=nama)
        alamat_baru = st.text_area("Alamat", value=alamat)
        err = ""
        if st.button("Simpan", type="primary", use_container_width=True):
            if not nama_baru.strip():
                err = "Nama properti wajib diisi."
            else:
                p.nama, p.alamat = nama_baru.strip(), alamat_baru.strip()
                sess.commit()
                notify.toast(f"Data properti {p.nama} tersimpan.")
                st.rerun()
        if err:
            st.error(err)


def render(factory):
    page_header("Properti",
                "Tepat dua properti &middot; perubahan nama tersimpan di seluruh modul")
    with factory() as sess:
        today = hari_ini()
        daftar = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        cols = st.columns(len(daftar))
        for col, p in zip(cols, daftar):
            with col:
                kamar = list(p.kamar)
                terisi = sum(1 for k in kamar if M.status_kamar(k, today) == "Terisi")
                kosong = sum(1 for k in kamar if M.status_kamar(k, today) == "Kosong")
                harga_rata = round(sum(k.harga_sewa for k in kamar) / len(kamar)) if kamar else 0
                st.markdown(
                    f"""
<div style="background:#FBF9F3;border:1px solid #DDD8CB;border-radius:12px;padding:24px">
  <div style="display:flex;align-items:center;gap:10px">
    <span class='kd kd-{p.warna}'></span>
    <b style="font-size:18px">{esc(p.nama)}</b>
  </div>
  <div class="pr-sub" style="margin:6px 0 14px">{esc(p.alamat)}</div>
  <div style="font-size:14px;line-height:22px"><b>{len(kamar)} kamar</b> &middot; {terisi} terisi &middot; {kosong} kosong</div>
  <div class="pr-sub">Harga sewa {fmt_rupiah(harga_rata)} per bulan (rata-rata)</div>
</div>""",
                    unsafe_allow_html=True,
                )
                if st.button("Ubah", key=f"ubah_p_{p.id}", use_container_width=True):
                    dialog_ubah_properti(factory, p.id, p.nama, p.alamat)
        st.caption("Sesuai aturan bisnis BR-01: properti tidak dapat ditambah, dihapus, atau dinonaktifkan.")
