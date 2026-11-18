# -*- coding: utf-8 -*-
"""Token desain Design System v2.4 -> CSS Streamlit.

Sumber kebenaran nilai spasi: 24/48/64, maksimal 3 kartu · 2 tabel · 6 kolom · 1 tombol primer.
Selektor DOM disesuaikan untuk Streamlit modern; nilai token yang wajib dipertahankan.
"""
import streamlit as st

TOKENS_CSS = """
<style>
:root{
  --pad-card:24px;    --gap-card:24px;    --gap-sec:48px;
  --pad-page:32px 36px; --pad-td:16px 14px; --lh-meta:22px;
  --espresso:#2E2A24; --amber:#D98E04; --ink:#26221C; --muted:#6B655A;
  --line:#DDD8CB; --cement:#E9E8E3; --ok:#2F7A4F; --wrn:#9A6408; --dgr:#B42318;
}
/* Padding halaman (token --pad-page) */
[data-testid="stMainBlockContainer"]{padding-top:32px; padding-left:36px; padding-right:36px; max-width:1200px;}

/* Angka dan label tidak pernah patah baris (Bagian 6: tabel) */
td .nowrap, .stCaption, [data-testid="stMetric"]{white-space:nowrap;}
[data-testid="stMetricValue"]{font-variant-numeric:tabular-nums;}

/* Judul halaman H1 32/40, meta data 14/22 */
[data-testid="stHeading"] h1{letter-spacing:-.4px;}
.meta-line{font-size:14px; line-height:22px; color:var(--muted); margin-top:-14px; margin-bottom:18px;}
.meta-line b{color:var(--ink);}

/* Tabel HTML render kustom (pills, titik warna properti, angka rata kanan tabular) */
table.km{width:100%; border-collapse:collapse; background:var(--ivory,#FBF9F3);
  border:1px solid var(--line); border-radius:12px; overflow:hidden;}
table.km th{font-size:11.5px; letter-spacing:.08em; color:var(--muted); font-weight:700; text-align:left;
  padding:12px 14px; background:#F1EDE2; border-bottom:1px solid var(--line);}
table.km td{padding:var(--pad-td); border-bottom:1px solid var(--line); font-size:14px; vertical-align:middle; color:var(--ink);}
table.km tr:last-child td{border-bottom:none;}
table.km td.num, table.km th.num{text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; font-weight:600;}
table.km tr.total td{background:#F1EDE2; font-weight:700; border-top:2px solid var(--line);}
.pill{border-radius:999px; font-size:12.5px; font-weight:700; display:inline-flex; align-items:center;
  gap:6px; padding:6px 12px; white-space:nowrap;}
.pill .bdot{width:6px; height:6px; border-radius:50%; background:currentColor; display:inline-block;}
.pill.ok{background:#E2EDE5; color:var(--ok);}
.pill.wrn{background:#F3E8D2; color:var(--wrn);}
.pill.dgr{background:#F4DBD7; color:var(--dgr);}
.pill.cem{background:var(--cement); color:var(--ink);}
.kamar-badge{background:var(--cement); border-radius:999px; padding:5px 11px 5px 9px; font-size:13px;
  font-weight:700; display:inline-flex; align-items:center; gap:7px; white-space:nowrap;}
.kd{width:7px; height:7px; border-radius:50%; display:inline-block;}
.kd-espresso{background:var(--espresso);} .kd-amber{background:var(--amber);}
.chip{width:30px; height:30px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center;
  font-weight:700; font-size:11.5px; background:var(--cement); color:var(--muted);}
.p-sub{font-size:12.5px; color:var(--dgr); font-weight:600; line-height:18px;}
.p-name{font-weight:700;}
.pr-sub{font-size:12.5px; color:var(--muted); line-height:18px;}
.tfooter{display:flex; justify-content:space-between; align-items:center; padding:14px 20px;
  border:1px solid var(--line); border-top:none; border-radius:0 0 12px 12px; background:#FBF9F3;
  font-size:13px; color:var(--muted);}
.notif-item{font-size:14px; line-height:22px; padding:6px 0; border-bottom:1px solid var(--line);}

/* Sidebar: pemilih properti selalu terlihat, item nav aktif espresso (dari token primary) */
[data-testid="stSidebar"]{background:#FBF9F3; border-right:1px solid var(--line);}
[data-testid="stSidebar"] hr{margin:8px 0; border-color:var(--line);}

/* Satu tombol primer per halaman: primary = espresso penuh, secondary = sand */
button[kind="primary"]{background:#2E2A24 !important; border-color:#2E2A24 !important; color:#FBF9F3 !important;}
button[kind="secondary"]{background:#E8E1CF !important; border-color:#E8E1CF !important; color:#2E2A24 !important;}

/* Fokus cincin biru 3px (aksesibilitas Bagian 9) */
button:focus-visible, a:focus-visible, input:focus-visible{outline:3px solid #1D5FA8 !important; outline-offset:1px;}

/* Dialog detail baris: satu tingkat permukaan */
[data-testid="stDialog"] div[data-testid="stVerticalBlock"]{gap:12px;}

/* Kartu statistik: label kecil -> angka besar -> satu baris meta (Bagian 7) */
[data-testid="stMetric"]{background:#FBF9F3; border:1px solid var(--line); border-radius:12px; padding:24px;}
[data-testid="stMetricLabel"] p{font-size:12px; letter-spacing:.09em; font-weight:700; text-transform:uppercase;}
[data-testid="stMetricDelta"] svg{display:none;}
</style>
"""


def inject_theme():
    st.markdown(TOKENS_CSS, unsafe_allow_html=True)
