# -*- coding: utf-8 -*-
"""Format angka & tanggal sesuai Design System v2.4 Bagian 3 dan zona waktu PRD (Asia/Jakarta)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Jakarta")

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
BULAN_PENUH = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"]


def hari_ini() -> date:
    """Hari ini menurut zona waktu Asia/Jakarta (PRD Bagian 1)."""
    return datetime.now(TZ).date()


def sekarang() -> datetime:
    return datetime.now(TZ)


def fmt_rupiah(n: int) -> str:
    """Rp 1.500.000 — titik ribuan, tanpa desimal, selalu satu baris."""
    return f"Rp {abs(int(n)):,}".replace(",", ".") if n < 0 else f"Rp {int(n):,}".replace(",", ".")


def fmt_tgl(d: date | None) -> str:
    """5 Nov 2026 — satu baris."""
    if d is None:
        return "—"
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def fmt_periode(d: date | None) -> str:
    """Nov 2026 — satu baris (periode tagihan = awal bulan)."""
    if d is None:
        return "—"
    return f"{BULAN[d.month - 1]} {d.year}"


def fmt_bulan_tahun(d: date) -> str:
    return f"{BULAN_PENUH[d.month - 1]} {d.year}"


def awal_bulan(d: date) -> date:
    return d.replace(day=1)


def tambah_bulan(d: date, n: int) -> date:
    """Awal bulan + n bulan, aman untuk tanggal 29-31 (PRD keputusan jatuh tempo)."""
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return d.replace(year=y, month=m, day=1)


def hari_dalam_bulan(d: date) -> int:
    return (tambah_bulan(d, 1) - timedelta(days=1)).day


def terlambat_hari(jatuh_tempo: date, today: date) -> int:
    """Jumlah hari lewat jatuh tempo (positif berarti sudah lewat)."""
    return (today - jatuh_tempo).days
