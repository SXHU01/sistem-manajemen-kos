# -*- coding: utf-8 -*-
"""Model database KosManage (PRD Bagian 1: SQLAlchemy + SQLite, uang integer rupiah).

Constraint database menegakkan aturan bisnis bila memungkinkan (BR-03, BR-11).
Tidak ada hapus permanen pada penyewaan/tagihan/pembayaran (keandalan & BR-19).
"""
from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint, create_engine, func, select)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship)

from utils.format import fmt_rupiah


class Base(DeclarativeBase):
    pass


class Properti(Base):
    """BR-01: tepat dua, dibuat saat instalasi, tidak dapat ditambah/dihapus (FR-04)."""
    __tablename__ = "properti"
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(100))
    alamat: Mapped[str] = mapped_column(Text, default="")
    warna: Mapped[str] = mapped_column(String(20), default="espresso")  # titik warna tetap
    kamar: Mapped[list["Kamar"]] = relationship(back_populates="properti")


class Kamar(Base):
    """BR-02: satu properti per kamar; BR-03: nomor unik per properti (constraint)."""
    __tablename__ = "kamar"
    __table_args__ = (UniqueConstraint("properti_id", "nomor", name="uq_kamar_properti_nomor"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    properti_id: Mapped[int] = mapped_column(ForeignKey("properti.id"))
    nomor: Mapped[str] = mapped_column(String(20))
    tipe: Mapped[str] = mapped_column(String(50), default="Standar")
    harga_sewa: Mapped[int] = mapped_column(Integer)          # rupiah integer
    perbaikan: Mapped[bool] = mapped_column(Boolean, default=False)  # FR-05
    properti: Mapped["Properti"] = relationship(back_populates="kamar")
    penyewaan: Mapped[list["Penyewaan"]] = relationship(back_populates="kamar")


class Penghuni(Base):
    """FR-07: nama, telepon, nomor identitas, catatan."""
    __tablename__ = "penghuni"
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(120))
    telepon: Mapped[str] = mapped_column(String(25), default="")
    nomor_identitas: Mapped[str] = mapped_column(String(40), default="")
    catatan: Mapped[str] = mapped_column(Text, default="")
    penyewaan: Mapped[list["Penyewaan"]] = relationship(back_populates="penghuni")


class Penyewaan(Base):
    """BR-07/BR-08: harga & jatuh tempo disalin saat dibuat; tanpa hapus permanen."""
    __tablename__ = "penyewaan"
    id: Mapped[int] = mapped_column(primary_key=True)
    kamar_id: Mapped[int] = mapped_column(ForeignKey("kamar.id"))
    penghuni_id: Mapped[int] = mapped_column(ForeignKey("penghuni.id"))
    mulai: Mapped[date] = mapped_column(Date)
    akhir_rencana: Mapped[date | None] = mapped_column(Date, nullable=True)
    harga_sewa_bulan: Mapped[int] = mapped_column(Integer)     # salinan harga (BR-08)
    jatuh_tempo_hari: Mapped[int] = mapped_column(Integer)     # 1..28 (BR-09)
    selesai_pada: Mapped[date | None] = mapped_column(Date, nullable=True)  # pengakhiran (FR-09)
    catatan_deposit: Mapped[str] = mapped_column(Text, default="")  # deposit = catatan teks (PRD 6.2)
    kamar: Mapped["Kamar"] = relationship(back_populates="penyewaan")
    penghuni: Mapped["Penghuni"] = relationship(back_populates="penyewaan")
    tagihan: Mapped[list["Tagihan"]] = relationship(back_populates="penyewaan")


class Tagihan(Base):
    """BR-10/BR-11: satu penyewaan + satu periode, unik (constraint)."""
    __tablename__ = "tagihan"
    __table_args__ = (UniqueConstraint("penyewaan_id", "periode", name="uq_tagihan_periode"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    penyewaan_id: Mapped[int] = mapped_column(ForeignKey("penyewaan.id"))
    periode: Mapped[date] = mapped_column(Date)                # awal bulan
    jatuh_tempo: Mapped[date] = mapped_column(Date)
    total: Mapped[int] = mapped_column(Integer)                # bulan penuh atau prorata (BR-13/14)
    penyewaan: Mapped["Penyewaan"] = relationship(back_populates="tagihan")
    pembayaran: Mapped[list["Pembayaran"]] = relationship(back_populates="tagihan")


class Pembayaran(Base):
    """BR-15/BR-19: banyak pembayaran per tagihan; koreksi = batal dengan alasan, bukan hapus."""
    __tablename__ = "pembayaran"
    id: Mapped[int] = mapped_column(primary_key=True)
    tagihan_id: Mapped[int] = mapped_column(ForeignKey("tagihan.id"))
    tanggal_bayar: Mapped[date] = mapped_column(Date)          # dasar laporan pendapatan (FR-16)
    nominal: Mapped[int] = mapped_column(Integer)
    metode: Mapped[str] = mapped_column(String(20), default="Tunai")   # Tunai / Transfer
    catatan: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Valid")   # Valid / Dibatalkan
    alasan_batal: Mapped[str | None] = mapped_column(Text, nullable=True)
    dibatalkan_pada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dibatalkan_oleh: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tagihan: Mapped["Tagihan"] = relationship(back_populates="pembayaran")


class Admin(Base):
    """FR-01: admin tunggal dibuat via skrip/instalasi; password hash (bcrypt)."""
    __tablename__ = "admin"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    gagal_login: Mapped[int] = mapped_column(Integer, default=0)
    terkunci_sampai: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------- Perhitungan status & sisa (dipakai controller & view, murni fungsi) ----------

def total_valid(tagihan: Tagihan) -> int:
    """Jumlah pembayaran valid (BR-16 memakai angka ini)."""
    return sum(p.nominal for p in tagihan.pembayaran if p.status == "Valid")


def sisa_tagihan(tagihan: Tagihan) -> int:
    return tagihan.total - total_valid(tagihan)


def status_tagihan(tagihan: Tagihan, today: date) -> str:
    """BR-18: Belum dibayar / Sebagian / Lunas / Menunggak."""
    terbayar = total_valid(tagihan)
    if terbayar >= tagihan.total:
        return "Lunas"
    if today > tagihan.jatuh_tempo:
        return "Menunggak"
    return "Sebagian" if terbayar > 0 else "Belum dibayar"


def status_kamar(kamar: Kamar, today: date) -> str:
    """FR-06: dihitung dari penyewaan aktif, kecuali ditandai Perbaikan."""
    if kamar.perbaikan:
        return "Perbaikan"
    for s in kamar.penyewaan:
        if s.selesai_pada is None and s.mulai <= today and (s.akhir_rencana is None or s.akhir_rencana >= today):
            return "Terisi"
    return "Kosong"


def sewa_aktif(penyewaan: Penyewaan, today: date) -> bool:
    return penyewaan.selesai_pada is None
