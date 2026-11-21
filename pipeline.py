import json
import re
import sqlite3
from pathlib import Path

import pandas as pd

IN_CSV = Path("data/mentah.csv")
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
    "media", "sosial", "akun", "unggah", "unggahan", "warganet", "masyarakat",
}

ATURAN_KATEGORI = {
    "Politik & Pemerintahan": [
        "prabowo", "jokowi", "gibran", "presiden", "wapres", "menteri", "dpr",
        "pemerintah", "pemilu", "pilkada", "pilpres", "partai", "kabinet",
        "demonstrasi", "demo", "pemakzulan", "diplomatik", "tni", "polri",
        "brimob", "sri sultan", "gubernur", "bupati", "walikota", "hukum",
    ],
    "Kesehatan": [
        "bpjs", "klinik", "kopdes", "rumah sakit", "dokter", "obat", "vaksin",
        "penyakit", "virus", "kesehatan", "medis", "gizi", "mbg", "sehat",
        "kanker", "jantung", "diabetes", "herbal", "pasien",
    ],
    "Ekonomi & Bansos": [
        "pkh", "bansos", "bantuan", "blt", "subsidi", "harga", "pajak",
        "ekonomi", "rupiah", "bank", "investasi", "saham", "pinjol", "utang",
        "anggaran", "dana", "ekspor", "impor", "koperasi", "gaji", "upah",
    ],
    "Penipuan & Modus": [
        "penipuan", "hadiah", "undian", "rekrutmen", "lowongan", "palsu",
        "tautan", "link", "saldo", "gratis", "transfer", "kode otp", "scam",
    ],
    "Bencana & Peristiwa": [
        "gempa", "banjir", "longsor", "kebakaran", "ledakan", "pipa minyak",
        "kecelakaan", "tsunami", "erupsi", "gunung", "cuaca", "badai",
    ],
    "Sosial & Tokoh": [
        "tokoh", "artis", "selebritas", "ulama", "kyai", "warga", "sekolah",
        "pendidikan", "kampus", "mahasiswa", "dedi mulyadi", "eva stevany",
    ],
}

def bersihkan_teks(teks: str) -> str:
    teks = re.sub(r"<[^>]+>", " ", str(teks or ""))
    teks = re.sub(r"\s+", " ", teks).strip()
    return teks

def normalisasi_label(label: str, judul: str) -> str:
    sumber = f"{label} {judul}".lower()
    if "salah" in sumber or "tidak benar" in sumber or "hoax" in sumber or "hoaks" in sumber:
        return "Salah"
    if "penipuan" in sumber:
        return "Penipuan"
    if "keliru" in sumber or "misinformasi" in sumber or "disinformasi" in sumber:
        return "Keliru"
    if "sebagian benar" in sumber:
        return "Sebagian Benar"
    if "benar" in sumber or "fakta" in sumber:
        return "Benar"
    return "Perlu Cek"

def klasifikasi_kategori(judul: str, ringkasan: str) -> str:
    teks = f"{judul} {ringkasan}".lower()
    skor_terbaik = 0
    kategori_terpilih = "Umum"

    for kategori, kata_kunci in ATURAN_KATEGORI.items():
        skor = sum(1 for kw in kata_kunci if re.search(rf"\b{re.escape(kw)}\b", teks))
        if skor > skor_terbaik:
            skor_terbaik = skor
            kategori_terpilih = kategori

    return kategori_terpilih

def ekstrak_kata_kunci(judul: str, ringkasan: str, top_n: int = 6) -> list[str]:
    teks = f"{judul} {ringkasan}".lower()
    teks = re.sub(r"\[[^\]]+\]", " ", teks)
    token = re.findall(r"[a-z0-9]{3,}", teks)

    frekuensi: dict[str, int] = {}
    for kata in token:
        if kata in STOPWORDS_ID or kata.isdigit():
            continue
        frekuensi[kata] = frekuensi.get(kata, 0) + 1

    urut = sorted(frekuensi.items(), key=lambda x: (-x[1], x[0]))
    return [kata for kata, _ in urut[:top_n]]

def proses_data(in_csv: Path = IN_CSV) -> list[dict]:
    if not in_csv.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {in_csv}")

    df = pd.read_csv(in_csv, dtype=str).fillna("")
    df = df.drop_duplicates(subset=["tautan"], keep="first").reset_index(drop=True)

    hasil: list[dict] = []
    for _, row in df.iterrows():
        judul = bersihkan_teks(row.get("judul", ""))
        tautan = bersihkan_teks(row.get("tautan", ""))
        tanggal = bersihkan_teks(row.get("tanggal", ""))
        ringkasan = bersihkan_teks(row.get("ringkasan", ""))
        label_awal = bersihkan_teks(row.get("label", ""))

        if not judul or not tautan:
            continue

        label_bersih = normalisasi_label(label_awal, judul)
        kategori_bersih = bersihkan_teks(row.get("kategori", "")) or klasifikasi_kategori(
            judul, ringkasan
        )
        kata_kunci = ekstrak_kata_kunci(judul, ringkasan)

        hasil.append(
            {
                "judul": judul,
                "label": label_bersih,
                "kategori": kategori_bersih,
                "tanggal": tanggal,
                "ringkasan": ringkasan,
                "kata_kunci": json.dumps(kata_kunci, ensure_ascii=False),
                "tautan": tautan,
            }
        )

    return hasil

def simpan_ke_sqlite(records: list[dict], db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS klaim_hoaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judul TEXT NOT NULL,
                label TEXT NOT NULL,
                kategori TEXT NOT NULL,
                tanggal TEXT,
                ringkasan TEXT,
                kata_kunci TEXT,
                tautan TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.execute("DELETE FROM klaim_hoaks")
        conn.executemany(
            """
            INSERT OR REPLACE INTO klaim_hoaks
                (judul, label, kategori, tanggal, ringkasan, kata_kunci, tautan)
            VALUES
                (:judul, :label, :kategori, :tanggal, :ringkasan, :kata_kunci, :tautan)
            """,
            records,
        )
        conn.commit()

def cetak_ringkasan(records: list[dict], db_path: Path = DB_PATH) -> None:
    print(f"Total data diproses ke {db_path}: {len(records)} baris\n")

    dist_label: dict[str, int] = {}
    dist_kategori: dict[str, int] = {}
    for r in records:
        dist_label[r["label"]] = dist_label.get(r["label"], 0) + 1
        dist_kategori[r["kategori"]] = dist_kategori.get(r["kategori"], 0) + 1

    print("Distribusi Label:")
    for k, v in sorted(dist_label.items(), key=lambda x: (-x[1], x[0])):
        print(f"  - {k}: {v}")

    print("\nDistribusi Kategori:")
    for k, v in sorted(dist_kategori.items(), key=lambda x: (-x[1], x[0])):
        print(f"  - {k}: {v}")

if __name__ == "__main__":
    data_bersih = proses_data(IN_CSV)
    simpan_ke_sqlite(data_bersih, DB_PATH)
    cetak_ringkasan(data_bersih, DB_PATH)