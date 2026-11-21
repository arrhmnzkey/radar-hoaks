import re
import subprocess
import time
from urllib.parse import urljoin
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://turnbackhoax.id/articles"
OUT_CSV = Path("data/mentah.csv") if "Path" in globals() else __import__("pathlib").Path("data/mentah.csv")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def ambil_html(url: str, timeout: int = 25) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"[Info] requests gagal ({exc}), mencoba curl.exe...")
        hasil = subprocess.run(
            ["curl.exe", "-sS", "-L", "--max-time", str(timeout), "-A", USER_AGENT, url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return hasil.stdout

def ekstrak_label_dari_judul(judul: str) -> str:
    match = re.match(r"^\s*\[([^\]]+)\]\s*", judul)
    if not match:
        return ""
    raw_label = match.group(1).strip().lower()
    mapping = {
        "salah": "Salah",
        "penipuan": "Penipuan",
        "keliru": "Keliru",
        "misinformasi": "Misinformasi",
        "disinformasi": "Disinformasi",
        "benar": "Benar",
        "sebagian benar": "Sebagian Benar",
        "fakta": "Fakta",
    }
    return mapping.get(raw_label, match.group(1).strip().title())

def bersihkan_teks(teks: str) -> str:
    return " ".join((teks or "").split()).strip()

def parse_halaman(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href_raw = (a.get("href") or "").strip()
        full_url = urljoin(page_url, href_raw)

        if "/articles/" not in full_url:
            continue
        if re.search(r"/articles/\d+-", full_url) is None:
            continue
        if full_url in seen_urls:
            continue

        # mencari judul dari elemen heading/judul di dalam link atau parent terdekat
        heading = a.select_one("h1, h2, h3, h4, .title, [class*='title']")
        if heading:
            judul = bersihkan_teks(heading.get_text(" ", strip=True))
        else:
            # Jika teks link panjang dan mengandung 'Faktanya', ambil bagian sebelum 'Faktanya'
            teks_link = bersihkan_teks(a.get_text(" ", strip=True))
            judul = bersihkan_teks(re.split(r"\s+Faktanya[,:\s]", teks_link, maxsplit=1)[0])

        if len(judul) < 10:
            continue

        label = ekstrak_label_dari_judul(judul)

        # Cari ringkasan dan tanggal pada kontainer kartu terdekat
        kontainer = a.find_parent(["article", "div", "li"])
        ringkasan = ""
        tanggal = ""
        if kontainer:
            time_el = kontainer.select_one("time")
            if time_el:
                tanggal = bersihkan_teks(time_el.get_text(" ", strip=True))

            for p in kontainer.select("p, .excerpt, [class*='excerpt'], [class*='summary']"):
                pt = bersihkan_teks(p.get_text(" ", strip=True))
                if pt and pt != judul and len(pt) > 25:
                    ringkasan = pt
                    break

        seen_urls.add(full_url)
        items.append(
            {
                "judul": judul,
                "label": label,
                "kategori": "",
                "tanggal": tanggal,
                "ringkasan": ringkasan,
                "tautan": full_url,
            }
        )

    return items

def scrape_turnbackhoax(start_page: int = 1, end_page: int = 3, delay: float = 1.0) -> list[dict]:
    semua_data: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(start_page, end_page + 1):
        url = f"{BASE_URL}?category=all&page={page}"
        html = ambil_html(url)
        records = parse_halaman(html, url)

        baru = 0
        for rec in records:
            if rec["tautan"] not in seen_urls:
                seen_urls.add(rec["tautan"])
                semua_data.append(rec)
                baru += 1

        print(f"Halaman {page}: ditemukan {len(records)} artikel ({baru} unik baru)")
        if page < end_page:
            time.sleep(delay)

    return semua_data

def simpan_csv(records: list[dict], out_path=OUT_CSV) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kolom = ["judul", "label", "kategori", "tanggal", "ringkasan", "tautan"]
    df = pd.DataFrame(records, columns=kolom)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Tersimpan {len(df)} baris ke {out_path}")

if __name__ == "__main__":
    data = scrape_turnbackhoax(start_page=1, end_page=3, delay=1.0)
    simpan_csv(data)