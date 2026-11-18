# -*- coding: utf-8 -*-
"""Pulihkan database dari backup (PRD: satu perintah untuk memulihkan).

Pemakaian:  python -m database.restore backups/kosmanage-2026-11-17.db
Database saat ini disalin dulu ke backups/ sebelum ditimpa.
"""
import os
import shutil
import sys

from database.db import BACKUP_DIR, DB_FILE


def pulihkan(path_backup: str) -> str:
    if not os.path.exists(path_backup):
        raise FileNotFoundError(f"Backup tidak ditemukan: {path_backup}")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    cadangan_sekarang = os.path.join(BACKUP_DIR, "kosmanage-sebelum-restore.db")
    if os.path.exists(DB_FILE):
        shutil.copy2(DB_FILE, cadangan_sekarang)
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    shutil.copy2(path_backup, DB_FILE)
    return cadangan_sekarang


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Pemakaian: python -m database.restore <path backup>")
        sys.exit(1)
    sebelum = pulihkan(sys.argv[1])
    print(f"Database dipulihkan dari {sys.argv[1]}.")
    print(f"Database sebelumnya disimpan di {sebelum}.")
