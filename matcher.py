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

# Bersihkan pengulangan frasa berlabel yang saling memuat
    parts = re.split(r"\s+(?=\[[A-Za-z0-9\s]+\])", teks)
    if len(parts) > 1:
        unik_parts: list[str] = []
        for p in parts:
            p_clean = p.strip()
            if p_clean and p_clean not in unik_parts:
                unik_parts.append(p_clean)
        if len(unik_parts) == 2:
            a, b = unik_parts[0], unik_parts[1]
            a_norm = re.sub(r"^\[[^\]]+\]\s*", "", a).lower()
            b_norm = re.sub(r"^\[[^\]]+\]\s*", "", b).lower()
            if a_norm in b_norm:
                teks = b
            elif b_norm in a_norm:
                teks = a

    return re.sub(r"\s+", " ", teks).strip()

def normalisasi_teks(teks: str) -> str:
    teks = rapikan_judul(teks).lower()
    teks = re.sub(r"\[[^\]]+\]", " ", teks)
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()