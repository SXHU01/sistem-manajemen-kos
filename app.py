# -*- coding: utf-8 -*-
"""KosManage — aplikasi admin dua properti kos (PRD v1.1, Design System v2.4).

Jalankan: streamlit run app.py
Login default: admin / kosmanage123  (ubah lewat env KOSMANAGE_ADMIN_USER / KOSMANAGE_ADMIN_PASS)
"""
import streamlit as st

from controllers import auth as c_auth
from database.db import backup_harian, init_db
from utils.format import sekarang
from utils import notify
from utils.notify import render_lonceng
from utils.theme import inject_theme

st.set_page_config(page_title="KosManage", page_icon="🏨", layout="wide",
                   initial_sidebar_state="expanded")
inject_theme()


@st.cache_resource(show_spinner="Menyiapkan database...")
def sumber_data():
    engine, factory = init_db()
    backup_harian(engine)  # FR-18: backup harian otomatis, retensi 30
    return engine, factory


def halaman_login(factory):
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
        st.markdown("<div style='display:flex;align-items:center;gap:12px'>"
                    "<div style='width:44px;height:44px;border-radius:10px;background:#2E2A24;color:#FBF9F3;"
                    "display:flex;align-items:center;justify-content:center;font-weight:800'>KM</div>"
                    "<div><div style='font-weight:800;font-size:22px'>KosManage</div>"
                    "<div style='color:#6B655A;font-size:13px'>Sistem Pengelola Dua Properti Kos</div>"
                    "</div></div>", unsafe_allow_html=True)
        with st.form("form_login", border=True):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Masuk", type="primary", use_container_width=True)
            if submitted:
                with factory() as sess:
                    ok, pesan = c_auth.login(sess, username.strip(), password)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["admin_user"] = username.strip()
                    st.session_state.last_active = sekarang()
                    st.rerun()
                st.error(pesan)  # error di bawah field-nya (PRD usability)
        st.caption("Sesi berakhir otomatis setelah 60 menit tidak aktif. "
                   "Lima kali gagal login mengunci akun selama 5 menit.")


def sidebar(factory):
    with st.sidebar:
        st.markdown("<div style='display:flex;align-items:center;gap:10px;padding:4px 0 8px'>"
                    "<div style='width:36px;height:36px;border-radius:9px;background:#2E2A24;color:#FBF9F3;"
                    "display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px'>KM</div>"
                    "<div><div style='font-weight:800;font-size:17px'>KosManage</div>"
                    "<div style='color:#6B655A;font-size:11px'>Sistem Pengelola Kos</div></div></div>",
                    unsafe_allow_html=True)
        # Pemilih properti: satu tempat, selalu terlihat (v2.4: Dua properti)
        with factory() as sess:
            from database import models as M
            properti_list = list(sess.query(M.Properti).order_by(M.Properti.id).all())
        pilih = st.selectbox("PILIH PROPERTI", properti_list,
                             format_func=lambda p: f"● {p.nama}",
                             key="pemilih_properti")
        st.session_state["properti_aktif_id"] = pilih.id
        st.session_state["properti_aktif_nama"] = pilih.nama
        render_lonceng()
        st.caption(f"Masuk sebagai **{st.session_state.get('admin_user', 'admin')}** · Admin Pengelola")
        if st.button("Keluar", use_container_width=True):
            st.session_state["logged_in"] = False
            notify.toast("Anda telah keluar.", "info")
            st.rerun()


def utama():
    engine, factory = sumber_data()

    # FR-01: halaman privat tidak dapat diakses tanpa sesi valid
    if not st.session_state.get("logged_in"):
        halaman_login(factory)
        st.stop()

    # FR-02: sesi idle 60 menit berakhir
    if c_auth.sesi_kadaluarsa(st.session_state.get("last_active")):
        st.session_state["logged_in"] = False
        notify.toast("Sesi berakhir setelah 60 menit tidak aktif. Silakan masuk kembali.", "warn")
        st.stop()
    st.session_state.last_active = sekarang()

    sidebar(factory)

    import pages.dashboard, pages.properti, pages.kamar, pages.penghuni
    import pages.penyewaan, pages.tagihan, pages.pembayaran, pages.riwayat, pages.laporan

    nav = st.navigation([
        st.Page(lambda: pages.dashboard.render(factory), title="Dashboard", icon="📊",
                default=True, url_path="dashboard"),
        st.Page(lambda: pages.properti.render(factory), title="Properti", icon="🏠", url_path="properti"),
        st.Page(lambda: pages.kamar.render(factory), title="Kamar", icon="🚪", url_path="kamar"),
        st.Page(lambda: pages.penghuni.render(factory), title="Penghuni", icon="👥", url_path="penghuni"),
        st.Page(lambda: pages.penyewaan.render(factory), title="Penyewaan", icon="🔗", url_path="penyewaan"),
        st.Page(lambda: pages.tagihan.render(factory), title="Tagihan", icon="🧾", url_path="tagihan"),
        st.Page(lambda: pages.pembayaran.render(factory), title="Pembayaran", icon="💳", url_path="pembayaran"),
        st.Page(lambda: pages.riwayat.render(factory), title="Riwayat", icon="🗂️", url_path="riwayat"),
        st.Page(lambda: pages.laporan.render(factory), title="Laporan", icon="📈", url_path="laporan"),
    ])
    nav.run()


if __name__ == "__main__":
    utama()
