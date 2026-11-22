import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path

DB_PATH = Path("data/hoaks.db")

STOPWORDS_ID = {
    "yang", "dan", "di", "ke", "dari", "pada", "untuk", "dengan", "atau",
    "ini", "itu", "adalah", "sebagai", "oleh", "karena", "tidak", "ada",
    "akan", "telah", "sudah", "belum", "juga", "bisa", "dapat", "jadi",
    "lebih", "sangat", "dalam", "atas", "bawah", "antara", "saat", "ketika",
    "setelah", "sebelum", "agar", "supaya", "namun", "tetapi", "bahwa",
    "tersebut", "merupakan", "menjadi", "melakukan", "membuat", "foto",
    "video", "gambar", "berita", "informasi", "klaim", "hoaks", "hoax",
    "faktanya", "fakta", "sebenarnya", "beredar", "dibagikan", "viral",
    "apakah", "benar", "benarkah", "bener", "salah", "kah", "dong", "ya", "nih", "deh", "sih",
    "gak", "nggak", "bikin", "kok", "emang", "memang",
}

def rapikan_judul(judul: str) -> str:
    teks = re.sub(r"\s+", " ", str(judul or "").replace("…", "...")).strip()
    if not teks:
        return ""

    # Ulangi pemangkasan jika ada potongan "..." yang diulang oleh versi lengkapnya
    for _ in range(3):
        match = re.match(r"^(.*?)\.\.\.\s+(.*)$", teks)
        if not match:
            break

        potongan_awal = match.group(1).strip()
        sisa_teks = match.group(2).strip()

        if len(sisa_teks) >= max(12, len(potongan_awal) // 2):
            label_match = re.match(r"^(\[[^\]]+\])\s*", potongan_awal)
            if label_match and not re.match(r"^\[[^\]]+\]", sisa_teks):
                teks = f"{label_match.group(1)} {sisa_teks}".strip()
            else:
                teks = sisa_teks
        else:
            break
