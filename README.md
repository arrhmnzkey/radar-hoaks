# CekHoaks Radar

Website cerdas untuk mengecek apakah sebuah klaim atau pesan berantai sudah pernah diklarifikasi sebagai hoaks. Pengguna menempelkan klaim, lalu sistem mencocokkannya dengan klarifikasi dari situs cek fakta dan menampilkan label serta sumber aslinya.

## Fitur

- Landing page dengan kolom cek klaim dan statistik
- Cek klaim berdasarkan skor kemiripan
- Daftar klarifikasi dengan filter kategori dan kata kunci
- Dashboard tren hoaks
- Chatbot untuk cek klaim dan tanya statistik
- Halaman admin untuk memperbarui data

## Cara Kerja

Scraping data turnbackhoax, pembersihan data, penyimpanan ke SQLite, lalu pencocokan klaim. Website dan chatbot memakai database dan fungsi pencocokan yang sama, sehingga hasilnya sinkron.

## Teknologi

Python, Flask, BeautifulSoup, pandas, SQLite, HTML, CSS, JavaScript

## Menjalankan

```bash
python -m pip install -r requirements.txt
python scraper.py
python pipeline.py
python app.py
```

Buka http://127.0.0.1:5000

## Catatan

Sistem tidak memberi vonis sendiri. Label dikutip dari situs cek fakta dan selalu disertai sumbernya. Jika klaim tidak ditemukan, itu tidak berarti klaimnya benar.

Arrizal Rahman 