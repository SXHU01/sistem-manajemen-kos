# -*- coding: utf-8 -*-
"""Pesan sistem sesuai Design System v2.4 Bagian 7.

Tiga jalur, tanpa banner tetap:
- toast sesaat tepat setelah aksi  -> st.toast
- pesan tertunda                   -> lonceng notifikasi (angka hitung) di sidebar
- validasi                         -> selalu di bawah field-nya (ditangani di views/controllers)
"""
import streamlit as st
from utils.format import sekarang


def toast(pesan: str, tipe: str = "ok"):
    """Konfirmasi sesaat setelah aksi berhasil."""
    ikon = {"ok": "✅", "info": "ℹ️", "warn": "⚠️", "dgr": "🚨"}.get(tipe, "ℹ️")
    st.toast(pesan, icon=ikon)


def tambah_notifikasi(pesan: str, tipe: str = "info"):
    """Masuk lonceng dengan angka hitung; tampil sampai admin membukanya."""
    daftar = st.session_state.setdefault("notifikasi", [])
    daftar.insert(0, {"waktu": sekarang().strftime("%d %b %H:%M"), "pesan": pesan, "tipe": tipe})
    del daftar[30:]


def jumlah_notifikasi() -> int:
    return len(st.session_state.get("notifikasi", []))


def render_lonceng():
    """Popover lonceng di sidebar: angka merah = jumlah pesan belum dibaca."""
    daftar = st.session_state.get("notifikasi", [])
    n = len(daftar)
    label = f"🔔 {n}" if n else "🔔"
    with st.sidebar.popover(label, use_container_width=True):
        if not daftar:
            st.caption("Tidak ada pesan tertunda. Hasil proses massal dan pengingat internal muncul di sini.")
        for item in daftar:
            st.markdown(
                f"<div class='notif-item'><b>{item['waktu']}</b> — {item['pesan']}</div>",
                unsafe_allow_html=True,
            )
        if daftar and st.button("Tandai sudah dibaca", use_container_width=True):
            st.session_state["notifikasi"] = []
            st.rerun()
