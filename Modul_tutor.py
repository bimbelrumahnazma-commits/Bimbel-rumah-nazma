import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import time
import pandas as pd
import random
import json
import uuid
import requests
import base64
import re
import hashlib
import hmac
import secrets
import os
import streamlit.components.v1 as components


# Komponen browser khusus untuk mengirim kejadian Focus Alert ke backend Streamlit.
# Folder nazma_focus_component harus ikut diunggah ke repository Streamlit Cloud.
try:
    NAZMA_FOCUS_COMPONENT = components.declare_component(
        "nazma_focus_tracker",
        path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "nazma_focus_component")
    )
except Exception:
    NAZMA_FOCUS_COMPONENT = None  # folder komponen belum diunggah: aplikasi tetap jalan tanpa Focus Alert


def _komponen_fokus_aman(**kwargs):
    if NAZMA_FOCUS_COMPONENT is None:
        return None
    try:
        return NAZMA_FOCUS_COMPONENT(**kwargs)
    except Exception:
        return None


# Daftar mata pelajaran dan program Bimbel Rumah Nazma
MAPEL_OPTIONS = [
    # PAUD / TK
    "Calistung", "Tematik TK", "Pendidikan Agama",

    # SD
    "Matematika SD", "Bahasa Indonesia SD", "IPAS SD",
    "Bahasa Inggris SD", "Pendidikan Pancasila SD", "PAI SD",
    "PJOK SD", "Seni Rupa SD", "Seni Musik SD", "Bahasa Arab SD",

    # SMP
    "Matematika SMP", "Bahasa Indonesia SMP", "Bahasa Inggris SMP",
    "IPA SMP", "IPS SMP", "Pendidikan Pancasila SMP", "PAI SMP",
    "Informatika SMP", "PJOK SMP", "Seni Budaya SMP", "Prakarya SMP",

    # SMA
    "Matematika SMA", "Bahasa Indonesia SMA", "Bahasa Inggris SMA",
    "Fisika SMA", "Kimia SMA", "Biologi SMA", "Ekonomi SMA",
    "Geografi SMA", "Sosiologi SMA", "Sejarah SMA", "PAI SMA",
    "Informatika SMA",

    # Program khusus / persiapan tes
    "OSN SD", "OSN SMP", "OSN SMA",
    "TOEFL", "SKD", "UTBK", "TKA",

    # Umum
    "Umum",
]

# =========================================================
# KONFIGURASI HALAMAN
# =========================================================
st.set_page_config(
    page_title="Portal Bimbel Rumah Nazma - Tahap 7.55",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background: #f4f7fc; color: #172554; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg,#123568 0%,#17457f 58%,#0d2e5c 100%);
        border-right: 1px solid #234d80;
    }
    [data-testid="stSidebar"] * { color: #f8fbff; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(255,255,255,.075);
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 10px; padding: 9px 10px; margin: 5px 0;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: rgba(255,255,255,.17); }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #d9edff; border-color: #d9edff;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {
        color: #123568 !important; font-weight: 700;
    }
    [data-testid="stSidebar"] button {
        background: rgba(255,255,255,.12) !important;
        color: white !important; border: 1px solid rgba(255,255,255,.28) !important;
    }
    [data-testid="stSidebar"] button:hover { background: rgba(255,255,255,.22) !important; }
    .main-header {
        background: linear-gradient(135deg, #123568 0%, #28559a 100%);
        padding: 24px; border-radius: 16px; color: white;
        margin-bottom: 22px; box-shadow: 0 5px 18px rgba(18,53,104,.16);
    }
    .portal-hero {
        background: linear-gradient(115deg, #ffffff 0%, #eef6ff 72%, #e2f0ff 100%);
        border: 1px solid #d8e5f5; border-radius: 18px;
        padding: 22px 24px; margin: 4px 0 18px 0;
        box-shadow: 0 3px 12px rgba(31,65,114,.06);
    }
    .portal-hero h2 { color: #102a56; margin: 0 0 6px 0; font-size: 1.65rem; }
    .portal-hero p { color: #526783; margin: 0; font-size: .98rem; }
    .portal-card {
        background: #ffffff; border: 1px solid #dce6f3;
        border-radius: 16px; padding: 17px 18px; min-height: 118px;
        box-shadow: 0 3px 12px rgba(31,65,114,.055);
        margin-bottom: 12px;
    }
    .portal-card .card-icon { font-size: 1.65rem; margin-bottom: 7px; }
    .portal-card h4 { color: #183765; font-size: 1rem; margin: 0 0 5px 0; }
    .portal-card p { color: #64748b; font-size: .86rem; margin: 0; line-height: 1.4; }
    [data-testid="stSidebar"] .stRadio > label { color: #ffffff !important; font-weight: 700; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #f8fbff; }
    .dashboard-section { background: #fff; border: 1px solid #dce6f3; border-radius: 16px; padding: 18px; margin-bottom: 14px; }
    div[data-testid="stTabs"] button { font-weight: 600; }
    div[data-testid="stButton"] button {
        border-radius: 10px; border: 1px solid #cbd9eb;
        min-height: 2.55rem;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        border-radius: 9px;
    }
    @media (max-width: 700px) {
        .portal-hero { padding: 17px; }
        .portal-hero h2 { font-size: 1.3rem; }
        .portal-card { min-height: 105px; padding: 14px; }
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# KONEKSI GOOGLE SHEETS
# =========================================================
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(creds)


@st.cache_resource
def init_spreadsheet():
    """Buka spreadsheet satu kali per proses Streamlit, bukan setiap rerun/session."""
    gc = init_connection()
    return gc.open_by_key("17JI1x966HfVG4YpfzCz_bssBwOmUTIJFbRutl0qyIZE")


@st.cache_resource
def _worksheet_cached(spreadsheet_id, worksheet_title):
    """Cache handle worksheet agar pemanggilan sheet.worksheet tidak meminta metadata berulang."""
    return init_spreadsheet().worksheet(worksheet_title)


def get_worksheet(worksheet_title):
    """Ambil handle worksheet dari cache proses."""
    book = init_spreadsheet()
    return _worksheet_cached(book.id, worksheet_title)


@st.cache_data(ttl=3600, show_spinner=False)
def _worksheet_header_cached(spreadsheet_id, worksheet_title):
    """Header jarang berubah; cache satu jam untuk mengurangi Read API."""
    return _worksheet_cached(spreadsheet_id, worksheet_title).row_values(1)


# Koneksi Google Sheets dibuat secara lazy (saat benar-benar dibutuhkan).
# Dengan begitu, halaman login dapat dirender lebih dahulu tanpa menunggu Google.
client = None
sheet = None


def buat_paket_audit_sistem():
    """Audit baca-saja dengan Google Sheets values_batch_get untuk mengurangi API calls."""
    book = init_spreadsheet()
    hasil = {
        "nama_aplikasi": "Portal Bimbel Rumah Nazma",
        "waktu_audit": waktu_lokal().strftime("%Y-%m-%d %H:%M:%S WIB"),
        "mode": "READ_ONLY",
        "ringkasan_sheet": [],
        "pemeriksaan": [],
        "catatan_privasi": "Tidak memuat PIN, hash PIN, nomor telepon, nama siswa, jawaban, atau catatan pribadi.",
        "metode_baca": "Google Sheets batch_get",
    }

    target = [
        "Data_Siswa", "Akun_Pengguna", "Bank_Soal_Master",
        "Tugas_Sesi_Siswa_v2", "DB_Jawaban_Siswa", "DB_Nilai_Tugas",
        "Relasi_Orangtua_Siswa", "Relasi_Tutor_Siswa",
        "Status_Sesi_Tugas", "Riwayat_Latihan",
    ]
    worksheets = book.worksheets()  # satu permintaan metadata untuk daftar worksheet
    sheet_map = {ws.title: ws for ws in worksheets}

    def quote_title(title):
        return "'" + str(title).replace("'", "''") + "'"

    # Satu batch request mengambil header semua sheet dan isi tabel target.
    ranges = []
    range_keys = []
    for ws in worksheets:
        ranges.append(f"{quote_title(ws.title)}!1:1")
        range_keys.append((ws.title, "header"))
    for nama in target:
        if nama in sheet_map:
            ranges.append(f"{quote_title(nama)}!A:ZZ")
            range_keys.append((nama, "data"))

    hasil_batch = {}
    try:
        response = book.values_batch_get(ranges, params={"value_render_option": "FORMATTED_VALUE"})
        value_ranges = response.get("valueRanges", [])
        for i, key in enumerate(range_keys):
            values = value_ranges[i].get("values", []) if i < len(value_ranges) else []
            hasil_batch[key] = values
    except Exception as exc:
        pesan = str(exc)
        hasil["error_batch"] = pesan[:300]
        for ws in worksheets:
            hasil["ringkasan_sheet"].append({
                "nama_sheet": ws.title, "jumlah_baris_terisi": None,
                "jumlah_kolom_header": None, "header": [],
                "status_baca": "GAGAL_BATCH: " + pesan[:180],
            })
        hasil["total_sheet"] = len(hasil["ringkasan_sheet"])
        hasil["total_pemeriksaan"] = 1
        hasil["pemeriksaan"].append({
            "area": "Pembacaan Google Sheets", "status": "GAGAL_BACA",
            "jumlah": None, "temuan": "Permintaan batch gagal. Tunggu kuota pulih sebelum mencoba lagi."
        })
        return hasil

    headers_by_sheet = {}
    records = {}
    for ws in worksheets:
        header_values = hasil_batch.get((ws.title, "header"), [])
        headers = [str(x).strip() for x in header_values[0]] if header_values else []
        headers_by_sheet[ws.title] = headers
        jumlah = None
        status_baca = "OK"
        if ws.title in target:
            values = hasil_batch.get((ws.title, "data"), [])
            rows = []
            if values:
                data_headers = [str(x).strip() for x in values[0]]
                for physical_row, row in enumerate(values[1:], start=2):
                    if any(str(v).strip() for v in row):
                        record = {h: (row[i] if i < len(row) else "") for i, h in enumerate(data_headers) if h}
                        # Nomor baris hanya dipakai untuk diagnosis internal; tidak menyalin data pribadi.
                        record["__baris_sheet"] = physical_row
                        rows.append(record)
            records[ws.title] = rows
            jumlah = len(rows)
        hasil["ringkasan_sheet"].append({
            "nama_sheet": ws.title,
            "jumlah_baris_terisi": jumlah,
            "jumlah_kolom_header": len(headers),
            "header": headers,
            "status_baca": status_baca,
        })

    def cek(area, status, jumlah, temuan):
        hasil["pemeriksaan"].append({"area": area, "status": status, "jumlah": jumlah, "temuan": temuan})

    for nama in target:
        if nama not in sheet_map:
            cek(nama, "SHEET_TIDAK_ADA", None, "Worksheet tidak ditemukan.")

    siswa = records.get("Data_Siswa", [])
    id_siswa = [str(r.get("ID_SISWA") or r.get("ID_Siswa") or "").strip() for r in siswa]
    id_isi = [x for x in id_siswa if x]
    duplikat_id = len(id_isi) - len(set(id_isi))
    kosong_id = sum(1 for x in id_siswa if not x)
    # Diagnostik duplikasi: tanpa ID asli, nama, PIN, atau kontak.
    from collections import defaultdict
    grup_id = defaultdict(list)
    for rec in siswa:
        sid = str(rec.get("ID_SISWA") or rec.get("ID_Siswa") or "").strip()
        if sid:
            grup_id[sid].append(rec)
    grup_duplikat = [items for items in grup_id.values() if len(items) > 1]
    diagnostik_duplikat = []
    kolom_pembanding_aman = ["Jenjang", "Kelas", "Mapel_Diambil", "Status"]
    for nomor_grup, items in enumerate(sorted(grup_duplikat, key=lambda x: min(int(z.get("__baris_sheet", 0)) for z in x)), start=1):
        konflik = {}
        for kolom in kolom_pembanding_aman:
            nilai_unik = {str(z.get(kolom, "")).strip().casefold() for z in items}
            if len(nilai_unik) > 1:
                konflik[kolom] = len(nilai_unik)
        diagnostik_duplikat.append({
            "kelompok": f"DUP-{nomor_grup:04d}",
            "jumlah_baris": len(items),
            "nomor_baris_sheet": sorted(int(z.get("__baris_sheet", 0)) for z in items),
            "kolom_nonpribadi_berbeda": konflik,
        })
    hasil["diagnostik_duplikasi_id"] = {
        "jumlah_id_unik": len(grup_id),
        "jumlah_kelompok_duplikat": len(grup_duplikat),
        "jumlah_kemunculan_berulang": duplikat_id,
        "kelompok": diagnostik_duplikat,
        "catatan": "ID asli, nama, PIN, nomor telepon, dan data pribadi tidak disertakan. Cocokkan nomor baris di Data_Siswa secara langsung.",
    }
    cek("Identitas siswa", "PERLU_PERHATIAN" if duplikat_id or kosong_id else "OK", len(siswa),
        f"ID kosong: {kosong_id}; kemunculan ID berulang di luar pertama: {duplikat_id}; ID unik: {len(grup_id)}. Nama siswa tidak disertakan.")

    bank = records.get("Bank_Soal_Master", [])
    bank_header = set(headers_by_sheet.get("Bank_Soal_Master", []))
    kolom_bank = [c for c in ("Kode_Soal", "Jenjang", "Kelas", "Mapel", "Bentuk_Soal", "Teks_Soal", "Kunci_Jawaban", "Status") if c not in bank_header]
    tanpa_kunci = sum(1 for r in bank if str(r.get("Kunci_Jawaban", "")).strip() == "")
    tanpa_bobot = sum(1 for r in bank if "Bobot" in bank_header and str(r.get("Bobot", "")).strip() == "")
    cek("Bank soal", "PERLU_PERHATIAN" if kolom_bank or tanpa_kunci else "OK", len(bank),
        f"Header wajib tidak ada: {', '.join(kolom_bank) or '-'}; soal tanpa kunci: {tanpa_kunci}; bobot kosong: {tanpa_bobot}.")

    tugas = records.get("Tugas_Sesi_Siswa_v2", [])
    cek("Tugas", "OK", len(tugas), "Jumlah baris tugas terbaca; isi tugas tidak diekspor.")
    jawaban = records.get("DB_Jawaban_Siswa", [])
    cek("Jawaban siswa", "OK", len(jawaban), "Jumlah baris jawaban terbaca; teks jawaban tidak diekspor.")
    nilai = records.get("DB_Nilai_Tugas", [])
    cek("Nilai tugas", "OK", len(nilai), "Jumlah baris nilai terbaca; nilai individual tidak diekspor.")
    sesi = records.get("Status_Sesi_Tugas", [])
    sesi_aktif = sum(1 for r in sesi if str(r.get("Status", "")).strip().casefold() == "aktif")
    cek("Timer/sesi aktif", "PERLU_PERHATIAN" if sesi_aktif else "OK", sesi_aktif,
        "Jumlah sesi berstatus Aktif saat audit; tidak memuat ID siswa/tugas.")
    relasi_ortu = records.get("Relasi_Orangtua_Siswa", [])
    cek("Relasi orang tua", "OK", len(relasi_ortu), "Jumlah relasi terbaca; identitas relasi tidak diekspor.")
    relasi_tutor = records.get("Relasi_Tutor_Siswa", [])
    cek("Relasi tutor", "OK", len(relasi_tutor), "Jumlah relasi terbaca; identitas relasi tidak diekspor.")
    akun = records.get("Akun_Pengguna", [])
    cek("Akun pengguna", "OK", len(akun), "Hanya jumlah akun; username, PIN, hash, dan level akun tidak diekspor.")

    hasil["total_sheet"] = len(hasil["ringkasan_sheet"])
    hasil["total_pemeriksaan"] = len(hasil["pemeriksaan"])
    return hasil


def pastikan_koneksi():
    """Inisialisasi Google Sheets hanya saat login atau fitur terautentikasi dipakai."""
    global client, sheet
    if sheet is None:
        try:
            client = init_connection()
            sheet = init_spreadsheet()
        except Exception as exc:
            st.error(
                "Gagal terhubung ke Google Sheets. Periksa koneksi internet dan "
                "Streamlit Secrets. Jika muncul error 429, kuota Google Sheets "
                "mungkin sedang penuh. Detail: " + str(exc)
            )
            st.stop()
    return sheet


BATAS_UNGGAH_BYTES = 10 * 1024 * 1024   # batas di Apps Script; foto dikecilkan otomatis agar lolos
AMBANG_KOMPRES_BYTES = 1_000_000
SISI_MAKS_GAMBAR = 1800
KUALITAS_JPEG = 82
_EKSTENSI_FOTO = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")


def kompres_gambar_untuk_unggah(data, nama, mime):
    """Kecilkan foto (maks. 1800 px, JPEG) agar lolos batas 10 MB. Berkas non-foto dikembalikan apa adanya."""
    nama_l = str(nama or "").lower()
    mime_l = str(mime or "").lower()
    if not (mime_l.startswith("image/") or nama_l.endswith(_EKSTENSI_FOTO)):
        return data, nama, mime
    heic = nama_l.endswith((".heic", ".heif")) or "heic" in mime_l or "heif" in mime_l
    if len(data) <= AMBANG_KOMPRES_BYTES and not heic:
        return data, nama, mime
    if heic:
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except Exception:
            raise ValueError(
                f"Foto {nama} berformat HEIC belum bisa diproses. Di iPhone: Pengaturan, Kamera, Format, "
                "pilih 'Paling Kompatibel', atau kirim ulang sebagai JPG."
            )
    try:
        import io
        from PIL import Image, ImageOps
        gambar = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        gambar.thumbnail((SISI_MAKS_GAMBAR, SISI_MAKS_GAMBAR))
        if gambar.mode not in ("RGB", "L"):
            rgba = gambar.convert("RGBA")
            latar = Image.new("RGB", rgba.size, (255, 255, 255))
            latar.paste(rgba, mask=rgba.split()[-1])
            gambar = latar
        keluar = io.BytesIO()
        gambar.save(keluar, "JPEG", quality=KUALITAS_JPEG, optimize=True)
        baru = keluar.getvalue()
    except Exception:
        return data, nama, mime  # gambar tidak terbaca: biarkan apa adanya, batas ukuran tetap diperiksa
    if len(baru) >= len(data) and not heic:
        return data, nama, mime
    return baru, os.path.splitext(str(nama))[0] + ".jpg", "image/jpeg"


def upload_lampiran_ke_drive(file_bytes, file_name, mime_type):
    """Unggah lampiran ke Google Drive melalui Apps Script milik akun Bimbel."""
    try:
        file_bytes, file_name, mime_type = kompres_gambar_untuk_unggah(file_bytes, file_name, mime_type)
        if len(file_bytes) > BATAS_UNGGAH_BYTES:
            raise ValueError(
                "ukuran lebih dari 10 MB. Foto dikecilkan otomatis; untuk video atau audio, "
                "kompres dulu lalu unggah ulang."
            )
        cfg = st.secrets["drive_upload"]
        endpoint = str(cfg["web_app_url"]).strip()
        token = str(cfg["token"]).strip()
        if not endpoint or not token:
            raise ValueError("URL Apps Script atau token upload belum diatur di Streamlit Secrets.")

        payload = {
            "token": token,
            "fileName": file_name,
            "mimeType": mime_type or "application/octet-stream",
            "fileData": base64.b64encode(file_bytes).decode("ascii"),
        }
        folder_id = str(cfg.get("folder_id", "")).strip()
        if folder_id:
            payload["folderId"] = folder_id

        response = requests.post(endpoint, json=payload, timeout=120, allow_redirects=False)

        if response.status_code in (301, 302, 303, 307, 308) and response.headers.get("Location"):
            response = requests.get(response.headers["Location"], timeout=120)
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError:
            raise RuntimeError("Respons Apps Script bukan JSON. Periksa URL deployment Web App.")

        if not result.get("success") or not result.get("url"):
            raise RuntimeError(result.get("error", "Google Drive tidak mengembalikan link file."))
        return str(result["url"])
    except Exception as e:
        raise RuntimeError(f"Gagal mengunggah lampiran '{file_name}': {e}")


def get_or_create_worksheet(title, headers, rows="2000", cols="20"):
    """Ambil worksheet tanpa membaca seluruh isi setiap rerun.
    Header ditulis saat worksheet baru dibuat; worksheet lama dipertahankan apa adanya.
    """
    try:
        return get_worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=rows, cols=cols)
        ws.append_row(headers)
        return ws


# ---------------------------------------------------------------------------
# Cache pembacaan sheet per-sheet. Setiap penulisan lewat gspread menandai HANYA sheet yang ditulis
# sebagai usang, sehingga sheet lain tetap memakai cache (kuota baca Google tidak terkuras setelah
# setiap simpan). State disimpan di modul gspread agar bertahan antar-rerun dan dibagi antar-sesi.
# ---------------------------------------------------------------------------
_STATE_CACHE = gspread.__dict__.setdefault("_nazma_cache_state", {"data": {}, "tulis": {}, "semua": 0.0})
TTL_CACHE_SHEET = 180  # detik


def _pasang_penanda_tulis():
    import functools
    kelas_ws = getattr(gspread, "Worksheet", None)
    if kelas_ws is None or getattr(kelas_ws, "_nazma_dipatch", False):
        return
    for nama in ("update", "batch_update", "update_cell", "update_cells", "update_acell", "append_row",
                 "append_rows", "insert_row", "insert_rows", "delete_rows", "delete_row", "clear",
                 "batch_clear", "add_rows", "add_cols", "resize", "delete_columns", "insert_cols"):
        asli = getattr(kelas_ws, nama, None)
        if asli is None:
            continue
        def _bungkus(asli=asli):
            @functools.wraps(asli)
            def terbungkus(self, *a, **k):
                try:
                    return asli(self, *a, **k)
                finally:
                    _STATE_CACHE["tulis"][self.title] = time.time()
            return terbungkus
        setattr(kelas_ws, nama, _bungkus())
    # Pemeriksaan header (row_values(1)) dilayani dari cache nilai sheet: tidak memanggil Google lagi.
    asli_rv = getattr(kelas_ws, "row_values", None)
    if asli_rv is not None:
        @functools.wraps(asli_rv)
        def row_values_cache(self, row, *a, **k):
            if row == 1 and not a and not k:
                try:
                    nilai = _baca_values_cache(self.spreadsheet_id, self.title)
                    baris = list(nilai[0]) if nilai else []
                    while baris and str(baris[-1]) == "":
                        baris.pop()
                    return baris
                except Exception:
                    pass
            return asli_rv(self, row, *a, **k)
        kelas_ws.row_values = row_values_cache
    kelas_ss = getattr(gspread, "Spreadsheet", None)
    asli_ss = getattr(kelas_ss, "batch_update", None) if kelas_ss else None
    if asli_ss is not None:
        @functools.wraps(asli_ss)
        def batch_ss(self, *a, **k):
            try:
                return asli_ss(self, *a, **k)
            finally:
                _STATE_CACHE["semua"] = time.time()
        kelas_ss.batch_update = batch_ss
    kelas_ws._nazma_dipatch = True


_pasang_penanda_tulis()


def _kuota_habis(exc):
    pesan = str(exc).lower()
    return "429" in pesan or "quota exceeded" in pesan or "resource_exhausted" in pesan


def _baca_values_dengan_ulang(ws, boleh_pakai_salinan=False):
    """get_all_values dengan 3x percobaan saat kuota Google habis (jeda bertambah)."""
    terakhir = None
    for percobaan in range(3):
        try:
            return ws.get_all_values()
        except Exception as exc:
            terakhir = exc
            if not _kuota_habis(exc):
                raise
            time.sleep(1.5 * (percobaan + 1))
    raise terakhir


class _CacheBacaSheet:
    """Pengganti st.cache_data: cache per sheet, TTL 3 menit, usang hanya bila sheet itu ditulis."""

    def __call__(self, spreadsheet_id, worksheet_title):
        kunci = (spreadsheet_id, worksheet_title)
        sekarang = time.time()
        ent = _STATE_CACHE["data"].get(kunci)
        if (ent and sekarang - ent[0] < TTL_CACHE_SHEET
                and ent[0] >= _STATE_CACHE["tulis"].get(worksheet_title, 0.0)
                and ent[0] >= _STATE_CACHE["semua"]):
            return ent[1]
        ws_cached = _worksheet_cached(spreadsheet_id, worksheet_title)
        try:
            nilai = _baca_values_dengan_ulang(ws_cached)
        except Exception as exc:
            if ent and _kuota_habis(exc):
                return ent[1]  # kuota habis: pakai data terakhir yang berhasil dibaca
            raise
        _STATE_CACHE["data"][kunci] = (sekarang, nilai)
        return nilai

    def clear(self, *args, **kwargs):
        """Kompatibilitas: invalidasi sudah otomatis per sheet saat ada penulisan; tidak ada yang dihapus massal."""
        return None


_baca_values_cache = _CacheBacaSheet()


def baca_records_aman(ws, refresh=False):
    """Membaca sheet dengan cache 180 detik; refresh=True memaksa pembacaan terbaru."""
    try:
        values = _baca_values_dengan_ulang(ws) if refresh else _baca_values_cache(sheet.id, ws.title)
    except Exception as exc:
        # Jika cache/API gagal, jangan menyamarkan error dengan data kosong.
        raise RuntimeError(f"Gagal membaca worksheet {ws.title}: {exc}")
    if not values:
        return []
    raw_headers = [str(x).strip() for x in values[0]]
    headers = []
    used = set()
    for i, name in enumerate(raw_headers):
        if not name:
            name = f"_kolom_{i+1}"
        base = name
        suffix = 2
        while name in used:
            name = f"{base}_{suffix}"
            suffix += 1
        used.add(name)
        headers.append(name)
    records = []
    for nomor_baris, row in enumerate(values[1:], start=2):
        if not any(str(v).strip() for v in row):
            continue
        rec = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
        # Alias header agar kompatibel dengan variasi nama kolom di Google Sheets.
        # Data_Siswa milik pengguna memakai Nama_Siswa, sedangkan modul lama
        # membaca Nama_Lengkap. Sediakan keduanya tanpa mengubah struktur sheet.
        if "Nama_Siswa" in rec and "Nama_Lengkap" not in rec:
            rec["Nama_Lengkap"] = rec["Nama_Siswa"]
        elif "Nama_Lengkap" in rec and "Nama_Siswa" not in rec:
            rec["Nama_Siswa"] = rec["Nama_Lengkap"]

        # Header ID siswa bisa tertulis ID_Siswa atau ID_SISWA: sediakan keduanya.
        if "ID_SISWA" in rec and "ID_Siswa" not in rec:
            rec["ID_Siswa"] = rec["ID_SISWA"]
        elif "ID_Siswa" in rec and "ID_SISWA" not in rec:
            rec["ID_SISWA"] = rec["ID_Siswa"]
        rec["_baris"] = nomor_baris  # nomor baris ASLI di sheet (aman walau ada baris kosong)
        records.append(rec)
    return records



# =========================================================
# KEAMANAN PIN: PBKDF2-HMAC-SHA256 + salt unik
# =========================================================
_PIN_ITERATIONS = 310_000
_PIN_PREFIX = "pbkdf2_sha256"


def hash_pin(pin):
    pin = str(pin or "")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _PIN_ITERATIONS)
    return f"{_PIN_PREFIX}${_PIN_ITERATIONS}${salt.hex()}${digest.hex()}"


def verifikasi_pin(pin_input, stored_pin):
    stored = str(stored_pin or "").strip()
    entered = str(pin_input or "").strip()
    if not stored or not entered:
        return False, False
    if stored.startswith(_PIN_PREFIX + "$"):
        try:
            prefix, iterations, salt_hex, digest_hex = stored.split("$", 3)
            if prefix != _PIN_PREFIX:
                return False, False
            digest = hashlib.pbkdf2_hmac(
                "sha256", entered.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
            ).hex()
            return hmac.compare_digest(digest, digest_hex), False
        except (ValueError, TypeError):
            return False, False
    # PIN lama masih plaintext: izinkan login satu kali, lalu minta caller upgrade.
    return hmac.compare_digest(entered, stored), True


def upgrade_pin_lama(ws, record, field_name, pin_input):
    """Upgrade plaintext ke HASH setelah login benar; tidak menambah/mengubah header."""
    if not record or not record.get("_baris"):
        return
    headers = ws.row_values(1)
    if field_name not in headers:
        raise ValueError(f"Kolom {field_name} tidak ditemukan pada {ws.title}.")
    ws.update_cell(int(record["_baris"]), headers.index(field_name) + 1, hash_pin(pin_input))
    _baca_values_cache.clear()


def simpan_pin_baru(ws, record_aktif, field_name, pin_baru, identity_field=None, identity_value=None):
    """Simpan PIN hash pada satu baris akun yang tervalidasi."""
    headers = [str(x).strip() for x in _worksheet_header_cached(init_spreadsheet().id, ws.title)]
    if field_name not in headers:
        raise ValueError(f"Kolom {field_name} tidak ditemukan pada {ws.title}.")
    pin_hash_baru = hash_pin(pin_baru)

    if ws.title == "Pengaturan_Aplikasi" and "Kunci" in headers:
        rows = ws.get_all_values()
        key_idx = headers.index("Kunci")
        value_idx = headers.index(field_name)
        pin_rows = [
            i + 1 for i, row in enumerate(rows[1:], start=1)
            if len(row) > key_idx and str(row[key_idx]).strip() == "PIN_OWNER"
        ]
        if not pin_rows:
            raise ValueError("Baris PIN_OWNER tidak ditemukan.")
        canonical_row = pin_rows[0]
        ws.update_cell(canonical_row, value_idx + 1, pin_hash_baru)
        for row_number in sorted(pin_rows[1:], reverse=True):
            ws.delete_rows(row_number)
        nilai_tersimpan = ws.cell(canonical_row, value_idx + 1).value
        cocok_tersimpan, _ = verifikasi_pin(pin_baru, nilai_tersimpan)
        if not cocok_tersimpan:
            raise RuntimeError("Penulisan PIN Owner belum berhasil diverifikasi.")
    else:
        nomor_baris = int(record_aktif.get("_baris", 0) or 0)
        if nomor_baris < 2:
            raise ValueError("Baris akun tidak valid. Muat ulang halaman lalu coba lagi.")
        if identity_field and identity_value:
            if identity_field not in headers:
                raise ValueError(f"Kolom identitas {identity_field} tidak ditemukan.")
            row_values = ws.row_values(nomor_baris)
            idx_identitas = headers.index(identity_field)
            nilai_identitas = row_values[idx_identitas] if idx_identitas < len(row_values) else ""
            if str(nilai_identitas).strip().casefold() != str(identity_value).strip().casefold():
                raise ValueError("Identitas akun berubah. Muat ulang daftar akun sebelum reset PIN.")

        ws.update_cell(nomor_baris, headers.index(field_name) + 1, pin_hash_baru)
        nilai_tersimpan = ws.cell(nomor_baris, headers.index(field_name) + 1).value
        cocok_tersimpan, _ = verifikasi_pin(pin_baru, nilai_tersimpan)
        if not cocok_tersimpan:
            raise RuntimeError(
                f"Penulisan PIN ke baris {nomor_baris} belum terverifikasi. "
                "PIN tidak boleh dianggap berhasil diubah."
            )

    _baca_values_cache.clear()


def pastikan_pemetaan_id_siswa(ws_akun, ws_siswa):
    """
    Membuat pemetaan ID_SISWA ke akun siswa di memori menggunakan cache.
    Tidak melakukan get_all_values langsung dan tidak menulis ke Sheets saat login.
    """
    akun_rows = baca_records_aman(ws_akun)
    siswa_rows = baca_records_aman(ws_siswa)

    nama_ke_siswa = {}
    nama_ganda = set()
    for siswa in siswa_rows:
        sid = str(siswa.get("ID_SISWA", siswa.get("ID_Siswa", ""))).strip().upper()
        nama = str(siswa.get("Nama_Siswa", siswa.get("Nama_Lengkap", ""))).strip().casefold()
        if not sid or not nama:
            continue
        if nama in nama_ke_siswa:
            nama_ganda.add(nama)
        else:
            nama_ke_siswa[nama] = sid
    for nama in nama_ganda:
        nama_ke_siswa.pop(nama, None)

    hasil = []
    for akun in akun_rows:
        akun_baru = dict(akun)
        level = str(akun.get("Level_Akses", "")).strip().casefold()
        if level == "siswa":
            id_tersimpan = str(akun.get("ID_SISWA", "")).strip().upper()
            if not id_tersimpan:
                nama_akun = str(akun.get("Nama_Pengguna", "")).strip().casefold()
                id_tersimpan = nama_ke_siswa.get(nama_akun, "")
            akun_baru["ID_SISWA"] = id_tersimpan
        hasil.append(akun_baru)
    return hasil


def ambil_pin_terkini(ws, record, field_name):
    """Baca PIN langsung dari baris Google Sheets; hindari record cache/session yang usang."""
    headers = [str(x).strip() for x in ws.row_values(1)]
    if field_name not in headers:
        raise ValueError(f"Kolom {field_name} tidak ditemukan pada {ws.title}.")
    nomor_baris = int(record.get("_baris", 0) or 0)
    if nomor_baris < 2:
        raise ValueError("Nomor baris akun tidak valid. Silakan logout lalu login kembali.")
    values = ws.row_values(nomor_baris)
    idx = headers.index(field_name)
    return values[idx] if idx < len(values) else ""


def form_ganti_pin(ws, record, field_name, key_prefix, identity_field=None, identity_value=None):
    """Form ganti PIN; validasi identitas dilakukan pada baris target, tanpa membaca seluruh sheet."""
    with st.container(border=True):
        st.markdown("#### 🔐 Keamanan Akun — Ganti PIN")
        st.caption("Username dan identitas akun tidak berubah. Hanya PIN yang diperbarui.")
        with st.form(f"{key_prefix}_form_ganti_pin"):
            pin_lama = st.text_input("PIN saat ini", type="password", key=f"{key_prefix}_pin_lama")
            pin_baru = st.text_input("PIN baru (minimal 6 angka)", type="password", key=f"{key_prefix}_pin_baru")
            konfirmasi = st.text_input("Ulangi PIN baru", type="password", key=f"{key_prefix}_pin_konfirmasi")
            submit = st.form_submit_button("Simpan PIN Baru")
        if submit:
            try:
                record_aktif = dict(record)
                nomor_baris = int(record_aktif.get("_baris", 0) or 0)
                if nomor_baris < 2:
                    raise ValueError("Baris akun tidak valid. Silakan logout lalu login kembali.")

                headers = [str(x).strip() for x in _worksheet_header_cached(init_spreadsheet().id, ws.title)]
                row_values = ws.row_values(nomor_baris)
                if identity_field and identity_value:
                    idx_identity = headers.index(identity_field)
                    actual_identity = row_values[idx_identity] if idx_identity < len(row_values) else ""
                    if str(actual_identity).strip().casefold() != str(identity_value).strip().casefold():
                        raise ValueError("Identitas akun tidak cocok dengan sesi login. Silakan logout dan login kembali.")
                idx_pin = headers.index(field_name)
                pin_tersimpan = row_values[idx_pin] if idx_pin < len(row_values) else ""

                cocok, _ = verifikasi_pin(pin_lama, pin_tersimpan)
                if not cocok:
                    st.error("PIN saat ini tidak sesuai. Jika PIN baru saja di-reset Owner, logout lalu login kembali dengan PIN hasil reset.")
                elif not pin_baru.isdigit() or len(pin_baru) < 6:
                    st.error("PIN baru harus berupa angka dan minimal 6 digit.")
                elif pin_baru != konfirmasi:
                    st.error("Konfirmasi PIN baru tidak sama.")
                elif hmac.compare_digest(pin_lama.strip(), pin_baru.strip()):
                    st.error("PIN baru harus berbeda dari PIN saat ini.")
                else:
                    simpan_pin_baru(
                        ws, record_aktif, field_name, pin_baru,
                        identity_field=identity_field, identity_value=identity_value
                    )
                    st.success("PIN berhasil diperbarui dan disimpan dalam bentuk HASH.")
                    st.rerun()
            except Exception as exc:
                st.error(f"PIN belum berhasil diperbarui: {exc}")


def header_cocok(actual, expected):
    """Bandingkan header sheet dengan struktur yang diharapkan (abaikan kolom kosong di ujung kanan)."""
    a = [str(x).strip() for x in actual]
    while a and a[-1] == "":
        a.pop()
    return a == list(expected)


def get_siswa_aktif():
    rows = baca_records_aman(get_worksheet("Data_Siswa"))
    return [
        str(s.get("Nama_Lengkap", "")).strip()
        for s in rows
        if str(s.get("Status", "Aktif")).strip().lower() not in ["nonaktif", "tidak aktif"]
        and str(s.get("Nama_Lengkap", "")).strip()
    ]


def cari_siswa_terbatas(kata, daftar, minimal=3, maksimal=8):
    """Cari nama siswa dengan ketikan. Mengembalikan (hasil, pesan); daftar penuh tidak pernah ditampilkan."""
    kata = str(kata or "").strip().casefold()
    if not kata:
        return [], ""
    if len(kata) < minimal:
        return [], f"Ketik minimal {minimal} huruf untuk mencari."
    cocok = sorted({str(n).strip() for n in (daftar or []) if str(n).strip() and kata in str(n).casefold()},
                   key=str.casefold)
    if not cocok:
        return [], "Siswa aktif tidak ditemukan."
    if len(cocok) > maksimal:
        return cocok[:maksimal], f"Hanya {maksimal} nama pertama yang ditampilkan. Ketik nama lebih lengkap untuk mempersempit."
    return cocok, ""


def get_siswa_record_by_nama(nama):
    """Ambil satu identitas siswa berdasarkan nama; gagal tertutup jika nama ganda."""
    target = str(nama or "").strip().casefold()
    if not target:
        return None
    rows = baca_records_aman(get_worksheet("Data_Siswa"))
    cocok = [r for r in rows
             if str(r.get("Nama_Lengkap", "")).strip().casefold() == target
             and str(r.get("Status", "Aktif")).strip().casefold() not in ("nonaktif", "tidak aktif")]
    if len(cocok) != 1 or not str(cocok[0].get("ID_Siswa", "")).strip():
        return None
    return cocok[0]


def get_siswa_id_by_nama(nama):
    """Kompatibilitas nama lama; tidak memilih ID pertama jika nama siswa ganda."""
    record = get_siswa_record_by_nama(nama)
    return str(record.get("ID_Siswa", "")).strip() if record else ""


def adalah_akun_ortu(akun):
    level = str(akun.get("Level_Akses", "") or "").strip().casefold()
    return any(x in level for x in ("ortu", "orang tua", "orangtua", "wali"))


def get_bank_soal():
    """Bank soal tunggal dengan 15 header baru."""
    ws = get_worksheet("Bank_Soal_Master")
    wajib = {"Kode_Soal", "Jenjang", "Kelas", "Mapel", "Bab_Atau_Topik", "Bentuk_Soal", "Teks_Soal", "Opsi_Jawaban", "Kunci_Jawaban", "Status"}
    kurang = sorted(wajib - set(ws.row_values(1)))
    if kurang:
        raise ValueError("Kolom Bank_Soal_Master belum lengkap: " + ", ".join(kurang))
    return [r for r in baca_records_aman(ws) if str(r.get("Status", "")).strip().lower() in ("aktif", "ya", "true", "1")]


def ubah_soal_untuk_tugas(q):
    """Salin soal ke tugas tanpa mengubah bank soal asli."""
    bentuk = str(q.get("Bentuk_Soal", ""))
    raw = str(q.get("Opsi_Jawaban", "") or "")
    pasangan = {}
    opsi = normalisasi_opsi(raw)
    if "menjodohkan" in bentuk.lower():
        pasangan = json.loads(raw)
        if not isinstance(pasangan, dict) or not isinstance(pasangan.get("kolom_A"), dict) or not isinstance(pasangan.get("kolom_B"), dict):
            raise ValueError("Format menjodohkan tidak valid: " + str(q.get("Kode_Soal", "")))
        opsi = []
    return {
        "ID_Soal": str(q.get("Kode_Soal", "")),
        "Jenjang": str(q.get("Jenjang", "")), "Kelas": str(q.get("Kelas", "")),
        "Mapel": str(q.get("Mapel", "")), "Topik": str(q.get("Bab_Atau_Topik", "")),
        "Bentuk_Soal": bentuk, "Teks_Soal": str(q.get("Teks_Soal", "")),
        "Url_Gambar": str(q.get("URL_Gambar", "")).strip(),
        "Url_Audio": str(q.get("URL_Audio", "")).strip(),
        "Url_Video": str(q.get("URL_Video", "")).strip(),
        "Url_Bacaan": str(q.get("URL_Bacaan", "")).strip(),
        "Opsi_List": opsi,
        "Pasangan": pasangan, "Kunci": str(q.get("Kunci_Jawaban", "")),
        "Pembahasan": str(q.get("Pembahasan", "")),
    }

# =========================================================
# LAMPIRAN MULTIFILE & FLIPBOOK
# Format: img::URL|pdf::URL|doc::URL|link::URL. URL lama tetap didukung.
# =========================================================
def drive_id(url):
    match = re.search(r"/d/([\w-]+)|[?&]id=([\w-]+)", str(url or ""))
    return (match.group(1) or match.group(2)) if match else None


def jenis_dari_mime(mime, nama=""):
    mime, nama = str(mime or "").lower(), str(nama or "").lower()
    if mime.startswith("image/") or nama.endswith((".png", ".jpg", ".jpeg")):
        return "img"
    if mime == "application/pdf" or nama.endswith(".pdf"):
        return "pdf"
    return "doc"


def parse_lampiran(teks):
    hasil = []
    for bagian in str(teks or "").split("|"):
        bagian = bagian.strip()
        if not bagian:
            continue
        jenis, url = bagian.split("::", 1) if "::" in bagian else ("link", bagian)
        jenis, url = jenis.strip().lower(), url.strip()
        if url.startswith(("https://", "http://")):
            hasil.append((jenis, url))
    return hasil


def img_url(url):
    fid = drive_id(url)
    return f"https://lh3.googleusercontent.com/d/{fid}=w1600" if fid else url


def media_direct_url(url):
    """Ubah link berbagi Google Drive menjadi URL unduhan untuk pemutar media."""
    url = str(url or "").strip()
    fid = drive_id(url)
    return f"https://drive.google.com/uc?export=download&id={fid}" if fid else url


def tampilkan_media_soal(soal):
    """Tampilkan media pendukung soal; semua field bersifat opsional."""
    audio = str(soal.get("Url_Audio", "") or "").strip()
    video = str(soal.get("Url_Video", "") or "").strip()
    bacaan = str(soal.get("Url_Bacaan", "") or "").strip()

    if audio.startswith(("https://", "http://")):
        st.markdown("🎧 **Audio soal**")
        audio_id = drive_id(audio)
        if audio_id:
            # Gunakan pemutar preview resmi Google Drive. Link unduhan langsung
            # dapat mengembalikan halaman konfirmasi, sehingga st.audio membaca 0:00.
            preview_url = f"https://drive.google.com/file/d/{audio_id}/preview"
            components.iframe(preview_url, height=150, scrolling=False)
        else:
            st.audio(audio)
        st.link_button("↗ Buka / Unduh Audio", audio, use_container_width=True)

    if video.startswith(("https://", "http://")):
        st.markdown("🎬 **Video soal**")
        st.video(media_direct_url(video))
        st.link_button("↗ Buka / Unduh Video", video, use_container_width=True)

    if bacaan.startswith(("https://", "http://")):
        st.link_button("📖 Buka bahan bacaan", bacaan, use_container_width=True)


def tampilkan_lampiran(url, tinggi=620):
    url = str(url or "").strip()
    if not url.startswith(("https://", "http://")):
        st.warning("Lampiran belum tersedia. Hubungi tutor.")
        return
    fid = drive_id(url)
    src = f"https://drive.google.com/file/d/{fid}/preview" if fid else url
    components.iframe(src, height=tinggi, scrolling=True)
    fid = drive_id(url)
    if fid:
        url_unduh = f"https://drive.google.com/uc?export=download&id={fid}"
    else:
        url_unduh = url
    col_buka, col_unduh = st.columns(2)
    with col_buka:
        st.link_button("↗ Buka lampiran", url, use_container_width=True)
    with col_unduh:
        st.link_button("⬇️ Unduh materi", url_unduh, use_container_width=True)


def flipbook_gambar(urls, tinggi=700):
    imgs = json.dumps([img_url(u) for u in urls], ensure_ascii=False)
    html = r'''<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
html,body{margin:0;padding:0;background:#1e293b;font-family:Arial,sans-serif}
#book-wrap{width:100%;display:flex;justify-content:center;align-items:center;padding:8px 0;box-sizing:border-box}
#book{margin:0 auto}.page{background:#fff;overflow:hidden}
.page img{width:100%;height:100%;object-fit:contain;display:block}
.nav{display:flex;justify-content:center;align-items:center;gap:12px;padding:10px;color:#fff;flex-wrap:wrap}
.nav button{padding:9px 14px;border:0;border-radius:8px;background:#dbeafe;color:#123568;font-weight:600}
#info{min-width:52px;text-align:center}#error{color:#fff;text-align:center;padding:12px}
</style></head><body>
<div id="book-wrap"><div id="book"></div></div>
<div class="nav"><button id="prev">◀ Sebelumnya</button><span id="info">Memuat...</span><button id="next">Berikutnya ▶</button></div>
<div id="error" hidden></div>
<script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"></script>
<script>
(function(){
 const imgs=__IMGS__, book=document.getElementById('book'), info=document.getElementById('info'), err=document.getElementById('error');
 if(!Array.isArray(imgs)||!imgs.length){info.textContent='Tidak ada halaman.';return;}
 if(typeof St==='undefined'||!St.PageFlip){err.hidden=false;err.textContent='Flipbook gagal dimuat. Periksa koneksi internet, atau buka foto melalui tautan lampiran.';info.textContent='';return;}
 imgs.forEach(src=>{const d=document.createElement('div');d.className='page';const im=document.createElement('img');im.src=src;im.alt='Halaman materi';d.appendChild(im);book.appendChild(d);});
 const pf=new St.PageFlip(book,{width:420,height:588,size:'stretch',minWidth:260,maxWidth:560,minHeight:360,maxHeight:784,showCover:false,usePortrait:true,mobileScrollSupport:true,drawShadow:true,flippingTime:600});
 pf.loadFromHTML(book.querySelectorAll('.page'));
 const update=()=>{info.textContent=(pf.getCurrentPageIndex()+1)+' / '+pf.getPageCount();};
 document.getElementById('prev').addEventListener('click',()=>pf.flipPrev());
 document.getElementById('next').addEventListener('click',()=>pf.flipNext());
 pf.on('flip',update);setTimeout(update,250);
})();
</script></body></html>'''.replace('__IMGS__', imgs)
    components.html(html, height=tinggi, scrolling=False)


def tampilkan_materi(teks_lampiran):
    items = parse_lampiran(teks_lampiran)
    if not items:
        st.warning("Lampiran belum tersedia. Hubungi tutor.")
        return
    gambar = [url for jenis, url in items if jenis == "img"]
    lainnya = [(jenis, url) for jenis, url in items if jenis != "img"]
    if gambar:
        st.markdown("#### 🖼️ Flipbook Materi")
        flipbook_gambar(gambar)
        for i, url_gambar in enumerate(gambar, 1):
            st.link_button(f"⬇️ Unduh halaman {i}", url_gambar, use_container_width=True)
    for jenis, url in lainnya:
        if jenis == "video":
            st.markdown("#### 🎬 Video Pembelajaran")
            fid = drive_id(url)
            st.video(f"https://drive.google.com/uc?export=download&id={fid}" if fid else url)
            st.link_button("↗ Buka / Unduh Video", url, use_container_width=True)
        elif jenis == "audio":
            st.markdown("#### 🎧 Audio Listening")
            fid = drive_id(url)
            st.audio(f"https://drive.google.com/uc?export=download&id={fid}" if fid else url)
            st.link_button("↗ Buka / Unduh Audio", url, use_container_width=True)
        else:
            st.markdown("#### 📄 Dokumen PDF" if jenis == "pdf" else "#### 📎 Dokumen" if jenis == "doc" else "#### 🔗 Materi / Flipbook Eksternal")
            tampilkan_lampiran(url)





# =========================================================
# JURNAL MENGAJAR HARIAN + CATATAN PERKEMBANGAN SISWA
# Disimpan terpisah dari catatan lama agar data lama tetap aman.
# =========================================================
JURNAL_HARIAN_HEADERS = [
    "ID_Jurnal", "ID_User", "ID_Tutor", "Tanggal", "Daftar_Siswa",
    "Daftar_Mapel", "Materi_Dibahas", "Evaluasi_Harian",
    "Catatan_Tutor", "Pengingat_Berikutnya", "Dibuat_Pada", "Diperbarui_Pada"
]
CATATAN_PERKEMBANGAN_HEADERS = [
    "ID_Riwayat", "ID_User", "ID_Tutor", "Nama_Siswa", "Kelas",
    "Tanggal_Catatan", "Perkembangan", "Kesulitan",
    "Perhatian_Tutor", "Rencana_Berikutnya", "Dibuat_Pada"
]


def get_jurnal_harian_worksheet():
    ws = get_or_create_worksheet(
        "Jurnal_Mengajar_Harian", JURNAL_HARIAN_HEADERS,
        rows="5000", cols=str(len(JURNAL_HARIAN_HEADERS))
    )
    if not header_cocok(ws.row_values(1), JURNAL_HARIAN_HEADERS):
        raise ValueError(
            "Header Jurnal_Mengajar_Harian tidak sesuai. Data tidak ditulis; "
            f"header terbaca: {ws.row_values(1)!r}"
        )
    return ws


def get_catatan_perkembangan_worksheet():
    ws = get_or_create_worksheet(
        "Catatan_Perkembangan_Tutor", CATATAN_PERKEMBANGAN_HEADERS,
        rows="5000", cols=str(len(CATATAN_PERKEMBANGAN_HEADERS))
    )
    if not header_cocok(ws.row_values(1), CATATAN_PERKEMBANGAN_HEADERS):
        raise ValueError(
            "Header Catatan_Perkembangan_Tutor tidak sesuai. Data tidak ditulis; "
            f"header terbaca: {ws.row_values(1)!r}"
        )
    return ws


def ambil_jurnal_harian(id_user):
    if not id_user:
        return []
    ws = get_jurnal_harian_worksheet()
    return [
        r for r in baca_records_aman(ws, refresh=True)
        if str(r.get("ID_User", "")).strip() == str(id_user).strip()
    ]


def simpan_atau_perbarui_jurnal(
    id_user, id_tutor, tanggal, daftar_siswa, daftar_mapel,
    materi_dibahas, evaluasi, catatan_tutor, pengingat
):
    if not id_user:
        raise ValueError("ID akun tutor tidak ditemukan. Silakan login ulang.")
    ws = get_jurnal_harian_worksheet()
    headers = [str(x).strip() for x in ws.row_values(1)]
    rows = ws.get_all_values()
    tanggal_text = str(tanggal)
    idx_user, idx_tanggal = headers.index("ID_User"), headers.index("Tanggal")
    target_row = None
    existing_id = ""
    for row_no, row in enumerate(rows[1:], start=2):
        if (len(row) > max(idx_user, idx_tanggal)
                and row[idx_user] == str(id_user)
                and row[idx_tanggal] == tanggal_text):
            target_row = row_no
            existing_id = row[headers.index("ID_Jurnal")] if len(row) > headers.index("ID_Jurnal") else ""
            break
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    values = [
        existing_id or ("JRN-" + uuid.uuid4().hex[:10].upper()),
        str(id_user), str(id_tutor or ""), tanggal_text,
        json.dumps(daftar_siswa, ensure_ascii=False),
        json.dumps(daftar_mapel, ensure_ascii=False),
        str(materi_dibahas or "").strip(),
        str(evaluasi or "").strip(), str(catatan_tutor or "").strip(),
        str(pengingat or "").strip(),
        now if not target_row else (rows[target_row - 1][headers.index("Dibuat_Pada")]
            if len(rows[target_row - 1]) > headers.index("Dibuat_Pada") else now),
        now
    ]
    if target_row:
        ws.update(f"A{target_row}:L{target_row}", [values], value_input_option="RAW")
        hasil = "diperbarui"
    else:
        ws.append_row(values, value_input_option="RAW")
        hasil = "disimpan"
    _baca_values_cache.clear()
    return hasil


def ambil_catatan_perkembangan_siswa(id_user, nama_siswa):
    if not id_user or not nama_siswa:
        return []
    ws = get_catatan_perkembangan_worksheet()
    return [
        r for r in baca_records_aman(ws, refresh=True)
        if str(r.get("ID_User", "")).strip() == str(id_user).strip()
        and str(r.get("Nama_Siswa", "")).strip().casefold() == str(nama_siswa).strip().casefold()
    ]


def simpan_catatan_perkembangan_siswa(
    id_user, id_tutor, nama_siswa, kelas, tanggal,
    perkembangan, kesulitan, perhatian, rencana
):
    if not id_user:
        raise ValueError("ID akun tutor tidak ditemukan.")
    if not str(nama_siswa or "").strip():
        raise ValueError("Nama siswa wajib diisi.")
    if not any(str(x or "").strip() for x in (perkembangan, kesulitan, perhatian, rencana)):
        raise ValueError("Isi minimal satu bagian catatan perkembangan.")
    ws = get_catatan_perkembangan_worksheet()
    ws.append_row([
        "PRG-" + uuid.uuid4().hex[:10].upper(), str(id_user), str(id_tutor or ""),
        str(nama_siswa).strip(), str(kelas or "").strip(), str(tanggal),
        str(perkembangan or "").strip(), str(kesulitan or "").strip(),
        str(perhatian or "").strip(), str(rencana or "").strip(),
        waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    ], value_input_option="RAW")
    _baca_values_cache.clear()


def _parse_json_list(value):
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


# =========================================================
# LIBRARY MATERI PRIBADI TUTOR
# File disimpan di Google Drive; indeks dan kepemilikan disimpan di Sheets.
# =========================================================
LIBRARY_TUTOR_HEADERS = [
    "ID_Media", "ID_User", "ID_Tutor", "Nama_File", "Mime_Type",
    "File_ID_Drive", "URL_Drive", "Ukuran_Bytes", "Kata_Kunci",
    "Tanggal_Upload", "Status"
]


def get_library_tutor_worksheet():
    ws = get_or_create_worksheet(
        "Library_Media_Tutor", LIBRARY_TUTOR_HEADERS,
        rows="5000", cols=str(len(LIBRARY_TUTOR_HEADERS))
    )
    actual = ws.row_values(1)
    if not header_cocok(actual, LIBRARY_TUTOR_HEADERS):
        raise ValueError(
            "Header Library_Media_Tutor tidak sesuai. Tidak ada data yang ditulis. "
            f"Header terbaca: {actual!r}"
        )
    return ws


def simpan_media_ke_library(id_user, id_tutor, nama_file, mime_type, url_drive, ukuran=0, kata_kunci=""):
    if not id_user:
        raise ValueError("ID akun tutor tidak ditemukan. Silakan login ulang.")
    fid = drive_id(url_drive)
    if not fid:
        raise ValueError("ID file Google Drive tidak berhasil dibaca dari tautan upload.")
    ws = get_library_tutor_worksheet()
    # Hindari membuat indeks ganda jika upload yang sama terkirim ulang.
    records = baca_records_aman(ws, refresh=True)
    for rec in records:
        if (str(rec.get("ID_User", "")) == str(id_user)
                and str(rec.get("File_ID_Drive", "")) == fid
                and str(rec.get("Status", "Aktif")) == "Aktif"):
            return rec.get("ID_Media", "")
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    media_id = "MED-" + uuid.uuid4().hex[:10].upper()
    ws.append_row([
        media_id, str(id_user), str(id_tutor or ""), str(nama_file),
        str(mime_type or "application/octet-stream"), fid, str(url_drive),
        str(int(ukuran or 0)), str(kata_kunci or ""), now, "Aktif"
    ], value_input_option="RAW")
    _baca_values_cache.clear()
    return media_id


def ambil_library_tutor(id_user, kata_kunci=""):
    if not id_user:
        return []
    ws = get_library_tutor_worksheet()
    q = str(kata_kunci or "").strip().casefold()
    hasil = []
    for rec in baca_records_aman(ws, refresh=True):
        if str(rec.get("ID_User", "")).strip() != str(id_user).strip():
            continue
        if str(rec.get("Status", "Aktif")).strip().lower() != "aktif":
            continue
        gabung = " ".join([
            str(rec.get("Nama_File", "")), str(rec.get("Kata_Kunci", "")),
            str(rec.get("Mime_Type", ""))
        ]).casefold()
        if q and q not in gabung:
            continue
        hasil.append({
            "id": str(rec.get("File_ID_Drive", "")),
            "name": str(rec.get("Nama_File", "")),
            "mimeType": str(rec.get("Mime_Type", "")),
            "webViewLink": str(rec.get("URL_Drive", "")),
            "size": str(rec.get("Ukuran_Bytes", "")),
            "source": "Library Tutor",
            "media_id": str(rec.get("ID_Media", ""))
        })
    return sorted(hasil, key=lambda x: x.get("name", "").casefold())


def nonaktifkan_media_library(media_id, id_user):
    ws = get_library_tutor_worksheet()
    headers = [str(x).strip() for x in ws.row_values(1)]
    rows = ws.get_all_values()
    i_mid, i_uid, i_status = [headers.index(x) for x in ("ID_Media", "ID_User", "Status")]
    for row_no, row in enumerate(rows[1:], start=2):
        if (len(row) > max(i_mid, i_uid, i_status)
                and row[i_mid] == str(media_id)
                and row[i_uid] == str(id_user)):
            ws.update_cell(row_no, i_status + 1, "Dihapus")
            _baca_values_cache.clear()
            return True
    return False


# =========================================================
# RUANG KERJA BERANDA TUTOR (MODUL BARU, TERPISAH DARI FITUR LAMA)
# =========================================================
CATATAN_TUTOR_HEADERS = [
    "ID_Catatan", "ID_User", "ID_Tutor", "Jenis_Catatan", "Tanggal",
    "Mapel", "Kelas", "Topik", "Isi_Catatan", "Pengingat",
    "Status", "Dibuat_Pada", "Diperbarui_Pada"
]


def get_catatan_tutor_worksheet():
    """Worksheet khusus ruang kerja tutor; tidak mengubah worksheet lama."""
    ws = get_or_create_worksheet(
        "Catatan_Tutor_Ruang_Kerja", CATATAN_TUTOR_HEADERS, rows="3000", cols=str(len(CATATAN_TUTOR_HEADERS))
    )
    actual = ws.row_values(1)
    if not header_cocok(actual, CATATAN_TUTOR_HEADERS):
        raise ValueError(
            "Header Catatan_Tutor_Ruang_Kerja tidak sesuai. Data tidak ditulis; "
            f"header terbaca: {actual!r}"
        )
    return ws


def ambil_catatan_tutor(id_user):
    if not id_user:
        return []
    ws = get_catatan_tutor_worksheet()
    return [r for r in baca_records_aman(ws, refresh=True)
            if str(r.get("ID_User", "")).strip() == str(id_user).strip()
            and str(r.get("Status", "Aktif")).strip().lower() != "dihapus"]


def simpan_catatan_tutor(id_user, id_tutor, jenis, tanggal, mapel, kelas, topik, isi, pengingat=""):
    if not id_user:
        raise ValueError("ID akun tutor tidak ditemukan. Silakan logout lalu login kembali.")
    if not str(isi or "").strip() and not str(topik or "").strip():
        raise ValueError("Isi catatan atau topik wajib diisi.")
    ws = get_catatan_tutor_worksheet()
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        "CTT-" + uuid.uuid4().hex[:10].upper(), str(id_user), str(id_tutor or ""),
        str(jenis), str(tanggal), str(mapel), str(kelas), str(topik),
        str(isi or "").strip(), str(pengingat or "").strip(), "Aktif", now, now
    ], value_input_option="RAW")
    _baca_values_cache.clear()


def ubah_status_catatan_tutor(id_catatan, id_user, status_baru):
    ws = get_catatan_tutor_worksheet()
    headers = [str(x).strip() for x in ws.row_values(1)]
    rows = ws.get_all_values()
    idx_id, idx_user, idx_status, idx_update = [headers.index(x) for x in
        ("ID_Catatan", "ID_User", "Status", "Diperbarui_Pada")]
    for nomor, row in enumerate(rows[1:], start=2):
        if (len(row) > max(idx_id, idx_user)
                and row[idx_id] == str(id_catatan)
                and row[idx_user] == str(id_user)):
            ws.update_cell(nomor, idx_status + 1, status_baru)
            ws.update_cell(nomor, idx_update + 1, waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"))
            _baca_values_cache.clear()
            return True
    return False


@st.cache_data(ttl=90, show_spinner=False)
def cari_file_google_drive(kata_kunci):
    """Cari lintas file Drive yang dapat diakses service account; hasil dibatasi 5 halaman."""
    qtext = str(kata_kunci or "").strip()
    if not qtext:
        return []
    info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    creds.refresh(GoogleAuthRequest())
    # Escape apostrof untuk Drive query language.
    safe = qtext.replace("\\", "\\\\").replace("'", "\\'")
    media_filter = (
        "mimeType = 'application/pdf' or "
        "mimeType contains 'image/' or "
        "mimeType contains 'audio/' or "
        "mimeType contains 'video/'"
    )
    query = (
        f"trashed = false and ({media_filter}) and "
        f"(name contains '{safe}' or fullText contains '{safe}')"
    )
    hasil, page_token = [], None
    for _ in range(5):
        params = {
            "q": query, "pageSize": 100,
            "orderBy": "modifiedTime desc",
            "fields": "nextPageToken,files(id,name,mimeType,webViewLink,modifiedTime,size)",
            "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"
        }
        if page_token:
            params["pageToken"] = page_token
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {creds.token}"}, params=params, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        hasil.extend(payload.get("files", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return hasil


def url_preview_drive(file_id):
    return f"https://drive.google.com/file/d/{file_id}/preview"


def ambil_bytes_media_drive(file_id, batas_mb=30):
    """Ambil isi file Drive publik sebagai bytes, bukan memberikan halaman HTML Drive ke player."""
    if not file_id:
        raise ValueError("ID file Google Drive tidak tersedia.")
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    with requests.get(
        url,
        stream=True,
        allow_redirects=True,
        timeout=(15, 90),
        headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"},
    ) as response:
        response.raise_for_status()
        content_type = str(response.headers.get("Content-Type", "")).lower()
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > batas_mb * 1024 * 1024:
            raise ValueError(f"File lebih besar dari batas pratinjau {batas_mb} MB.")
        chunks, total = [], 0
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > batas_mb * 1024 * 1024:
                raise ValueError(f"File lebih besar dari batas pratinjau {batas_mb} MB.")
            chunks.append(chunk)
        data = b"".join(chunks)
    # Drive kadang mengembalikan halaman HTML izin/konfirmasi, bukan konten media.
    awal = data[:512].lstrip().lower()
    if "text/html" in content_type or awal.startswith(b"<!doctype html") or awal.startswith(b"<html"):
        raise RuntimeError(
            "Google Drive mengirim halaman HTML, bukan file media. Periksa izin Anyone with the link "
            "dan pastikan deployment Apps Script sudah diperbarui."
        )
    if not data:
        raise RuntimeError("File media kosong atau tidak dapat diunduh dari Google Drive.")
    return data


def tampilkan_file_ruang_tutor(file_item):
    mime = str(file_item.get("mimeType", ""))
    nama = str(file_item.get("name", "Materi"))
    fid = str(file_item.get("id", ""))
    if not fid:
        st.warning("ID file Drive tidak tersedia.")
        return
    st.markdown(f"**{nama}**")
    st.caption(f"Tipe: {mime or 'tidak diketahui'} · Terakhir diubah: {file_item.get('modifiedTime', '-')}")
    if mime == "application/pdf":
        st.markdown("##### 📖 Pembaca PDF")
        components.iframe(url_preview_drive(fid), height=650, scrolling=True)
    elif mime.startswith(("image/", "audio/", "video/")):
        # Unduh bytes media terlebih dahulu. URL halaman/unduhan Drive tidak selalu
        # dapat dipakai langsung oleh player HTML5 di browser.
        try:
            media_bytes = ambil_bytes_media_drive(fid, batas_mb=30)
            if mime.startswith("image/"):
                st.image(media_bytes, caption=nama, use_container_width=True)
            elif mime.startswith("audio/"):
                st.markdown("##### 🎧 Audio Player")
                st.audio(media_bytes, format=mime)
            else:
                st.markdown("##### 🎬 Video Player")
                st.video(media_bytes)
        except Exception as exc:
            st.warning(f"Media belum dapat dimuat: {exc}")
    else:
        st.info("Pratinjau langsung tidak tersedia untuk format ini. Buka file melalui Google Drive.")
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("↗ Buka di Google Drive", file_item.get("webViewLink") or url_preview_drive(fid), use_container_width=True)
    with c2:
        st.link_button("⬇ Unduh file", f"https://drive.google.com/uc?export=download&id={fid}", use_container_width=True)


def tampilkan_papan_tutor(id_user, id_tutor):
    st.markdown("#### 📌 Papan Tutor Saya")
    st.caption("Pengingat dan ide pribadi. Catatan hanya ditampilkan kepada akun tutor yang membuatnya.")
    with st.expander("➕ Tambah pengingat / target / ide", expanded=False):
        with st.form("form_papan_tutor_pribadi", clear_on_submit=True):
            judul = st.text_input("Judul / hal yang perlu diingat")
            isi = st.text_area("Catatan", height=90)
            jenis = st.selectbox("Jenis", ["Pengingat", "Target", "Checklist", "Ide Mengajar"])
            pengingat = st.text_input("Tanggal / waktu pengingat (opsional)", placeholder="Contoh: Jumat, sebelum kelas sore")
            simpan = st.form_submit_button("Simpan ke Papan Saya", use_container_width=True)
        if simpan:
            try:
                simpan_catatan_tutor(id_user, id_tutor, jenis, waktu_lokal().strftime("%Y-%m-%d"), "", "", judul, isi, pengingat)
                st.success("Catatan pribadi berhasil disimpan.")
                st.rerun()
            except Exception as exc:
                st.error(f"Catatan belum tersimpan: {exc}")
    try:
        daftar = ambil_catatan_tutor(id_user)
        daftar = sorted(daftar, key=lambda x: (str(x.get("Status", "")) != "Disematkan", str(x.get("Diperbarui_Pada", ""))), reverse=True)
        if not daftar:
            st.info("Papan masih kosong. Tambahkan pengingat atau ide mengajar.")
        for item in daftar[-12:][::-1]:
            with st.container(border=True):
                st.markdown(f"**{item.get('Topik', 'Catatan')}** · {item.get('Jenis_Catatan', 'Catatan')}")
                if item.get("Isi_Catatan"):
                    st.write(item.get("Isi_Catatan"))
                if item.get("Pengingat"):
                    st.caption("⏰ " + item.get("Pengingat"))
                col_pin, col_done, col_del = st.columns(3)
                cid = item.get("ID_Catatan", "")
                with col_pin:
                    label = "Lepas pin" if item.get("Status") == "Disematkan" else "Sematkan"
                    if st.button(label, key=f"pin_catatan_{cid}", use_container_width=True):
                        ubah_status_catatan_tutor(cid, id_user, "Aktif" if label == "Lepas pin" else "Disematkan")
                        st.rerun()
                with col_done:
                    if st.button("Selesai", key=f"done_catatan_{cid}", use_container_width=True):
                        ubah_status_catatan_tutor(cid, id_user, "Selesai")
                        st.rerun()
                with col_del:
                    if st.button("Hapus", key=f"hapus_catatan_{cid}", use_container_width=True):
                        ubah_status_catatan_tutor(cid, id_user, "Dihapus")
                        st.rerun()
    except Exception as exc:
        st.warning(f"Papan Tutor Saya belum dapat dimuat: {exc}")


# =========================================================
# MODUL KEHADIRAN - menggunakan tab database baru
# =========================================================
KEHADIRAN_HEADERS = [
    "ID_Kehadiran", "ID_Siswa", "ID_Tutor", "Tanggal_Sesi", "Waktu_Hadir",
    "Waktu_Selesai_Belajar", "Status_Kehadiran", "ID_Riwayat_Paket",
    "Nomor_Pertemuan", "Dicatat_Oleh", "Waktu_Dicatat", "Catatan"
]
KOREKSI_HEADERS = [
    "ID_Koreksi", "ID_Kehadiran", "Kolom_Dikoreksi", "Nilai_Lama",
    "Nilai_Baru", "Alasan_Koreksi", "ID_User_Pengoreksi", "Waktu_Koreksi"
]


def waktu_lokal():
    """Timestamp konsisten untuk WIB, disimpan sebagai teks ISO lokal."""
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def get_attendance_worksheet():
    ws = get_or_create_worksheet("Kehadiran_Sesi", KEHADIRAN_HEADERS, rows="3000", cols="12")
    headers = ws.row_values(1)
    if not header_cocok(headers, KEHADIRAN_HEADERS):
        raise ValueError("Header Kehadiran_Sesi tidak sesuai struktur database. Data tidak ditulis.")
    return ws


def get_attendance_corrections_worksheet():
    ws = get_or_create_worksheet("Riwayat_Koreksi_Kehadiran", KOREKSI_HEADERS, rows="2000", cols="8")
    headers = ws.row_values(1)
    if not header_cocok(headers, KOREKSI_HEADERS):
        raise ValueError("Header Riwayat_Koreksi_Kehadiran tidak sesuai. Data koreksi tidak ditulis.")
    return ws


def muat_ulang_data_bersih():
    """Buang cache bacaan dan penanda sesi lama agar data dibaca segar (dipakai saat login/pindah peran)."""
    try:
        _baca_values_cache.clear()
    except Exception:
        pass
    for k in ("_tugas_jawaban_terkunci", "_indeks_baris_jawaban_siswa", "_draft_pending_by_task",
              "_draft_status_by_task", "_draft_saved_for_task", "_galat_simpan", "_tutor_id_dicoba"):
        st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if str(k).startswith(("_cache_", "_indeks_")):
            st.session_state.pop(k, None)


def tombol_muat_ulang_sidebar(kunci):
    if st.sidebar.button("🔄 Muat ulang data", key=kunci, use_container_width=True,
                         help="Pakai bila data tampak kosong atau belum berubah."):
        muat_ulang_data_bersih()
        st.rerun()


def resolve_tutor_id(user_row):
    """Cocokkan akun login dengan Data_Tutor; tidak menebak ID."""
    user_id = str(user_row.get("ID_User", "")).strip()
    nama_user = str(user_row.get("Nama_Pengguna", "")).strip()
    tutor_rows, galat = None, None
    for percobaan in range(3):
        try:
            tutor_rows = baca_records_aman(get_worksheet("Data_Tutor"), refresh=True)
            break
        except Exception as exc:
            galat = exc
            time.sleep(1.5 * (percobaan + 1))
    if tutor_rows is None:
        st.session_state["_tutor_id_gagal_baca"] = str(galat)
        return ""
    st.session_state.pop("_tutor_id_gagal_baca", None)
    matches = []
    for rec in tutor_rows:
        rec_user_id = str(rec.get("ID_User", "")).strip()
        rec_name = str(rec.get("Nama_Tutor", "")).strip()
        if user_id and rec_user_id and user_id == rec_user_id:
            matches.append(str(rec.get("ID_Tutor", "")).strip())
        elif not user_id and nama_user and rec_name.lower() == nama_user.lower():
            matches.append(str(rec.get("ID_Tutor", "")).strip())
    matches = [x for x in matches if x]
    return matches[0] if len(set(matches)) == 1 else ""


def siswa_tutor_terhubung(tutor_id):
    """Ambil siswa dari relasi aktif saja. Gagal tertutup jika ID tutor tidak ditemukan."""
    if not tutor_id:
        return set()
    try:
        relasi = baca_records_aman(get_worksheet("Relasi_Tutor_Siswa"))
    except Exception:
        return set()
    ids = set()
    for r in relasi:
        status = str(r.get("Status_Relasi", "Aktif")).strip().lower()
        if str(r.get("ID_Tutor", "")).strip() == tutor_id and status not in ("nonaktif", "tidak aktif", "selesai"):
            sid = str(r.get("ID_Siswa", "")).strip()
            if sid:
                ids.add(sid)
    return ids


def cari_sesi_aktif(id_siswa, id_tutor=None):
    ws = get_attendance_worksheet()
    records = baca_records_aman(ws)
    for rec in reversed(records):
        row_num = rec["_baris"]
        if (str(rec.get("ID_Siswa", "")).strip() == str(id_siswa).strip()
                and (not id_tutor or str(rec.get("ID_Tutor", "")).strip() == str(id_tutor).strip())
                and str(rec.get("Status_Kehadiran", "")).strip().lower() == "hadir"
                and not str(rec.get("Waktu_Selesai_Belajar", "")).strip()):
            return ws, row_num, rec
    return ws, None, None


def catat_kehadiran(id_siswa, id_tutor, nama_tutor, catatan=""):
    ws, row_num, existing = cari_sesi_aktif(id_siswa)
    if existing:
        return False, "Siswa masih memiliki sesi berstatus Hadir yang belum ditandai selesai."
    now = waktu_lokal()
    ws.append_row([
        "KHD-" + uuid.uuid4().hex[:10].upper(), str(id_siswa), str(id_tutor),
        now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "", "Hadir", "", "",
        str(nama_tutor), now.strftime("%Y-%m-%d %H:%M:%S %Z"), str(catatan)
    ])
    return True, "Kehadiran berhasil dicatat."


def tandai_selesai_belajar(id_siswa, id_tutor):
    ws, row_num, rec = cari_sesi_aktif(id_siswa, id_tutor)
    if not rec:
        return False, "Tidak ditemukan sesi aktif yang dapat diselesaikan."
    headers = ws.row_values(1)
    col_finish = headers.index("Waktu_Selesai_Belajar") + 1
    col_status = headers.index("Status_Kehadiran") + 1
    now = waktu_lokal()
    ws.update_cell(row_num, col_finish, now.strftime("%H:%M:%S"))
    ws.update_cell(row_num, col_status, "Selesai Belajar")
    return True, "Waktu selesai belajar berhasil dicatat."


def koreksi_kehadiran(id_kehadiran, kolom, nilai_baru, alasan, id_user):
    if not alasan.strip():
        return False, "Alasan koreksi wajib diisi."
    if kolom not in ("Waktu_Hadir", "Waktu_Selesai_Belajar", "Status_Kehadiran"):
        return False, "Kolom ini tidak dapat dikoreksi dari portal."
    ws = get_attendance_worksheet()
    headers = ws.row_values(1)
    id_col = headers.index("ID_Kehadiran") + 1
    cell = ws.find(str(id_kehadiran))
    if not cell:
        return False, "Data kehadiran tidak ditemukan."
    col_num = headers.index(kolom) + 1
    nilai_lama = str(ws.cell(cell.row, col_num).value or "")
    nilai_baru = str(nilai_baru).strip()
    ws.update_cell(cell.row, col_num, nilai_baru)
    try:
        log_ws = get_attendance_corrections_worksheet()
        now = waktu_lokal()
        log_ws.append_row([
            "KOR-" + uuid.uuid4().hex[:10].upper(), str(id_kehadiran), kolom,
            nilai_lama, nilai_baru, alasan.strip(), str(id_user),
            now.strftime("%Y-%m-%d %H:%M:%S %Z")
        ])
    except Exception:
        # Rollback agar perubahan tidak terjadi tanpa jejak audit.
        ws.update_cell(cell.row, col_num, nilai_lama)
        raise
    return True, "Koreksi tersimpan dan tercatat di Riwayat_Koreksi_Kehadiran."


def tampilkan_riwayat_kehadiran(id_siswa, judul="Riwayat Kehadiran"):
    st.markdown(f"#### {judul}")
    try:
        records = [r for r in baca_records_aman(get_attendance_worksheet())
                   if str(r.get("ID_Siswa", "")).strip() == str(id_siswa).strip()]
        if not records:
            st.info("Belum ada catatan kehadiran.")
            return
        rows = []
        for r in reversed(records[-30:]):
            rows.append({
                "Tanggal": r.get("Tanggal_Sesi", "-"),
                "Waktu Hadir": r.get("Waktu_Hadir", "Belum tercatat") or "Belum tercatat",
                "Selesai Belajar": r.get("Waktu_Selesai_Belajar", "Belum selesai") or "Belum selesai",
                "Status": r.get("Status_Kehadiran", "-"),
                "Tutor": r.get("Dicatat_Oleh", "-")
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("'Selesai Belajar' menandai berakhirnya pembelajaran, bukan waktu siswa dijemput atau meninggalkan lokasi.")
    except Exception as e:
        st.warning(f"Riwayat kehadiran belum dapat dibaca: {e}")


TASK_BASE_HEADERS = ["ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Judul_Tugas", "Jenis_Tugas", "Sumber", "Instruksi", "File_Offline", "Timer_Menit", "Tenggat", "Soal_JSON", "Status_Tugas", "Tutor", "Mode_Pengerjaan"]
TASK_HEADERS = TASK_BASE_HEADERS + ["ID_Siswa", "ID_Tutor"]
ANSWER_HEADERS = ["ID_Jawaban", "ID_Penugasan", "ID_Siswa", "Nomor_Soal", "Jawaban", "Status_Jawaban", "Waktu_Tersimpan", "Waktu_Dikumpulkan"]


def pastikan_header_tugas(ws):
    """Migrasi aman: pertahankan semua kolom lama, tambahkan identitas di ujung kanan."""
    headers = [str(x).strip() for x in ws.row_values(1)]
    base_sebelum_mode = TASK_BASE_HEADERS[:-1]
    if headers == base_sebelum_mode:
        if ws.col_count < len(TASK_BASE_HEADERS):
            ws.add_cols(len(TASK_BASE_HEADERS) - ws.col_count)
        ws.update_cell(1, len(TASK_BASE_HEADERS), "Mode_Pengerjaan")
        headers = TASK_BASE_HEADERS.copy()
    if headers[:len(TASK_BASE_HEADERS)] != TASK_BASE_HEADERS:
        return False
    tambahan = [h for h in ("ID_Siswa", "ID_Tutor") if h not in headers]
    if tambahan:
        kolom_awal = len(headers) + 1
        if ws.col_count < len(headers) + len(tambahan):
            ws.add_cols(len(headers) + len(tambahan) - ws.col_count)
        ws.update(f"{gspread.utils.rowcol_to_a1(1, kolom_awal)}:{gspread.utils.rowcol_to_a1(1, kolom_awal + len(tambahan) - 1)}", [tambahan], value_input_option="RAW")
        try:
            _baca_values_cache.clear()
        except Exception:
            pass
        headers = [str(x).strip() for x in ws.row_values(1)]
    return headers == TASK_HEADERS


ACTIVE_TASK_HEADERS = ["ID_Siswa", "ID_Tugas", "Waktu_Mulai", "Status", "Waktu_Selesai"]


def get_active_task_worksheet():
    """Status sesi online di server agar kunci materi berlaku lintas tab/perangkat."""
    try:
        ws = get_worksheet("Status_Sesi_Tugas")
    except gspread.WorksheetNotFound:
        ws = init_spreadsheet().add_worksheet(
            title="Status_Sesi_Tugas", rows="2000", cols=len(ACTIVE_TASK_HEADERS)
        )
        ws.append_row(ACTIVE_TASK_HEADERS)
        _worksheet_header_cached.clear()
    header_aktif = [str(x).strip() for x in _worksheet_header_cached(init_spreadsheet().id, ws.title)]
    if header_aktif != ACTIVE_TASK_HEADERS:
        raise ValueError("Header Status_Sesi_Tugas tidak sesuai.")
    return ws


def baca_sesi_aktif_siswa(siswa_id):
    """Membaca status sesi dari cache bersama; cache dibersihkan saat sesi berubah."""
    rows = baca_records_aman(get_active_task_worksheet())
    sid = str(siswa_id or "").strip()
    aktif = [r for r in rows if str(r.get("ID_Siswa", "")).strip() == sid
             and str(r.get("Status", "")).strip().lower() == "aktif"]
    return aktif[-1] if aktif else None


def hitung_sisa_waktu_sesi(sesi, timer_menit, sekarang=None):
    """Menghitung sisa detik dari waktu server; None berarti tanpa timer/tidak valid."""
    try:
        durasi = int(float(str(timer_menit or "0").strip().replace(",", ".")))
        if durasi <= 0:
            return None
        mulai_txt = str((sesi or {}).get("Waktu_Mulai", "")).strip()
        mulai = datetime.strptime(mulai_txt, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=ZoneInfo("Asia/Jakarta")
        )
        now = sekarang or waktu_lokal()
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
        elapsed = (now - mulai).total_seconds()
        return max(0, int(durasi * 60 - elapsed + 0.999))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Waktu mulai atau durasi timer tidak valid. Hubungi Tutor.")


def tampilkan_timer_sisa(sisa_detik, task_id):
    """Hitung mundur visual di browser; keputusan simpan/kirim tetap divalidasi server."""
    detik = max(0, int(sisa_detik))
    html = f"""
    <div id="nazma-timer-{task_id}" style="padding:10px 14px;border:1px solid #d6a84f;border-radius:10px;background:#fff8e8;color:#6b4b00;font-weight:600;font-size:16px;">
      ⏱️ Sisa waktu: <span class="waktu">{detik//60:02d}:{detik%60:02d}</span>
      <span class="pesan" style="font-weight:400;"></span>
    </div>
    <script>
    (function(){{
      const box=document.getElementById("nazma-timer-{task_id}");
      if(!box) return;
      let s={detik};
      const tick=()=>{{
        const m=Math.floor(s/60), d=s%60;
        box.querySelector(".waktu").textContent=String(m).padStart(2,"0")+":"+String(d).padStart(2,"0");
        if(s<=0){{
          box.querySelector(".pesan").textContent=" — Waktu habis. Lembar jawaban terkunci oleh server.";
          clearInterval(timer);
          return;
        }}
        s--;
      }};
      tick();
      const timer=setInterval(tick,1000);
    }})();
    </script>
    """
    components.html(html, height=62, scrolling=False)


def _parse_tenggat_server(nilai):
    """Parse tenggat tugas ke waktu Asia/Jakarta; tanggal tanpa jam berlaku sampai akhir hari."""
    teks = str(nilai or "").strip()
    if not teks:
        return None
    kandidat = teks.replace(" WIB", "").replace(" wib", "").strip()
    try:
        dt = datetime.fromisoformat(kandidat.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
        else:
            dt = dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return dt
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(kandidat, fmt).replace(tzinfo=ZoneInfo("Asia/Jakarta"))
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(kandidat, fmt).replace(
                hour=23, minute=59, second=59, tzinfo=ZoneInfo("Asia/Jakarta")
            )
        except ValueError:
            continue
    raise ValueError("Format tenggat tugas tidak dikenali. Hubungi Tutor untuk memperbaiki tenggat.")


def validasi_waktu_pengiriman(task_id, siswa_id):
    """Pemeriksaan otoritatif server untuk tenggat dan timer sebelum draft/pengiriman."""
    try:
        ws_tugas = get_worksheet("Tugas_Sesi_Siswa_v2")
        tugas = baca_records_aman(ws_tugas, refresh=True)
    except gspread.WorksheetNotFound:
        tugas = get_student_tasks()
    task = next((r for r in tugas if str(r.get("ID_Tugas", "")).strip() == str(task_id).strip()), None)
    if not task:
        raise ValueError("Data tugas tidak ditemukan. Jawaban belum disimpan/dikirim.")

    # Validasi identitas dilakukan di server untuk setiap operasi dari portal siswa.
    # Jangan percaya ID_Siswa yang hanya dikirim dari parameter/widget.
    sid_parameter = str(siswa_id or "").strip()
    sid_tugas = str(task.get("ID_Siswa", "")).strip()
    sid_sesi = str(st.session_state.get("siswa_id", "")).strip()
    if not st.session_state.get("siswa_logged_in") or not sid_sesi:
        raise ValueError("Sesi akun siswa tidak valid. Silakan login kembali.")
    if sid_parameter != sid_sesi:
        raise ValueError("Identitas siswa pada sesi tidak cocok. Jawaban tidak disimpan.")
    if not sid_tugas:
        raise ValueError("Identitas siswa pada data tugas belum lengkap. Hubungi Tutor; jawaban belum disimpan.")
    if sid_tugas != sid_sesi:
        raise ValueError("Tugas ini bukan milik akun siswa yang sedang login. Jawaban tidak disimpan.")

    modus_task = mode_tugas(task)
    offline_siswa = modus_task == TASK_MODE_OFFLINE and unggah_oleh_tugas(task) == "siswa"
    if modus_task != TASK_MODE_ONLINE and not offline_siswa:
        return True
    sekarang = waktu_lokal()
    tenggat = _parse_tenggat_server(task.get("Tenggat"))
    if tenggat and sekarang > tenggat:
        raise ValueError("Tenggat tugas sudah tercapai. Lembar jawaban dikunci dan perubahan tidak dapat disimpan.")

    timer = str(task.get("Timer_Menit", "0") or "0").strip()
    try:
        durasi = float(timer.replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Pengaturan timer tugas tidak valid. Hubungi Tutor.")
    if durasi <= 0:
        return True
    sesi = baca_sesi_aktif_siswa(siswa_id)
    if offline_siswa and (not sesi or str(sesi.get("ID_Tugas", "")).strip() != str(task_id).strip()):
        # Siswa sudah menekan Selesai: kirim diizinkan selama masa unggah setelah Selesai.
        _sesi_selesai = baca_sesi_selesai_siswa(siswa_id, task_id)
        if _sesi_selesai and sisa_detik_unggah_setelah_selesai(_sesi_selesai, sekarang=sekarang) > 0:
            return True
        if _sesi_selesai:
            raise ValueError("Masa unggah setelah Selesai sudah habis. Hubungi Tutor untuk membuka kembali.")
    if not sesi or str(sesi.get("ID_Tugas", "")).strip() != str(task_id).strip():
        raise ValueError("Sesi pengerjaan tidak aktif. Muat ulang tugas dan hubungi Tutor bila masalah berlanjut.")
    sisa = hitung_sisa_waktu_sesi(sesi, durasi + masa_tambahan_menit(task), sekarang=sekarang)
    if sisa <= 0:
        raise ValueError("Waktu pengerjaan sudah habis. Jawaban tidak dapat disimpan/dikirim melalui sesi ini. Hubungi Tutor untuk pemeriksaan draft terakhir.")
    return True


def mulai_sesi_online(siswa_id, task_id):
    """Mencatat sesi mulai di server. Satu siswa hanya boleh punya satu sesi aktif."""
    # Jangan izinkan sesi baru dimulai setelah tenggat tugas online lewat.
    try:
        tugas_rows = baca_records_aman(get_worksheet("Tugas_Sesi_Siswa_v2"), refresh=True)
    except gspread.WorksheetNotFound:
        tugas_rows = get_student_tasks()
    tugas = next((r for r in tugas_rows
                  if str(r.get("ID_Tugas", "")).strip() == str(task_id).strip()), None)
    if not tugas:
        return False, "Data tugas tidak ditemukan. Hubungi Tutor."

    # Tombol Mulai juga harus memverifikasi pemilik tugas di sisi server.
    sid_sesi = str(st.session_state.get("siswa_id", "")).strip()
    sid_parameter = str(siswa_id or "").strip()
    sid_tugas = str(tugas.get("ID_Siswa", "")).strip()
    if not st.session_state.get("siswa_logged_in") or not sid_sesi:
        return False, "Sesi akun siswa tidak valid. Silakan login kembali."
    if sid_parameter != sid_sesi or not sid_tugas or sid_tugas != sid_sesi:
        return False, "Tugas ini bukan milik akun siswa yang sedang login."

    if mode_tugas(tugas) in (TASK_MODE_ONLINE, TASK_MODE_OFFLINE):
        tenggat = _parse_tenggat_server(tugas.get("Tenggat"))
        if tenggat and waktu_lokal() > tenggat:
            return False, "Tenggat tugas sudah lewat. Hubungi Tutor."
    if sesi_kedaluwarsa_tugas(siswa_id, task_id):
        return False, "Waktu pengerjaan tugas ini sudah habis. Hubungi Tutor bila perlu dibuka kembali."
    ws = get_active_task_worksheet()
    aktif = baca_sesi_aktif_siswa(siswa_id)
    if aktif and str(aktif.get("ID_Tugas", "")).strip() != str(task_id).strip():
        return False, "Selesaikan tugas online yang sedang aktif terlebih dahulu."
    if aktif:
        return True, "Sesi tugas ini sudah aktif."
    ws.append_row([
        str(siswa_id).strip(), str(task_id).strip(),
        waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"), "Aktif", ""
    ], value_input_option="RAW")
    _baca_values_cache.clear()
    _worksheet_header_cached.clear()
    return True, "Sesi pengerjaan dimulai."


def akhiri_sesi_online(siswa_id, task_id):
    ws = get_active_task_worksheet()
    # Baca kondisi terbaru dari Sheets, bukan cache sesi yang mungkin sudah kedaluwarsa.
    rows = baca_records_aman(ws, refresh=True)
    sid, tid = str(siswa_id).strip(), str(task_id).strip()
    for row in reversed(rows):
        if (str(row.get("ID_Siswa", "")).strip() == sid
                and str(row.get("ID_Tugas", "")).strip() == tid
                and str(row.get("Status", "")).strip().lower() == "aktif"):
            baris = int(row["_baris"])
            selesai = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
            ws.update(f"D{baris}:E{baris}", [["Selesai", selesai]], value_input_option="RAW")
            _baca_values_cache.clear()
            return True
    _baca_values_cache.clear()
    return False


MASA_UNGGAH_MENIT = 10  # waktu tambahan khusus mengunggah foto pada tugas Offline yang diunggah siswa


def unggah_oleh_tugas(t):
    """'siswa' atau 'tutor'. Tugas Offline lama tanpa metadata dianggap diunggah oleh tutor."""
    try:
        data = json.loads(t.get("Soal_JSON", "") or "[]")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            meta = data[0].get(TASK_META_KEY, {})
            if isinstance(meta, dict) and str(meta.get("unggah_oleh", "")).strip().lower() == "siswa":
                return "siswa"
    except (ValueError, TypeError):
        pass
    return "tutor"


def masa_tambahan_menit(t):
    """Menit tambahan setelah timer habis, khusus tugas Offline yang diunggah siswa."""
    if mode_tugas(t) == TASK_MODE_OFFLINE and unggah_oleh_tugas(t) == "siswa":
        return MASA_UNGGAH_MENIT
    return 0


def _durasi_menit(t):
    try:
        return max(0.0, float(str(t.get("Timer_Menit", "0") or "0").strip().replace(",", ".")))
    except (TypeError, ValueError):
        return 0.0


def sesi_kedaluwarsa_tugas(siswa_id, task_id):
    """True bila sesi tugas ini pernah berakhir karena waktu habis dan belum dibuka ulang oleh tutor."""
    rows = baca_records_aman(get_active_task_worksheet())
    sid, tid = str(siswa_id or "").strip(), str(task_id or "").strip()
    return any(
        str(r.get("ID_Siswa", "")).strip() == sid and str(r.get("ID_Tugas", "")).strip() == tid
        and str(r.get("Status", "")).strip().lower() == "kedaluwarsa"
        for r in rows
    )


def sesi_selesai_tugas(siswa_id, task_id):
    """True bila siswa sudah menekan Selesai Mengerjakan (sesi berstatus Selesai) untuk tugas ini."""
    rows = baca_records_aman(get_active_task_worksheet())
    sid, tid = str(siswa_id or "").strip(), str(task_id or "").strip()
    return any(
        str(r.get("ID_Siswa", "")).strip() == sid and str(r.get("ID_Tugas", "")).strip() == tid
        and str(r.get("Status", "")).strip().lower() == "selesai"
        for r in rows
    )


def baca_sesi_selesai_siswa(siswa_id, task_id):
    """Baris sesi terakhir berstatus Selesai untuk siswa dan tugas ini (atau None)."""
    rows = baca_records_aman(get_active_task_worksheet())
    sid, tid = str(siswa_id or "").strip(), str(task_id or "").strip()
    cocok = [
        r for r in rows
        if str(r.get("ID_Siswa", "")).strip() == sid and str(r.get("ID_Tugas", "")).strip() == tid
        and str(r.get("Status", "")).strip().lower() == "selesai"
    ]
    return cocok[-1] if cocok else None


def sisa_detik_unggah_setelah_selesai(sesi_selesai, sekarang=None):
    """Sisa detik masa unggah (MASA_UNGGAH_MENIT) sejak siswa menekan Selesai Mengerjakan."""
    try:
        selesai = datetime.strptime(str((sesi_selesai or {}).get("Waktu_Selesai", "")).strip(), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=ZoneInfo("Asia/Jakarta")
        )
    except (TypeError, ValueError):
        return 0
    now = sekarang or waktu_lokal()
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
    return max(0, int(MASA_UNGGAH_MENIT * 60 - (now - selesai).total_seconds()))


def tampilkan_tombol_selesai_mengerjakan(siswa_id, task_id, expander_state_key):
    """Tombol Selesai dengan konfirmasi (menghentikan timer dan membebaskan kunci tugas lain)."""
    kunci_konfirmasi = f"_konfirmasi_selesai_{task_id}"
    if not st.session_state.get(kunci_konfirmasi):
        if st.button("✅ Selesai Mengerjakan", key=f"selesai_kerja_{task_id}", type="primary"):
            st.session_state[kunci_konfirmasi] = True
            st.session_state[expander_state_key] = True
            st.rerun()
        return
    st.warning("Yakin sudah selesai? Waktu pengerjaan akan dihentikan dan tugas ini tidak bisa dimulai lagi.")
    kol_ya, kol_belum = st.columns(2)
    with kol_ya:
        if st.button("Ya, sudah selesai", key=f"ya_selesai_{task_id}", type="primary"):
            try:
                akhiri_sesi_online(siswa_id, task_id)
                st.session_state.pop(kunci_konfirmasi, None)
                st.session_state[expander_state_key] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Belum dapat menandai selesai ({exc.__class__.__name__}). Coba lagi.")
    with kol_belum:
        if st.button("Belum", key=f"belum_selesai_{task_id}"):
            st.session_state.pop(kunci_konfirmasi, None)
            st.session_state[expander_state_key] = True
            st.rerun()


def kirim_otomatis_draft(siswa_id, task_id):
    """Ubah semua jawaban Draft pada tugas ini menjadi terkirim. Tidak menyentuh pengiriman yang sudah ada."""
    ws = get_answers_worksheet()
    sid, tid = str(siswa_id or "").strip(), str(task_id or "").strip()
    baris_pair = [
        r for r in baca_records_aman(ws, refresh=True)
        if str(r.get("ID_Penugasan", "")).strip() == tid and str(r.get("ID_Siswa", "")).strip() == sid
    ]
    if not baris_pair:
        return 0
    for r in baris_pair:
        status = str(r.get("Status_Jawaban", "")).strip().lower()
        if "dikirim" in status or "menunggu" in status or "dinilai" in status:
            return 0  # sudah pernah dikirim atau dinilai
    sekarang = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    pembaruan = [
        {"range": f"F{int(r['_baris'])}:H{int(r['_baris'])}",
         "values": [["Dikirim - Menunggu Penilaian", r.get("Waktu_Tersimpan", "") or sekarang, sekarang]]}
        for r in baris_pair
    ]
    ws.batch_update(pembaruan, value_input_option="RAW")
    _baca_values_cache.clear()
    return len(pembaruan)


def _sesi_sudah_habis(sesi, tugas):
    raw_durasi = str((tugas or {}).get("Timer_Menit", "") or "").strip()
    if not raw_durasi:
        return False  # tugas tanpa timer
    try:
        durasi = float(raw_durasi.replace(",", "."))
    except (TypeError, ValueError):
        return None  # status timer tidak diketahui; jangan dianggap aktif atau kedaluwarsa
    if durasi <= 0:
        return False
    try:
        sisa = hitung_sisa_waktu_sesi(sesi, durasi + masa_tambahan_menit(tugas))
    except ValueError:
        return None
    return sisa is not None and sisa <= 0


def _akhiri_sesi_kedaluwarsa(sesi, tugas):
    ws = get_active_task_worksheet()
    baris = int(sesi["_baris"])
    selesai = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    ws.update(f"D{baris}:E{baris}", [["Kedaluwarsa", selesai]], value_input_option="RAW")
    _baca_values_cache.clear()
    if mode_tugas(tugas) == TASK_MODE_ONLINE:
        try:
            kirim_otomatis_draft(sesi.get("ID_Siswa", ""), sesi.get("ID_Tugas", ""))
        except Exception:
            pass  # sesi tetap dilepas; draft bisa dikirim ulang pada pemeriksaan berikutnya


def lepas_sesi_kedaluwarsa(siswa_id, daftar_tugas):
    """Lepas kunci sesi aktif milik siswa bila waktunya lewat; jawaban draft tugas Online ikut terkirim."""
    sesi = baca_sesi_aktif_siswa(siswa_id)
    if not sesi:
        return False
    tid = str(sesi.get("ID_Tugas", "")).strip()
    tugas = next((t for t in (daftar_tugas or []) if str(t.get("ID_Tugas", "")).strip() == tid), None)
    if not tugas or _sesi_sudah_habis(sesi, tugas) is not True:
        return False
    _akhiri_sesi_kedaluwarsa(sesi, tugas)
    return True


def lepas_semua_sesi_kedaluwarsa(daftar_tugas, segarkan=False):
    """Dipakai halaman tutor: proses semua sesi aktif yang waktunya habis, walau siswa tidak membuka portal lagi."""
    peta = {str(t.get("ID_Tugas", "")).strip(): t for t in (daftar_tugas or [])}
    jumlah = 0
    for sesi in baca_records_aman(get_active_task_worksheet(), refresh=segarkan):
        if str(sesi.get("Status", "")).strip().lower() != "aktif":
            continue
        tugas = peta.get(str(sesi.get("ID_Tugas", "")).strip())
        if tugas and _sesi_sudah_habis(sesi, tugas) is True:
            _akhiri_sesi_kedaluwarsa(sesi, tugas)
            jumlah += 1
    return jumlah


def buka_ulang_sesi(siswa_id, task_id):
    """Dipakai tutor: lepas kunci sesi aktif atau buka kembali tugas yang waktunya habis."""
    ws = get_active_task_worksheet()
    rows = baca_records_aman(ws, refresh=True)
    sid, tid = str(siswa_id or "").strip(), str(task_id or "").strip()
    selesai = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    jumlah = 0
    for r in rows:
        if (str(r.get("ID_Siswa", "")).strip() == sid and str(r.get("ID_Tugas", "")).strip() == tid
                and str(r.get("Status", "")).strip().lower() in ("aktif", "kedaluwarsa")):
            baris = int(r["_baris"])
            ws.update(f"D{baris}:E{baris}", [["Dibuka_Ulang", selesai]], value_input_option="RAW")
            jumlah += 1
    if jumlah:
        _baca_values_cache.clear()
    return jumlah


def gerbang_sesi_tugas(t, task_id, siswa_id, sesi_aktif_page, expander_state_key):
    """Mulai, timer, dan kunci untuk tugas Offline. True bila area kerja boleh ditampilkan."""
    timer_txt = str(t.get("Timer_Menit", "")).strip()
    if timer_txt in ("", "0"):
        return True  # tanpa timer: tenggat tetap diperiksa server saat mengirim
    sesi_ini_aktif = bool(sesi_aktif_page and str(sesi_aktif_page.get("ID_Tugas", "")).strip() == task_id)
    sesi_lain_aktif = bool(sesi_aktif_page and not sesi_ini_aktif)
    try:
        habis = sesi_kedaluwarsa_tugas(siswa_id, task_id)
    except Exception:
        habis = False
    if habis and not sesi_ini_aktif:
        st.error("⏰ Waktu pengerjaan tugas ini sudah habis. Hubungi Tutor bila perlu dibuka kembali.")
        return False
    if sesi_lain_aktif:
        st.warning("Tugas ini terkunci karena kamu sedang mengerjakan tugas lain. Kumpulkan tugas yang aktif terlebih dahulu.")
        return False
    if not sesi_ini_aktif and unggah_oleh_tugas(t) != "siswa":
        try:
            if sesi_selesai_tugas(siswa_id, task_id):
                st.success("✅ Kamu sudah menyelesaikan tugas ini. Menunggu Tutor mengunggah hasil pekerjaan.")
                return True
        except Exception:
            pass
    if not sesi_ini_aktif and unggah_oleh_tugas(t) == "siswa":
        try:
            _selesai_row = baca_sesi_selesai_siswa(siswa_id, task_id)
        except Exception:
            _selesai_row = None
        if _selesai_row:
            _sisa_unggah = sisa_detik_unggah_setelah_selesai(_selesai_row)
            if _sisa_unggah > 0:
                st.success(
                    f"⏹ Timer sudah berhenti. Unggah hasil pekerjaanmu lalu tekan Kirim. "
                    f"Sisa waktu unggah sekitar {max(1, _sisa_unggah // 60)} menit."
                )
                return True
            st.error("⏰ Masa unggah setelah Selesai sudah habis. Hubungi Tutor bila perlu dibuka kembali.")
            return False
    if not sesi_ini_aktif:
        st.info("Tekan Mulai Mengerjakan jika sudah siap. Soal terbuka dan waktu berjalan setelah tombol ditekan; tugas lain terkunci sampai selesai.")
        if st.button("▶️ Mulai Mengerjakan", key=f"mulai_offline_{task_id}", type="primary"):
            ok_mulai, pesan_mulai = mulai_sesi_online(siswa_id, task_id)
            if ok_mulai:
                st.session_state[expander_state_key] = True
                st.success(pesan_mulai)
                st.rerun()
            else:
                st.error(pesan_mulai)
        return False
    grace = masa_tambahan_menit(t)
    try:
        sisa = hitung_sisa_waktu_sesi(sesi_aktif_page, timer_txt)
        if sisa and sisa > 0:
            tampilkan_timer_sisa(sisa, task_id)
            if grace:
                st.caption(f"Setelah waktu habis ada {grace} menit tambahan khusus untuk mengunggah foto hasil pekerjaan.")
        else:
            if not grace:
                st.error("⏰ Waktu pengerjaan sudah habis.")
                return False
            sisa_unggah = hitung_sisa_waktu_sesi(sesi_aktif_page, _durasi_menit(t) + grace)
            if not sisa_unggah:
                st.error("⏰ Waktu mengerjakan dan waktu unggah sudah habis. Hubungi Tutor bila perlu dibuka kembali.")
                return False
            st.warning("⏰ Waktu mengerjakan habis. Segera unggah hasil pekerjaanmu sebelum waktu unggah berakhir.")
            tampilkan_timer_sisa(sisa_unggah, f"{task_id}-unggah")
    except ValueError as exc:
        st.error(str(exc))
        return False
    tampilkan_nazma_focus_alert(task_id, siswa_id, t)
    return True


def tampilkan_panel_offline_tutor(tutor_id, tutor_nama, daftar_tugas, jawaban_records):
    """Panel tutor: unggah hasil tugas Offline (variasi 'Tutor yang mengunggah') dan kelola sesi siswa."""
    tid_login = str(tutor_id or "").strip()
    tugas_semua = list(daftar_tugas or [])
    tugas_milik = [t for t in tugas_semua if tugas_milik_tutor(t, tid_login)]
    legacy_tanpa_id = sum(
        1 for t in tugas_semua
        if not str(t.get("ID_Tutor", "")).strip()
        and str(t.get("Tutor", "")).strip().casefold() == str(tutor_nama or "").strip().casefold()
    )
    if legacy_tanpa_id:
        st.warning(
            f"{legacy_tanpa_id} tugas historis belum memiliki ID_Tutor sehingga disembunyikan demi keamanan. "
            "Pengelola perlu memverifikasi dan menetapkan pemiliknya sebelum tugas dapat diakses kembali."
        )
    sudah = {
        (str(j.get("ID_Tugas", "")).strip(), str(j.get("ID_Siswa", "")).strip())
        for j in (jawaban_records or [])
    }
    kandidat = [
        t for t in tugas_milik
        if mode_tugas(t) == TASK_MODE_OFFLINE
        and (str(t.get("ID_Tugas", "")).strip(), str(t.get("ID_Siswa", "")).strip()) not in sudah
    ]
    with st.expander(f"🗒️ Tugas offline yang belum ada hasilnya: input oleh Tutor ({len(kandidat)})", expanded=bool(kandidat)):
        if not kandidat:
            st.caption("Semua tugas offline sudah memiliki hasil.")
        else:
            peta = {
                f"{t.get('Nama_Siswa', '')} | {t.get('Mapel', '')} - {t.get('Judul_Tugas', '')}"
                f"{' (siswa belum mengirim)' if unggah_oleh_tugas(t) == 'siswa' else ''} | {t.get('ID_Tugas', '')}": t
                for t in kandidat
            }
            pilih = st.selectbox("Pilih tugas offline:", list(peta.keys()), key="off_tutor_pilih")
            t_pilih = peta[pilih]
            id_tugas = str(t_pilih.get("ID_Tugas", "")).strip()
            id_siswa = str(t_pilih.get("ID_Siswa", "")).strip()
            catatan = st.text_area("Catatan Tutor (opsional):", key=f"off_tutor_cat_{id_tugas}")
            berkas = st.file_uploader(
                "Unggah foto atau PDF hasil pekerjaan siswa (opsional bila catatan diisi):",
                type=["jpg", "jpeg", "png", "webp", "pdf"], accept_multiple_files=True,
                key=f"off_tutor_file_{id_tugas}"
            )
            if st.button("📤 Kirim hasil untuk diperiksa", key=f"off_tutor_kirim_{id_tugas}"):
                if not berkas and not catatan.strip():
                    st.error("Unggah foto atau PDF hasil pekerjaan, atau isi catatan Tutor.")
                elif not id_siswa:
                    st.error("ID siswa pada tugas ini tidak ditemukan. Hubungi pengelola.")
                else:
                    urls_lampiran_tutor = []
                    try:
                        if berkas:
                            hasil_lampiran_tutor = simpan_lampiran_jawaban(id_tugas, id_siswa, berkas, oleh_tutor=True)
                            urls_lampiran_tutor = [x.get("URL_Drive", "") for x in hasil_lampiran_tutor]
                        teks = "Hasil pekerjaan offline diinput Tutor"
                        if catatan.strip():
                            teks += " — " + catatan.strip()
                        ok_kirim = simpan_pengiriman_jawaban(id_tugas, id_siswa, {"0": teks}, lewati_validasi_waktu=True)
                        if not ok_kirim:
                            raise RuntimeError("Pengiriman tidak tersimpan atau tugas sudah terkunci. Periksa status tugas sebelum mencoba lagi.")
                        try:
                            akhiri_sesi_online(id_siswa, id_tugas)
                        except Exception:
                            pass
                        st.success("Hasil terkirim. Sekarang muncul di daftar pemeriksaan di bawah.")
                        st.rerun()
                    except Exception as exc:
                        catat_log_gagal_pengiriman(id_tugas, id_siswa, "input_hasil_offline_tutor", exc, urls_lampiran_tutor)
                        st.error(f"Hasil belum terkirim: {exc.__class__.__name__}. Periksa log pengiriman sebelum mencoba ulang.")

    peta_tugas = {str(t.get("ID_Tugas", "")).strip(): t for t in tugas_milik}
    try:
        sesi_rows = baca_records_aman(get_active_task_worksheet())
    except Exception as exc:
        st.warning(f"Daftar sesi belum dapat dibaca: {exc}")
        sesi_rows = []
    bermasalah = [
        r for r in sesi_rows
        if str(r.get("Status", "")).strip().lower() in ("aktif", "kedaluwarsa")
        and str(r.get("ID_Tugas", "")).strip() in peta_tugas
    ]
    with st.expander(f"🕒 Sesi pengerjaan siswa: kunci dan waktu habis ({len(bermasalah)})", expanded=False):
        if not bermasalah:
            st.caption("Tidak ada sesi aktif atau sesi yang waktunya habis pada tugas Anda.")
        else:
            opsi = {}
            for r in bermasalah:
                tg = peta_tugas.get(str(r.get("ID_Tugas", "")).strip(), {})
                status_db = str(r.get("Status", "")).strip().lower()
                status_timer = _sesi_sudah_habis(r, tg) if status_db == "aktif" else False
                if status_db == "kedaluwarsa":
                    status_txt = "Waktu habis"
                elif status_timer is None:
                    status_txt = "Perlu pemeriksaan timer"
                elif status_timer is True:
                    status_txt = "Waktu habis (belum diproses)"
                else:
                    status_txt = "Sedang berjalan"
                label = f"{status_txt} | {tg.get('Nama_Siswa', '')} | {tg.get('Mapel', '')} - {tg.get('Judul_Tugas', '')} | mulai {r.get('Waktu_Mulai', '')}"
                opsi[label] = r
            pilih_sesi = st.selectbox("Pilih sesi:", list(opsi.keys()), key="off_tutor_sesi")
            st.caption("Membuka ulang melepas kunci siswa dan mengizinkan tugas dimulai lagi dari awal.")
            if st.button("🔓 Lepas kunci / buka ulang tugas", key="off_tutor_buka_ulang"):
                r_pilih = opsi[pilih_sesi]
                try:
                    n = buka_ulang_sesi(r_pilih.get("ID_Siswa", ""), r_pilih.get("ID_Tugas", ""))
                    st.success("Sesi dibuka ulang." if n else "Sesi sudah tidak aktif.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Sesi belum dapat dibuka ulang: {exc}")


# =========================================================
# EVALUASI SUSULAN: mengisi jurnal/evaluasi sesi yang terlewat
# Memakai sheet dan tata letak kolom yang sama dengan form "Jurnal dan Evaluasi Sesi".
# =========================================================
JURNAL_SESI_HEADERS = ["ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Kondisi_Siswa", "Keaktifan",
                       "Kendala_Umum", "Rekomendasi", "Handover", "Dokumentasi"]
EVALUASI_MAPEL_HEADERS = ["ID_Evaluasi", "ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Mapel", "Materi",
                          "Target", "Capaian", "Penguatan", "Nilai"]
BATAS_HARI_SUSULAN = 30


def _tanggal_dari_teks(teks):
    try:
        return datetime.strptime(str(teks or "").strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def sesi_belum_dievaluasi(id_tutor, nama_tutor, hari_ini, batas_hari=BATAS_HARI_SUSULAN):
    """Sesi 'Hadir' milik tutor dalam batas_hari terakhir yang belum memiliki jurnal sesi."""
    # Hanya membaca: memakai worksheet ber-cache agar pengingat di Beranda tidak membebani API.
    hadir = baca_records_aman(get_or_create_worksheet("Kehadiran_Sesi", KEHADIRAN_HEADERS, rows="3000", cols="12"))
    nama_by_id = {
        str(s.get("ID_Siswa", "")).strip(): str(s.get("Nama_Lengkap", "")).strip()
        for s in baca_records_aman(get_worksheet("Data_Siswa"))
    }
    jurnal = baca_records_aman(get_or_create_worksheet("Jurnal_Sesi_Tutor_v2", JURNAL_SESI_HEADERS))
    nama_login = str(nama_tutor or "").strip().casefold()
    sudah = {
        (str(j.get("Tanggal", "")).strip()[:10], str(j.get("Nama_Siswa", "")).strip().casefold())
        for j in jurnal if str(j.get("Tutor", "")).strip().casefold() == nama_login
    }
    batas = hari_ini - timedelta(days=batas_hari)
    hasil, terlihat = [], set()
    for r in hadir:
        if str(r.get("ID_Tutor", "")).strip() != str(id_tutor or "").strip() or not str(id_tutor or "").strip():
            continue
        if str(r.get("Status_Kehadiran", "")).strip().casefold() != "hadir":
            continue
        tgl = _tanggal_dari_teks(r.get("Tanggal_Sesi"))
        nama = nama_by_id.get(str(r.get("ID_Siswa", "")).strip(), "")
        if not tgl or not nama or tgl < batas or tgl > hari_ini:
            continue
        kunci = (tgl.strftime("%Y-%m-%d"), nama.casefold())
        if kunci in sudah or kunci in terlihat:
            continue
        terlihat.add(kunci)
        hasil.append({"tanggal": tgl, "nama": nama, "id_siswa": str(r.get("ID_Siswa", "")).strip()})
    return sorted(hasil, key=lambda x: (-x["tanggal"].toordinal(), x["nama"].casefold()))


def simpan_jurnal_evaluasi_sesi(tanggal, nama_siswa, tutor, kondisi, keaktifan, kendala,
                                rekomendasi, handover, dokumentasi, evaluasi_mapel):
    """Simpan jurnal sesi dan evaluasi per mapel. Menolak jurnal ganda pada siswa, tanggal, dan tutor yang sama."""
    tgl = tanggal.strftime("%Y-%m-%d")
    ws_sesi = get_or_create_worksheet("Jurnal_Sesi_Tutor_v2", JURNAL_SESI_HEADERS)
    for j in baca_records_aman(ws_sesi, refresh=True):
        if (str(j.get("Tanggal", "")).strip()[:10] == tgl
                and str(j.get("Nama_Siswa", "")).strip().casefold() == str(nama_siswa).strip().casefold()
                and str(j.get("Tutor", "")).strip().casefold() == str(tutor).strip().casefold()):
            raise ValueError("Jurnal untuk siswa dan tanggal ini sudah ada, jadi tidak disimpan ganda.")
    id_sesi = "SES-" + uuid.uuid4().hex[:10].upper()
    ws_sesi.append_row([id_sesi, tgl, nama_siswa, tutor, kondisi, keaktifan, kendala,
                        rekomendasi, handover, dokumentasi])
    gagal_evaluasi = None
    try:
        ws_eval = get_or_create_worksheet("Evaluasi_Mapel_Tutor_v2", EVALUASI_MAPEL_HEADERS)
        baris = [
            ["EVL-" + uuid.uuid4().hex[:10].upper(), id_sesi, tgl, nama_siswa, tutor, mp,
             ev.get("Materi", ""), ev.get("Target", ""), ev.get("Capaian", ""),
             ev.get("Penguatan", ""), ev.get("Nilai", "")]
            for mp, ev in (evaluasi_mapel or {}).items()
        ]
        if baris:
            ws_eval.append_rows(baris, value_input_option="RAW")
    except Exception as exc:
        gagal_evaluasi = exc
    _baca_values_cache.clear()
    return id_sesi, gagal_evaluasi


def unggah_dokumentasi_evaluasi(daftar_file):
    """Unggah foto/video dokumentasi ke Drive. Mengembalikan (entri 'jenis::url', daftar peringatan)."""
    entri, peringatan = [], []
    for file_doc in list(daftar_file or []):
        if len(file_doc.getvalue()) > 30 * 1024 * 1024:
            peringatan.append(f"{file_doc.name} melebihi batas 30 MB dan tidak diunggah.")
            continue
        try:
            url_doc = upload_lampiran_ke_drive(
                file_doc.getvalue(), file_doc.name, file_doc.type or "application/octet-stream"
            )
            entri.append(f"{jenis_dari_mime(file_doc.type, file_doc.name)}::{url_doc}")
        except Exception as exc:
            peringatan.append(f"Lampiran {file_doc.name} gagal diunggah: {exc}")
    return entri, peringatan


def _form_evaluasi_susulan(nama_siswa, tanggal, tutor):
    kunci = f"{nama_siswa}_{tanggal.strftime('%Y%m%d')}"
    st.markdown(f"#### Evaluasi sesi {nama_siswa} · {tanggal.strftime('%d-%m-%Y')}")
    mapel = st.multiselect("Mata pelajaran yang diajarkan:", MAPEL_OPTIONS, key=f"evs_mapel_{kunci}")
    with st.form(f"evs_form_{kunci}"):
        evaluasi_mapel = {}
        for idx, mp in enumerate(mapel):
            st.markdown(f"**{mp}**")
            materi = st.text_input(f"Materi {mp}", key=f"evs_materi_{kunci}_{idx}")
            target = st.text_input(f"Target belajar {mp}", key=f"evs_target_{kunci}_{idx}")
            capaian = st.text_area(f"Kompetensi yang dikuasai / hasil belajar {mp}", key=f"evs_capaian_{kunci}_{idx}")
            penguatan = st.text_area(f"Bagian yang perlu penguatan {mp}", key=f"evs_penguatan_{kunci}_{idx}")
            nilai = st.text_input(f"Nilai latihan (opsional) {mp}", key=f"evs_nilai_{kunci}_{idx}")
            evaluasi_mapel[mp] = {"Materi": materi, "Target": target, "Capaian": capaian,
                                  "Penguatan": penguatan, "Nilai": nilai}
        kondisi = st.selectbox("Kondisi siswa:", ["Baik", "Cukup", "Kurang fokus", "Lelah", "Perlu perhatian khusus"],
                               key=f"evs_kondisi_{kunci}")
        keaktifan = st.selectbox("Keaktifan siswa:", ["Sangat aktif", "Aktif", "Cukup aktif", "Pasif"],
                                 key=f"evs_aktif_{kunci}")
        kendala = st.text_area("Kendala selama sesi:", key=f"evs_kendala_{kunci}")
        rekomendasi = st.text_area("Rekomendasi / tindak lanjut:", key=f"evs_rekom_{kunci}")
        handover = st.text_area("Catatan untuk tutor berikutnya (handover):", key=f"evs_handover_{kunci}")
        dokumentasi = st.text_input("Link dokumentasi (opsional):", key=f"evs_dok_{kunci}")
        file_dok = st.file_uploader(
            "Lampiran evaluasi tutor (foto/video):",
            type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "webm", "m4v"],
            accept_multiple_files=True, key=f"evs_file_{kunci}"
        )
        kirim = st.form_submit_button("💾 Simpan Evaluasi Susulan")
    if not kirim:
        return
    if not mapel:
        st.error("Pilih minimal satu mata pelajaran yang diajarkan pada sesi ini.")
        return
    try:
        daftar_dok = [dokumentasi.strip()] if dokumentasi.strip() else []
        entri, peringatan = unggah_dokumentasi_evaluasi(file_dok)
        daftar_dok += entri
        id_sesi, gagal = simpan_jurnal_evaluasi_sesi(
            tanggal, nama_siswa, tutor, kondisi, keaktifan, kendala, rekomendasi, handover,
            " | ".join(daftar_dok), evaluasi_mapel
        )
        pesan = f"✅ Evaluasi susulan {nama_siswa} tanggal {tanggal.strftime('%d-%m-%Y')} tersimpan (ID sesi {id_sesi})."
        if gagal:
            pesan += f" ⚠️ Evaluasi per mapel belum seluruhnya tersimpan ({gagal}). Jangan kirim ulang; catat ID sesi ini."
        if peringatan:
            pesan += " " + " ".join(peringatan)
        st.session_state["_evs_notice"] = pesan
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        if exc.__class__.__name__ in ("RerunException", "StopException"):
            raise
        st.error(f"Evaluasi belum tersimpan: {exc}. Periksa riwayat sebelum mencoba lagi.")


def tampilkan_evaluasi_susulan(id_tutor, nama_tutor):
    st.subheader("🗓️ Evaluasi Susulan")
    st.caption(
        f"Isi lembar evaluasi sesi yang terlewat, sampai {BATAS_HARI_SUSULAN} hari ke belakang. "
        "Hasilnya tersimpan sama seperti jurnal dan evaluasi sesi biasa."
    )
    notice = st.session_state.pop("_evs_notice", None)
    if notice:
        st.success(notice)
    hari_ini = waktu_lokal().date()
    try:
        tertunda = sesi_belum_dievaluasi(id_tutor, nama_tutor, hari_ini)
    except Exception as exc:
        st.error(f"Daftar sesi belum dapat dibaca: {exc}")
        tertunda = []
    cara = st.radio(
        "Pilih sesi dari:", ["Daftar kehadiran yang belum dievaluasi", "Pilih manual (siswa dan tanggal)"],
        horizontal=True, key="evs_cara"
    )
    nama_target, tanggal_target = None, None
    if cara.startswith("Daftar"):
        if not tertunda:
            st.info(f"Semua sesi hadir dalam {BATAS_HARI_SUSULAN} hari terakhir sudah punya evaluasi.")
        else:
            peta = {f"{x['tanggal'].strftime('%d-%m-%Y')} · {x['nama']}": x for x in tertunda}
            st.caption(f"{len(tertunda)} sesi belum dievaluasi.")
            pilih = st.selectbox("Pilih sesi:", list(peta.keys()), key="evs_pilih")
            nama_target, tanggal_target = peta[pilih]["nama"], peta[pilih]["tanggal"]
    else:
        kata = st.text_input("Ketik nama siswa (minimal 3 huruf):", key="evs_cari").strip()
        if kata and len(kata) < 3:
            st.caption("Ketik minimal 3 huruf untuk mencari.")
        elif kata:
            try:
                cocok = sorted({n for n in get_siswa_aktif() if kata.casefold() in n.casefold()})
            except Exception as exc:
                st.error(f"Daftar siswa belum dapat dibaca: {exc}")
                cocok = []
            if not cocok:
                st.info("Tidak ada siswa aktif dengan nama tersebut.")
            else:
                nama_target = cocok[0] if len(cocok) == 1 else st.selectbox(
                    "Ada beberapa nama yang cocok, pilih salah satu:", cocok[:8], key=f"evs_cocok_{kata.casefold()}"
                )
        if nama_target:
            tanggal_target = st.date_input(
                "Tanggal sesi:", value=hari_ini - timedelta(days=1),
                min_value=hari_ini - timedelta(days=BATAS_HARI_SUSULAN), max_value=hari_ini, key="evs_tanggal"
            )
    if nama_target and tanggal_target:
        _form_evaluasi_susulan(nama_target, tanggal_target, nama_tutor)


def baca_evaluasi_mapel_anak(nama_anak, batas=50):
    """Evaluasi per mapel untuk satu anak, terbaru dulu. Catatan internal (handover, kendala) tidak ikut."""
    try:
        rows = baca_records_aman(get_worksheet("Evaluasi_Mapel_Tutor_v2"))
    except gspread.WorksheetNotFound:
        return []
    target = str(nama_anak or "").strip().casefold()
    cocok = [r for r in rows if target and str(r.get("Nama_Siswa", "")).strip().casefold() == target]
    cocok.sort(key=lambda r: str(r.get("Tanggal", "")), reverse=True)
    return cocok[:batas]


def rekonsiliasi_sesi_aktif_siswa(siswa_id, status_by_task, nilai_ids):
    """Tutup hanya sesi aktif yang tugasnya sudah terbukti terkirim atau dinilai.

    Tidak menghapus baris riwayat dan tidak membuka sesi yang status pengumpulannya
    belum jelas. Dipakai untuk memulihkan kunci tertinggal setelah pengiriman berhasil.
    """
    sid = str(siswa_id or "").strip()
    if not sid:
        return False
    sesi = baca_sesi_aktif_siswa(sid)
    if not sesi:
        return False
    tid = str(sesi.get("ID_Tugas", "")).strip()
    status = str(status_by_task.get(tid, "")).strip().lower()
    sudah_dikirim = (
        tid in {str(x).strip() for x in (nilai_ids or set())}
        or (tid, str(siswa_id).strip()) in (nilai_ids or set())
        or "dikirim" in status
        or "menunggu" in status
        or "dinilai" in status
    )
    if not sudah_dikirim:
        return False
    return akhiri_sesi_online(sid, tid)


def get_student_tasks():
    """Membaca tugas dari sheet V2, dengan konversi aman untuk sheet lama."""
    try:
        ws = get_worksheet("Tugas_Sesi_Siswa_v2")
        records = baca_records_aman(ws)
        # Satu pembacaan Data_Siswa untuk seluruh tugas lama, bukan satu API read per tugas.
        siswa_rows = baca_records_aman(get_worksheet("Data_Siswa"))
        nama_ke_id = {}
        nama_ganda = set()
        for siswa in siswa_rows:
            nama = str(siswa.get("Nama_Lengkap", "")).strip().casefold()
            sid = str(siswa.get("ID_Siswa", "")).strip()
            aktif = str(siswa.get("Status", "Aktif")).strip().casefold() not in ("nonaktif", "tidak aktif")
            if nama and sid and aktif:
                if nama in nama_ke_id:
                    nama_ganda.add(nama)
                else:
                    nama_ke_id[nama] = sid
        for rec in records:
            if not str(rec.get("ID_Siswa", "")).strip():
                nama = str(rec.get("Nama_Siswa", "")).strip().casefold()
                if nama and nama not in nama_ganda:
                    rec["ID_Siswa"] = nama_ke_id.get(nama, "")
        return records
    except gspread.WorksheetNotFound:
        try:
            ws = get_worksheet("Tugas_Sesi_Siswa")
            old = baca_records_aman(ws)
        except gspread.WorksheetNotFound:
            return []
        converted = []
        for r in old:
            if r.get("ID_Tugas") or r.get("Nama_Siswa"):
                converted.append({**r, "Judul_Tugas": r.get("Judul_Tugas", r.get("Instruksi", "")), "Soal_JSON": r.get("Soal_JSON", "")})
        return converted


NILAI_TUGAS_HEADERS = [
    "ID_Nilai", "ID_Penugasan", "ID_Siswa", "ID_Tutor_Penilai",
    "Nilai", "Nilai_Maksimal", "Umpan_Balik", "Tanggal_Penilaian"
]


def get_nilai_tugas_worksheet():
    """Ambil sheet nilai dengan skema aktif; tidak mengubah header/data lama."""
    ws = get_or_create_worksheet(
        "DB_Nilai_Tugas", NILAI_TUGAS_HEADERS,
        rows="5000", cols=str(len(NILAI_TUGAS_HEADERS))
    )
    headers = [str(x).strip() for x in ws.row_values(1)]
    if headers != NILAI_TUGAS_HEADERS:
        raise ValueError(
            "Header DB_Nilai_Tugas tidak sesuai. Tidak ada perubahan data. "
            "Header yang dibutuhkan: " + ", ".join(NILAI_TUGAS_HEADERS)
        )
    return ws


def kunci_nilai_penugasan(record):
    """Kunci satu nilai akhir per pasangan penugasan dan siswa."""
    return (
        str(record.get("ID_Penugasan", record.get("ID_Tugas", ""))).strip(),
        str(record.get("ID_Siswa", "")).strip(),
    )


def indeks_nilai_penugasan(records):
    """Indeks nilai yang kompatibel dengan header baru dan rekaman lama."""
    hasil = {}
    for record in records or []:
        key = kunci_nilai_penugasan(record)
        if all(key):
            hasil[key] = record
    return hasil




def baca_nilai_tugas_terpadu(refresh=False):
    """Baca nilai kanonis dan pulihkan baris lama hanya melalui ID_Jawaban
    yang cocok persis dengan DB_Persetujuan_Nilai. Fungsi ini read-only.
    Baris lama yang tidak dapat dipetakan tidak ditebak atau diubah.
    """
    ws = get_nilai_tugas_worksheet()
    nilai_raw = baca_records_aman(ws, refresh=refresh)
    try:
        ws_persetujuan = _sheet_v2("DB_Persetujuan_Nilai", PERSETUJUAN_NILAI_HEADERS)
        persetujuan = baca_records_aman(ws_persetujuan, refresh=refresh)
    except Exception:
        persetujuan = []

    approval_by_answer = {}
    for approval in persetujuan:
        answer_id = str(approval.get("ID_Jawaban", "")).strip()
        status = str(approval.get("Status_Persetujuan", "")).strip().casefold()
        if answer_id and status == "disetujui dan diterbitkan":
            approval_by_answer[answer_id] = approval

    hasil = []
    for record in nilai_raw:
        id_penugasan = str(record.get("ID_Penugasan", "")).strip()
        id_siswa = str(record.get("ID_Siswa", "")).strip()
        if id_penugasan.startswith("TGS-") and id_siswa.startswith("SIS-"):
            hasil.append(record)
            continue

        approval = approval_by_answer.get(id_penugasan)
        if not approval:
            continue

        hasil.append({
            "ID_Nilai": record.get("ID_Nilai", ""),
            "ID_Penugasan": str(approval.get("ID_Tugas", "")).strip(),
            "ID_Siswa": str(approval.get("ID_Siswa", "")).strip(),
            "ID_Tutor_Penilai": "",
            "Nilai": str(approval.get("Nilai_Akhir", record.get("Nilai", ""))).strip(),
            "Nilai_Maksimal": "100",
            "Umpan_Balik": str(approval.get("Catatan", "") or record.get("Nilai_Maksimal", "")),
            "Tanggal_Penilaian": str(approval.get("Waktu_Persetujuan", "") or record.get("Tanggal_Penilaian", "")),
            "_ID_Jawaban": id_penugasan,
            "_Dipulihkan_Dari_Persetujuan": True,
            "_baris": record.get("_baris", ""),
        })
    return hasil

def get_answers_worksheet():
    try:
        ws = get_worksheet("DB_Jawaban_Siswa")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="DB_Jawaban_Siswa", rows="3000", cols="8")
        ws.append_row(ANSWER_HEADERS)
        _worksheet_header_cached.clear()
    headers = _worksheet_header_cached(init_spreadsheet().id, "DB_Jawaban_Siswa")
    if not header_cocok(headers, ANSWER_HEADERS):
        raise ValueError("Header DB_Jawaban_Siswa tidak sesuai. Struktur yang dibutuhkan: " + ", ".join(ANSWER_HEADERS))
    return ws


LAMPIRAN_JAWABAN_HEADERS = [
    "ID_Lampiran", "ID_Tugas", "ID_Siswa", "Nama_File", "Mime_Type",
    "URL_Drive", "Waktu_Upload", "Status_Lampiran"
]


def get_lampiran_jawaban_worksheet():
    """Sheet terpisah agar struktur DB_Jawaban_Siswa lama tetap utuh."""
    ws = get_or_create_worksheet("DB_Lampiran_Jawaban", LAMPIRAN_JAWABAN_HEADERS, rows="3000", cols="8")
    if not header_cocok(ws.row_values(1), LAMPIRAN_JAWABAN_HEADERS):
        raise ValueError("Header DB_Lampiran_Jawaban tidak sesuai. Data tidak ditulis.")
    return ws


LOG_GAGAL_PENGIRIMAN_HEADERS = [
    "ID_Log", "Waktu", "ID_Tugas", "ID_Siswa", "Tahap", "Jenis_Gagal",
    "Jumlah_File", "Referensi_File_Drive"
]


def catat_log_gagal_pengiriman(task_id, student_id, tahap, exc, url_drive=()):
    """Catat kegagalan tanpa menyimpan PIN, token, isi jawaban, atau data sensitif lain."""
    try:
        ws = get_or_create_worksheet(
            "Log_Gagal_Pengiriman", LOG_GAGAL_PENGIRIMAN_HEADERS,
            rows="1000", cols=str(len(LOG_GAGAL_PENGIRIMAN_HEADERS))
        )
        headers = [str(x).strip() for x in ws.row_values(1)]
        if headers != LOG_GAGAL_PENGIRIMAN_HEADERS:
            return False
        urls = [str(x).strip() for x in (url_drive or ()) if str(x).strip()]
        ws.append_row([
            "ERR-" + uuid.uuid4().hex[:10].upper(),
            waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
            str(task_id or ""), str(student_id or ""), str(tahap or ""),
            exc.__class__.__name__ if isinstance(exc, BaseException) else str(exc)[:80],
            len(urls), json.dumps(urls, ensure_ascii=False)
        ], value_input_option="RAW")
        _baca_values_cache.clear()
        return True
    except Exception:
        return False


STATUS_LAMPIRAN_KOREKSI = "Koreksi Tutor"
STATUS_LAMPIRAN_BAHAN = "Bahan Tutor"


def simpan_lampiran_jawaban(task_id, student_id, uploaded_files, oleh_tutor=False, status="Terkirim"):
    """Upload lampiran setelah memastikan akun siswa/tutor berhak atas tugas tersebut."""
    if not uploaded_files:
        return []

    # Gunakan pembacaan tugas yang sudah menormalkan data lama (termasuk
    # pemetaan ID_Siswa dari Nama_Siswa yang unik). Data tugas dibaca ulang
    # agar keputusan akses tidak bergantung pada daftar tugas di tampilan.
    try:
        ws_tugas = get_worksheet("Tugas_Sesi_Siswa_v2")
        tugas_rows = baca_records_aman(ws_tugas, refresh=True)
        # Untuk baris historis yang belum memiliki ID_Siswa, lakukan pemetaan
        # hanya bila nama siswa cocok secara unik dengan Data_Siswa.
        siswa_rows = baca_records_aman(get_worksheet("Data_Siswa"), refresh=True)
        nama_ke_id, nama_ganda = {}, set()
        for siswa in siswa_rows:
            nama = str(siswa.get("Nama_Lengkap", "")).strip().casefold()
            sid = str(siswa.get("ID_SISWA", siswa.get("ID_Siswa", ""))).strip()
            aktif = str(siswa.get("Status", "Aktif")).strip().casefold() not in ("nonaktif", "tidak aktif")
            if nama and sid and aktif:
                if nama in nama_ke_id:
                    nama_ganda.add(nama)
                else:
                    nama_ke_id[nama] = sid
        for row in tugas_rows:
            if not str(row.get("ID_Siswa", "")).strip():
                nama = str(row.get("Nama_Siswa", "")).strip().casefold()
                if nama and nama not in nama_ganda:
                    row["ID_Siswa"] = nama_ke_id.get(nama, "")
    except gspread.WorksheetNotFound:
        tugas_rows = get_student_tasks()
    tugas = next((r for r in tugas_rows
                  if str(r.get("ID_Tugas", "")).strip() == str(task_id or "").strip()), None)
    if not tugas:
        raise ValueError("Data tugas tidak ditemukan. Lampiran tidak diunggah.")

    sid_tugas = str(tugas.get("ID_Siswa", "")).strip()
    sid_parameter = str(student_id or "").strip()
    if not sid_tugas or sid_parameter != sid_tugas:
        raise ValueError("ID siswa tidak cocok dengan pemilik tugas. Lampiran tidak diunggah.")

    if oleh_tutor:
        tutor_id = str(st.session_state.get("tutor_id", "")).strip()
        tutor_nama = str(st.session_state.get("tutor_nama", "")).strip()
        if not st.session_state.get("tutor_logged_in") or not tutor_id:
            raise ValueError("Sesi tutor tidak valid. Lampiran tidak diunggah.")
        if not tugas_milik_tutor(tugas, tutor_id, tutor_nama):
            raise ValueError("Tutor tidak memiliki akses ke tugas ini. Lampiran tidak diunggah.")
    else:
        sid_sesi = str(st.session_state.get("siswa_id", "")).strip()
        if not st.session_state.get("siswa_logged_in") or not sid_sesi or sid_sesi != sid_parameter:
            raise ValueError("Sesi akun siswa tidak cocok. Lampiran tidak diunggah.")

    siap = []
    for file_item in uploaded_files:
        data, nama, mime = kompres_gambar_untuk_unggah(
            file_item.getvalue(), file_item.name, file_item.type or "application/octet-stream"
        )
        if len(data) > BATAS_UNGGAH_BYTES:
            raise ValueError(
                f"File {nama} melebihi batas 10 MB. Foto dikecilkan otomatis; kompres video/audio lebih dulu."
            )
        siap.append((data, nama, mime))
    if sum(len(d) for d, _, _ in siap) > 40 * 1024 * 1024:
        raise ValueError("Total lampiran satu pengiriman maksimal 40 MB.")
    ws = get_lampiran_jawaban_worksheet()
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    hasil = []
    urls_terunggah = []
    try:
        for data, nama, mime in siap:
            url = upload_lampiran_ke_drive(data, nama, mime)
            urls_terunggah.append(url)
            rows.append([
                "LMP-" + uuid.uuid4().hex[:10].upper(), task_id, student_id,
                nama, mime, url, now, status
            ])
            hasil.append({"Nama_File": nama, "URL_Drive": url, "Mime_Type": mime})
        if rows:
            ws.append_rows(rows, value_input_option="RAW")
            _baca_values_cache.clear()
        return hasil
    except Exception as exc:
        # File Drive tidak dihapus; URL dicatat agar dapat direkonsiliasi tanpa upload ulang buta.
        catat_log_gagal_pengiriman(task_id, student_id, "unggah_lampiran_atau_catat_sheet", exc, urls_terunggah)
        raise


def baca_lampiran_jawaban(task_id, student_id, refresh=False, jenis="siswa"):
    """Baca lampiran berdasarkan pasangan ID tugas+siswa. jenis='siswa' = hasil pekerjaan siswa/tutor-input;
    jenis='tutor' = koreksi foto dan bahan belajar dari tutor (dipisah agar tidak tercampur)."""
    try:
        ws = get_lampiran_jawaban_worksheet()
        dari_tutor = (STATUS_LAMPIRAN_KOREKSI.casefold(), STATUS_LAMPIRAN_BAHAN.casefold())
        return [r for r in baca_records_aman(ws, refresh=refresh)
                if str(r.get("ID_Tugas", "")).strip() == str(task_id).strip()
                and str(r.get("ID_Siswa", "")).strip() == str(student_id).strip()
                and ((str(r.get("Status_Lampiran", "")).strip().casefold() in dari_tutor) == (jenis == "tutor"))]
    except gspread.WorksheetNotFound:
        return []


PESAN_ORTU_HEADERS = [
    "ID_Pesan", "ID_Ortu", "ID_Siswa", "Nama_Siswa", "Pesan",
    "URL_Lampiran", "Nama_File", "Mime_Type", "Waktu_Kirim",
    "Status_Pesan", "Balasan_Tutor", "Nama_Tutor", "Waktu_Balasan"
]


def get_pesan_ortu_worksheet():
    """Ambil/buat sheet pesan orang tua dan inisialisasi header hanya jika baris pertama kosong.

    Tidak menimpa header yang sudah ada atau mengubah riwayat pesan. Jika ditemukan
    header lain, hentikan penulisan dan tampilkan diagnosis agar data lama aman.
    """
    nama_sheet = "Pesan_Orangtua_Tutor"
    try:
        ws = get_worksheet(nama_sheet)
    except gspread.WorksheetNotFound:
        try:
            ws = sheet.add_worksheet(title=nama_sheet, rows="3000", cols="13")
        except Exception as exc:
            raise RuntimeError(
                f"Sheet {nama_sheet} belum ada dan gagal dibuat. Periksa izin edit "
                f"akun layanan Google Sheets. Detail: {exc}"
            ) from exc

    # Sheet mungkin pernah dibuat tetapi proses sebelumnya terhenti sebelum header ditulis.
    actual = [str(x).strip() for x in ws.row_values(1)]
    while actual and actual[-1] == "":
        actual.pop()

    if not actual:
        try:
            ws.update([PESAN_ORTU_HEADERS], "A1:M1", value_input_option="RAW")
            actual = [str(x).strip() for x in ws.row_values(1)]
            while actual and actual[-1] == "":
                actual.pop()
        except Exception as exc:
            raise RuntimeError(
                f"Sheet {nama_sheet} berhasil ditemukan/dibuat, tetapi header gagal ditulis. "
                f"Periksa izin edit Google Sheets. Detail: {exc}"
            ) from exc

    if not header_cocok(actual, PESAN_ORTU_HEADERS):
        raise ValueError(
            f"Struktur header sheet {nama_sheet} berbeda dari format yang diperlukan. "
            f"Header terbaca: {actual!r}. Tidak ada data yang ditulis atau dihapus. "
            "Periksa sheet sebelum melakukan perubahan manual."
        )
    return ws


def simpan_pesan_ortu(id_ortu, id_siswa, nama_siswa, pesan, files):
    files = list(files or [])
    if sum(len(f.getvalue()) for f in files) > 40 * 1024 * 1024:
        raise ValueError("Total lampiran satu pesan maksimal 40 MB.")
    ws = get_pesan_ortu_worksheet()
    urls, names, mimes = [], [], []
    for f in files or []:
        data = f.getvalue()
        if len(data) > 20 * 1024 * 1024:
            raise ValueError(f"{f.name} melebihi batas 20 MB.")
        mime = f.type or "application/octet-stream"
        url = upload_lampiran_ke_drive(data, f.name, mime)
        urls.append(url)
        names.append(f.name)
        mimes.append(mime)
    if not str(pesan or "").strip() and not urls:
        raise ValueError("Isi pesan atau lampirkan minimal satu foto/video.")
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        "PES-" + uuid.uuid4().hex[:10].upper(), id_ortu, id_siswa, nama_siswa,
        str(pesan or "").strip(), "|".join(urls), "|".join(names),
        "|".join(mimes), now, "Menunggu Tutor", "", "", ""
    ], value_input_option="RAW")
    return True


def tampilkan_media_url(url, mime="", nama="Lampiran"):
    jenis = jenis_dari_mime(mime, nama)
    fid = drive_id(url)
    media_url = f"https://drive.google.com/uc?export=download&id={fid}" if fid else url
    if jenis == "video":
        st.video(media_url)
    elif jenis == "audio":
        st.audio(media_url)
    elif jenis == "img":
        st.image(img_url(url), caption=nama, use_container_width=True)
    else:
        st.link_button(f"📎 Buka {nama}", url, use_container_width=True)


class _BerkasMemori:
    """Pembungkus byte agar bisa dikirim lewat simpan_lampiran_jawaban seperti file unggahan."""
    def __init__(self, nama, tipe, data):
        self.name, self.type, self._data = nama, tipe, data

    def getvalue(self):
        return self._data


try:
    from streamlit_image_coordinates import streamlit_image_coordinates as _komponen_klik
except Exception:  # komponen opsional; tanpa itu dipakai penggeser posisi
    _komponen_klik = None


def _unduh_gambar_drive(url):
    """Unduh foto lampiran (di-cache per sesi) sebagai objek PIL."""
    from PIL import Image
    import io
    kunci = "_img_cache_" + hashlib.md5(str(url).encode()).hexdigest()
    data = st.session_state.get(kunci)
    if data is None:
        fid = drive_id(url)
        alamat = f"https://drive.google.com/uc?export=download&id={fid}" if fid else url
        resp = requests.get(alamat, timeout=25)
        resp.raise_for_status()
        data = resp.content
        st.session_state[kunci] = data
    gambar = Image.open(io.BytesIO(data))
    try:
        from PIL import ImageOps
        gambar = ImageOps.exif_transpose(gambar)
    except Exception:
        pass
    return gambar.convert("RGB")


def _gambar_dengan_tanda(gambar, tanda):
    """Gambar ✅/❌/❓ di atas salinan foto. tanda: [(jenis, x_persen, y_persen)]."""
    from PIL import ImageDraw
    salin = gambar.copy()
    gb = ImageDraw.Draw(salin)
    w, h = salin.size
    r = max(22, int(min(w, h) * 0.035))
    tebal = max(5, r // 4)
    for jenis, xp, yp in tanda:
        x, y = int(w * xp / 100), int(h * yp / 100)
        if jenis == "❌":
            gb.line([(x - r, y - r), (x + r, y + r)], fill=(220, 30, 30), width=tebal)
            gb.line([(x - r, y + r), (x + r, y - r)], fill=(220, 30, 30), width=tebal)
        elif jenis == "✅":
            gb.line([(x - r, y), (x - r // 3, y + r), (x + r, y - r)], fill=(20, 150, 60), width=tebal)
        else:
            gb.ellipse([x - r, y - r, x + r, y + r], outline=(240, 150, 0), width=tebal)
            gb.text((x - r // 4, y - r // 2), "?", fill=(240, 150, 0))
    return salin


def tampilkan_koreksi_tutor(id_tugas, id_siswa):
    """Panel tutor: (1) unggah foto yang sudah ditandai / kunci / pembahasan untuk siswa,
    (2) tandai foto jawaban siswa langsung dengan ✅/❌."""
    id_tugas, id_siswa = str(id_tugas).strip(), str(id_siswa).strip()
    kunci = f"{id_tugas}_{id_siswa}"
    with st.expander("🖍️ Koreksi foto & bahan belajar untuk siswa", expanded=False):
        # ---- Tingkat 1: unggah berkas dari tutor
        st.markdown("**1. Unggah foto koreksi / kunci / pembahasan**")
        st.caption("Tandai foto lebih dulu di HP (markup Galeri/Google Foto) atau siapkan PDF kunci, lalu unggah di sini.")
        jenis_lamp = st.radio("Jenis berkas:", ["Foto koreksi (sudah ditandai)", "Kunci jawaban / pembahasan"],
                              key=f"kor_jenis_{kunci}", horizontal=True)
        berkas = st.file_uploader("Pilih berkas (JPG, PNG, PDF):", type=["jpg", "jpeg", "png", "webp", "pdf"],
                                  accept_multiple_files=True, key=f"kor_file_{kunci}")
        if st.button("📤 Kirim ke siswa", key=f"kor_kirim_{kunci}", disabled=not berkas):
            try:
                simpan_lampiran_jawaban(
                    id_tugas, id_siswa, berkas, oleh_tutor=True,
                    status=STATUS_LAMPIRAN_KOREKSI if jenis_lamp.startswith("Foto") else STATUS_LAMPIRAN_BAHAN)
                st.success("Terkirim. Siswa dapat melihatnya di tugas ini.")
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal mengunggah: {exc}")

        # ---- Tingkat 2: tandai foto langsung
        st.markdown("---")
        st.markdown("**2. Tandai foto jawaban siswa**")
        foto = [x for x in baca_lampiran_jawaban(id_tugas, id_siswa, refresh=True)
                if jenis_dari_mime(x.get("Mime_Type", ""), x.get("Nama_File", "")) == "img"]
        if not foto:
            st.caption("Belum ada foto jawaban siswa untuk ditandai.")
        else:
            peta = {f"{i + 1}. {x.get('Nama_File', 'foto')}": x for i, x in enumerate(foto)}
            pilih = st.selectbox("Pilih foto:", list(peta), key=f"tnd_foto_{kunci}")
            item = peta[pilih]
            kunci_tanda = f"_tanda_{kunci}_{item.get('ID_Lampiran', pilih)}"
            tanda = st.session_state.setdefault(kunci_tanda, [])
            jenis = st.radio("Tanda:", ["❌", "✅", "❓"], key=f"tnd_jenis_{kunci}", horizontal=True)
            try:
                asli = _unduh_gambar_drive(item.get("URL_Drive", ""))
            except Exception as exc:
                asli = None
                st.error(f"Foto belum bisa dimuat untuk ditandai ({exc.__class__.__name__}). "
                         "Gunakan cara 1 (unggah foto yang sudah ditandai).")
            if asli is not None:
                pratinjau = _gambar_dengan_tanda(asli, tanda)
                if _komponen_klik is not None:
                    st.caption("Ketuk bagian foto yang ingin ditandai.")
                    lebar = 640
                    klik = _komponen_klik(pratinjau, width=lebar, key=f"tnd_klik_{kunci}_{len(tanda)}")
                    if klik and klik.get("width"):
                        titik = (round(klik["x"] * 100 / klik["width"], 1), round(klik["y"] * 100 / klik["height"], 1))
                        if st.session_state.get(f"_klik_terakhir_{kunci}") != (len(tanda), titik):
                            tanda.append((jenis, titik[0], titik[1]))
                            st.session_state[f"_klik_terakhir_{kunci}"] = (len(tanda), titik)
                            st.rerun()
                else:
                    st.image(pratinjau, use_container_width=True)
                    st.caption("Mode penggeser (komponen ketuk belum terpasang).")
                    xp = st.slider("Posisi mendatar (%)", 0, 100, 50, key=f"tnd_x_{kunci}")
                    yp = st.slider("Posisi tegak (%)", 0, 100, 50, key=f"tnd_y_{kunci}")
                    if st.button("➕ Tempel tanda di posisi ini", key=f"tnd_tempel_{kunci}"):
                        tanda.append((jenis, xp, yp))
                        st.rerun()
                c1, c2 = st.columns(2)
                if c1.button("↩️ Batalkan tanda terakhir", key=f"tnd_undo_{kunci}", disabled=not tanda):
                    tanda.pop()
                    st.rerun()
                if c2.button("💾 Simpan & kirim foto bertanda", key=f"tnd_simpan_{kunci}", disabled=not tanda, type="primary"):
                    try:
                        import io
                        buf = io.BytesIO()
                        pratinjau.save(buf, format="JPEG", quality=88)
                        nama_asli = str(item.get("Nama_File", "foto")).rsplit(".", 1)[0]
                        simpan_lampiran_jawaban(
                            id_tugas, id_siswa,
                            [_BerkasMemori(f"koreksi_{nama_asli}.jpg", "image/jpeg", buf.getvalue())],
                            oleh_tutor=True, status=STATUS_LAMPIRAN_KOREKSI)
                        st.session_state[kunci_tanda] = []
                        st.success("Foto bertanda terkirim ke siswa. Foto asli tetap tersimpan.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Gagal menyimpan foto bertanda: {exc}")

        sudah = baca_lampiran_jawaban(id_tugas, id_siswa, refresh=True, jenis="tutor")
        if sudah:
            st.markdown("---")
            st.markdown("**Sudah dikirim ke siswa:**")
            for lamp in sudah:
                tampilkan_media_url(lamp.get("URL_Drive", ""), lamp.get("Mime_Type", ""), lamp.get("Nama_File", "Lampiran"))


def tampilkan_bahan_tutor_siswa(id_tugas, id_siswa):
    """Sisi siswa: koreksi foto dan bahan belajar dari tutor untuk tugas ini."""
    try:
        bahan = baca_lampiran_jawaban(id_tugas, id_siswa, refresh=True, jenis="tutor")
    except Exception:
        return
    if not bahan:
        return
    st.markdown("#### 📚 Koreksi & bahan belajar dari tutor")
    for lamp in bahan:
        tampilkan_media_url(lamp.get("URL_Drive", ""), lamp.get("Mime_Type", ""), lamp.get("Nama_File", "Lampiran"))


def baca_bank_soal_semua():
    ws = get_worksheet("Bank_Soal_Master")
    return baca_records_aman(ws, refresh=True)


def ubah_status_soal_bank(daftar_kode, status_baru):
    """Ubah Status baris soal berdasarkan Kode_Soal pada data segar. Mengembalikan jumlah baris yang diubah."""
    ws = get_worksheet("Bank_Soal_Master")
    data = ws.get_all_values()
    if not data:
        return 0
    h = [str(x).strip() for x in data[0]]
    i_kode, i_status = h.index("Kode_Soal"), h.index("Status")
    target = {str(k).strip() for k in daftar_kode}
    pembaruan = [{"range": gspread.utils.rowcol_to_a1(n, i_status + 1), "values": [[status_baru]]}
                 for n, row in enumerate(data[1:], start=2)
                 if i_kode < len(row) and str(row[i_kode]).strip() in target]
    if pembaruan:
        ws.batch_update(pembaruan, value_input_option="RAW")
        _baca_values_cache.clear()
    return len(pembaruan)


def hapus_soal_bank_nonaktif(daftar_kode):
    """Hapus permanen HANYA baris berstatus Nonaktif. Hapus dari bawah agar nomor baris tidak bergeser."""
    ws = get_worksheet("Bank_Soal_Master")
    data = ws.get_all_values()
    h = [str(x).strip() for x in data[0]]
    i_kode, i_status = h.index("Kode_Soal"), h.index("Status")
    target = {str(k).strip() for k in daftar_kode}
    baris = [n for n, row in enumerate(data[1:], start=2)
             if i_kode < len(row) and str(row[i_kode]).strip() in target
             and i_status < len(row) and str(row[i_status]).strip().casefold() == "nonaktif"]
    for n in sorted(baris, reverse=True):
        ws.delete_rows(n)
    _baca_values_cache.clear()
    return len(baris)


def tampilkan_pembersih_bank(tampil):
    """Nonaktifkan soal yang kacau (bisa dipulihkan), atau hapus permanen yang sudah nonaktif."""
    with st.expander("🧹 Bersihkan soal yang kacau", expanded=False):
        mode = st.radio("Aksi:", ["Nonaktifkan soal", "Pulihkan / hapus soal nonaktif"], key="bersih_mode", horizontal=True)
        if mode == "Nonaktifkan soal":
            st.caption("Soal nonaktif hilang dari bank dan bisa dipulihkan. Tugas yang sudah dikirim memakai salinan soal sendiri.")
            cakupan = st.radio("Cakupan:", ["Per paket", "Per soal", "Semua soal aktif"], horizontal=True, key="bersih_cakupan")
            try:
                aktif_bank = [x for x in baca_records_aman(get_worksheet("Bank_Soal_Master")) if _soal_aktif(x)]
            except Exception as exc:
                aktif_bank = []
                st.error(f"Gagal membaca bank: {exc}")
            dipilih, label_cakupan = [], ""
            if cakupan == "Per paket":
                paket = {}
                for x in aktif_bank:
                    nama = re.sub(r"\s+", " ", str(x.get("Bab_Atau_Topik", "") or "")).strip() or "(tanpa paket)"
                    paket.setdefault(nama, []).append(str(x.get("Kode_Soal", "")).strip())
                pilih_paket = st.multiselect("Pilih paket:", sorted(paket, key=str.casefold), key="bersih_paket",
                                             format_func=lambda n: f"{n} ({len(paket[n])} soal)")
                dipilih = [c for n in pilih_paket for c in paket[n] if c]
                label_cakupan = f"{len(pilih_paket)} paket"
            elif cakupan == "Per soal":
                semua = st.checkbox(f"Pilih semua {len(tampil)} soal sesuai filter di atas", key="bersih_semua")
                peta = {str(x.get("Kode_Soal", "")): x for x in tampil}
                if semua:
                    dipilih = list(peta)
                else:
                    dipilih = st.multiselect(
                        "Pilih soal:", list(peta), key="bersih_pilih",
                        format_func=lambda c: f"{c} | {pisah_wacana(peta[c].get('Teks_Soal', ''))[1][:60]}")
                label_cakupan = "soal terpilih"
            else:
                dipilih = [str(x.get("Kode_Soal", "")).strip() for x in aktif_bank if str(x.get("Kode_Soal", "")).strip()]
                label_cakupan = "seluruh bank"
                st.warning(f"Ini menonaktifkan SEMUA {len(dipilih)} soal aktif di bank.")
                kata = st.text_input("Ketik SEMUA untuk melanjutkan:", key="bersih_kata")
                if kata.strip().upper() != "SEMUA":
                    dipilih = []
            yakin = st.checkbox(f"Saya yakin menonaktifkan {len(dipilih)} soal ({label_cakupan}).", key="bersih_yakin")
            if st.button("🚫 Nonaktifkan", disabled=not (dipilih and yakin), key="bersih_tombol"):
                try:
                    n = ubah_status_soal_bank(dipilih, "Nonaktif")
                    st.success(f"{n} soal dinonaktifkan.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Gagal: {exc}")
        else:
            try:
                nonaktif = [r for r in baca_bank_soal_semua() if str(r.get("Status", "")).strip().casefold() == "nonaktif"]
            except Exception as exc:
                nonaktif = []
                st.error(f"Gagal membaca bank: {exc}")
            if not nonaktif:
                st.caption("Tidak ada soal nonaktif.")
            else:
                peta = {str(x.get("Kode_Soal", "")): x for x in nonaktif}
                dipilih = st.multiselect(
                    "Pilih soal nonaktif:", list(peta), key="bersih_pilih_non",
                    format_func=lambda c: f"{c} | {pisah_wacana(peta[c].get('Teks_Soal', ''))[1][:60]}")
                c1, c2 = st.columns(2)
                if c1.button("♻️ Pulihkan", disabled=not dipilih, key="bersih_pulih"):
                    n = ubah_status_soal_bank(dipilih, "Aktif")
                    st.success(f"{n} soal dipulihkan.")
                    st.rerun()
                yakin_h = st.checkbox("Saya yakin menghapus PERMANEN soal terpilih (tidak bisa dipulihkan).", key="bersih_yakin_hapus")
                if c2.button("🗑️ Hapus permanen", disabled=not (dipilih and yakin_h), key="bersih_hapus"):
                    n = hapus_soal_bank_nonaktif(dipilih)
                    st.success(f"{n} soal dihapus.")
                    st.rerun()


def baca_jawaban_tergabung(ws, segarkan=False):
    """Gabungkan baris per-soal menjadi format internal yang dipakai tampilan siswa/tutor."""
    rows = baca_records_aman(ws, refresh=segarkan)
    grouped = {}
    for r in rows:
        task_id = str(r.get("ID_Penugasan", "")).strip()
        student_id = str(r.get("ID_Siswa", "")).strip()
        if not task_id or not student_id:
            continue
        key = (task_id, student_id)
        item = grouped.setdefault(key, {"ID_Jawaban": r.get("ID_Jawaban", ""), "ID_Tugas": task_id, "ID_Siswa": student_id, "Jawaban": {}, "Status": r.get("Status_Jawaban", "Draft"), "Waktu_Kirim": r.get("Waktu_Dikumpulkan", "")})
        nomor = str(r.get("Nomor_Soal", "")).strip()
        if nomor:
            item["Jawaban"][nomor] = r.get("Jawaban", "")
        status = str(r.get("Status_Jawaban", "Draft"))
        if status.lower() == "sudah dinilai":
            item["Status"] = "Sudah Dinilai"
        elif "menunggu" in status.lower() or "dikirim" in status.lower():
            if item["Status"] != "Sudah Dinilai":
                item["Status"] = "Dikirim - Menunggu Penilaian"
        item["Waktu_Kirim"] = r.get("Waktu_Dikumpulkan", "") or item["Waktu_Kirim"]
    result = []
    try:
        siswa_rows = baca_records_aman(get_worksheet("Data_Siswa"))
        names = {str(x.get("ID_Siswa", "")).strip(): x.get("Nama_Lengkap", "") for x in siswa_rows}
    except Exception:
        names = {}
    for item in grouped.values():
        item["Nama_Siswa"] = names.get(item["ID_Siswa"], item["ID_Siswa"])
        item["Jawaban_JSON"] = json.dumps(item["Jawaban"], ensure_ascii=False)
        result.append(item)
    return result



BATAS_SEL_SHEETS = 45000  # batas aman satu sel Google Sheets (50.000 karakter)
INTERVAL_PENYEGARAN_TUTOR = 45  # detik; mengurangi pembacaan berulang Google Sheets


def tugas_milik_tutor(t, tutor_id, tutor_nama=""):
    """Akses tugas hanya diberikan jika ID_Tutor cocok; nama bukan bukti kepemilikan."""
    pemilik_id = str((t or {}).get("ID_Tutor", "")).strip()
    tid = str(tutor_id or "").strip()
    return bool(tid and pemilik_id and pemilik_id == tid)


def ambil_jawaban_menunggu_milik(tutor_id, tutor_nama, segarkan=False, daftar_tugas=None):
    """Jawaban menunggu pemeriksaan; gunakan snapshot tugas bila sudah tersedia."""
    sumber_tugas = daftar_tugas if daftar_tugas is not None else get_student_tasks()
    tugas = {str(t.get("ID_Tugas", "")).strip(): t for t in sumber_tugas}
    hasil = []
    for j in baca_jawaban_tergabung(get_answers_worksheet(), segarkan=segarkan):
        if "menunggu" not in str(j.get("Status", "")).casefold():
            continue
        tg = tugas.get(str(j.get("ID_Tugas", "")).strip())
        if not tg or not tugas_milik_tutor(tg, tutor_id, tutor_nama):
            continue
        id_siswa = str(j.get("ID_Siswa", "")).strip()
        nama = str(j.get("Nama_Siswa", "")).strip()
        if not nama or nama == id_siswa:
            nama = str(tg.get("Nama_Siswa", "")).strip() or id_siswa
        x = dict(j)
        x.update({
            "Nama_Tampil": nama,
            "Judul": str(tg.get("Judul_Tugas", "")).strip() or str(j.get("ID_Tugas", "")),
            "Mapel": str(tg.get("Mapel", "")).strip(),
            "Kategori": "PR" if adalah_pr(tg) else "Tugas sesi",
        })
        hasil.append(x)
    hasil.sort(key=lambda x: str(x.get("Waktu_Kirim", "")), reverse=True)
    return hasil


def tampilkan_daftar_pemeriksaan(tutor_id, tutor_nama, interval_detik=INTERVAL_PENYEGARAN_TUTOR):
    """Daftar jawaban yang perlu diperiksa: nama jelas, tombol Periksa, dan penyegaran otomatis."""
    def _isi():
        try:
            semua_tugas = get_student_tasks()
            tugas_milik = [t for t in semua_tugas if tugas_milik_tutor(t, tutor_id)]
            # Tampilan polling memakai cache bersama; pembacaan paksa tiap fragment
            # menyebabkan lonjakan Read requests saat beberapa tutor aktif bersamaan.
            lepas_semua_sesi_kedaluwarsa(tugas_milik, segarkan=False)
            daftar = ambil_jawaban_menunggu_milik(
                tutor_id, tutor_nama, segarkan=False, daftar_tugas=semua_tugas
            )
        except Exception as exc:
            pesan = str(exc).lower()
            if "429" in pesan or "quota exceeded" in pesan or "resource_exhausted" in pesan:
                st.warning("Google Sheets sedang membatasi pembacaan. Data daftar pemeriksaan belum diperbarui; coba Muat ulang beberapa saat lagi.")
            else:
                st.error(f"Daftar pemeriksaan belum dapat dibaca: {exc.__class__.__name__}")
            return
        kiri, kanan = st.columns([4, 1])
        kiri.markdown(f"**📥 {len(daftar)} jawaban menunggu pemeriksaan**")
        if kanan.button("🔄 Muat ulang", key="periksa_muat_ulang"):
            _baca_values_cache.clear()
            st.rerun()
        if not daftar:
            st.info("Tidak ada jawaban yang menunggu pemeriksaan.")
            return
        kata = st.text_input("Cari nama siswa atau tugas:", key="periksa_cari").strip().casefold()
        tampil = [x for x in daftar if not kata or kata in f"{x['Nama_Tampil']} {x['Judul']} {x['Mapel']}".casefold()]
        peta_pelanggaran = hitung_pelanggaran_fokus() if tampil else {}
        if not tampil:
            st.caption("Tidak ada yang cocok dengan pencarian.")
        for x in tampil[:30]:
            id_tugas = str(x.get("ID_Tugas", "")).strip()
            id_siswa = str(x.get("ID_Siswa", "")).strip()
            teks, tombol = st.columns([4, 1])
            teks.markdown(f"**{x['Nama_Tampil']}** · {x['Kategori']} {x['Mapel']} — {x['Judul']}")
            _jml_p = peta_pelanggaran.get((id_tugas, id_siswa), 0)
            teks.caption(
                f"Dikirim: {x.get('Waktu_Kirim') or '-'}"
                + (f" · 🚨 Keluar tab {teks_pelanggaran(_jml_p)}" if _jml_p else " · Keluar tab 0 kali")
            )
            if tombol.button("Periksa", key=f"periksa_{id_tugas}_{id_siswa}"):
                st.session_state["_periksa_terpilih"] = f"{id_tugas}|{id_siswa}"
                _baca_values_cache.clear()
                st.rerun()
        if len(tampil) > 30:
            st.caption(f"Menampilkan 30 dari {len(tampil)}. Gunakan pencarian untuk mempersempit.")

    if hasattr(st, "fragment"):
        try:
            st.fragment(run_every=f"{int(interval_detik)}s")(_isi)()
            return
        except TypeError:
            pass  # versi Streamlit tanpa run_every: tombol Muat ulang tetap tersedia
    _isi()


def _panggil_sheets_dengan_retry_429(func, *args, **kwargs):
    """Ulangi hanya respons kuota 429 dengan jeda bertahap; jangan ulangi error jaringan ambigu."""
    jeda = (1, 2, 4)
    for percobaan in range(len(jeda) + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            pesan = str(exc).lower()
            status = getattr(getattr(exc, "response", None), "status_code", None)
            is_429 = status == 429 or "429" in pesan or "quota exceeded" in pesan or "resource_exhausted" in pesan
            if not is_429 or percobaan >= len(jeda):
                raise
            time.sleep(jeda[percobaan])


def _tampung_jawaban_draft(task_id, student_id, answers):
    """Callback widget hanya menampung perubahan; tidak memanggil Google Sheets."""
    task_id = str(task_id)
    student_id = str(student_id)
    pending_all = st.session_state.setdefault("_draft_pending_by_task", {})
    pending = pending_all.setdefault(task_id, {})
    for nomor, nilai in (answers or {}).items():
        pending[str(nomor)] = nilai
    st.session_state.setdefault("_draft_student_by_task", {})[task_id] = student_id
    st.session_state.setdefault("_draft_status_by_task", {})[task_id] = "Menunggu penyimpanan"
    st.session_state.setdefault("_draft_changed_at_by_task", {})[task_id] = time.time()
    st.session_state.pop("_galat_simpan", None)


def _flush_draft_task(task_id, student_id, paksa=False):
    """Kirim seluruh jawaban tertunda dalam satu operasi batch per jenis perubahan."""
    task_id = str(task_id)
    student_id = str(student_id)
    pending_all = st.session_state.setdefault("_draft_pending_by_task", {})
    pending = pending_all.get(task_id, {})
    if not pending:
        return True, "Tidak ada perubahan yang menunggu."

    # Snapshot agar perubahan baru yang masuk tidak terhapus setelah proses simpan.
    snapshot = dict(pending)
    try:
        ok = simpan_jawaban_per_soal(task_id, student_id, snapshot, submitted=False)
        if not ok:
            return False, "Tugas sudah terkunci atau tidak dapat diperbarui."
        pending_now = pending_all.get(task_id, {})
        for nomor, nilai in snapshot.items():
            if nomor in pending_now and pending_now[nomor] == nilai:
                pending_now.pop(nomor, None)
        if not pending_now:
            pending_all.pop(task_id, None)
        st.session_state.setdefault("_draft_status_by_task", {})[task_id] = "Tersimpan"
        st.session_state.setdefault("_draft_saved_at_by_task", {})[task_id] = time.time()
        st.session_state.pop("_galat_simpan", None)
        return True, "Draft berhasil disimpan."
    except Exception as exc:
        st.session_state.setdefault("_draft_status_by_task", {})[task_id] = "Gagal menyimpan"
        st.session_state["_galat_simpan"] = exc.__class__.__name__
        return False, f"Gagal menyimpan ({exc.__class__.__name__}). Periksa koneksi dan coba lagi."


if hasattr(st, "fragment"):
    @st.fragment(run_every="25s")
    def _autosave_semua_draft_fragment(student_id):
        """Satu pemantau autosave untuk seluruh tugas, tetap aktif saat siswa berpindah menu."""
        pending_all = st.session_state.get("_draft_pending_by_task", {})
        student_map = st.session_state.get("_draft_student_by_task", {})
        changed_map = st.session_state.get("_draft_changed_at_by_task", {})
        for task_key, pending in list(pending_all.items()):
            if not pending:
                continue
            owner_id = str(student_map.get(task_key, student_id))
            if owner_id != str(student_id):
                continue
            changed_at = changed_map.get(task_key, 0)
            if changed_at and (time.time() - float(changed_at) >= 25):
                _flush_draft_task(task_key, student_id)
        pending_count = sum(len(v) for v in st.session_state.get("_draft_pending_by_task", {}).values())
        if pending_count:
            st.caption(f"⏳ {pending_count} perubahan jawaban menunggu penyimpanan batch.")
else:
    def _autosave_semua_draft_fragment(student_id):
        st.caption("Autosave berkala tidak tersedia pada versi Streamlit ini. Simpan draft secara manual sebelum berpindah menu.")


def _otorisasi_simpan_jawaban(task_id, student_id):
    """Pastikan pasangan tugas-siswa sah untuk sesi siswa atau tutor pemilik tugas."""
    try:
        tugas_rows = baca_records_aman(get_worksheet("Tugas_Sesi_Siswa_v2"), refresh=True)
    except gspread.WorksheetNotFound:
        tugas_rows = get_student_tasks()

    tugas = next((r for r in tugas_rows
                  if str(r.get("ID_Tugas", "")).strip() == str(task_id or "").strip()), None)
    if not tugas:
        raise ValueError("Data tugas tidak ditemukan. Jawaban tidak disimpan.")

    sid = str(student_id or "").strip()
    sid_tugas = str(tugas.get("ID_Siswa", "")).strip()
    if not sid_tugas or sid != sid_tugas:
        raise ValueError("ID siswa tidak cocok dengan pemilik tugas. Jawaban tidak disimpan.")

    # Jika konteks login tutor aktif, hanya tutor pemilik tugas yang boleh
    # menginput hasil offline atas nama siswa.
    if st.session_state.get("tutor_logged_in"):
        tutor_id = str(st.session_state.get("tutor_id", "")).strip()
        tutor_nama = str(st.session_state.get("tutor_nama", "")).strip()
        if not tutor_id or not tugas_milik_tutor(tugas, tutor_id, tutor_nama):
            raise ValueError("Tutor tidak memiliki akses ke tugas ini. Jawaban tidak disimpan.")
        return tugas

    sid_sesi = str(st.session_state.get("siswa_id", "")).strip()
    if not st.session_state.get("siswa_logged_in") or not sid_sesi or sid != sid_sesi:
        raise ValueError("Sesi akun siswa tidak cocok. Jawaban tidak disimpan.")
    return tugas


def simpan_jawaban_per_soal(task_id, student_id, answers, submitted=False, _otorisasi_sudah=False):
    """Simpan jawaban dengan indeks baris sesi; satu pembacaan awal, lalu update langsung."""
    # Otorisasi identitas dan kepemilikan wajib berlaku untuk draft maupun submit.
    # Jalur submit boleh meneruskan hasil validasi server yang baru saja dilakukan.
    if not _otorisasi_sudah:
        _otorisasi_simpan_jawaban(task_id, student_id)
    # Validasi waktu hanya untuk draft di sini; submit siswa sudah divalidasi
    # oleh simpan_pengiriman_jawaban sebelum masuk ke fungsi ini.
    if not submitted:
        validasi_waktu_pengiriman(task_id, student_id)
    ws = get_answers_worksheet()
    cache_key = "_indeks_baris_jawaban_siswa"
    locked_key = "_tugas_jawaban_terkunci"
    if cache_key not in st.session_state:
        rows = baca_records_aman(ws)
        index = {}
        locked = set()
        for row in rows:
            key = (
                str(row.get("ID_Penugasan", "")).strip(),
                str(row.get("ID_Siswa", "")).strip(),
                str(row.get("Nomor_Soal", "")).strip()
            )
            if all(key):
                index[key] = int(row.get("_baris", 0) or 0)
            status_row = str(row.get("Status_Jawaban", "")).strip().lower()
            if key[0] and key[1] and (
                "dikirim" in status_row or "menunggu" in status_row or "dinilai" in status_row
            ):
                locked.add((key[0], key[1]))
        st.session_state[cache_key] = index
        st.session_state[locked_key] = locked

    index = st.session_state[cache_key]
    locked = st.session_state.get(locked_key, set())
    pair = (str(task_id), str(student_id))
    if pair in locked:
        return False

    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    status = "Dikirim - Menunggu Penilaian" if submitted else "Draft"
    updates, new_rows, new_keys = [], [], []
    for nomor, jawaban in answers.items():
        nomor = str(nomor)
        if jawaban is None:
            jawaban = ""
        teks = json.dumps(jawaban, ensure_ascii=False) if isinstance(jawaban, (list, dict)) else str(jawaban)
        values = [teks, status, now, now if submitted else ""]
        key = (str(task_id), str(student_id), nomor)
        row_number = index.get(key)
        if row_number:
            updates.append({"range": f"E{row_number}:H{row_number}", "values": [values]})
        else:
            new_rows.append([
                "JWB-" + uuid.uuid4().hex[:10].upper(),
                str(task_id), str(student_id), nomor
            ] + values)
            new_keys.append(key)

    if updates:
        _panggil_sheets_dengan_retry_429(ws.batch_update, updates, value_input_option="RAW")
    if new_rows:
        try:
            response = _panggil_sheets_dengan_retry_429(ws.append_rows, new_rows, value_input_option="RAW")
        except Exception:
            # Hindari append ganda jika respons jaringan gagal setelah Google mungkin menerima penulisan.
            st.session_state.pop(cache_key, None)
            st.session_state.pop(locked_key, None)
            _baca_values_cache.clear()
            raise
        updated_range = ((response or {}).get("updates") or {}).get("updatedRange", "")
        match = re.search(r"![A-Z]+(\d+):", updated_range)
        if match:
            first_row = int(match.group(1))
            for offset, key in enumerate(new_keys):
                index[key] = first_row + offset
        else:
            fresh_rows = baca_records_aman(ws, refresh=True)
            for row in fresh_rows:
                key = (
                    str(row.get("ID_Penugasan", "")).strip(),
                    str(row.get("ID_Siswa", "")).strip(),
                    str(row.get("Nomor_Soal", "")).strip()
                )
                if key in new_keys:
                    index[key] = int(row.get("_baris", 0) or 0)

    if submitted:
        locked.add(pair)
        st.session_state[locked_key] = locked
        _baca_values_cache.clear()
    else:
        st.session_state["_draft_saved_for_task"] = str(task_id)
        st.session_state.pop("_galat_simpan", None)
    return True


def simpan_pengiriman_jawaban(task_id, student_id, answers, lewati_validasi_waktu=False):
    # Validasi waktu siswa sekaligus memverifikasi identitas dan kepemilikan tugas.
    # Jalur tutor offline memakai pemeriksaan kepemilikan terpisah.
    if lewati_validasi_waktu:
        if not st.session_state.get("tutor_logged_in"):
            raise ValueError("Hanya Tutor yang berwenang melewati validasi timer.")
        _otorisasi_simpan_jawaban(task_id, student_id)
    else:
        validasi_waktu_pengiriman(task_id, student_id)
    return simpan_jawaban_per_soal(
        task_id, student_id, answers, submitted=True, _otorisasi_sudah=True
    )


def jawaban_kosong(v):
    if v is None:
        return True
    if isinstance(v, (list, tuple)):
        return len(v) == 0
    if isinstance(v, dict):
        return not any(str(x).strip() for x in v.values())
    return not str(v).strip()


def _nilai_normalisasi(v):
    """Normalisasi jawaban untuk pencocokan kunci tanpa membedakan kapital/spasi."""
    if isinstance(v, str):
        return re.sub(r"\s+", " ", v.strip()).casefold()
    return v


def _nilai_parse_jawaban(v):
    """Pulihkan list/dict yang disimpan sebagai JSON string di Google Sheets."""
    if isinstance(v, str):
        teks = v.strip()
        if teks.startswith(("[", "{")):
            try:
                return json.loads(teks)
            except (ValueError, TypeError):
                return v
    return v




# =========================================================
# TAHAP 7.38 — VALIDASI TIMER ONLINE & TENGGAT TANGGAL/JAM
# Catatan: penghitungan mundur server-side dan riwayat percobaan masih tahap berikutnya.
#
# # TAHAP 7.36 — MODUL 8 RANCANGAN PENGEMBANGAN
# Kartu soal, validasi, rubrik essay, persetujuan nilai,
# pratinjau, draft persisten, template, laporan, dan pemulihan form aktif.
# =========================================================

TEMPLATE_SOAL_HEADERS = [
    "ID_Template", "Nama_Template", "Tutor", "Mapel",
    "Konfigurasi_JSON", "Dibuat_Pada", "Diperbarui_Pada"
]
DRAFT_TUGAS_HEADERS = [
    "ID_Draft", "ID_Siswa", "Nama_Siswa", "Tutor",
    "Payload_JSON", "Status", "Dibuat_Pada", "Diperbarui_Pada"
]
FORM_AKTIF_HEADERS = [
    "ID_Form", "ID_Siswa", "Nama_Siswa", "Tutor",
    "Payload_JSON", "Status", "Dibuat_Pada", "Diperbarui_Pada"
]
PERSETUJUAN_NILAI_HEADERS = [
    "ID_Persetujuan", "ID_Jawaban", "ID_Tugas", "ID_Siswa",
    "Nilai_Sementara", "Nilai_Akhir", "Status_Persetujuan",
    "Disetujui_Oleh", "Waktu_Persetujuan", "Catatan"
]
HASIL_OFFLINE_HEADERS = [
    "ID_Hasil", "ID_Tugas", "ID_Siswa", "Foto_Hasil_JSON",
    "Catatan_Umum", "Tutor", "Waktu_Dinilai", "Status"
]
DETAIL_NILAI_OFFLINE_HEADERS = [
    "ID_Detail", "ID_Hasil", "ID_Tugas", "ID_Siswa",
    "Mapel", "Nilai", "Catatan_Mapel", "Tutor", "Waktu_Dinilai"
]


def siapkan_sheet_hasil_offline():
    """Siapkan tabel hasil Offline tanpa menyentuh sheet penilaian lama."""
    ws_hasil = _sheet_v2("DB_Hasil_Offline", HASIL_OFFLINE_HEADERS)
    ws_detail = _sheet_v2("DB_Detail_Nilai_Offline", DETAIL_NILAI_OFFLINE_HEADERS)
    return ws_hasil, ws_detail



def _sheet_v2(nama, headers):
    """Sheet baru khusus fitur 7.36; tidak mengubah struktur sheet lama."""
    ws = get_or_create_worksheet(nama, headers, rows="3000", cols=str(max(20, len(headers))))
    header = [str(x).strip() for x in ws.row_values(1)]
    if header != headers:
        raise RuntimeError(
            f"Header worksheet {nama} tidak sesuai. Data tidak ditulis untuk mencegah kolom bergeser."
        )
    return ws


def _parse_pasangan_manual(teks):
    hasil = {}
    for bagian in str(teks or "").split("|"):
        if ":" in bagian:
            kode, isi = bagian.split(":", 1)
            if kode.strip() and isi.strip():
                hasil[kode.strip()] = isi.strip()
    return hasil


def _parse_rubrik_kata_kunci(teks):
    """
    Menerima dua format:
    1) Kata kunci | sinonim1, sinonim2 | bobot
    2) Kata kunci | sinonim (bobot)
    Satu kriteria ditulis dalam satu baris.
    """
    hasil = []
    pola_bobot_akhir = re.compile(r"^(.*?)\s*\(\s*([0-9]+(?:[.,][0-9]+)?)\s*\)\s*$")
    for nomor_baris, baris in enumerate(str(teks or "").splitlines(), 1):
        baris = baris.strip()
        if not baris:
            continue
        bagian = [x.strip() for x in baris.split("|")]
        kata = ""
        sinonim_teks = ""
        bobot_teks = ""

        if len(bagian) >= 3:
            kata, sinonim_teks, bobot_teks = bagian[0], bagian[1], bagian[2]
        elif len(bagian) == 2:
            kata, kolom_sinonim = bagian
            cocok = pola_bobot_akhir.match(kolom_sinonim)
            if not cocok:
                raise ValueError(
                    f"Baris {nomor_baris}: gunakan 'Kata kunci | sinonim (bobot)' "
                    "atau 'Kata kunci | sinonim | bobot'."
                )
            sinonim_teks, bobot_teks = cocok.group(1).strip(), cocok.group(2).strip()
        else:
            cocok = pola_bobot_akhir.match(bagian[0])
            if not cocok:
                raise ValueError(
                    f"Baris {nomor_baris}: format rubrik belum benar. "
                    "Contoh: Fotosintesis | proses fotosintesis (30)."
                )
            kata, bobot_teks = cocok.group(1).strip(), cocok.group(2).strip()
            sinonim_teks = ""

        sinonim = [x.strip() for x in sinonim_teks.split(",") if x.strip()]
        try:
            bobot = float(str(bobot_teks).replace(",", "."))
        except (ValueError, TypeError):
            raise ValueError(f"Bobot rubrik '{kata}' harus berupa angka.")
        if not kata or bobot <= 0:
            raise ValueError("Kata kunci wajib diisi dan bobot harus lebih dari nol.")
        hasil.append({"kata_kunci": kata, "alternatif": sinonim, "bobot": bobot})

    if hasil and sum(float(x["bobot"]) for x in hasil) <= 0:
        raise ValueError("Total bobot rubrik harus lebih dari nol.")
    return hasil


def hitung_nilai_essay_keyword(jawaban, rubrik):
    """Menghasilkan nilai sementara berbasis frasa/kata kunci dan alternatif."""
    teks = re.sub(r"\s+", " ", str(jawaban or "").strip().casefold())
    if not rubrik:
        return {"nilai": None, "ditemukan": [], "belum_ditemukan": [], "status": "Perlu pemeriksaan manual"}
    total = sum(max(0.0, float(x.get("bobot", 0) or 0)) for x in rubrik)
    if total <= 0:
        return {"nilai": None, "ditemukan": [], "belum_ditemukan": [], "status": "Rubrik tidak valid"}
    ditemukan, belum = [], []
    bobot_ditemukan = 0.0
    for item in rubrik:
        kandidat = [str(item.get("kata_kunci", ""))] + list(item.get("alternatif", []) or [])
        kandidat = [re.sub(r"\s+", " ", str(x).strip().casefold()) for x in kandidat if str(x).strip()]
        cocok = any(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", teks) for k in kandidat)
        if cocok:
            ditemukan.append(item.get("kata_kunci", ""))
            bobot_ditemukan += float(item.get("bobot", 0) or 0)
        else:
            belum.append(item.get("kata_kunci", ""))
    nilai = round(min(100.0, max(0.0, bobot_ditemukan / total * 100)), 2)
    return {
        "nilai": nilai, "ditemukan": ditemukan,
        "belum_ditemukan": belum, "status": "Nilai sementara"
    }


def hitung_nilai_sementara(daftar_soal, jawaban):
    """Gabungkan penilaian objektif dan estimasi Essay; bukan nilai terbit."""
    objektif = hitung_nilai_objektif(daftar_soal, jawaban)
    rincian = list(objektif.get("rincian", []))
    manual = list(objektif.get("soal_manual", []))
    total_bobot = sum(float(x.get("bobot", 1) or 1) for x in rincian)
    total_poin = sum(float(x.get("poin", 0) or 0) * float(x.get("bobot", 1) or 1) for x in rincian)
    detail_essay = []
    nomor_essay = {
        nomor for nomor, soal in enumerate(daftar_soal or [], 1)
        if any(k in str(soal.get("Bentuk_Soal", "")).casefold() for k in ("essay", "esai", "uraian", "isian"))
    }
    manual = [nomor for nomor in manual if nomor not in nomor_essay]
    # Essay/isian dinilai penuh oleh tutor (tanpa kata kunci/sinonim).
    manual = list(manual) + sorted(nomor_essay)
    skor = round(total_poin / total_bobot * 100, 2) if total_bobot > 0 else None
    return {
        "nilai_sementara": skor,
        "rincian": rincian,
        "essay": detail_essay,
        "soal_manual": sorted(set(manual)),
        "siap_disetujui": bool(daftar_soal) and not manual and skor is not None
    }


def simpan_template_soal(nama, tutor, mapel, konfigurasi):
    if not str(nama or "").strip():
        raise ValueError("Nama template wajib diisi.")
    ws = _sheet_v2("DB_Template_Lembar_Jawaban", TEMPLATE_SOAL_HEADERS)
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([
        "TPL-" + uuid.uuid4().hex[:10].upper(), str(nama).strip(),
        str(tutor), str(mapel), json.dumps(konfigurasi, ensure_ascii=False),
        now, now
    ], value_input_option="RAW")
    _baca_values_cache.clear()


def ambil_template_soal(tutor):
    try:
        ws = _sheet_v2("DB_Template_Lembar_Jawaban", TEMPLATE_SOAL_HEADERS)
        return [
            x for x in baca_records_aman(ws)
            if str(x.get("Tutor", "")).strip() in ("", str(tutor).strip())
        ]
    except gspread.WorksheetNotFound:
        return []
    except Exception:
        return []


# =========================================================
# BANK BERKAS SOAL (PDF/GAMBAR) + TEMPLATE LEMBAR JAWABAN MELEKAT
# Sheet baru DB_Bank_Berkas_Soal; sheet lama tidak diubah.
# =========================================================
BANK_BERKAS_HEADERS = [
    "ID_Berkas", "Judul", "Mapel", "Kelas_Jenjang", "Bab_Atau_Topik", "Jenis_File",
    "Lampiran_JSON", "Konfigurasi_JSON", "Jumlah_Soal", "Pemilik_Tutor", "Dibagikan",
    "Status", "Sidik_Jari", "Dibuat_Pada", "Diperbarui_Pada"
]
KELAS_BANK_OPTIONS = ["Calistung"] + [f"Kelas {i}" for i in range(1, 13)] + ["Umum"]
BATAS_KONFIGURASI_BANK = 45000  # batas aman satu sel Google Sheets (50.000 karakter)
TTL_CACHE_BANK_BERKAS = 120
_EKSTENSI_GAMBAR = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _json_aman(teks, bawaan):
    try:
        nilai = json.loads(teks) if str(teks or "").strip() else bawaan
    except (ValueError, TypeError):
        return bawaan
    return nilai if isinstance(nilai, type(bawaan)) else bawaan


def _jenis_file_bank(lampiran):
    nama = [str(f.get("name", "")).lower() for f in lampiran]
    if nama and all(n.endswith(".pdf") for n in nama):
        return "PDF"
    if nama and all(n.endswith(_EKSTENSI_GAMBAR) for n in nama):
        return "Gambar"
    return "Campuran"


def ambil_bank_berkas(tutor, paksa=False):
    """Daftar berkas aktif yang boleh dipakai tutor (milik sendiri atau dibagikan)."""
    kunci = "_nazma_bank_berkas_cache"
    cache = st.session_state.get(kunci)
    if not paksa and cache and (time.time() - cache[0]) < TTL_CACHE_BANK_BERKAS:
        data = cache[1]
    else:
        ws = _sheet_v2("DB_Bank_Berkas_Soal", BANK_BERKAS_HEADERS)
        data = baca_records_aman(ws, refresh=paksa)
        st.session_state[kunci] = (time.time(), data)
    nama = str(tutor or "").strip()
    return [
        x for x in data
        if str(x.get("Status", "")).strip() == "Aktif"
        and (str(x.get("Dibagikan", "")).strip().casefold() == "ya"
             or str(x.get("Pemilik_Tutor", "")).strip() == nama)
    ]


def simpan_berkas_ke_bank(judul, mapel, kelas, topik, lampiran, konfigurasi, tutor, dibagikan=True, jenis_file=None):
    """Simpan berkas yang sudah ada di Google Drive ke bank. Berkas yang sama diperbarui, bukan digandakan."""
    judul = str(judul or "").strip()
    if not judul:
        raise ValueError("Judul berkas di bank wajib diisi.")
    daftar = [
        {"name": str(f.get("name", "")), "mime": str(f.get("mime", "")), "url": str(f.get("url", ""))}
        for f in (lampiran or []) if f.get("url")
    ]
    if not daftar:
        raise ValueError("Berkas belum tersimpan di Google Drive, jadi belum bisa masuk bank.")
    sumber_sidik = sorted(str(f.get("sha256") or f.get("url")) for f in lampiran if f.get("url"))
    sidik = hashlib.sha256("|".join(sumber_sidik).encode("utf-8")).hexdigest()[:24]
    konfigurasi = list(konfigurasi or [])
    konfigurasi_json = json.dumps(konfigurasi, ensure_ascii=False)
    template_ok = bool(konfigurasi)
    if len(konfigurasi_json) > BATAS_KONFIGURASI_BANK:
        konfigurasi_json, template_ok = "[]", False
    ws = _sheet_v2("DB_Bank_Berkas_Soal", BANK_BERKAS_HEADERS)
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    nama_tutor = str(tutor or "").strip()
    ada = next((
        r for r in baca_records_aman(ws, refresh=True)
        if str(r.get("Pemilik_Tutor", "")).strip() == nama_tutor
        and str(r.get("Sidik_Jari", "")).strip() == sidik
        and str(r.get("Status", "")).strip() == "Aktif"
    ), None)
    jumlah_soal = len(konfigurasi) if template_ok else 0
    if ada and not template_ok:
        # Simpan ulang tanpa template tidak boleh menghapus template yang sudah ada.
        konfigurasi_json = str(ada.get("Konfigurasi_JSON", "") or "[]")
        jumlah_soal = int(ada.get("Jumlah_Soal", 0) or 0)
    data = [
        ada.get("ID_Berkas") if ada else "BRK-" + uuid.uuid4().hex[:10].upper(),
        judul, str(mapel or ""), str(kelas or ""), str(topik or "").strip(), jenis_file or _jenis_file_bank(daftar),
        json.dumps(daftar, ensure_ascii=False), konfigurasi_json, jumlah_soal,
        nama_tutor, "Ya" if dibagikan else "Tidak", "Aktif", sidik,
        ada.get("Dibuat_Pada", now) if ada else now, now
    ]
    if ada:
        ws.update(f"A{ada['_baris']}:O{ada['_baris']}", [data], value_input_option="RAW")
    else:
        tulis_baris_di_bawah(ws, data, "RAW")
    _baca_values_cache.clear()
    st.session_state.pop("_nazma_bank_berkas_cache", None)
    return {"aksi": "diperbarui" if ada else "baru", "template": template_ok, "id": data[0]}


def daftar_berkas_milik(tutor):
    """Semua berkas bank milik tutor (aktif dan nonaktif), terbaru dulu."""
    ws = _sheet_v2("DB_Bank_Berkas_Soal", BANK_BERKAS_HEADERS)
    nama = str(tutor or "").strip()
    milik = [r for r in baca_records_aman(ws, refresh=True) if str(r.get("Pemilik_Tutor", "")).strip() == nama]
    return sorted(milik, key=lambda r: str(r.get("Diperbarui_Pada", "")), reverse=True)


def perbarui_berkas_bank(id_berkas, tutor, judul, mapel, kelas, topik, dibagikan, aktif, hapus_template=False):
    """Ubah data berkas bank. Hanya pemilik yang boleh; berkas tidak pernah dihapus, hanya dinonaktifkan."""
    judul = str(judul or "").strip()
    if not judul:
        raise ValueError("Judul berkas wajib diisi.")
    ws = _sheet_v2("DB_Bank_Berkas_Soal", BANK_BERKAS_HEADERS)
    rec = next((r for r in baca_records_aman(ws, refresh=True)
                if str(r.get("ID_Berkas", "")).strip() == str(id_berkas).strip()), None)
    if not rec:
        raise ValueError("Berkas tidak ditemukan.")
    if str(rec.get("Pemilik_Tutor", "")).strip() != str(tutor or "").strip():
        raise ValueError("Hanya pemilik berkas yang dapat mengubahnya.")
    nilai = dict(rec)
    nilai.update({
        "Judul": judul, "Mapel": str(mapel or ""), "Kelas_Jenjang": str(kelas or ""),
        "Bab_Atau_Topik": str(topik or "").strip(), "Dibagikan": "Ya" if dibagikan else "Tidak",
        "Status": "Aktif" if aktif else "Nonaktif",
        "Diperbarui_Pada": waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
    })
    if hapus_template:
        nilai["Konfigurasi_JSON"], nilai["Jumlah_Soal"] = "[]", 0
    data = [nilai.get(h, "") for h in BANK_BERKAS_HEADERS]
    ws.update(f"A{rec['_baris']}:O{rec['_baris']}", [data], value_input_option="RAW")
    _baca_values_cache.clear()
    st.session_state.pop("_nazma_bank_berkas_cache", None)
    return True


def kategori_koleksi(r):
    """Kelompokkan berkas bank: link, pdf, atau gambar (campuran digolongkan ke pdf)."""
    jenis = str(r.get("Jenis_File", "")).strip().casefold()
    lampiran = _json_aman(r.get("Lampiran_JSON", ""), [])
    mime = [str(f.get("mime", "")) for f in lampiran if isinstance(f, dict)]
    if jenis == "link drive" or (mime and all(m == "text/uri-list" for m in mime)):
        return "link"
    if jenis == "gambar":
        return "gambar"
    return "pdf"


def _buka_persiapan_dengan_berkas(id_berkas):
    st.session_state["_koleksi_pakai"] = id_berkas
    st.session_state["menu_navigasi_tutor"] = "📝 Persiapan Sesi & Bank Soal"


def tampilkan_kelola_bank_berkas(tutor, kategori=None):
    if kategori is None:
        st.subheader("📚 Bank Berkas Saya")
    st.caption(
        "Berkas yang Anda simpan. Berkas yang dinonaktifkan tidak muncul saat memilih sumber soal, "
        "sedangkan tugas yang sudah dibuat tidak terpengaruh."
    )
    notice = st.session_state.pop("_bbs_notice", None)
    if notice:
        st.success(notice)
    try:
        milik = daftar_berkas_milik(tutor)
    except Exception as exc:
        st.error(f"Bank Berkas belum dapat dibaca: {exc}")
        return
    if kategori:
        milik = [r for r in milik if kategori_koleksi(r) == kategori]
    if not milik:
        st.info("Belum ada item di sini. Tambahkan lewat formulir di atas.")
        return
    peta = {}
    for r in milik:
        status = "Aktif" if str(r.get("Status", "")).strip() == "Aktif" else "Nonaktif"
        label = f"{status} | {r.get('Judul', '')} | {r.get('Mapel', '')} | {r.get('Kelas_Jenjang', '')} | {r.get('ID_Berkas', '')}"
        peta[label] = r
    pilih = st.selectbox("Pilih berkas:", list(peta.keys()), key=f"bbs_pilih_{kategori or 'semua'}")
    r = peta[pilih]
    id_berkas = str(r.get("ID_Berkas", "")).strip()
    for lb in _json_aman(r.get("Lampiran_JSON", ""), []):
        if isinstance(lb, dict) and str(lb.get("url", "")).startswith(("http://", "https://")):
            st.markdown(f"📎 [{lb.get('name', 'berkas')}]({lb['url']})")
    if str(r.get("Status", "")).strip() == "Aktif":
        st.button("➡️ Pakai untuk tugas", key=f"bbs_pakai_{id_berkas}",
                  on_click=_buka_persiapan_dengan_berkas, args=(id_berkas,))
    try:
        jumlah_template = int(r.get("Jumlah_Soal", 0) or 0)
    except (ValueError, TypeError):
        jumlah_template = 0
    st.caption(f"Template lembar jawaban: {jumlah_template} soal" if jumlah_template else "Template lembar jawaban: belum ada")
    mapel_sekarang = str(r.get("Mapel", "")).strip()
    opsi_mapel = list(MAPEL_OPTIONS)
    if mapel_sekarang and mapel_sekarang not in opsi_mapel:
        opsi_mapel = [mapel_sekarang] + opsi_mapel
    kelas_sekarang = str(r.get("Kelas_Jenjang", "")).strip()
    opsi_kelas = list(KELAS_BANK_OPTIONS)
    if kelas_sekarang and kelas_sekarang not in opsi_kelas:
        opsi_kelas = [kelas_sekarang] + opsi_kelas
    with st.form(f"bbs_form_{id_berkas}"):
        judul = st.text_input("Judul:", value=str(r.get("Judul", "")), key=f"bbs_judul_{id_berkas}")
        mapel = st.selectbox("Mapel:", opsi_mapel, index=opsi_mapel.index(mapel_sekarang) if mapel_sekarang in opsi_mapel else 0,
                             key=f"bbs_mapel_{id_berkas}")
        kelas = st.selectbox("Kelas / jenjang:", opsi_kelas, index=opsi_kelas.index(kelas_sekarang) if kelas_sekarang in opsi_kelas else 0,
                             key=f"bbs_kelas_{id_berkas}")
        topik = st.text_input("Bab / topik:", value=str(r.get("Bab_Atau_Topik", "")), key=f"bbs_topik_{id_berkas}")
        dibagikan = st.checkbox("Bagikan ke tutor lain", value=str(r.get("Dibagikan", "")).strip().casefold() == "ya",
                                key=f"bbs_bagikan_{id_berkas}")
        aktif = st.checkbox("Aktif (tampil di pilihan sumber soal)", value=str(r.get("Status", "")).strip() == "Aktif",
                            key=f"bbs_aktif_{id_berkas}")
        hapus_tpl = False
        if jumlah_template:
            hapus_tpl = st.checkbox("Hapus template lembar jawaban dari berkas ini", value=False, key=f"bbs_hapus_{id_berkas}")
        simpan = st.form_submit_button("💾 Simpan perubahan")
    if simpan:
        try:
            perbarui_berkas_bank(id_berkas, tutor, judul, mapel, kelas, topik, dibagikan, aktif, hapus_tpl)
            st.session_state["_bbs_notice"] = f"✅ Perubahan pada berkas '{judul.strip()}' tersimpan."
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            if exc.__class__.__name__ in ("RerunException", "StopException"):
                raise
            st.error(f"Perubahan belum tersimpan: {exc}")


def _kolom_identitas_koleksi(k):
    judul = st.text_input("Judul *", key=f"kol_judul_{k}")
    mapel = st.selectbox("Mapel", MAPEL_OPTIONS, key=f"kol_mapel_{k}")
    kelas = st.selectbox("Kelas / jenjang", KELAS_BANK_OPTIONS, key=f"kol_kelas_{k}")
    topik = st.text_input("Bab / topik (opsional)", key=f"kol_topik_{k}")
    bagikan = st.checkbox("Bagikan ke tutor lain", value=False, key=f"kol_bagikan_{k}")
    return judul, mapel, kelas, topik, bagikan


def _simpan_item_koleksi(tutor, judul, mapel, kelas, topik, bagikan, lampiran, jenis_file):
    hasil = simpan_berkas_ke_bank(judul, mapel, kelas, topik, lampiran, [], tutor, bagikan, jenis_file=jenis_file)
    st.session_state["_koleksi_notice"] = (
        "✅ Item koleksi " + ("diperbarui." if hasil["aksi"] == "diperbarui" else "disimpan.")
    )
    st.session_state["_koleksi_n"] = st.session_state.get("_koleksi_n", 0) + 1


def tampilkan_koleksi_soal(tutor):
    """Satu tempat untuk bahan soal: hasil konversi, link Drive, PDF, dan gambar."""
    st.header("📚 Koleksi Soal")
    st.caption("Simpan dan kelola bahan soal Anda. Untuk memakainya, tekan 'Pakai untuk tugas' pada item.")
    notice = st.session_state.pop("_koleksi_notice", None)
    if notice:
        st.success(notice)
    jenis_pilihan = {
        "🟩 Soal hasil konversi": "konversi", "☁️ Link Google Drive": "link",
        "📕 File PDF": "pdf", "🖼️ File JPG / gambar soal": "gambar",
    }
    pilih = st.radio("Pilih jenis:", list(jenis_pilihan), key="koleksi_jenis")
    jenis = jenis_pilihan[pilih]
    n = st.session_state.get("_koleksi_n", 0)
    st.markdown("---")

    if jenis == "konversi":
        with st.expander("➕ Tambah soal baru (konverter otomatis)", expanded=False):
            tampilkan_konverter_bank_soal("tutor")
        st.markdown("#### Soal di Bank Soal")
        try:
            bank = get_bank_soal()
        except Exception as exc:
            st.error(f"Bank soal belum dapat dibaca: {exc}")
            return
        if not bank:
            st.info("Bank soal masih kosong. Tambahkan soal lewat konverter di atas.")
            return
        c1, c2 = st.columns(2)
        mapel_f = c1.selectbox("Mapel:", ["Semua"] + sorted({str(x.get("Mapel", "")).strip() for x in bank if str(x.get("Mapel", "")).strip()}), key="kol_bank_mapel")
        jenjang_f = c2.selectbox("Jenjang:", ["Semua"] + sorted({str(x.get("Jenjang", "")).strip() for x in bank if str(x.get("Jenjang", "")).strip()}), key="kol_bank_jenjang")
        kata = st.text_input("Cari bab/topik atau isi soal:", key="kol_bank_kata").strip().casefold()
        tampil = [
            x for x in bank
            if (mapel_f == "Semua" or str(x.get("Mapel", "")).strip() == mapel_f)
            and (jenjang_f == "Semua" or str(x.get("Jenjang", "")).strip() == jenjang_f)
            and (not kata or kata in f"{x.get('Bab_Atau_Topik', '')} {x.get('Teks_Soal', '')}".casefold())
        ]
        st.markdown(f"**{len(tampil)} soal** sesuai filter.")
        if tampil:
            st.dataframe(pd.DataFrame([{
                "Kode": x.get("Kode_Soal", ""), "Jenjang": x.get("Jenjang", ""), "Kelas": x.get("Kelas", ""),
                "Mapel": x.get("Mapel", ""), "Bab/Topik": x.get("Bab_Atau_Topik", ""),
                "Bentuk": x.get("Bentuk_Soal", ""), "Soal": pisah_wacana(x.get("Teks_Soal", ""))[1][:90],
            } for x in tampil[:200]]), use_container_width=True, hide_index=True)
            if len(tampil) > 200:
                st.caption("Menampilkan 200 soal pertama; persempit filter untuk melihat yang lain.")
            _peta_lihat = {str(x.get("Kode_Soal", "")): x for x in tampil[:200]}
            _kode_lihat = st.selectbox("🔍 Lihat soal lengkap (rumus tampil rapi):", [""] + list(_peta_lihat),
                                       format_func=lambda c: "— pilih soal —" if not c else f"{c} | {pisah_wacana(_peta_lihat[c].get('Teks_Soal', ''))[1][:60]}",
                                       key="kol_bank_lihat")
            if _kode_lihat:
                _x = _peta_lihat[_kode_lihat]
                tampil_soal_md("•", _x.get("Teks_Soal", ""))
                for _h, _o in zip("ABCDEFGH", [o for o in str(_x.get("Opsi_Jawaban", "")).split("|") if o.strip()]):
                    st.markdown(f"{_h}. {rapikan_rumus(_o)}")
                if str(_x.get("Kunci_Jawaban", "")).strip():
                    st.markdown(f"**🔑 Kunci:** {rapikan_rumus(_x.get('Kunci_Jawaban'))}")
                if str(_x.get("Pembahasan", "")).strip():
                    st.markdown(f"**📖 Pembahasan:** {rapikan_rumus(_x.get('Pembahasan'))}")
        tampilkan_pembersih_bank(tampil)
        st.button("➡️ Buka Persiapan Sesi untuk memakai soal", key="kol_buka_persiapan",
                  on_click=lambda: st.session_state.update({"menu_navigasi_tutor": "📝 Persiapan Sesi & Bank Soal"}))
        st.caption("Di Persiapan Sesi, pilih siswa lalu sumber 'Bank Soal Bersama'.")
        return

    if jenis == "link":
        with st.expander("➕ Tambah link Google Drive / Flipbook", expanded=False):
            with st.form(f"kol_form_link_{n}", clear_on_submit=False):
                judul, mapel, kelas, topik, bagikan = _kolom_identitas_koleksi(f"link{n}")
                tautan = st.text_area("Link (satu link per baris) *", placeholder="https://...", key=f"kol_tautan_{n}")
                kirim = st.form_submit_button("💾 Simpan ke Koleksi")
            if kirim:
                daftar = [x.strip() for x in tautan.splitlines() if x.strip()]
                if not judul.strip():
                    st.error("Judul wajib diisi.")
                elif not daftar or not all(x.lower().startswith(("http://", "https://")) for x in daftar):
                    st.error("Isi minimal satu link, dan setiap link harus diawali http:// atau https://.")
                else:
                    try:
                        lampiran = [{"name": f"Link materi {no}", "mime": "text/uri-list", "url": u}
                                    for no, u in enumerate(daftar, 1)]
                        _simpan_item_koleksi(tutor, judul, mapel, kelas, topik, bagikan, lampiran, "Link Drive")
                        st.rerun()
                    except Exception as exc:
                        if exc.__class__.__name__ in ("RerunException", "StopException"):
                            raise
                        st.error(f"Belum tersimpan: {exc}")
        tampilkan_kelola_bank_berkas(tutor, kategori="link")
        return

    # PDF atau gambar
    pdf = jenis == "pdf"
    with st.expander("➕ Tambah file PDF" if pdf else "➕ Tambah gambar soal", expanded=False):
        with st.form(f"kol_form_{jenis}_{n}", clear_on_submit=False):
            judul, mapel, kelas, topik, bagikan = _kolom_identitas_koleksi(f"{jenis}{n}")
            berkas = st.file_uploader(
                "Pilih file PDF *" if pdf else "Pilih gambar (boleh beberapa) *",
                type=["pdf"] if pdf else ["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True, key=f"kol_file_{jenis}_{n}"
            )
            kirim = st.form_submit_button("💾 Unggah & simpan ke Koleksi")
        if kirim:
            if not judul.strip():
                st.error("Judul wajib diisi.")
            elif not berkas:
                st.error("Pilih minimal satu file.")
            elif sum(len(f.getvalue()) for f in berkas) > 40 * 1024 * 1024:
                st.error("Total ukuran lebih dari 40 MB. Kurangi jumlah file.")
            else:
                try:
                    lampiran = []
                    with st.spinner("Mengunggah ke Google Drive..."):
                        for f in berkas:
                            isi = f.getvalue()
                            mime = f.type or ("application/pdf" if pdf else "image/jpeg")
                            url = upload_lampiran_ke_drive(isi, f.name, mime)
                            lampiran.append({"name": f.name, "mime": mime, "url": url,
                                             "sha256": hashlib.sha256(isi).hexdigest()})
                    _simpan_item_koleksi(tutor, judul, mapel, kelas, topik, bagikan, lampiran, "PDF" if pdf else "Gambar")
                    st.rerun()
                except Exception as exc:
                    if exc.__class__.__name__ in ("RerunException", "StopException"):
                        raise
                    st.error(f"Belum tersimpan: {exc}")
    tampilkan_kelola_bank_berkas(tutor, kategori="pdf" if pdf else "gambar")


def pilih_berkas_dari_bank(k, tutor):
    """UI memilih berkas dari bank. Mengembalikan lampiran siap pakai dan template jawabannya."""
    kosong = {"files": [], "template": [], "id": "", "berkas": None}
    try:
        daftar = ambil_bank_berkas(tutor)
    except Exception as exc:
        st.error(f"Bank Berkas Soal belum dapat dibaca: {exc}")
        return kosong
    if not daftar:
        st.info(
            "Bank Berkas Soal masih kosong. Saat membuat tugas dari 'Upload dari perangkat', "
            "buka bagian 'Simpan ke Bank Berkas Soal' agar berkas dan template jawabannya bisa dipakai ulang."
        )
        return kosong
    pakai = st.session_state.pop("_koleksi_pakai_aktif", "")
    pakai_rec = next((x for x in daftar if str(x.get("ID_Berkas", "")).strip() == pakai), None) if pakai else None
    if pakai_rec:
        st.session_state[f"bb_cari_{k}"] = str(pakai_rec.get("Judul", ""))
        st.session_state[f"bb_mp_{k}"] = "Semua"
        st.session_state[f"bb_kelas_{k}"] = "Semua"
    kata = st.text_input("Cari judul berkas:", key=f"bb_cari_{k}").strip().casefold()
    mapel_opsi = ["Semua"] + sorted({str(x.get("Mapel", "")).strip() for x in daftar if str(x.get("Mapel", "")).strip()})
    kelas_opsi = ["Semua"] + sorted({str(x.get("Kelas_Jenjang", "")).strip() for x in daftar if str(x.get("Kelas_Jenjang", "")).strip()})
    mapel_f = st.selectbox("Filter mapel:", mapel_opsi, key=f"bb_mp_{k}")
    kelas_f = st.selectbox("Filter kelas:", kelas_opsi, key=f"bb_kelas_{k}")
    peta = {}
    for x in daftar:
        id_berkas = str(x.get("ID_Berkas", "")).strip()
        if not id_berkas:
            continue
        if mapel_f != "Semua" and str(x.get("Mapel", "")).strip() != mapel_f:
            continue
        if kelas_f != "Semua" and str(x.get("Kelas_Jenjang", "")).strip() != kelas_f:
            continue
        gabung = f"{x.get('Judul', '')} {x.get('Bab_Atau_Topik', '')}".casefold()
        if kata and kata not in gabung:
            continue
        peta[id_berkas] = x
    st.caption(f"{len(peta)} berkas cocok.")
    placeholder = "— Pilih berkas —"

    def _label(id_berkas):
        if id_berkas == placeholder:
            return placeholder
        b = peta[id_berkas]
        teks = f"{b.get('Judul', '')} · {b.get('Mapel', '')} · {b.get('Kelas_Jenjang', '')}"
        try:
            n_soal = int(b.get("Jumlah_Soal", 0) or 0)
        except (ValueError, TypeError):
            n_soal = 0
        return teks + (f" · template {n_soal} soal" if n_soal else " · tanpa template")

    daftar_pilihan = [placeholder] + list(peta.keys())
    pilihan = st.selectbox(
        "Pilih berkas soal:", daftar_pilihan, format_func=_label,
        index=daftar_pilihan.index(pakai) if pakai in daftar_pilihan else 0,
        key=f"bb_pilih_{k}_{mapel_f}_{kelas_f}_{kata}"
    )
    if pilihan == placeholder or pilihan not in peta:
        return kosong
    berkas = peta[pilihan]
    lampiran = _json_aman(berkas.get("Lampiran_JSON", ""), [])
    files = []
    for i, lb in enumerate(lampiran):
        if isinstance(lb, dict) and str(lb.get("url", "")).startswith(("http://", "https://")):
            files.append({
                "name": str(lb.get("name", "berkas")), "mime": str(lb.get("mime", "") or "application/octet-stream"),
                "url": str(lb["url"]), "uploaded": True, "sha256": f"bank:{pilihan}:{i}"
            })
            st.markdown(f"📎 [{lb.get('name', 'berkas')}]({lb['url']})")
    if not files:
        st.warning("Lampiran pada berkas ini tidak valid. Pilih berkas lain.")
        return kosong
    template = _json_aman(berkas.get("Konfigurasi_JSON", ""), [])
    if template:
        st.success(f"Template lembar jawaban tersedia ({len(template)} soal). Tidak perlu konfigurasi ulang.")
    else:
        st.info("Berkas ini belum punya template jawaban. Konfigurasi bisa dibuat sekali di bawah.")
    return {"files": files, "template": template, "id": pilihan, "berkas": berkas}


def form_simpan_ke_bank(k, judul_tugas, mapel_tugas):
    """Pilihan menyimpan berkas yang baru diunggah ke bank. None bila tidak dicentang."""
    with st.expander("📚 Simpan ke Bank Berkas Soal (opsional)", expanded=False):
        simpan = st.checkbox("Simpan berkas ini agar bisa dipakai ulang untuk siswa lain", key=f"bb_simpan_{k}")
        if not simpan:
            return None
        judul = st.text_input("Judul di bank:", value=str(judul_tugas or ""), key=f"bb_judul_{k}")
        kelas = st.selectbox("Kelas / jenjang:", KELAS_BANK_OPTIONS, key=f"bb_kelas_simpan_{k}")
        topik = st.text_input("Bab / topik (opsional):", key=f"bb_topik_{k}")
        dibagikan = st.checkbox("Bagikan ke tutor lain", value=True, key=f"bb_bagikan_{k}")
        st.caption(
            "Jika Anda memilih lembar jawaban online, konfigurasi jawaban ikut tersimpan sebagai template "
            "yang melekat pada berkas. Tersimpan saat tombol 'Tambahkan ke daftar tugas' ditekan."
        )
    return {"judul": judul, "mapel": mapel_tugas, "kelas": kelas, "topik": topik, "dibagikan": dibagikan}


def simpan_draft_tugas_persisten(id_siswa, nama_siswa, tutor, daftar_draft):
    """
    Menyimpan metadata draft ke sheet terpisah. Lampiran sudah diunggah ke Drive
    ketika draft dibuat; sheet hanya menyimpan URL dan metadata file, bukan byte file.
    """
    ws = _sheet_v2("DB_Draft_Tugas_Tutor", DRAFT_TUGAS_HEADERS)
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    payload = []
    for item in (daftar_draft or []):
        aman = dict(item)
        aman["Files"] = [
            {k: v for k, v in f.items() if k != "bytes"}
            for f in (item.get("Files", []) or [])
        ]
        payload.append(aman)
    teks_payload = json.dumps(payload, ensure_ascii=False)
    if len(teks_payload) > BATAS_SEL_SHEETS:
        st.warning(
            "Draft terlalu besar untuk disimpan otomatis ke spreadsheet. Draft tetap ada selama halaman ini terbuka; "
            "kirim tugasnya sebelum menutup halaman, atau kurangi jumlah soal per tugas."
        )
        return False
    records = baca_records_aman(ws, refresh=True)
    aktif = next((
        r for r in records
        if str(r.get("ID_Siswa", "")) == str(id_siswa)
        and str(r.get("Tutor", "")) == str(tutor)
        and str(r.get("Status", "")) == "Draft"
    ), None)
    data = [
        aktif.get("ID_Draft") if aktif else "DRF-" + uuid.uuid4().hex[:10].upper(),
        str(id_siswa), str(nama_siswa), str(tutor),
        teks_payload, "Draft",
        aktif.get("Dibuat_Pada", now) if aktif else now, now
    ]
    if aktif:
        ws.update(f"A{aktif['_baris']}:H{aktif['_baris']}", [data], value_input_option="RAW")
    else:
        ws.append_row(data, value_input_option="RAW")


def ambil_draft_tugas_persisten(id_siswa, tutor):
    try:
        ws = _sheet_v2("DB_Draft_Tugas_Tutor", DRAFT_TUGAS_HEADERS)
        record = next((
            r for r in reversed(baca_records_aman(ws, refresh=True))
            if str(r.get("ID_Siswa", "")) == str(id_siswa)
            and str(r.get("Tutor", "")) == str(tutor)
            and str(r.get("Status", "")) == "Draft"
        ), None)
        if not record:
            return []
        payload = json.loads(record.get("Payload_JSON", "[]") or "[]")
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def hapus_draft_tugas_persisten(id_siswa, tutor):
    try:
        ws = _sheet_v2("DB_Draft_Tugas_Tutor", DRAFT_TUGAS_HEADERS)
        for r in baca_records_aman(ws, refresh=True):
            if str(r.get("ID_Siswa", "")) == str(id_siswa) and str(r.get("Tutor", "")) == str(tutor) and str(r.get("Status", "")) == "Draft":
                ws.update_cell(r["_baris"], DRAFT_TUGAS_HEADERS.index("Status") + 1, "Dikirim")
    except Exception:
        pass


def _serialisasi_form_aman(nilai):
    """Ubah state widget menjadi struktur JSON yang aman untuk dipulihkan."""
    if isinstance(nilai, datetime):
        return {"__nazma_type__": "datetime", "value": nilai.isoformat()}
    if isinstance(nilai, date):
        return {"__nazma_type__": "date", "value": nilai.isoformat()}
    if isinstance(nilai, dict):
        return {str(k): _serialisasi_form_aman(v) for k, v in nilai.items()}
    if isinstance(nilai, (list, tuple)):
        return [_serialisasi_form_aman(v) for v in nilai]
    if nilai is None or isinstance(nilai, (str, int, float, bool)):
        return nilai
    return None


def _pulihkan_form_aman(nilai):
    if isinstance(nilai, dict):
        tipe = nilai.get("__nazma_type__")
        if tipe == "date":
            try:
                return date.fromisoformat(str(nilai.get("value", "")))
            except ValueError:
                return None
        if tipe == "datetime":
            try:
                return datetime.fromisoformat(str(nilai.get("value", "")))
            except ValueError:
                return None
        return {k: _pulihkan_form_aman(v) for k, v in nilai.items()}
    if isinstance(nilai, list):
        return [_pulihkan_form_aman(v) for v in nilai]
    return nilai


def simpan_form_aktif_persisten(id_siswa, nama_siswa, tutor, payload):
    """Simpan satu pekerjaan form aktif per tutor-siswa; draft yang sudah dibuat tetap terpisah."""
    ws = _sheet_v2("DB_Form_Tugas_Aktif", FORM_AKTIF_HEADERS)
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    payload_json = json.dumps(_serialisasi_form_aman(payload), ensure_ascii=False)
    ptr_key = f"_nazma_form_aktif_ptr_{id_siswa}_{tutor}"
    aktif = None
    ptr = st.session_state.get(ptr_key)
    if isinstance(ptr, dict) and ptr.get("baris"):
        # Cukup membaca satu baris untuk memastikan penunjuk masih benar (bukan seluruh sheet).
        try:
            baris_cek = ws.get(f"A{ptr['baris']}:F{ptr['baris']}")
            nilai_baris = baris_cek[0] if baris_cek else []
            if (len(nilai_baris) >= 6 and str(nilai_baris[0]) == str(ptr.get("ID_Form"))
                    and str(nilai_baris[5]) == "Aktif"):
                aktif = {"ID_Form": ptr["ID_Form"], "_baris": ptr["baris"],
                         "Dibuat_Pada": ptr.get("Dibuat_Pada", now)}
        except Exception:
            aktif = None
    if aktif is None:
        records = baca_records_aman(ws, refresh=True)
        aktif = next((
            r for r in reversed(records)
            if str(r.get("ID_Siswa", "")) == str(id_siswa)
            and str(r.get("Tutor", "")) == str(tutor)
            and str(r.get("Status", "")) == "Aktif"
        ), None)
    data = [
        aktif.get("ID_Form") if aktif else "FRM-" + uuid.uuid4().hex[:10].upper(),
        str(id_siswa), str(nama_siswa), str(tutor), payload_json, "Aktif",
        aktif.get("Dibuat_Pada", now) if aktif else now, now
    ]
    if aktif:
        ws.update(f"A{aktif['_baris']}:H{aktif['_baris']}", [data], value_input_option="RAW")
        st.session_state[ptr_key] = {"ID_Form": data[0], "baris": int(aktif["_baris"]),
                                     "Dibuat_Pada": data[6]}
    else:
        hasil_tambah = ws.append_row(data, value_input_option="RAW")
        try:
            rentang = str((hasil_tambah or {}).get("updates", {}).get("updatedRange", ""))
            cocok_baris = re.search(r"!A(\d+):", rentang)
            if cocok_baris:
                st.session_state[ptr_key] = {"ID_Form": data[0], "baris": int(cocok_baris.group(1)),
                                             "Dibuat_Pada": data[6]}
        except Exception:
            pass
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def ambil_form_aktif_persisten(id_siswa, tutor):
    ws = _sheet_v2("DB_Form_Tugas_Aktif", FORM_AKTIF_HEADERS)
    record = next((
        r for r in reversed(baca_records_aman(ws, refresh=True))
        if str(r.get("ID_Siswa", "")) == str(id_siswa)
        and str(r.get("Tutor", "")) == str(tutor)
        and str(r.get("Status", "")) == "Aktif"
    ), None)
    if not record:
        return None
    payload = json.loads(record.get("Payload_JSON", "{}") or "{}")
    if not isinstance(payload, dict):
        return None
    return {
        "ID_Form": record.get("ID_Form", ""),
        "Diperbarui_Pada": record.get("Diperbarui_Pada", ""),
        "payload": _pulihkan_form_aman(payload)
    }


def ubah_status_form_aktif(id_siswa, tutor, status):
    st.session_state.pop(f"_nazma_form_aktif_ptr_{id_siswa}_{tutor}", None)
    ws = _sheet_v2("DB_Form_Tugas_Aktif", FORM_AKTIF_HEADERS)
    for record in baca_records_aman(ws, refresh=True):
        if (str(record.get("ID_Siswa", "")) == str(id_siswa)
            and str(record.get("Tutor", "")) == str(tutor)
            and str(record.get("Status", "")) == "Aktif"):
            ws.update_cell(record["_baris"], FORM_AKTIF_HEADERS.index("Status") + 1, str(status))


def _kunci_autosave_form(id_siswa, tutor):
    return "_nazma_form_autosave_" + hashlib.sha1(
        f"{id_siswa}|{tutor}".encode("utf-8")
    ).hexdigest()[:16]


# Nilai tombol (mis. "Salin konfigurasi nomor N") tidak boleh disimpan atau dipulihkan:
# Streamlit melarang penulisan nilai tombol lewat session_state.
KUNCI_TOMBOL_TIDAK_DISIMPAN = ("_salin_",)
JEDA_AUTOSAVE_DETIK = 15


def _kunci_tombol(nama):
    return any(m in str(nama) for m in KUNCI_TOMBOL_TIDAK_DISIMPAN)


def _ambil_widget_state_form(k):
    """Ambil state kontrol form yang perlu dipulihkan; file uploader disimpan terpisah."""
    prefix_tepat = (
        f"kt_{k}", f"mp_{k}", f"jd_{k}", f"sm_{k}", f"lk_{k}",
        f"mode_{k}", f"jumlah_manual_{k}", f"_template_awal_{k}",
        f"in_{k}", f"tm_{k}_", f"tg_{k}_", f"template_pilih_{k}",
        f"template_nama_{k}", f"ps_{k}_", f"fj_{k}", f"fk_{k}",
        f"fm_{k}", f"ft_{k}", f"fb_{k}",
        f"bb_cari_{k}", f"bb_mp_{k}", f"bb_kelas_{k}", f"bb_pilih_{k}_", f"ubah_cfg_{k}",
        f"unggah_oleh_{k}"
    )
    prefix_awalan = f"cfg_{k}_"
    hasil = {}
    for key, value in list(st.session_state.items()):
        nama = str(key)
        if _kunci_tombol(nama):
            continue
        if nama.startswith(prefix_awalan) or any(
            nama == p or (p.endswith("_") and nama.startswith(p))
            for p in prefix_tepat
        ):
            if nama.startswith(f"up_{k}"):
                continue
            aman = _serialisasi_form_aman(value)
            if aman is not None:
                hasil[nama] = aman
    return hasil


def _hapus_lampiran_autosave(k):
    st.session_state.pop(f"_autosave_files_{k}", None)
    st.session_state.pop(f"up_{k}", None)


def catat_persetujuan_nilai(id_jawaban, id_tugas, id_siswa, nilai_sementara,
                            nilai_akhir, tutor, catatan):
    ws = _sheet_v2("DB_Persetujuan_Nilai", PERSETUJUAN_NILAI_HEADERS)
    sudah_ada = next((
        r for r in baca_records_aman(ws)
        if str(r.get("ID_Jawaban", "")).strip() == str(id_jawaban).strip()
        and str(r.get("Status_Persetujuan", "")).strip().lower() == "disetujui dan diterbitkan"
    ), None)
    if sudah_ada:
        return False
    ws.append_row([
        "APR-" + uuid.uuid4().hex[:10].upper(), str(id_jawaban),
        str(id_tugas), str(id_siswa),
        "" if nilai_sementara is None else nilai_sementara,
        nilai_akhir, "Disetujui dan diterbitkan", str(tutor),
        waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"), str(catatan or "")
    ], value_input_option="RAW")
    _baca_values_cache.clear()
    return True


def validasi_konfigurasi_soal(soal):
    """Validasi struktur soal sebelum masuk draft tugas."""
    masalah = []
    bentuk = str(soal.get("Bentuk_Soal", "")).casefold()
    opsi = soal.get("Opsi_List", []) or []
    kunci = soal.get("Kunci", "")
    if any(x in bentuk for x in ("pilihan ganda", "pgk kategori", "pgk mcma")) and len(opsi) < 2:
        masalah.append("minimal dua opsi diperlukan")
    if "pilihan ganda" in bentuk and "kompleks" not in bentuk and "mcma" not in bentuk:
        if not str(kunci).strip():
            masalah.append("kunci jawaban belum diisi")
        elif str(kunci).strip() not in opsi:
            masalah.append("kunci harus sama dengan salah satu opsi")
    elif "pgk mcma" in bentuk or "pilihan ganda kompleks" in bentuk:
        daftar_kunci = kunci if isinstance(kunci, list) else [x.strip() for x in str(kunci).split("|") if x.strip()]
        if not daftar_kunci or any(x not in opsi for x in daftar_kunci):
            masalah.append("kunci PG kompleks harus dipilih dari opsi yang tersedia")
    elif "pgk kategori" in bentuk:
        if not str(kunci).strip() or str(kunci).strip() not in opsi:
            masalah.append("kunci kategori harus dipilih dari opsi")
    elif "benar" in bentuk:
        if str(kunci).strip().casefold() not in ("benar", "salah"):
            masalah.append("kunci Benar-Salah harus Benar atau Salah")
    elif "menjodohkan" in bentuk:
        pasangan = soal.get("Pasangan", {}) or {}
        kiri = pasangan.get("kolom_A", {}) or {}
        kanan = pasangan.get("kolom_B", {}) or {}
        kunci_p = kunci.get("pasangan", {}) if isinstance(kunci, dict) else {}
        if not kiri or not kanan or not kunci_p:
            masalah.append("Kolom A, Kolom B, dan kunci pasangan wajib lengkap")
        elif set(kunci_p.keys()) - set(kiri.keys()) or set(kunci_p.values()) - set(kanan.keys()):
            masalah.append("kode kunci pasangan harus cocok dengan Kolom A dan Kolom B")
    try:
        if float(soal.get("Bobot", 1) or 0) <= 0:
            masalah.append("bobot soal harus lebih dari nol")
    except (ValueError, TypeError):
        masalah.append("bobot soal harus berupa angka")
    return masalah


def buat_konfigurasi_kartu_soal(jumlah, key_prefix, konfigurasi_awal=None):
    """UI kartu per nomor; lebih nyaman untuk layar HP daripada tabel lebar."""
    konfigurasi_awal = konfigurasi_awal or []
    hasil = []
    tipe_opsi = [
        "Pilihan ganda", "Pilihan ganda kompleks", "Benar-Salah",
        "PGK Kategori", "PGK MCMA", "Essay", "Menjodohkan"
    ]
    for nomor in range(1, int(jumlah) + 1):
        awal = konfigurasi_awal[nomor - 1] if nomor <= len(konfigurasi_awal) else {}
        tipe_awal = str(awal.get("Bentuk_Soal", "Pilihan ganda"))
        if tipe_awal not in tipe_opsi:
            tipe_awal = "Pilihan ganda"
        with st.expander(f"Nomor {nomor} · {tipe_awal}", expanded=(nomor == 1)):
            if nomor > 1 and st.button(
                f"Salin konfigurasi nomor {nomor-1}",
                key=f"{key_prefix}_salin_{nomor}"
            ):
                for suffix in ("tipe", "bobot", "opsi", "kunci", "rubrik", "a", "b", "kp"):
                    key_lama = f"{key_prefix}_{suffix}_{nomor-1}"
                    key_baru = f"{key_prefix}_{suffix}_{nomor}"
                    if key_lama in st.session_state:
                        st.session_state[key_baru] = st.session_state[key_lama]
                st.rerun()
            tipe = st.selectbox(
                "Tipe jawaban",
                tipe_opsi,
                index=tipe_opsi.index(tipe_awal),
                key=f"{key_prefix}_tipe_{nomor}"
            )
            bobot = st.number_input(
                "Bobot nilai", min_value=0.1, max_value=100.0, step=0.5,
                value=float(awal.get("Bobot", 1) or 1),
                key=f"{key_prefix}_bobot_{nomor}"
            )
            opsi = []
            pasangan = {}
            rubrik = []
            kunci = ""
            if tipe in ("Pilihan ganda", "Pilihan ganda kompleks", "PGK Kategori", "PGK MCMA"):
                opsi_default = " | ".join(awal.get("Opsi_List", []) or ["A", "B", "C", "D"])
                opsi_teks = st.text_input(
                    "Opsi jawaban (pisahkan dengan |)",
                    value=opsi_default,
                    key=f"{key_prefix}_opsi_{nomor}"
                )
                opsi = [x.strip() for x in opsi_teks.split("|") if x.strip()]
                if tipe in ("Pilihan ganda kompleks", "PGK MCMA"):
                    kunci_teks = st.text_input(
                        "Kunci jawaban (pisahkan dengan |)",
                        value=" | ".join(awal.get("Kunci", []) if isinstance(awal.get("Kunci"), list) else ([awal.get("Kunci", "")] if awal.get("Kunci") else [])),
                        key=f"{key_prefix}_kunci_{nomor}"
                    )
                    kunci = [x.strip() for x in kunci_teks.split("|") if x.strip()]
                else:
                    kunci_awal = str(awal.get("Kunci", "") or "")
                    kunci = st.selectbox(
                        "Kunci jawaban",
                        [""] + opsi,
                        index=([""] + opsi).index(kunci_awal) if kunci_awal in opsi else 0,
                        key=f"{key_prefix}_kunci_{nomor}"
                    )
            elif tipe == "Benar-Salah":
                kunci_awal = str(awal.get("Kunci", "Benar") or "Benar")
                kunci = st.radio(
                    "Kunci jawaban", ["Benar", "Salah"],
                    index=0 if kunci_awal.casefold() == "benar" else 1,
                    horizontal=True, key=f"{key_prefix}_kunci_{nomor}"
                )
                opsi = ["Benar", "Salah"]
            elif tipe == "Essay":
                st.caption("Essay dinilai langsung oleh tutor saat pemeriksaan (tanpa kata kunci).")
                rubrik = []
                kunci = ""
            elif tipe == "Menjodohkan":
                a_awal = awal.get("Pasangan", {}).get("kolom_A", {})
                b_awal = awal.get("Pasangan", {}).get("kolom_B", {})
                kp_awal = (awal.get("Kunci", {}) or {}).get("pasangan", {}) if isinstance(awal.get("Kunci", {}), dict) else {}
                def _pasangan_ke_teks(data):
                    return "\n".join(f"{k}:{v}" for k, v in (data or {}).items())
                col_a = st.text_area(
                    "Kolom A (satu baris kode:teks)",
                    value=_pasangan_ke_teks(a_awal), key=f"{key_prefix}_a_{nomor}", height=90
                )
                col_b = st.text_area(
                    "Kolom B (satu baris kode:teks)",
                    value=_pasangan_ke_teks(b_awal), key=f"{key_prefix}_b_{nomor}", height=90
                )
                key_pair = st.text_input(
                    "Kunci pasangan (format A:X|B:Y)",
                    value="|".join(f"{k}:{v}" for k, v in kp_awal.items()),
                    key=f"{key_prefix}_kp_{nomor}"
                )
                def _parse_baris_pasangan(teks):
                    out = {}
                    for row in str(teks or "").splitlines():
                        if ":" in row:
                            k, v = row.split(":", 1)
                            if k.strip() and v.strip():
                                out[k.strip()] = v.strip()
                    return out
                pasangan = {
                    "kolom_A": _parse_baris_pasangan(col_a),
                    "kolom_B": _parse_baris_pasangan(col_b)
                }
                kunci = {"pasangan": _parse_pasangan_manual(key_pair)}
            soal = {
                "Teks_Soal": "", "Bentuk_Soal": tipe, "Opsi_List": opsi,
                "Pasangan": pasangan, "Kunci": kunci,
                "Rubrik_Kata_Kunci": rubrik, "Bobot": float(bobot)
            }
            masalah = validasi_konfigurasi_soal(soal)
            if masalah:
                st.caption("Belum lengkap: " + "; ".join(masalah))
            else:
                st.caption("Konfigurasi nomor ini valid.")
            hasil.append(soal)
    return hasil


def tampilkan_pratinjau_lembar_jawaban(daftar_soal, judul="Pratinjau lembar jawaban siswa"):
    with st.expander("👁️ " + judul, expanded=False):
        if not daftar_soal:
            st.info("Belum ada konfigurasi soal.")
            return
        _st_w = {}
        for nomor, soal in enumerate(daftar_soal, 1):
            bentuk = str(soal.get("Bentuk_Soal", "")).casefold()
            opsi = soal.get("Opsi_List", []) or []
            tampil_soal_md(nomor, soal.get("Teks_Soal"), _st_w, "Jawab berdasarkan soal pada lampiran.")
            if "benar" in bentuk:
                st.caption("Pilihan siswa: ○ Benar   ○ Salah")
            elif "pgk mcma" in bentuk or "pilihan ganda kompleks" in bentuk:
                st.caption("Pilihan siswa (boleh lebih dari satu): " + " · ".join(f"□ {x}" for x in opsi))
            elif "pgk kategori" in bentuk or "pilihan ganda" in bentuk:
                st.caption("Pilihan siswa: " + " · ".join(f"○ {x}" for x in opsi))
            elif "menjodohkan" in bentuk:
                pasangan = soal.get("Pasangan", {}) or {}
                kiri = pasangan.get("kolom_A", {}) or {}
                kanan = pasangan.get("kolom_B", {}) or {}
                st.caption("Kolom A: " + " · ".join(f"{k}. {v}" for k, v in kiri.items()))
                st.caption("Kolom B: " + " · ".join(f"{k}. {v}" for k, v in kanan.items()))
                st.caption("Siswa memilih pasangan untuk setiap item.")
            else:
                st.caption("Kolom jawaban uraian / Essay.")
            st.divider()


# =========================================================
# FITUR BARU (disisipkan): tampilan soal yang diberikan ke siswa, untuk tutor.
# Dipakai di Portofolio siswa dan saat memeriksa/menilai jawaban.
# Hanya membaca data tugas; tidak menulis apa pun ke Google Sheets.
# =========================================================
def _isi_soal_tugas_tutor(tugas, tampil_kunci=True):
    """Isi tampilan soal/lampiran tugas untuk tutor. Tanpa expander, aman dipakai di dalam expander."""
    if not tugas:
        st.info("Data tugas tidak ditemukan, sehingga soal tidak dapat ditampilkan.")
        return
    try:
        daftar_soal, _mode_json = buka_soal_dan_mode(tugas.get("Soal_JSON", ""), tugas.get("Jenis_Tugas", ""))
        timer_txt = str(tugas.get("Timer_Menit", "") or "").strip()
        st.caption(
            f"Mapel: {tugas.get('Mapel', '-')} · Sumber: {tugas.get('Sumber', '-') or '-'} · "
            f"Mode: {mode_tugas(tugas)} · Diberikan: {tugas.get('Tanggal', '-')} · "
            f"Timer: {'Tanpa timer' if timer_txt in ('', '0') else timer_txt + ' menit'}"
        )
        if str(tugas.get("Instruksi", "") or "").strip():
            st.write(f"**Instruksi:** {tugas.get('Instruksi')}")

        lampiran = parse_lampiran(tugas.get("File_Offline", ""))
        if lampiran:
            st.markdown("**📎 Soal / lampiran yang diberikan ke siswa:**")
            for no, (jenis, url) in enumerate(lampiran, 1):
                if jenis == "img":
                    st.image(img_url(url), caption=f"Halaman {no}", use_container_width=True)
                elif jenis == "video":
                    st.video(media_direct_url(url))
                elif jenis == "audio":
                    st.audio(media_direct_url(url))
                else:
                    fid = drive_id(url)
                    if fid:
                        components.iframe(f"https://drive.google.com/file/d/{fid}/preview", height=480, scrolling=True)
                st.markdown(f"[↗ Buka lampiran {no} ({jenis})]({url})")

        if daftar_soal:
            st.markdown(f"**📝 Soal pada lembar jawaban ({len(daftar_soal)} butir):**")
            _st_w = {}
            for i, soal in enumerate(daftar_soal, 1):
                if not isinstance(soal, dict):
                    continue
                teks = str(soal.get("Teks_Soal", "") or "").strip()
                if teks:
                    tampil_soal_md(i, teks, _st_w)
                else:
                    st.markdown(f"**{i}.** _(teks soal ada pada lampiran di atas)_")
                if str(soal.get("Url_Gambar", "") or "").strip():
                    st.image(img_url(soal["Url_Gambar"]), use_container_width=True)
                for ikon, kolom in (("🎧 Audio", "Url_Audio"), ("🎬 Video", "Url_Video"), ("📖 Bacaan", "Url_Bacaan")):
                    u = str(soal.get(kolom, "") or "").strip()
                    if u.startswith(("https://", "http://")):
                        st.markdown(f"[{ikon} soal {i}]({u})")
                bentuk = str(soal.get("Bentuk_Soal", "") or "")
                if bentuk:
                    st.caption(f"Bentuk: {bentuk} · Bobot: {soal.get('Bobot', 1)}")
                opsi = soal.get("Opsi_List", []) or []
                if isinstance(opsi, list) and opsi:
                    st.caption("Pilihan: " + " · ".join(str(x) for x in opsi))
                pasangan = soal.get("Pasangan", {}) or {}
                if isinstance(pasangan, dict) and pasangan:
                    kiri = pasangan.get("kolom_A", {}) or {}
                    kanan = pasangan.get("kolom_B", {}) or {}
                    st.caption("Kolom A: " + " · ".join(f"{k}. {v}" for k, v in kiri.items()))
                    st.caption("Kolom B: " + " · ".join(f"{k}. {v}" for k, v in kanan.items()))
                if tampil_kunci:
                    kunci = str(soal.get("Kunci", "") or "").strip()
                    if kunci:
                        st.caption(f"🔑 Kunci (hanya terlihat tutor): {kunci}")
        if not lampiran and not daftar_soal:
            st.caption("Tugas ini tidak memiliki soal atau lampiran yang tersimpan.")
    except Exception as exc:
        st.warning(f"Soal tugas belum dapat ditampilkan: {exc.__class__.__name__}")


def tampilkan_soal_tugas_untuk_tutor(tugas, expanded=True, judul="📘 Soal yang diberikan pada tugas ini"):
    """Expander soal untuk satu tugas; dipakai saat tutor memeriksa dan menilai jawaban."""
    with st.expander(judul, expanded=expanded):
        _isi_soal_tugas_tutor(tugas)


def _tampilkan_jawaban_per_soal(tugas, jawaban_dict):
    """Tampilkan per soal: soal, jawaban siswa, kunci dan pembahasan (khusus tutor)."""
    try:
        daftar, _m = buka_soal_dan_mode(tugas.get("Soal_JSON", ""), tugas.get("Jenis_Tugas", ""))
    except Exception:
        daftar = []
    if not daftar:
        if jawaban_dict:
            st.json(jawaban_dict)
        else:
            st.caption("Tidak ada jawaban ketik; lihat lampiran jawaban siswa.")
        return
    hasil = hitung_nilai_objektif(daftar, jawaban_dict or {})
    poin = {x["nomor"]: x["poin"] for x in hasil.get("rincian", [])}
    for i, soal in enumerate(daftar, 1):
        if not isinstance(soal, dict):
            continue
        jw = (jawaban_dict or {}).get(str(i), "")
        if isinstance(jw, (list, dict)):
            jw = json.dumps(jw, ensure_ascii=False)
        tanda = ""
        if i in poin:
            tanda = " ✅" if poin[i] >= 0.999 else (" 🟡" if poin[i] > 0 else " ❌")
        _w, _isi = pisah_wacana(soal.get("Teks_Soal", ""))
        teks = rapikan_rumus(_isi) or "(soal ada pada lampiran)"
        with st.expander(f"No. {i} · {soal.get('Bentuk_Soal', '')}{tanda}", expanded=False):
            if _w:
                st.info("📖 " + rapikan_rumus(_w))
            st.markdown(f"**Soal:** {teks}")
            st.markdown(f"**Jawaban siswa:** {rapikan_rumus(jw) if str(jw).strip() else '_(kosong)_'}")
            kunci = soal.get("Kunci", soal.get("Kunci_Jawaban", ""))
            if isinstance(kunci, (list, dict)):
                kunci = json.dumps(kunci, ensure_ascii=False)
            if str(kunci).strip():
                st.markdown(f"**🔑 Kunci:** {rapikan_rumus(kunci)}")
            if str(soal.get("Pembahasan", "") or "").strip():
                st.markdown(f"**📖 Pembahasan:** {rapikan_rumus(soal.get('Pembahasan'))}")


def tampilkan_pilih_soal_portofolio(nama_siswa, daftar_tugas):
    """Di Portofolio: pilih satu tugas siswa lalu lihat soal yang pernah diberikan."""
    tugas_ada = [t for t in (daftar_tugas or []) if str(t.get("ID_Tugas", "")).strip()]
    if not tugas_ada:
        return
    opsi = {}
    for t in reversed(tugas_ada):  # terbaru di atas
        label = (
            f"{str(t.get('Tanggal', ''))[:10]} | {t.get('Mapel', '')} - "
            f"{t.get('Judul_Tugas', '') or t.get('Instruksi', '')} | {t.get('ID_Tugas', '')}"
        )
        opsi[label] = t
    with st.expander(f"📘 Soal yang diberikan ke {nama_siswa}", expanded=False):
        pilih = st.selectbox(
            "Pilih tugas untuk melihat soalnya:", ["— Pilih tugas —"] + list(opsi.keys()),
            key=f"pilih_soal_portofolio_{nama_siswa}"
        )
        if pilih != "— Pilih tugas —":
            tugas_p = opsi[pilih]
            try:
                _jawab = next((x for x in baca_jawaban_tergabung(get_answers_worksheet(), segarkan=True)
                               if x.get("ID_Tugas") == str(tugas_p.get("ID_Tugas", "")).strip()
                               and x.get("ID_Siswa") == str(tugas_p.get("ID_Siswa", "")).strip()), None)
            except Exception:
                _jawab = None
            if _jawab and isinstance(_jawab.get("Jawaban"), dict) and _jawab.get("Jawaban"):
                st.markdown("#### ✅ Jawaban siswa, benar/salah, kunci & pembahasan")
                _tampilkan_jawaban_per_soal(tugas_p, _jawab["Jawaban"])
                with st.expander("Lihat daftar soal tanpa jawaban siswa", expanded=False):
                    _isi_soal_tugas_tutor(tugas_p)
            else:
                st.caption("Siswa belum mengirim jawaban online untuk tugas ini, jadi hanya soal yang tampil.")
                _isi_soal_tugas_tutor(tugas_p)


# =========================================================
# FITUR BARU (disisipkan): konverter soal otomatis untuk Bank_Soal_Master.
# Menerima teks soal biasa (Word/WhatsApp/ChatGPT) atau baris tabel yang disalin
# dari spreadsheet lain, lalu menyusunnya sesuai header Bank_Soal_Master.
# Kunci jawaban otomatis diubah dari huruf (B) menjadi teks pilihan, karena
# penilaian otomatis mencocokkan teks pilihan siswa dengan kolom Kunci_Jawaban.
# =========================================================
_BANK_RE_NOMOR = re.compile(r"^\s*(\d{1,3})\s*[.)]\s+(.*)$")
_BANK_RE_OPSI = re.compile(r"^\s*\(?([A-Ha-h])[.)]\s+(.*)$")
_BANK_RE_KUNCI = re.compile(r"^\s*(?:kunci(?:\s+jawaban)?|jawaban(?:\s+benar)?|answer|key)\s*[:=]\s*(.*)$", re.I)
_BANK_RE_BAHAS = re.compile(r"^\s*(?:pembahasan|penjelasan|explanation)\s*[:=]\s*(.*)$", re.I)
_BANK_RE_BENTUK = re.compile(r"^\s*(?:tipe|bentuk|jenis)(?:\s+soal)?\s*[:=]\s*(.*)$", re.I)
_BANK_RE_LABEL = re.compile(r"^\s*\(?[A-Ha-h][.)]\s+")

_BANK_ALIAS_BENTUK = {
    "pilihan ganda": "Pilihan ganda", "pg": "Pilihan ganda", "pilgan": "Pilihan ganda",
    "multiple choice": "Pilihan ganda", "mcq": "Pilihan ganda",
    "pilihan ganda kompleks": "PGK MCMA", "pgk": "PGK MCMA", "pgk mcma": "PGK MCMA", "mcma": "PGK MCMA",
    "pgk kategori": "PGK Kategori",
    "benar salah": "Benar-Salah", "benar-salah": "Benar-Salah", "b/s": "Benar-Salah",
    "bs": "Benar-Salah", "true false": "Benar-Salah", "true/false": "Benar-Salah",
    "essay": "Essay", "esai": "Essay", "uraian": "Essay", "isian": "Essay",
    "isian singkat": "Essay", "jawaban singkat": "Essay",
    "menjodohkan": "Menjodohkan",
}
_BANK_ALIAS_KOLOM = {
    "teks": ["teks soal", "soal", "pertanyaan", "teks", "question", "butir soal", "teks_soal"],
    "opsi": ["opsi jawaban", "opsi", "pilihan", "pilihan jawaban", "options", "opsi_jawaban"],
    "kunci": ["kunci jawaban", "kunci", "jawaban benar", "jawaban", "answer", "key", "kunci_jawaban"],
    "bentuk": ["bentuk soal", "bentuk", "tipe", "tipe soal", "jenis soal", "jenis", "bentuk_soal"],
    "pembahasan": ["pembahasan", "penjelasan", "explanation"],
    "mapel": ["mapel", "mata pelajaran", "pelajaran", "subject"],
    "jenjang": ["jenjang", "tingkat", "level"],
    "kelas": ["kelas", "class", "grade"],
    "topik": ["bab atau topik", "bab_atau_topik", "bab", "topik", "materi", "topic"],
    "url_gambar": ["url gambar", "url_gambar", "gambar", "link gambar"],
    "url_audio": ["url audio", "url_audio", "audio", "link audio"],
    "url_video": ["url video", "url_video", "video", "link video"],
    "url_bacaan": ["url bacaan", "url_bacaan", "bacaan", "link bacaan"],
    "bobot": ["bobot", "skor", "poin"],
}


_WACANA_BUKA, _WACANA_TUTUP = "[[WACANA]]", "[[/WACANA]]"
_RE_RUMUS_KURUNG = re.compile(r"\(([^()$]*\\[A-Za-z]+[^()$]*)\)")
_RE_RUMUS_PERLU = re.compile(r"\\(?:leq?|geq?|neq?|times|div|cdot|pm|frac|sqrt|pi|alpha|beta|theta|sum|infty|approx|rightarrow|to|angle|degree|circ|log|sin|cos|tan)\b")


def rapikan_rumus(teks):
    """Ubah rumus mentah (x+y\\leq 8), \\(..\\), \\[..\\] menjadi $..$ agar tampil sebagai matematika."""
    t = str(teks or "")
    if not t or "\\" not in t:
        return t
    t = re.sub(r"\\\[(.+?)\\\]", lambda m: "$$" + m.group(1).strip() + "$$", t, flags=re.S)
    t = re.sub(r"\\\((.+?)\\\)", lambda m: "$" + m.group(1).strip() + "$", t, flags=re.S)
    sebelum = None
    while sebelum != t:  # tangani rumus bertingkat kurung satu tingkat demi satu
        sebelum = t
        t = _RE_RUMUS_KURUNG.sub(lambda m: "$" + m.group(1).strip() + "$", t)
    return t


def gabung_wacana(wacana, teks):
    w = str(wacana or "").strip()
    return f"{_WACANA_BUKA}{w}{_WACANA_TUTUP}\n{teks}" if w else str(teks or "")


def pisah_wacana(teks):
    """Kembalikan (wacana, teks_soal). Wacana disimpan di depan Teks_Soal dengan penanda."""
    t = str(teks or "")
    if t.startswith(_WACANA_BUKA) and _WACANA_TUTUP in t:
        w, _, sisa = t[len(_WACANA_BUKA):].partition(_WACANA_TUTUP)
        return w.strip(), sisa.strip()
    return "", t.strip()


def tampil_soal_md(nomor, teks, state=None, kosong=""):
    """Tampilkan nomor + teks soal; wacana muncul sekali di atas kelompok soalnya."""
    w, isi = pisah_wacana(teks)
    if w and (state is None or state.get("w") != w):
        st.info("📖 " + rapikan_rumus(w))
        if state is not None:
            state["w"] = w
    isi = rapikan_rumus(isi) or kosong
    st.markdown(f"**{nomor}. {isi}**")


def _bank_hapus_label(teks):
    return _BANK_RE_LABEL.sub("", str(teks or "")).strip()


def bank_parse_teks_soal(teks):
    """Ubah teks soal biasa menjadi daftar soal mentah. Satu soal diawali nomor (1. / 1))."""
    teks = str(teks or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not teks:
        return []
    baris_all = teks.split("\n")
    if any(_BANK_RE_NOMOR.match(b) for b in baris_all):
        ada_opsi_global = any(_BANK_RE_OPSI.match(b) for b in baris_all)
        blok, nomor_blok, sekarang, pembuka, terakhir = [], [], None, [], 0
        for b in baris_all:
            cocok = _BANK_RE_NOMOR.match(b)
            mulai_baru = bool(cocok) and (sekarang is None or not _BANK_RE_OPSI.match(b))
            if mulai_baru and sekarang is not None and ada_opsi_global:
                n = int(cocok.group(1))
                selesai = any(_BANK_RE_KUNCI.match(x) or _BANK_RE_BAHAS.match(x) for x in sekarang) \
                    or sum(1 for x in sekarang if _BANK_RE_OPSI.match(x)) >= 2
                baris_terakhir = next((x for x in reversed(sekarang) if x.strip()), "")
                if selesai:
                    mulai_baru = n > terakhir
                else:  # langkah bernomor di dalam teks bacaan bukan soal baru
                    mulai_baru = n == terakhir + 1 and not _BANK_RE_NOMOR.match(baris_terakhir)
            if mulai_baru:
                sekarang = [cocok.group(2)]
                blok.append(sekarang)
                nomor_blok.append(int(cocok.group(1)))
                terakhir = int(cocok.group(1))
            elif sekarang is not None:
                sekarang.append(b)
            else:
                pembuka.append(b)
        teks_pembuka = " ".join(x.strip() for x in pembuka if x.strip())
        # Teks sebelum nomor 1 hanya dipertahankan bila berupa bacaan/tabel pernyataan; judul lembar dibuang.
        if teks_pembuka and (len(teks_pembuka) >= 120 or _BANK_KATA_WACANA.match(teks_pembuka)
                             or re.search(r"pernyataan.*\bbenar\b.*\bsalah\b", teks_pembuka, re.I)):
            blok.insert(0, pembuka)
            nomor_blok.insert(0, None)
        pasangan_blok = [(x, n) for x, n in zip(blok, nomor_blok) if any(str(y).strip() for y in x)]
    else:
        potongan = re.split(r"\n\s*\n\s*\n|\n\s*-{3,}\s*\n", teks)
        pasangan_blok = [(p.split("\n"), None) for p in potongan if p.strip()]

    hasil = []
    for baris_blok, nomor_asli in pasangan_blok:
        majemuk = _bank_parse_bs_majemuk(baris_blok)
        if majemuk:
            hasil.extend(majemuk)
            continue
        item = {"teks": "", "opsi": [], "kunci": "", "bentuk": "", "pembahasan": "", "no": nomor_asli}
        mode, kosong_dulu = "teks", False
        for b in baris_blok:
            if not b.strip():
                kosong_dulu = True
                continue
            m_kunci, m_bahas, m_bentuk, m_opsi = (
                _BANK_RE_KUNCI.match(b), _BANK_RE_BAHAS.match(b), _BANK_RE_BENTUK.match(b), _BANK_RE_OPSI.match(b)
            )
            if m_kunci:
                item["kunci"], mode = m_kunci.group(1).strip(), "kunci"
            elif m_bahas:
                item["pembahasan"], mode = m_bahas.group(1).strip(), "bahas"
            elif m_bentuk:
                item["bentuk"], mode = m_bentuk.group(1).strip(), "bentuk"
            elif m_opsi:
                item["opsi"].append(m_opsi.group(2).strip())
                mode = "opsi"
            elif mode in ("opsi", "kunci", "bahas") and (kosong_dulu or item.get("wacana_lanjut")) and len(b.strip()) > 60:
                item["wacana_lanjut"] = (item.get("wacana_lanjut", "") + "\n" + b.strip()).strip()
            elif mode == "opsi" and item["opsi"]:
                item["opsi"][-1] = (item["opsi"][-1] + " " + b.strip()).strip()
            elif mode == "kunci":
                item["kunci"] = (item["kunci"] + " " + b.strip()).strip()
            elif mode == "bahas":
                item["pembahasan"] = (item["pembahasan"] + " " + b.strip()).strip()
            else:
                pemisah = "\n\n" if kosong_dulu else "\n"
                item["teks"] = (item["teks"] + pemisah + b.strip()).strip() if item["teks"] else b.strip()
            kosong_dulu = False
        _bank_pisah_bacaan_dari_pertanyaan(item)
        hasil.append(item)
    return _bank_kelompokkan_wacana(hasil)


_BANK_KATA_BACA = re.compile(r"^\s*(?:read|baca|bacalah|simak|simaklah|perhatikan|look|study)\b", re.I)


def _bank_pisah_bacaan_dari_pertanyaan(item):
    """Teks bertingkat (instruksi, bacaan, pertanyaan) -> bacaan dipisah dari pertanyaan terakhir."""
    if not item["opsi"] or item.get("wacana"):
        return
    paragraf = [x.strip() for x in item["teks"].split("\n\n") if x.strip()]
    if len(paragraf) >= 3 and (_BANK_KATA_BACA.match(paragraf[0]) or len("\n\n".join(paragraf[:-1])) >= 150):
        item["wacana"] = "\n\n".join(paragraf[:-1])
        item["teks"] = paragraf[-1]


_BANK_RE_KUNCI_MULAI = re.compile(r"^\W*(?:kunci|jawaban|answer|key)\b", re.I)
_BANK_RE_PERNYATAAN_PER = re.compile(r"^\W*pernyataan\s*(?:no\.?\s*)?(\d+)\s*[:=\-]\s*(.*)$", re.I)


def _bank_parse_bs_majemuk(baris):
    """Satu blok berisi beberapa pernyataan Benar/Salah (tabel 'No | Pernyataan | Benar | Salah') ->
    beberapa soal Benar-Salah yang berbagi bacaan. Mengembalikan [] bila bukan format ini."""
    L = [re.sub(r"\s+", " ", str(x).replace("\t", " ")).strip() for x in baris]
    L = [x for x in L if x]
    idx_head = next((i for i, x in enumerate(L)
                     if re.search(r"pernyataan", x, re.I) and re.search(r"\bbenar\b", x, re.I) and re.search(r"\bsalah\b", x, re.I)
                     and len(x) < 60), None)
    if idx_head is None:
        return []
    sebelum = L[:idx_head]
    instruksi = [x for x in sebelum if re.search(r"(benar|salah)", x, re.I) and re.search(r"tentukan|nyatakan|tulis|pilih", x, re.I)]
    wacana = [x for x in sebelum if x not in instruksi and not re.match(r"^pertanyaan\s*:?$", x, re.I)]
    pernyataan, kunci_map, bahas_map, ada_kunci, n_aktif = [], {}, {}, False, None
    for x in L[idx_head + 1:]:
        if ada_kunci:
            m = _BANK_RE_PERNYATAAN_PER.match(x)
            if m:
                n_aktif = int(m.group(1))
                kunci_map[n_aktif] = m.group(2).split(".")[0].split(",")[0].strip()
                bahas_map[n_aktif] = []
                sisa = ".".join(m.group(2).split(".")[1:]).strip()
                if sisa:
                    bahas_map[n_aktif].append(sisa)
            elif n_aktif is not None:
                bahas_map[n_aktif].append(re.sub(r"^[\u2022\u25E6\-\*•◦]\s*", "", x))
            continue
        if _BANK_RE_KUNCI_MULAI.match(x) and not re.match(r"^\d", x):
            ada_kunci = True
            continue
        bersih = re.sub(r"(\s*\[\s*\])+\s*$", "", x)
        kunci_sisip = ""
        m_bar = re.match(r"^(.*?)\s*\|\s*(benar|salah|b|s|true|false)\s*$", bersih, re.I)
        if m_bar:
            bersih, kunci_sisip = m_bar.group(1), m_bar.group(2)
        m = re.match(r"^\(?([0-9]{1,2}|[A-Za-z])[.)]?\s+(.+)$", bersih)
        if m:
            pernyataan.append((m.group(1), m.group(2).strip(), kunci_sisip))
    if len(pernyataan) < 2:
        return []
    teks_wacana = "\n\n".join(wacana)
    hasil = []
    for urut, (no, teks_p, kunci_sisip) in enumerate(pernyataan, 1):
        kunci = kunci_sisip or kunci_map.get(int(no) if no.isdigit() else urut, "")
        pemb = " ".join(bahas_map.get(int(no) if no.isdigit() else urut, []))
        hasil.append({"teks": "Benar atau Salah: " + teks_p, "opsi": ["Benar", "Salah"], "kunci": kunci,
                      "bentuk": "Benar-Salah", "pembahasan": pemb, "wacana": teks_wacana, "no": None})
    return hasil


_BANK_KATA_WACANA = re.compile(r"^\s*(?:wacana|bacaan|stimulus|teks\s+bacaan|bacalah|simaklah|perhatikan\s+teks)\b", re.I)


def _bank_apakah_wacana(item, berikutnya):
    """Blok tanpa pilihan/kunci yang diikuti soal berpilihan dianggap teks bacaan, bukan soal."""
    if item["opsi"] or item["kunci"] or item["pembahasan"] or item["bentuk"]:
        return False
    if not berikutnya or not berikutnya["opsi"]:
        return False
    t = item["teks"].strip()
    return bool(_BANK_KATA_WACANA.match(t)) or (len(t) >= 120 and not t.endswith("?"))


def _bank_kelompokkan_wacana(hasil):
    """Pindahkan teks bacaan menjadi lampiran soal (kunci 'wacana'), tidak lagi dihitung sebagai nomor soal."""
    keluar, aktif = [], ""
    for idx, item in enumerate(hasil):
        berikut = hasil[idx + 1] if idx + 1 < len(hasil) else None
        if _bank_apakah_wacana(item, berikut):
            aktif = _BANK_KATA_WACANA.sub("", item["teks"], count=1).lstrip(" :.\n") if re.match(r"^\s*(?:wacana|bacaan|stimulus|teks\s+bacaan)\b", item["teks"], re.I) else item["teks"]
            continue
        sisa = item.pop("wacana_lanjut", "")
        if item.get("wacana"):
            aktif = ""
        elif aktif and item["opsi"]:
            item["wacana"] = aktif
        keluar.append(item)
        if sisa:
            aktif = sisa  # teks bacaan yang ditulis setelah pilihan terakhir milik kelompok berikutnya
    # "Based on the text in number 7" / "pada nomor 21": pakai bacaan milik nomor yang dirujuk
    peta_w = {it["no"]: it["wacana"] for it in keluar if it.get("no") and it.get("wacana")}
    for it in keluar:
        if not it.get("wacana") and it["opsi"]:
            m = re.search(r"(?:number|no\.?|nomor)\s*(\d{1,3})", it["teks"], re.I)
            if m and int(m.group(1)) in peta_w:
                it["wacana"] = peta_w[int(m.group(1))]
    return keluar


def _bank_cocokkan_kolom(nama_kolom):
    kunci = re.sub(r"\s+", " ", str(nama_kolom or "").strip().casefold().replace("_", " "))
    for baku, alias in _BANK_ALIAS_KOLOM.items():
        if kunci in [a.replace("_", " ") for a in alias]:
            return baku
    cocok = re.match(r"^(?:opsi|pilihan|jawaban)?\s*([a-h])$", kunci)
    if cocok:
        return "opsi_" + cocok.group(1)
    return ""


def bank_parse_tabel(teks):
    """Baca baris tabel yang disalin dari spreadsheet (tab / koma / titik koma) dengan baris judul kolom."""
    import csv
    import io
    teks = str(teks or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not teks:
        return [], []
    baris_pertama = teks.split("\n", 1)[0]
    pemisah = "\t" if "\t" in baris_pertama else (";" if baris_pertama.count(";") > baris_pertama.count(",") else ",")
    baris = [r for r in csv.reader(io.StringIO(teks), delimiter=pemisah) if any(str(c).strip() for c in r)]
    if len(baris) < 2:
        return [], ["Tabel minimal berisi baris judul kolom dan satu baris soal."]
    peta = [_bank_cocokkan_kolom(c) for c in baris[0]]
    masalah = []
    if "teks" not in peta:
        masalah.append("Kolom soal tidak ditemukan. Beri judul kolom 'Soal', 'Pertanyaan', atau 'Teks_Soal'.")
        return [], masalah
    hasil = []
    for r in baris[1:]:
        item = {"teks": "", "opsi": [], "kunci": "", "bentuk": "", "pembahasan": ""}
        opsi_huruf = {}
        for idx, sel in enumerate(r):
            kolom = peta[idx] if idx < len(peta) else ""
            sel = str(sel or "").strip()
            if not kolom or not sel:
                continue
            if kolom.startswith("opsi_"):
                opsi_huruf[kolom[-1]] = sel
            elif kolom == "opsi":
                bagian = re.split(r"\s*\|\s*|\n|;", sel)
                item["opsi"] = [x.strip() for x in bagian if x.strip()]
            else:
                item[kolom] = sel
        if opsi_huruf and not item["opsi"]:
            item["opsi"] = [opsi_huruf[h] for h in sorted(opsi_huruf)]
        hasil.append(item)
    return hasil, masalah


def _bank_sidik_soal(teks, opsi, bentuk):
    """Soal dianggap sama hanya bila teks, SEMUA pilihan (urutan sama), dan bentuknya sama persis.
    Angka yang berbeda pada teks atau pilihan membuat soal dianggap berbeda."""
    rapat = lambda x: re.sub(r"\s+", " ", str(x or "")).strip().casefold()
    return (rapat(teks), rapat(opsi), rapat(bentuk))


def _paket_norm(x):
    return re.sub(r"\s+", " ", str(x or "")).strip().casefold()


def _soal_aktif(baris):
    return str(baris.get("Status", "")).strip().casefold() not in ("nonaktif", "tidak aktif", "arsip")


def daftar_paket_bank():
    """Nama paket (Bab/topik) dari soal aktif di bank, tanpa duplikat, urut abjad."""
    try:
        baris = baca_records_aman(get_worksheet("Bank_Soal_Master"))
    except Exception:
        return []
    peta = {}
    for x in baris:
        nama = re.sub(r"\s+", " ", str(x.get("Bab_Atau_Topik", "") or "")).strip()
        if nama and _soal_aktif(x):
            peta.setdefault(_paket_norm(nama), nama)
    return sorted(peta.values(), key=str.casefold)


def _bank_kunci_ke_teks(kunci_raw, opsi):
    """Ubah kunci huruf (B / A,C) menjadi teks pilihan. Mengembalikan (daftar_teks, masalah)."""
    mentah = str(kunci_raw or "").strip()
    if not mentah:
        return [], "kunci jawaban kosong"
    peta_teks = {_nilai_normalisasi(o): o for o in opsi}
    if _nilai_normalisasi(mentah) in peta_teks:
        return [peta_teks[_nilai_normalisasi(mentah)]], ""
    if re.match(r"^\(?[A-Ha-h][.)]\s+\S", mentah):
        mentah = re.match(r"^\(?([A-Ha-h])", mentah).group(1)
    # Kunci berupa isi pilihan (mis. deretan angka "0,75; 0,8; 1,2"): cocokkan utuh, jangan dipecah per koma.
    def _longgar(x):
        return re.sub(r"[\s.,;:|/<>\-–—]+", "", str(x)).casefold()
    cocok_longgar = [o for o in opsi if _longgar(o) and _longgar(o) == _longgar(mentah)]
    if len(cocok_longgar) == 1:
        return [cocok_longgar[0]], ""
    token = [t for t in re.split(r"\s*(?:[,;|&/]|\bdan\b)\s*|\s+", mentah) if t]
    hasil = []
    for t in token:
        huruf = t.strip(".)(").upper()
        if len(huruf) == 1 and huruf.isalpha() and 0 <= ord(huruf) - 65 < len(opsi):
            teks_opsi = opsi[ord(huruf) - 65]
        elif _nilai_normalisasi(t) in peta_teks:
            teks_opsi = peta_teks[_nilai_normalisasi(t)]
        else:
            return [], f"kunci '{mentah}' tidak cocok dengan pilihan yang ada"
        if teks_opsi not in hasil:
            hasil.append(teks_opsi)
    return hasil, ""


def bank_bangun_baris(raw, meta, bentuk_peta=None):
    """Susun satu soal mentah menjadi baris Bank_Soal_Master. Mengembalikan dict dengan _masalah dan _catatan."""
    bentuk_peta = bentuk_peta or {}
    masalah, catatan = [], []
    teks = rapikan_rumus(str(raw.get("teks", "") or "").strip())
    if not teks:
        masalah.append("teks soal kosong")
    wacana_raw = rapikan_rumus(str(raw.get("wacana", "") or "").strip())
    opsi = []
    for o in raw.get("opsi", []) or []:
        o = rapikan_rumus(_bank_hapus_label(o))
        if "|" in o:
            o = o.replace("|", "/")
            catatan.append("tanda | dalam pilihan diganti /")
        if o:
            opsi.append(o)

    bentuk_sebut = re.sub(r"\s+", " ", str(raw.get("bentuk", "") or "").strip().casefold())
    bentuk = _BANK_ALIAS_BENTUK.get(bentuk_sebut, "")
    if bentuk_sebut and not bentuk:
        masalah.append(f"bentuk soal '{raw.get('bentuk')}' tidak dikenali")
    kunci_teks = []
    kunci_raw = rapikan_rumus(str(raw.get("kunci", "") or "").strip())

    if bentuk == "Menjodohkan":
        masalah.append("soal menjodohkan perlu diisi manual di sheet (format JSON kolom A/B)")
    else:
        opsi_asli = list(opsi)
        sinonim_benar = {"b", "benar", "true", "t", "ya", "betul", "right", "correct", "yes", "y"}
        sinonim_salah = {"s", "salah", "false", "f", "tidak", "wrong", "incorrect", "no", "n"}
        bs_otomatis = (not bentuk) and {x.casefold() for x in opsi} == {"benar", "salah"}
        if bentuk == "Benar-Salah" or bs_otomatis:
            bentuk = "Benar-Salah"
            opsi = ["Benar", "Salah"]
            k = kunci_raw.casefold().strip(". ")
            if bs_otomatis and len(opsi_asli) == 2 and k in ("a", "b"):
                kunci_teks = [("Benar" if opsi_asli[ord(k) - 97].casefold() == "benar" else "Salah")]
            elif k in sinonim_benar:
                kunci_teks = ["Benar"]
            elif k in sinonim_salah:
                kunci_teks = ["Salah"]
            else:
                masalah.append("kunci Benar/Salah tidak jelas")
        elif opsi or bentuk in ("Pilihan ganda", "PGK MCMA", "PGK Kategori"):
            if len(opsi) < 2:
                masalah.append("soal pilihan butuh minimal 2 pilihan")
            else:
                kunci_teks, m = _bank_kunci_ke_teks(kunci_raw, opsi)
                if m:
                    masalah.append(m)
                if not bentuk:
                    bentuk = "PGK MCMA" if len(kunci_teks) > 1 else "Pilihan ganda"
                    if len(kunci_teks) > 1:
                        catatan.append("kunci lebih dari satu, dijadikan PGK MCMA")
                elif bentuk == "Pilihan ganda" and len(kunci_teks) > 1:
                    masalah.append("pilihan ganda biasa hanya boleh satu kunci")
        else:
            bentuk = "Essay"
            kunci_teks = [kunci_raw] if kunci_raw else []
            if not kunci_raw:
                catatan.append("essay tanpa kunci, dinilai manual")
    bentuk_akhir = bentuk_peta.get(bentuk.casefold(), bentuk)

    bobot = str(raw.get("bobot", "") or "").strip().replace(",", ".")
    try:
        bobot = str(float(bobot)).rstrip("0").rstrip(".") if bobot else "1"
        if float(bobot) <= 0:
            masalah.append("bobot harus lebih dari 0")
    except ValueError:
        masalah.append(f"bobot '{raw.get('bobot')}' bukan angka")
        bobot = "1"

    def _ambil(kolom, bawaan=""):
        return str(raw.get(kolom, "") or "").strip() or str(meta.get(kolom, bawaan) or "").strip()

    for kolom_url in ("url_gambar", "url_audio", "url_video", "url_bacaan"):
        u = str(raw.get(kolom_url, "") or "").strip()
        if u and not u.lower().startswith(("http://", "https://")):
            masalah.append(f"{kolom_url} harus diawali http:// atau https://")
    sep = "|"
    return {
        "Kode_Soal": "BS-" + uuid.uuid4().hex[:8].upper(),
        "Jenjang": _ambil("jenjang"), "Kelas": _ambil("kelas"), "Mapel": _ambil("mapel"),
        "Bab_Atau_Topik": _ambil("topik"),
        "Bentuk_Soal": bentuk_akhir, "Teks_Soal": gabung_wacana(wacana_raw, teks),
        "Opsi_Jawaban": sep.join(opsi) if bentuk != "Essay" else "",
        "Kunci_Jawaban": sep.join(kunci_teks),
        "Pembahasan": rapikan_rumus(str(raw.get("pembahasan", "") or "").strip()),
        "URL_Gambar": str(raw.get("url_gambar", "") or "").strip(),
        "URL_Audio": str(raw.get("url_audio", "") or "").strip(),
        "URL_Video": str(raw.get("url_video", "") or "").strip(),
        "URL_Bacaan": str(raw.get("url_bacaan", "") or "").strip(),
        "Bobot": bobot, "Status": "Aktif",
        "_masalah": masalah, "_catatan": catatan,
    }


def bank_susun_sesuai_header(headers, baris):
    """Letakkan nilai pada kolom sesuai urutan header sheet; kolom yang tidak dikenal dibiarkan kosong."""
    return [str(baris.get(h, "") if not str(h).startswith("_") else "") for h in headers]


def _tulis_baris_bank(ws_bank, baris_tulis, jumlah_kolom):
    """Tulis tepat di bawah baris terakhir yang berisi data (bukan menebak 'tabel' seperti append_rows).
    Mengembalikan (baris_awal, baris_akhir)."""
    nilai = ws_bank.get_all_values()
    awal = len(nilai) + 1
    akhir = awal + len(baris_tulis) - 1
    kolom = re.sub(r"\d+", "", gspread.utils.rowcol_to_a1(1, max(int(jumlah_kolom), 1)))
    rentang = f"A{awal}:{kolom}{akhir}"
    try:
        ws_bank.update(range_name=rentang, values=baris_tulis, value_input_option="RAW")
    except Exception as exc:
        if "grid" not in str(exc).lower():
            raise
        ws_bank.add_rows(len(baris_tulis) + 10)
        ws_bank.update(range_name=rentang, values=baris_tulis, value_input_option="RAW")
    return awal, akhir


def tampilkan_konverter_bank_soal(konteks="owner"):
    """UI konverter: tempel soal -> periksa hasil konversi -> simpan ke Bank_Soal_Master."""
    k = f"bk_{konteks}"
    st.caption(
        "Tempel soal apa adanya. Aplikasi menyusunnya sesuai kolom Bank_Soal_Master, memindahkan kunci huruf "
        "(misalnya B) menjadi teks pilihan, lalu menampilkan hasilnya untuk Anda periksa sebelum disimpan."
    )
    mode = st.radio(
        "Bentuk tempelan:", ["Teks soal biasa (Word / WhatsApp / ChatGPT)", "Baris tabel dari spreadsheet lain"],
        key=f"{k}_mode"
    )
    if mode.startswith("Teks"):
        st.code(
            "1. Ibu kota Indonesia adalah ...\nA. Bandung\nB. Jakarta\nC. Surabaya\nD. Medan\n"
            "Kunci: B\nPembahasan: Jakarta adalah ibu kota saat ini.\n\n"
            "2. Sebutkan dua contoh gaya!\nKunci: gaya dorong dan gaya tarik",
            language="text"
        )
        st.caption(
            "Satu soal diawali nomor. Pilihan A, B, C, dst. Baris 'Kunci:' dan 'Pembahasan:' opsional. "
            "Tanpa pilihan dianggap Essay. Pilihan Benar/Salah dikenali otomatis. Boleh menulis 'Bentuk: PGK' untuk "
            "kunci lebih dari satu (A, C)."
        )
    else:
        st.caption(
            "Salin baris dari Google Sheets/Excel termasuk baris judul kolom. Judul seperti Soal, Pertanyaan, Opsi, "
            "Pilihan, A/B/C/D, Kunci, Jawaban, Tipe, Mapel, Kelas dikenali otomatis."
        )
    # Isian dan tombol dibungkus form agar teks yang diketik ikut terkirim saat tombol ditekan.
    # Tanpa form, di HP ketukan pertama hanya menyimpan isian lalu halaman dimuat ulang sehingga tombol tampak tidak merespons.
    with st.form(f"{k}_form", clear_on_submit=False, enter_to_submit=False):
        teks_tempel = st.text_area("Tempel di sini:", height=220, key=f"{k}_teks")

        st.markdown("**Data umum untuk soal yang tidak mencantumkannya sendiri:**")
        kol1, kol2 = st.columns(2)
        with kol1:
            jenjang = st.text_input("Jenjang (contoh: SMP)", key=f"{k}_jenjang")
            kelas = st.text_input("Kelas (contoh: Kelas 7)", key=f"{k}_kelas")
        with kol2:
            mapel = st.selectbox("Mapel", [""] + list(MAPEL_OPTIONS), key=f"{k}_mapel")
            _paket_lama = daftar_paket_bank()
            paket_pilih = st.selectbox("Paket yang sudah ada (opsional)", [""] + _paket_lama,
                                       format_func=lambda x: "— pilih paket —" if not x else x, key=f"{k}_paket_lama")
            topik = st.text_input("Bab / topik = nama paket (ketik untuk paket baru)", key=f"{k}_topik")
        konversi_ditekan = st.form_submit_button("🔄 Konversi dan periksa")
    meta = {"jenjang": jenjang.strip(), "kelas": kelas.strip(), "mapel": mapel.strip(), "topik": (topik.strip() or paket_pilih.strip())}

    kunci_hasil = f"{k}_hasil"
    if konversi_ditekan:
        if not teks_tempel.strip():
            st.warning("Tempel soal terlebih dahulu.")
        else:
            try:
                ws_bank = get_worksheet("Bank_Soal_Master")
                headers = ws_bank.row_values(1)
                existing = baca_records_aman(ws_bank, refresh=True)
                bentuk_peta = {str(x.get("Bentuk_Soal", "")).strip().casefold(): str(x.get("Bentuk_Soal", "")).strip()
                               for x in existing if str(x.get("Bentuk_Soal", "")).strip()}
                # Duplikat hanya dihitung di paket yang sama (Bab/topik sama) dan hanya terhadap soal aktif.
                teks_ada = {(_bank_sidik_soal(x.get("Teks_Soal", ""), x.get("Opsi_Jawaban", ""), x.get("Bentuk_Soal", "")),
                             _paket_norm(x.get("Bab_Atau_Topik", "")))
                            for x in existing if _soal_aktif(x)}
                if mode.startswith("Teks"):
                    mentah, masalah_umum = bank_parse_teks_soal(teks_tempel), []
                else:
                    mentah, masalah_umum = bank_parse_tabel(teks_tempel)
                kurang = sorted({"Kode_Soal", "Jenjang", "Kelas", "Mapel", "Bab_Atau_Topik", "Bentuk_Soal",
                                 "Teks_Soal", "Opsi_Jawaban", "Kunci_Jawaban", "Status"} - set(headers))
                if kurang:
                    masalah_umum.append("Kolom Bank_Soal_Master belum lengkap: " + ", ".join(kurang))
                baris_hasil, dilihat = [], set()
                for item in mentah:
                    b = bank_bangun_baris(item, meta, bentuk_peta)
                    norm = _bank_sidik_soal(b["Teks_Soal"], b["Opsi_Jawaban"], b["Bentuk_Soal"])
                    norm = (norm, _paket_norm(b.get("Bab_Atau_Topik", "")))
                    if b["Teks_Soal"] and (norm in teks_ada or norm in dilihat):
                        b["_masalah"].append("soal yang sama sudah ada di paket ini, dilewati")
                    dilihat.add(norm)
                    for kolom_wajib, nama_tampil in (("Jenjang", "jenjang"), ("Kelas", "kelas"), ("Mapel", "mapel")):
                        if not b[kolom_wajib]:
                            b["_masalah"].append(f"{nama_tampil} belum diisi")
                    baris_hasil.append(b)
                st.session_state[kunci_hasil] = {"headers": headers, "baris": baris_hasil, "umum": masalah_umum}
            except Exception as exc:
                st.session_state.pop(kunci_hasil, None)
                st.error(f"Konversi belum dapat dilakukan: {exc}")

    hasil = st.session_state.get(kunci_hasil)
    if not hasil:
        return
    for pesan in hasil["umum"]:
        st.error(pesan)
    baris_hasil = hasil["baris"]
    if not baris_hasil:
        st.info("Tidak ada soal yang terbaca. Periksa format tempelan.")
        return
    jumlah_dup = sum(1 for b in baris_hasil if any("sudah ada" in m for m in b["_masalah"]))
    abaikan_dup = False
    if jumlah_dup:
        abaikan_dup = st.checkbox(
            f"{jumlah_dup} soal sama persis dengan soal lain di paket ini. Simpan juga (abaikan pemeriksaan duplikat)",
            key=f"{k}_abaikan_dup")
    def _masalah_efektif(b):
        return [m for m in b["_masalah"] if not (abaikan_dup and "sudah ada" in m)]
    siap = [b for b in baris_hasil if not _masalah_efektif(b)]
    st.markdown(f"**Hasil: {len(siap)} soal siap disimpan dari {len(baris_hasil)} soal terbaca.**")
    st.dataframe(pd.DataFrame([
        {
            "No": i,
            "Status": "✅ Siap" if not _masalah_efektif(b) else "❌ " + "; ".join(_masalah_efektif(b))[:70],
            "Bentuk": b["Bentuk_Soal"], "Soal": pisah_wacana(b["Teks_Soal"])[1][:80],
            "Bacaan": "📖" if pisah_wacana(b["Teks_Soal"])[0] else "",
            "Pilihan": b["Opsi_Jawaban"], "Kunci": b["Kunci_Jawaban"],
            "Catatan": "; ".join(_masalah_efektif(b) + b["_catatan"]),
        } for i, b in enumerate(baris_hasil, 1)
    ]), use_container_width=True, hide_index=True)
    if len(siap) < len(baris_hasil):
        st.caption("Soal bertanda ❌ tidak ikut disimpan; alasannya tertulis di kolom Status. Perbaiki teks tempelan lalu tekan Konversi lagi.")
    if siap and not hasil["umum"]:
        if st.button(f"💾 Simpan {len(siap)} soal ke Bank_Soal_Master", type="primary", key=f"{k}_simpan"):
            try:
                ws_bank = get_worksheet("Bank_Soal_Master")
                baris_tulis = [bank_susun_sesuai_header(hasil["headers"], b) for b in siap]
                baris_awal, baris_akhir = _panggil_sheets_dengan_retry_429(
                    _tulis_baris_bank, ws_bank, baris_tulis, len(hasil["headers"])
                )
                _baca_values_cache.clear()
                st.session_state.pop(kunci_hasil, None)
                # Verifikasi: baca ulang dari Google Sheets dan pastikan soal terbaca sebagai soal aktif.
                tersimpan = baca_records_aman(ws_bank, refresh=True)
                kode_tulis = {b["Kode_Soal"] for b in siap}
                terbaca = [
                    r for r in tersimpan
                    if str(r.get("Kode_Soal", "")).strip() in kode_tulis
                    and str(r.get("Status", "")).strip().lower() in ("aktif", "ya", "true", "1")
                ]
                total_aktif = sum(
                    1 for r in tersimpan if str(r.get("Status", "")).strip().lower() in ("aktif", "ya", "true", "1")
                )
                if len(terbaca) == len(siap):
                    st.success(
                        f"{len(siap)} soal tersimpan di Bank_Soal_Master (baris {baris_awal}-{baris_akhir}) dan terverifikasi. "
                        f"Bank Soal sekarang berisi {total_aktif} soal aktif. Soal terbaru tampil paling atas di pilihan Bank Soal Bersama."
                    )
                else:
                    st.error(
                        f"Hanya {len(terbaca)} dari {len(siap)} soal terbaca sebagai soal aktif setelah disimpan. "
                        f"Periksa baris {baris_awal}-{baris_akhir} di sheet Bank_Soal_Master (kolom Kode_Soal dan Status)."
                    )
            except Exception as exc:
                st.error(f"Soal belum tersimpan: {exc}")


def tulis_baris_di_bawah(ws, baris, mode="RAW", nilai_sekarang=None):
    """Tulis satu baris tepat di kolom A pada baris kosong pertama di bawah data.
    Tidak memakai append_row, karena append_row menebak 'tabel' dan bisa menggeser kolom bila sheet
    punya blok data lain; akibatnya ID siswa mendarat di kolom yang salah. Mengembalikan nomor baris."""
    nilai = nilai_sekarang if nilai_sekarang is not None else ws.get_all_values()
    nomor = len(nilai) + 1
    kolom = re.sub(r"\d+", "", gspread.utils.rowcol_to_a1(1, max(len(baris), 1)))
    rentang = f"A{nomor}:{kolom}{nomor}"
    try:
        ws.update(range_name=rentang, values=[list(baris)], value_input_option=mode)
    except Exception as exc:
        if "grid" not in str(exc).lower():
            raise
        ws.add_rows(10)
        ws.update(range_name=rentang, values=[list(baris)], value_input_option=mode)
    return nomor


def tulis_banyak_baris_di_bawah(ws, daftar_baris, mode="RAW"):
    """Tulis beberapa baris sekaligus (satu panggilan update) tepat di bawah data terakhir.
    Pengganti append_rows yang menebak 'tabel' dan bisa menggeser kolom. Mengembalikan baris pertama."""
    daftar_baris = [list(b) for b in (daftar_baris or [])]
    if not daftar_baris:
        return None
    awal = len(ws.get_all_values()) + 1
    akhir = awal + len(daftar_baris) - 1
    lebar = max(len(b) for b in daftar_baris)
    kolom = re.sub(r"\d+", "", gspread.utils.rowcol_to_a1(1, max(lebar, 1)))
    rentang = f"A{awal}:{kolom}{akhir}"
    try:
        ws.update(range_name=rentang, values=daftar_baris, value_input_option=mode)
    except Exception as exc:
        if "grid" not in str(exc).lower():
            raise
        ws.add_rows(len(daftar_baris) + 10)
        ws.update(range_name=rentang, values=daftar_baris, value_input_option=mode)
    _baca_values_cache.clear()
    return awal


NAMA_SHEET_ID_SISWA = [
    "Data_Siswa", "Akun_Pengguna", "Relasi_Orangtua_Siswa", "Tugas_Sesi_Siswa_v2",
    "DB_Jawaban_Siswa", "DB_Lampiran_Jawaban", "DB_Nilai_Tugas", "Riwayat_Focus_Alert",
]


def _muat_sheet_id_siswa():
    """Baca (ws, nilai, indeks_kolom_ID_Siswa) untuk semua sheet yang memuat ID siswa."""
    hasil = []
    daftar_nama = list(NAMA_SHEET_ID_SISWA)
    try:
        judul_sesi = get_active_task_worksheet().title
        if judul_sesi not in daftar_nama:
            daftar_nama.append(judul_sesi)
    except Exception:
        pass
    for nama in daftar_nama:
        try:
            ws = get_worksheet(nama)
        except gspread.WorksheetNotFound:
            continue
        nilai = ws.get_all_values()
        if not nilai:
            continue
        kolom = [i for i, h in enumerate(nilai[0]) if str(h).strip().casefold() == "id_siswa"]
        if kolom:
            hasil.append((ws, nilai, kolom))
    return hasil


def hitung_pemakaian_id_siswa(sheet_data, id_cari):
    """Jumlah baris per sheet yang memuat id_cari pada kolom ID_Siswa."""
    kunci = str(id_cari).strip().upper()
    hasil = {}
    for ws, nilai, kolom in sheet_data:
        n = sum(
            1 for row in nilai[1:]
            if any(c < len(row) and str(row[c]).strip().upper() == kunci for c in kolom)
        )
        if n:
            hasil[ws.title] = n
    return hasil


def ganti_id_siswa_di_semua_sheet(sheet_data, id_lama, id_baru):
    """Ganti id_lama menjadi id_baru pada semua kolom ID_Siswa. Satu batch_update per sheet."""
    kunci = str(id_lama).strip().upper()
    ringkas = {}
    for ws, nilai, kolom in sheet_data:
        pembaruan = []
        for nomor, row in enumerate(nilai[1:], start=2):
            for c in kolom:
                if c < len(row) and str(row[c]).strip().upper() == kunci:
                    pembaruan.append({"range": gspread.utils.rowcol_to_a1(nomor, c + 1), "values": [[id_baru]]})
        if pembaruan:
            ws.batch_update(pembaruan, value_input_option="RAW")
            ringkas[ws.title] = len(pembaruan)
    _baca_values_cache.clear()
    return ringkas


def tampilkan_cek_perbaiki_id():
    st.header("🔧 Cek & Perbaiki ID Siswa")
    st.caption(
        "Mencari siswa yang namanya sama tetapi ID di Data_Siswa berbeda dengan ID di Akun_Pengguna. "
        "Pindai dulu (hanya membaca), lalu pilih ID yang dipertahankan. Perbaikan menyamakan ID di semua sheet."
    )
    if st.button("🔍 Pindai ID siswa", key="pindai_id_siswa"):
        try:
            st.session_state["_pindai_id"] = _muat_sheet_id_siswa()
        except Exception as exc:
            st.error(f"Pemindaian gagal ({exc.__class__.__name__}): {exc}")
            return
    sheet_data = st.session_state.get("_pindai_id")
    if not sheet_data:
        st.info("Tekan Pindai untuk memulai.")
        return
    peta = {ws.title: (nilai, kolom) for ws, nilai, kolom in sheet_data}
    if "Data_Siswa" not in peta or "Akun_Pengguna" not in peta:
        st.error("Sheet Data_Siswa atau Akun_Pengguna tidak ditemukan.")
        return

    def _records(judul):
        nilai, _k = peta[judul]
        kepala = [str(h).strip() for h in nilai[0]]
        return [dict(zip(kepala, row)) for row in nilai[1:] if any(str(x).strip() for x in row)]

    def _ambil(rec, *nama):
        for n in nama:
            if str(rec.get(n, "")).strip():
                return str(rec.get(n, "")).strip()
        return ""

    siswa = _records("Data_Siswa")
    id_siswa_semua = {}
    nama_ke_id = {}
    for r in siswa:
        sid = _ambil(r, "ID_SISWA", "ID_Siswa").upper()
        nama = _ambil(r, "Nama_Siswa", "Nama_Lengkap").casefold()
        if sid and nama:  # baris hanya-ID (tanpa nama) tidak dihitung sebagai siswa
            id_siswa_semua.setdefault(sid, []).append(nama)
            nama_ke_id.setdefault(nama, []).append(sid)
    kasus = []
    for r in _records("Akun_Pengguna"):
        if _ambil(r, "Level_Akses").casefold() != "siswa":
            continue
        id_akun = _ambil(r, "ID_SISWA", "ID_Siswa").upper()
        nama = _ambil(r, "Nama_Pengguna").casefold()
        id_data = nama_ke_id.get(nama, [])
        if id_data and id_akun not in id_data:
            kasus.append({"Nama": _ambil(r, "Nama_Pengguna"), "ID_Data_Siswa": id_data[0], "ID_Akun": id_akun or "(kosong)", "jenis": "beda"})
        elif not id_data and id_akun and id_akun not in id_siswa_semua:
            kasus.append({"Nama": _ambil(r, "Nama_Pengguna"), "ID_Data_Siswa": "-", "ID_Akun": id_akun, "jenis": "akun tanpa siswa"})
    ganda = {i: n for i, n in id_siswa_semua.items() if len(n) > 1}
    if ganda:
        st.warning("ID ganda di Data_Siswa: " + "; ".join(f"{i} → {', '.join(n)}" for i, n in ganda.items()))
    # Baris sisa: hanya berisi ID (semua kolom lain kosong) dan ID itu juga ada pada baris siswa bernama.
    nilai_ds, kolom_ds = peta["Data_Siswa"]
    kepala_ds = [str(h).strip().casefold() for h in nilai_ds[0]]
    kolom_id_ds = set(kolom_ds)
    baris_sisa = []
    for nomor, row in enumerate(nilai_ds[1:], start=2):
        ids = {str(row[c]).strip().upper() for c in kolom_id_ds if c < len(row) and str(row[c]).strip()}
        lain = [str(x).strip() for j, x in enumerate(row) if j not in kolom_id_ds and str(x).strip()]
        if ids and not lain and any(i in id_siswa_semua for i in ids):
            baris_sisa.append((nomor, sorted(ids)[0]))
    if baris_sisa:
        st.warning(
            f"Ditemukan {len(baris_sisa)} baris sisa di Data_Siswa: hanya berisi ID (tanpa nama/kelas/PIN), "
            "sedangkan ID yang sama sudah ada pada baris siswa bernama. Baris sisa tidak dipakai aplikasi."
        )
        st.caption("Contoh (nomor baris → ID): " + ", ".join(f"{n}→{i}" for n, i in baris_sisa[:15]) + (" …" if len(baris_sisa) > 15 else ""))
        st.caption("Sebelum membersihkan, buat salinan spreadsheet (File → Buat salinan). Pembersihan hanya mengosongkan sel baris sisa, tidak menghapus baris.")
        yakin_sisa = st.checkbox("Saya sudah membuat salinan dan ingin mengosongkan baris sisa.", key="yakin_baris_sisa")
        if st.button("🧹 Kosongkan baris sisa ber-ID", key="bersihkan_baris_sisa", disabled=not yakin_sisa):
            try:
                ws_ds = next(ws for ws, _n, _k in sheet_data if ws.title == "Data_Siswa")
                lebar_ds = max(len(kepala_ds), 1)
                kolom_akhir = re.sub(r"\d+", "", gspread.utils.rowcol_to_a1(1, lebar_ds))
                ws_ds.batch_clear([f"A{n}:{kolom_akhir}{n}" for n, _i in baris_sisa])
                _baca_values_cache.clear()
                st.session_state.pop("_pindai_id", None)
                st.success(f"{len(baris_sisa)} baris sisa dikosongkan. Tekan Pindai lagi untuk memeriksa ulang.")
            except Exception as exc:
                st.error(f"Gagal membersihkan ({exc.__class__.__name__}): {exc}")
    if not kasus:
        st.success("Tidak ditemukan siswa dengan ID berbeda antara Data_Siswa dan Akun_Pengguna.")
        return
    baris_tabel = []
    for k in kasus:
        pakai_data = hitung_pemakaian_id_siswa(sheet_data, k["ID_Data_Siswa"]) if k["ID_Data_Siswa"] != "-" else {}
        pakai_akun = hitung_pemakaian_id_siswa(sheet_data, k["ID_Akun"]) if k["ID_Akun"] != "(kosong)" else {}
        baris_tabel.append({
            "Nama": k["Nama"], "Jenis": k["jenis"],
            "ID di Data_Siswa": k["ID_Data_Siswa"], "Dipakai (Data_Siswa ID)": ", ".join(f"{a}:{b}" for a, b in pakai_data.items()) or "-",
            "ID di Akun": k["ID_Akun"], "Dipakai (Akun ID)": ", ".join(f"{a}:{b}" for a, b in pakai_akun.items()) or "-",
        })
    st.dataframe(pd.DataFrame(baris_tabel), use_container_width=True, hide_index=True)
    bisa_diperbaiki = [k for k in kasus if k["jenis"] == "beda" and k["ID_Akun"] != "(kosong)"]
    if not bisa_diperbaiki:
        st.info("Kasus di atas perlu diperiksa manual (akun tanpa siswa / ID akun kosong).")
        return
    pilih = st.selectbox(
        "Pilih siswa yang diperbaiki:",
        [f"{k['Nama']} · Data {k['ID_Data_Siswa']} / Akun {k['ID_Akun']}" for k in bisa_diperbaiki],
        key="pilih_kasus_id"
    )
    k = bisa_diperbaiki[[f"{x['Nama']} · Data {x['ID_Data_Siswa']} / Akun {x['ID_Akun']}" for x in bisa_diperbaiki].index(pilih)]
    opsi_a = f"Pakai ID Data_Siswa: {k['ID_Data_Siswa']} (ID akun {k['ID_Akun']} diganti)"
    opsi_b = f"Pakai ID Akun: {k['ID_Akun']} (ID Data_Siswa {k['ID_Data_Siswa']} diganti)"
    arah = st.radio("ID yang dipertahankan:", [opsi_a, opsi_b], key="arah_id")
    if arah == opsi_a:
        id_final, id_buang = k["ID_Data_Siswa"], k["ID_Akun"]
    else:
        id_final, id_buang = k["ID_Akun"], k["ID_Data_Siswa"]
    pemilik_buang = id_siswa_semua.get(id_buang.upper(), [])
    pemilik_final = id_siswa_semua.get(id_final.upper(), [])
    nama_kasus = k["Nama"].strip().casefold()
    lain_buang = [n for n in pemilik_buang if n != nama_kasus]
    lain_final = [n for n in pemilik_final if n != nama_kasus]
    if lain_buang or lain_final:
        st.error("ID yang terlibat juga dipakai siswa lain di Data_Siswa. Perbaiki manual agar tidak menimpa data siswa lain.")
        return
    rencana = hitung_pemakaian_id_siswa(sheet_data, id_buang)
    st.write(f"**Rencana:** ganti `{id_buang}` → `{id_final}` pada: " + (", ".join(f"{a} ({b} baris)" for a, b in rencana.items()) or "tidak ada baris"))
    yakin = st.checkbox("Saya sudah memeriksa rencana di atas dan siap menyamakan ID.", key="yakin_id")
    if st.button("✅ Samakan ID sekarang", key="terapkan_id", disabled=not yakin):
        try:
            ringkas = ganti_id_siswa_di_semua_sheet(sheet_data, id_buang, id_final)
            st.session_state.pop("_pindai_id", None)
            st.success("ID disamakan: " + (", ".join(f"{a} ({b})" for a, b in ringkas.items()) or "tidak ada perubahan") +
                       f". Siswa kini memakai ID {id_final} untuk login.")
        except Exception as exc:
            st.error(f"Gagal menyamakan ID ({exc.__class__.__name__}): {exc}. Periksa sheet sebelum mengulang.")


def _id_berikutnya(nilai_list, default):
    """ID berikutnya mengikuti pola ID yang sudah ada di kolom (awalan, pemisah, lebar angka)."""
    from collections import Counter
    pola = re.compile(r"^(.*?)(\d+)$")
    awalan_ada, maks, lebar = Counter(), {}, {}
    for v in nilai_list:
        m = pola.match(str(v).strip())
        if not m:
            continue
        awal, angka = m.group(1), m.group(2)
        awalan_ada[awal] += 1
        maks[awal] = max(maks.get(awal, 0), int(angka))
        lebar[awal] = max(lebar.get(awal, 0), len(angka))
    if not awalan_ada:
        return default
    awal = awalan_ada.most_common(1)[0][0]
    return f"{awal}{maks[awal] + 1:0{lebar[awal]}d}"


def tambah_baris_sesuai_header(ws, nilai, wajib=(), id_otomatis=None):
    """Tulis satu baris mengikuti urutan header sheet yang sebenarnya (bukan asumsi urutan kolom).
    nilai: {nama_header: isi}. id_otomatis: {nama_header: ID_awal_bila_kolom_kosong}; ID dibuat dari isi kolom
    tepat sebelum menulis. Header yang tidak dikenal dibiarkan kosong. Mengembalikan nilai akhir (kunci huruf kecil)."""
    data = ws.get_all_values()
    if not data:
        raise RuntimeError(f"Sheet {ws.title} belum memiliki header.")
    headers = [str(h).strip() for h in data[0]]
    kecil = [h.casefold() for h in headers]
    kurang = [w for w in wajib if w.casefold() not in kecil]
    if kurang:
        raise RuntimeError(f"Kolom {', '.join(kurang)} tidak ditemukan di sheet {ws.title}.")
    akhir = {str(k).casefold(): v for k, v in nilai.items()}
    for header, default in (id_otomatis or {}).items():
        if header.casefold() in kecil:
            idx = kecil.index(header.casefold())
            akhir[header.casefold()] = _id_berikutnya(
                [r[idx] if idx < len(r) else "" for r in data[1:]], default
            )
    tulis_baris_di_bawah(ws, [akhir.get(h, "") for h in kecil], "RAW", nilai_sekarang=data)
    _baca_values_cache.clear()
    return akhir


def buat_akun_pengguna(nama, level, pin, id_siswa=""):
    """Buat baris login di Akun_Pengguna dengan ID_User otomatis (USR-xxx) dan PIN ter-hash."""
    ws = get_worksheet("Akun_Pengguna")
    data = ws.get_all_values()
    headers = [str(h).strip().casefold() for h in data[0]] if data else []
    username_ada = set()
    if "username" in headers:
        i = headers.index("username")
        username_ada = {str(r[i]).strip().casefold() for r in data[1:] if i < len(r)}
    dasar = ("siswa_" if str(level).casefold() == "siswa" else "ortu_") + (
        re.sub(r"[^a-z0-9]+", "", str(nama).casefold())[:20] or "user"
    )
    username, n = dasar, 2
    while username.casefold() in username_ada:
        username, n = f"{dasar}{n}", n + 1
    akhir = tambah_baris_sesuai_header(
        ws,
        {
            "Nama_Pengguna": nama, "Level_Akses": level, "Username": username,
            "PIN_Password": hash_pin(pin), "Akses_Khusus": level,
            "ID_SISWA": id_siswa, "Status": "Aktif",
        },
        wajib=("ID_User", "Nama_Pengguna", "Level_Akses", "PIN_Password"),
        id_otomatis={"ID_User": "USR-001"},
    )
    return akhir["id_user"]


def daftarkan_orang_tua(nama_ortu, hubungan, pin, id_siswa, wali_utama=True, no_hp=""):
    """Buat akun login wali (Akun_Pengguna), data wali (Data_Orangtua), dan relasi ke anak
    (Relasi_Orangtua_Siswa). Jika satu langkah gagal, pesan galat menyebut langkah yang sudah tersimpan."""
    tersimpan = []
    try:
        # Periksa dulu header semua sheet agar tidak ada data setengah jadi.
        for judul, wajib in (("Akun_Pengguna", ("ID_User", "Nama_Pengguna", "Level_Akses", "PIN_Password")),
                             ("Data_Orangtua", ("ID_Ortu", "ID_User", "Nama_Ortu")),
                             ("Relasi_Orangtua_Siswa", ("ID_Ortu", "ID_Siswa"))):
            header_ada = [str(h).strip().casefold() for h in get_worksheet(judul).row_values(1)]
            kurang = [w for w in wajib if w.casefold() not in header_ada]
            if kurang:
                raise RuntimeError(f"Kolom {', '.join(kurang)} tidak ditemukan di sheet {judul}.")
        id_user = buat_akun_pengguna(nama_ortu, "Orang Tua", pin)
        tersimpan.append(f"akun login {id_user}")
        tanggal = waktu_lokal().strftime("%Y-%m-%d")
        hasil_ortu = tambah_baris_sesuai_header(
            get_worksheet("Data_Orangtua"),
            {"ID_User": id_user, "Nama_Ortu": nama_ortu, "Status_Ortu": "Aktif",
             "No_HP": no_hp, "Hubungan": hubungan, "Tanggal_Dibuat": tanggal},
            wajib=("ID_Ortu", "ID_User", "Nama_Ortu"),
            id_otomatis={"ID_Ortu": "ORT001"},
        )
        id_ortu = hasil_ortu["id_ortu"]
        tersimpan.append(f"Data_Orangtua {id_ortu}")
        ws_relasi = get_worksheet("Relasi_Orangtua_Siswa")
        header_relasi = [str(h).strip() for h in ws_relasi.row_values(1)]
        auto_relasi = {}
        if header_relasi and "relasi" in header_relasi[0].casefold():
            auto_relasi = {header_relasi[0]: "REL001"}
        tambah_baris_sesuai_header(
            ws_relasi,
            {"ID_Ortu": id_ortu, "ID_Siswa": id_siswa, "Hubungan": hubungan,
             "Wali_Utama": "Ya" if wali_utama else "Tidak", "Status_Relasi": "Aktif",
             "Tanggal_Dibuat": tanggal},
            wajib=("ID_Ortu", "ID_Siswa"),
            id_otomatis=auto_relasi,
        )
        tersimpan.append("relasi ke anak")
        return {"id_user": id_user, "id_ortu": id_ortu}
    except Exception as exc:
        awal = ("Sudah tersimpan: " + ", ".join(tersimpan) + ". ") if tersimpan else "Belum ada yang tersimpan. "
        raise RuntimeError(f"{awal}Gagal: {exc}") from exc


def tampilkan_pilih_siswa_tambahan(selected_siswa, siswa_aktif, dalam_expander=True):
    """Pilih beberapa siswa untuk tugas yang sama.
    Urutan tampilan: kotak cari -> hasil (tombol ➕) -> daftar siswa terpilih (✅ nama + tombol Hapus).
    Kotak cari dikosongkan otomatis setelah menambah, dan ada pesan konfirmasi di bawahnya."""
    kunci = f"_siswa_tambahan_{selected_siswa}"
    kunci_cari = f"cari_tambahan_{selected_siswa}"
    kunci_info = f"_info_tambahan_{selected_siswa}"
    terpilih = list(st.session_state.get(kunci, []))
    utama = str(selected_siswa).strip().casefold()

    def _tambah(*daftar_nama):
        daftar = list(st.session_state.get(kunci, []))
        sudah = {str(x).strip().casefold() for x in daftar}
        baru_ditambah = []
        for nama in daftar_nama:
            kunci_nama = str(nama).strip().casefold()
            if kunci_nama and kunci_nama != utama and kunci_nama not in sudah:
                daftar.append(nama)
                sudah.add(kunci_nama)
                baru_ditambah.append(nama)
        st.session_state[kunci] = daftar
        st.session_state[kunci_cari] = ""
        if baru_ditambah:
            st.session_state[kunci_info] = (
                f"✅ {', '.join(baru_ditambah)} berhasil ditambahkan. Total {len(daftar)} siswa lain. "
                "Ketik nama siswa berikutnya di kotak di atas bila masih ada."
            )

    def _hapus(nama):
        st.session_state[kunci] = [x for x in st.session_state.get(kunci, []) if x != nama]
        st.session_state[kunci_info] = f"🗑 {nama} dihapus dari daftar."

    judul_bagi = f"👥 Beri tugas yang sama ke siswa lain (opsional) — {len(terpilih)} dipilih"
    if dalam_expander:
        wadah_bagi = st.expander(judul_bagi, expanded=bool(terpilih))
    else:
        wadah_bagi = st.container(border=True)
    with wadah_bagi:
        if not dalam_expander:
            st.markdown(f"**{judul_bagi}**")
        st.caption(
            f"Siswa utama: {selected_siswa}. Ketik nama siswa lain, tekan Enter, lalu tekan tombol ➕ pada nama yang cocok. "
            "Ulangi untuk menambah siswa lain. Setiap siswa mendapat tugas, timer, jawaban, dan nilai sendiri."
        )
        cari = st.text_input(
            "Ketik nama siswa lalu tekan Enter (minimal 3 huruf):", key=kunci_cari
        )
        sudah_dipilih = {str(x).strip().casefold() for x in terpilih}
        hasil, pesan = cari_siswa_terbatas(
            cari,
            [n for n in siswa_aktif
             if str(n).strip().casefold() != utama and str(n).strip().casefold() not in sudah_dipilih]
        )
        if pesan:
            st.caption(pesan)
        if len(hasil) > 1:
            st.button(
                f"➕ Tambah semua yang cocok ({len(hasil)})",
                key=f"tbh_semua_{selected_siswa}", on_click=_tambah, args=tuple(hasil)
            )
        for nama in hasil:
            st.button(f"➕ Tambah {nama}", key=f"tbh_tambah_{selected_siswa}_{nama}", on_click=_tambah, args=(nama,))
        info = st.session_state.get(kunci_info)
        if info:
            st.success(info)
        if terpilih:
            st.markdown(f"**Siswa lain yang akan menerima tugas ini ({len(terpilih)}):**")
            for nama in terpilih:
                kiri, kanan = st.columns([3, 2])
                kiri.markdown(f"✅ **{nama}**")
                kanan.button("🗑 Hapus", key=f"tbh_hapus_{selected_siswa}_{nama}", on_click=_hapus, args=(nama,))


def tombol_kembali(kunci_menu, wadah=None, label="↩️ Kembali ke halaman sebelumnya"):
    """Ingat menu yang dipilih; tombol ini mengembalikan ke menu sebelumnya (dipanggil SETELAH widget menu dibuat)."""
    wadah = wadah or st.sidebar
    riwayat = st.session_state.setdefault("_riwayat_menu", {}).setdefault(kunci_menu, [])
    sekarang = st.session_state.get(kunci_menu)
    if sekarang is not None and (not riwayat or riwayat[-1] != sekarang):
        riwayat.append(sekarang)
        del riwayat[:-10]

    def _kembali():
        r = st.session_state.get("_riwayat_menu", {}).get(kunci_menu, [])
        if len(r) >= 2:
            r.pop()
            st.session_state[kunci_menu] = r[-1]

    wadah.button(label, key=f"kembali_{kunci_menu}", on_click=_kembali,
                 disabled=len(riwayat) < 2, use_container_width=True)


def edit_tugas_terkirim(ws, id_tugas, perubahan):
    """Perbarui kolom tugas pada baris SEGAR (bukan nomor baris dari cache). perubahan: {nama_kolom: nilai}."""
    data = ws.get_all_values()
    if not data:
        return False
    headers = [str(h).strip() for h in data[0]]
    if "ID_Tugas" not in headers:
        return False
    i_id = headers.index("ID_Tugas")
    for nomor, row in enumerate(data[1:], start=2):
        if i_id < len(row) and str(row[i_id]).strip() == str(id_tugas).strip():
            pembaruan = [{"range": gspread.utils.rowcol_to_a1(nomor, headers.index(k) + 1), "values": [[v]]}
                         for k, v in perubahan.items() if k in headers]
            if pembaruan:
                ws.batch_update(pembaruan, value_input_option="RAW")
                _baca_values_cache.clear()
            return True
    return False


def _peta_baris_tugas_segar(ws):
    """Baca langsung dari Sheets (tanpa cache) lalu petakan ID_Tugas -> (nomor baris, status). Cache lama
    bisa membuat nomor baris keliru setelah ada baris yang dihapus, jadi aksi tulis selalu memakai ini."""
    data = ws.get_all_values()
    if not data:
        return [], {}
    headers = [str(h).strip() for h in data[0]]
    if "ID_Tugas" not in headers or "Status_Tugas" not in headers:
        raise RuntimeError("Kolom ID_Tugas atau Status_Tugas tidak ditemukan di Tugas_Sesi_Siswa_v2.")
    i_id, i_st = headers.index("ID_Tugas"), headers.index("Status_Tugas")
    peta = {}
    for nomor, row in enumerate(data[1:], start=2):
        if i_id < len(row) and str(row[i_id]).strip():
            peta[str(row[i_id]).strip()] = (nomor, str(row[i_st]).strip() if i_st < len(row) else "")
    return headers, peta


def tampilkan_riwayat_tugas_owner():
    """Riwayat tugas SEMUA tutor untuk Pengelola: lihat, batalkan, pulihkan, dan bersihkan tugas batal."""
    st.header("📜 Riwayat Semua Tugas")
    st.caption(
        "Tugas dari semua tutor. Batalkan = tugas hilang dari siswa tetapi masih tercatat dan bisa dipulihkan. "
        "Hapus permanen hanya untuk tugas yang sudah dibatalkan dan belum pernah dikirim siswa. "
        "Tugas yang sudah dikirim atau dinilai boleh dibatalkan (dengan konfirmasi) tetapi tidak pernah dihapus permanen karena menyimpan jawaban dan nilai."
    )
    _pesan_riw = st.session_state.pop("_pesan_riwayat_tugas", None)
    if _pesan_riw:
        st.success(_pesan_riw)
    if st.button("🔄 Muat ulang data", key="riw_muat"):
        _baca_values_cache.clear()
        st.rerun()
    try:
        ws = get_worksheet("Tugas_Sesi_Siswa_v2")
    except gspread.WorksheetNotFound:
        st.info("Sheet Tugas_Sesi_Siswa_v2 belum ada.")
        return
    tugas = baca_records_aman(ws)
    if not tugas:
        st.info("Belum ada tugas.")
        return
    try:
        jawaban = baca_jawaban_tergabung(get_answers_worksheet())
    except Exception:
        jawaban = []
    status_by_task = {str(x.get("ID_Tugas", "")).strip(): str(x.get("Status", "")) for x in jawaban}
    try:
        nilai_keys = {kunci_nilai_penugasan(n) for n in baca_nilai_tugas_terpadu() if all(kunci_nilai_penugasan(n))}
    except Exception:
        nilai_keys = set()

    def nama_tutor(t):
        return str(t.get("Tutor", "")).strip() or "(tanpa tutor)"

    c1, c2 = st.columns(2)
    f_tutor = c1.selectbox("Tutor:", ["Semua tutor"] + sorted({nama_tutor(t) for t in tugas}), key="riw_tutor")
    f_status = c2.selectbox("Status:", ["Semua", "Aktif", "Dibatalkan"], key="riw_status")
    f_kata = st.text_input("Cari nama siswa atau judul (opsional):", key="riw_kata").strip().casefold()

    baris, opsi = [], {}
    for t in reversed(tugas):
        tid = str(t.get("ID_Tugas", "")).strip()
        if not tid:
            continue
        batal = "batal" in str(t.get("Status_Tugas", "")).lower()
        kode, label = label_status(t, status_by_task, nilai_keys)
        if batal:
            kode, label = "batal", "🚫 Dibatalkan"
        if f_tutor != "Semua tutor" and nama_tutor(t) != f_tutor:
            continue
        if f_status == "Aktif" and batal:
            continue
        if f_status == "Dibatalkan" and not batal:
            continue
        teks_cari = f"{t.get('Nama_Siswa', '')} {t.get('Judul_Tugas', '')} {t.get('Mapel', '')}".casefold()
        if f_kata and f_kata not in teks_cari:
            continue
        baris.append({
            "Tanggal": str(t.get("Tanggal", ""))[:10], "Tutor": nama_tutor(t),
            "Siswa": t.get("Nama_Siswa", ""), "Mapel": t.get("Mapel", ""),
            "Judul": t.get("Judul_Tugas", ""), "Status": label, "ID": tid,
        })
        opsi[tid] = (kode, f"{t.get('Nama_Siswa', '')} | {t.get('Mapel', '')} | {t.get('Judul_Tugas', '')} | {nama_tutor(t)} | {str(t.get('Tanggal', ''))[:10]} | {tid}")

    st.markdown(f"**{len(baris)} tugas** sesuai filter.")
    if not baris:
        return
    st.dataframe(pd.DataFrame(baris[:300]), use_container_width=True, hide_index=True)
    if len(baris) > 300:
        st.caption("Tabel menampilkan 300 tugas terbaru; persempit filter untuk melihat yang lain.")

    st.markdown("#### Proses tugas terpilih")
    pilih = st.multiselect(
        "Pilih tugas (maksimal 30 sekali proses):",
        options=list(opsi.keys())[:200], format_func=lambda i: opsi[i][1],
        key=f"riw_pilih_{abs(hash((f_tutor, f_status, f_kata))) % 10**8}_{st.session_state.get('_riw_n', 0)}",
        max_selections=30
    )
    ada_terkirim = [i for i in pilih if opsi[i][0] in ("dikirim", "dinilai")]
    izin_terkirim = True
    if ada_terkirim:
        izin_terkirim = st.checkbox(
            f"Saya yakin membatalkan {len(ada_terkirim)} tugas yang sudah dikirim/dinilai. "
            "Jawaban dan nilai tetap tersimpan; tugas hanya disembunyikan dan bisa dipulihkan.",
            key=f"riw_yakin_terkirim_{len(ada_terkirim)}")
    bisa_batal = [i for i in pilih if opsi[i][0] != "batal" and (izin_terkirim or opsi[i][0] not in ("dikirim", "dinilai"))]
    bisa_pulih = [i for i in pilih if opsi[i][0] == "batal"]

    kiri, kanan = st.columns(2)
    if kiri.button(f"🚫 Batalkan ({len(bisa_batal)})", disabled=not bisa_batal, key="riw_batalkan"):
        try:
            headers, peta = _peta_baris_tugas_segar(ws)
            kolom_status = headers.index("Status_Tugas") + 1
            data = [
                {"range": gspread.utils.rowcol_to_a1(peta[i][0], kolom_status), "values": [["Dibatalkan"]]}
                for i in bisa_batal if i in peta
            ]
            if data:
                ws.batch_update(data, value_input_option="RAW")
            _baca_values_cache.clear()
            st.session_state["_pesan_riwayat_tugas"] = f"{len(data)} tugas dibatalkan."
            st.session_state["_riw_n"] = st.session_state.get("_riw_n", 0) + 1
            st.rerun()
        except Exception as exc:
            st.error(f"Gagal membatalkan: {exc}")
    if kanan.button(f"♻️ Pulihkan ({len(bisa_pulih)})", disabled=not bisa_pulih, key="riw_pulihkan"):
        try:
            headers, peta = _peta_baris_tugas_segar(ws)
            kolom_status = headers.index("Status_Tugas") + 1
            data = [
                {"range": gspread.utils.rowcol_to_a1(peta[i][0], kolom_status), "values": [["Diberikan"]]}
                for i in bisa_pulih if i in peta
            ]
            if data:
                ws.batch_update(data, value_input_option="RAW")
            _baca_values_cache.clear()
            st.session_state["_pesan_riwayat_tugas"] = f"{len(data)} tugas dipulihkan."
            st.session_state["_riw_n"] = st.session_state.get("_riw_n", 0) + 1
            st.rerun()
        except Exception as exc:
            st.error(f"Gagal memulihkan: {exc}")

    # Hapus permanen: hanya tugas batal yang tidak punya jawaban maupun nilai.
    id_dengan_jejak = set(status_by_task) | {k[0] for k in nilai_keys if isinstance(k, tuple) and k}
    batal_semua = [t for t in tugas if "batal" in str(t.get("Status_Tugas", "")).lower()]
    layak_hapus = [str(t.get("ID_Tugas", "")).strip() for t in batal_semua
                   if str(t.get("ID_Tugas", "")).strip() and str(t.get("ID_Tugas", "")).strip() not in id_dengan_jejak]
    with st.expander(f"🗑 Bersihkan tugas batal ({len(layak_hapus)} bisa dihapus permanen)"):
        st.warning("Baris tugas yang sudah dibatalkan dan belum pernah dikirim akan dihapus permanen dari Google Sheets. Tidak bisa dibatalkan.")
        yang_dihapus = [i for i in pilih if i in layak_hapus]
        mode = st.radio(
            "Yang dihapus:", [f"Hanya yang saya pilih di atas ({len(yang_dihapus)})",
                              f"Semua tugas batal yang layak dihapus ({len(layak_hapus)})"],
            key="riw_mode_hapus"
        )
        target = yang_dihapus if mode.startswith("Hanya") else layak_hapus
        konfirmasi = st.text_input("Ketik HAPUS untuk melanjutkan:", key="riw_konfirmasi_hapus").strip()
        if st.button(f"Hapus permanen {len(target)} tugas", disabled=not target or konfirmasi != "HAPUS", key="riw_hapus"):
            try:
                headers, peta = _peta_baris_tugas_segar(ws)
                # Periksa ulang dari data segar: harus masih berstatus batal.
                baris_hapus = sorted(
                    {peta[i][0] for i in target if i in peta and "batal" in peta[i][1].lower()}, reverse=True
                )
                if baris_hapus:
                    permintaan = [
                        {"deleteDimension": {"range": {
                            "sheetId": ws.id, "dimension": "ROWS", "startIndex": n - 1, "endIndex": n
                        }}} for n in baris_hapus  # dari bawah ke atas agar nomor baris tidak bergeser
                    ]
                    ws.spreadsheet.batch_update({"requests": permintaan})
                _baca_values_cache.clear()
                st.session_state["_pesan_riwayat_tugas"] = f"{len(baris_hapus)} tugas dihapus permanen."
                st.session_state["_riw_n"] = st.session_state.get("_riw_n", 0) + 1
                st.session_state.pop("riw_konfirmasi_hapus", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal menghapus: {exc}")


def tampilkan_laporan_perkembangan(nama_siswa, tugas, jawaban, nilai):
    """Ringkasan perkembangan dengan relasi nilai berdasarkan penugasan dan siswa."""
    tugas_siswa = [
        x for x in tugas
        if not adalah_materi(x)
        and str(x.get("Nama_Siswa", "")).strip().casefold() == str(nama_siswa).strip().casefold()
    ]
    ids_tugas = {str(x.get("ID_Tugas", "")).strip() for x in tugas_siswa}
    ids_siswa = {str(x.get("ID_Siswa", "")).strip() for x in tugas_siswa if str(x.get("ID_Siswa", "")).strip()}
    jawaban_siswa = [
        x for x in jawaban
        if str(x.get("ID_Tugas", "")).strip() in ids_tugas
    ]
    nilai_siswa = [
        x for x in nilai
        if (str(x.get("ID_Penugasan", x.get("ID_Tugas", ""))).strip() in ids_tugas)
        and (not ids_siswa or str(x.get("ID_Siswa", "")).strip() in ids_siswa)
    ]
    nilai_angka = []
    for x in nilai_siswa:
        try:
            nilai_angka.append(float(x.get("Nilai", 0)))
        except (ValueError, TypeError):
            pass
    c1, c2, c3 = st.columns(3)
    c1.metric("Total tugas", len(tugas_siswa))
    c2.metric("Jawaban terkirim", len(jawaban_siswa))
    c3.metric("Nilai diterbitkan", len(nilai_angka))
    _peta_pel = hitung_pelanggaran_fokus()
    _total_pel = sum(
        jml for (id_t, id_s), jml in _peta_pel.items()
        if id_t in ids_tugas and (not ids_siswa or id_s in ids_siswa)
    )
    st.metric("Total pelanggaran keluar tab", teks_pelanggaran(_total_pel))
    if nilai_angka:
        st.metric("Rata-rata nilai terbit", f"{sum(nilai_angka)/len(nilai_angka):.1f}")
    else:
        st.caption("Belum ada nilai akhir yang diterbitkan.")



def hitung_nilai_objektif(daftar_soal, jawaban):
    """Hitung nilai soal objektif. Soal uraian sengaja tidak dinilai otomatis."""
    total_objektif = 0
    total_bobot = 0.0
    poin_tertimbang = 0.0
    benar = 0
    rincian = []
    manual = []
    for nomor, soal in enumerate(daftar_soal, 1):
        bentuk = str(soal.get("Bentuk_Soal", "")).casefold()
        kunci = _nilai_parse_jawaban(soal.get("Kunci", soal.get("Kunci_Jawaban", "")))
        siswa = _nilai_parse_jawaban(jawaban.get(str(nomor), ""))
        if any(k in bentuk for k in ("uraian", "essay", "esai", "isian", "jawaban singkat")):
            manual.append(nomor)
            continue
        if not str(kunci).strip() and not isinstance(kunci, (list, dict)):
            manual.append(nomor)
            continue

        bobot = max(0.0, float(soal.get("Bobot", 1) or 1))
        total_objektif += 1
        total_bobot += bobot
        if "pgk mcma" in bentuk or "pilihan ganda kompleks" in bentuk:
            k = kunci if isinstance(kunci, list) else [x.strip() for x in str(kunci).split("|") if x.strip()]
            s = siswa if isinstance(siswa, list) else ([siswa] if siswa not in ("", None) else [])
            k_norm = {_nilai_normalisasi(x) for x in k}
            s_norm = {_nilai_normalisasi(x) for x in s}
            # Nilai parsial: proporsi pilihan kunci yang tepat, tanpa bonus untuk pilihan salah.
            poin = len(k_norm & s_norm) / len(k_norm) if k_norm else 0
            if s_norm - k_norm:
                poin = max(0, poin - len(s_norm - k_norm) / max(len(k_norm), 1))
            poin = max(0, min(1, poin))
        elif "menjodohkan" in bentuk:
            if not isinstance(kunci, dict):
                try:
                    kunci = json.loads(str(kunci))
                except (ValueError, TypeError):
                    kunci = {}
            if not isinstance(siswa, dict):
                siswa = {}
            kunci_pasangan = kunci.get("pasangan", kunci) if isinstance(kunci, dict) else {}
            if isinstance(kunci_pasangan, dict) and kunci_pasangan:
                cocok = sum(
                    1 for k, v in kunci_pasangan.items()
                    if _nilai_normalisasi(siswa.get(k, "")) == _nilai_normalisasi(v)
                )
                poin = cocok / len(kunci_pasangan)
            else:
                poin = 0
        else:
            poin = 1.0 if _nilai_normalisasi(siswa) == _nilai_normalisasi(kunci) else 0.0

        if poin >= 0.999:
            benar += 1
        poin_tertimbang += poin * bobot
        rincian.append({"nomor": nomor, "poin": poin, "bobot": bobot})

    skor = (poin_tertimbang / total_bobot * 100) if total_bobot > 0 else None
    return {
        "skor_objektif": round(skor, 2) if skor is not None else None,
        "jumlah_objektif": total_objektif,
        "jumlah_benar_penuh": benar,
        "soal_manual": manual,
        "rincian": rincian,
    }


def hitung_nilai_akhir_berbobot(daftar_soal, hasil_sementara, nilai_manual=None):
    """Gabungkan skor otomatis dan skor manual memakai bobot soal dari tutor."""
    nilai_manual = {int(k): float(v) for k, v in (nilai_manual or {}).items()}
    rincian_auto = {
        int(x.get("nomor")): (float(x.get("poin", 0) or 0) * 100.0, float(x.get("bobot", 0) or 0))
        for x in (hasil_sementara or {}).get("rincian", [])
    }
    total_bobot = 0.0
    total_tertimbang = 0.0
    belum_dinilai = []
    for nomor, soal in enumerate(daftar_soal or [], 1):
        try:
            bobot = float(soal.get("Bobot", 1) or 0)
        except (TypeError, ValueError):
            return None
        if bobot <= 0:
            return None
        if nomor in rincian_auto:
            skor, _bobot_hasil = rincian_auto[nomor]
        elif nomor in nilai_manual:
            skor = max(0.0, min(100.0, nilai_manual[nomor]))
        else:
            belum_dinilai.append(nomor)
            continue
        total_bobot += bobot
        total_tertimbang += skor * bobot
    if belum_dinilai or total_bobot <= 0:
        return None
    return round(max(1.0, min(100.0, total_tertimbang / total_bobot)), 2)


PENILAI_OTOMATIS = "SISTEM-OTOMATIS"


def terbitkan_nilai_otomatis(task_id, siswa_id, daftar_soal, jawaban):
    """Terbitkan nilai langsung bila SEMUA soal objektif. Essay/isian/campuran tetap diperiksa tutor.
    Mengembalikan nilai yang terbit, atau None bila tidak diterbitkan."""
    hasil = hitung_nilai_sementara(daftar_soal, jawaban)
    if not hasil.get("siap_disetujui"):
        return None
    nilai = hitung_nilai_akhir_berbobot(daftar_soal, hasil)
    if nilai is None:
        return None
    task_id, siswa_id = str(task_id).strip(), str(siswa_id).strip()
    if not task_id or not siswa_id:
        return None
    ws_nilai = get_nilai_tugas_worksheet()
    sudah = any(kunci_nilai_penugasan(r) == (task_id, siswa_id) for r in baca_nilai_tugas_terpadu(refresh=True))
    nilai_aman = max(1, min(100, int(round(float(nilai)))))
    if not sudah:
        ws_nilai.append_row([
            "NIL-" + uuid.uuid4().hex[:10].upper(), task_id, siswa_id, PENILAI_OTOMATIS,
            nilai_aman, 100, "Dinilai otomatis (soal objektif). Pembahasan bersama tutor.",
            waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
        ], value_input_option="RAW")
        _baca_values_cache.clear()
    try:
        catat_persetujuan_nilai(f"AUTO-{task_id}-{siswa_id}", task_id, siswa_id,
                                hasil.get("nilai_sementara"), nilai_aman, PENILAI_OTOMATIS,
                                "Nilai otomatis soal objektif")
    except Exception:
        pass  # catatan persetujuan pelengkap; nilai sudah terbit
    ws_j = get_answers_worksheet()
    pembaruan = [
        {"range": f"F{r['_baris']}", "values": [["Sudah Dinilai"]]}
        for r in baca_records_aman(ws_j, refresh=True)
        if str(r.get("ID_Penugasan", "")).strip() == task_id and str(r.get("ID_Siswa", "")).strip() == siswa_id
    ]
    if pembaruan:
        ws_j.batch_update(pembaruan, value_input_option="RAW")
    return nilai_aman


def koreksi_nilai_terbit(id_tugas, id_siswa, nilai_baru, catatan, tutor_id):
    """Tutor memperbarui baris nilai yang sudah terbit (mis. hasil nilai otomatis)."""
    ws = get_nilai_tugas_worksheet()
    for r in baca_records_aman(ws, refresh=True):
        if kunci_nilai_penugasan(r) == (str(id_tugas).strip(), str(id_siswa).strip()):
            baris = int(r["_baris"])
            nilai_aman = max(1, min(100, int(round(float(nilai_baru)))))
            ws.batch_update([
                {"range": f"D{baris}:H{baris}", "values": [[
                    str(tutor_id), nilai_aman, 100, str(catatan or ""),
                    waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")]]},
            ], value_input_option="RAW")
            _baca_values_cache.clear()
            return True
    return False


def tampilkan_hasil_objektif_siswa(daftar_soal, jawaban, id_tugas=None, id_siswa=None):
    """Nilai + benar/salah per nomor untuk siswa. Kunci dan pembahasan TIDAK ditampilkan."""
    if id_tugas and id_siswa:
        try:
            baris_nilai = next((r for r in baca_nilai_tugas_terpadu()
                                if kunci_nilai_penugasan(r) == (str(id_tugas).strip(), str(id_siswa).strip())), None)
        except Exception:
            baris_nilai = None
        if baris_nilai:
            st.metric("Nilai", f"{baris_nilai.get('Nilai', '-')}/{baris_nilai.get('Nilai_Maksimal', 100) or 100}")
            if str(baris_nilai.get("Umpan_Balik", "")).strip() and PENILAI_OTOMATIS not in str(baris_nilai.get("ID_Tutor_Penilai", "")):
                st.caption("💬 Komentar tutor: " + str(baris_nilai.get("Umpan_Balik")))
    jawaban = jawaban if isinstance(jawaban, dict) else {}
    hasil = hitung_nilai_objektif(daftar_soal, jawaban)
    if not hasil.get("rincian"):
        return
    st.markdown("**📋 Hasil per soal**")
    baris = []
    for x in hasil["rincian"]:
        jw = jawaban.get(str(x["nomor"]), "")
        if isinstance(jw, (list, dict)):
            jw = ", ".join(map(str, jw.values() if isinstance(jw, dict) else jw))
        jw_txt = rapikan_rumus(jw) if str(jw).strip() else "(kosong)"
        if x["poin"] >= 0.999:
            baris.append(f"✅ **No. {x['nomor']}** benar")
        elif x["poin"] > 0:
            baris.append(f"🟡 **No. {x['nomor']}** sebagian benar — jawabanmu: {jw_txt}")
        else:
            baris.append(f"❌ **No. {x['nomor']}** salah — jawabanmu: {jw_txt}")
    st.markdown("  \n".join(baris))
    st.caption("Kunci dan pembahasan akan dibahas bersama tutor.")
    if hasil.get("soal_manual"):
        st.caption("Soal nomor " + ", ".join(map(str, hasil["soal_manual"])) + " menunggu pemeriksaan tutor.")


def normalisasi_opsi(teks):
    if not teks:
        return []
    return [x.strip() for x in str(teks).split("|") if x.strip()]


def simpan_tugas_dan_soal(
    nama_siswa, mapel, instruksi, timer, daftar_soal,
    file_info="", tutor=""
):
    """Simpan tugas dengan ID unik. Data soal disimpan sebagai JSON di kolom Soal_JSON."""
    ws = get_or_create_worksheet(
        "Tugas_Sesi_Siswa",
        [
            "ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Instruksi",
            "File_Offline", "Timer_Menit", "Soal_JSON", "Status_Tugas", "Tutor"
        ],
        cols="20"
    )

    # Jika sheet lama masih memakai 5 kolom, tambahkan header baru tanpa menghapus data.
    headers = ws.row_values(1)
    required = [
        "ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Instruksi",
        "File_Offline", "Timer_Menit", "Soal_JSON", "Status_Tugas", "Tutor"
    ]
    if headers != required:
        # Sheet lama tetap dipertahankan; buat sheet versi baru agar data lama tidak bergeser.
        ws = get_or_create_worksheet(
            "Tugas_Sesi_Siswa_v2",
            required,
            cols="20"
        )

    id_tugas = "TGS-" + uuid.uuid4().hex[:10].upper()
    ws.append_row([
        id_tugas,
        waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
        nama_siswa,
        mapel,
        instruksi,
        file_info,
        timer,
        json.dumps(daftar_soal, ensure_ascii=False),
        "Diberikan",
        tutor
    ])
    return id_tugas


# =========================================================
# PENUGASAN: TUGAS SESI, PR, MATERI. Mendukung banyak tugas / banyak kali penugasan.
# Kategori disimpan di kolom Jenis_Tugas (struktur sheet TIDAK berubah):
#   "Online" / "Offline"            -> tugas sesi
#   "PR Online" / "PR Offline"      -> pekerjaan rumah (punya tenggat)
#   "Materi Tambahan"               -> bahan bacaan (tidak perlu dikerjakan)
# =========================================================
KATEGORI_SESI = "📝 Tugas sesi (dikerjakan saat belajar)"
KATEGORI_PR = "📌 PR (dikerjakan di rumah)"
SUMBER_BANK = "Bank Soal Bersama (Spreadsheet)"
SUMBER_DRIVE = "Link Google Drive / Flipbook"
SUMBER_UPLOAD = "Upload dari perangkat"
SUMBER_BERKAS = "Bank Berkas Soal (PDF/Gambar)"


TASK_MODE_MATERI = "Materi saja"
TASK_MODE_ONLINE = "Tugas online"
TASK_MODE_UPLOAD = "Tugas upload"  # kompatibilitas data lama
TASK_MODE_OFFLINE = "Tugas offline"
TASK_META_KEY = "_nazma_task_meta"


def reset_mode_pengerjaan_widget(widget_key):
    """Hapus pilihan mode dan konfigurasi sumber ketika sumber soal berubah."""
    st.session_state.pop(f"mode_{widget_key}", None)
    st.session_state.pop(f"mode_pengerjaan_{widget_key}", None)


def bungkus_soal_dengan_mode(daftar_soal, mode, daftar_mapel=None, unggah_oleh=None):
    """Simpan mode dan daftar mapel sebagai metadata tanpa mengubah header sheet lama."""
    soal = [dict(x) for x in (daftar_soal or []) if isinstance(x, dict)]
    mapel_aman = []
    for nama in (daftar_mapel or []):
        nama = str(nama or "").strip()
        if nama and nama not in mapel_aman:
            mapel_aman.append(nama)
    meta = {TASK_META_KEY: {"mode": mode, "daftar_mapel": mapel_aman}}
    if mode == TASK_MODE_OFFLINE and str(unggah_oleh or "").strip().lower() in ("siswa", "tutor"):
        meta[TASK_META_KEY]["unggah_oleh"] = str(unggah_oleh).strip().lower()
    return [meta] + soal


def daftar_mapel_tugas(t):
    """Ambil daftar mapel dari metadata baru; fallback ke kolom Mapel lama."""
    try:
        data = json.loads(t.get("Soal_JSON", "") or "[]")
        if isinstance(data, list) and data and isinstance(data[0], dict):
            meta = data[0].get(TASK_META_KEY, {})
            daftar = meta.get("daftar_mapel", []) if isinstance(meta, dict) else []
            daftar = [str(x).strip() for x in daftar if str(x).strip()]
            if daftar:
                return daftar
    except Exception:
        pass
    satu = str(t.get("Mapel", "") or "").strip()
    return [satu] if satu else []


def buka_soal_dan_mode(nilai_json, jenis_tugas=""):
    """Baca metadata mode dan tetap kompatibel dengan Soal_JSON versi lama."""
    try:
        data = json.loads(nilai_json) if nilai_json else []
    except (ValueError, TypeError):
        data = []
    if not isinstance(data, list):
        return [], (TASK_MODE_MATERI if str(jenis_tugas).lower().startswith("materi") else TASK_MODE_UPLOAD)
    mode = ""
    if data and isinstance(data[0], dict) and TASK_META_KEY in data[0]:
        meta = data.pop(0).get(TASK_META_KEY, {})
        mode = str(meta.get("mode", "")).strip() if isinstance(meta, dict) else ""
    if not mode:
        if str(jenis_tugas).lower().startswith("materi"):
            mode = TASK_MODE_MATERI
        elif data:
            mode = TASK_MODE_ONLINE
        else:
            mode = TASK_MODE_UPLOAD
    if mode not in (TASK_MODE_MATERI, TASK_MODE_ONLINE, TASK_MODE_UPLOAD, TASK_MODE_OFFLINE):
        mode = TASK_MODE_UPLOAD
    return data, mode


def mode_tugas(t):
    mode_sheet = str(t.get("Mode_Pengerjaan", "") or "").strip()
    daftar_soal, mode_json = buka_soal_dan_mode(t.get("Soal_JSON", ""), t.get("Jenis_Tugas", ""))
    # Kompatibilitas: tugas lama yang tersimpan sebagai mode upload tetapi sudah
    # memiliki daftar soal dialihkan ke lembar jawaban online. Baris lama tanpa
    # daftar soal tetap memakai alur upload lama agar data historis tidak rusak.
    if mode_sheet == TASK_MODE_UPLOAD and daftar_soal:
        return TASK_MODE_ONLINE
    if mode_sheet in (TASK_MODE_MATERI, TASK_MODE_ONLINE, TASK_MODE_UPLOAD, TASK_MODE_OFFLINE):
        return mode_sheet
    return mode_json


def adalah_pr(t):
    return str(t.get("Jenis_Tugas", "")).strip().lower().startswith("pr")


def adalah_materi(t):
    return mode_tugas(t) == TASK_MODE_MATERI or str(t.get("Jenis_Tugas", "")).strip().lower().startswith("materi")


def parse_tanggal(teks):
    try:
        return datetime.strptime(str(teks).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def label_status(t, status_by_task, nilai_keys, sesi_by_task=None):
    """Kembalikan status tugas; nilai dicocokkan dengan ID penugasan + ID siswa."""
    tid = str(t.get("ID_Tugas", "")).strip()
    sid = str(t.get("ID_Siswa", "")).strip()
    s = str(status_by_task.get(tid, "")).lower()
    sudah_dinilai = (tid, sid) in (nilai_keys or set()) or tid in (nilai_keys or set())
    if sudah_dinilai or "dinilai" in s:
        return "dinilai", "✅ Sudah dinilai"
    if "dikirim" in s or "menunggu" in s:
        return "dikirim", "📤 Dikirim"
    if adalah_materi(t):
        return "materi", "📖 Materi"
    tgl = parse_tanggal(t.get("Tenggat"))
    terlambat = tgl is not None and tgl < waktu_lokal().date()
    if s == "draft":
        return "draft", ("⚠️ Terlambat (draft)" if terlambat else "✏️ Draft")
    sesi = str((sesi_by_task or {}).get(tid, "")).strip().lower()
    if sesi == "aktif":
        return "berjalan", "⏳ Sedang mengerjakan"
    if sesi == "kedaluwarsa":
        return "habis", "⏰ Waktu habis, belum mengirim"
    return "belum", ("⚠️ Terlambat" if terlambat else "🆕 Belum dikerjakan")



FOCUS_ALERT_HEADERS = [
    "ID_Event", "Waktu_Server", "ID_Siswa", "ID_Tugas", "Nama_Tugas",
    "ID_Tutor", "Tutor", "Jumlah_Kejadian", "Jenis_Kejadian", "Status_Telegram"
]


def get_focus_alert_worksheet():
    """Log Focus Alert terpisah; tidak mengubah struktur sheet tugas/jawaban."""
    ws = get_or_create_worksheet(
        "Riwayat_Focus_Alert", FOCUS_ALERT_HEADERS,
        rows="5000", cols=str(len(FOCUS_ALERT_HEADERS))
    )
    actual = [str(x).strip() for x in ws.row_values(1)]
    if actual != FOCUS_ALERT_HEADERS:
        raise ValueError(
            "Header Riwayat_Focus_Alert tidak sesuai. Data tidak ditulis. "
            "Header yang dibutuhkan: " + ", ".join(FOCUS_ALERT_HEADERS)
        )
    return ws


TELEGRAM_TUTOR_HEADERS = ["ID_Tutor", "Chat_ID", "Waktu_Diperbarui"]


def simpan_chat_id_tutor(tutor_id, chat_id):
    """Simpan Chat ID pribadi tutor berdasarkan ID_Tutor; token bot tetap di Secrets."""
    tid = str(tutor_id or "").strip()
    cid = str(chat_id or "").strip()
    if not tid:
        return False, "ID tutor tidak ditemukan. Silakan login ulang."
    if not cid or not re.fullmatch(r"-?\d+", cid):
        return False, "Chat ID harus berupa angka."
    try:
        ws = get_or_create_worksheet(
            "Telegram_Tutor", TELEGRAM_TUTOR_HEADERS,
            rows="500", cols=str(len(TELEGRAM_TUTOR_HEADERS))
        )
        headers = [str(x).strip() for x in ws.row_values(1)]
        if headers != TELEGRAM_TUTOR_HEADERS:
            return False, "Header sheet Telegram_Tutor tidak sesuai. Jangan ubah data otomatis."
        records = baca_records_aman(ws, refresh=True)
        baris = next((int(r.get("_baris", 0)) for r in records
                      if str(r.get("ID_Tutor", "")).strip() == tid), 0)
        values = [tid, cid, waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")]
        if baris >= 2:
            ws.update(f"A{baris}:C{baris}", [values], value_input_option="RAW")
        else:
            ws.append_row(values, value_input_option="RAW")
        _baca_values_cache.clear()
        return True, "Chat ID tersimpan. Silakan kirim pesan uji."
    except Exception as exc:
        return False, f"Gagal menyimpan Chat ID: {exc.__class__.__name__}"


def ambil_chat_id_tutor_sheet(tutor_id):
    tid = str(tutor_id or "").strip()
    if not tid:
        return ""
    try:
        ws = get_worksheet("Telegram_Tutor")
        rows = baca_records_aman(ws, refresh=True)
        rec = next((r for r in rows if str(r.get("ID_Tutor", "")).strip() == tid), None)
        return str((rec or {}).get("Chat_ID", "")).strip()
    except gspread.WorksheetNotFound:
        return ""
    except Exception:
        return ""


def _konfigurasi_telegram(tutor_id):
    """Konfigurasi notifikasi umum; perilaku lama dipertahankan."""
    cfg = st.secrets.get("telegram", {})
    bot_token = str(cfg.get("bot_token", "")).strip()
    if not bot_token:
        return "", "", "BELUM_DIKONFIGURASI"
    penerima = str(cfg.get("default_chat_id", "")).strip()
    try:
        peta_tutor = cfg.get("tutor_chat_ids", {})
        tid = str(tutor_id or "").strip()
        if tid and peta_tutor and str(peta_tutor.get(tid, "")).strip():
            penerima = str(peta_tutor.get(tid, "")).strip()
    except Exception:
        pass
    if not penerima:
        return bot_token, "", "CHAT_ID_BELUM_DIATUR"
    return bot_token, penerima, ""


def _konfigurasi_telegram_focus(tutor_id):
    """Focus Alert wajib memakai Chat ID pribadi tutor, tanpa fallback ke chat default."""
    cfg = st.secrets.get("telegram", {})
    bot_token = str(cfg.get("bot_token", "")).strip()
    if not bot_token:
        return "", "", "BELUM_DIKONFIGURASI"
    tid = str(tutor_id or "").strip()
    penerima = ambil_chat_id_tutor_sheet(tid) if tid else ""
    if not penerima:
        try:
            peta_tutor = cfg.get("tutor_chat_ids", {})
            if tid and peta_tutor:
                penerima = str(peta_tutor.get(tid, "")).strip()
        except Exception:
            pass
    if not penerima:
        return bot_token, "", "CHAT_ID_TUTOR_BELUM_DIDAFTARKAN"
    return bot_token, penerima, ""


def _konfigurasi_telegram_tugas(tutor_id):
    """Bot khusus notifikasi 'tugas selesai dikirim' ([telegram_tugas] di Secrets) supaya bunyinya bisa
    dibedakan dari bot Focus Alert. Chat ID tutor sama; bila bot khusus belum diisi, memakai bot lama."""
    token_focus, penerima, alasan = _konfigurasi_telegram_focus(tutor_id)
    token_tugas = ""
    try:
        token_tugas = str(st.secrets.get("telegram_tugas", {}).get("bot_token", "")).strip()
    except Exception:
        token_tugas = ""
    if token_tugas:
        return token_tugas, penerima, ("" if penerima else "CHAT_ID_TUTOR_BELUM_DIDAFTARKAN"), True
    return token_focus, penerima, alasan, False


def kirim_telegram_pesan(bot_token, chat_id, teks):
    """(berhasil, keterangan). Keterangan hanya berisi respons Telegram, tidak pernah token."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={"chat_id": chat_id, "text": teks, "disable_web_page_preview": True, "disable_notification": False},
            timeout=10
        )
    except requests.exceptions.RequestException as exc:
        return False, f"koneksi gagal ({exc.__class__.__name__})"
    try:
        hasil = r.json()
    except ValueError:
        hasil = {}
    if r.ok and hasil.get("ok"):
        return True, "TERKIRIM"
    deskripsi = str(hasil.get("description", "tanpa keterangan"))[:120]
    if r.status_code == 404:
        return False, "HTTP 404: endpoint/token bot tidak ditemukan. Periksa ulang telegram.bot_token di Streamlit Secrets; jangan ubah Chat ID dulu."
    if r.status_code == 401:
        return False, "HTTP 401: token bot ditolak. Periksa token dari BotFather di Streamlit Secrets."
    return False, f"HTTP {r.status_code}: {deskripsi}"


def kirim_telegram_focus_alert(evento, task_info=None):
    """Kirim notifikasi server-side. Mengembalikan status singkat untuk dicatat di log."""
    try:
        task_info = task_info or {}
        bot_token, penerima, alasan = _konfigurasi_telegram_focus(
            task_info.get("ID_Tutor", "")
        )
        if alasan:
            return alasan
        siswa_id = str(evento.get("student_id", "")).strip()
        nama = str(task_info.get("Nama_Siswa", "")).strip() or siswa_id
        judul = str(task_info.get("Judul_Tugas", "Tugas siswa")).strip() or "Tugas siswa"
        task_id = str(task_info.get("ID_Tugas", evento.get("task_id", ""))).strip()
        jumlah = int(evento.get("count", 1) or 1)
        pesan = (
            "🚨 NAZMA FOCUS ALERT\n"
            "Siswa meninggalkan halaman pengerjaan.\n\n"
            f"Siswa: {nama} ({siswa_id})\n"
            f"Tugas: {judul}\n"
            f"ID Tugas: {task_id}\n"
            f"Jumlah kejadian pada perangkat ini: {jumlah} kali\n"
            f"Waktu: {waktu_lokal().strftime('%d-%m-%Y %H:%M:%S')} WIB\n\n"
            "Catatan: ini bukan bukti otomatis menyontek; periksa konteksnya."
        )
        ok, ket = kirim_telegram_pesan(bot_token, penerima, pesan)
        return "TERKIRIM" if ok else f"GAGAL_TELEGRAM: {ket}"[:150]
    except Exception as exc:
        return f"GAGAL_TELEGRAM: {exc.__class__.__name__}"


def kirim_telegram_notifikasi_pengiriman(task_id, student_id, jenis="jawaban"):
    """Beritahu tutor saat siswa berhasil mengirim jawaban/lampiran; gagal notifikasi tidak membatalkan kiriman."""
    try:
        try:
            tugas_rows = baca_records_aman(get_worksheet("Tugas_Sesi_Siswa_v2"), refresh=True)
        except gspread.WorksheetNotFound:
            tugas_rows = get_student_tasks()
        tugas = next((
            t for t in tugas_rows
            if str(t.get("ID_Tugas", "")).strip() == str(task_id or "").strip()
        ), None)
        if not tugas:
            return False, "Data tugas tidak ditemukan untuk notifikasi."
        tutor_id = str(tugas.get("ID_Tutor", "")).strip()
        tutor_nama = str(tugas.get("Tutor", "")).strip()
        bot_token, chat_id, alasan, _bot_khusus = _konfigurasi_telegram_tugas(tutor_id)
        if alasan:
            return False, alasan
        siswa_id = str(student_id or "").strip()
        nama_siswa = str(tugas.get("Nama_Siswa", "")).strip() or siswa_id
        judul = str(tugas.get("Judul_Tugas", "Tugas siswa")).strip() or "Tugas siswa"
        try:
            jumlah_pelanggaran = hitung_pelanggaran_fokus(refresh=True).get(
                (str(task_id or "").strip(), siswa_id), 0
            )
        except Exception:
            jumlah_pelanggaran = 0
        baris_pelanggaran = (
            f"🚨 Pelanggaran keluar tab: {teks_pelanggaran(jumlah_pelanggaran)}\n"
            if jumlah_pelanggaran else "✅ Pelanggaran keluar tab: 0 kali\n"
        )
        pesan = (
            "🔔 NAZMA — TUGAS SELESAI DIKIRIM\n\n"
            f"Siswa: {nama_siswa} ({siswa_id})\n"
            f"Tugas: {judul}\n"
            f"Jenis kiriman: {jenis}\n"
            f"{baris_pelanggaran}"
            f"Tutor: {tutor_nama or tutor_id}\n"
            f"Waktu: {waktu_lokal().strftime('%d-%m-%Y %H:%M:%S')} WIB\n\n"
            "Silakan buka Portal Tutor → Portofolio Siswa → Jawaban yang menunggu pemeriksaan."
        )
        # disable_notification=False meminta notifikasi normal Telegram.
        return kirim_telegram_pesan(bot_token, chat_id, pesan)
    except Exception as exc:
        return False, f"Notifikasi gagal: {exc.__class__.__name__}"


def uji_telegram_tugas(tutor_id, tutor_nama):
    """Pesan uji untuk bot notifikasi tugas. Tutor harus menekan Start di bot ini lebih dulu."""
    try:
        bot_token, penerima, alasan, bot_khusus = _konfigurasi_telegram_tugas(tutor_id)
    except Exception as exc:
        return False, f"Konfigurasi Secrets tidak terbaca: {exc.__class__.__name__}"
    if alasan:
        return False, "Chat ID pribadi belum didaftarkan atau bot belum dikonfigurasi. Isi Chat ID di atas lalu Simpan Chat ID."
    if not bot_khusus:
        return False, "Bagian [telegram_tugas] dengan bot_token belum terbaca di Secrets, jadi masih memakai bot lama."
    ok, ket = kirim_telegram_pesan(
        bot_token, penerima,
        f"✅ Tes bot Notifikasi Tugas Nazma untuk {tutor_nama or 'tutor'}. Pesan ini muncul saat siswa selesai mengirim tugas."
    )
    if ok:
        return True, "Pesan uji bot tugas terkirim. Periksa Telegram Anda."
    if "403" in ket or "chat not found" in ket.lower() or "400" in ket:
        return False, f"{ket}. Buka bot tugas di Telegram lalu tekan Start/kirim satu pesan, kemudian coba lagi."
    return False, ket


def uji_telegram_tutor(tutor_id, tutor_nama):
    """Kirim pesan uji dan jelaskan penyebab bila gagal. Mengembalikan (berhasil, pesan)."""
    try:
        bot_token, penerima, alasan = _konfigurasi_telegram_focus(tutor_id)
    except Exception as exc:
        return False, f"Konfigurasi Secrets tidak terbaca: {exc.__class__.__name__}"
    if alasan == "BELUM_DIKONFIGURASI":
        return False, "Bagian [telegram] dengan bot_token belum ada di Secrets Streamlit."
    if alasan == "CHAT_ID_TUTOR_BELUM_DIDAFTARKAN":
        return False, "Chat ID pribadi belum didaftarkan. Isi Chat ID pada Pengaturan Akun lalu tekan Simpan Chat ID."
    ok, ket = kirim_telegram_pesan(
        bot_token, penerima,
        f"✅ Tes notifikasi Nazma untuk {tutor_nama or 'tutor'}. Jika pesan ini masuk, Focus Alert siap dipakai."
    )
    if ok:
        return True, "Pesan uji terkirim. Periksa Telegram Anda."
    petunjuk = ""
    k = ket.lower()
    if "404" in k or "endpoint/token bot tidak ditemukan" in k:
        petunjuk = " Periksa token bot pada Streamlit Secrets: pastikan tidak terpotong, tidak ada karakter tambahan, dan berasal dari BotFather. Chat ID bukan penyebab utama HTTP 404."
    elif "unauthorized" in k or "401" in k:
        petunjuk = " Token bot salah atau sudah dicabut."
    elif "chat not found" in k or "400" in k:
        petunjuk = " Chat ID salah, atau Anda belum menekan Start pada bot."
    elif "blocked" in k or "403" in k:
        petunjuk = " Bot diblokir atau belum di-Start oleh penerima."
    elif "koneksi" in k:
        petunjuk = " Server tidak dapat menjangkau Telegram."
    return False, f"Pesan uji gagal ({ket})." + petunjuk


def catat_focus_alert_server(evento, task_info=None):
    """Kirim Telegram lebih dulu, lalu catat log. Kegagalan log tidak boleh menahan notifikasi."""
    task_info = task_info or {}
    status_telegram = kirim_telegram_focus_alert(evento, task_info)
    try:
        ws = get_focus_alert_worksheet()
        ws.append_row([
            str(evento.get("event_id", "")),
            waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
            str(evento.get("student_id", "")),
            str(task_info.get("ID_Tugas", evento.get("task_id", ""))),
            str(task_info.get("Judul_Tugas", "")),
            str(task_info.get("ID_Tutor", "")),
            str(task_info.get("Tutor", "")),
            int(evento.get("count", 1) or 1),
            str(evento.get("event_type", "tab_hidden_return")),
            status_telegram
        ], value_input_option="RAW")
    except Exception as exc:
        st.session_state["_focus_log_galat"] = str(exc)[:160]
    return status_telegram


def hitung_pelanggaran_fokus(refresh=False):
    """Jumlah pelanggaran keluar tab per (ID_Tugas, ID_Siswa), dihitung dari Riwayat_Focus_Alert.
    Tiap ID_Event dihitung sekali. Jika log tidak terbaca, hasilnya kosong agar laporan nilai tetap tampil."""
    try:
        ws = get_or_create_worksheet(
            "Riwayat_Focus_Alert", FOCUS_ALERT_HEADERS, rows="5000", cols=str(len(FOCUS_ALERT_HEADERS))
        )
        rows = baca_records_aman(ws, refresh=refresh)
    except Exception:
        return {}
    kejadian = {}
    for r in rows:
        id_tugas = str(r.get("ID_Tugas", "")).strip()
        id_siswa = str(r.get("ID_Siswa", "")).strip()
        if not id_tugas or not id_siswa:
            continue
        id_event = str(r.get("ID_Event", "")).strip() or f"baris-{r.get('_baris', len(kejadian))}"
        try:
            jumlah = max(1, int(float(r.get("Jumlah_Kejadian", 1) or 1)))
        except (ValueError, TypeError):
            jumlah = 1
        kejadian.setdefault((id_tugas, id_siswa), {})[id_event] = jumlah
    # Jumlah kejadian unik, atau hitungan berjalan tertinggi bila ada baris log yang gagal tertulis.
    return {k: max(len(v), max(v.values())) for k, v in kejadian.items()}


def teks_pelanggaran(jumlah):
    return f"{int(jumlah or 0)} kali"


def tampilkan_peringatan_fokus(tutor_id, tutor_nama, interval_detik=INTERVAL_PENYEGARAN_TUTOR, menit=120):
    """Riwayat peringatan fokus terbaru untuk tutor, juga bila Telegram gagal. Menyegar otomatis."""
    def _isi():
        try:
            ws = get_or_create_worksheet("Riwayat_Focus_Alert", FOCUS_ALERT_HEADERS, rows="5000", cols=str(len(FOCUS_ALERT_HEADERS)))
            rows = baca_records_aman(ws, refresh=True)
            tugas = {str(t.get("ID_Tugas", "")).strip(): t for t in get_student_tasks()}
        except Exception as exc:
            st.caption(f"Riwayat peringatan fokus belum dapat dibaca: {exc}")
            return
        batas = waktu_lokal().replace(tzinfo=None) - timedelta(minutes=menit)
        tid = str(tutor_id or "").strip()
        tampil = []
        for r in rows:
            try:
                waktu = datetime.strptime(str(r.get("Waktu_Server", "")).strip()[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            tg = tugas.get(str(r.get("ID_Tugas", "")).strip(), {})
            pemilik = str(r.get("ID_Tutor", "")).strip() or str(tg.get("ID_Tutor", "")).strip()
            if waktu < batas or not tid or pemilik != tid:
                continue
            tampil.append({
                "Waktu": waktu.strftime("%H:%M:%S"),
                "Siswa": str(tg.get("Nama_Siswa", "")).strip() or str(r.get("ID_Siswa", "")),
                "Tugas": r.get("Nama_Tugas", "") or tg.get("Judul_Tugas", ""),
                "Kejadian": r.get("Jumlah_Kejadian", ""),
                "Telegram": r.get("Status_Telegram", ""),
            })
        tampil.sort(key=lambda x: x["Waktu"], reverse=True)
        judul = f"🚨 Peringatan fokus dalam {menit // 60} jam terakhir ({len(tampil)})"
        with st.expander(judul, expanded=bool(tampil)):
            if tampil:
                st.dataframe(pd.DataFrame(tampil[:10]), use_container_width=True, hide_index=True)
            else:
                st.caption("Belum ada siswa yang meninggalkan halaman pengerjaan.")
            if NAZMA_FOCUS_COMPONENT is None:
                st.warning("Pendeteksi keluar halaman tidak aktif: folder komponen nazma_focus_component tidak ditemukan di aplikasi.")

    if hasattr(st, "fragment"):
        try:
            st.fragment(run_every=f"{int(interval_detik)}s")(_isi)()
            return
        except TypeError:
            pass
    _isi()


def tampilkan_nazma_focus_alert(task_id, siswa_id, task_info=None):
    """Focus Alert browser -> event component -> backend -> Telegram + Google Sheets."""
    task_info = task_info or {}
    event = _komponen_fokus_aman(
        task_id=str(task_id),
        student_id=str(siswa_id),
        enabled=True,
        key=f"nazma_focus_{re.sub(r'[^A-Za-z0-9_-]', '_', str(siswa_id))}_{re.sub(r'[^A-Za-z0-9_-]', '_', str(task_id))}",
        default=None
    )
    if isinstance(event, dict):
        event_id = str(event.get("event_id", "")).strip()
        if event_id:
            seen_key = "_nazma_focus_events_processed"
            seen = st.session_state.setdefault(seen_key, [])
            if event_id not in seen:
                # Tandai sebelum I/O agar rerun tidak mengirim notifikasi ganda.
                seen.append(event_id)
                st.session_state[seen_key] = seen[-200:]
                try:
                    catat_focus_alert_server(event, task_info)
                except Exception:
                    # Kegagalan pencatatan tidak mengganggu timer atau pengerjaan siswa.
                    pass

_CSS_KARTU_TUGAS = """
<style>
.kt{display:flex;gap:14px;align-items:center;border-radius:16px;padding:14px 16px;margin:14px 0 4px 0;border:2px solid #cfe0ff;background:#f3f8ff}
.kt .kt-ik{font-size:2.4rem;line-height:1}
.kt .kt-jd{font-size:1.1rem;font-weight:800;color:#13315c;line-height:1.25}
.kt .kt-mp{font-size:.9rem;color:#4a5d7a;margin-top:2px}
.kt .kt-st{display:inline-block;font-size:.8rem;font-weight:700;border-radius:999px;padding:2px 10px;margin-top:6px;background:#e3eefc;color:#13315c}
.kt .kt-tg{font-size:.82rem;font-weight:700;margin-top:6px}
.kt-merah{background:#fff1f0;border-color:#ffb3ad}.kt-merah .kt-tg{color:#c0261b}
.kt-kuning{background:#fff8e6;border-color:#ffd98a}.kt-kuning .kt-tg{color:#9a6200}
.kt-hijau{background:#effaf1;border-color:#b5e3bd}.kt-hijau .kt-tg{color:#1f7a34}
.kt-abu{background:#f4f5f7;border-color:#dfe2e8;opacity:.9}.kt-abu .kt-tg{color:#667085}
[class*="st-key-kerjakan_"] details>summary{background:#1e6fd9;color:#fff;border-radius:12px;font-weight:800;padding:.7rem 1rem}
[class*="st-key-kerjakan_"] details>summary p,[class*="st-key-kerjakan_"] details>summary span{color:#fff!important;font-size:1.05rem}
[class*="st-key-kerjakan_"] details>summary svg{fill:#fff;color:#fff}
[class*="st-key-lihat_"] details>summary{background:#eef1f6;border-radius:12px}
</style>
"""


def _kartu_depan_html(t, kode, label, mapel_txt, judul, ikon, tenggat):
    import html as _h
    selesai = kode in ("dikirim", "dinilai")
    warna, info_tg = ("kt-abu" if selesai else "kt-hijau"), ""
    tgl = parse_tanggal(tenggat) if tenggat and not adalah_materi(t) else None
    if tgl is not None and not selesai:
        sisa = (tgl - waktu_lokal().date()).days
        if sisa < 0:
            warna, info_tg = "kt-merah", "⏰ Sudah lewat tenggat, kerjakan sekarang ya!"
        elif sisa == 0:
            warna, info_tg = "kt-merah", "⏰ Tenggat HARI INI"
        elif sisa <= 2:
            warna, info_tg = "kt-kuning", f"🕒 Tenggat {sisa} hari lagi"
        else:
            info_tg = f"📅 Tenggat {_h.escape(str(tenggat)[:16])}"
    elif tenggat and not adalah_materi(t):
        info_tg = f"📅 Tenggat {_h.escape(str(tenggat)[:16])}"
    return (
        f'<div class="kt {warna}"><div class="kt-ik">{ikon}</div><div>'
        f'<div class="kt-jd">{_h.escape(str(judul))}</div>'
        f'<div class="kt-mp">{_h.escape(str(mapel_txt))}</div>'
        f'<span class="kt-st">{_h.escape(str(label))}</span>'
        + (f'<div class="kt-tg">{info_tg}</div>' if info_tg else "") + '</div></div>'
    )


def tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids, sesi_aktif_page=None):
    """Satu kartu tugas/PR untuk siswa. Setiap tugas menyimpan jawabannya sendiri
    (tidak saling menimpa), dan terkunci setelah dikirim."""
    task_id = str(t.get("ID_Tugas", "")).strip()
    siswa_id = st.session_state.get("siswa_id", "")
    kode, label = label_status(t, status_by_task, nilai_ids)
    terkunci = kode in ("dikirim", "dinilai")
    ikon = "📌" if adalah_pr(t) else ("📖" if adalah_materi(t) else ("🗒️" if mode_tugas(t) == TASK_MODE_OFFLINE else "📝"))
    judul = t.get("Judul_Tugas") or t.get("Instruksi") or "Tugas"
    tenggat = str(t.get("Tenggat", "")).strip()
    tambahan = f" · tenggat {tenggat}" if tenggat and not adalah_materi(t) else ""

    # Pertahankan kartu tetap terbuka setelah tombol Mulai memicu st.rerun().
    # Cek sesi dari server juga agar kartu terbuka kembali setelah refresh halaman.
    expander_state_key = f"_buka_kartu_tugas_{task_id}"
    sesi_awal = sesi_aktif_page if siswa_id else None
    sesi_tugas_ini_awal = bool(
        sesi_awal and str(sesi_awal.get("ID_Tugas", "")).strip() == task_id
        and str(sesi_awal.get("Status", "")).strip().lower() == "aktif"
    )
    kartu_terbuka = bool(st.session_state.get(expander_state_key, False) or sesi_tugas_ini_awal)

    label_mapel_tugas = ", ".join(daftar_mapel_tugas(t)) or t.get("Mapel", "Mapel")
    st.markdown(_CSS_KARTU_TUGAS + _kartu_depan_html(t, kode, label, label_mapel_tugas, judul, ikon, tenggat),
                unsafe_allow_html=True)
    if adalah_materi(t):
        _label_buka, _awalan = "📖 Buka materi", "lihat_"
    elif terkunci:
        _label_buka, _awalan = "🔎 Lihat tugas & hasil", "lihat_"
    elif kode == "draft":
        _label_buka, _awalan = "▶ Lanjutkan mengerjakan", "kerjakan_"
    else:
        _label_buka, _awalan = "▶ Kerjakan sekarang", "kerjakan_"
    try:
        _wadah_kartu = st.container(key=f"{_awalan}{task_id}")
    except TypeError:  # versi Streamlit lama tanpa parameter key
        _wadah_kartu = st.container()
    with _wadah_kartu, st.expander(_label_buka, expanded=kartu_terbuka):
        timer_txt = str(t.get("Timer_Menit", "")).strip()
        st.write(f"**Instruksi Tutor:** {t.get('Instruksi') or '-'}")
        st.write(f"**Diberikan:** {t.get('Tanggal') or '-'}")
        if tenggat and not adalah_materi(t):
            st.write(f"**Tenggat:** {tenggat}")
        if not adalah_materi(t):
            st.write(f"**Durasi:** {'Tanpa timer' if timer_txt in ('', '0') else timer_txt + ' menit'}")

        tahan_lampiran = bool(
            timer_txt not in ("", "0") and not terkunci and not adalah_materi(t)
            and mode_tugas(t) in (TASK_MODE_ONLINE, TASK_MODE_OFFLINE)
            and not sesi_tugas_ini_awal
        )
        if t.get("File_Offline"):
            st.markdown("### 📎 Soal / Lampiran Tugas")
            if tahan_lampiran:
                st.info("🔒 Soal terbuka setelah kamu menekan Mulai Mengerjakan.")
            else:
                tampilkan_materi(t.get("File_Offline"))

        soal_json = str(t.get("Soal_JSON", "") or "")
        daftar_soal, _mode_json_lama = buka_soal_dan_mode(soal_json, t.get("Jenis_Tugas", ""))
        mode_pengerjaan = mode_tugas(t)

        if mode_pengerjaan == TASK_MODE_MATERI:
            sesi_aktif_materi = sesi_aktif_page
            if sesi_aktif_materi:
                st.error("🔒 Materi terkunci selama tugas online sedang dikerjakan. Kumpulkan tugas aktif terlebih dahulu.")
                return
            st.info("Ini materi bacaan dari Tutor, tidak ada yang perlu dikirim.")
        elif mode_pengerjaan == TASK_MODE_ONLINE and daftar_soal:
            sesi_aktif = sesi_aktif_page
            sesi_ini_aktif = bool(sesi_aktif and str(sesi_aktif.get("ID_Tugas", "")).strip() == task_id)
            sesi_lain_aktif = bool(sesi_aktif and not sesi_ini_aktif)
            try:
                waktu_habis_online = (not terkunci) and (not sesi_ini_aktif) and sesi_kedaluwarsa_tugas(siswa_id, task_id)
            except Exception:
                waktu_habis_online = False
            if terkunci:
                st.info("Jawaban sudah dikirim, jadi tidak bisa diubah lagi.")
            elif waktu_habis_online:
                st.error("⏰ Waktu pengerjaan tugas ini sudah habis. Hubungi Tutor bila perlu dibuka kembali.")
                return
            elif sesi_lain_aktif:
                st.warning("Tugas ini terkunci karena kamu sedang mengerjakan tugas online lain. Kumpulkan tugas yang aktif terlebih dahulu.")
                return
            elif not sesi_ini_aktif:
                st.info("Tekan Mulai Mengerjakan jika sudah siap. Setelah dimulai, tugas online lain akan terkunci sampai jawaban dikumpulkan.")
                if st.button("▶️ Mulai Mengerjakan", key=f"mulai_online_{task_id}", type="primary"):
                    ok_mulai, pesan_mulai = mulai_sesi_online(siswa_id, task_id)
                    if ok_mulai:
                        st.session_state[expander_state_key] = True
                        st.success(pesan_mulai)
                        st.rerun()
                    else:
                        st.error(pesan_mulai)
                return
            if not terkunci and sesi_ini_aktif:
                if timer_txt not in ("", "0"):
                    sisa_timer = hitung_sisa_waktu_sesi(sesi_aktif, timer_txt)
                    tampilkan_timer_sisa(sisa_timer, task_id)
                tampilkan_nazma_focus_alert(task_id, siswa_id, t)
            st.markdown("#### 📝 Lembar Jawaban Online")
            file_jawaban = []
            lampiran_lama = baca_lampiran_jawaban(task_id, siswa_id) if terkunci else []
            if terkunci:
                for lamp in lampiran_lama:
                    st.markdown(f"[📎 {lamp.get('Nama_File', 'Lampiran jawaban')}]({lamp.get('URL_Drive', '')})")
            soal_dari_lampiran_awal = str(t.get("Sumber", "") or "").strip() in (SUMBER_UPLOAD, SUMBER_DRIVE, SUMBER_BERKAS)
            old_answer = {}
            for ans in jawaban_siswa:
                if str(ans.get("ID_Tugas", "")) == task_id:
                    try:
                        old_answer = json.loads(ans.get("Jawaban_JSON", "{}") or "{}")
                    except (ValueError, TypeError):
                        old_answer = {}
                    break
            if terkunci:
                st.info("Jawaban sudah dikirim, jadi tidak bisa diubah lagi.")
                if not soal_dari_lampiran_awal:
                    try:
                        tampilkan_hasil_objektif_siswa(daftar_soal, old_answer, task_id, siswa_id)
                    except Exception as _e:
                        st.caption(f"Rincian hasil belum bisa ditampilkan ({_e.__class__.__name__}). Tekan 🔄 Muat ulang data.")
                if st.session_state.get(f"_galat_auto_{task_id}"):
                    st.caption("Nilai otomatis belum terbit; tutor akan memeriksa jawabanmu. "
                               f"(Info teknis: {str(st.session_state[f'_galat_auto_{task_id}'])[:120]})")
                tampilkan_bahan_tutor_siswa(task_id, siswa_id)

            # Untuk tugas yang sumber soalnya berupa PDF/link/lampiran, aplikasi hanya
            # menyediakan lembar jawaban. Pertanyaan dan teks opsi tetap berada di sumber.
            sumber_tugas = str(t.get("Sumber", "") or "").strip()
            soal_dari_lampiran = sumber_tugas in (SUMBER_UPLOAD, SUMBER_DRIVE, SUMBER_BERKAS)
            data_soal_tidak_lengkap = False
            _st_w = {}
            for i, soal in enumerate(daftar_soal, 1):
                qkey = f"student_{task_id}_{i}"
                bentuk = str(soal.get("Bentuk_Soal", "")).lower()
                opsi = soal.get("Opsi_List", [])
                if not isinstance(opsi, list):
                    opsi = []
                teks_tampil = str(soal.get("Teks_Soal", "") or "").strip()
                if teks_tampil:
                    tampil_soal_md(i, teks_tampil, _st_w)
                elif soal_dari_lampiran:
                    st.markdown(f"**{i}. Lihat soal nomor {i} pada lampiran di atas.**")
                else:
                    data_soal_tidak_lengkap = True
                    st.warning(f"Soal nomor {i} belum memiliki teks pertanyaan. Tutor perlu memperbaiki soal ini.")
                    st.markdown(f"**{i}. Teks pertanyaan belum tersedia.**")
                if "pilihan ganda" in bentuk and not soal_dari_lampiran:
                    opsi_hanya_label = bool(opsi) and all(
                        re.fullmatch(r"[A-Da-d][.)]?", str(x).strip()) for x in opsi
                    )
                    if len(opsi) < 2 or opsi_hanya_label:
                        data_soal_tidak_lengkap = True
                        st.warning(f"Pilihan jawaban nomor {i} belum lengkap. Hubungi tutor.")
                if "pilihan ganda" in bentuk and soal_dari_lampiran and len(opsi) < 2:
                    data_soal_tidak_lengkap = True
                    st.warning(f"Label pilihan jawaban nomor {i} belum lengkap. Tutor perlu melengkapi A/B/C/D.")
                if soal.get("Url_Gambar"):
                    st.image(img_url(soal["Url_Gambar"]), use_container_width=True)
                tampilkan_media_soal(soal)

                # Simpan segera setelah perubahan jawaban. Batch berkala tetap menjadi
                # jalur pemulihan jika penyimpanan langsung gagal.
                def _simpan_satu(nilai, question_no=i, tid=task_id):
                    sid_callback = str(st.session_state.get("siswa_id", "")).strip()
                    _tampung_jawaban_draft(
                        tid, sid_callback, {str(question_no): nilai}
                    )
                    ok_simpan, pesan_simpan = _flush_draft_task(
                        tid, sid_callback, paksa=True
                    )
                    if ok_simpan:
                        st.session_state.setdefault("_draft_status_by_task", {})[tid] = "Tersimpan"
                        st.session_state.pop("_galat_simpan", None)
                    else:
                        st.session_state.setdefault("_draft_status_by_task", {})[tid] = "Menunggu penyimpanan"
                        st.session_state["_galat_simpan"] = pesan_simpan

                def _update_answer(question_no=i, widget_key=qkey, tid=task_id):
                    _simpan_satu(st.session_state.get(widget_key, ""), question_no, tid)

                if "pgk mcma" in bentuk or "pilihan ganda kompleks" in bentuk:
                    default_m = old_answer.get(str(i), [])
                    if isinstance(default_m, str):
                        try:
                            default_m = json.loads(default_m)
                        except (ValueError, TypeError):
                            default_m = [default_m]
                    if not isinstance(default_m, list):
                        default_m = []
                    default_m = [x for x in default_m if x in opsi]
                    st.multiselect(f"Pilih jawaban nomor {i}:", opsi, default=default_m,
                                   key=qkey, on_change=_update_answer, disabled=terkunci)
                elif "pgk kategori" in bentuk:
                    tersimpan = old_answer.get(str(i))
                    st.radio(f"Pilih kategori nomor {i}:", opsi, format_func=rapikan_rumus,
                             index=opsi.index(tersimpan) if tersimpan in opsi else None,
                             key=qkey, on_change=_update_answer, disabled=terkunci)
                elif "pilihan ganda" in bentuk:
                    tersimpan = old_answer.get(str(i))
                    st.radio(f"Pilih jawaban nomor {i}:", opsi, format_func=rapikan_rumus,
                             index=opsi.index(tersimpan) if tersimpan in opsi else None,
                             key=qkey, on_change=_update_answer, disabled=terkunci)
                elif "menjodohkan" in bentuk:
                    pasangan = soal.get("Pasangan", {})
                    kiri = pasangan.get("kolom_A", {})
                    kanan = pasangan.get("kolom_B", {})
                    if not kiri or not kanan:
                        st.warning("Data pasangan belum valid.")
                    else:
                        st.caption("Pilih pasangan yang sesuai untuk setiap item.")
                        st.write("**Pilihan Kolom B:** " + " · ".join(f"{k}. {v}" for k, v in kanan.items()))
                        jawaban_lama = old_answer.get(str(i), {})
                        if isinstance(jawaban_lama, str):
                            try:
                                jawaban_lama = json.loads(jawaban_lama)
                            except (ValueError, TypeError):
                                jawaban_lama = {}
                        if not isinstance(jawaban_lama, dict):
                            jawaban_lama = {}

                        def _update_pasangan(question_no=i, tid=task_id, qk=qkey, kodes=list(kiri.keys())):
                            jwb = {}
                            for kd in kodes:
                                v = st.session_state.get(f"{qk}_{kd}", "— Pilih —")
                                jwb[kd] = "" if v == "— Pilih —" else v
                            _simpan_satu(jwb, question_no, tid)

                        jawaban_pasangan = {}
                        for kode_kiri, teks_kiri in kiri.items():
                            pilihan = ["— Pilih —"] + list(kanan.keys())
                            nilai_lama = str(jawaban_lama.get(kode_kiri, "— Pilih —")) or "— Pilih —"
                            pilihan_aktif = st.selectbox(
                                f"{kode_kiri}. {teks_kiri}", pilihan,
                                index=pilihan.index(nilai_lama) if nilai_lama in pilihan else 0,
                                format_func=lambda x, d=kanan: x if x == "— Pilih —" else f"{x}. {d[x]}",
                                key=f"{qkey}_{kode_kiri}", on_change=_update_pasangan, disabled=terkunci)
                            jawaban_pasangan[kode_kiri] = "" if pilihan_aktif == "— Pilih —" else pilihan_aktif
                        st.session_state[qkey] = jawaban_pasangan
                elif "benar" in bentuk:
                    nilai_default = old_answer.get(str(i))
                    pilihan_bs = ["Benar", "Salah"]
                    st.radio(f"Jawaban nomor {i}:", pilihan_bs,
                             index=pilihan_bs.index(nilai_default) if nilai_default in pilihan_bs else None,
                             horizontal=True, key=qkey, on_change=_update_answer, disabled=terkunci)
                else:
                    st.text_area(f"Jawaban nomor {i}:", value=str(old_answer.get(str(i), "")),
                                 key=qkey, on_change=_update_answer, disabled=terkunci)

            # Satu area lampiran bersama untuk seluruh jawaban esai dalam tugas ini.
            # Siswa mengetik jawaban pada lembar online dan melampirkan foto tulisan tangan.
            ada_soal_esai = any(
                any(kata in str(q.get("Bentuk_Soal", "")).lower() for kata in ("esai", "essay", "uraian"))
                for q in daftar_soal
            )
            if ada_soal_esai:
                st.markdown("#### 📷 Foto Jawaban Esai")
                st.caption("Ketik jawaban esai pada kolom online. Foto tulisan tangan bersifat opsional: unggah bila Anda juga menulis jawaban di kertas.")
                if not terkunci:
                    file_jawaban = st.file_uploader(
                        "Unggah foto jawaban esai (opsional):",
                        type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
                        accept_multiple_files=True,
                        key=f"lampiran_online_{task_id}"
                    ) or []
                    if file_jawaban:
                        st.caption(f"{len(file_jawaban)} foto dipilih. Foto dikecilkan otomatis saat dikirim; maksimal 40 MB total.")
                else:
                    if not lampiran_lama:
                        st.caption("Tidak ada foto lampiran pada pengumpulan ini (opsional).")

            if not terkunci:
                status_draft = st.session_state.get("_draft_status_by_task", {}).get(task_id, "")
                if status_draft == "Menunggu penyimpanan":
                    st.info("⏳ Jawaban tersimpan sementara di sesi ini dan menunggu autosave batch.")
                elif status_draft == "Tersimpan":
                    st.caption("✓ Draft terakhir berhasil disimpan ke server.")
                if st.button("💾 Simpan Draft Sekarang", key=f"simpan_draft_{task_id}"):
                    ok_draft, pesan_draft = _flush_draft_task(task_id, siswa_id, paksa=True)
                    if ok_draft:
                        st.success(pesan_draft)
                    else:
                        st.error("Draft belum berhasil disimpan: " + pesan_draft)
                if st.session_state.get("_galat_simpan"):
                    st.warning("Draft belum tersimpan. Periksa koneksi; sistem akan mencoba lagi.")

            if not terkunci:
                current_answers = {}
                for i in range(1, len(daftar_soal) + 1):
                    v = st.session_state.get(f"student_{task_id}_{i}", "")
                    current_answers[str(i)] = "" if v is None else v
                belum = [n for n, v in current_answers.items() if jawaban_kosong(v)]
                boleh_kirim = not data_soal_tidak_lengkap
                if data_soal_tidak_lengkap:
                    st.error("Tugas ini belum dapat dikirim karena ada data soal yang tidak lengkap. Tutor perlu memperbaikinya terlebih dahulu.")
                if belum:
                    st.warning("Soal nomor " + ", ".join(belum) + " belum dijawab.")
                    konfirmasi_kosong = st.checkbox(
                        "Saya yakin ingin mengirim walaupun masih ada soal yang kosong.",
                        key=f"yakin_{task_id}"
                    )
                    boleh_kirim = boleh_kirim and konfirmasi_kosong
                if not boleh_kirim:
                    alasan_kirim = []
                    if data_soal_tidak_lengkap:
                        alasan_kirim.append("data soal belum lengkap (hubungi tutor)")
                    if belum and not st.session_state.get(f"yakin_{task_id}", False):
                        alasan_kirim.append("jawab semua soal atau centang konfirmasi soal yang dikosongkan")
                    if alasan_kirim:
                        st.info("Tombol Kirim belum aktif. Yang perlu dilakukan: " + "; ".join(alasan_kirim) + ".")
                _flag_kirim = f"_mengirim_{task_id}"
                st.button(
                    "⏳ Sedang mengirim…" if st.session_state.get(_flag_kirim) else "📤 Kirim Jawaban",
                    key=f"submit_{task_id}",
                    disabled=(not boleh_kirim) or bool(st.session_state.get(_flag_kirim)),
                    on_click=st.session_state.__setitem__, args=(_flag_kirim, True),
                )
                if st.session_state.get(_flag_kirim):
                    st.info("⏳ Sedang mengirim. Jangan tutup halaman dan jangan tekan tombol lagi sampai selesai.")
                    urls_lampiran_online = []
                    nilai_otomatis = None
                    try:
                        # Validasi timer dilakukan sebelum unggah lampiran maupun simpan jawaban.
                        validasi_waktu_pengiriman(task_id, siswa_id)
                        if file_jawaban:
                            hasil_lampiran_online = simpan_lampiran_jawaban(task_id, siswa_id, file_jawaban)
                            urls_lampiran_online = [x.get("URL_Drive", "") for x in hasil_lampiran_online]
                        ok = simpan_pengiriman_jawaban(task_id, siswa_id, current_answers)
                        # Tutup sesi juga bila pengiriman terdeteksi sudah pernah tersimpan (idempoten).
                        akhiri_sesi_online(siswa_id, task_id)
                        if ok:
                            st.session_state.get("_draft_pending_by_task", {}).pop(task_id, None)
                            st.session_state.setdefault("_draft_status_by_task", {})[task_id] = "Terkirim"
                            nilai_otomatis = None
                            if not soal_dari_lampiran:
                                try:
                                    nilai_otomatis = terbitkan_nilai_otomatis(task_id, siswa_id, daftar_soal, current_answers)
                                except Exception as _e_auto:
                                    nilai_otomatis = None  # gagal otomatis: tetap menunggu tutor
                                    catat_log_gagal_pengiriman(task_id, siswa_id, "nilai_otomatis", _e_auto)
                                    st.session_state[f"_galat_auto_{task_id}"] = f"{_e_auto.__class__.__name__}: {_e_auto}"
                            # Notifikasi hanya dikirim setelah penyimpanan jawaban berhasil.
                            try:
                                kirim_telegram_notifikasi_pengiriman(
                                    task_id, siswa_id,
                                    "jawaban online" + (" + lampiran foto" if file_jawaban else "")
                                )
                            except Exception:
                                pass  # kegagalan notifikasi tidak boleh membatalkan pengiriman
                        st.success(("Jawaban berhasil dikirim. Nilai soal objektif sudah terbit." if nilai_otomatis is not None
                                    else "Jawaban berhasil dikirim. Tutor akan memeriksanya.") if ok
                                   else "Jawaban untuk tugas ini sudah dikirim sebelumnya.")
                        st.rerun()
                    except Exception as e:
                        catat_log_gagal_pengiriman(task_id, siswa_id, "pengiriman_jawaban_online", e, urls_lampiran_online)
                        st.error(f"Pengiriman jawaban/lampiran gagal ({e.__class__.__name__}). Periksa koneksi dan status pengiriman sebelum mencoba ulang.")
                    finally:
                        st.session_state[_flag_kirim] = False

        elif mode_pengerjaan == TASK_MODE_OFFLINE and unggah_oleh_tugas(t) != "siswa":
            if terkunci:
                st.info("Hasil pekerjaan sudah diunggah Tutor. " + (
                    "Tutor akan memeriksanya." if kode == "dikirim" else "Sudah dinilai oleh Tutor."))
                tampilkan_bahan_tutor_siswa(task_id, siswa_id)
            elif gerbang_sesi_tugas(t, task_id, siswa_id, sesi_aktif_page, expander_state_key):
                st.info("Tugas ini dikerjakan di kertas. Setelah selesai, Tutor yang akan mengunggah foto hasil pekerjaan dan memasukkan nilai.")
                st.caption("Tidak perlu mengunggah foto dari akun siswa.")
                # FITUR BARU: tombol Selesai Mengerjakan (menghentikan timer, membebaskan kunci tugas lain)
                if sesi_aktif_page and str(sesi_aktif_page.get("ID_Tugas", "")).strip() == task_id:
                    tampilkan_tombol_selesai_mengerjakan(siswa_id, task_id, expander_state_key)
        else:
            # Mode upload lama dipertahankan hanya untuk kompatibilitas tugas historis.
            if mode_pengerjaan == TASK_MODE_ONLINE and not daftar_soal:
                st.error("Mode tugas terbaca sebagai online, tetapi daftar soal tidak ditemukan atau format Soal_JSON tidak valid. Hubungi tutor untuk memeriksa data tugas.")
            elif terkunci:
                st.info("Sudah ditandai selesai. Tutor akan memeriksa hasilnya." if kode == "dikirim"
                        else "Sudah dinilai oleh Tutor.")
                tampilkan_bahan_tutor_siswa(task_id, siswa_id)
            elif mode_pengerjaan == TASK_MODE_OFFLINE and not gerbang_sesi_tugas(
                    t, task_id, siswa_id, sesi_aktif_page, expander_state_key):
                return
            else:
                # FITUR BARU: tugas offline unggah mandiri: Mulai -> kerjakan -> Selesai Mengerjakan -> unggah foto.
                # Alur: Mulai -> kerjakan -> Selesai (timer berhenti, tersimpan di sheet) -> Unggah -> Kirim.
                _timer_ofl = str(t.get("Timer_Menit", "")).strip()
                if mode_pengerjaan == TASK_MODE_OFFLINE and _timer_ofl not in ("", "0"):
                    try:
                        _sisa_kerja = hitung_sisa_waktu_sesi(sesi_aktif_page, _timer_ofl) if (
                            sesi_aktif_page and str(sesi_aktif_page.get("ID_Tugas", "")).strip() == task_id
                        ) else 0
                    except Exception:
                        _sisa_kerja = 0
                    if _sisa_kerja and _sisa_kerja > 0:
                        st.info("Kerjakan di kertas. Setelah selesai menulis, tekan Selesai Mengerjakan (timer berhenti), lalu unggah foto hasilnya dan kirim.")
                        tampilkan_tombol_selesai_mengerjakan(siswa_id, task_id, expander_state_key)
                        return
                st.info("Kerjakan melalui materi/lampiran dari Tutor. Unggah foto, PDF, audio, atau video hasil pekerjaan, lalu kirim kepada Tutor.")
                catatan_siswa = st.text_area("Catatan untuk Tutor (opsional):", key=f"cat_{task_id}")
                file_jawaban_offline = st.file_uploader(
                    "Unggah foto, PDF, audio, atau video hasil pekerjaan:",
                    type=["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf", "mp4", "mov", "webm", "m4v",
                          "mp3", "wav", "m4a", "ogg", "aac"],
                    accept_multiple_files=True,
                    key=f"lampiran_offline_{task_id}"
                )
                if file_jawaban_offline:
                    st.caption("Foto dikecilkan otomatis. Video/audio maksimal 10 MB per file. Pastikan video/audio dapat diputar dan suaranya jelas.")
                _flag_kirim_ofl = f"_mengirim_ofl_{task_id}"
                st.button(
                    "⏳ Sedang mengirim…" if st.session_state.get(_flag_kirim_ofl) else "📤 Kirim Hasil Pekerjaan",
                    key=f"selesai_{task_id}",
                    disabled=bool(st.session_state.get(_flag_kirim_ofl)),
                    on_click=st.session_state.__setitem__, args=(_flag_kirim_ofl, True),
                )
                if st.session_state.get(_flag_kirim_ofl):
                    st.info("⏳ Sedang mengirim. Jangan tutup halaman dan jangan tekan tombol lagi sampai selesai.")
                    urls_lampiran_offline = []
                    try:
                        teks = "Sudah dikerjakan (offline)"
                        if catatan_siswa.strip():
                            teks += " — " + catatan_siswa.strip()
                        if not file_jawaban_offline and not catatan_siswa.strip():
                            st.error("Unggah minimal satu foto/PDF atau isi catatan untuk Tutor.")
                        else:
                            validasi_waktu_pengiriman(task_id, siswa_id)
                            if file_jawaban_offline:
                                hasil_lampiran_offline = simpan_lampiran_jawaban(task_id, siswa_id, file_jawaban_offline)
                                urls_lampiran_offline = [x.get("URL_Drive", "") for x in hasil_lampiran_offline]
                            ok = simpan_pengiriman_jawaban(task_id, siswa_id, {"0": teks})
                            # Tutup sesi walau sistem mengenali pengiriman yang sudah tersimpan sebelumnya.
                            akhiri_sesi_online(siswa_id, task_id)
                            if ok:
                                try:
                                    kirim_telegram_notifikasi_pengiriman(
                                        task_id, siswa_id,
                                        "hasil pekerjaan upload mandiri" + (" + lampiran" if file_jawaban_offline else "")
                                    )
                                except Exception:
                                    pass  # kegagalan notifikasi tidak boleh membatalkan pengiriman
                            st.success("Hasil pekerjaan berhasil dikirim. Tutor akan memeriksanya." if ok
                                       else "Tugas ini sudah dikirim sebelumnya.")
                            st.rerun()
                    except Exception as e:
                        catat_log_gagal_pengiriman(task_id, siswa_id, "pengiriman_hasil_offline_siswa", e, urls_lampiran_offline)
                        st.error(f"Pengiriman hasil pekerjaan gagal ({e.__class__.__name__}). Periksa status pengiriman sebelum mencoba ulang.")
                    finally:
                        st.session_state[_flag_kirim_ofl] = False


# =========================================================
# HEADER APLIKASI
# =========================================================
st.markdown("""
<div class="main-header">
    <h2 style="margin:0;">✨ Portal Bimbel Rumah Nazma</h2>
    <p style="margin:4px 0 0 0; opacity:0.9;">
        Sistem Pembelajaran Terpadu, Multi-Mapel, Flipbook, Timer, & Evaluasi Berkelanjutan
    </p>
</div>
""", unsafe_allow_html=True)
VERSI_KODE = "28-11-2026 · Paket soal, kartu tugas ramah anak v17"
st.caption(f"Versi kode: {VERSI_KODE}")

peran = st.selectbox(
    "🔑 Pilih Akses Login Portal:",
    ["🎓 Siswa", "🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "👨‍👩‍👧 Orang Tua"]
)
st.markdown("---")


# =========================================================
# 1. MODUL SISWA
# =========================================================
def _status_aktif(value, default=True):
    """Pemeriksaan status akun yang dipakai lintas portal."""
    status = str(value or "").strip().casefold()
    if not status:
        return default
    return status not in {"nonaktif", "tidak aktif", "inactive", "0", "false", "berhenti"}


if peran == "🎓 Siswa":
    st.subheader("🎓 Login Portal Siswa")

    if "siswa_logged_in" not in st.session_state:
        st.session_state.siswa_logged_in = False
        st.session_state.siswa_nama = ""
        st.session_state.siswa_jenjang = ""
        st.session_state.siswa_id = ""

    if not st.session_state.siswa_logged_in:
        id_siswa_login = st.text_input("ID Siswa (contoh: SIS-084):", key="login_siswa_id").strip().upper()
        pin_siswa = st.text_input("PIN Siswa (minimal 6 angka):", type="password", key="login_siswa_pin")

        if st.button("🚀 Masuk ke Akun Siswa"):
            muat_ulang_data_bersih()
            pastikan_koneksi()
            if not id_siswa_login or not pin_siswa:
                st.error("ID dan PIN wajib diisi.")
            else:
                try:
                    ws_akun_login = get_worksheet("Akun_Pengguna")
                    akun_rows_login = pastikan_pemetaan_id_siswa(
                        ws_akun_login, get_worksheet("Data_Siswa")
                    )
                    akun_siswa = next((
                        r for r in akun_rows_login
                        if str(r.get("ID_SISWA", "")).strip().upper() == id_siswa_login
                        and str(r.get("Level_Akses", "")).strip().casefold() == "siswa"
                        and verifikasi_pin(pin_siswa, r.get("PIN_Password", ""))[0]
                    ), None)

                    data_siswa_login = baca_records_aman(get_worksheet("Data_Siswa"))
                    siswa_match = next((
                        r for r in data_siswa_login
                        if str(r.get("ID_SISWA", r.get("ID_Siswa", ""))).strip().upper() == id_siswa_login
                    ), None)

                    if not akun_siswa or not siswa_match:
                        st.error("ID atau PIN tidak sesuai.")
                    elif not _status_aktif(siswa_match.get("Status", "Aktif")):
                        st.error("🚫 Akun Siswa Anda sudah Nonaktif. Silakan hubungi pengelola.")
                    else:
                        # Putuskan konteks tutor lama sebelum menetapkan identitas siswa.
                        st.session_state.tutor_logged_in = False
                        st.session_state.tutor_nama = ""
                        st.session_state.tutor_id = ""
                        st.session_state.tutor_user_id = ""
                        st.session_state.pop("tutor_baris", None)
                        cocok_pin, pin_lama_plain = verifikasi_pin(pin_siswa, akun_siswa.get("PIN_Password", ""))
                        if cocok_pin and pin_lama_plain:
                            upgrade_pin_lama(ws_akun_login, akun_siswa, "PIN_Password", pin_siswa)
                        st.session_state.siswa_logged_in = True
                        st.session_state.siswa_nama = siswa_match.get("Nama_Siswa", siswa_match.get("Nama_Lengkap", "Siswa"))
                        st.session_state.siswa_id = str(siswa_match.get("ID_SISWA", siswa_match.get("ID_Siswa", ""))).strip()
                        st.session_state.siswa_jenjang = str(siswa_match.get("Jenjang", "SD")).strip().upper()
                        st.session_state.siswa_baris = int(siswa_match.get("_baris", 0))
                        st.session_state.siswa_akun_baris = int(akun_siswa.get("_baris", 0))
                        st.session_state.siswa_user_id = str(akun_siswa.get("ID_User", "")).strip()
                        st.rerun()
                except Exception as exc:
                    st.error(f"Login siswa belum dapat diproses: {exc}")

    else:
        pastikan_koneksi()
        nama_aktif = st.session_state.siswa_nama
        jenjang_aktif = st.session_state.siswa_jenjang
        col_welcome, col_logout = st.columns([4, 1])
        with col_welcome:
            st.success(f"Halo, Ananda **{nama_aktif}** ({jenjang_aktif})! Semangat Belajar! 🌟")
        with col_logout:
            if st.button("🚪 Logout"):
                draft_pending = st.session_state.get("_draft_pending_by_task", {})
                draft_errors = []
                for draft_task_id in list(draft_pending.keys()):
                    ok_logout, msg_logout = _flush_draft_task(
                        draft_task_id, st.session_state.get("siswa_id", ""), paksa=True
                    )
                    if not ok_logout:
                        draft_errors.append(f"{draft_task_id}: {msg_logout}")
                if draft_errors:
                    st.error(
                        "Logout ditunda karena ada draft yang belum tersimpan. "
                        "Periksa koneksi lalu tekan Simpan Draft: " + " | ".join(draft_errors)
                    )
                else:
                    st.session_state.siswa_logged_in = False
                    st.session_state.siswa_nama = ""
                    st.session_state.siswa_id = ""
                    st.session_state.siswa_jenjang = ""
                    st.session_state.pop("siswa_baris", None)
                    st.session_state.pop("siswa_akun_baris", None)
                    st.session_state.pop("siswa_user_id", None)
                    st.session_state.pop("_indeks_baris_jawaban_siswa", None)
                    st.session_state.pop("_tugas_jawaban_terkunci", None)
                    st.session_state.pop("_draft_saved_for_task", None)
                    st.session_state.pop("_draft_pending_by_task", None)
                    st.session_state.pop("_draft_student_by_task", None)
                    st.session_state.pop("_draft_status_by_task", None)
                    st.session_state.pop("_draft_changed_at_by_task", None)
                    st.session_state.pop("_draft_saved_at_by_task", None)
                    st.rerun()

        # Tetap aktif di semua menu siswa agar antrean draft tidak berhenti saat berpindah halaman.
        _autosave_semua_draft_fragment(st.session_state.get("siswa_id", ""))

        # Panel ganti PIN tidak ditampilkan di beranda siswa.
        # Reset PIN siswa dilakukan oleh Owner; autentikasi tetap memakai PIN hash.

        try:
            tugas_anak = [
                t for t in get_student_tasks()
                if str(t.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
                and "batal" not in str(t.get("Status_Tugas", "")).lower()
                and not adalah_materi(t)  # Arsip materi lama: tetap di Sheets, tidak ditampilkan ke siswa.
            ]
        except Exception as e:
            tugas_anak = []
            st.error(f"Gagal membaca daftar tugas: {e}")

        try:
            jawaban_ws = get_answers_worksheet()
            jawaban_records = baca_jawaban_tergabung(jawaban_ws)
        except Exception as e:
            jawaban_records = []
            st.warning(f"Data jawaban belum dapat dibaca: {e}")

        siswa_id_aktif = str(st.session_state.siswa_id).strip()
        jawaban_siswa = [
            x for x in jawaban_records
            if (siswa_id_aktif and str(x.get("ID_Siswa", "")).strip() == siswa_id_aktif)
            or str(x.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
        ]
        status_by_task = {}
        for ans in jawaban_siswa:
            status_by_task[str(ans.get("ID_Tugas", ""))] = str(ans.get("Status", "Draft"))

        try:
            nilai_records = baca_nilai_tugas_terpadu()
        except Exception as exc_nilai:
            nilai_records = []
            st.warning(f"Data nilai belum dapat dibaca: {exc_nilai}")
        nilai_ids = {kunci_nilai_penugasan(n) for n in nilai_records if all(kunci_nilai_penugasan(n))}

        tugas_pr = sorted([t for t in tugas_anak if adalah_pr(t)], key=lambda x: str(x.get("Tenggat", "")) or "9999")
        tugas_reguler = [t for t in tugas_anak if not adalah_pr(t)]
        tugas_dikerjakan = [t for t in tugas_anak if not adalah_materi(t)]
        status_list = [label_status(t, status_by_task, nilai_ids) for t in tugas_dikerjakan]
        total = len(tugas_dikerjakan)
        submitted = sum(1 for k, _ in status_list if k in ("dikirim", "dinilai"))
        marked = sum(1 for k, _ in status_list if k == "dinilai")
        draft_count = sum(1 for k, _ in status_list if k == "draft")
        pending = sum(1 for k, _ in status_list if k == "belum")
        pr_status = [label_status(t, status_by_task, nilai_ids) for t in tugas_pr if not adalah_materi(t)]
        pr_belum = sum(1 for k, _ in pr_status if k in ("belum", "draft"))
        pr_terlambat = sum(1 for k, lb in pr_status if k in ("belum", "draft") and "Terlambat" in lb)

        st.markdown("### 🏠 Beranda Belajar")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tugas diberikan", total)
        m2.metric("Belum dikerjakan", pending)
        m3.metric("Draft jawaban", draft_count)
        m4.metric("Sudah dinilai", marked)

        # Pulihkan kunci yang tertinggal hanya jika data pengumpulan/penilaian
        # membuktikan tugas pada sesi aktif sudah selesai. Riwayat sesi tetap disimpan.
        try:
            rekonsiliasi_sesi_aktif_siswa(siswa_id_aktif, status_by_task, nilai_ids)
        except Exception as exc:
            st.warning(f"Status sesi online belum dapat direkonsiliasi: {exc}")
        try:
            lepas_sesi_kedaluwarsa(siswa_id_aktif, tugas_anak)
        except Exception as exc:
            st.warning(f"Sesi yang waktunya habis belum dapat dilepas: {exc}")
        sesi_online_aktif_global = baca_sesi_aktif_siswa(siswa_id_aktif)
        # Bersihkan pilihan menu lama agar sesi yang masih menyimpan "Materi" tetap aman.
        if st.session_state.get("menu_navigasi_siswa") == "📖 Materi":
            st.session_state.pop("menu_navigasi_siswa", None)
        menu_siswa = st.sidebar.radio(
            "MENU SISWA",
            ["🏠 Beranda", "📝 Tugas", "📌 PR", "📝 Hasil Penilaian", "📈 Riwayat Belajar", "🔐 Keamanan"],
            label_visibility="visible",
            key="menu_navigasi_siswa"
        )
        st.sidebar.markdown("---")
        tombol_kembali("menu_navigasi_siswa")
        tombol_muat_ulang_sidebar("muat_ulang_siswa")
        st.sidebar.markdown("**Ruang Belajar Siswa**")
        st.sidebar.caption(f"Login sebagai: {nama_aktif}")

        if menu_siswa == "🏠 Beranda":
            st.markdown(
                f'<div class="portal-hero"><h2>Selamat Datang, {nama_aktif} 👋</h2>'
                '<p>Ruang belajar pribadi Bimbel Rumah Nazma</p></div>',
                unsafe_allow_html=True
            )
            st.markdown("#### Ringkasan Belajar")
            ringkas = st.columns(4)
            ringkas[0].metric("Tugas diberikan", total)
            ringkas[1].metric("Belum dikerjakan", pending)
            ringkas[2].metric("Draft jawaban", draft_count)
            ringkas[3].metric("Sudah dinilai", marked)
            if pr_terlambat:
                st.warning(f"⚠️ Ada {pr_terlambat} PR yang sudah lewat tenggat. Buka menu PR untuk mengerjakannya.")
            elif pr_belum:
                st.info(f"📌 Ada {pr_belum} PR yang belum dikerjakan. Buka menu PR.")
            if pending:
                st.button(f"▶ Ada {pending} tugas menunggu. Kerjakan sekarang!", type="primary", key="beranda_ke_tugas",
                          use_container_width=True,
                          on_click=lambda: st.session_state.update({"menu_navigasi_siswa": "📝 Tugas"}))
            st.info("Pilih menu di sebelah kiri untuk mengerjakan tugas dan PR, melihat nilai, atau memeriksa riwayat belajar.")

        elif menu_siswa == "📝 Tugas":
            st.markdown("### 📝 Tugas Pembelajaran")
            daftar_tugas_menu = [t for t in tugas_reguler if not adalah_materi(t)]
            tugas_reguler_aktif = [
                t for t in daftar_tugas_menu
                if label_status(t, status_by_task, nilai_ids)[0] not in ("dikirim", "dinilai")
            ]
            tugas_reguler_selesai = [
                t for t in daftar_tugas_menu
                if label_status(t, status_by_task, nilai_ids)[0] in ("dikirim", "dinilai")
            ]
            st.markdown(f"#### Tugas yang perlu dikerjakan ({len(tugas_reguler_aktif)})")
            if tugas_reguler_aktif:
                for t in tugas_reguler_aktif:
                    tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids, sesi_online_aktif_global)
            else:
                st.success("Tidak ada tugas aktif yang menunggu dikerjakan.")
            if tugas_reguler_selesai:
                with st.expander(f"📚 Riwayat / Arsip Tugas Selesai ({len(tugas_reguler_selesai)})", expanded=False):
                    st.caption("Tugas yang sudah dikirim atau dinilai dipindahkan ke sini. Riwayat tetap tersimpan dan dapat dibuka kembali.")
                    for t in reversed(tugas_reguler_selesai):
                        tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids, sesi_online_aktif_global)

        elif menu_siswa == "📌 PR":
            st.markdown(f"### 📌 PR Ananda {nama_aktif}")
            if st.session_state.get("_galat_simpan"):
                st.warning("Jawaban terakhir belum tersimpan otomatis: " + str(st.session_state.pop("_galat_simpan")))
            if not tugas_pr:
                st.info("Belum ada PR dari Tutor.")
            else:
                if pr_terlambat:
                    st.warning(f"⚠️ {pr_terlambat} PR sudah lewat tenggat. Kerjakan secepatnya ya.")
                aktif = [t for t in tugas_pr if label_status(t, status_by_task, nilai_ids)[0] in ("belum", "draft")]
                selesai = [t for t in tugas_pr if label_status(t, status_by_task, nilai_ids)[0] in ("dikirim", "dinilai")]
                st.markdown(f"#### PR yang perlu dikerjakan ({len(aktif)})")
                if aktif:
                    for t in aktif:
                        tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids, sesi_online_aktif_global)
                else:
                    st.success("Semua PR sudah dikerjakan. Hebat! 🎉")
                if selesai:
                    st.markdown(f"#### PR yang sudah dikirim / dinilai ({len(selesai)})")
                    for t in selesai:
                        tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids, sesi_online_aktif_global)

        elif menu_siswa == "📝 Hasil Penilaian":
            st.markdown("### 📝 Hasil Penilaian Tutor")
            info_tugas = {str(t.get("ID_Tugas", "")).strip(): t for t in tugas_anak}
            def _id_tugas_nilai(n):
                # Skema nilai aktif memakai ID_Penugasan; ID_Tugas dipertahankan untuk data lama.
                return str(n.get("ID_Penugasan", n.get("ID_Tugas", ""))).strip()
            hasil_nilai = [
                n for n in nilai_records
                if _id_tugas_nilai(n) in info_tugas
                and str(n.get("ID_Siswa", "")).strip().casefold() == siswa_id_aktif.casefold()
            ]
            if hasil_nilai:
                for n in reversed(hasil_nilai):
                    tg = info_tugas.get(_id_tugas_nilai(n), {})
                    st.markdown(f"**{tg.get('Mapel', 'Tugas')} — {tg.get('Judul_Tugas') or _id_tugas_nilai(n)}**")
                    st.metric("Nilai", n.get("Nilai", "-"))
                    umpan_balik = str(n.get("Umpan_Balik", n.get("Catatan", "")) or "").strip()
                    st.write(f"Catatan Tutor: {umpan_balik or '-'}")
                    nama_tutor_nilai = tg.get("Tutor") or n.get("Tutor") or "-"
                    waktu_nilai = n.get("Tanggal_Penilaian", n.get("Waktu_Penilaian", "-"))
                    st.caption(f"Diperiksa oleh {nama_tutor_nilai} · {waktu_nilai}")
                    try:
                        _soal_n, _mode_n = buka_soal_dan_mode(tg.get("Soal_JSON", ""), tg.get("Jenis_Tugas", ""))
                        if _soal_n and _mode_n == TASK_MODE_ONLINE:
                            _jw_n = {}
                            for _a in jawaban_siswa:
                                if str(_a.get("ID_Tugas", "")).strip() == _id_tugas_nilai(n):
                                    _jw_n = json.loads(_a.get("Jawaban_JSON", "{}") or "{}")
                                    break
                            with st.expander("📋 Lihat benar/salah per soal", expanded=False):
                                tampilkan_hasil_objektif_siswa(_soal_n, _jw_n)
                    except Exception as _e:
                        st.caption(f"Rincian per soal belum bisa dimuat ({_e.__class__.__name__}).")
                    st.divider()
            else:
                st.info("Belum ada hasil penilaian dari Tutor.")

        elif menu_siswa == "🔐 Keamanan":
            st.markdown("### 🔐 Keamanan Akun")
            st.caption("Ubah PIN akunmu sendiri. ID Siswa tidak berubah. Jangan bagikan PIN kepada siapa pun.")
            akun_siswa_aktif = None
            if st.session_state.get("siswa_akun_baris"):
                akun_siswa_aktif = next((
                    r for r in baca_records_aman(get_worksheet("Akun_Pengguna"))
                    if int(r.get("_baris", 0) or 0) == int(st.session_state.siswa_akun_baris)
                ), None)
            if akun_siswa_aktif:
                form_ganti_pin(
                    get_worksheet("Akun_Pengguna"), akun_siswa_aktif,
                    "PIN_Password", "siswa",
                    identity_field="ID_User",
                    identity_value=st.session_state.get("siswa_user_id", "")
                )
            else:
                st.warning("Data akun belum ditemukan. Silakan logout lalu login kembali.")

        elif menu_siswa == "📈 Riwayat Belajar":
            st.markdown("### 📈 Riwayat Belajar")
            try:
                ws_r = get_worksheet("Riwayat_Latihan")
                data_tabel_siswa = [
                    {
                        "Tanggal": str(r.get("Waktu_Selesai", ""))[:10],
                        "Mapel": r.get("Mapel"),
                        "Aktivitas": r.get("Topik_Kuis"),
                        "Skor": r.get("Skor"),
                        "Catatan": r.get("Detail_Salah")
                    }
                    for r in baca_records_aman(ws_r)
                    if str(r.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
                ]
                if data_tabel_siswa:
                    st.dataframe(pd.DataFrame(data_tabel_siswa), use_container_width=True)
                else:
                    st.info("Belum ada riwayat belajar.")
            except gspread.WorksheetNotFound:
                st.info("Riwayat belajar belum tersedia.")
            tampilkan_riwayat_kehadiran(st.session_state.siswa_id, "Kehadiran Sesi Belajar")


# =========================================================
# 2. MODUL TUTOR
# =========================================================
elif peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar Portal")

    if "tutor_logged_in" not in st.session_state:
        st.session_state.tutor_logged_in = False
        st.session_state.tutor_nama = ""
        st.session_state.tutor_id = ""
        st.session_state.tutor_user_id = ""

    if not st.session_state.tutor_logged_in:
        username = st.text_input("Username Pengajar:")
        pin = st.text_input("PIN / Password:", type="password")

        if st.button("Masuk Pengajar"):
            pastikan_koneksi()
            muat_ulang_data_bersih()
            # Login harus membaca PIN terbaru dari Google Sheets, bukan cache 180 detik.
            data = baca_records_aman(get_worksheet("Akun_Pengguna"), refresh=True)
            user_found = False
            is_active = True
            salah_menu = False

            for row in data:
                if (
                    str(row.get("Username", "")).strip().lower() == username.strip().lower()
                    and verifikasi_pin(pin, row.get("PIN_Password", ""))[0]
                ):
                    user_found = True
                    cocok_pin, pin_lama_plain = verifikasi_pin(pin, row.get("PIN_Password", ""))
                    if cocok_pin and pin_lama_plain:
                        upgrade_pin_lama(get_worksheet("Akun_Pengguna"), row, "PIN_Password", pin)
                    status_tutor = str(row.get("Status", "Aktif")).strip().lower()
                    if status_tutor == "nonaktif":
                        is_active = False
                    elif adalah_akun_ortu(row):
                        # Akun wali murid tidak boleh masuk portal tutor.
                        salah_menu = True
                    else:
                        # Putuskan konteks siswa lama sebelum menetapkan identitas tutor.
                        st.session_state.siswa_logged_in = False
                        st.session_state.siswa_nama = ""
                        st.session_state.siswa_id = ""
                        st.session_state.siswa_jenjang = ""
                        for _kunci_siswa in (
                            "siswa_baris", "siswa_akun_baris", "siswa_user_id",
                            "_indeks_baris_jawaban_siswa", "_tugas_jawaban_terkunci",
                            "_draft_saved_for_task", "_draft_pending_by_task",
                            "_draft_student_by_task", "_draft_status_by_task",
                            "_draft_changed_at_by_task", "_draft_saved_at_by_task",
                        ):
                            st.session_state.pop(_kunci_siswa, None)
                        st.session_state.tutor_logged_in = True
                        st.session_state.tutor_nama = str(row.get("Nama_Pengguna", "")).strip()
                        st.session_state.tutor_user_id = str(row.get("ID_User", "")).strip()
                        st.session_state.tutor_id = resolve_tutor_id(row)
                        st.session_state.tutor_baris = int(row.get("_baris", 0))
                        st.rerun()
                    break

            if not user_found:
                st.error("Username atau PIN salah!")
            elif not is_active:
                st.error("🚫 Akun Pengajar Anda sudah Nonaktif.")
            elif salah_menu:
                st.error("Akun ini adalah akun Wali Murid. Silakan masuk lewat menu Orang Tua.")

    else:
        pastikan_koneksi()
        st.success(f"👨‍🏫 Tutor Aktif: **{st.session_state.tutor_nama}**")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.session_state.tutor_id = ""
            st.session_state.tutor_user_id = ""
            st.session_state.pop("tutor_baris", None)
            st.session_state.pop("menu_navigasi_tutor", None)
            st.session_state.pop("_tutor_id_dicoba", None)
            st.rerun()

        if not st.session_state.get("tutor_id") and not st.session_state.get("_tutor_id_dicoba"):
            st.session_state["_tutor_id_dicoba"] = True  # satu kali per sesi, agar tidak membebani kuota
            try:
                _akun = baca_records_aman(get_worksheet("Akun_Pengguna"), refresh=True)
                _baris_akun = next((r for r in _akun if str(r.get("ID_User", "")).strip()
                                    == str(st.session_state.get("tutor_user_id", "")).strip()), None)
                if _baris_akun:
                    st.session_state.tutor_id = resolve_tutor_id(_baris_akun)
            except Exception as _e:
                st.session_state["_tutor_id_gagal_baca"] = str(_e)
        if not st.session_state.get("tutor_id") and st.session_state.get("_tutor_id_gagal_baca"):
            st.warning("Data tutor belum bisa dibaca dari Google Sheets (kemungkinan kuota sedang penuh), "
                       "bukan karena akun salah. Tekan 🔄 Muat ulang data di sidebar.")
        if not st.session_state.get("tutor_id"):
            st.warning("ID tutor belum dapat dicocokkan dengan Data_Tutor. Fitur kehadiran dinonaktifkan sampai ID_User pada Akun_Pengguna cocok dengan Data_Tutor, atau nama akun sama persis dengan Nama_Tutor.")

        st.sidebar.markdown(
            """
            <div style="background:linear-gradient(145deg,#123568,#28559a);
                        padding:18px 14px;border-radius:14px;color:white;
                        text-align:center;margin-bottom:14px;">
              <div style="font-size:2rem;">📚</div>
              <div style="font-weight:750;font-size:1.05rem;">Bimbel Rumah Nazma</div>
              <div style="font-size:.78rem;opacity:.85;">Portal Pengajar / Tutor</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.sidebar.markdown("#### MENU PENGAJAR")
        def _pilih_menu_tutor(target):
            st.session_state["menu_navigasi_tutor"] = target

        # Bersihkan pilihan menu Materi Tambahan dari sesi tutor versi lama.
        if st.session_state.get("menu_navigasi_tutor") == "📚 Materi Tambahan":
            st.session_state.pop("menu_navigasi_tutor", None)
        menu_tutor = st.sidebar.radio(
            "Navigasi",
            [
                "🏠 Beranda",
                "📝 Persiapan Sesi & Bank Soal",
                "📚 Koleksi Soal",
                "📋 Pantau Tugas & PR",
                "📊 Portofolio Siswa",
                "🕒 Kehadiran Siswa",
                "🗓️ Evaluasi Susulan",
                "📨 Pesan Orang Tua",
                "⚙️ Pengaturan Akun"
            ],
            label_visibility="collapsed",
            key="menu_navigasi_tutor"
        )
        st.sidebar.markdown("---")
        tombol_kembali("menu_navigasi_tutor")
        tombol_muat_ulang_sidebar("muat_ulang_tutor")
        st.sidebar.caption(f"Login sebagai: {st.session_state.tutor_nama}")
        if st.sidebar.button("🚪 Keluar dari Portal", key="sidebar_logout_tutor", use_container_width=True):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.session_state.tutor_id = ""
            st.session_state.tutor_user_id = ""
            st.session_state.pop("tutor_baris", None)
            st.session_state.pop("menu_navigasi_tutor", None)
            st.rerun()

        # -------------------------------------------------
        # BERANDA TUTOR - ruang kerja pribadi (sidebar tetap)
        # -------------------------------------------------
        if menu_tutor == "🏠 Beranda":
            try:
                jumlah_tertunda = len(sesi_belum_dievaluasi(
                    st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", ""), waktu_lokal().date()
                ))
                if jumlah_tertunda:
                    st.info(f"🗓️ Ada {jumlah_tertunda} sesi yang belum dievaluasi. Buka menu **Evaluasi Susulan** untuk melengkapinya.")
            except Exception:
                pass
            try:
                jumlah_menunggu_nilai = len(ambil_jawaban_menunggu_milik(
                    st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", "")
                ))
                if jumlah_menunggu_nilai:
                    st.warning(f"📥 {jumlah_menunggu_nilai} jawaban siswa menunggu pemeriksaan. Buka menu **Portofolio Siswa**.")
            except Exception:
                pass
            id_user_aktif = str(st.session_state.get("tutor_user_id", "")).strip()
            id_tutor_aktif = str(st.session_state.get("tutor_id", "")).strip()

            # JURNAL MENGAJAR HARIAN
            st.markdown("## Jurnal Mengajar")
            st.caption(
                "Satu tanggal untuk seluruh kegiatan mengajar. Catatan dapat disimpan bertahap "
                "dan diperbarui kapan saja, termasuk setelah mengajar."
            )

            try:
                semua_jurnal_tutor = ambil_jurnal_harian(id_user_aktif)
            except Exception as exc:
                semua_jurnal_tutor = []
                st.error(f"Jurnal belum dapat dimuat: {exc}")

            tanggal_jurnal = st.date_input(
                "Tanggal jurnal", value=waktu_lokal().date(), key="tanggal_jurnal_harian"
            )
            tanggal_jurnal_text = tanggal_jurnal.strftime("%Y-%m-%d")
            jurnal_terpilih = next(
                (r for r in semua_jurnal_tutor if str(r.get("Tanggal", "")) == tanggal_jurnal_text),
                None
            )

            # Tampilkan jurnal hari yang sama pada minggu sebelumnya sebagai pengingat.
            tanggal_minggu_lalu = tanggal_jurnal - timedelta(days=7)
            jurnal_minggu_lalu = next(
                (r for r in semua_jurnal_tutor
                 if str(r.get("Tanggal", "")) == tanggal_minggu_lalu.strftime("%Y-%m-%d")),
                None
            )
            if jurnal_minggu_lalu:
                with st.expander(
                    f"🔔 Catatan {tanggal_minggu_lalu.strftime('%A, %d %B %Y')} — pengingat minggu lalu",
                    expanded=True
                ):
                    st.caption("Referensi untuk membantu mengingat kegiatan pada hari yang sama minggu sebelumnya.")
                    nama_lalu = _parse_json_list(jurnal_minggu_lalu.get("Daftar_Siswa", "[]"))
                    mapel_lalu = _parse_json_list(jurnal_minggu_lalu.get("Daftar_Mapel", "[]"))
                    st.markdown("**Siswa yang belajar**")
                    st.write(", ".join(
                        [str(x.get("nama", "")) + (f" ({x.get('kelas', '')})" if x.get("kelas") else "")
                         if isinstance(x, dict) else str(x) for x in nama_lalu]
                    ) or "Belum dicatat")
                    st.markdown("**Mata pelajaran**")
                    st.write(", ".join(map(str, mapel_lalu)) or "Belum dicatat")
                    if jurnal_minggu_lalu.get("Materi_Dibahas"):
                        st.markdown("**Materi**")
                        st.write(jurnal_minggu_lalu.get("Materi_Dibahas"))
                    if jurnal_minggu_lalu.get("Evaluasi_Harian"):
                        st.markdown("**Evaluasi sebelumnya**")
                        st.write(jurnal_minggu_lalu.get("Evaluasi_Harian"))
                    if jurnal_minggu_lalu.get("Pengingat_Berikutnya"):
                        st.info("Pengingat sebelumnya: " + jurnal_minggu_lalu.get("Pengingat_Berikutnya"))

            with st.container(border=True):
                st.markdown("#### 🗒️ CATATAN / PERTEMUAN")
                st.caption(
                    "Tuliskan siapa saja yang belajar hari ini. Nama boleh ditulis satu per baris; "
                    "tidak harus membuat entri terpisah untuk setiap sesi."
                )
                siswa_default = _parse_json_list(jurnal_terpilih.get("Daftar_Siswa", "[]")) if jurnal_terpilih else []
                if siswa_default and isinstance(siswa_default[0], dict):
                    siswa_default_text = "\n".join(
                        str(x.get("nama", "")) + (f" — {x.get('kelas', '')}" if x.get("kelas") else "")
                        for x in siswa_default
                    )
                else:
                    siswa_default_text = "\n".join(map(str, siswa_default))

                mapel_default = _parse_json_list(jurnal_terpilih.get("Daftar_Mapel", "[]")) if jurnal_terpilih else []
                mapel_default_pilihan = [x for x in mapel_default if x in MAPEL_OPTIONS]
                mapel_default_manual = ", ".join(x for x in mapel_default if x not in MAPEL_OPTIONS)
                # Jurnal harian sengaja tidak memuat daftar seluruh siswa.
                # Tutor menulis nama/kelompok yang benar-benar diajar hari itu.
                with st.form("form_jurnal_harian_tutor", clear_on_submit=False, enter_to_submit=False):
                    daftar_siswa_text = st.text_area(
                        "Siapa saja yang belajar hari ini?",
                        value=siswa_default_text,
                        height=105,
                        placeholder="Contoh:\nAnak A — Kelas 8\nAnak B — Kelas 6\nKelompok 3 anak — Kelas 7",
                        key=f"jurnal_siswa_{tanggal_jurnal_text}"
                    )
                    daftar_mapel = st.multiselect(
                        "Mata pelajaran yang diajarkan (boleh pilih banyak)",
                        options=MAPEL_OPTIONS,
                        default=mapel_default_pilihan,
                        key=f"jurnal_mapel_{tanggal_jurnal_text}"
                    )
                    mapel_manual = st.text_input(
                        "Mapel lain (opsional, pisahkan dengan koma)",
                        value=mapel_default_manual,
                        placeholder="Contoh: Kaligrafi, Tahfiz",
                        key=f"jurnal_mapel_manual_{tanggal_jurnal_text}"
                    )
                    materi_default = jurnal_terpilih.get("Materi_Dibahas", "") if jurnal_terpilih else ""
                    materi_dibahas = st.text_area(
                        "Materi yang dibahas",
                        value=materi_default,
                        height=110,
                        placeholder="Contoh:\nIPA: Sistem pernapasan\nMatematika: Pecahan dan perbandingan\nBahasa Inggris: Simple Present",
                        key=f"jurnal_materi_{tanggal_jurnal_text}"
                    )
                    evaluasi_default = jurnal_terpilih.get("Evaluasi_Harian", "") if jurnal_terpilih else ""
                    evaluasi_harian = st.text_area(
                        "Evaluasi harian (boleh diisi nanti)",
                        value=evaluasi_default,
                        height=100,
                        placeholder="Apa yang sudah dipahami siswa? Apa yang masih perlu dilatih?",
                        key=f"jurnal_evaluasi_{tanggal_jurnal_text}"
                    )
                    catatan_default = jurnal_terpilih.get("Catatan_Tutor", "") if jurnal_terpilih else ""
                    catatan_pribadi_harian = st.text_area(
                        "Catatan pribadi tutor",
                        value=catatan_default,
                        height=90,
                        placeholder="Catatan untuk dirimu sendiri, bukan laporan orang tua...",
                        key=f"jurnal_pribadi_{tanggal_jurnal_text}"
                    )
                    pengingat_default = jurnal_terpilih.get("Pengingat_Berikutnya", "") if jurnal_terpilih else ""
                    pengingat_mingguan = st.text_area(
                        "Pengingat untuk hari yang sama minggu depan",
                        value=pengingat_default,
                        height=80,
                        placeholder="Contoh: Siapkan latihan tambahan pecahan dan lanjutkan materi IPA.",
                        key=f"jurnal_pengingat_{tanggal_jurnal_text}"
                    )
                    simpan_jurnal = st.form_submit_button(
                        "💾 Simpan / Perbarui Jurnal Harian", use_container_width=True
                    )

                if simpan_jurnal:
                    try:
                        siswa_baris = [
                            x.strip() for x in daftar_siswa_text.splitlines() if x.strip()
                        ]
                        # Nama ditulis bebas; format "Nama — Kelas" dipisah untuk memudahkan pencarian.
                        siswa_terstruktur = []
                        for baris_siswa in siswa_baris:
                            if "—" in baris_siswa:
                                nama_siswa, kelas_siswa = baris_siswa.split("—", 1)
                            elif " - " in baris_siswa:
                                nama_siswa, kelas_siswa = baris_siswa.split(" - ", 1)
                            else:
                                nama_siswa, kelas_siswa = baris_siswa, ""
                            siswa_terstruktur.append({
                                "nama": nama_siswa.strip(), "kelas": kelas_siswa.strip()
                            })
                        semua_mapel = list(daftar_mapel)
                        for item_mapel in mapel_manual.split(","):
                            item_mapel = item_mapel.strip()
                            if item_mapel and item_mapel not in semua_mapel:
                                semua_mapel.append(item_mapel)
                        simpan_atau_perbarui_jurnal(
                            id_user_aktif, id_tutor_aktif, tanggal_jurnal_text,
                            siswa_terstruktur, semua_mapel, materi_dibahas,
                            evaluasi_harian, catatan_pribadi_harian, pengingat_mingguan
                        )
                        st.success("Jurnal harian berhasil disimpan. Kamu bisa membukanya dan memperbaruinya kapan saja.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Jurnal belum tersimpan: {exc}")

            # Riwayat jurnal untuk membuka tanggal lama.
            with st.expander("📚 Riwayat jurnal mengajar", expanded=False):
                if semua_jurnal_tutor:
                    for jurnal in sorted(
                        semua_jurnal_tutor, key=lambda x: str(x.get("Tanggal", "")), reverse=True
                    )[:20]:
                        tgl = str(jurnal.get("Tanggal", ""))
                        nama_list = _parse_json_list(jurnal.get("Daftar_Siswa", "[]"))
                        nama_ringkas = ", ".join(
                            str(x.get("nama", "")) if isinstance(x, dict) else str(x)
                            for x in nama_list[:3]
                        )
                        st.markdown(f"**{tgl}**")
                        st.caption(nama_ringkas or "Belum ada nama siswa")
                        st.divider()
                    st.caption("Untuk membuka jurnal lama, ubah Tanggal jurnal pada pemilih tanggal di atas.")
                else:
                    st.caption("Belum ada jurnal yang tersimpan.")

            # CATATAN KHUSUS SISWA: riwayat tutor pribadi, tidak dikirim ke orang tua.
            st.markdown("#### 👤 Catatan Khusus Siswa")
            st.caption(
                "Pilih nama siswa untuk membuka riwayat perkembangan, kesulitan, perhatian, "
                "dan rencana belajar. Catatan ini hanya untuk tutor."
            )
            # Pilihan catatan khusus dibatasi pada nama yang pernah dicatat tutor sendiri.
            nama_siswa_opsi = []
            nama_siswa_jurnal = [
                x.get("nama", "") for x in _parse_json_list(
                    jurnal_terpilih.get("Daftar_Siswa", "[]") if jurnal_terpilih else "[]"
                ) if isinstance(x, dict) and x.get("nama")
            ]
            nama_siswa_opsi = sorted(set(nama_siswa_opsi + nama_siswa_jurnal), key=str.casefold)
            with st.expander("Buka / tambah catatan khusus siswa", expanded=False):
                pilihan_manual = st.text_input(
                    "Nama siswa", placeholder="Ketik nama siswa jika tidak ada di daftar",
                    key="nama_siswa_catatan_khusus"
                )
                if nama_siswa_opsi:
                    nama_pilihan = st.selectbox(
                        "Atau pilih siswa", options=[""] + nama_siswa_opsi,
                        key="pilih_nama_catatan_khusus"
                    )
                else:
                    nama_pilihan = ""
                nama_target_catatan = pilihan_manual.strip() or nama_pilihan
                if nama_target_catatan:
                    try:
                        riwayat_perkembangan = ambil_catatan_perkembangan_siswa(
                            id_user_aktif, nama_target_catatan
                        )
                    except Exception as exc:
                        riwayat_perkembangan = []
                        st.warning(f"Riwayat siswa belum dapat dimuat: {exc}")
                    if riwayat_perkembangan:
                        st.markdown("**Riwayat catatan sebelumnya**")
                        for catatan_siswa in riwayat_perkembangan[-5:][::-1]:
                            st.markdown(f"**{catatan_siswa.get('Tanggal_Catatan', '-')} · {catatan_siswa.get('Kelas', '-') }**")
                            if catatan_siswa.get("Perkembangan"):
                                st.write("Perkembangan: " + catatan_siswa.get("Perkembangan"))
                            if catatan_siswa.get("Kesulitan"):
                                st.write("Kesulitan: " + catatan_siswa.get("Kesulitan"))
                            if catatan_siswa.get("Perhatian_Tutor"):
                                st.write("Perhatian tutor: " + catatan_siswa.get("Perhatian_Tutor"))
                            if catatan_siswa.get("Rencana_Berikutnya"):
                                st.info("Rencana: " + catatan_siswa.get("Rencana_Berikutnya"))
                            st.divider()
                    with st.form("form_catatan_khusus_siswa", clear_on_submit=True, enter_to_submit=False):
                        kelas_catatan_siswa = st.text_input("Kelas", placeholder="Contoh: Kelas 8")
                        perkembangan_siswa = st.text_area("Perkembangan", placeholder="Apa yang sudah dikuasai?")
                        kesulitan_siswa = st.text_area("Kesulitan", placeholder="Apa yang masih sulit?")
                        perhatian_siswa = st.text_area("Perhatian tutor", placeholder="Hal yang perlu diingat saat mengajar anak ini.")
                        rencana_siswa = st.text_area("Rencana berikutnya", placeholder="Latihan atau materi lanjutan.")
                        simpan_catatan_siswa = st.form_submit_button(
                            "💾 Simpan catatan siswa", use_container_width=True
                        )
                    if simpan_catatan_siswa:
                        try:
                            simpan_catatan_perkembangan_siswa(
                                id_user_aktif, id_tutor_aktif, nama_target_catatan,
                                kelas_catatan_siswa, tanggal_jurnal_text,
                                perkembangan_siswa, kesulitan_siswa,
                                perhatian_siswa, rencana_siswa
                            )
                            st.success("Catatan perkembangan siswa tersimpan secara pribadi.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Catatan siswa belum tersimpan: {exc}")

            st.markdown("## Penampil Media")
            id_user_library = str(st.session_state.get("tutor_user_id", "")).strip()
            id_tutor_library = str(st.session_state.get("tutor_id", "")).strip()

            with st.container(border=True):
                kata_kunci_library = st.text_input(
                    "Cari materi", placeholder="Cari materi, misalnya: Trigonometri",
                    key="kata_kunci_library_tutor"
                )
                sumber_library = st.radio(
                    "Sumber materi", ["Semua sumber", "Library Saya", "Google Drive"],
                    horizontal=True, key="sumber_library_tutor"
                )
                if st.button("🔎 Cari Materi", key="cari_library_tutor", use_container_width=True):
                    hasil_library = []
                    kesalahan_library = []
                    if sumber_library in ("Semua sumber", "Library Saya"):
                        try:
                            hasil_library.extend(ambil_library_tutor(id_user_library, kata_kunci_library))
                        except Exception as exc:
                            kesalahan_library.append(f"Library Saya: {exc}")
                    if sumber_library in ("Semua sumber", "Google Drive") and kata_kunci_library.strip():
                        try:
                            hasil_drive = cari_file_google_drive(kata_kunci_library.strip())
                            for item in hasil_drive:
                                item["source"] = "Google Drive"
                            hasil_library.extend(hasil_drive)
                        except Exception as exc:
                            kesalahan_library.append(f"Google Drive: {exc}")
                    # Gabungkan tanpa menggandakan file berdasarkan ID Drive.
                    unik, seen = [], set()
                    for item in hasil_library:
                        fid = str(item.get("id", ""))
                        if fid and fid not in seen:
                            seen.add(fid)
                            unik.append(item)
                    st.session_state["hasil_library_tutor"] = unik
                    st.session_state["kata_kunci_hasil_library_tutor"] = kata_kunci_library.strip()
                    st.session_state.pop("pilih_hasil_library_tutor", None)
                    st.session_state.pop("media_preview_tutor", None)
                    st.session_state.pop("media_preview_upload_gallery_tutor", None)
                    st.session_state["error_library_tutor"] = kesalahan_library

                for err in st.session_state.get("error_library_tutor", []):
                    st.warning(err)

                hasil_library = st.session_state.get("hasil_library_tutor", [])
                if hasil_library:
                    st.caption(f"Ditemukan {len(hasil_library)} materi.")
                    idx_media = st.selectbox(
                        "Pilih materi untuk ditampilkan",
                        options=range(len(hasil_library)),
                        format_func=lambda i: (
                            f"{hasil_library[i].get('name', 'Tanpa nama')} "
                            f"· {hasil_library[i].get('source', 'Drive')}"
                        ),
                        key="pilih_hasil_library_tutor"
                    )
                    media_pilihan = hasil_library[idx_media]
                    st.session_state["media_preview_tutor"] = media_pilihan
                    st.session_state.pop("media_preview_upload_gallery_tutor", None)
                elif st.session_state.get("kata_kunci_hasil_library_tutor"):
                    st.info("Belum ada materi yang cocok pada sumber yang dipilih.")

                with st.expander("＋ Tambahkan materi ke Library Saya", expanded=False):
                    st.caption(
                        "Pilih file dari File Manager HP/laptop. File akan diunggah satu kali ke Drive "
                        "dan dicatat sebagai koleksi pribadi akun tutor ini."
                    )
                    file_lokal = st.file_uploader(
                        "Pilih materi (boleh beberapa gambar sekaligus)",
                        type=["pdf", "png", "jpg", "jpeg", "webp", "mp3", "wav", "m4a", "ogg", "aac", "mp4", "mov", "webm", "m4v"],
                        accept_multiple_files=True, key="upload_media_beranda_tutor"
                    )
                    kata_kunci_simpan = st.text_input(
                        "Kata kunci / kategori (opsional)",
                        placeholder="Contoh: Matematika, Trigonometri, Kelas 8",
                        key="kata_kunci_simpan_library_tutor"
                    )
                    if not file_lokal:
                        st.caption(
                            "Pilih file dulu, lalu tekan Simpan. Jika file bertanda ❗ merah, "
                            "hapus (✖) dan pilih ulang, atau periksa koneksi internet."
                        )
                    if st.button(
                        "⬆️ Simpan ke Library Saya", key="unggah_media_beranda_tutor",
                        use_container_width=True
                    ):
                        berhasil, gagal = [], []
                        if not file_lokal:
                            st.warning("Belum ada file yang dipilih atau file gagal terunggah (❗). Pilih ulang file-nya.")
                        with st.spinner("Mengunggah dan menyimpan indeks library..."):
                            for satu_file in file_lokal:
                                try:
                                    data_file = satu_file.getvalue()
                                    if len(data_file) > 10 * 1024 * 1024:
                                        raise ValueError("Ukuran maksimal 10 MB per file.")
                                    url_file = upload_lampiran_ke_drive(
                                        data_file, satu_file.name, satu_file.type
                                    )
                                    simpan_media_ke_library(
                                        id_user_library, id_tutor_library,
                                        satu_file.name, satu_file.type, url_file,
                                        len(data_file), kata_kunci_simpan
                                    )
                                    berhasil.append(satu_file.name)
                                except Exception as exc:
                                    gagal.append(f"{satu_file.name}: {exc}")
                        if berhasil:
                            st.success(f"{len(berhasil)} file tersimpan di Library Saya.")
                            st.session_state["hasil_library_tutor"] = ambil_library_tutor(id_user_library, "")
                            st.session_state["kata_kunci_hasil_library_tutor"] = ""
                            st.rerun()
                        for pesan in gagal:
                            st.error(pesan)

                # Satu area penampil untuk file hasil pencarian maupun unggahan baru.
                media_preview = st.session_state.get("media_preview_tutor")
                gallery_preview = st.session_state.get("media_preview_upload_gallery_tutor", [])
                if media_preview:
                    st.caption("Sumber: " + str(media_preview.get("source", "Google Drive")))
                    tampilkan_file_ruang_tutor(media_preview)
                elif gallery_preview:
                    st.markdown("**Materi yang baru diunggah**")
                    for item in gallery_preview:
                        fid = drive_id(item.get("url", ""))
                        if fid:
                            tampilkan_file_ruang_tutor({
                                "id": fid, "name": item.get("name", "Materi"),
                                "mimeType": item.get("mime", ""),
                                "webViewLink": item.get("url", "")
                            })
                else:
                    st.markdown(
                        "<div style='background:#f1f3f5;border-radius:12px;padding:42px 16px;"
                        "text-align:center;margin-top:12px;'>"
                        "<div style='font-size:34px;'>▣</div>"
                        "<div style='font-size:20px;color:#606770;'>PDF · JPG · Video · Audio</div>"
                        "<div style='font-size:16px;color:#777;margin-top:6px;'>Pilih materi dari Drive atau Library Saya</div>"
                        "</div>", unsafe_allow_html=True
                    )

            st.divider()
            tampilkan_papan_tutor(id_user_aktif, id_tutor_aktif)

        elif menu_tutor == "⚙️ Pengaturan Akun":
                st.header("⚙️ Pengaturan Akun")
                st.caption("Ubah PIN hanya saat diperlukan. Username dan identitas akun tidak berubah.")
                akun_tutor_aktif = None
                if st.session_state.get("tutor_baris"):
                    akun_tutor_aktif = next((
                        r for r in baca_records_aman(get_worksheet("Akun_Pengguna"))
                        if int(r.get("_baris", 0)) == int(st.session_state.tutor_baris)
                    ), None)
                if akun_tutor_aktif:
                    form_ganti_pin(
                        get_worksheet("Akun_Pengguna"),
                        akun_tutor_aktif,
                        "PIN_Password",
                        "tutor",
                        identity_field="ID_User",
                        identity_value=st.session_state.get("tutor_user_id", "")
                    )
                else:
                    st.warning("Data akun tutor belum ditemukan. Silakan logout lalu login kembali.")
                with st.expander("🔔 Notifikasi Telegram (Focus Alert)", expanded=False):
                    tutor_id_notif = str(st.session_state.get("tutor_id", "")).strip()
                    chat_id_tersimpan = ambil_chat_id_tutor_sheet(tutor_id_notif)
                    st.caption("Daftarkan Chat ID Telegram pribadi agar Focus Alert tugas yang Anda berikan masuk ke chat Anda sendiri.")
                    chat_id_input = st.text_input(
                        "Chat ID Telegram pribadi",
                        value=chat_id_tersimpan,
                        key=f"chat_id_telegram_tutor_{tutor_id_notif}",
                        placeholder="Contoh: 123456789",
                        help="Ambil Chat ID dengan BotNazmaAntiCurang setelah Anda mengirim /start atau pesan ke bot tersebut. Jangan masukkan token bot."
                    )
                    if st.button("Simpan Chat ID", key="simpan_chat_id_telegram_tutor"):
                        ok_simpan, pesan_simpan = simpan_chat_id_tutor(tutor_id_notif, chat_id_input)
                        (st.success if ok_simpan else st.error)(pesan_simpan)
                    if st.button("Kirim pesan uji Telegram", key="tes_telegram_tutor"):
                        ok_tg, pesan_tg = uji_telegram_tutor(
                            tutor_id_notif, st.session_state.get("tutor_nama", "")
                        )
                        (st.success if ok_tg else st.error)(pesan_tg)
                    if st.button("Kirim pesan uji bot Tugas", key="tes_telegram_tugas_tutor"):
                        ok_tg2, pesan_tg2 = uji_telegram_tugas(
                            tutor_id_notif, st.session_state.get("tutor_nama", "")
                        )
                        (st.success if ok_tg2 else st.error)(pesan_tg2)
                    st.caption("Bot Tugas dipakai untuk notifikasi 'tugas selesai dikirim'. Buka bot itu di Telegram dan tekan Start sekali; setelah itu bunyinya bisa diatur terpisah dari bot Focus Alert.")
                    if NAZMA_FOCUS_COMPONENT is None:
                        st.warning("Folder komponen nazma_focus_component tidak ditemukan, jadi pendeteksi keluar halaman belum aktif.")

        elif menu_tutor == "📝 Persiapan Sesi & Bank Soal":
                st.header("📖 Persiapan Sesi Pembelajaran")
                siswa_aktif = get_siswa_aktif()

                search_query = st.text_input("🔍 Cari nama siswa yang sedang diajar:", key="tutor_cari_siswa").strip().lower()
                hasil_pencarian, pesan_cari = cari_siswa_terbatas(search_query, siswa_aktif)
                selected_siswa = None
                if hasil_pencarian:
                    pilihan = st.selectbox("Pilih siswa:", hasil_pencarian, key="tutor_pilih_siswa")
                    selected_siswa = pilihan
                    if pesan_cari:
                        st.caption(pesan_cari)
                elif search_query:
                    st.warning(pesan_cari or "Siswa aktif tidak ditemukan.")
                else:
                    st.info("Ketik nama siswa untuk menyiapkan materi dan tugas.")

                if selected_siswa:
                    st.markdown("---")
                    st.subheader(f"📚 Rencana tugas untuk: {selected_siswa}")
                    st.caption("Setiap tugas disimpan sebagai catatan tersendiri sehingga satu siswa dapat menerima beberapa tugas dari beberapa mata pelajaran.")
                    st.caption("Mau menambah atau mengonversi soal baru? Buka menu **📚 Koleksi Soal** di sebelah kiri.")

                    # Draft tugas disimpan di session state sampai tutor menekan tombol simpan.
                    draft_key = f"draft_tugas_{selected_siswa}"
                    if draft_key not in st.session_state:
                        try:
                            id_siswa_draft = get_siswa_id_by_nama(selected_siswa)
                            st.session_state[draft_key] = ambil_draft_tugas_persisten(
                                id_siswa_draft, st.session_state.get("tutor_nama", "")
                            )
                        except Exception:
                            st.session_state[draft_key] = []

                    # Pulihkan pekerjaan form yang belum dipindahkan ke daftar draft.
                    id_siswa_form = get_siswa_id_by_nama(selected_siswa)
                    tutor_form = st.session_state.get("tutor_nama", "")
                    recovery_key = _kunci_autosave_form(id_siswa_form, tutor_form)
                    keputusan_key = f"_nazma_form_recovery_decided_{recovery_key}"
                    dicek_key = f"_nazma_form_dicek_{recovery_key}"
                    pekerjaan_aktif = None
                    try:
                        if not st.session_state.get(dicek_key) and not st.session_state.get(keputusan_key):
                            pekerjaan_aktif = ambil_form_aktif_persisten(id_siswa_form, tutor_form)
                            if not pekerjaan_aktif:
                                st.session_state[dicek_key] = True
                    except Exception as exc:
                        pekerjaan_aktif = None
                        st.error(f"Status pekerjaan terakhir tidak dapat diperiksa dari Google Sheets: {exc}")

                    if pekerjaan_aktif and not st.session_state.get(keputusan_key):
                        st.warning(
                            "Ada pekerjaan yang belum selesai untuk siswa ini. "
                            f"Pembaruan terakhir: {pekerjaan_aktif.get('Diperbarui_Pada') or 'waktu tidak tersedia'}."
                        )
                        col_lanjut, col_baru = st.columns(2)
                        with col_lanjut:
                            if st.button("↩ Lanjutkan pekerjaan terakhir", key=f"pulihkan_form_{recovery_key}", type="primary"):
                                st.session_state["_nazma_form_restore_payload"] = pekerjaan_aktif["payload"]
                                st.session_state[keputusan_key] = True
                                st.rerun()
                        with col_baru:
                            if st.button("＋ Mulai pekerjaan baru", key=f"baru_form_{recovery_key}"):
                                nomor_lama = int(pekerjaan_aktif["payload"].get("form_n", st.session_state.get("form_n", 0)) or 0)
                                ubah_status_form_aktif(id_siswa_form, tutor_form, "Diarsipkan")
                                st.session_state["form_n"] = max(int(st.session_state.get("form_n", 0)), nomor_lama + 1)
                                st.session_state[keputusan_key] = True
                                st.rerun()

                    # Terapkan state sebelum widget dibuat agar Streamlit tidak menolak perubahan session_state.
                    payload_pulih = st.session_state.pop("_nazma_form_restore_payload", None)
                    if isinstance(payload_pulih, dict):
                        n_pulih = int(payload_pulih.get("form_n", 0) or 0)
                        st.session_state["form_n"] = n_pulih
                        k_pulih = f"{selected_siswa}_{n_pulih}"
                        for nama_widget, nilai_widget in (payload_pulih.get("widget_state", {}) or {}).items():
                            if _kunci_tombol(nama_widget):
                                continue  # draft lama mungkin memuat kunci tombol; jangan ditulis balik
                            st.session_state[nama_widget] = nilai_widget
                        st.session_state[f"_source_identity_{k_pulih}"] = payload_pulih.get("source_identity", "")
                        st.session_state[f"_autosave_files_{k_pulih}"] = payload_pulih.get("files", []) or []
                        st.session_state[f"_nazma_restored_notice_{k_pulih}"] = True
                        st.session_state[recovery_key] = payload_pulih
                        restored_json = json.dumps(
                            _serialisasi_form_aman(payload_pulih), ensure_ascii=False, sort_keys=True
                        )
                        st.session_state[f"_nazma_form_autosave_hash_{recovery_key}"] = hashlib.sha256(
                            restored_json.encode("utf-8")
                        ).hexdigest()

                    with st.expander("➕ Buat tugas baru", expanded=True):
                        # Widget biasa (bukan st.form) supaya pilihan sumber/kategori langsung mengubah isian di bawahnya.
                        n_form = st.session_state.get("form_n", 0)
                        k = f"{selected_siswa}_{n_form}"
                        if st.session_state.pop(f"_nazma_restored_notice_{k}", False):
                            st.success("Pekerjaan terakhir berhasil dipulihkan. Periksa kembali sebelum melanjutkan.")
                        notice_bank = st.session_state.pop("_nazma_bank_berkas_notice", None)
                        if notice_bank:
                            st.info(notice_bank)

                        kategori_label = st.radio("Kategori penugasan:", [KATEGORI_SESI, KATEGORI_PR], key=f"kt_{k}")
                        untuk_pr = kategori_label == KATEGORI_PR
                        mapel_tugas = st.selectbox("Mata pelajaran:", MAPEL_OPTIONS, key=f"mp_{k}")
                        judul_tugas = st.text_input("Judul / topik tugas:", key=f"jd_{k}")
                        if st.session_state.get("_koleksi_pakai"):
                            # Sekali pakai: arahkan sumber ke Bank Berkas, lalu bebaskan pilihan sumber lagi.
                            st.session_state[f"sm_{k}"] = SUMBER_BERKAS
                            st.session_state["_koleksi_pakai_aktif"] = st.session_state.pop("_koleksi_pakai")
                        sumber_tugas = st.radio(
                            "Sumber materi / soal:",
                            [SUMBER_BANK, SUMBER_BERKAS, SUMBER_DRIVE, SUMBER_UPLOAD],
                            key=f"sm_{k}",
                            on_change=reset_mode_pengerjaan_widget,
                            args=(k,)
                        )
                        # Sumber soal harus dipilih dan tersedia sebelum tutor menentukan cara pengerjaan.
                        jenis_tugas = "Online"  # nilai kompatibilitas untuk kategori tugas lama
                        mode_widget_key = f"mode_{k}"
                        source_identity_key = f"_source_identity_{k}"

                        link_tugas = ""
                        file_tugas = []
                        soal_dipilih = []
                        berkas_files = []
                        berkas_template = []

                        if sumber_tugas == SUMBER_BANK:
                            try:
                                bank = get_bank_soal()
                            except Exception as e:
                                bank = []
                                st.error(f"Bank soal belum dapat dibaca: {e}")
                            if not bank:
                                st.info("Bank_Soal_Master belum berisi soal berstatus Aktif.")
                            else:
                                def _opsi(kolom):
                                    return ["Semua"] + sorted({str(q.get(kolom, "")).strip() for q in bank if str(q.get(kolom, "")).strip()})
                                jenjang_filter = st.selectbox("Filter jenjang soal:", _opsi("Jenjang"), key=f"fj_{k}")
                                kelas_filter = st.selectbox("Filter kelas soal:", _opsi("Kelas"), key=f"fk_{k}")
                                mapel_filter = st.selectbox("Filter mapel soal:", _opsi("Mapel"), key=f"fm_{k}")
                                topik_filter = st.selectbox("Filter topik soal:", _opsi("Bab_Atau_Topik"), key=f"ft_{k}")
                                bentuk_filter = st.selectbox("Filter bentuk soal:", _opsi("Bentuk_Soal"), key=f"fb_{k}")
                                bank_filter = [
                                    q for q in bank
                                    if (jenjang_filter == "Semua" or str(q.get("Jenjang", "")).strip() == jenjang_filter)
                                    and (kelas_filter == "Semua" or str(q.get("Kelas", "")).strip() == kelas_filter)
                                    and (mapel_filter == "Semua" or str(q.get("Mapel", "")).strip() == mapel_filter)
                                    and (topik_filter == "Semua" or str(q.get("Bab_Atau_Topik", "")).strip() == topik_filter)
                                    and (bentuk_filter == "Semua" or str(q.get("Bentuk_Soal", "")).strip() == bentuk_filter)
                                ]
                                kunci_pilih = f"ps_{k}_{jenjang_filter}_{kelas_filter}_{mapel_filter}_{topik_filter}_{bentuk_filter}"
                                peta_soal = {}
                                for q in reversed(bank_filter):  # soal terbaru (baris paling bawah) tampil di atas
                                    kode = str(q.get("Kode_Soal", "")).strip() or f"BARIS-{q.get('_baris')}"
                                    peta_soal[kode] = q
                                kode_dipilih = st.multiselect(
                                    f"Pilih soal untuk tugas ini ({len(peta_soal)} soal tersedia):",
                                    options=list(peta_soal.keys()),
                                    format_func=lambda c: f"{c} | {pisah_wacana(peta_soal[c].get('Teks_Soal', ''))[1][:100]}",
                                    key=kunci_pilih
                                )
                                for kode in kode_dipilih:
                                    try:
                                        soal_dipilih.append(ubah_soal_untuk_tugas(peta_soal[kode]))
                                    except Exception as e:
                                        st.warning(f"Soal {kode} dilewati: {e}")

                                if soal_dipilih:
                                    st.caption("Soal, tipe, opsi, dan kunci diambil langsung dari Bank Soal Master. Tidak perlu konfigurasi ulang.")

                            source_ready = bool(soal_dipilih)
                            mode_pengerjaan = TASK_MODE_ONLINE
                            source_identity = "bank:" + "|".join(
                                str(q.get("ID_Soal", "")) for q in soal_dipilih
                            )
                            if source_ready:
                                st.caption("Lembar jawaban online akan dibuat otomatis dari soal yang dipilih.")

                        elif sumber_tugas == SUMBER_BERKAS:
                            hasil_berkas = pilih_berkas_dari_bank(k, st.session_state.get("tutor_nama", ""))
                            berkas_files = hasil_berkas["files"]
                            berkas_template = hasil_berkas["template"]
                            source_ready = bool(berkas_files)
                            source_identity = "berkas:" + hasil_berkas["id"]

                        elif sumber_tugas == SUMBER_DRIVE:
                            link_tugas = st.text_area(
                                "Masukkan link Google Drive / Flipbook (satu link per baris):",
                                placeholder="https://...",
                                key=f"lk_{k}"
                            )
                            link_list_sumber = [x.strip() for x in link_tugas.splitlines() if x.strip()]
                            link_valid = bool(link_list_sumber) and all(
                                x.lower().startswith(("http://", "https://")) for x in link_list_sumber
                            )
                            source_ready = link_valid
                            source_identity = "drive:" + "|".join(link_list_sumber)
                            if link_list_sumber and not link_valid:
                                st.warning("Periksa tautan. Setiap link harus diawali http:// atau https://.")

                        else:
                            file_tugas = st.file_uploader(
                                "Unggah file soal/materi dari perangkat (PDF, dokumen, gambar, audio, video):",
                                type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg", "webp",
                                      "mp4", "mov", "webm", "m4v", "mp3", "wav", "m4a", "ogg", "aac"],
                                accept_multiple_files=True,
                                key=f"up_{k}"
                            )
                            daftar_file_sumber = list(file_tugas or [])
                            autosave_files_key = f"_autosave_files_{k}"
                            autosave_files = list(st.session_state.get(autosave_files_key, []) or [])
                            identitas_file = [
                                hashlib.sha256(f.getvalue()).hexdigest()
                                for f in daftar_file_sumber
                            ]
                            hash_tersimpan = {str(x.get("sha256", "")) for x in autosave_files}
                            # File baru ditambahkan ke lampiran tersimpan; penghapusan dilakukan lewat tombol khusus.
                            file_gagal_autosave = []
                            for f, hash_file in zip(daftar_file_sumber, identitas_file):
                                if hash_file in hash_tersimpan:
                                    continue
                                try:
                                    url_file = upload_lampiran_ke_drive(
                                        f.getvalue(), f.name, f.type or "application/octet-stream"
                                    )
                                    autosave_files.append({
                                        "name": f.name, "mime": f.type or "application/octet-stream",
                                        "url": url_file, "uploaded": True, "sha256": hash_file
                                    })
                                    hash_tersimpan.add(hash_file)
                                except Exception as exc:
                                    file_gagal_autosave.append(f"{f.name}: {exc}")
                            st.session_state[autosave_files_key] = autosave_files
                            if file_gagal_autosave:
                                st.error("Lampiran belum berhasil diamankan untuk pemulihan: " + "; ".join(file_gagal_autosave))
                            if autosave_files:
                                st.caption(f"{len(autosave_files)} lampiran sudah diamankan di Google Drive untuk pemulihan.")
                                st.button("Hapus lampiran tersimpan", key=f"hapus_lampiran_autosave_{k}",
                                          on_click=_hapus_lampiran_autosave, args=(k,))
                            identitas_persisten = [str(x.get("sha256", "")) for x in autosave_files if x.get("sha256")]
                            source_ready = (
                                bool(autosave_files)
                                and not file_gagal_autosave
                                and len(autosave_files) >= len(daftar_file_sumber)
                            )
                            source_identity = "upload:" + "|".join(sorted(set(identitas_persisten)))

                        if sumber_tugas != SUMBER_UPLOAD:
                            st.session_state.pop(f"_autosave_files_{k}", None)

                        # Langkah 3 alur tutor: setelah sumber materi dipilih, tanya apakah dibagikan ke siswa lain.
                        tampilkan_pilih_siswa_tambahan(selected_siswa, siswa_aktif, dalam_expander=False)

                        # Mode pengerjaan dipilih terpisah dari format sumber materi.
                        if source_ready:
                            mode_pengerjaan = st.radio(
                                "Cara siswa mengerjakan:",
                                [TASK_MODE_ONLINE, TASK_MODE_OFFLINE],
                                horizontal=True,
                                key=f"mode_pengerjaan_{k}"
                            )
                        else:
                            mode_pengerjaan = None

                        daftar_mapel_tugas = [mapel_tugas]
                        unggah_oleh_pilihan = ""
                        if mode_pengerjaan == TASK_MODE_OFFLINE:
                            daftar_mapel_tugas = st.multiselect(
                                "Mata pelajaran yang dinilai (boleh lebih dari satu):",
                                options=MAPEL_OPTIONS,
                                default=[mapel_tugas] if mapel_tugas in MAPEL_OPTIONS else [],
                                key=f"mapel_offline_{k}"
                            )
                            if daftar_mapel_tugas:
                                mapel_tugas = daftar_mapel_tugas[0]
                            st.caption("Setiap mata pelajaran akan memiliki kolom nilai dan catatan tersendiri.")
                            label_unggah_oleh = st.radio(
                                "Siapa yang mengunggah hasil pekerjaan?",
                                ["Siswa unggah sendiri", "Tutor yang mengunggah"],
                                horizontal=True, key=f"unggah_oleh_{k}"
                            )
                            unggah_oleh_pilihan = "siswa" if label_unggah_oleh.startswith("Siswa") else "tutor"

                        # Jika sumber diganti, dihapus, atau isinya berubah, pilihan mode dan konfigurasi lama
                        # direset agar tidak tertaut ke lampiran yang berbeda.
                        identity_lama = st.session_state.get(source_identity_key)
                        identitas_berubah = identity_lama != source_identity
                        if identitas_berubah:
                            st.session_state.pop(mode_widget_key, None)
                            st.session_state.pop(f"jumlah_manual_{k}", None)
                            st.session_state.pop(f"konfigurasi_manual_{k}", None)
                            st.session_state.pop(f"_template_awal_{k}", None)
                            for widget_key in list(st.session_state.keys()):
                                if str(widget_key).startswith(f"cfg_{k}_"):
                                    st.session_state.pop(widget_key, None)
                            st.session_state[source_identity_key] = source_identity
                            if sumber_tugas == SUMBER_BERKAS and berkas_template:
                                # Template yang melekat pada berkas dimuat otomatis: tidak perlu konfigurasi ulang.
                                st.session_state[f"_template_awal_{k}"] = berkas_template
                                st.session_state[f"jumlah_manual_{k}"] = len(berkas_template) or 10

                        # Format sumber (Bank, Drive/Flipbook, PDF, JPG, PNG, dll.)
                        # tidak menentukan mode pengerjaan. Tutor memilih Online atau Offline.
                        if mode_pengerjaan == TASK_MODE_ONLINE and sumber_tugas != SUMBER_BANK and source_ready:
                            st.info("Siswa akan mengerjakan melalui lembar jawaban online. Jika ada soal esai/uraian, siswa mengetik jawabannya dan boleh (opsional) menambahkan foto tulisan tangan.")
                        elif mode_pengerjaan == TASK_MODE_OFFLINE:
                            st.info("Siswa mengerjakan di kertas. Foto hasil pekerjaan dan nilai akan dimasukkan oleh Tutor.")

                        # Konfigurasi custom memakai kartu per nomor, bukan tabel horizontal.
                        masalah_konfigurasi = []
                        gunakan_template_berkas = False
                        if (sumber_tugas == SUMBER_BERKAS and berkas_template and source_ready
                                and mode_pengerjaan == TASK_MODE_ONLINE):
                            ubah_konfigurasi_berkas = st.checkbox(
                                "Ubah konfigurasi lembar jawaban (opsional)", value=False, key=f"ubah_cfg_{k}"
                            )
                            gunakan_template_berkas = not ubah_konfigurasi_berkas
                            if gunakan_template_berkas:
                                st.markdown("#### ⚙️ Lembar jawaban dari template berkas")
                                soal_dipilih = json.loads(json.dumps(berkas_template))
                                for nomor, satu_soal in enumerate(soal_dipilih, 1):
                                    masalah = validasi_konfigurasi_soal(satu_soal)
                                    if masalah:
                                        masalah_konfigurasi.append(f"Nomor {nomor}: " + "; ".join(masalah))
                                tampilkan_pratinjau_lembar_jawaban(soal_dipilih)
                        if (sumber_tugas != SUMBER_BANK and source_ready and mode_pengerjaan == TASK_MODE_ONLINE
                                and not gunakan_template_berkas):
                            st.markdown("#### ⚙️ Konfigurasi lembar jawaban")
                            st.caption(
                                "Atur tipe jawaban dan jumlah nomor. Karena sumber soal berasal dari lampiran/link, "
                                "pertanyaan dan teks opsi tidak perlu diketik ulang. Untuk pilihan ganda, cukup gunakan "
                                "label A, B, C, D. Jawaban esai diketik online; foto tulisan tangan "
                                "bersifat opsional saat pengumpulan. Essay dinilai langsung oleh tutor; "
                                "nilai akhir menunggu persetujuan tutor."
                            )
                            templates = ambil_template_soal(st.session_state.get("tutor_nama", ""))
                            template_map = {
                                f"{x.get('Nama_Template')} · {x.get('Mapel')}": x
                                for x in templates
                            }
                            pilih_template = st.selectbox(
                                "Gunakan template (opsional):",
                                ["— Mulai dari konfigurasi baru —"] + list(template_map.keys()),
                                key=f"template_pilih_{k}"
                            )
                            if st.button("Muat template", key=f"template_muat_{k}",
                                         disabled=pilih_template == "— Mulai dari konfigurasi baru —"):
                                try:
                                    data_tpl = json.loads(template_map[pilih_template].get("Konfigurasi_JSON", "[]"))
                                    st.session_state[f"_template_awal_{k}"] = data_tpl if isinstance(data_tpl, list) else []
                                    st.session_state[f"jumlah_manual_{k}"] = len(st.session_state[f"_template_awal_{k}"]) or 10
                                    for widget_key in list(st.session_state.keys()):
                                        if str(widget_key).startswith(f"cfg_{k}_"):
                                            st.session_state.pop(widget_key, None)
                                    st.success("Template dimuat. Periksa kembali konfigurasi sebelum digunakan.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Template tidak dapat dimuat: {exc}")

                            konfigurasi_awal = st.session_state.get(f"_template_awal_{k}", [])
                            jumlah_default = len(konfigurasi_awal) if konfigurasi_awal else 10
                            jumlah_manual = st.number_input(
                                "Jumlah nomor soal:", min_value=1, max_value=100,
                                value=jumlah_default, step=1, key=f"jumlah_manual_{k}"
                            )
                            soal_dipilih = buat_konfigurasi_kartu_soal(
                                int(jumlah_manual), f"cfg_{k}", konfigurasi_awal
                            )
                            for nomor, satu_soal in enumerate(soal_dipilih, 1):
                                masalah = validasi_konfigurasi_soal(satu_soal)
                                if masalah:
                                    masalah_konfigurasi.append(f"Nomor {nomor}: " + "; ".join(masalah))
                            tampilkan_pratinjau_lembar_jawaban(soal_dipilih)

                            with st.expander("💾 Simpan konfigurasi sebagai template", expanded=False):
                                nama_template_baru = st.text_input(
                                    "Nama template:", key=f"template_nama_{k}",
                                    placeholder="Contoh: 10 PG + 5 Essay"
                                )
                                if st.button("Simpan template", key=f"template_simpan_{k}"):
                                    if masalah_konfigurasi:
                                        st.error("Perbaiki konfigurasi yang belum valid sebelum menyimpan template.")
                                    else:
                                        try:
                                            simpan_template_soal(
                                                nama_template_baru,
                                                st.session_state.get("tutor_nama", ""),
                                                mapel_tugas,
                                                soal_dipilih
                                            )
                                            st.success("Template berhasil disimpan.")
                                            st.rerun()
                                        except Exception as exc:
                                            st.error(f"Template gagal disimpan: {exc}")

                            if masalah_konfigurasi:
                                with st.expander(f"⚠️ Perlu dilengkapi ({len(masalah_konfigurasi)} masalah)", expanded=False):
                                    for pesan in masalah_konfigurasi:
                                        st.warning(pesan)

                        # Detail penugasan dilengkapi setelah sumber dan cara pengerjaan ditentukan.
                        instruksi_tugas = st.text_area("Instruksi untuk siswa:", key=f"in_{k}")
                        # FITUR BARU: durasi dan tenggat mengikuti pengaturan form sebelumnya (siswa/tugas sebelumnya).
                        _kat_waktu = "pr" if untuk_pr else "sesi"
                        _opsi_timer = [0, 15, 30, 45, 60, 90, 120]
                        _timer_idx_awal = 0 if untuk_pr else 2
                        _tenggat_awal = datetime.combine(
                            waktu_lokal().date() + (timedelta(days=3) if untuk_pr else timedelta(days=0)),
                            datetime.strptime("23:59", "%H:%M").time()
                        )
                        _waktu_lalu = st.session_state.get("_nazma_waktu_terakhir", {}).get(_kat_waktu)
                        if (_waktu_lalu and _waktu_lalu["timer"] in _opsi_timer
                                and _waktu_lalu["tenggat"] > waktu_lokal().replace(tzinfo=None)):
                            _timer_idx_awal = _opsi_timer.index(_waktu_lalu["timer"])
                            _tenggat_awal = _waktu_lalu["tenggat"]
                        timer_tugas = st.selectbox(
                            "Durasi pengerjaan:", [0, 15, 30, 45, 60, 90, 120], index=_timer_idx_awal,
                            format_func=lambda x: "Tanpa timer (khusus upload)" if x == 0 else f"{x} menit",
                            key=f"tm_{k}_{'pr' if untuk_pr else 'sesi'}"
                        )
                        tenggat_tugas = st.date_input(
                            "Tanggal tenggat:",
                            value=_tenggat_awal.date(),
                            key=f"tg_{k}_{'pr' if untuk_pr else 'sesi'}"
                        )
                        tenggat_jam = st.time_input(
                            "Jam tenggat:", value=_tenggat_awal.time(),
                            key=f"tgj_{k}_{'pr' if untuk_pr else 'sesi'}"
                        )
                        tenggat_datetime = datetime.combine(tenggat_tugas, tenggat_jam)
                        st.session_state.setdefault("_nazma_waktu_terakhir", {})[_kat_waktu] = {
                            "timer": timer_tugas, "tenggat": tenggat_datetime
                        }
                        mode_online_aktif = mode_pengerjaan == TASK_MODE_ONLINE
                        if mode_online_aktif:
                            st.caption("Tugas online wajib memiliki timer. Timer dimulai ketika siswa menekan tombol Mulai Mengerjakan.")
                        elif mode_pengerjaan == TASK_MODE_OFFLINE:
                            if untuk_pr:
                                st.caption("Timer PR bersifat opsional (pilih 'Tanpa timer' bila tidak diperlukan; tenggat tetap berlaku). Jika diisi, timer berjalan sejak siswa menekan Mulai.")
                            else:
                                st.caption(
                                    "Tugas sesi Offline wajib memakai timer agar siswa fokus. Soal terbuka setelah siswa menekan Mulai."
                                    + (f" Setelah waktu habis siswa mendapat {MASA_UNGGAH_MENIT} menit tambahan khusus untuk mengunggah foto."
                                       if unggah_oleh_pilihan == "siswa" else "")
                                )
                        else:
                            st.caption("Mode lama tanpa timer dipertahankan untuk kompatibilitas data historis.")

                        # Autosave pekerjaan yang belum masuk daftar draft ke Google Sheets.
                        state_form = _ambil_widget_state_form(k)
                        files_form = list(st.session_state.get(f"_autosave_files_{k}", []) or [])
                        ada_pekerjaan = bool(
                            judul_tugas.strip()
                            or link_tugas.strip()
                            or files_form
                            or soal_dipilih
                            or (sumber_tugas != SUMBER_BANK and source_ready and mode_pengerjaan is not None)
                            or instruksi_tugas.strip()
                            or any(
                                ("_rubrik_" in nama and str(nilai or "").strip())
                                or ("_kunci_" in nama and str(nilai or "").strip())
                                or ("_kp_" in nama and str(nilai or "").strip())
                                for nama, nilai in state_form.items()
                            )
                        )
                        if ada_pekerjaan:
                            payload_form = {
                                "form_n": n_form,
                                "widget_state": state_form,
                                "source_identity": source_identity,
                                "files": files_form
                            }
                            payload_json_form = json.dumps(
                                _serialisasi_form_aman(payload_form), ensure_ascii=False, sort_keys=True
                            )
                            payload_hash = hashlib.sha256(payload_json_form.encode("utf-8")).hexdigest()
                            hash_session_key = f"_nazma_form_autosave_hash_{recovery_key}"
                            if st.session_state.get(hash_session_key) != payload_hash:
                                ts_key = f"_nazma_form_autosave_ts_{recovery_key}"
                                sisa_jeda = JEDA_AUTOSAVE_DETIK - (time.time() - float(st.session_state.get(ts_key, 0) or 0))
                                if sisa_jeda > 0:
                                    st.caption("⏳ Perubahan terbaru akan tersimpan otomatis pada interaksi berikutnya.")
                                else:
                                    try:
                                        simpan_form_aktif_persisten(
                                            id_siswa_form, selected_siswa, tutor_form, payload_form
                                        )
                                        st.session_state[hash_session_key] = payload_hash
                                        st.session_state[recovery_key] = payload_form
                                        st.session_state[ts_key] = time.time()
                                        st.caption("✓ Pekerjaan sementara tersimpan otomatis.")
                                    except Exception as exc:
                                        st.error(f"Pekerjaan belum aman tersimpan. Periksa koneksi Google Sheets: {exc}")
                            else:
                                st.caption("✓ Pekerjaan tersimpan.")
                        elif st.session_state.get(recovery_key):
                            st.caption("Pekerjaan sebelumnya masih tersimpan sampai Ibu memilih mulai baru atau memindahkannya ke daftar draft.")

                        simpan_bank_pilihan = None
                        if sumber_tugas == SUMBER_UPLOAD and source_ready:
                            simpan_bank_pilihan = form_simpan_ke_bank(k, judul_tugas, mapel_tugas)
                        elif sumber_tugas == SUMBER_DRIVE and source_ready:
                            # FITUR BARU: link Drive/Flipbook juga bisa disimpan ke bank agar dipakai ulang
                            st.caption(
                                "Ingin link ini dipakai lagi untuk siswa lain? Buka kotak di bawah dan centang Simpan. "
                                "Judul dan mapel terisi otomatis, cukup pilih kelas."
                            )
                            simpan_bank_pilihan = form_simpan_ke_bank(k, judul_tugas, mapel_tugas)

                        tambah_draft = st.button("Tambahkan ke daftar tugas", key=f"tambah_{k}")

                        if tambah_draft:
                            link_list = [x.strip() for x in link_tugas.splitlines() if x.strip()]
                            daftar_file = list(file_tugas or [])
                            total_byte = sum(len(f.getvalue()) for f in daftar_file)

                            if not judul_tugas.strip():
                                st.error("Judul / topik tugas wajib diisi.")
                            elif untuk_pr and tenggat_tugas < waktu_lokal().date():
                                st.error("Tenggat PR tidak boleh sebelum hari ini.")
                            elif mode_pengerjaan == TASK_MODE_ONLINE and int(timer_tugas or 0) <= 0:
                                st.error("Tugas dengan lembar jawaban online wajib memiliki timer lebih dari 0 menit.")
                            elif mode_pengerjaan == TASK_MODE_OFFLINE and not untuk_pr and int(timer_tugas or 0) <= 0:
                                st.error("Tugas sesi Offline wajib memiliki timer lebih dari 0 menit.")
                            elif mode_pengerjaan == TASK_MODE_OFFLINE and not daftar_mapel_tugas:
                                st.error("Pilih minimal satu mata pelajaran untuk tugas Offline.")
                            elif tenggat_datetime <= waktu_lokal().replace(tzinfo=None):
                                st.error("Tanggal dan jam tenggat harus lebih besar dari waktu sekarang.")
                            elif sumber_tugas == SUMBER_BANK and not soal_dipilih:
                                st.error("Pilih minimal satu soal dari Bank Soal Master.")
                            elif sumber_tugas == SUMBER_BERKAS and not berkas_files:
                                st.error("Pilih berkas soal dari Bank Berkas Soal.")
                            elif sumber_tugas != SUMBER_BANK and mode_pengerjaan is None:
                                st.error("Pilih cara siswa mengerjakan: lembar jawaban online atau upload hasil tulisan tangan.")
                            elif sumber_tugas == SUMBER_DRIVE and not link_list:
                                st.error("Masukkan minimal satu link Drive / Flipbook.")
                            elif sumber_tugas == SUMBER_DRIVE and any(not l.lower().startswith(("http://", "https://")) for l in link_list):
                                st.error("Setiap link harus diawali https://")
                            elif sumber_tugas == SUMBER_UPLOAD and not daftar_file and not files_form:
                                st.error("Pilih minimal satu file yang akan dilampirkan.")
                            elif sumber_tugas == SUMBER_UPLOAD and len(files_form) < len(daftar_file):
                                st.error("Sebagian lampiran belum berhasil disimpan ke Google Drive. Coba lagi sebelum membuat draft.")
                            elif any(len(f.getvalue()) > 20 * 1024 * 1024 for f in daftar_file):
                                st.error("Ukuran tiap lampiran maksimal 20 MB. Kompres video/audio lalu unggah kembali.")
                            elif total_byte > 40 * 1024 * 1024:
                                st.error("Total lampiran satu tugas maksimal 40 MB. Bagi menjadi beberapa tugas.")
                            elif sumber_tugas != SUMBER_BANK and mode_pengerjaan == TASK_MODE_ONLINE and masalah_konfigurasi:
                                st.error("Konfigurasi lembar jawaban belum valid. Periksa kartu soal yang ditandai.")
                            else:
                                # Lampiran sudah diamankan di Google Drive saat dipilih agar form aktif dapat dipulihkan.
                                if sumber_tugas == SUMBER_UPLOAD:
                                    files = list(files_form)
                                elif sumber_tugas == SUMBER_BERKAS:
                                    files = list(berkas_files)
                                else:
                                    files = []
                                st.session_state[draft_key].append({
                                    "Mapel": mapel_tugas, "Judul": judul_tugas.strip(),
                                    # Kategori PR disimpan di Jenis_Tugas: "PR Online" / "PR Offline"
                                    "Jenis": f"PR {jenis_tugas}" if untuk_pr else jenis_tugas,
                                    "Sumber": sumber_tugas, "Instruksi": instruksi_tugas.strip(), "Timer": timer_tugas,
                                    "Tenggat": tenggat_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                                    "Links": link_list, "Files": files, "Soal": soal_dipilih,
                                    "Mode_Pengerjaan": mode_pengerjaan,
                                    "Unggah_Oleh": unggah_oleh_pilihan if mode_pengerjaan == TASK_MODE_OFFLINE else "",
                                    "Daftar_Mapel": list(daftar_mapel_tugas or [mapel_tugas])
                                })
                                try:
                                    simpan_draft_tugas_persisten(
                                        get_siswa_id_by_nama(selected_siswa), selected_siswa,
                                        st.session_state.get("tutor_nama", ""),
                                        st.session_state[draft_key]
                                    )
                                except Exception as exc:
                                    st.warning(f"Draft tersimpan di sesi ini, tetapi sinkronisasi Google Sheets gagal: {exc}")
                                try:
                                    ubah_status_form_aktif(id_siswa_form, tutor_form, "Dipindahkan ke daftar draft")
                                except Exception as exc:
                                    st.warning(f"Tugas masuk daftar draft, tetapi status pekerjaan sementara belum diperbarui: {exc}")
                                st.session_state.pop(f"_nazma_form_autosave_hash_{recovery_key}", None)
                                st.session_state.pop(f"_autosave_files_{k}", None)
                                if simpan_bank_pilihan and sumber_tugas == SUMBER_DRIVE:
                                    # FITUR BARU: ubah link menjadi entri lampiran bank (tidak mengubah draft yang sudah dibuat)
                                    files = [
                                        {"name": f"Link materi {no}", "mime": "text/uri-list", "url": u}
                                        for no, u in enumerate(link_list, 1)
                                    ]
                                if simpan_bank_pilihan:
                                    try:
                                        hasil_bank = simpan_berkas_ke_bank(
                                            simpan_bank_pilihan["judul"] or judul_tugas.strip(),
                                            simpan_bank_pilihan["mapel"], simpan_bank_pilihan["kelas"],
                                            simpan_bank_pilihan["topik"], files,
                                            soal_dipilih if mode_pengerjaan == TASK_MODE_ONLINE else [],
                                            st.session_state.get("tutor_nama", ""), simpan_bank_pilihan["dibagikan"]
                                        )
                                        st.session_state["_nazma_bank_berkas_notice"] = (
                                            "📚 Berkas " + ("diperbarui di" if hasil_bank["aksi"] == "diperbarui" else "disimpan ke")
                                            + " Bank Berkas Soal"
                                            + (" beserta template jawabannya." if hasil_bank["template"] else " (tanpa template jawaban).")
                                        )
                                    except Exception as exc:
                                        st.session_state["_nazma_bank_berkas_notice"] = (
                                            f"⚠️ Tugas sudah masuk draft, tetapi berkas belum tersimpan ke bank: {exc}"
                                        )
                                st.session_state["form_n"] = n_form + 1  # kosongkan isian, siap menambah tugas berikutnya
                                st.success("Masuk ke daftar draft. Anda bisa menambah tugas atau PR lain (mapel lain / jenis lain), lalu tekan Simpan & Kirim.")
                                st.rerun()

                    daftar_draft = st.session_state[draft_key]
                    if st.session_state.get("_nazma_notice_tambahan"):
                        st.info(st.session_state.pop("_nazma_notice_tambahan"))
                    st.markdown("### 📋 Daftar tugas yang akan dikirim")
                    if daftar_draft:
                        for i, item in enumerate(daftar_draft, 1):
                            ikon = "📌" if str(item["Jenis"]).startswith("PR") else "📝"
                            label_mapel_item = ", ".join(item.get("Daftar_Mapel", []) or [item.get("Mapel", "")])
                            with st.expander(f"{i}. {ikon} {label_mapel_item} — {item['Judul']} ({item['Jenis']})"):
                                st.write(f"Mata pelajaran: {label_mapel_item}")
                                st.write(f"Sumber: {item['Sumber']}")
                                st.write(f"Mode pengerjaan: {item.get('Mode_Pengerjaan', TASK_MODE_UPLOAD)}")
                                st.write(f"Timer: {'Tanpa timer' if item['Timer'] == 0 else str(item['Timer']) + ' menit'} | Tenggat: {item['Tenggat']}")
                                if item.get("Unggah_Oleh"):
                                    st.write("Hasil diunggah oleh: " + ("Siswa" if item["Unggah_Oleh"] == "siswa" else "Tutor"))
                                st.write(f"Jumlah soal: {len(item['Soal'])}")
                                for link in item.get("Links", []):
                                    st.write(f"Link: {link}")
                                for file_item in item.get("Files", []):
                                    status_file = "sudah tersimpan di Google Drive" if file_item.get("url") else "menunggu diunggah"
                                    st.info(f"Lampiran {status_file}: {file_item['name']}")
                                if st.button("🗑️ Hapus dari daftar", key=f"hapus_item_{selected_siswa}_{i}"):
                                    daftar_draft.pop(i - 1)
                                    try:
                                        simpan_draft_tugas_persisten(
                                            get_siswa_id_by_nama(selected_siswa), selected_siswa,
                                            st.session_state.get("tutor_nama", ""), daftar_draft
                                        )
                                    except Exception:
                                        pass
                                    st.rerun()
                                if st.checkbox("✏️ Edit judul, instruksi, timer, tenggat", key=f"edit_toggle_{selected_siswa}_{i}"):
                                    try:
                                        _dt_lama = datetime.strptime(str(item.get("Tenggat", ""))[:19], "%Y-%m-%d %H:%M:%S")
                                    except (ValueError, TypeError):
                                        try:
                                            _dt_lama = datetime.strptime(str(item.get("Tenggat", ""))[:10] + " 23:59:00", "%Y-%m-%d %H:%M:%S")
                                        except (ValueError, TypeError):
                                            _dt_lama = waktu_lokal().replace(tzinfo=None) + timedelta(days=1)
                                    with st.form(f"form_edit_item_{selected_siswa}_{i}"):
                                        _judul_baru = st.text_input("Judul", value=str(item.get("Judul", "")))
                                        _instruksi_baru = st.text_area("Instruksi", value=str(item.get("Instruksi", "")))
                                        _timer_baru = st.number_input(
                                            "Timer (menit, 0 = tanpa timer)", min_value=0, max_value=600,
                                            value=int(item.get("Timer", 0) or 0)
                                        )
                                        _tgl_baru = st.date_input("Tenggat tanggal", value=_dt_lama.date())
                                        _jam_baru = st.time_input("Tenggat jam", value=_dt_lama.time())
                                        if st.form_submit_button("💾 Simpan perubahan"):
                                            if not _judul_baru.strip():
                                                st.error("Judul tidak boleh kosong.")
                                            elif item.get("Mode_Pengerjaan", TASK_MODE_UPLOAD) == TASK_MODE_ONLINE and int(_timer_baru) <= 0:
                                                st.error("Tugas online memerlukan timer lebih dari 0 menit.")
                                            else:
                                                item["Judul"] = _judul_baru.strip()
                                                item["Instruksi"] = _instruksi_baru
                                                item["Timer"] = int(_timer_baru)
                                                item["Tenggat"] = datetime.combine(_tgl_baru, _jam_baru).strftime("%Y-%m-%d %H:%M:%S")
                                                try:
                                                    simpan_draft_tugas_persisten(
                                                        get_siswa_id_by_nama(selected_siswa), selected_siswa,
                                                        st.session_state.get("tutor_nama", ""), daftar_draft
                                                    )
                                                except Exception:
                                                    pass
                                                st.session_state.pop(f"edit_toggle_{selected_siswa}_{i}", None)
                                                st.rerun()
                                if st.button("📄 Duplikasi tugas ini", key=f"duplikasi_item_{selected_siswa}_{i}"):
                                    salinan = json.loads(json.dumps(item, ensure_ascii=False))
                                    salinan["Judul"] = str(salinan.get("Judul", "")) + " (Salinan)"
                                    daftar_draft.append(salinan)
                                    try:
                                        simpan_draft_tugas_persisten(
                                            get_siswa_id_by_nama(selected_siswa), selected_siswa,
                                            st.session_state.get("tutor_nama", ""), daftar_draft
                                        )
                                    except Exception as exc:
                                        st.warning(f"Salinan ada di sesi ini tetapi belum tersinkron: {exc}")
                                    st.rerun()
                        # FITUR BARU: ringkasan siswa tambahan (dipilih di bagian atas halaman)
                        _tambahan_dipilih = list(st.session_state.get(f"_siswa_tambahan_{selected_siswa}", []))
                        if _tambahan_dipilih:
                            st.info(
                                f"👥 Semua tugas di daftar ini juga akan dikirim ke {len(_tambahan_dipilih)} siswa lain: "
                                + ", ".join(_tambahan_dipilih) + ". Ubah pilihan di bagian atas halaman."
                            )
                        _semua_penerima = [selected_siswa] + [
                            n for n in _tambahan_dipilih if str(n).strip().casefold() != str(selected_siswa).strip().casefold()
                        ]
                        _penerima_pilih = st.multiselect(
                            "Kirim ke siswa (hapus nama yang tidak hadir):",
                            _semua_penerima, default=_semua_penerima,
                            key="penerima_kirim_" + "|".join(_semua_penerima)
                        )
                        _utama_ikut = selected_siswa in _penerima_pilih
                        _tambahan_final = [n for n in _penerima_pilih if n != selected_siswa]
                        col_kirim, col_hapus = st.columns(2)
                        with col_kirim:
                            if st.button(f"📤 Simpan & Kirim Semua ({len(daftar_draft)})", type="primary", key=f"kirim_semua_{selected_siswa}"):
                                try:
                                    if not _penerima_pilih:
                                        st.error("Pilih minimal satu siswa penerima.")
                                        st.stop()
                                    # Validasi ulang seluruh draft tepat sebelum publikasi, termasuk draft lama yang dipulihkan.
                                    masalah_publikasi = []
                                    for nomor_item, item in enumerate(daftar_draft, 1):
                                        mode_item = item.get("Mode_Pengerjaan", TASK_MODE_UPLOAD)
                                        if mode_item == TASK_MODE_ONLINE and int(item.get("Timer", 0) or 0) <= 0:
                                            masalah_publikasi.append(
                                                f"Tugas ke-{nomor_item} ({item.get('Judul', 'Tanpa judul')}): timer online harus lebih dari 0 menit."
                                            )
                                        try:
                                            teks_tenggat = str(item.get("Tenggat", "")).strip()
                                            if len(teks_tenggat) == 10:
                                                dt_tenggat = datetime.strptime(teks_tenggat + " 23:59:00", "%Y-%m-%d %H:%M:%S")
                                            else:
                                                dt_tenggat = datetime.strptime(teks_tenggat[:19], "%Y-%m-%d %H:%M:%S")
                                            if dt_tenggat <= waktu_lokal().replace(tzinfo=None):
                                                masalah_publikasi.append(
                                                    f"Tugas ke-{nomor_item} ({item.get('Judul', 'Tanpa judul')}): tenggat sudah lewat."
                                                )
                                        except (ValueError, TypeError):
                                            masalah_publikasi.append(
                                                f"Tugas ke-{nomor_item} ({item.get('Judul', 'Tanpa judul')}): tanggal/jam tenggat tidak valid."
                                            )
                                    for nomor_item, item in enumerate(daftar_draft, 1):
                                        try:
                                            _ukuran_soal = len(json.dumps(bungkus_soal_dengan_mode(
                                                item["Soal"], item.get("Mode_Pengerjaan", TASK_MODE_UPLOAD),
                                                item.get("Daftar_Mapel", [item.get("Mapel", "")]),
                                                item.get("Unggah_Oleh") or None
                                            ), ensure_ascii=False))
                                        except Exception:
                                            _ukuran_soal = 0
                                        if _ukuran_soal > BATAS_SEL_SHEETS:
                                            masalah_publikasi.append(
                                                f"Tugas ke-{nomor_item} ({item.get('Judul', 'Tanpa judul')}): data soal terlalu besar "
                                                f"({_ukuran_soal:,} karakter, batas {BATAS_SEL_SHEETS:,}). Kurangi jumlah soal atau pecah menjadi dua tugas."
                                            )
                                    if masalah_publikasi:
                                        for pesan_masalah in masalah_publikasi:
                                            st.error(pesan_masalah)
                                        st.stop()
                                    ws_tugas = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS)
                                    if not pastikan_header_tugas(ws_tugas):
                                        st.error("Header Tugas_Sesi_Siswa_v2 tidak cocok. Data tidak ditulis agar tidak bergeser.")
                                    else:
                                        id_siswa_terpilih = get_siswa_id_by_nama(selected_siswa)
                                        id_tutor_aktif = str(st.session_state.get("tutor_id", "")).strip()
                                        if not id_siswa_terpilih:
                                            st.error("Identitas siswa tidak dapat dipastikan. Jika ada nama siswa yang sama, pilih siswa melalui identitas yang dibedakan pada data siswa sebelum mengirim tugas.")
                                            st.stop()
                                        if not id_tutor_aktif:
                                            st.error("ID tutor tidak ditemukan pada akun login. Tugas tidak dikirim agar tanggung jawab penilaian tidak hilang.")
                                            st.stop()
                                        # Unggah seluruh lampiran dulu; baris tugas ditulis setelah semua unggahan berhasil.
                                        hasil_kirim = []
                                        for item in daftar_draft:
                                            entri_lampiran = []
                                            for file_item in item.get("Files", []):
                                                url = file_item.get("url")
                                                if not url and file_item.get("bytes"):
                                                    url = upload_lampiran_ke_drive(
                                                        file_item["bytes"], file_item["name"], file_item.get("mime", "application/octet-stream")
                                                    )
                                                if url:
                                                    entri_lampiran.append(
                                                        f"{jenis_dari_mime(file_item.get('mime', ''), file_item['name'])}::{url}"
                                                    )
                                            for link in item.get("Links", []):
                                                entri_lampiran.append(f"link::{link}")
                                            hasil_kirim.append((item, "|".join(entri_lampiran)))

                                        now_txt = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
                                        baris_baru = []
                                        for item, file_info in hasil_kirim:
                                            baris_baru.append([
                                                "TGS-" + uuid.uuid4().hex[:10].upper(), now_txt, selected_siswa,
                                                item["Mapel"], item["Judul"], item["Jenis"], item["Sumber"], item["Instruksi"],
                                                file_info, item["Timer"], item["Tenggat"],
                                                json.dumps(bungkus_soal_dengan_mode(
                                                    item["Soal"], item.get("Mode_Pengerjaan", TASK_MODE_UPLOAD),
                                                    item.get("Daftar_Mapel", [item.get("Mapel", "")]),
                                                    item.get("Unggah_Oleh") or None
                                                ), ensure_ascii=False),
                                                "Diberikan", st.session_state.tutor_nama,
                                                item.get("Mode_Pengerjaan", TASK_MODE_UPLOAD),
                                                get_siswa_id_by_nama(selected_siswa),
                                                str(st.session_state.get("tutor_id", "")).strip()
                                            ])
                                        if _utama_ikut:
                                            tulis_banyak_baris_di_bawah(ws_tugas, baris_baru)
                                        # FITUR BARU: salin penugasan yang sama ke siswa tambahan.
                                        # Lampiran Drive yang sudah diunggah dipakai ulang; tiap siswa mendapat ID_Tugas baru.
                                        try:
                                            nama_tambahan = list(_tambahan_final)
                                            baris_tambahan, siswa_terkirim, siswa_dilewati = [], [], []
                                            for nama_t in nama_tambahan:
                                                id_t = get_siswa_id_by_nama(nama_t)
                                                if not id_t:
                                                    siswa_dilewati.append(nama_t)
                                                    continue
                                                for baris_asal in baris_baru:
                                                    baris_salin = list(baris_asal)
                                                    baris_salin[0] = "TGS-" + uuid.uuid4().hex[:10].upper()
                                                    baris_salin[2] = nama_t
                                                    baris_salin[15] = id_t
                                                    baris_tambahan.append(baris_salin)
                                                siswa_terkirim.append(nama_t)
                                            if baris_tambahan:
                                                tulis_banyak_baris_di_bawah(ws_tugas, baris_tambahan)
                                            catatan_tambahan = ""
                                            if siswa_terkirim:
                                                catatan_tambahan = "Tugas yang sama juga terkirim ke: " + ", ".join(siswa_terkirim) + "."
                                            if siswa_dilewati:
                                                catatan_tambahan += (
                                                    " Tidak dikirim (identitas tidak dapat dipastikan / nama ganda): "
                                                    + ", ".join(siswa_dilewati) + "."
                                                )
                                            if catatan_tambahan:
                                                st.session_state["_nazma_notice_tambahan"] = catatan_tambahan.strip()
                                            st.session_state.pop(f"_siswa_tambahan_{selected_siswa}", None)
                                        except Exception as exc_tambahan:
                                            st.session_state["_nazma_notice_tambahan"] = (
                                                f"Tugas untuk {selected_siswa} sudah terkirim, tetapi pengiriman ke siswa tambahan gagal "
                                                f"({exc_tambahan.__class__.__name__}). Pilih siswa tambahan lalu kirim ulang dari siswa tersebut."
                                            )
                                        n_pr = sum(1 for it in daftar_draft if str(it["Jenis"]).startswith("PR"))
                                        st.session_state[draft_key] = []
                                        try:
                                            hapus_draft_tugas_persisten(
                                                get_siswa_id_by_nama(selected_siswa),
                                                st.session_state.get("tutor_nama", "")
                                            )
                                        except Exception:
                                            pass
                                        _label_kirim = selected_siswa if _utama_ikut else ", ".join(_tambahan_final)
                                        st.success(f"{len(hasil_kirim)} penugasan terkirim untuk {_label_kirim} ({n_pr} PR, {len(hasil_kirim) - n_pr} tugas sesi).")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menyimpan tugas: {e}")
                        with col_hapus:
                            if st.button("Kosongkan daftar draft", key=f"hapus_draft_{selected_siswa}"):
                                st.session_state[draft_key] = []
                                try:
                                    hapus_draft_tugas_persisten(
                                        get_siswa_id_by_nama(selected_siswa),
                                        st.session_state.get("tutor_nama", "")
                                    )
                                except Exception:
                                    pass
                                st.rerun()
                    else:
                        st.info("Belum ada tugas di daftar draft.")

                    st.markdown("---")
                    st.subheader("📝 Jurnal dan Evaluasi Sesi")
                    # Status kirim per siswa-tanggal mencegah klik berulang setelah penyimpanan sukses.
                    tanggal_sesi = st.date_input("Tanggal sesi:", waktu_lokal().date(), key=f"tgl_sesi_{selected_siswa}")
                    # Versi form naik setelah simpan, sehingga isian kosong lagi dan tombol selalu aktif.
                    ver_jurnal = st.session_state.get(f"jurnal_ver_{selected_siswa}", 0)
                    jurnal_sig_key = f"jurnal_sig_{selected_siswa}_{tanggal_sesi.strftime('%Y%m%d')}"
                    for jenis_pesan, isi_pesan in st.session_state.pop(f"jurnal_pesan_{selected_siswa}", []):
                        (st.success if jenis_pesan == "ok" else st.warning)(isi_pesan)
                    mapel_diajarkan = st.multiselect("Mata pelajaran yang diajarkan:", MAPEL_OPTIONS, key=f"mapel_ajar_{selected_siswa}_{ver_jurnal}")
                    with st.form(f"form_jurnal_v2_{selected_siswa}_{ver_jurnal}"):
                        st.markdown("#### Evaluasi per mata pelajaran")
                        evaluasi_mapel = {}
                        for idx, mp in enumerate(mapel_diajarkan):
                            st.markdown(f"**{mp}**")
                            materi_mp = st.text_input(f"Materi {mp}", key=f"materi_mp_{selected_siswa}_{idx}_{ver_jurnal}")
                            target_mp = st.text_input(f"Target belajar {mp}", key=f"target_mp_{selected_siswa}_{idx}_{ver_jurnal}")
                            capaian_mp = st.text_area(f"Kompetensi yang dikuasai / hasil belajar {mp}", key=f"capaian_mp_{selected_siswa}_{idx}_{ver_jurnal}")
                            penguatan_mp = st.text_area(f"Bagian yang perlu penguatan {mp}", key=f"penguatan_mp_{selected_siswa}_{idx}_{ver_jurnal}")
                            nilai_mp = st.text_input(f"Nilai latihan (opsional) {mp}", key=f"nilai_mp_{selected_siswa}_{idx}_{ver_jurnal}")
                            evaluasi_mapel[mp] = {"Materi": materi_mp, "Target": target_mp, "Capaian": capaian_mp, "Penguatan": penguatan_mp, "Nilai": nilai_mp}
                        st.markdown("#### Catatan umum sesi")
                        kondisi_siswa = st.selectbox("Kondisi siswa:", ["Baik", "Cukup", "Kurang fokus", "Lelah", "Perlu perhatian khusus"])
                        keaktifan = st.selectbox("Keaktifan siswa:", ["Sangat aktif", "Aktif", "Cukup aktif", "Pasif"])
                        kendala_umum = st.text_area("Kendala selama sesi:")
                        rekomendasi = st.text_area("Rekomendasi / tindak lanjut:")
                        handover = st.text_area("Catatan untuk tutor berikutnya (handover):")
                        dokumentasi = st.text_input("Link dokumentasi (opsional):")
                        file_dokumentasi = st.file_uploader(
                            "Lampiran evaluasi tutor (foto/video):",
                            type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "webm", "m4v"],
                            accept_multiple_files=True,
                            key=f"lampiran_evaluasi_{selected_siswa}_{ver_jurnal}"
                        )
                        simpan_jurnal = st.form_submit_button(
                            "💾 Simpan Jurnal dan Evaluasi"
                        )

                    if simpan_jurnal:
                        _sig_jurnal = json.dumps(
                            [kondisi_siswa, keaktifan, kendala_umum, rekomendasi, handover, dokumentasi, evaluasi_mapel],
                            sort_keys=True, ensure_ascii=False
                        )
                        if st.session_state.get(jurnal_sig_key) == _sig_jurnal:
                            st.warning("Isi jurnal ini sama dengan yang baru saja disimpan. Ubah isinya bila ingin membuat jurnal baru.")
                            simpan_jurnal = False
                    if simpan_jurnal:
                        pesan_jurnal = []
                        try:
                            daftar_dokumentasi = [dokumentasi.strip()] if dokumentasi.strip() else []
                            peringatan_lampiran = []
                            for file_doc in list(file_dokumentasi or []):
                                if len(file_doc.getvalue()) > 30 * 1024 * 1024:
                                    peringatan_lampiran.append(f"{file_doc.name} melebihi batas 30 MB dan tidak diunggah.")
                                    continue
                                try:
                                    url_doc = upload_lampiran_ke_drive(
                                        file_doc.getvalue(), file_doc.name, file_doc.type or "application/octet-stream"
                                    )
                                    daftar_dokumentasi.append(
                                        f"{jenis_dari_mime(file_doc.type, file_doc.name)}::{url_doc}"
                                    )
                                except Exception as upload_error:
                                    peringatan_lampiran.append(f"Lampiran {file_doc.name} gagal diunggah: {upload_error}")
                            dokumentasi_final = " | ".join(daftar_dokumentasi)
                            ws_sesi = get_or_create_worksheet("Jurnal_Sesi_Tutor_v2", ["ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Kondisi_Siswa", "Keaktifan", "Kendala_Umum", "Rekomendasi", "Handover", "Dokumentasi"])
                            id_sesi = "SES-" + uuid.uuid4().hex[:10].upper()
                            ws_sesi.append_row([id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, kondisi_siswa, keaktifan, kendala_umum, rekomendasi, handover, dokumentasi_final])
                            # Kunci setelah jurnal utama berhasil tersimpan, agar retry tidak menggandakan jurnal.
                            st.session_state[jurnal_sig_key] = _sig_jurnal
                            try:
                                ws_eval = get_or_create_worksheet("Evaluasi_Mapel_Tutor_v2", ["ID_Evaluasi", "ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Mapel", "Materi", "Target", "Capaian", "Penguatan", "Nilai"])
                                baris_eval = [["EVL-" + uuid.uuid4().hex[:10].upper(), id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, mp, ev["Materi"], ev["Target"], ev["Capaian"], ev["Penguatan"], ev["Nilai"]] for mp, ev in evaluasi_mapel.items()]
                                if baris_eval:
                                    ws_eval.append_rows(baris_eval, value_input_option="RAW")
                                pesan_jurnal.append(("ok", f"✅ Terkirim! Jurnal sesi dan evaluasi berhasil disimpan. ID sesi: {id_sesi}."))
                            except Exception as eval_error:
                                pesan_jurnal.append(("warn", f"Jurnal utama sudah tersimpan dengan ID {id_sesi}, tetapi evaluasi per mapel belum seluruhnya tersimpan. Jangan kirim ulang jurnal; catat ID ini untuk perbaikan: {eval_error}"))
                            for peringatan in peringatan_lampiran:
                                pesan_jurnal.append(("warn", peringatan))
                            _baca_values_cache.clear()
                            st.session_state[f"jurnal_pesan_{selected_siswa}"] = pesan_jurnal
                            st.session_state[f"jurnal_ver_{selected_siswa}"] = ver_jurnal + 1
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan jurnal/evaluasi: {e}. Periksa riwayat sebelum mencoba mengirim ulang.")

            # -------------------------------------------------
            # TAB 2: PORTOFOLIO DAN PENILAIAN JAWABAN
            # -------------------------------------------------
        elif menu_tutor == "📚 Koleksi Soal":
            tampilkan_koleksi_soal(st.session_state.get("tutor_nama", ""))

        elif menu_tutor == "📋 Pantau Tugas & PR":
                st.header("📋 Pantau Tugas & PR")
                st.caption("Lihat semua tugas dan PR yang pernah diberikan ke seorang siswa, statusnya, dan tenggatnya.")
                try:
                    pilihan_pantau = get_siswa_aktif()
                except Exception as e:
                    pilihan_pantau = []
                    st.error(f"Daftar siswa belum dapat dibaca: {e}")
                cari_pantau = st.text_input(
                    "🔍 Cari nama siswa:",
                    key="cari_pantau_siswa",
                    placeholder="Ketik nama siswa..."
                ).strip().lower()
                hasil_pantau, pesan_pantau = cari_siswa_terbatas(cari_pantau, pilihan_pantau)
                if hasil_pantau and pesan_pantau:
                    st.caption(pesan_pantau)
                if cari_pantau and hasil_pantau:
                    nama_pantau = st.selectbox(
                        "Pilih siswa yang cocok:",
                        hasil_pantau,
                        key="pantau_siswa_hasil"
                    )
                    try:
                        sid_pantau = get_siswa_id_by_nama(nama_pantau)
                        semua_tugas = [t for t in get_student_tasks()
                                       if str(t.get("Nama_Siswa", "")).strip().lower() == nama_pantau.strip().lower()
                                       and not adalah_materi(t)]  # Materi lama diarsipkan, bukan ditampilkan.
                        # Status dicocokkan lewat pasangan ID tugas + ID siswa pada baris tugas itu sendiri,
                        # bukan lewat pencarian nama (nama ganda atau ID kosong membuat status salah).
                        pasangan_pantau = {
                            (str(t.get("ID_Tugas", "")).strip(),
                             str(t.get("ID_Siswa", "")).strip() or str(sid_pantau or "").strip())
                            for t in semua_tugas
                        }
                        try:
                            jwb_pantau = [x for x in baca_jawaban_tergabung(get_answers_worksheet())
                                          if (str(x.get("ID_Tugas", "")).strip(), str(x.get("ID_Siswa", "")).strip()) in pasangan_pantau]
                        except Exception:
                            jwb_pantau = []
                        sesi_pantau = {}
                        try:
                            for s in baca_records_aman(get_active_task_worksheet()):
                                st_s = str(s.get("Status", "")).strip().lower()
                                pasang_s = (str(s.get("ID_Tugas", "")).strip(), str(s.get("ID_Siswa", "")).strip())
                                if st_s in ("aktif", "kedaluwarsa") and pasang_s in pasangan_pantau:
                                    sesi_pantau[pasang_s[0]] = st_s
                        except Exception:
                            sesi_pantau = {}
                        status_pantau = {str(x.get("ID_Tugas", "")): str(x.get("Status", "")) for x in jwb_pantau}
                        try:
                            nilai_pantau = {kunci_nilai_penugasan(n)
                                            for n in baca_nilai_tugas_terpadu()
                                            if all(kunci_nilai_penugasan(n))}
                        except Exception:
                            nilai_pantau = set()

                        saring = st.radio("Tampilkan:", ["Semua", "PR", "Tugas sesi"], horizontal=True, key="pantau_saring")
                        baris = []
                        for t in reversed(semua_tugas):
                            if saring == "PR" and not adalah_pr(t):
                                continue
                            if saring == "Tugas sesi" and adalah_pr(t):
                                continue
                            if "batal" in str(t.get("Status_Tugas", "")).lower():
                                label = "🚫 Dibatalkan"
                            else:
                                label = label_status(t, status_pantau, nilai_pantau, sesi_pantau)[1]
                            baris.append({
                                "Kategori": "PR" if adalah_pr(t) else "Tugas sesi",
                                "Mapel": t.get("Mapel"), "Judul": t.get("Judul_Tugas"),
                                "Jenis": t.get("Jenis_Tugas"), "Tenggat": t.get("Tenggat") or "-",
                                "Diberikan": str(t.get("Tanggal", ""))[:10], "Status": label,
                            })
                        if baris:
                            st.dataframe(pd.DataFrame(baris), use_container_width=True, hide_index=True)
                        else:
                            st.info("Belum ada penugasan untuk siswa ini.")

                        # Batalkan tugas yang salah kirim (hanya yang belum dikerjakan)
                        bisa_batal = [t for t in semua_tugas
                                      if "batal" not in str(t.get("Status_Tugas", "")).lower()
                                      and label_status(t, status_pantau, nilai_pantau)[0] in ("belum", "draft", "materi", "dikirim", "dinilai")]
                        _bisa_edit = [t for t in bisa_batal if label_status(t, status_pantau, nilai_pantau)[0] in ("belum", "draft", "materi", "dikirim", "dinilai")]
                        if _bisa_edit:
                            with st.expander("✏️ Edit tugas yang sudah tersimpan/terkirim"):
                                _peta_edit = {f"{t.get('Mapel')} | {t.get('Judul_Tugas')} | {str(t.get('Tanggal', ''))[:10]} | {label_status(t, status_pantau, nilai_pantau)[1]}": t for t in _bisa_edit}
                                _pilih_edit = st.selectbox("Pilih tugas:", list(_peta_edit.keys()), key="pantau_edit_pilih")
                                _t_edit = _peta_edit[_pilih_edit]
                                _sudah_dikerjakan = label_status(_t_edit, status_pantau, nilai_pantau)[0] in ("dikirim", "dinilai")
                                if _sudah_dikerjakan:
                                    st.caption("Siswa sudah mengirim jawaban, jadi hanya judul dan instruksi yang bisa diubah agar jawaban tidak rusak.")
                                _kunci_e = str(_t_edit.get("ID_Tugas", ""))
                                _judul_e = st.text_input("Judul tugas:", str(_t_edit.get("Judul_Tugas", "")), key=f"edit_judul_{_kunci_e}")
                                _instr_e = st.text_area("Instruksi:", str(_t_edit.get("Instruksi", "")), key=f"edit_instr_{_kunci_e}")
                                _ubah = {"Judul_Tugas": _judul_e.strip(), "Instruksi": _instr_e.strip()}
                                if not _sudah_dikerjakan:
                                    _timer_e = st.text_input("Timer (menit, kosongkan bila tanpa timer):", str(_t_edit.get("Timer_Menit", "")), key=f"edit_timer_{_kunci_e}")
                                    _tenggat_e = st.text_input("Tenggat:", str(_t_edit.get("Tenggat", "")), key=f"edit_tenggat_{_kunci_e}")
                                    _ubah.update({"Timer_Menit": _timer_e.strip(), "Tenggat": _tenggat_e.strip()})
                                if st.button("💾 Simpan perubahan tugas", key=f"edit_simpan_{_kunci_e}", disabled=not _judul_e.strip()):
                                    try:
                                        if edit_tugas_terkirim(get_worksheet("Tugas_Sesi_Siswa_v2"), _kunci_e, _ubah):
                                            st.success("Tugas diperbarui.")
                                            st.rerun()
                                        else:
                                            st.error("Tugas tidak ditemukan di sheet.")
                                    except Exception as _e:
                                        st.error(f"Gagal menyimpan: {_e}")
                        if bisa_batal:
                            with st.expander("🚫 Batalkan tugas"):
                                peta_batal = {f"{t.get('Mapel')} | {t.get('Judul_Tugas')} | {t.get('Jenis_Tugas')} | {str(t.get('Tanggal', ''))[:10]}": t for t in bisa_batal}
                                pilih_batal = st.selectbox("Pilih tugas:", list(peta_batal.keys()), key="pantau_batal_pilih")
                                _kode_batal = label_status(peta_batal[pilih_batal], status_pantau, nilai_pantau)[0]
                                if _kode_batal in ("dikirim", "dinilai"):
                                    st.warning("Siswa sudah mengirim jawaban. Tugas hanya disembunyikan; jawaban dan nilai tetap tersimpan, dan pemilik portal bisa memulihkannya.")
                                yakin_batal = st.checkbox("Saya yakin membatalkan tugas ini (siswa tidak akan melihatnya lagi).", key="pantau_batal_yakin")
                                if st.button("Batalkan tugas", disabled=not yakin_batal, key="pantau_batal_tombol"):
                                    try:
                                        if edit_tugas_terkirim(get_worksheet("Tugas_Sesi_Siswa_v2"),
                                                               peta_batal[pilih_batal].get("ID_Tugas"), {"Status_Tugas": "Dibatalkan"}):
                                            st.success("Tugas dibatalkan.")
                                            st.rerun()
                                        else:
                                            st.error("Tugas tidak ditemukan di sheet.")
                                    except Exception as _e:
                                        st.error(f"Gagal membatalkan: {_e}")
                    except Exception as e:
                        st.error(f"Pantauan belum dapat ditampilkan: {e}")
                elif cari_pantau:
                    st.warning(pesan_pantau or "Siswa aktif tidak ditemukan.")
                else:
                    st.info("Ketik nama siswa untuk melihat tugas dan PR.")

        elif menu_tutor == "📊 Portofolio Siswa":
                st.header("📊 Portofolio & Pemeriksaan Jawaban Siswa")
                st.subheader("📈 Ringkasan perkembangan siswa")
                tutor_id_portofolio = str(st.session_state.get("tutor_id", "")).strip()
                tutor_nama_portofolio = str(st.session_state.get("tutor_nama", "")).strip().casefold()

                def _tugas_milik_tutor_login(t):
                    return tugas_milik_tutor(t, tutor_id_portofolio)

                try:
                    st.caption("Ringkasan hanya menampilkan tugas yang Anda berikan sendiri.")
                    kata_cari_siswa = st.text_input(
                        "Ketik nama siswa (minimal 3 huruf):",
                        key="cari_siswa_laporan_736"
                    ).strip()
                    nama_siswa_laporan = "— Pilih siswa —"
                    if kata_cari_siswa:
                        if len(kata_cari_siswa) < 3:
                            st.caption("Ketik minimal 3 huruf untuk mencari.")
                        else:
                            cocok_nama = sorted({
                                n for n in get_siswa_aktif()
                                if kata_cari_siswa.casefold() in n.casefold()
                            })
                            if not cocok_nama:
                                st.info("Tidak ada siswa aktif dengan nama tersebut.")
                            elif len(cocok_nama) == 1:
                                nama_siswa_laporan = cocok_nama[0]
                            else:
                                nama_siswa_laporan = st.selectbox(
                                    "Ada beberapa nama yang cocok, pilih salah satu:",
                                    ["— Pilih siswa —"] + cocok_nama[:8],
                                    key=f"pilih_cocok_laporan_736_{kata_cari_siswa.casefold()}"
                                )
                                if len(cocok_nama) > 8:
                                    st.caption("Hanya 8 nama pertama yang ditampilkan. Ketik nama lebih lengkap untuk mempersempit.")
                    if nama_siswa_laporan != "— Pilih siswa —":
                        semua_tugas_laporan = [x for x in get_student_tasks() if _tugas_milik_tutor_login(x)]
                        semua_jawaban_laporan = baca_jawaban_tergabung(get_worksheet("DB_Jawaban_Siswa"))
                        semua_nilai_laporan = baca_nilai_tugas_terpadu()
                        tampilkan_laporan_perkembangan(
                            nama_siswa_laporan, semua_tugas_laporan,
                            semua_jawaban_laporan, semua_nilai_laporan
                        )
                        tugas_siswa_laporan = [
                            x for x in semua_tugas_laporan
                            if str(x.get("Nama_Siswa", "")).strip().casefold() == nama_siswa_laporan.strip().casefold()
                            and not adalah_materi(x)
                        ]
                        # Tampilkan foto/PDF hasil mandiri pada Portofolio, dengan relasi ID tugas + ID siswa.
                        if tugas_siswa_laporan:
                            lampiran_portofolio = []
                            for tugas_laporan in tugas_siswa_laporan:
                                lampiran_portofolio.extend(
                                    baca_lampiran_jawaban(
                                        tugas_laporan.get("ID_Tugas", ""),
                                        tugas_laporan.get("ID_Siswa", ""),
                                        refresh=True
                                    )
                                )
                            if lampiran_portofolio:
                                with st.expander(f"📷 Foto/lampiran jawaban {nama_siswa_laporan}", expanded=True):
                                    for lamp in lampiran_portofolio:
                                        tampilkan_media_url(
                                            lamp.get("URL_Drive", ""),
                                            lamp.get("Mime_Type", ""),
                                            lamp.get("Nama_File", "Lampiran")
                                        )
                        if tugas_siswa_laporan:
                            siswa_ids_laporan = {
                                str(x.get("ID_Siswa", "")).strip() for x in tugas_siswa_laporan
                                if str(x.get("ID_Siswa", "")).strip()
                            }
                            nilai_map_laporan = {
                                kunci_nilai_penugasan(x): x.get("Nilai")
                                for x in semua_nilai_laporan
                                if kunci_nilai_penugasan(x)[0]
                                and (not siswa_ids_laporan or kunci_nilai_penugasan(x)[1] in siswa_ids_laporan)
                            }
                            _peta_pel_laporan = hitung_pelanggaran_fokus()
                            _sudah_kirim_laporan = {
                                (str(j.get("ID_Tugas", "")).strip(), str(j.get("ID_Siswa", "")).strip())
                                for j in semua_jawaban_laporan
                            }

                            def _teks_pel_laporan(t):
                                kunci_t = (str(t.get("ID_Tugas", "")).strip(), str(t.get("ID_Siswa", "")).strip())
                                if kunci_t in _peta_pel_laporan:
                                    return teks_pelanggaran(_peta_pel_laporan[kunci_t])
                                return teks_pelanggaran(0) if kunci_t in _sudah_kirim_laporan else "-"

                            st.dataframe(pd.DataFrame([
                                {
                                    "Mapel": x.get("Mapel", ""),
                                    "Tugas": x.get("Judul_Tugas", ""),
                                    "Kategori": "PR" if adalah_pr(x) else "Tugas sesi",
                                    "Nilai akhir": nilai_map_laporan.get(
                                        (str(x.get("ID_Tugas", "")).strip(), str(x.get("ID_Siswa", "")).strip()),
                                        "Belum terbit"
                                    ),
                                    "Pelanggaran (keluar tab)": _teks_pel_laporan(x)
                                } for x in tugas_siswa_laporan
                            ]), use_container_width=True, hide_index=True)
                            # FITUR BARU: soal yang diberikan ke siswa ini
                            tampilkan_pilih_soal_portofolio(nama_siswa_laporan, tugas_siswa_laporan)
                except Exception as exc:
                    st.warning(f"Ringkasan perkembangan belum dapat dimuat: {exc}")

                st.markdown("---")
                try:
                    ws_jawaban = get_worksheet("DB_Jawaban_Siswa")
                    jawaban_records = baca_jawaban_tergabung(ws_jawaban, segarkan=False)
                except gspread.WorksheetNotFound:
                    jawaban_records = []

                tampilkan_peringatan_fokus(
                    st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", "")
                )
                tampilkan_panel_offline_tutor(
                    st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", ""),
                    get_student_tasks(), jawaban_records
                )
                st.subheader("Jawaban yang menunggu pemeriksaan")
                tutor_id_login = str(st.session_state.get("tutor_id", "")).strip()
                daftar_tugas_review = get_student_tasks()
                peta_tugas_review = {str(t.get("ID_Tugas", "")).strip(): t for t in daftar_tugas_review}
                menunggu = []
                for jawaban in jawaban_records:
                    if "menunggu" not in str(jawaban.get("Status", "")).casefold():
                        continue
                    tugas_review = peta_tugas_review.get(str(jawaban.get("ID_Tugas", "")).strip(), {})
                    if tugas_milik_tutor(tugas_review, tutor_id_login):
                        menunggu.append(jawaban)
                try:
                    info_tgs = {str(t.get("ID_Tugas", "")).strip(): t for t in get_student_tasks()}
                except Exception:
                    info_tgs = {}
                opsi_jwb = {f"{x.get('ID_Tugas', '')}|{x.get('ID_Siswa', '')}": x for x in menunggu}
                kunci_terpilih = st.session_state.get("_periksa_terpilih", "")
                item = opsi_jwb.get(kunci_terpilih)
                if kunci_terpilih and item is None:
                    st.session_state.pop("_periksa_terpilih", None)  # sudah dinilai atau tidak ada lagi
                if item is None:
                    tampilkan_daftar_pemeriksaan(
                        st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", "")
                    )
                else:
                    tg_item = info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {})
                    nama_tampil_item = str(item.get("Nama_Siswa", "")).strip()
                    if not nama_tampil_item or nama_tampil_item == str(item.get("ID_Siswa", "")).strip():
                        nama_tampil_item = str(tg_item.get("Nama_Siswa", "")).strip() or str(item.get("ID_Siswa", ""))
                    st.markdown(
                        f"### 📝 Sedang diperiksa: {nama_tampil_item} · "
                        f"{tg_item.get('Mapel', '')} — {tg_item.get('Judul_Tugas', '')}"
                    )
                    try:
                        if sesi_kedaluwarsa_tugas(item.get("ID_Siswa", ""), item.get("ID_Tugas", "")):
                            st.caption("⏰ Jawaban ini terkirim otomatis karena waktu pengerjaan habis.")
                    except Exception:
                        pass
                    if st.button("← Kembali ke daftar", key="periksa_kembali"):
                        st.session_state.pop("_periksa_terpilih", None)
                        st.rerun()
                if item is not None:
                    st.write(f"**Siswa:** {nama_tampil_item}")
                    _jml_pelanggaran_item = hitung_pelanggaran_fokus().get(
                        (str(item.get("ID_Tugas", "")).strip(), str(item.get("ID_Siswa", "")).strip()), 0
                    )
                    if _jml_pelanggaran_item:
                        st.warning(f"🚨 Pelanggaran: siswa keluar dari tab/halaman {teks_pelanggaran(_jml_pelanggaran_item)} saat mengerjakan.")
                    else:
                        st.caption("Pelanggaran keluar tab: 0 kali.")
                    # FITUR BARU: soal yang dikirim ke siswa ikut muncul saat menilai
                    tampilkan_soal_tugas_untuk_tutor(
                        info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {}), expanded=True
                    )
                    lampiran_item = baca_lampiran_jawaban(
                            item.get("ID_Tugas", ""), item.get("ID_Siswa", "")
                        )
                    if lampiran_item:
                        st.markdown("**📎 Lampiran jawaban siswa:**")
                        for lamp in lampiran_item:
                            tampilkan_media_url(
                                lamp.get("URL_Drive", ""),
                                lamp.get("Mime_Type", ""),
                                lamp.get("Nama_File", "Lampiran")
                            )
                    else:
                        st.caption("Tidak ada lampiran foto/PDF pada pengiriman ini.")
                    tampilkan_koreksi_tutor(item.get("ID_Tugas", ""), item.get("ID_Siswa", ""))
                    try:
                        jawaban_dict = json.loads(item.get("Jawaban_JSON", "{}"))
                    except (ValueError, TypeError):
                        jawaban_dict = {}
                    st.write("**Jawaban siswa:**")
                    _tampilkan_jawaban_per_soal(
                        info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {}), jawaban_dict
                    )
                    tugas_terpilih = info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {})
                    # Metadata mode di elemen pertama Soal_JSON harus dibuang agar nomor soal tidak bergeser.
                    soal_untuk_nilai, _mode_review = buka_soal_dan_mode(
                        tugas_terpilih.get("Soal_JSON", ""), tugas_terpilih.get("Jenis_Tugas", "")
                    )
                    hasil_otomatis = hitung_nilai_objektif(soal_untuk_nilai, jawaban_dict) if soal_untuk_nilai else {
                        "skor_objektif": None, "jumlah_objektif": 0,
                        "jumlah_benar_penuh": 0, "soal_manual": [], "rincian": []
                    }
                    hasil_sementara = hitung_nilai_sementara(soal_untuk_nilai, jawaban_dict) if soal_untuk_nilai else {
                        "nilai_sementara": None, "essay": [], "soal_manual": [], "siap_disetujui": False
                    }
                    semua_objektif = bool(soal_untuk_nilai) and hasil_otomatis["jumlah_objektif"] == len(soal_untuk_nilai)
                    if hasil_otomatis["skor_objektif"] is not None:
                        st.markdown("**Hasil pemeriksaan otomatis (khusus soal objektif):**")
                        st.metric("Skor objektif", f'{hasil_otomatis["skor_objektif"]:.2f}/100')
                        st.caption(
                            f'{hasil_otomatis["jumlah_benar_penuh"]} soal benar penuh dari '
                            f'{hasil_otomatis["jumlah_objektif"]} soal objektif.'
                        )
                    if hasil_otomatis["soal_manual"]:
                        st.info(
                            "Soal nomor " + ", ".join(map(str, hasil_otomatis["soal_manual"])) +
                            " perlu diperiksa manual. Nilai akhir tetap ditentukan tutor."
                        )
                    elif not soal_untuk_nilai:
                        st.warning("Data soal/kunci tidak tersedia pada tugas ini. Penilaian dilakukan manual.")

                    if hasil_sementara.get("nilai_sementara") is not None and hasil_sementara.get("soal_manual"):
                        st.caption(
                            f'Skor sementara dari soal objektif: {hasil_sementara["nilai_sementara"]:.2f}/100. '
                            "Soal essay/isian dinilai tutor pada form di bawah."
                        )
                    nilai_awal = int(round(hasil_sementara.get("nilai_sementara") or hasil_otomatis["skor_objektif"] or 1))
                    key_penilaian = f"{item.get('ID_Tugas')}_{item.get('ID_Siswa')}"
                    with st.form(f"form_penilaian_jawaban_{key_penilaian}"):
                        st.caption("Skor otomatis memakai bobot yang ditentukan tutor. Soal yang belum dapat dinilai otomatis harus diberi skor manual.")
                        nilai_manual_per_soal = {}
                        konfirmasi_manual_per_soal = {}
                        for nomor_manual in hasil_sementara.get("soal_manual", []):
                            soal_manual = soal_untuk_nilai[nomor_manual - 1] if 0 < nomor_manual <= len(soal_untuk_nilai) else {}
                            st.markdown(f"**Penilaian manual nomor {nomor_manual}** · Bobot {soal_manual.get('Bobot', 1)}")
                            nilai_manual_per_soal[nomor_manual] = st.number_input(
                                f"Skor soal {nomor_manual} (0–100)", min_value=0, max_value=100, value=0,
                                key=f"nilai_manual_{key_penilaian}_{nomor_manual}"
                            )
                            konfirmasi_manual_per_soal[nomor_manual] = st.checkbox(
                                f"Saya sudah memeriksa soal nomor {nomor_manual}",
                                key=f"konfirmasi_manual_{key_penilaian}_{nomor_manual}"
                            )
                        nilai_berbobot = hitung_nilai_akhir_berbobot(
                            soal_untuk_nilai, hasil_sementara, nilai_manual_per_soal
                        ) if soal_untuk_nilai else None
                        if nilai_berbobot is not None:
                            st.metric("Nilai akhir berdasarkan bobot tutor", f"{nilai_berbobot:.2f}/100")
                            nilai_awal = int(round(nilai_berbobot))
                        elif hasil_sementara.get("soal_manual"):
                            st.warning("Lengkapi pemeriksaan manual setiap soal agar nilai berbobot dapat dihitung.")
                        nilai = st.number_input("Nilai akhir (1–100):", min_value=1, max_value=100, value=max(1, min(100, nilai_awal)))
                        catatan = st.text_area("💬 Komentar tutor untuk tugas ini:", key=f"komentar_tugas_{key_penilaian}")
                        persetujuan = st.checkbox("Saya sudah memeriksa hasil dan menyetujui penerbitan nilai akhir.")
                        # Tombol tetap mengirim nilai checkbox; validasi dilakukan setelah submit.
                        simpan_nilai = st.form_submit_button("Setujui dan Terbitkan Nilai")
                        if simpan_nilai:
                            tugas_target = info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {})
                            tutor_id_sekarang = str(st.session_state.get("tutor_id", "")).strip()
                            izin_menilai = tugas_milik_tutor(tugas_target, tutor_id_sekarang)
                            if not izin_menilai:
                                st.error("Penerbitan ditolak. Hanya tutor pemberi tugas yang dapat menerbitkan nilai.")
                            elif any(not sudah for sudah in konfirmasi_manual_per_soal.values()):
                                st.warning("Periksa dan konfirmasi semua soal yang memerlukan penilaian manual.")
                            elif nilai_berbobot is None and soal_untuk_nilai:
                                st.warning("Nilai berbobot belum dapat dihitung. Periksa bobot dan skor setiap soal.")
                            elif not persetujuan:
                                st.warning("Centang persetujuan tutor terlebih dahulu sebelum menerbitkan nilai.")
                            elif not str(item.get("ID_Tugas", "")).strip() or not str(item.get("ID_Siswa", "")).strip():
                                st.error("ID penugasan atau ID siswa kosong. Nilai tidak diterbitkan untuk mencegah salah relasi.")
                            else:
                                ws_nilai = get_nilai_tugas_worksheet()
                                id_tugas_target = str(item.get("ID_Tugas", "")).strip()
                                id_siswa_target = str(item.get("ID_Siswa", "")).strip()
                                nilai_baru_diterbitkan = False
                                nilai_terbit_ada = next((
                                    r for r in baca_nilai_tugas_terpadu(refresh=True)
                                    if kunci_nilai_penugasan(r) == (id_tugas_target, id_siswa_target)
                                ), None)
                                if nilai_terbit_ada:
                                    st.info(
                                        f"Nilai untuk penugasan ini sudah diterbitkan "
                                        f"(ID nilai: {nilai_terbit_ada.get('ID_Nilai', '-')}). "
                                        "Sistem tidak membuat nilai kedua untuk siswa dan tugas yang sama."
                                    )
                                else:
                                    nilai_aman = max(1, min(100, int(round(float(nilai)))))
                                    ws_nilai.append_row([
                                        "NIL-" + uuid.uuid4().hex[:10].upper(),
                                        id_tugas_target,
                                        id_siswa_target,
                                        str(st.session_state.get("tutor_id", "")).strip(),
                                        nilai_aman,
                                        100,
                                        str(catatan or ""),
                                        waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
                                    ], value_input_option="RAW")
                                    _baca_values_cache.clear()
                                    nilai_baru_diterbitkan = True
                                # Catat persetujuan secara idempotent; tidak membuat baris kedua untuk ID_Jawaban yang sama.
                                catat_persetujuan_nilai(
                                    item.get("ID_Jawaban"), item.get("ID_Tugas"),
                                    item.get("ID_Siswa"), hasil_sementara.get("nilai_sementara"),
                                    nilai, st.session_state.tutor_nama, catatan
                                )
                                # Tandai seluruh baris soal pada penugasan/siswa sebagai sudah dinilai.
                                all_rows = baca_records_aman(ws_jawaban)
                                pembaruan = [
                                    {"range": f"F{row['_baris']}", "values": [["Sudah Dinilai"]]}
                                    for row in all_rows
                                    if str(row.get("ID_Penugasan", "")) == str(item.get("ID_Tugas", ""))
                                    and str(row.get("ID_Siswa", "")) == str(item.get("ID_Siswa", ""))
                                ]
                                if pembaruan:
                                    ws_jawaban.batch_update(pembaruan, value_input_option="RAW")
                                if nilai_baru_diterbitkan:
                                    st.success("Satu nilai akhir berbobot berhasil diterbitkan untuk siswa dan penugasan ini.")
                                else:
                                    st.info("Nilai untuk pasangan siswa dan penugasan ini sudah ada; tidak dibuat nilai duplikat.")
                                st.rerun()


                st.markdown("---")
                with st.expander("✅ Nilai otomatis soal online: lihat benar/salah, kunci & pembahasan, atau koreksi", expanded=True):
                    try:
                        _tid_k = str(st.session_state.get("tutor_id", "")).strip()
                        _auto = [
                            r for r in baca_nilai_tugas_terpadu()
                            if str(r.get("ID_Tutor_Penilai", "")).strip() == PENILAI_OTOMATIS
                            and tugas_milik_tutor(info_tgs.get(str(r.get("ID_Penugasan", "")).strip(), {}), _tid_k)
                        ]
                    except Exception as _e:
                        _auto = []
                        st.warning(f"Daftar belum bisa dimuat: {_e}")
                    if not _auto:
                        st.caption("Belum ada nilai otomatis untuk tugas Anda.")
                    else:
                        _peta_k = {f"{r.get('ID_Penugasan')}|{r.get('ID_Siswa')}": r for r in _auto}
                        _pilih_k = st.selectbox(
                            "Pilih nilai:", list(_peta_k), key="koreksi_pilih",
                            format_func=lambda k: f"{info_tgs.get(_peta_k[k].get('ID_Penugasan'), {}).get('Nama_Siswa', _peta_k[k].get('ID_Siswa'))} · "
                                                  f"{info_tgs.get(_peta_k[k].get('ID_Penugasan'), {}).get('Judul_Tugas', _peta_k[k].get('ID_Penugasan'))} · nilai {_peta_k[k].get('Nilai')}")
                        try:
                            _r0 = _peta_k[_pilih_k]
                            _tg0 = info_tgs.get(str(_r0.get("ID_Penugasan", "")).strip(), {})
                            _jw0 = next((x for x in baca_jawaban_tergabung(get_answers_worksheet(), segarkan=True)
                                         if x.get("ID_Tugas") == str(_r0.get("ID_Penugasan", "")).strip()
                                         and x.get("ID_Siswa") == str(_r0.get("ID_Siswa", "")).strip()), None)
                            if _jw0:
                                st.markdown("**Rincian jawaban, kunci, dan pembahasan:**")
                                _tampilkan_jawaban_per_soal(_tg0, _jw0.get("Jawaban", {}))
                        except Exception as _e:
                            st.caption(f"Rincian belum bisa dimuat ({_e.__class__.__name__}).")
                        _nilai_k = st.number_input("Nilai baru (1–100):", 1, 100, int(float(_peta_k[_pilih_k].get("Nilai") or 1)), key="koreksi_nilai")
                        _cat_k = st.text_input("Komentar tutor:", key="koreksi_catatan")
                        if st.button("💾 Simpan koreksi", key="koreksi_simpan"):
                            _r = _peta_k[_pilih_k]
                            if koreksi_nilai_terbit(_r.get("ID_Penugasan"), _r.get("ID_Siswa"), _nilai_k, _cat_k, _tid_k):
                                st.success("Nilai dikoreksi.")
                                st.rerun()
                            else:
                                st.error("Nilai tidak ditemukan.")
                st.subheader("Rekap latihan lama")
                nama_portofolio = st.text_input("Cari nama siswa untuk melihat rekap:", key="nama_portofolio")
                if nama_portofolio:
                    try:
                        ws_r = get_worksheet("Riwayat_Latihan")
                        data_rekap = []
                        for r in baca_records_aman(ws_r):
                            if str(r.get("Nama_Siswa", "")).strip().lower() == nama_portofolio.strip().lower():
                                data_rekap.append({
                                    "Tanggal": str(r.get("Waktu_Selesai", ""))[:10],
                                    "Mapel": r.get("Mapel"),
                                    "Aktivitas": r.get("Topik_Kuis"),
                                    "Skor": r.get("Skor"),
                                    "Catatan": r.get("Detail_Salah")
                                })
                        if data_rekap:
                            st.dataframe(pd.DataFrame(data_rekap), use_container_width=True)
                        else:
                            st.info("Belum ada rekap untuk siswa ini.")
                    except Exception as e:
                        st.info(f"Rekap belum tersedia: {e}")

        elif menu_tutor == "🕒 Kehadiran Siswa":
                st.header("🕒 Kehadiran dan Waktu Belajar")
                tutor_id = st.session_state.get("tutor_id", "")
                if not tutor_id:
                    st.error("Pencatatan kehadiran belum bisa digunakan karena ID_Tutor akun ini belum terhubung dengan Data_Tutor.")
                else:
                    try:
                        allowed_ids = siswa_tutor_terhubung(tutor_id)
                        student_records = baca_records_aman(get_worksheet("Data_Siswa"))
                        pilihan_siswa = [
                            r for r in student_records
                            if str(r.get("ID_Siswa", "")).strip() in allowed_ids
                            and str(r.get("Status", "Aktif")).strip().lower() not in ("nonaktif", "tidak aktif")
                        ]
                        if not pilihan_siswa:
                            st.info("Belum ada siswa aktif yang terhubung dengan tutor ini pada Relasi_Tutor_Siswa.")
                        else:
                            cari_hadir = st.text_input(
                                "🔍 Cari nama siswa yang hadir:",
                                key="attendance_student_search",
                                placeholder="Ketik nama siswa..."
                            ).strip().casefold()
                            hasil_hadir = [
                                r for r in pilihan_siswa
                                if cari_hadir and cari_hadir in str(r.get("Nama_Lengkap", "")).casefold()
                            ]
                            if not cari_hadir:
                                st.info("Ketik nama siswa untuk mencatat kehadiran.")
                            elif not hasil_hadir:
                                st.warning("Siswa tidak ditemukan pada daftar siswa yang terhubung dengan tutor ini.")
                            if hasil_hadir:
                                opsi_siswa = {
                                    f"{r.get('Nama_Lengkap', 'Tanpa nama')} · {r.get('ID_Siswa', '')}": r
                                    for r in hasil_hadir
                                }
                                pilihan_label = st.selectbox(
                                    "Pilih siswa yang cocok:",
                                    list(opsi_siswa.keys()),
                                    key="attendance_student_select_search"
                                )
                                siswa_pilih = opsi_siswa[pilihan_label]
                                sid = str(siswa_pilih.get("ID_Siswa", "")).strip()
                                st.write(f"**Siswa:** {siswa_pilih.get('Nama_Lengkap', '-')}")
                                try:
                                    ws_att, active_row, active_rec = cari_sesi_aktif(sid, tutor_id)
                                    flash_att_key = f"flash_kehadiran_{sid}"
                                    if st.session_state.get(flash_att_key):
                                        st.success(st.session_state.pop(flash_att_key))
                                    if active_rec:
                                        st.info(f"Sesi aktif sejak pukul **{active_rec.get('Waktu_Hadir', '-')}** pada {active_rec.get('Tanggal_Sesi', '-')}")
                                        if st.button("✅ Tandai Selesai Belajar", type="primary", key=f"finish_att_{sid}"):
                                            ok, msg = tandai_selesai_belajar(sid, tutor_id)
                                            if ok:
                                                st.session_state[flash_att_key] = "✅ Terkirim! Waktu selesai belajar berhasil dicatat."
                                                st.rerun()
                                            else:
                                                st.error(msg)
                                    else:
                                        catatan_hadir = st.text_input("Catatan kehadiran (opsional):", key=f"attendance_note_{sid}")
                                        if st.button("🟢 Catat Hadir / Mulai Belajar", type="primary", key=f"start_att_{sid}"):
                                            ok, msg = catat_kehadiran(sid, tutor_id, st.session_state.tutor_nama, catatan_hadir)
                                            if ok:
                                                st.session_state[flash_att_key] = "✅ Terkirim! Kehadiran berhasil dicatat. Sesi belajar sudah aktif."
                                                st.rerun()
                                            else:
                                                st.error(msg)
                                    tampilkan_riwayat_kehadiran(sid, "Riwayat Kehadiran Siswa")

                                    # Koreksi hanya untuk catatan yang dibuat oleh tutor yang sedang login.
                                    records_tutor = [r for r in baca_records_aman(get_attendance_worksheet())
                                                     if str(r.get("ID_Tutor", "")).strip() == tutor_id
                                                     and str(r.get("ID_Siswa", "")).strip() == sid]
                                    if records_tutor:
                                        with st.expander("✏️ Koreksi catatan kehadiran (wajib alasan)"):
                                            rec_options = {
                                                f"{r.get('Tanggal_Sesi', '')} | {r.get('Waktu_Hadir', '')} | {r.get('ID_Kehadiran', '')}": r
                                                for r in records_tutor[-20:]
                                            }
                                            rec_label = st.selectbox("Pilih catatan:", list(rec_options.keys()), key=f"corr_rec_{sid}")
                                            rec_selected = rec_options[rec_label]
                                            kolom_koreksi = st.selectbox("Bagian yang dikoreksi:", ["Waktu_Hadir", "Waktu_Selesai_Belajar", "Status_Kehadiran"], key=f"corr_col_{sid}")
                                            nilai_awal = str(rec_selected.get(kolom_koreksi, ""))
                                            if kolom_koreksi == "Status_Kehadiran":
                                                nilai_koreksi = st.selectbox("Nilai baru:", ["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"], index=["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"].index(nilai_awal) if nilai_awal in ["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"] else 0, key=f"corr_val_{sid}")
                                            else:
                                                nilai_koreksi = st.text_input("Nilai baru (format HH:MM:SS):", value=nilai_awal, key=f"corr_val_{sid}")
                                            alasan_koreksi = st.text_area("Alasan koreksi:", key=f"corr_reason_{sid}")
                                            if st.button("Simpan Koreksi", key=f"save_corr_{sid}"):
                                                try:
                                                    ok, msg = koreksi_kehadiran(rec_selected.get("ID_Kehadiran", ""), kolom_koreksi, nilai_koreksi, alasan_koreksi, st.session_state.get("tutor_user_id", ""))
                                                    (st.success if ok else st.error)(msg)
                                                    if ok:
                                                        st.rerun()
                                                except Exception as e:
                                                    st.error(f"Koreksi gagal: {e}")
                                except Exception as e:
                                    st.error(f"Modul kehadiran bermasalah: {e}")
                    except Exception as e:
                        st.error(f"Data relasi tutor-siswa belum dapat dibaca: {e}")


        elif menu_tutor == "🗓️ Evaluasi Susulan":
            tampilkan_evaluasi_susulan(st.session_state.get("tutor_id", ""), st.session_state.get("tutor_nama", ""))

        elif menu_tutor == "📨 Pesan Orang Tua":
            st.header("📨 Pesan dari Orang Tua")
            try:
                allowed_ids = siswa_tutor_terhubung(st.session_state.get("tutor_id", ""))
                siswa_rows = baca_records_aman(get_worksheet("Data_Siswa"))
                nama_by_id = {
                    str(r.get("ID_SISWA", r.get("ID_Siswa", ""))).strip():
                    str(r.get("Nama_Siswa", r.get("Nama_Lengkap", ""))).strip()
                    for r in siswa_rows
                }
                ws_pesan = get_pesan_ortu_worksheet()
                pesan_rows = [
                    r for r in baca_records_aman(ws_pesan)
                    if str(r.get("ID_Siswa", "")).strip() in allowed_ids
                ]
                if not pesan_rows:
                    st.info("Belum ada pesan orang tua untuk siswa yang terhubung dengan akun tutor ini.")
                else:
                    for pesan in reversed(pesan_rows):
                        with st.expander(
                            f"{pesan.get('Nama_Siswa', 'Siswa')} · {pesan.get('Waktu_Kirim', '')} · {pesan.get('Status_Pesan', '')}",
                            expanded=str(pesan.get("Status_Pesan", "")).lower().startswith("menunggu")
                        ):
                            st.write(pesan.get("Pesan", "") or "Orang tua mengirim lampiran tanpa catatan teks.")
                            urls = str(pesan.get("URL_Lampiran", "")).split("|") if pesan.get("URL_Lampiran") else []
                            names = str(pesan.get("Nama_File", "")).split("|") if pesan.get("Nama_File") else []
                            mimes = str(pesan.get("Mime_Type", "")).split("|") if pesan.get("Mime_Type") else []
                            for ix, url in enumerate(urls):
                                nm = names[ix] if ix < len(names) else f"Lampiran {ix+1}"
                                mt = mimes[ix] if ix < len(mimes) else ""
                                tampilkan_media_url(url, mt, nm)
                            if pesan.get("Balasan_Tutor"):
                                st.markdown("**Balasan sebelumnya:**")
                                st.write(pesan.get("Balasan_Tutor"))
                            balasan = st.text_area(
                                "Balasan / catatan untuk orang tua:",
                                key=f"balas_pesan_{pesan.get('ID_Pesan')}"
                            )
                            if st.button("Kirim balasan", key=f"kirim_balas_{pesan.get('ID_Pesan')}"):
                                if not balasan.strip():
                                    st.warning("Tulis balasan terlebih dahulu.")
                                else:
                                    headers = ws_pesan.row_values(1)
                                    row_num = int(pesan.get("_baris", 0))
                                    ws_pesan.update_cell(row_num, headers.index("Balasan_Tutor")+1, balasan.strip())
                                    ws_pesan.update_cell(row_num, headers.index("Nama_Tutor")+1, st.session_state.tutor_nama)
                                    ws_pesan.update_cell(row_num, headers.index("Waktu_Balasan")+1, waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"))
                                    ws_pesan.update_cell(row_num, headers.index("Status_Pesan")+1, "Sudah Dibalas")
                                    st.success("Balasan tersimpan.")
                                    st.rerun()
            except Exception as e:
                st.error(f"Pesan orang tua belum dapat dimuat: {e}")


    # =========================================================
    # 3. MODUL OWNER
    # =========================================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    pastikan_koneksi()
    st.subheader("👑 Portal Pengelola Bimbel")
    if "owner_logged_in" not in st.session_state:
        st.session_state.owner_logged_in = False
    # PIN Owner disimpan sebagai HASH pada worksheet khusus agar dapat diganti dari portal.
    # Username/akun pada Akun_Pengguna tidak disentuh.
    ws_owner_security = get_or_create_worksheet(
        "Pengaturan_Aplikasi", ["Kunci", "Nilai"], rows="20", cols="2"
    )
    # Pastikan worksheet lama yang kosong memiliki header. Pemeriksaan dilakukan
    # sekali per sesi agar tidak menambah Read request pada setiap rerun.
    if not st.session_state.get("_owner_security_header_checked", False):
        try:
            header_owner = ws_owner_security.row_values(1)
            if not header_owner:
                ws_owner_security.update("A1:B1", [["Kunci", "Nilai"]])
                _baca_values_cache.clear()
            elif (
                len(header_owner) >= 2
                and str(header_owner[0]).strip() == "PIN_OWNER"
                and str(header_owner[1]).strip()
                and str(header_owner[0]).strip() != "Kunci"
            ):
                # Pemulihan jika PIN_OWNER telanjur tertulis sebagai baris pertama
                # karena header worksheet sebelumnya kosong.
                ws_owner_security.insert_row(["Kunci", "Nilai"], index=1)
                _baca_values_cache.clear()
            st.session_state["_owner_security_header_checked"] = True
        except Exception as exc:
            st.error(f"Gagal memeriksa header penyimpanan PIN Owner: {exc}")
    # Gunakan cache singkat agar rerun Streamlit tidak selalu meminta Read baru.
    owner_settings = baca_records_aman(ws_owner_security)
    owner_pin_records = [
        r for r in owner_settings
        if str(r.get("Kunci", "")).strip() == "PIN_OWNER"
    ]
    owner_pin_record = owner_pin_records[0] if owner_pin_records else None

    if not st.session_state.owner_logged_in:
        pin_owner = st.text_input("PIN Pengelola:", type="password", key="login_owner_pin")
        owner_pin_awal = str(st.secrets.get("owner_pin", "")).strip() or "1605"
        if not owner_pin_record and not str(st.secrets.get("owner_pin", "")).strip():
            st.warning("PIN Pengelola masih memakai PIN bawaan 1605. Setelah login, segera ganti melalui Keamanan Owner.")
        if st.button("Masuk sebagai Pengelola", key="btn_login_owner"):
            muat_ulang_data_bersih()
            record_pin_cocok = None
            if owner_pin_records:
                for kandidat_pin in owner_pin_records:
                    cocok, _ = verifikasi_pin(pin_owner, kandidat_pin.get("Nilai", ""))
                    if cocok:
                        record_pin_cocok = kandidat_pin
                        break
            else:
                cocok = hmac.compare_digest(pin_owner.strip(), owner_pin_awal)
                if cocok:
                    # PIN bawaan belum memiliki baris hash; migrasi dibuat satu kali.
                    ws_owner_security.append_row(["PIN_OWNER", hash_pin(pin_owner.strip())])
                    _baca_values_cache.clear()
            if record_pin_cocok is not None or (not owner_pin_records and cocok):
                # Catat baris hash yang benar-benar cocok untuk sesi ini.
                if record_pin_cocok is not None:
                    st.session_state.owner_pin_row = int(record_pin_cocok.get("_baris", 0) or 0)
                st.session_state.owner_logged_in = True
                st.rerun()
            else:
                st.error("PIN Pengelola salah.")
    if st.session_state.owner_logged_in:
        if st.button("🚪 Logout Pengelola", key="btn_logout_owner"):
            st.session_state.owner_logged_in = False
            st.rerun()
        st.success("Akses diizinkan.")
        # Menu pilihan (bukan st.tabs): lebih mudah ditekan di HP dan hanya bagian terpilih yang diproses.
        _MENU_OWNER = {
            1: "🎁 Undian Hadiah", 2: "👥 Kelola Status Akun", 3: "📚 Arsip Bank Soal",
            4: "🔑 Reset PIN", 5: "🔐 Keamanan Owner", 6: "➕ Tambah Siswa",
            9: "👪 Tambah Orang Tua", 10: "📜 Riwayat Semua Tugas", 11: "🔧 Cek & Perbaiki ID",
            7: "🧪 Audit Data Sistem", 8: "🧩 Pulihkan Tugas Historis",
        }
        _menu_owner_pilih = st.selectbox("Menu Pengelola:", list(_MENU_OWNER.values()), key="menu_owner_pilih")
        tombol_kembali("menu_owner_pilih", wadah=st)

        if _menu_owner_pilih == _MENU_OWNER[11]:
            tampilkan_cek_perbaiki_id()

        if _menu_owner_pilih == _MENU_OWNER[8]:
            st.header("🧩 Pemulihan Kepemilikan Tugas Historis")
            st.caption("Tugas tanpa ID_Tutor tetap disembunyikan dari tutor sampai pengelola memverifikasi dan menetapkan pemiliknya. Tidak ada tugas atau jawaban yang dihapus.")
            try:
                ws_tugas_legacy = get_worksheet("Tugas_Sesi_Siswa_v2")
                tugas_legacy = baca_records_aman(ws_tugas_legacy, refresh=False)
                tutor_legacy = baca_records_aman(get_worksheet("Data_Tutor"), refresh=False)
                pilihan_tutor = {}
                for tr in tutor_legacy:
                    tid = str(tr.get("ID_Tutor", "")).strip()
                    nama_t = str(tr.get("Nama_Tutor", "")).strip()
                    if tid and nama_t:
                        pilihan_tutor[f"{nama_t} · {tid}"] = tid
                tanpa = [t for t in tugas_legacy if not str(t.get("ID_Tutor", "")).strip()]
                st.metric("Tugas historis tanpa ID_Tutor", len(tanpa))
                if not tanpa:
                    st.success("Tidak ada tugas historis tanpa pemilik.")
                elif not pilihan_tutor:
                    st.error("Data_Tutor belum menyediakan pasangan ID_Tutor dan Nama_Tutor yang valid.")
                else:
                    opsi_tugas = {
                        f"{str(t.get('Nama_Siswa','(tanpa nama)'))} | {str(t.get('Judul_Tugas','(tanpa judul)'))} | {str(t.get('ID_Tugas',''))}": t
                        for t in tanpa if str(t.get("ID_Tugas", "")).strip()
                    }
                    if opsi_tugas:
                        label_tugas = st.selectbox("Pilih satu tugas yang sudah diverifikasi", list(opsi_tugas), key="legacy_task_owner_select")
                        label_tutor = st.selectbox("Tetapkan tutor pemilik", list(pilihan_tutor), key="legacy_task_tutor_select")
                        konfirmasi_owner = st.checkbox("Saya sudah memverifikasi bahwa tutor tersebut memang pemilik tugas ini.", key="legacy_task_owner_confirm")
                        if st.button("Simpan pemilik tugas", key="legacy_task_owner_save", disabled=not konfirmasi_owner):
                            target = opsi_tugas[label_tugas]
                            id_tutor_target = pilihan_tutor[label_tutor]
                            headers_tugas = [str(x).strip() for x in ws_tugas_legacy.row_values(1)]
                            if "ID_Tutor" not in headers_tugas:
                                st.error("Kolom ID_Tutor tidak ditemukan. Tidak ada perubahan yang dilakukan.")
                            else:
                                baris_target = int(target.get("_baris", 0) or 0)
                                if baris_target < 2:
                                    st.error("Nomor baris tugas tidak valid. Tidak ada perubahan yang dilakukan.")
                                else:
                                    col_tutor = headers_tugas.index("ID_Tutor") + 1
                                    ws_tugas_legacy.update_cell(baris_target, col_tutor, id_tutor_target)
                                    _baca_values_cache.clear()
                                    st.success("ID_Tutor berhasil ditetapkan untuk satu tugas. Periksa kembali daftar sebelum memulihkan tugas berikutnya.")
                                    st.rerun()
                    st.dataframe(pd.DataFrame([{
                        "Nama Siswa": t.get("Nama_Siswa", ""),
                        "Judul Tugas": t.get("Judul_Tugas", ""),
                        "ID Tugas": t.get("ID_Tugas", ""),
                        "Tutor lama (referensi saja)": t.get("Tutor", ""),
                    } for t in tanpa]), use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error(f"Daftar tugas historis belum dapat dibaca: {exc.__class__.__name__}")

        if _menu_owner_pilih == _MENU_OWNER[9]:
            st.header("👪 Tambah Orang Tua / Wali Murid")
            st.caption("ID login wali (USR-xxx) dan ID orang tua dibuat otomatis, lalu langsung dihubungkan ke anak.")
            _pesan_ortu = st.session_state.pop("_pesan_ortu_baru", None)
            if _pesan_ortu:
                st.success(_pesan_ortu)
            n_ortu = st.session_state.get("_ortu_baru_n", 0)
            try:
                kata_anak = st.text_input("Ketik nama anak (minimal 3 huruf):", key=f"ortu_baru_cari_{n_ortu}").strip()
                hasil_anak, pesan_anak = cari_siswa_terbatas(kata_anak, get_siswa_aktif())
                anak_dipilih = None
                if hasil_anak:
                    anak_dipilih = st.selectbox("Pilih anak:", hasil_anak, key=f"ortu_baru_anak_{n_ortu}")
                    if pesan_anak:
                        st.caption(pesan_anak)
                elif kata_anak:
                    st.warning(pesan_anak or "Siswa aktif tidak ditemukan.")
                if anak_dipilih:
                    id_anak_baru = get_siswa_id_by_nama(anak_dipilih)
                    if not id_anak_baru:
                        st.error("Identitas anak tidak dapat dipastikan (nama ganda atau ID kosong). Periksa Data_Siswa.")
                    else:
                        try:
                            id_ortu_anak = [
                                str(r.get("ID_Ortu", "")).strip()
                                for r in baca_records_aman(get_worksheet("Relasi_Orangtua_Siswa"))
                                if str(r.get("ID_Siswa", r.get("ID_SISWA", ""))).strip() == id_anak_baru
                            ]
                            if id_ortu_anak:
                                nama_ortu_ada = {
                                    str(r.get("ID_Ortu", "")).strip(): str(r.get("Nama_Ortu", "")).strip()
                                    for r in baca_records_aman(get_worksheet("Data_Orangtua"))
                                }
                                st.info(
                                    f"{anak_dipilih} ({id_anak_baru}) sudah terhubung dengan: "
                                    + ", ".join(f"{i} {nama_ortu_ada.get(i, '')}".strip() for i in id_ortu_anak)
                                    + ". Anda tetap bisa menambah wali lain (misalnya ayah dan ibu)."
                                )
                        except Exception:
                            pass
                        nama_ortu_baru = st.text_input("Nama orang tua / wali *", key=f"ortu_baru_nama_{n_ortu}").strip()
                        hubungan_baru = st.selectbox("Hubungan dengan anak", ["Ayah", "Ibu", "Wali"], key=f"ortu_baru_hub_{n_ortu}")
                        no_hp_ortu_baru = st.text_input("No. HP wali (opsional)", key=f"ortu_baru_hp_{n_ortu}").strip()
                        pin_ortu_baru = st.text_input("PIN awal wali (minimal 6 angka) *", type="password", key=f"ortu_baru_pin_{n_ortu}")
                        pin_ortu_ulang = st.text_input("Ulangi PIN awal *", type="password", key=f"ortu_baru_pin2_{n_ortu}")
                        wali_utama_baru = st.checkbox("Wali utama", value=not id_ortu_anak, key=f"ortu_baru_utama_{n_ortu}")
                        if st.button("Simpan Orang Tua", key=f"ortu_baru_simpan_{n_ortu}"):
                            if not nama_ortu_baru:
                                st.error("Nama orang tua wajib diisi.")
                            elif not pin_ortu_baru.isdigit() or len(pin_ortu_baru) < 6:
                                st.error("PIN awal harus berupa angka minimal 6 digit.")
                            elif pin_ortu_baru != pin_ortu_ulang:
                                st.error("Konfirmasi PIN tidak sama.")
                            else:
                                try:
                                    hasil_ortu_baru = daftarkan_orang_tua(
                                        nama_ortu_baru, hubungan_baru, pin_ortu_baru, id_anak_baru, wali_utama_baru, no_hp_ortu_baru
                                    )
                                    st.session_state["_pesan_ortu_baru"] = (
                                        f"✅ {nama_ortu_baru} ({hubungan_baru} dari {anak_dipilih}) tersimpan. "
                                        f"ID login wali: {hasil_ortu_baru['id_user']} (ID orang tua {hasil_ortu_baru['id_ortu']}) "
                                        "dengan PIN yang baru Anda isi."
                                    )
                                    st.session_state["_ortu_baru_n"] = n_ortu + 1
                                    st.rerun()
                                except Exception as exc_ortu:
                                    st.error(f"Orang tua belum tersimpan lengkap. {exc_ortu}")
            except Exception as exc_tab_ortu:
                st.error(f"Form orang tua belum dapat dibuka: {exc_tab_ortu}")

        if _menu_owner_pilih == _MENU_OWNER[10]:
            tampilkan_riwayat_tugas_owner()

        if _menu_owner_pilih == _MENU_OWNER[7]:
            st.header("🧪 Audit Data Sistem")
            st.caption(
                "Pemeriksaan baca-saja untuk membantu menelusuri masalah aplikasi. "
                "Audit tidak mengubah Google Sheets dan tidak mengekspor data pribadi siswa."
            )
            st.warning(
                "Saat dijalankan, sistem membaca header seluruh worksheet dan isi ringkas "
                "sejumlah tabel operasional. Hindari menjalankan audit berulang kali dalam waktu singkat."
            )
            if st.button("Jalankan Audit dan Siapkan Paket", key="btn_jalankan_audit_sistem"):
                try:
                    with st.spinner("Memeriksa struktur dan konsistensi data..."):
                        paket_audit = buat_paket_audit_sistem()
                    st.session_state["paket_audit_sistem"] = paket_audit
                    st.success("Paket audit berhasil dibuat. Tidak ada data yang diubah.")
                except Exception as exc:
                    st.error(f"Audit belum selesai: {exc}")

            paket_audit = st.session_state.get("paket_audit_sistem")
            if paket_audit:
                st.metric("Worksheet terdeteksi", paket_audit.get("total_sheet", 0))
                st.metric("Pemeriksaan", paket_audit.get("total_pemeriksaan", 0))
                st.markdown("**Ringkasan pemeriksaan**")
                st.dataframe(pd.DataFrame(paket_audit.get("pemeriksaan", [])), use_container_width=True, hide_index=True)
                diagnostik = paket_audit.get("diagnostik_duplikasi_id", {})
                if diagnostik:
                    st.markdown("**Pemeriksaan duplikasi ID_SISWA (tanpa identitas pribadi)**")
                    st.caption(
                        f"ID unik: {diagnostik.get('jumlah_id_unik', 0)} · "
                        f"Kelompok duplikat: {diagnostik.get('jumlah_kelompok_duplikat', 0)} · "
                        f"Kemunculan berulang: {diagnostik.get('jumlah_kemunculan_berulang', 0)}"
                    )
                    st.dataframe(pd.DataFrame(diagnostik.get("kelompok", [])), use_container_width=True, hide_index=True)
                st.markdown("**Struktur worksheet**")
                struktur_ringkas = [{
                    "Nama Sheet": x.get("nama_sheet"),
                    "Baris Data": x.get("jumlah_baris_terisi"),
                    "Jumlah Header": x.get("jumlah_kolom_header"),
                    "Status Baca": x.get("status_baca"),
                } for x in paket_audit.get("ringkasan_sheet", [])]
                st.dataframe(pd.DataFrame(struktur_ringkas), use_container_width=True, hide_index=True)
                json_audit = json.dumps(paket_audit, ensure_ascii=False, indent=2)
                csv_audit = pd.DataFrame(paket_audit.get("pemeriksaan", [])).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Unduh Paket Audit (JSON)", data=json_audit.encode("utf-8"),
                    file_name="Audit_Bimbel_Rumah_Nazma.json", mime="application/json",
                    key="download_audit_json"
                )
                st.download_button(
                    "⬇️ Unduh Ringkasan Audit (CSV)", data=csv_audit,
                    file_name="Ringkasan_Audit_Bimbel_Nazma.csv", mime="text/csv",
                    key="download_audit_csv"
                )
                csv_duplikat = pd.DataFrame(diagnostik.get("kelompok", [])).to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "⬇️ Unduh Diagnostik Duplikasi ID (CSV)", data=csv_duplikat,
                    file_name="Diagnostik_Duplikasi_ID_Siswa.csv", mime="text/csv",
                    key="download_audit_duplikat_csv"
                )

        if _menu_owner_pilih == _MENU_OWNER[6]:
            st.header("➕ Pendaftaran Siswa Baru")
            st.caption("Isi satu formulir saja. ID dibuat otomatis; data disimpan ke Data_Siswa dan akun login siswa dibuat di Akun_Pengguna.")
            _pesan_daftar = st.session_state.pop("_pesan_daftar_siswa", None)
            if _pesan_daftar:
                (st.success if _pesan_daftar[0] == "success" else st.warning)(_pesan_daftar[1])
            try:
                ws_daftar = get_worksheet("Data_Siswa")
                values_daftar = _baca_values_cache(sheet.id, ws_daftar.title)
                headers_daftar = [str(h).strip() for h in values_daftar[0]] if values_daftar else []
                kolom_id = "ID_SISWA" if "ID_SISWA" in headers_daftar else (
                    "ID_Siswa" if "ID_Siswa" in headers_daftar else None
                )
                kolom_nama = "Nama_Lengkap" if "Nama_Lengkap" in headers_daftar else (
                    "Nama_Siswa" if "Nama_Siswa" in headers_daftar else None
                )
                kolom_pin = "PIN_Siswa" if "PIN_Siswa" in headers_daftar else None
                kolom_jenjang = "Jenjang" if "Jenjang" in headers_daftar else None
                kolom_kelas = "Kelas" if "Kelas" in headers_daftar else None
                kolom_status = "Status" if "Status" in headers_daftar else None
                kolom_poin = "Poin" if "Poin" in headers_daftar else None
                kolom_tanggal = next((c for c in ("Tanggal_Daftar", "Tanggal_Masuk", "Tanggal") if c in headers_daftar), None)

                wajib_tidak_ada = [
                    nama for nama, kolom in (
                        ("ID_SISWA atau ID_Siswa", kolom_id),
                        ("Nama_Lengkap atau Nama_Siswa", kolom_nama),
                        ("PIN_Siswa", kolom_pin),
                        ("Jenjang", kolom_jenjang),
                    ) if kolom is None
                ]
                if wajib_tidak_ada:
                    st.error("Header Data_Siswa belum cocok. Kolom yang tidak ditemukan: " + ", ".join(wajib_tidak_ada))
                    st.caption("Header yang terbaca: " + " | ".join(headers_daftar))
                else:
                    records_daftar = baca_records_aman(ws_daftar)
                    nomor_terpakai = []
                    for rec in records_daftar:
                        id_lama = str(rec.get(kolom_id, "")).strip()
                        cocok_id = re.fullmatch(r"SIS-(\d+)", id_lama, flags=re.IGNORECASE)
                        if cocok_id:
                            nomor_terpakai.append(int(cocok_id.group(1)))
                    id_baru = f"SIS-{(max(nomor_terpakai, default=0) + 1):03d}"

                    st.info(f"ID siswa berikutnya: **{id_baru}**")
                    # Widget jenjang diletakkan di luar st.form agar perubahan jenjang
                    # langsung memperbarui daftar kelas pada rerun Streamlit.
                    nama_baru = st.text_input(
                        "Nama lengkap siswa *", key="tambah_siswa_nama"
                    )
                    jenjang_baru = st.selectbox(
                        "Jenjang *", ["TK", "SD", "SMP", "SMA", "Umum"],
                        key="tambah_siswa_jenjang"
                    )
                    kelas_opsi = {
                        "TK": ["Kelompok A", "Kelompok B"],
                        "SD": [f"Kelas {i}" for i in range(1, 7)],
                        "SMP": [f"Kelas {i}" for i in range(7, 10)],
                        "SMA": [f"Kelas {i}" for i in range(10, 13)],
                        "Umum": ["Umum"],
                    }
                    kelas_baru = st.selectbox(
                        "Kelas", kelas_opsi[jenjang_baru],
                        key="tambah_siswa_kelas"
                    )
                    pin_baru = st.text_input(
                        "PIN awal (minimal 6 angka) *", type="password",
                        key="tambah_siswa_pin"
                    )
                    pin_ulang = st.text_input(
                        "Ulangi PIN awal *", type="password",
                        key="tambah_siswa_pin_ulang"
                    )
                    simpan_siswa = st.button(
                        "Simpan Siswa Baru", key="btn_simpan_siswa_baru"
                    )
                    if simpan_siswa:
                        nama_input = nama_baru.strip()
                        if not nama_input:
                            st.error("Nama siswa wajib diisi.")
                        elif not pin_baru.isdigit() or len(pin_baru) < 6:
                            st.error("PIN awal harus berupa angka minimal 6 digit.")
                        elif pin_baru != pin_ulang:
                            st.error("Konfirmasi PIN tidak sama.")
                        else:
                            try:
                                # Baca langsung dari worksheet pada saat tombol ditekan.
                                # Jangan gunakan cache untuk keputusan duplikasi atau ID.
                                data_terkini = ws_daftar.get_all_values()
                                if not data_terkini:
                                    raise RuntimeError("Worksheet Data_Siswa belum memiliki header.")
                                header_terkini = [str(h).strip() for h in data_terkini[0]]
                                if kolom_id not in header_terkini or kolom_nama not in header_terkini:
                                    raise RuntimeError("Header ID atau nama siswa berubah. Periksa Data_Siswa.")

                                idx_id = header_terkini.index(kolom_id)
                                idx_nama = header_terkini.index(kolom_nama)
                                nama_key = nama_input.casefold()

                                # Deteksi nama yang benar-benar sudah ada pada spreadsheet.
                                duplikat = None
                                nomor_terpakai_submit = []
                                for row in data_terkini[1:]:
                                    nama_sheet = str(row[idx_nama] if idx_nama < len(row) else "").strip()
                                    id_sheet = str(row[idx_id] if idx_id < len(row) else "").strip()
                                    if nama_sheet and nama_sheet.casefold() == nama_key:
                                        duplikat = (id_sheet, nama_sheet)
                                    match_id = re.fullmatch(r"SIS-(\d+)", id_sheet, flags=re.IGNORECASE)
                                    if match_id:
                                        nomor_terpakai_submit.append(int(match_id.group(1)))

                                if duplikat:
                                    st.warning(
                                        f"Nama {duplikat[1]} memang sudah ada di Data_Siswa"
                                        + (f" dengan ID {duplikat[0]}." if duplikat[0] else ".")
                                        + " Tidak ada baris baru yang ditambahkan."
                                    )
                                else:
                                    id_submit = f"SIS-{(max(nomor_terpakai_submit, default=0) + 1):03d}"
                                    # Gunakan header aktual, bukan asumsi urutan kolom.
                                    row_baru = []
                                    for header in header_terkini:
                                        if header == kolom_id:
                                            row_baru.append(id_submit)
                                        elif header == kolom_nama:
                                            row_baru.append(nama_input)
                                        elif header == kolom_pin:
                                            row_baru.append(hash_pin(pin_baru))
                                        elif header == kolom_jenjang:
                                            row_baru.append(jenjang_baru)
                                        elif header == kolom_kelas:
                                            row_baru.append(kelas_baru)
                                        elif header == "Mapel_Diambil":
                                            row_baru.append("")
                                        elif header == "PIN_Ortu":
                                            row_baru.append("")
                                        elif header == kolom_status:
                                            row_baru.append("Aktif")
                                        elif header == kolom_poin:
                                            row_baru.append("0")
                                        elif header == kolom_tanggal:
                                            row_baru.append(waktu_lokal().strftime("%Y-%m-%d"))
                                        else:
                                            row_baru.append("")

                                    nomor_baris_baru = tulis_baris_di_bawah(
                                        ws_daftar, row_baru, "USER_ENTERED", nilai_sekarang=data_terkini
                                    )

                                    # Konfirmasi dengan membaca ulang spreadsheet, bukan mengandalkan
                                    # respons tombol atau tabel cache.
                                    _baca_values_cache.clear()
                                    data_verifikasi = ws_daftar.get_all_values()
                                    header_verifikasi = [
                                        str(h).strip() for h in data_verifikasi[0]
                                    ] if data_verifikasi else []
                                    if kolom_id not in header_verifikasi or kolom_nama not in header_verifikasi:
                                        raise RuntimeError(
                                            "Baris dikirim, tetapi header tidak dapat diverifikasi. "
                                            "Periksa Data_Siswa sebelum mencoba lagi."
                                        )
                                    vi_id = header_verifikasi.index(kolom_id)
                                    vi_nama = header_verifikasi.index(kolom_nama)
                                    tersimpan = any(
                                        len(row) > max(vi_id, vi_nama)
                                        and str(row[vi_id]).strip() == id_submit
                                        and str(row[vi_nama]).strip().casefold() == nama_key
                                        for row in data_verifikasi[1:]
                                    )
                                    if tersimpan:
                                        st.session_state["pendaftaran_sukses_terakhir"] = (
                                            id_submit, nama_input
                                        )
                                        # Login siswa membaca Akun_Pengguna, jadi akun dibuat sekaligus di sini.
                                        try:
                                            buat_akun_pengguna(nama_input, "Siswa", pin_baru, id_siswa=id_submit)
                                            st.session_state["_pesan_daftar_siswa"] = (
                                                "success",
                                                f"✅ {nama_input} tersimpan. ID login siswa: **{id_submit}** "
                                                "dengan PIN yang baru Anda isi. Akun login sudah dibuat otomatis."
                                            )
                                        except Exception as exc_akun:
                                            st.session_state["_pesan_daftar_siswa"] = (
                                                "warning",
                                                f"{nama_input} ({id_submit}) tersimpan di Data_Siswa, tetapi akun login "
                                                f"belum dibuat: {exc_akun}. Siswa belum bisa login sampai akunnya dibuat."
                                            )
                                        st.rerun()
                                    else:
                                        st.error(
                                            "Permintaan simpan sudah dikirim, tetapi baris belum "
                                            "terbaca kembali dari Google Sheets. Jangan tekan Simpan "
                                            "lagi dulu; periksa Data_Siswa agar tidak terjadi duplikasi."
                                        )
                            except Exception as exc:
                                st.error(
                                    f"Pendaftaran belum dapat dikonfirmasi: {exc}. "
                                    "Periksa Data_Siswa sebelum mencoba menyimpan ulang."
                                )
                    st.divider()
                    st.markdown("**Siswa terdaftar terbaru**")
                    if records_daftar:
                        ringkas = [
                            {
                                "ID": str(r.get(kolom_id, "")),
                                "Nama": str(r.get(kolom_nama, "")),
                                "Jenjang": str(r.get(kolom_jenjang, "")),
                                "Kelas": str(r.get(kolom_kelas, "")) if kolom_kelas else "",
                                "Status": str(r.get(kolom_status, "Aktif")) if kolom_status else "Aktif",
                            }
                            for r in records_daftar[-10:]
                        ]
                        st.dataframe(pd.DataFrame(ringkas[::-1]), use_container_width=True, hide_index=True)
            except Exception as exc:
                st.error(f"Form pendaftaran siswa belum dapat dibuka: {exc}")

        if _menu_owner_pilih == _MENU_OWNER[1]:
            data_siswa_all = baca_records_aman(get_worksheet("Data_Siswa"))
            peserta_undian = []
            for s in data_siswa_all:
                try:
                    p_val = int(float(str(s.get("Poin", 0) or 0).strip() or 0))
                except (ValueError, TypeError):
                    p_val = 0
                if p_val >= 100 and str(s.get("Status", "Aktif")).strip().lower() != "nonaktif":
                    peserta_undian.append({
                        "Nama": s.get("Nama_Lengkap"),
                        "Jenjang": s.get("Jenjang"),
                        "Poin": p_val
                    })
            if peserta_undian:
                st.dataframe(pd.DataFrame(peserta_undian), use_container_width=True)
                if st.button("🎲 Undi Pemenang"):
                    pemenang = random.choice(peserta_undian)
                    st.balloons()
                    st.success(
                        f"Selamat kepada **{pemenang['Nama']}** ({pemenang['Jenjang']})!"
                    )
            else:
                st.info("Belum ada siswa yang mencapai 100 poin.")

        if _menu_owner_pilih == _MENU_OWNER[2]:
            ws_siswa = get_worksheet("Data_Siswa")
            records_siswa = baca_records_aman(ws_siswa)
            if records_siswa:
                kolom_tampil = [
                    c for c in ["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]
                    if c in records_siswa[0]
                ]
                # Tambahkan akun pengguna (USR) siswa dan orang tua serta nama ortu.
                peta_ortu = {}
                ortu_info, akun_siswa = {}, {}
                try:
                    for o in baca_records_aman(get_worksheet("Data_Orangtua")):
                        ortu_info[str(o.get("ID_Ortu", "")).strip()] = (
                            str(o.get("ID_User", "")).strip(), str(o.get("Nama_Ortu", "")).strip()
                        )
                    for rel in baca_records_aman(get_worksheet("Relasi_Orangtua_Siswa")):
                        sid, oid = str(rel.get("ID_Siswa", "")).strip(), str(rel.get("ID_Ortu", "")).strip()
                        if sid and oid:
                            peta_ortu.setdefault(sid.upper(), []).append(oid)
                    for ak in baca_records_aman(get_worksheet("Akun_Pengguna")):
                        if str(ak.get("Level_Akses", "")).strip().casefold() == "siswa":
                            kid = str(ak.get("ID_SISWA", ak.get("ID_Siswa", ""))).strip().upper()
                            if kid:
                                akun_siswa[kid] = str(ak.get("ID_User", "")).strip()
                except Exception:
                    pass
                df_kelola = pd.DataFrame(records_siswa)[kolom_tampil].copy()
                _ids = [str(x).strip().upper() for x in df_kelola["ID_Siswa"]] if "ID_Siswa" in df_kelola else []
                df_kelola["Akun_Siswa (USR)"] = [akun_siswa.get(i, "-") or "-" for i in _ids]
                df_kelola["Akun_Ortu (USR)"] = [
                    ", ".join((ortu_info.get(o, ("", ""))[0] or "-") for o in peta_ortu.get(i, [])) or "-" for i in _ids
                ]
                df_kelola["Nama_Ortu"] = [
                    ", ".join((ortu_info.get(o, ("", ""))[1] or o) for o in peta_ortu.get(i, [])) or "-" for i in _ids
                ]
                st.dataframe(df_kelola, use_container_width=True, hide_index=True)
                with st.form("form_status"):
                    # Pakai ID siswa (bukan nama) agar yang diubah pasti baris siswa yang dipilih.
                    opsi_status = {
                        f"{s.get('Nama_Lengkap')} · {s.get('ID_Siswa', '')}": s
                        for s in records_siswa if s.get("Nama_Lengkap")
                    }
                    pilih_nama = st.selectbox("Pilih Siswa:", list(opsi_status.keys()))
                    status_baru = st.selectbox("Status:", ["Aktif", "Nonaktif"])
                    if st.form_submit_button("Update Status"):
                        headers = ws_siswa.row_values(1)
                        if "Status" in headers:
                            ws_siswa.update_cell(opsi_status[pilih_nama]["_baris"], headers.index("Status") + 1, status_baru)
                            st.success("Status berhasil diperbarui.")
                            st.rerun()
                        else:
                            st.error("Kolom Status tidak ditemukan di Data_Siswa.")
            else:
                st.info("Data siswa kosong.")

        if _menu_owner_pilih == _MENU_OWNER[3]:
            try:
                ws_bank = get_worksheet("Bank_Soal_Master")
                st.dataframe(pd.DataFrame(baca_records_aman(ws_bank)).drop(columns=["_baris"], errors="ignore"), use_container_width=True)
            except Exception as e:
                st.error(f"Bank soal belum dapat dibuka: {e}")
            # FITUR BARU: konverter soal otomatis
            st.markdown("---")
            st.subheader("📥 Tambah soal ke Bank Soal (otomatis rapi)")
            tampilkan_konverter_bank_soal("owner")

        if _menu_owner_pilih == _MENU_OWNER[4]:
            st.caption("Owner dapat membuat PIN pengganti. PIN langsung disimpan dalam bentuk HASH; pengguna dapat menggantinya lagi setelah login.")
            jenis_akun = st.radio("Jenis akun", ["Siswa", "Tutor / Orang Tua"], horizontal=True, key="owner_jenis_reset")
            if jenis_akun == "Siswa":
                ws_reset = get_worksheet("Akun_Pengguna")
                ws_siswa_reset = get_worksheet("Data_Siswa")
                daftar_reset = pastikan_pemetaan_id_siswa(ws_reset, ws_siswa_reset)
                field_pin_reset = "PIN_Password"
                pilihan_reset = {
                    f"{r.get('Nama_Pengguna', 'Tanpa nama')} · {r.get('ID_SISWA', '')}": r
                    for r in daftar_reset
                    if str(r.get("Level_Akses", "")).strip().casefold() == "siswa"
                    and r.get("ID_SISWA")
                    and str(r.get("Akses_Khusus", "Siswa")).strip().casefold() == "siswa"
                }
            else:
                ws_reset = get_worksheet("Akun_Pengguna")
                daftar_reset = baca_records_aman(ws_reset)
                field_pin_reset = "PIN_Password"
                pilihan_reset = {
                    f"{r.get('Nama_Pengguna', r.get('Username', 'Tanpa nama'))} · {r.get('Username', '')}": r
                    for r in daftar_reset if r.get("Username") and str(r.get("Status", "Aktif")).strip().casefold() != "nonaktif"
                }
            if pilihan_reset:
                with st.form("owner_form_reset_pin"):
                    target_reset = st.selectbox("Pilih akun", list(pilihan_reset.keys()))
                    pin_reset = st.text_input("PIN pengganti (minimal 6 angka)", type="password")
                    pin_reset_ulang = st.text_input("Ulangi PIN pengganti", type="password")
                    konfirmasi_reset = st.checkbox("Saya memastikan akun yang dipilih benar.")
                    submit_reset = st.form_submit_button("Reset PIN Akun")
                if submit_reset:
                    if not konfirmasi_reset:
                        st.error("Centang konfirmasi sebelum melanjutkan.")
                    elif not pin_reset.isdigit() or len(pin_reset) < 6:
                        st.error("PIN pengganti harus berupa angka dan minimal 6 digit.")
                    elif pin_reset != pin_reset_ulang:
                        st.error("Konfirmasi PIN tidak sama.")
                    else:
                        try:
                            record_target = pilihan_reset[target_reset]
                            if jenis_akun == "Tutor / Orang Tua":
                                simpan_pin_baru(
                                    ws_reset,
                                    record_target,
                                    field_pin_reset,
                                    pin_reset,
                                    identity_field="Username",
                                    identity_value=record_target.get("Username", "")
                                )
                            else:
                                simpan_pin_baru(
                                    ws_reset, record_target, field_pin_reset, pin_reset,
                                    identity_field="ID_User",
                                    identity_value=record_target.get("ID_User", "")
                                )
                            st.success("PIN akun berhasil direset, dibaca ulang, dan diverifikasi pada baris akun yang tepat.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Reset PIN gagal: {exc}")
            else:
                st.info("Tidak ada akun yang dapat dipilih pada kategori ini.")

        if _menu_owner_pilih == _MENU_OWNER[5]:
            st.caption("Ganti PIN Owner langsung dari portal. PIN disimpan sebagai HASH pada worksheet Pengaturan_Aplikasi; data username dan akun pengguna tidak diubah.")
            owner_settings = baca_records_aman(ws_owner_security)
            owner_pin_records = [
                r for r in owner_settings
                if str(r.get("Kunci", "")).strip() == "PIN_OWNER"
            ]
            owner_pin_record = next(
                (r for r in owner_pin_records
                 if int(r.get("_baris", 0) or 0) == int(st.session_state.get("owner_pin_row", 0) or 0)),
                owner_pin_records[0] if owner_pin_records else None
            )
            if owner_pin_record:
                form_ganti_pin(ws_owner_security, owner_pin_record, "Nilai", "owner", identity_field="Kunci", identity_value="PIN_OWNER")
            else:
                st.error("Data PIN Owner belum ditemukan. Silakan logout lalu login kembali untuk membuat penyimpanan PIN aman.")


# =========================================================
# 4. MODUL ORANG TUA - login melalui Akun_Pengguna
# =========================================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua (Wali Siswa)")
    st.caption("Masuk menggunakan ID_User dan PIN Wali yang terdaftar di Akun_Pengguna.")

    if "ortu_logged_in" not in st.session_state:
        st.session_state.ortu_logged_in = False
        st.session_state.ortu_user_id = ""
        st.session_state.ortu_id = ""
        st.session_state.ortu_nama = ""
        st.session_state.ortu_children = []

    def _norm_text(value):
        return str(value or "").strip().casefold()

    def _status_aktif(value, default=True):
        status = _norm_text(value)
        if not status:
            return default
        return status not in {"nonaktif", "tidak aktif", "inactive", "0", "false", "berhenti"}

    def _ambil_anak_wali(id_ortu):
        relasi_rows = baca_records_aman(get_worksheet("Relasi_Orangtua_Siswa"))
        siswa_rows = baca_records_aman(get_worksheet("Data_Siswa"))

        # Header Data_Siswa yang dipastikan pengguna adalah ID_SISWA (huruf kapital).
        siswa_by_id = {}
        for siswa in siswa_rows:
            sid = str(siswa.get("ID_SISWA", siswa.get("ID_Siswa", ""))).strip()
            if sid:
                siswa_by_id[sid] = siswa

        anak = []
        for relasi in relasi_rows:
            rid_ortu = str(relasi.get("ID_Ortu", "")).strip()
            status_relasi = relasi.get("Status_Relasi", "")
            if rid_ortu != str(id_ortu).strip() or not _status_aktif(status_relasi):
                continue

            sid = str(relasi.get("ID_Siswa", relasi.get("ID_SISWA", ""))).strip()
            siswa = siswa_by_id.get(sid)
            if not siswa:
                continue
            if not _status_aktif(siswa.get("Status", "Aktif")):
                continue

            anak.append({
                "ID_SISWA": sid,
                "Nama_Lengkap": str(siswa.get("Nama_Lengkap", "")).strip(),
                "Jenjang": str(siswa.get("Jenjang", "")).strip(),
                "Kelas": str(siswa.get("Kelas", "")).strip(),
                "Hubungan": str(relasi.get("Hubungan", "")).strip(),
                "Wali_Utama": str(relasi.get("Wali_Utama", "")).strip(),
            })

        # Hindari duplikasi relasi yang tidak sengaja.
        hasil = []
        terlihat = set()
        for item in anak:
            if item["ID_SISWA"] not in terlihat:
                terlihat.add(item["ID_SISWA"])
                hasil.append(item)
        return hasil

    if not st.session_state.ortu_logged_in:
        id_wali_login = st.text_input("ID Wali (ID_User):", key="login_ortu_id").strip().upper()
        pin_ortu = st.text_input("PIN Wali (minimal 6 angka):", type="password", key="login_ortu_pin")

        if st.button("Masuk Portal Wali Murid", key="btn_login_ortu"):
            pastikan_koneksi()
            muat_ulang_data_bersih()
            try:
                akun_rows = baca_records_aman(get_worksheet("Akun_Pengguna"))
                akun = next((
                    r for r in akun_rows
                    if str(r.get("ID_User", "")).strip().upper() == id_wali_login
                    and verifikasi_pin(pin_ortu, r.get("PIN_Password", ""))[0]
                ), None)

                if akun:
                    cocok_pin, pin_lama_plain = verifikasi_pin(pin_ortu, akun.get("PIN_Password", ""))
                    if cocok_pin and pin_lama_plain:
                        upgrade_pin_lama(get_worksheet("Akun_Pengguna"), akun, "PIN_Password", pin_ortu)

                if not id_wali_login or not pin_ortu.strip():
                    st.error("ID Wali dan PIN wajib diisi.")
                elif not akun:
                    st.error("ID atau PIN tidak sesuai.")
                elif not _status_aktif(akun.get("Status", "Aktif")):
                    st.error("🚫 Akun ini sudah Nonaktif. Silakan hubungi pengelola.")
                else:
                    level_valid = adalah_akun_ortu(akun)
                    if not level_valid:
                        st.error("Akun ini bukan akun Wali Murid. Periksa Level_Akses di Akun_Pengguna.")
                    else:
                        user_id = str(akun.get("ID_User", "")).strip()
                        ortu_rows = baca_records_aman(get_worksheet("Data_Orangtua"))
                        ortu = next((
                            r for r in ortu_rows
                            if str(r.get("ID_User", "")).strip() == user_id
                            and _status_aktif(r.get("Status_Ortu", "Aktif"))
                        ), None)

                        if not ortu:
                            st.error("Data orang tua aktif dengan ID_User tersebut tidak ditemukan di Data_Orangtua.")
                        else:
                            id_ortu = str(ortu.get("ID_Ortu", "")).strip()
                            anak = _ambil_anak_wali(id_ortu)
                            if not anak:
                                st.error("Belum ada anak dengan relasi aktif untuk akun wali murid ini.")
                            else:
                                st.session_state.ortu_logged_in = True
                                st.session_state.ortu_user_id = user_id
                                st.session_state.ortu_id = id_ortu
                                st.session_state.ortu_nama = str(ortu.get("Nama_Ortu", akun.get("Nama_Pengguna", "Wali Murid"))).strip()
                                st.session_state.ortu_children = anak
                                st.session_state.ortu_baris = int(akun.get("_baris", 0))
                                st.rerun()
            except Exception as e:
                st.error(f"Gagal memeriksa akun wali murid: {e}")

    else:
        pastikan_koneksi()
        col_welcome, col_logout = st.columns([4, 1])
        with col_welcome:
            st.success(f"Selamat datang, **{st.session_state.ortu_nama}** 👋")
        with col_logout:
            if st.button("🚪 Logout", key="btn_logout_ortu"):
                for key in [
                    "ortu_logged_in", "ortu_user_id", "ortu_id",
                    "ortu_nama", "ortu_children", "pilihan_anak_wali", "ortu_baris"
                ]:
                    st.session_state.pop(key, None)
                st.rerun()

        # Pengaturan PIN orang tua dipindahkan ke menu khusus agar tidak memenuhi beranda.

        anak_list = st.session_state.get("ortu_children", [])
        if not anak_list:
            st.warning("Data anak tidak ditemukan. Silakan logout lalu masuk kembali.")
            st.stop()
        if len(anak_list) > 1:
            pilihan_anak = st.selectbox(
                "Pilih anak yang ingin dilihat",
                options=range(len(anak_list)),
                format_func=lambda i: (
                    f"{anak_list[i]['Nama_Lengkap']} "
                    f"({anak_list[i]['Jenjang']} {anak_list[i]['Kelas']})"
                ),
                key="pilihan_anak_wali"
            )
            anak_aktif = anak_list[pilihan_anak]
        else:
            anak_aktif = anak_list[0]

        id_anak_ortu = anak_aktif["ID_SISWA"]
        nama_anak_aktif = anak_aktif["Nama_Lengkap"]

        st.markdown(
            f"**Anak:** {nama_anak_aktif}  \n"
            f"**Jenjang/Kelas:** {anak_aktif['Jenjang']} / {anak_aktif['Kelas']}  \n"
            f"**Hubungan:** {anak_aktif['Hubungan'] or '-'}"
        )
        st.markdown("---")

        st.markdown(
            f'<div class="portal-hero"><h2>Beranda Belajar {nama_anak_aktif} 👋</h2>'
            '<p>Pantau sesi, tugas, nilai, dan kehadiran anak</p></div>',
            unsafe_allow_html=True
        )
        menu_ortu = st.sidebar.radio(
            "MENU WALI MURID",
            ["🏠 Beranda Anak", "📋 Transparansi Sesi & PR",
             "📈 Rekap Nilai & Evaluasi", "🕒 Kehadiran Anak",
             "💬 Pesan untuk Tutor", "⚙️ Pengaturan Akun"],
            label_visibility="visible",
            key="menu_navigasi_ortu"
        )
        st.sidebar.markdown("---")
        tombol_kembali("menu_navigasi_ortu")
        tombol_muat_ulang_sidebar("muat_ulang_ortu")
        st.sidebar.caption(f"Wali murid: {st.session_state.ortu_nama}")
        st.sidebar.caption(f"Anak aktif: {nama_anak_aktif}")

        if menu_ortu == "🏠 Beranda Anak":
            st.markdown("#### Ringkasan Anak")
            st.markdown(
                f"**Nama:** {nama_anak_aktif}  \n"
                f"**Jenjang/Kelas:** {anak_aktif['Jenjang']} / {anak_aktif['Kelas']}  \n"
                f"**Hubungan:** {anak_aktif['Hubungan'] or '-'}"
            )
            st.info("Gunakan menu di sebelah kiri untuk melihat laporan sesi, nilai, dan kehadiran anak.")

        elif menu_ortu == "📋 Transparansi Sesi & PR":
            laporan_list = []
            try:
                ws_riwayat = get_worksheet("Riwayat_Latihan")
                for r in baca_records_aman(ws_riwayat):
                    nama_r = str(r.get("Nama_Siswa", "")).strip()
                    if _norm_text(nama_r) == _norm_text(nama_anak_aktif):
                        laporan_list.append({
                            "Tanggal": r.get("Waktu_Selesai", "-"),
                            "Materi": f"[{r.get('Mapel')}] {r.get('Topik_Kuis')}",
                            "Skor": r.get("Skor", "-"),
                            "Catatan": r.get("Detail_Salah", "-")
                        })
            except Exception:
                pass

            try:
                ws_jurnal = get_worksheet("Form Responses 1")
                for j in baca_records_aman(ws_jurnal):
                    val_nama = str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip()
                    if _norm_text(val_nama) == _norm_text(nama_anak_aktif):
                        laporan_list.append({
                            "Tanggal": j.get("Tanggal Mengajar", j.get("Tanggal", "-")),
                            "Materi": j.get("Materi dan Pelajaran Hari Ini", j.get("Materi", "-")),
                            "Skor": j.get("Nilai/skor latihan", j.get("Skor", "-")),
                            "Catatan": j.get("Pencapaian Belajar", "-")
                        })
            except Exception:
                pass

            if laporan_list:
                st.dataframe(pd.DataFrame(laporan_list), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada catatan sesi atau PR untuk anak ini.")

        elif menu_ortu == "📈 Rekap Nilai & Evaluasi":
            st.header("📈 Rekap Nilai & Evaluasi")
            data_tabel_ortu = []
            try:
                peta_pel_ortu = hitung_pelanggaran_fokus()
                nilai_ortu = baca_nilai_tugas_terpadu()
                tugas_ortu = {
                    str(t.get("ID_Tugas", "")).strip(): t
                    for t in get_student_tasks()
                    if str(t.get("ID_Siswa", "")).strip() == str(id_anak_ortu).strip()
                    or _norm_text(t.get("Nama_Siswa", "")) == _norm_text(nama_anak_aktif)
                }
                for n in nilai_ortu:
                    id_tugas_nilai = str(n.get("ID_Penugasan", n.get("ID_Tugas", ""))).strip()
                    if str(n.get("ID_Siswa", "")).strip() != str(id_anak_ortu).strip():
                        continue
                    tugas = tugas_ortu.get(id_tugas_nilai, {})
                    if not tugas:
                        continue
                    data_tabel_ortu.append({
                        "Tanggal": n.get("Tanggal_Penilaian", n.get("Waktu_Penilaian", "-")),
                        "Mapel": tugas.get("Mapel", "-"),
                        "Aktivitas": tugas.get("Judul_Tugas", id_tugas_nilai or "-"),
                        "Nilai": n.get("Nilai", "-"),
                        "Pelanggaran (keluar tab)": teks_pelanggaran(
                            peta_pel_ortu.get((id_tugas_nilai, str(id_anak_ortu).strip()), 0)
                        ),
                        "Evaluasi Tutor": n.get("Umpan_Balik", n.get("Catatan", "-")),
                        "Tutor": tugas.get("Tutor") or n.get("Tutor") or n.get("ID_Tutor_Penilai", "-")
                    })
            except Exception as exc:
                st.warning(f"Nilai anak belum dapat dibaca dari sistem: {exc}")

            if data_tabel_ortu:
                st.dataframe(pd.DataFrame(data_tabel_ortu), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada nilai yang diterbitkan untuk anak ini.")

            st.subheader("📝 Evaluasi Sesi dari Tutor")
            try:
                evaluasi_anak = baca_evaluasi_mapel_anak(nama_anak_aktif)
            except Exception as exc:
                evaluasi_anak = []
                st.warning(f"Evaluasi sesi belum dapat dibaca: {exc}")
            if evaluasi_anak:
                st.dataframe(pd.DataFrame([{
                    "Tanggal": e.get("Tanggal", "-"), "Mapel": e.get("Mapel", "-"), "Materi": e.get("Materi", "-"),
                    "Target": e.get("Target", "-"), "Dikuasai": e.get("Capaian", "-"),
                    "Perlu penguatan": e.get("Penguatan", "-"), "Nilai latihan": e.get("Nilai", "-"),
                    "Tutor": e.get("Tutor", "-")
                } for e in evaluasi_anak]), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada evaluasi sesi dari tutor untuk anak ini.")


        elif menu_ortu == "⚙️ Pengaturan Akun":
            st.header("⚙️ Pengaturan Akun Orang Tua")
            st.caption("Ubah PIN akun wali murid. Username dan identitas akun tidak berubah.")
            akun_ortu_aktif = None
            if st.session_state.get("ortu_baris"):
                akun_ortu_aktif = next((
                    r for r in baca_records_aman(get_worksheet("Akun_Pengguna"))
                    if int(r.get("_baris", 0) or 0) == int(st.session_state.ortu_baris)
                ), None)
            if akun_ortu_aktif:
                form_ganti_pin(
                    get_worksheet("Akun_Pengguna"), akun_ortu_aktif,
                    "PIN_Password", "ortu",
                    identity_field="ID_User",
                    identity_value=akun_ortu_aktif.get("ID_User", "")
                )
            else:
                st.warning("Data akun orang tua belum ditemukan. Silakan logout lalu login kembali.")

        elif menu_ortu == "🕒 Kehadiran Anak":
            tampilkan_riwayat_kehadiran(id_anak_ortu, "Riwayat Kehadiran Anak")

        elif menu_ortu == "💬 Pesan untuk Tutor":
            st.header("💬 Pesan untuk Tutor")
            st.caption("Kirim catatan dari sekolah, pertanyaan, atau hal yang perlu dibahas saat bimbel. Sertakan foto, audio, atau video bila diperlukan.")
            with st.form(f"form_pesan_ortu_{id_anak_ortu}", clear_on_submit=True):
                pesan_ortu = st.text_area(
                    "Catatan untuk tutor:",
                    placeholder="Contoh: Anak mendapat tugas grammar dari sekolah dan masih kesulitan memahami simple past tense."
                )
                lampiran_ortu = st.file_uploader(
                    "Lampirkan foto, PDF, audio, atau video (opsional):",
                    type=["jpg", "jpeg", "png", "webp", "pdf", "mp4", "mov", "webm", "m4v",
                          "mp3", "wav", "m4a", "ogg", "aac"],
                    accept_multiple_files=True,
                    key=f"upload_pesan_ortu_{id_anak_ortu}"
                )
                st.caption("Maksimal 20 MB per file. Lampiran disimpan di Google Drive.")
                kirim_pesan_ortu = st.form_submit_button("📤 Kirim ke Tutor")
            if kirim_pesan_ortu:
                try:
                    simpan_pesan_ortu(
                        st.session_state.ortu_id, id_anak_ortu, nama_anak_aktif,
                        pesan_ortu, lampiran_ortu
                    )
                    st.success("Pesan berhasil dikirim ke daftar pesan tutor yang terhubung dengan anak.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Pesan belum berhasil dikirim: {e}")

            st.markdown("### Riwayat pesan")
            try:
                ws_pesan = get_pesan_ortu_worksheet()
                riwayat_pesan = [
                    r for r in baca_records_aman(ws_pesan)
                    if str(r.get("ID_Ortu", "")).strip() == str(st.session_state.ortu_id).strip()
                    and str(r.get("ID_Siswa", "")).strip() == str(id_anak_ortu).strip()
                ]
                if not riwayat_pesan:
                    st.info("Belum ada pesan yang dikirim.")
                else:
                    for pesan in reversed(riwayat_pesan):
                        with st.expander(f"{pesan.get('Waktu_Kirim', '')} · {pesan.get('Status_Pesan', '')}"):
                            st.write(pesan.get("Pesan", "") or "Pesan berupa lampiran.")
                            if pesan.get("Balasan_Tutor"):
                                st.markdown(f"**Balasan {pesan.get('Nama_Tutor', 'Tutor')}:**")
                                st.write(pesan.get("Balasan_Tutor"))
            except Exception as e:
                st.warning(f"Riwayat pesan belum dapat dibaca: {e}")
