# -*- coding: utf-8 -*-
"""Komponen view bersama — menerapkan Design System v2.4 Bagian 5-7.

Pola halaman: judul + satu baris meta data + kontrol dropdown + SATU tombol primer + satu konten utama.
Tabel default maksimal 6 kolom; footer hanya hitungan + pagination.
"""
import html as _html
import streamlit as st
from utils.format import fmt_rupiah

PAGE_SIZE = 10

# Satu status, satu warna, satu kata (Bagian 1: status berarti)
PILL_CLASS = {
    "Lunas": "ok", "Terisi": "ok", "Berlangsung": "ok", "Valid": "ok",
    "Sebagian": "wrn", "Perbaikan": "wrn",
    "Menunggak": "dgr",
    "Belum dibayar": "cem", "Kosong": "cem", "Dibatalkan": "cem", "Selesai": "cem",
}


def pill(status: str) -> str:
    cls = PILL_CLASS.get(status, "cem")
    return f"<span class='pill {cls}'><span class='bdot'></span>{_html.escape(status)}</span>"


def kamar_badge(nomor: str, warna: str) -> str:
    """Badge kamar satu baris dengan titik warna properti (espresso/amber)."""
    return f"<span class='kamar-badge'><span class='kd kd-{warna}'></span>Kamar {_html.escape(str(nomor))}</span>"


def esc(v) -> str:
    return _html.escape(str(v))


def page_header(judul: str, meta_html: str | None = None):
    """Judul halaman + SATU baris meta data (angka, bukan kalimat deskripsi)."""
    st.header(judul)
    if meta_html:
        st.markdown(f"<div class='meta-line'>{meta_html}</div>", unsafe_allow_html=True)


def render_table(colomns: list[dict], rows: list[dict], total_row: dict | None = None) -> bool:
    """Tabel HTML dari Design System: th kecil, td 16px, angka rata kanan, pills, badge kamar.

    colomns: [{"label": "PENGHUNI", "key": "penghuni", "num": False, "width": "24%"}]
    rows:    list[dict] berisi HTML siap render (gunakan pill(), kamar_badge(), esc()).
    return:  True jika ada baris (untuk empty state di view).
    """
    if not rows:
        return False
    ths = "".join(
        f"<th class=\"{'num' if c.get('num') else ''}\" style=\"width:{c.get('width', 'auto')}\">{_html.escape(c['label'])}</th>"
        for c in colomns
    )
    trs = []
    for r in rows:
        tds = "".join(
            f"<td class=\"{'num' if c.get('num') else ''}\">{r.get(c['key'], '')}</td>" for c in colomns
        )
        trs.append(f"<tr>{tds}</tr>")
    if total_row:
        tds = "".join(
            f"<td class=\"{'num' if c.get('num') else ''}\">{total_row.get(c['key'], '')}</td>" for c in colomns
        )
        trs.append(f"<tr class='total'>{tds}</tr>")
    st.markdown(f"<table class='km'><thead><tr>{ths}</tr></thead><tbody>{''.join(trs)}</tbody></table>",
                unsafe_allow_html=True)
    return True


def paginate(rows: list, key: str) -> tuple[list, int, int, int]:
    """Pagination standar: 10 baris per halaman. Footer digambar terpisah via render_pager()."""
    total = len(rows)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    st.session_state.setdefault(f"pg_{key}", 1)
    cur = min(max(1, st.session_state[f"pg_{key}"]), pages)
    mulai = (cur - 1) * PAGE_SIZE
    st.session_state[f"pginfo_{key}"] = (cur, pages)
    return rows[mulai:mulai + PAGE_SIZE], cur, pages, total


def render_pager(key: str):
    """Footer tabel: 'Menampilkan halaman x dari y' + tombol pager (dipanggil SETELAH tabel)."""
    info = st.session_state.get(f"pginfo_{key}")
    if not info:
        return
    cur, pages = info
    c1, c2, c3 = st.columns([4, 1, 1])
    c1.markdown(f"<div class='tfooter'>Menampilkan halaman {cur} dari {pages}</div>",
                unsafe_allow_html=True)
    if pages <= 1:
        return
    if c2.button("‹", key=f"{key}_prev", disabled=cur <= 1, use_container_width=True):
        st.session_state[f"pg_{key}"] = cur - 1
        st.rerun()
    if c3.button("›", key=f"{key}_next", disabled=cur >= pages, use_container_width=True):
        st.session_state[f"pg_{key}"] = cur + 1
        st.rerun()


def rupiah_cell(n: int) -> str:
    return fmt_rupiah(n)


def meta(**bagian) -> str:
    """Buat baris meta data: meta(tagihan=42, perhatian=3) -> '42 tagihan · 3 perlu perhatian'.
    Nilai penting dibungkus <b> otomatis."""
    potongan = []
    for label, nilai in bagian.items():
        label = label.replace("_", " ")
        potongan.append(f"<b>{esc(nilai)}</b> {esc(label)}")
    return " &middot; ".join(potongan)
