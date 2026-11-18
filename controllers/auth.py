# -*- coding: utf-8 -*-
"""Autentikasi admin tunggal (FR-01/FR-02, keamanan PRD Bagian 9).

- Password bcrypt; minimal 8 karakter.
- Lima gagal login berturut-turut mengunci akun 5 menit.
- Sesi idle 60 menit berakhir.
"""
import bcrypt
from datetime import timedelta

from database import models as M
from utils.format import sekarang

MAKS_GAGAL = 5
DURASI_KUNCI = timedelta(minutes=5)
IDLE_TIMEOUT = timedelta(minutes=60)


def _verifikasi(password: str, hash_: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hash_.encode())
    except ValueError:
        return False


def login(sess, username: str, password: str) -> tuple[bool, str]:
    """Coba login. Kembalikan (berhasil, pesan). Pesan gagal selalu umum, kecuali kunci akun."""
    admin = sess.query(M.Admin).filter_by(username=username).first()
    if admin is None:
        return False, "Username atau password salah."
    # SQLite menyimpan DateTime tanpa zona; bandingkan dalam WIB naive agar konsisten
    sekarang_dt = sekarang().replace(tzinfo=None)
    if admin.terkunci_sampai is not None and admin.terkunci_sampai > sekarang_dt:
        sisa_menit = int((admin.terkunci_sampai - sekarang_dt).total_seconds() // 60) + 1
        return False, f"Akun terkunci. Coba lagi dalam {sisa_menit} menit."
    if len(password) < 8:
        return False, "Password minimal 8 karakter."
    if _verifikasi(password, admin.password_hash):
        admin.gagal_login = 0
        admin.terkunci_sampai = None
        sess.commit()
        return True, ""
    admin.gagal_login += 1
    if admin.gagal_login >= MAKS_GAGAL:
        admin.terkunci_sampai = sekarang_dt + DURASI_KUNCI
        admin.gagal_login = 0
        pesan = "Login gagal lima kali. Akun dikunci selama 5 menit."
    else:
        pesan = "Username atau password salah."
    sess.commit()
    return False, pesan


def sesi_kadaluarsa(last_active, now=None) -> bool:
    """FR-02: sesi berakhir setelah 60 menit tidak aktif."""
    if last_active is None:
        return True
    return (now or sekarang()) - last_active > IDLE_TIMEOUT
