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

def ambil_token_penting(teks: str) -> set[str]:
    bersih = normalisasi_teks(teks)
    return {
        tok
        for tok in bersih.split()
        if len(tok) >= 3 and tok not in STOPWORDS_ID and not tok.isdigit()
    }

def cosine_sim_counter(vec_a: Counter, vec_b: Counter) -> float:
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

def muat_klaim_db(db_path: Path = DB_PATH) -> list[dict]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database tidak ditemukan: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, judul, label, kategori, tanggal, ringkasan, kata_kunci, tautan
            FROM klaim_hoaks
            """
        ).fetchall()

    hasil: list[dict] = []
    for r in rows:
        judul_rapi = rapikan_judul(r["judul"])
        try:
            kw_list = json.loads(r["kata_kunci"] or "[]")
            if not isinstance(kw_list, list):
                kw_list = []
        except json.JSONDecodeError:
            kw_list = []

        teks_indeks = " ".join(
            [
                normalisasi_teks(judul_rapi),
                normalisasi_teks(r["ringkasan"]),
                " ".join(normalisasi_teks(k) for k in kw_list),
            ]
        ).strip()

        hasil.append(
            {
                "id": r["id"],
                "judul": judul_rapi,
                "label": r["label"],
                "kategori": r["kategori"],
                "tanggal": r["tanggal"] or "",
                "ringkasan": r["ringkasan"] or "",
                "kata_kunci": kw_list,
                "tautan": r["tautan"],
                "teks_indeks": teks_indeks,
            }
        )
    return hasil 

def cari_klaim_serupa(
    kueri: str,
    top_k: int = 3,
    ambang_batas: float = 0.08,
    db_path: Path = DB_PATH,
) -> list[dict]:
    kueri_bersih = normalisasi_teks(kueri)
    if not kueri_bersih:
        return []

    records = muat_klaim_db(db_path)
    if not records:
        return []

    vec_kueri = Counter(kueri_bersih.split())
    token_kueri = ambil_token_penting(kueri)

    kandidat: list[dict] = []
    for item in records:
        vec_item = Counter(item["teks_indeks"].split())
        skor_cos = cosine_sim_counter(vec_kueri, vec_item)

        token_item = ambil_token_penting(
            f"{item['judul']} {item['ringkasan']} {' '.join(item['kata_kunci'])}"
        )
        irisan = token_kueri & token_item
        rasio_token = (len(irisan) / len(token_kueri)) if token_kueri else 0.0

        skor_akhir = (0.60 * skor_cos) + (0.40 * rasio_token)

        if skor_akhir >= ambang_batas or len(irisan) >= 2:
            kandidat.append(
                {
                    **{k: v for k, v in item.items() if k != "teks_indeks"},
                    "skor": round(skor_akhir, 4),
                    "skor_cosine": round(skor_cos, 4),
                    "kata_cocok": sorted(irisan),
                }
            )

    kandidat.sort(key=lambda x: (-x["skor"], -len(x["kata_cocok"]), x["id"]))
    return kandidat[:top_k]

if __name__ == "__main__":
    contoh_kueri = [
        "BPJS diganti klinik kopdes bener gak?",
        "foto jokowi ditangkap brimob",
        "pipa minyak arab saudi meledak",
    ]

    for q in contoh_kueri:
        print(f"\nKueri: {q}")
        hasil = cari_klaim_serupa(q, top_k=2)
        if not hasil:
            print("  -> Tidak ditemukan kecocokan yang cukup dekat.")
            continue
        for rank, h in enumerate(hasil, 1):
            print(f"  {rank}. [{h['label']}] {h['judul']} (skor={h['skor']}, cocok={h['kata_cocok']})")
            print(f"     Link: {h['tautan']}")