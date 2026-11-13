import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
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
import streamlit.components.v1 as components


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
]

# =========================================================
# KONFIGURASI HALAMAN
# =========================================================
st.set_page_config(
    page_title="Portal Bimbel Rumah Nazma",
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


try:
    client = init_connection()
    sheet = init_spreadsheet()
except Exception as e:
    st.error(
        "Gagal terhubung ke Google Sheets. Jika muncul error 429, kuota baca "
        "Google Sheets untuk akun layanan sedang penuh. Tunggu hingga kuota pulih "
        "sebelum mencoba lagi. Detail: " + str(e)
    )
    st.stop()


def upload_lampiran_ke_drive(file_bytes, file_name, mime_type):
    """Unggah lampiran ke Google Drive melalui Apps Script milik akun Bimbel."""
    try:
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

        response = requests.post(endpoint, json=payload, timeout=120)
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
        return sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=rows, cols=cols)
        ws.append_row(headers)
        return ws


@st.cache_data(ttl=180, show_spinner=False)
def _baca_values_cache(spreadsheet_id, worksheet_title):
    """Cache nilai sheet 3 menit; memakai objek spreadsheet yang sudah di-cache."""
    ws_cached = init_spreadsheet().worksheet(worksheet_title)
    return ws_cached.get_all_values()


def baca_records_aman(ws, refresh=False):
    """Membaca sheet dengan cache 180 detik; refresh=True memaksa pembacaan terbaru."""
    try:
        values = ws.get_all_values() if refresh else _baca_values_cache(sheet.id, ws.title)
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


def simpan_pin_baru(ws, record_aktif, field_name, pin_baru):
    headers = [str(x).strip() for x in ws.row_values(1)]
    if field_name not in headers:
        raise ValueError(f"Kolom {field_name} tidak ditemukan pada {ws.title}.")
    pin_hash_baru = hash_pin(pin_baru)

    # Khusus PIN Owner: jadikan satu baris PIN_OWNER sebagai sumber utama
    # dan bersihkan baris duplikat setelah nilai baru berhasil ditulis.
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
    else:
        ws.update_cell(int(record["_baris"]), headers.index(field_name) + 1, pin_hash_baru)

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
    """Form ganti PIN; verifikasi memakai nilai terbaru langsung dari sheet, bukan cache."""
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
                # Untuk akun siswa, cari ulang berdasarkan ID_User unik saat tombol ditekan.
                # Jangan mengandalkan nomor baris yang disimpan ketika login.
                record_aktif = dict(record)
                if identity_field and identity_value:
                    semua_baris = ws.get_all_values()
                    if not semua_baris:
                        raise ValueError("Data Akun_Pengguna kosong.")
                    header_aktual = [str(x).strip() for x in semua_baris[0]]
                    if identity_field not in header_aktual:
                        raise ValueError(f"Kolom identitas {identity_field} tidak ditemukan.")
                    idx_identitas = header_aktual.index(identity_field)
                    idx_pin = header_aktual.index(field_name) if field_name in header_aktual else -1
                    if idx_pin < 0:
                        raise ValueError(f"Kolom {field_name} tidak ditemukan.")
                    baris_cocok = None
                    for nomor, row in enumerate(semua_baris[1:], start=2):
                        nilai_identitas = row[idx_identitas] if idx_identitas < len(row) else ""
                        if str(nilai_identitas).strip() == str(identity_value).strip():
                            baris_cocok = nomor
                            pin_tersimpan = row[idx_pin] if idx_pin < len(row) else ""
                            break
                    if baris_cocok is None:
                        raise ValueError("Akun tidak ditemukan berdasarkan ID_User. Silakan logout dan login kembali.")
                    record_aktif["_baris"] = baris_cocok
                else:
                    pin_tersimpan = ambil_pin_terkini(ws, record_aktif, field_name)
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
                    simpan_pin_baru(ws, record, field_name, pin_baru)
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
    rows = baca_records_aman(sheet.worksheet("Data_Siswa"))
    return [
        str(s.get("Nama_Lengkap", "")).strip()
        for s in rows
        if str(s.get("Status", "Aktif")).strip().lower() not in ["nonaktif", "tidak aktif"]
        and str(s.get("Nama_Lengkap", "")).strip()
    ]


def get_siswa_id_by_nama(nama):
    for s in baca_records_aman(sheet.worksheet("Data_Siswa")):
        if str(s.get("Nama_Lengkap", "")).strip().lower() == str(nama).strip().lower():
            return str(s.get("ID_Siswa", "")).strip()
    return ""


def adalah_akun_ortu(akun):
    level = str(akun.get("Level_Akses", "") or "").strip().casefold()
    return any(x in level for x in ("ortu", "orang tua", "orangtua", "wali"))


def get_bank_soal():
    """Bank soal tunggal dengan 15 header baru."""
    ws = sheet.worksheet("Bank_Soal_Master")
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


def resolve_tutor_id(user_row):
    """Cocokkan akun login dengan Data_Tutor; tidak menebak ID."""
    user_id = str(user_row.get("ID_User", "")).strip()
    nama_user = str(user_row.get("Nama_Pengguna", "")).strip()
    try:
        tutor_rows = baca_records_aman(sheet.worksheet("Data_Tutor"))
    except Exception:
        return ""
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
        relasi = baca_records_aman(sheet.worksheet("Relasi_Tutor_Siswa"))
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


TASK_HEADERS = ["ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Judul_Tugas", "Jenis_Tugas", "Sumber", "Instruksi", "File_Offline", "Timer_Menit", "Tenggat", "Soal_JSON", "Status_Tugas", "Tutor"]
ANSWER_HEADERS = ["ID_Jawaban", "ID_Penugasan", "ID_Siswa", "Nomor_Soal", "Jawaban", "Status_Jawaban", "Waktu_Tersimpan", "Waktu_Dikumpulkan"]


def get_student_tasks():
    """Membaca tugas dari sheet V2, dengan konversi aman untuk sheet lama."""
    try:
        ws = sheet.worksheet("Tugas_Sesi_Siswa_v2")
        records = baca_records_aman(ws)
        return records
    except gspread.WorksheetNotFound:
        try:
            ws = sheet.worksheet("Tugas_Sesi_Siswa")
            old = baca_records_aman(ws)
        except gspread.WorksheetNotFound:
            return []
        converted = []
        for r in old:
            if r.get("ID_Tugas") or r.get("Nama_Siswa"):
                converted.append({**r, "Judul_Tugas": r.get("Judul_Tugas", r.get("Instruksi", "")), "Soal_JSON": r.get("Soal_JSON", "")})
        return converted


def get_answers_worksheet():
    try:
        ws = sheet.worksheet("DB_Jawaban_Siswa")
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title="DB_Jawaban_Siswa", rows="3000", cols="8")
        ws.append_row(ANSWER_HEADERS)
    headers = ws.row_values(1)
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


def simpan_lampiran_jawaban(task_id, student_id, uploaded_files):
    """Upload lampiran siswa ke Drive lalu simpan metadata dan URL-nya."""
    if not uploaded_files:
        return []
    total_bytes = sum(len(f.getvalue()) for f in uploaded_files)
    if total_bytes > 40 * 1024 * 1024:
        raise ValueError("Total lampiran satu pengiriman maksimal 40 MB.")
    ws = get_lampiran_jawaban_worksheet()
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    hasil = []
    for file_item in uploaded_files:
        file_bytes = file_item.getvalue()
        if len(file_bytes) > 10 * 1024 * 1024:
            raise ValueError(f"File {file_item.name} melebihi batas 10 MB.")
        mime = file_item.type or "application/octet-stream"
        url = upload_lampiran_ke_drive(file_bytes, file_item.name, mime)
        rows.append([
            "LMP-" + uuid.uuid4().hex[:10].upper(), task_id, student_id,
            file_item.name, mime, url, now, "Terkirim"
        ])
        hasil.append({"Nama_File": file_item.name, "URL_Drive": url, "Mime_Type": mime})
    if rows:
        ws.append_rows(rows, value_input_option="RAW")
    return hasil


def baca_lampiran_jawaban(task_id, student_id):
    try:
        ws = get_lampiran_jawaban_worksheet()
        return [r for r in baca_records_aman(ws)
                if str(r.get("ID_Tugas", "")).strip() == str(task_id).strip()
                and str(r.get("ID_Siswa", "")).strip() == str(student_id).strip()]
    except gspread.WorksheetNotFound:
        return []


PESAN_ORTU_HEADERS = [
    "ID_Pesan", "ID_Ortu", "ID_Siswa", "Nama_Siswa", "Pesan",
    "URL_Lampiran", "Nama_File", "Mime_Type", "Waktu_Kirim",
    "Status_Pesan", "Balasan_Tutor", "Nama_Tutor", "Waktu_Balasan"
]


def get_pesan_ortu_worksheet():
    ws = get_or_create_worksheet("Pesan_Orangtua_Tutor", PESAN_ORTU_HEADERS, rows="3000", cols="13")
    if not header_cocok(ws.row_values(1), PESAN_ORTU_HEADERS):
        raise ValueError("Header Pesan_Orangtua_Tutor tidak sesuai. Data tidak ditulis.")
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


def baca_jawaban_tergabung(ws):
    """Gabungkan baris per-soal menjadi format internal yang dipakai tampilan siswa/tutor."""
    rows = baca_records_aman(ws)
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
        siswa_rows = baca_records_aman(sheet.worksheet("Data_Siswa"))
        names = {str(x.get("ID_Siswa", "")).strip(): x.get("Nama_Lengkap", "") for x in siswa_rows}
    except Exception:
        names = {}
    for item in grouped.values():
        item["Nama_Siswa"] = names.get(item["ID_Siswa"], item["ID_Siswa"])
        item["Jawaban_JSON"] = json.dumps(item["Jawaban"], ensure_ascii=False)
        result.append(item)
    return result


def simpan_jawaban_per_soal(task_id, student_id, answers, submitted=False):
    """Simpan jawaban per soal secara batch. Draft TIDAK menimpa jawaban yang sudah dikirim/dinilai."""
    ws = get_answers_worksheet()
    rows = baca_records_aman(ws)
    now = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
    status = "Dikirim - Menunggu Penilaian" if submitted else "Draft"
    existing = {}
    sudah_terkunci = False
    for row in rows:
        if str(row.get("ID_Penugasan", "")) == str(task_id) and str(row.get("ID_Siswa", "")) == str(student_id):
            existing[str(row.get("Nomor_Soal", ""))] = row["_baris"]
            st_low = str(row.get("Status_Jawaban", "")).lower()
            if "dikirim" in st_low or "menunggu" in st_low or "dinilai" in st_low:
                sudah_terkunci = True
    if sudah_terkunci:
        return False

    updates, new_rows = [], []
    for nomor, jawaban in answers.items():
        nomor = str(nomor)
        if jawaban is None:
            jawaban = ""
        teks = json.dumps(jawaban, ensure_ascii=False) if isinstance(jawaban, (list, dict)) else str(jawaban)
        values = [teks, status, now, now if submitted else ""]
        if nomor in existing:
            r = existing[nomor]
            updates.append({"range": f"E{r}:H{r}", "values": [values]})
        else:
            new_rows.append(["JWB-" + uuid.uuid4().hex[:10].upper(), task_id, student_id, nomor] + values)
    if updates:
        ws.batch_update(updates, value_input_option="RAW")
    if new_rows:
        ws.append_rows(new_rows, value_input_option="RAW")
    return True


def simpan_pengiriman_jawaban(task_id, student_id, answers):
    return simpan_jawaban_per_soal(task_id, student_id, answers, submitted=True)


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
        return re.sub(r"\\s+", " ", v.strip()).casefold()
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


def hitung_nilai_objektif(daftar_soal, jawaban):
    """Hitung nilai soal objektif. Soal uraian sengaja tidak dinilai otomatis."""
    total_objektif = 0
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

        total_objektif += 1
        if "pilihan ganda kompleks" in bentuk:
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
        rincian.append({"nomor": nomor, "poin": poin})

    skor = (sum(x["poin"] for x in rincian) / total_objektif * 100) if total_objektif else None
    return {
        "skor_objektif": round(skor, 2) if skor is not None else None,
        "jumlah_objektif": total_objektif,
        "jumlah_benar_penuh": benar,
        "soal_manual": manual,
        "rincian": rincian,
    }


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


def adalah_pr(t):
    return str(t.get("Jenis_Tugas", "")).strip().lower().startswith("pr")


def adalah_materi(t):
    return str(t.get("Jenis_Tugas", "")).strip().lower().startswith("materi")


def parse_tanggal(teks):
    try:
        return datetime.strptime(str(teks).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def label_status(t, status_by_task, nilai_ids):
    """Kembalikan (kode, label). kode: dinilai / dikirim / draft / belum / materi."""
    tid = str(t.get("ID_Tugas", "")).strip()
    s = str(status_by_task.get(tid, "")).lower()
    if tid in nilai_ids or "dinilai" in s:
        return "dinilai", "✅ Sudah dinilai"
    if "dikirim" in s or "menunggu" in s:
        return "dikirim", "📤 Dikirim"
    if adalah_materi(t):
        return "materi", "📖 Materi"
    tgl = parse_tanggal(t.get("Tenggat"))
    terlambat = tgl is not None and tgl < waktu_lokal().date()
    if s == "draft":
        return "draft", ("⚠️ Terlambat (draft)" if terlambat else "✏️ Draft")
    return "belum", ("⚠️ Terlambat" if terlambat else "🆕 Belum dikerjakan")


def tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids):
    """Satu kartu tugas/PR untuk siswa. Setiap tugas menyimpan jawabannya sendiri
    (tidak saling menimpa), dan terkunci setelah dikirim."""
    task_id = str(t.get("ID_Tugas", "")).strip()
    siswa_id = st.session_state.get("siswa_id", "")
    kode, label = label_status(t, status_by_task, nilai_ids)
    terkunci = kode in ("dikirim", "dinilai")
    ikon = "📌" if adalah_pr(t) else ("📖" if adalah_materi(t) else "📝")
    judul = t.get("Judul_Tugas") or t.get("Instruksi") or "Tugas"
    tenggat = str(t.get("Tenggat", "")).strip()
    tambahan = f" · tenggat {tenggat}" if tenggat and not adalah_materi(t) else ""

    with st.expander(f"{ikon} {t.get('Mapel', 'Mapel')} · {judul} · {label}{tambahan}", expanded=False):
        timer_txt = str(t.get("Timer_Menit", "")).strip()
        st.write(f"**Instruksi Tutor:** {t.get('Instruksi') or '-'}")
        st.write(f"**Diberikan:** {t.get('Tanggal') or '-'}")
        if tenggat and not adalah_materi(t):
            st.write(f"**Tenggat:** {tenggat}")
        if not adalah_materi(t):
            st.write(f"**Durasi:** {'Tanpa timer' if timer_txt in ('', '0') else timer_txt + ' menit'}")

        if t.get("File_Offline"):
            st.markdown("### 📖 Materi dari Tutor")
            tampilkan_materi(t.get("File_Offline"))

        soal_json = str(t.get("Soal_JSON", "") or "")
        try:
            daftar_soal = json.loads(soal_json) if soal_json else []
        except (ValueError, TypeError):
            daftar_soal = []

        if daftar_soal:
            st.markdown("#### 📝 Lembar Jawaban Online")
            file_jawaban = []
            if not terkunci:
                file_jawaban = st.file_uploader(
                    "Lampirkan foto, PDF, audio, atau video jawaban (opsional):",
                    type=["jpg", "jpeg", "png", "webp", "pdf", "mp4", "mov", "webm", "m4v",
                          "mp3", "wav", "m4a", "ogg", "aac"],
                    accept_multiple_files=True,
                    key=f"lampiran_online_{task_id}"
                )
                if file_jawaban:
                    st.caption("Maksimal 20 MB per file. Audio/video akan disimpan ke Google Drive saat jawaban dikirim.")
            else:
                lampiran_lama = baca_lampiran_jawaban(task_id, siswa_id)
                for lamp in lampiran_lama:
                    st.markdown(f"[📎 {lamp.get('Nama_File', 'Lampiran jawaban')}]({lamp.get('URL_Drive', '')})")
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

            for i, soal in enumerate(daftar_soal, 1):
                qkey = f"student_{task_id}_{i}"
                bentuk = str(soal.get("Bentuk_Soal", "")).lower()
                opsi = soal.get("Opsi_List", [])
                st.markdown(f"**{i}. {soal.get('Teks_Soal', '')}**")
                if soal.get("Url_Gambar"):
                    st.image(img_url(soal["Url_Gambar"]), use_container_width=True)
                tampilkan_media_soal(soal)

                # Simpan HANYA soal ini, ke tugas ini (bukan tugas terakhir yang ditampilkan)
                def _simpan_satu(nilai, question_no=i, tid=task_id):
                    try:
                        simpan_jawaban_per_soal(tid, st.session_state.get("siswa_id", ""), {str(question_no): nilai}, submitted=False)
                    except Exception as e:
                        st.session_state["_galat_simpan"] = str(e)

                def _update_answer(question_no=i, widget_key=qkey, tid=task_id):
                    _simpan_satu(st.session_state.get(widget_key, ""), question_no, tid)

                if "pilihan ganda kompleks" in bentuk:
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
                elif "pilihan ganda" in bentuk:
                    tersimpan = old_answer.get(str(i))
                    st.radio(f"Pilih jawaban nomor {i}:", opsi,
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

            if not terkunci:
                current_answers = {}
                for i in range(1, len(daftar_soal) + 1):
                    v = st.session_state.get(f"student_{task_id}_{i}", "")
                    current_answers[str(i)] = "" if v is None else v
                belum = [n for n, v in current_answers.items() if jawaban_kosong(v)]
                boleh_kirim = True
                if belum:
                    st.warning("Soal nomor " + ", ".join(belum) + " belum dijawab.")
                    boleh_kirim = st.checkbox("Saya yakin ingin mengirim walaupun masih ada soal yang kosong.",
                                              key=f"yakin_{task_id}")
                if st.button("📤 Kirim Jawaban", key=f"submit_{task_id}", disabled=not boleh_kirim):
                    try:
                        # Upload file lebih dulu; tabel jawaban online yang lama tidak diubah.
                        if file_jawaban:
                            simpan_lampiran_jawaban(task_id, siswa_id, file_jawaban)
                        ok = simpan_pengiriman_jawaban(task_id, siswa_id, current_answers)
                        st.success("Jawaban berhasil dikirim. Tutor akan memeriksanya." if ok
                                   else "Jawaban untuk tugas ini sudah dikirim sebelumnya.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Pengiriman jawaban/lampiran gagal: {e}")

        elif adalah_materi(t):
            st.info("Ini materi bacaan dari Tutor, tidak ada yang perlu dikirim.")
        else:
            # Tugas tanpa soal digital (offline / dikerjakan di buku): siswa menandai sudah selesai.
            if terkunci:
                st.info("Sudah ditandai selesai. Tutor akan memeriksa hasilnya." if kode == "dikirim"
                        else "Sudah dinilai oleh Tutor.")
            else:
                st.info("Kerjakan melalui materi/lampiran dari Tutor. Unggah foto, PDF, audio, atau video hasil pekerjaan, lalu kirim kepada Tutor.")
                catatan_siswa = st.text_area("Catatan untuk Tutor (opsional):", key=f"cat_{task_id}")
                file_jawaban_offline = st.file_uploader(
                    "Unggah foto, PDF, audio, atau video hasil pekerjaan:",
                    type=["jpg", "jpeg", "png", "webp", "pdf", "mp4", "mov", "webm", "m4v",
                          "mp3", "wav", "m4a", "ogg", "aac"],
                    accept_multiple_files=True,
                    key=f"lampiran_offline_{task_id}"
                )
                if file_jawaban_offline:
                    st.caption("Maksimal 20 MB per file. Pastikan video/audio dapat diputar dan suaranya jelas.")
                if st.button("📤 Kirim Hasil Pekerjaan", key=f"selesai_{task_id}"):
                    try:
                        teks = "Sudah dikerjakan (offline)"
                        if catatan_siswa.strip():
                            teks += " — " + catatan_siswa.strip()
                        if not file_jawaban_offline and not catatan_siswa.strip():
                            st.error("Unggah minimal satu foto/PDF atau isi catatan untuk Tutor.")
                        else:
                            if file_jawaban_offline:
                                simpan_lampiran_jawaban(task_id, siswa_id, file_jawaban_offline)
                            ok = simpan_pengiriman_jawaban(task_id, siswa_id, {"0": teks})
                            st.success("Hasil pekerjaan berhasil dikirim. Tutor akan memeriksanya." if ok
                                       else "Tugas ini sudah dikirim sebelumnya.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Pengiriman hasil pekerjaan gagal: {e}")


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
            if not id_siswa_login or not pin_siswa:
                st.error("ID dan PIN wajib diisi.")
            else:
                try:
                    ws_akun_login = sheet.worksheet("Akun_Pengguna")
                    akun_rows_login = pastikan_pemetaan_id_siswa(
                        ws_akun_login, sheet.worksheet("Data_Siswa")
                    )
                    akun_siswa = next((
                        r for r in akun_rows_login
                        if str(r.get("ID_SISWA", "")).strip().upper() == id_siswa_login
                        and str(r.get("Level_Akses", "")).strip().casefold() == "siswa"
                        and verifikasi_pin(pin_siswa, r.get("PIN_Password", ""))[0]
                    ), None)

                    data_siswa_login = baca_records_aman(sheet.worksheet("Data_Siswa"))
                    siswa_match = next((
                        r for r in data_siswa_login
                        if str(r.get("ID_SISWA", r.get("ID_Siswa", ""))).strip().upper() == id_siswa_login
                    ), None)

                    if not akun_siswa or not siswa_match:
                        st.error("ID atau PIN tidak sesuai.")
                    elif not _status_aktif(siswa_match.get("Status", "Aktif")):
                        st.error("🚫 Akun Siswa Anda sudah Nonaktif. Silakan hubungi pengelola.")
                    else:
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
        nama_aktif = st.session_state.siswa_nama
        jenjang_aktif = st.session_state.siswa_jenjang
        col_welcome, col_logout = st.columns([4, 1])
        with col_welcome:
            st.success(f"Halo, Ananda **{nama_aktif}** ({jenjang_aktif})! Semangat Belajar! 🌟")
        with col_logout:
            if st.button("🚪 Logout"):
                st.session_state.siswa_logged_in = False
                st.session_state.siswa_nama = ""
                st.session_state.siswa_id = ""
                st.session_state.siswa_jenjang = ""
                st.session_state.pop("siswa_baris", None)
                st.session_state.pop("siswa_akun_baris", None)
                st.session_state.pop("siswa_user_id", None)
                st.rerun()

        if st.session_state.get("siswa_akun_baris"):
            akun_siswa_aktif = next((
                r for r in baca_records_aman(sheet.worksheet("Akun_Pengguna"))
                if int(r.get("_baris", 0)) == int(st.session_state.siswa_akun_baris)
                and str(r.get("Level_Akses", "")).strip().casefold() == "siswa"
            ), None)
            if akun_siswa_aktif:
                form_ganti_pin(
                    sheet.worksheet("Akun_Pengguna"),
                    akun_siswa_aktif,
                    "PIN_Password",
                    "siswa",
                    identity_field="ID_User",
                    identity_value=st.session_state.get("siswa_user_id", "")
                )

        try:
            tugas_anak = [
                t for t in get_student_tasks()
                if str(t.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
                and "batal" not in str(t.get("Status_Tugas", "")).lower()
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
            nilai_records = baca_records_aman(sheet.worksheet("DB_Nilai_Tugas"))
        except Exception:
            nilai_records = []
        nilai_ids = {str(n.get("ID_Tugas", "")).strip() for n in nilai_records}

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

        menu_siswa = st.sidebar.radio(
            "MENU SISWA",
            ["🏠 Beranda", "📚 Materi & Tugas", "📌 PR", "📝 Hasil Penilaian", "📈 Riwayat Belajar"],
            label_visibility="visible",
            key="menu_navigasi_siswa"
        )
        st.sidebar.markdown("---")
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
            st.info("Pilih menu di sebelah kiri untuk membuka materi, mengerjakan tugas, melihat nilai, atau memeriksa riwayat belajar.")

        elif menu_siswa == "📚 Materi & Tugas":
            st.markdown(f"### 🎒 Tugas Belajar Ananda {nama_aktif}")
            if st.session_state.get("_galat_simpan"):
                st.warning("Jawaban terakhir belum tersimpan otomatis: " + str(st.session_state.pop("_galat_simpan")))
            if not tugas_reguler:
                st.info("Belum ada tugas atau materi dari Tutor.")
            else:
                for t in tugas_reguler:
                    tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids)

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
                        tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids)
                else:
                    st.success("Semua PR sudah dikerjakan. Hebat! 🎉")
                if selesai:
                    st.markdown(f"#### PR yang sudah dikirim / dinilai ({len(selesai)})")
                    for t in selesai:
                        tampilkan_kartu_tugas(t, jawaban_siswa, status_by_task, nilai_ids)

        elif menu_siswa == "📝 Hasil Penilaian":
            st.markdown("### 📝 Hasil Penilaian Tutor")
            info_tugas = {str(t.get("ID_Tugas", "")).strip(): t for t in tugas_anak}
            hasil_nilai = [n for n in nilai_records if str(n.get("ID_Tugas", "")).strip() in info_tugas]
            if hasil_nilai:
                for n in reversed(hasil_nilai):
                    tg = info_tugas.get(str(n.get("ID_Tugas", "")).strip(), {})
                    st.markdown(f"**{tg.get('Mapel', 'Tugas')} — {tg.get('Judul_Tugas') or n.get('ID_Tugas', '')}**")
                    st.metric("Nilai", n.get("Nilai", "-"))
                    st.write(f"Catatan Tutor: {n.get('Catatan', '-')}")
                    st.caption(f"Diperiksa oleh {n.get('Tutor', '-')} · {n.get('Waktu_Penilaian', '-')}")
                    st.divider()
            else:
                st.info("Belum ada hasil penilaian dari Tutor.")

        elif menu_siswa == "📈 Riwayat Belajar":
            st.markdown("### 📈 Riwayat Belajar")
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
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
            data = baca_records_aman(sheet.worksheet("Akun_Pengguna"))
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
                        upgrade_pin_lama(sheet.worksheet("Akun_Pengguna"), row, "PIN_Password", pin)
                    status_tutor = str(row.get("Status", "Aktif")).strip().lower()
                    if status_tutor == "nonaktif":
                        is_active = False
                    elif adalah_akun_ortu(row):
                        # Akun wali murid tidak boleh masuk portal tutor.
                        salah_menu = True
                    else:
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
        st.success(f"👨‍🏫 Tutor Aktif: **{st.session_state.tutor_nama}**")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.session_state.tutor_id = ""
            st.session_state.tutor_user_id = ""
            st.session_state.pop("tutor_baris", None)
            st.rerun()

        if st.session_state.get("tutor_baris"):
            akun_tutor_aktif = next((r for r in baca_records_aman(sheet.worksheet("Akun_Pengguna")) if int(r.get("_baris", 0)) == int(st.session_state.tutor_baris)), None)
            if akun_tutor_aktif:
                form_ganti_pin(sheet.worksheet("Akun_Pengguna"), akun_tutor_aktif, "PIN_Password", "tutor")

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
        menu_tutor = st.sidebar.radio(
            "Navigasi",
            [
                "🏠 Beranda",
                "📝 Persiapan Sesi & Bank Soal",
                "📋 Pantau Tugas & PR",
                "📊 Portofolio Siswa",
                "📚 Materi Tambahan",
                "🕒 Kehadiran Siswa",
                "📨 Pesan Orang Tua"
            ],
            label_visibility="collapsed",
            key="menu_navigasi_tutor"
        )
        st.sidebar.markdown("---")
        st.sidebar.caption(f"Login sebagai: {st.session_state.tutor_nama}")
        if st.sidebar.button("🚪 Keluar dari Portal", key="sidebar_logout_tutor", use_container_width=True):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.session_state.tutor_id = ""
            st.session_state.tutor_user_id = ""
            st.rerun()

        # -------------------------------------------------
        # BERANDA TUTOR - dashboard ringkas tanpa statistik rahasia
        # -------------------------------------------------
        if menu_tutor == "🏠 Beranda":
                st.markdown(
                    f"""
                    <div class="portal-hero">
                        <h2>Selamat Datang, {st.session_state.tutor_nama} 👋</h2>
                        <p>Portal Pengajar Bimbel Rumah Nazma</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("#### Akses cepat")
                quick_cols = st.columns(4)
                quick_cards = [
                    ("📝", "Persiapan Sesi", "Siapkan materi dan tugas untuk siswa."),
                    ("📚", "Bank Soal", "Pilih soal untuk tugas yang akan dikirim."),
                    ("📂", "Materi / Flipbook", "Kelola dan bagikan bahan pembelajaran."),
                    ("🕒", "Kehadiran", "Catat kedatangan dan selesainya sesi belajar."),
                ]
                for col, (icon, title, desc) in zip(quick_cols, quick_cards):
                    with col:
                        st.markdown(
                            f'<div class="portal-card"><div class="card-icon">{icon}</div>'
                            f'<h4>{title}</h4><p>{desc}</p></div>',
                            unsafe_allow_html=True
                        )

                st.markdown("#### Ruang kerja pengajar")
                st.caption(
                    "Pilih menu di atas untuk melanjutkan pekerjaan. "
                    "Beranda ini sengaja tidak menampilkan jumlah siswa, daftar siswa binaan, "
                    "atau ringkasan data internal bimbel."
                )
                action_cols = st.columns(2)
                with action_cols[0]:
                    st.info("**Tugas & evaluasi**\n\nBuat tugas berdasarkan kebutuhan belajar siswa melalui menu Persiapan Sesi & Bank Soal.")
                with action_cols[1]:
                    st.info("**Administrasi sesi**\n\nCatat kehadiran dan waktu selesai belajar melalui menu Kehadiran Siswa.")

            # -------------------------------------------------
            # TAB 1: KONFIGURASI TUGAS DAN EVALUASI SESI (VERSI 2)
            # -------------------------------------------------
        elif menu_tutor == "📝 Persiapan Sesi & Bank Soal":
                st.header("📖 Persiapan Sesi Pembelajaran")
                siswa_aktif = get_siswa_aktif()

                search_query = st.text_input("🔍 Cari nama siswa yang sedang diajar:", key="tutor_cari_siswa").strip().lower()
                hasil_pencarian = [x for x in siswa_aktif if search_query in x.lower()] if search_query else []
                selected_siswa = None
                if search_query:
                    if hasil_pencarian:
                        pilihan = st.selectbox("Pilih siswa:", hasil_pencarian, key="tutor_pilih_siswa")
                        selected_siswa = pilihan
                    else:
                        st.warning("Siswa aktif tidak ditemukan.")
                else:
                    st.info("Ketik nama siswa untuk menyiapkan materi dan tugas.")

                if selected_siswa:
                    st.markdown("---")
                    st.subheader(f"📚 Rencana tugas untuk: {selected_siswa}")
                    st.caption("Setiap tugas disimpan sebagai catatan tersendiri sehingga satu siswa dapat menerima beberapa tugas dari beberapa mata pelajaran.")

                    # Draft tugas disimpan di session state sampai tutor menekan tombol simpan.
                    draft_key = f"draft_tugas_{selected_siswa}"
                    if draft_key not in st.session_state:
                        st.session_state[draft_key] = []

                    with st.expander("➕ Buat tugas baru", expanded=True):
                        # Widget biasa (bukan st.form) supaya pilihan sumber/kategori langsung mengubah isian di bawahnya.
                        n_form = st.session_state.get("form_n", 0)
                        k = f"{selected_siswa}_{n_form}"

                        kategori_label = st.radio("Kategori penugasan:", [KATEGORI_SESI, KATEGORI_PR], key=f"kt_{k}")
                        untuk_pr = kategori_label == KATEGORI_PR
                        mapel_tugas = st.selectbox("Mata pelajaran:", MAPEL_OPTIONS, key=f"mp_{k}")
                        judul_tugas = st.text_input("Judul / topik tugas:", key=f"jd_{k}")
                        jenis_tugas = st.radio("Jenis pengerjaan:", ["Online", "Offline"], horizontal=True, key=f"jn_{k}")
                        sumber_tugas = st.radio("Sumber materi / soal:", [SUMBER_BANK, SUMBER_DRIVE, SUMBER_UPLOAD], key=f"sm_{k}")
                        instruksi_tugas = st.text_area("Instruksi untuk siswa:", key=f"in_{k}")
                        timer_tugas = st.selectbox(
                            "Durasi pengerjaan:", [0, 15, 30, 45, 60, 90, 120], index=0 if untuk_pr else 2,
                            format_func=lambda x: "Tanpa timer" if x == 0 else f"{x} menit", key=f"tm_{k}_{'pr' if untuk_pr else 'sesi'}"
                        )
                        tenggat_tugas = st.date_input(
                            "Tenggat PR:" if untuk_pr else "Tanggal tenggat:",
                            value=waktu_lokal().date() + (timedelta(days=3) if untuk_pr else timedelta(days=0)),
                            key=f"tg_{k}_{'pr' if untuk_pr else 'sesi'}"
                        )

                        link_tugas = ""
                        file_tugas = []
                        soal_dipilih = []

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
                                for q in bank_filter:
                                    kode = str(q.get("Kode_Soal", "")).strip() or f"BARIS-{q.get('_baris')}"
                                    peta_soal[kode] = q
                                kode_dipilih = st.multiselect(
                                    f"Pilih soal untuk tugas ini ({len(peta_soal)} soal tersedia):",
                                    options=list(peta_soal.keys()),
                                    format_func=lambda c: f"{c} | {str(peta_soal[c].get('Teks_Soal', ''))[:100]}",
                                    key=kunci_pilih
                                )
                                for kode in kode_dipilih:
                                    try:
                                        soal_dipilih.append(ubah_soal_untuk_tugas(peta_soal[kode]))
                                    except Exception as e:
                                        st.warning(f"Soal {kode} dilewati: {e}")

                        elif sumber_tugas == SUMBER_DRIVE:
                            link_tugas = st.text_area("Link Google Drive / Flipbook (satu link per baris):",
                                                      placeholder="https://...", key=f"lk_{k}")
                        else:
                            file_tugas = st.file_uploader(
                                "Pilih materi/soal dari perangkat (PDF, dokumen, gambar, audio, video):",
                                type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg", "webp",
                                      "mp4", "mov", "webm", "m4v", "mp3", "wav", "m4a", "ogg", "aac"],
                                accept_multiple_files=True, key=f"up_{k}"
                            )

                        tambah_draft = st.button("Tambahkan ke daftar tugas", key=f"tambah_{k}")

                        if tambah_draft:
                            link_list = [x.strip() for x in link_tugas.splitlines() if x.strip()]
                            daftar_file = list(file_tugas or [])
                            total_byte = sum(len(f.getvalue()) for f in daftar_file)

                            if not judul_tugas.strip():
                                st.error("Judul / topik tugas wajib diisi.")
                            elif untuk_pr and tenggat_tugas < waktu_lokal().date():
                                st.error("Tenggat PR tidak boleh sebelum hari ini.")
                            elif sumber_tugas == SUMBER_BANK and not soal_dipilih:
                                st.error("Pilih minimal satu soal dari Bank Soal.")
                            elif sumber_tugas == SUMBER_DRIVE and not link_list:
                                st.error("Masukkan minimal satu link Drive / Flipbook.")
                            elif sumber_tugas == SUMBER_DRIVE and any(not l.lower().startswith(("http://", "https://")) for l in link_list):
                                st.error("Setiap link harus diawali https://")
                            elif sumber_tugas == SUMBER_UPLOAD and not daftar_file:
                                st.error("Pilih minimal satu file yang akan dilampirkan.")
                            elif any(len(f.getvalue()) > 20 * 1024 * 1024 for f in daftar_file):
                                st.error("Ukuran tiap lampiran maksimal 20 MB. Kompres video/audio lalu unggah kembali.")
                            elif total_byte > 40 * 1024 * 1024:
                                st.error("Total lampiran satu tugas maksimal 40 MB. Bagi menjadi beberapa tugas.")
                            else:
                                files = [{"name": f.name, "bytes": f.getvalue(), "mime": f.type or "application/octet-stream"}
                                         for f in daftar_file]
                                st.session_state[draft_key].append({
                                    "Mapel": mapel_tugas, "Judul": judul_tugas.strip(),
                                    # Kategori PR disimpan di Jenis_Tugas: "PR Online" / "PR Offline"
                                    "Jenis": f"PR {jenis_tugas}" if untuk_pr else jenis_tugas,
                                    "Sumber": sumber_tugas, "Instruksi": instruksi_tugas.strip(), "Timer": timer_tugas,
                                    "Tenggat": tenggat_tugas.strftime("%Y-%m-%d"),
                                    "Links": link_list, "Files": files, "Soal": soal_dipilih
                                })
                                st.session_state["form_n"] = n_form + 1  # kosongkan isian, siap menambah tugas berikutnya
                                st.success("Masuk ke daftar draft. Anda bisa menambah tugas atau PR lain (mapel lain / jenis lain), lalu tekan Simpan & Kirim.")
                                st.rerun()

                    daftar_draft = st.session_state[draft_key]
                    st.markdown("### 📋 Daftar tugas yang akan dikirim")
                    if daftar_draft:
                        for i, item in enumerate(daftar_draft, 1):
                            ikon = "📌" if str(item["Jenis"]).startswith("PR") else "📝"
                            with st.expander(f"{i}. {ikon} {item['Mapel']} — {item['Judul']} ({item['Jenis']})"):
                                st.write(f"Sumber: {item['Sumber']}")
                                st.write(f"Timer: {'Tanpa timer' if item['Timer'] == 0 else str(item['Timer']) + ' menit'} | Tenggat: {item['Tenggat']}")
                                st.write(f"Jumlah soal: {len(item['Soal'])}")
                                for link in item.get("Links", []):
                                    st.write(f"Link: {link}")
                                for file_item in item.get("Files", []):
                                    st.info(f"Lampiran siap diunggah ke Google Drive saat tugas dikirim: {file_item['name']}")
                                if st.button("🗑️ Hapus dari daftar", key=f"hapus_item_{selected_siswa}_{i}"):
                                    daftar_draft.pop(i - 1)
                                    st.rerun()
                        col_kirim, col_hapus = st.columns(2)
                        with col_kirim:
                            if st.button(f"📤 Simpan & Kirim Semua ({len(daftar_draft)})", type="primary", key=f"kirim_semua_{selected_siswa}"):
                                try:
                                    ws_tugas = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS)
                                    if not header_cocok(ws_tugas.row_values(1), TASK_HEADERS):
                                        st.error("Header Tugas_Sesi_Siswa_v2 berbeda dari struktur yang diperlukan. Data tidak ditulis agar tidak bergeser.")
                                    else:
                                        # Unggah seluruh lampiran dulu; baris tugas ditulis setelah semua unggahan berhasil.
                                        hasil_kirim = []
                                        for item in daftar_draft:
                                            entri_lampiran = []
                                            for file_item in item.get("Files", []):
                                                url = upload_lampiran_ke_drive(file_item["bytes"], file_item["name"], file_item["mime"])
                                                entri_lampiran.append(f"{jenis_dari_mime(file_item['mime'], file_item['name'])}::{url}")
                                            for link in item.get("Links", []):
                                                entri_lampiran.append(f"link::{link}")
                                            hasil_kirim.append((item, "|".join(entri_lampiran)))

                                        now_txt = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
                                        baris_baru = []
                                        for item, file_info in hasil_kirim:
                                            baris_baru.append([
                                                "TGS-" + uuid.uuid4().hex[:10].upper(), now_txt, selected_siswa,
                                                item["Mapel"], item["Judul"], item["Jenis"], item["Sumber"], item["Instruksi"],
                                                file_info, item["Timer"], item["Tenggat"], json.dumps(item["Soal"], ensure_ascii=False),
                                                "Diberikan", st.session_state.tutor_nama
                                            ])
                                        ws_tugas.append_rows(baris_baru, value_input_option="RAW")
                                        n_pr = sum(1 for it in daftar_draft if str(it["Jenis"]).startswith("PR"))
                                        st.session_state[draft_key] = []
                                        st.success(f"{len(hasil_kirim)} penugasan terkirim untuk {selected_siswa} ({n_pr} PR, {len(hasil_kirim) - n_pr} tugas sesi).")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menyimpan tugas: {e}")
                        with col_hapus:
                            if st.button("Kosongkan daftar draft", key=f"hapus_draft_{selected_siswa}"):
                                st.session_state[draft_key] = []
                                st.rerun()
                    else:
                        st.info("Belum ada tugas di daftar draft.")

                    st.markdown("---")
                    st.subheader("📝 Jurnal dan Evaluasi Sesi")
                    # Tanggal & pilihan mapel di LUAR form agar kolom evaluasi per mapel langsung muncul.
                    tanggal_sesi = st.date_input("Tanggal sesi:", waktu_lokal().date(), key=f"tgl_sesi_{selected_siswa}")
                    mapel_diajarkan = st.multiselect("Mata pelajaran yang diajarkan:", MAPEL_OPTIONS, key=f"mapel_ajar_{selected_siswa}")
                    with st.form(f"form_jurnal_v2_{selected_siswa}"):
                        st.markdown("#### Evaluasi per mata pelajaran")
                        evaluasi_mapel = {}
                        for idx, mp in enumerate(mapel_diajarkan):
                            st.markdown(f"**{mp}**")
                            materi_mp = st.text_input(f"Materi {mp}", key=f"materi_mp_{selected_siswa}_{idx}")
                            target_mp = st.text_input(f"Target belajar {mp}", key=f"target_mp_{selected_siswa}_{idx}")
                            capaian_mp = st.text_area(f"Kompetensi yang dikuasai / hasil belajar {mp}", key=f"capaian_mp_{selected_siswa}_{idx}")
                            penguatan_mp = st.text_area(f"Bagian yang perlu penguatan {mp}", key=f"penguatan_mp_{selected_siswa}_{idx}")
                            nilai_mp = st.text_input(f"Nilai latihan (opsional) {mp}", key=f"nilai_mp_{selected_siswa}_{idx}")
                            evaluasi_mapel[mp] = {"Materi": materi_mp, "Target": target_mp, "Capaian": capaian_mp, "Penguatan": penguatan_mp, "Nilai": nilai_mp}
                        st.markdown("#### Catatan umum sesi")
                        kondisi_siswa = st.selectbox("Kondisi siswa:", ["Baik", "Cukup", "Kurang fokus", "Lelah", "Perlu perhatian khusus"])
                        keaktifan = st.selectbox("Keaktifan siswa:", ["Sangat aktif", "Aktif", "Cukup aktif", "Pasif"])
                        kendala_umum = st.text_area("Kendala selama sesi:")
                        rekomendasi = st.text_area("Rekomendasi / tindak lanjut:")
                        handover = st.text_area("Catatan untuk tutor berikutnya (handover):")
                        dokumentasi = st.text_input("Link dokumentasi (opsional):")
                        simpan_jurnal = st.form_submit_button("💾 Simpan Jurnal dan Evaluasi")

                    if simpan_jurnal:
                        try:
                            ws_sesi = get_or_create_worksheet("Jurnal_Sesi_Tutor_v2", ["ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Kondisi_Siswa", "Keaktifan", "Kendala_Umum", "Rekomendasi", "Handover", "Dokumentasi"])
                            id_sesi = "SES-" + uuid.uuid4().hex[:10].upper()
                            ws_sesi.append_row([id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, kondisi_siswa, keaktifan, kendala_umum, rekomendasi, handover, dokumentasi])
                            ws_eval = get_or_create_worksheet("Evaluasi_Mapel_Tutor_v2", ["ID_Evaluasi", "ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Mapel", "Materi", "Target", "Capaian", "Penguatan", "Nilai"])
                            for mp, ev in evaluasi_mapel.items():
                                ws_eval.append_row(["EVL-" + uuid.uuid4().hex[:10].upper(), id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, mp, ev["Materi"], ev["Target"], ev["Capaian"], ev["Penguatan"], ev["Nilai"]])
                            st.success("Jurnal sesi dan evaluasi per mapel berhasil disimpan.")
                        except Exception as e:
                            st.error(f"Gagal menyimpan jurnal/evaluasi: {e}")

            # -------------------------------------------------
            # TAB 2: PORTOFOLIO DAN PENILAIAN JAWABAN
            # -------------------------------------------------
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
                hasil_pantau = [
                    nama for nama in pilihan_pantau
                    if cari_pantau and cari_pantau in str(nama).lower()
                ]
                if cari_pantau and hasil_pantau:
                    nama_pantau = st.selectbox(
                        "Pilih siswa yang cocok:",
                        hasil_pantau,
                        key="pantau_siswa_hasil"
                    )
                    try:
                        sid_pantau = get_siswa_id_by_nama(nama_pantau)
                        semua_tugas = [t for t in get_student_tasks()
                                       if str(t.get("Nama_Siswa", "")).strip().lower() == nama_pantau.strip().lower()]
                        try:
                            jwb_pantau = [x for x in baca_jawaban_tergabung(get_answers_worksheet())
                                          if str(x.get("ID_Siswa", "")).strip() == sid_pantau]
                        except Exception:
                            jwb_pantau = []
                        status_pantau = {str(x.get("ID_Tugas", "")): str(x.get("Status", "")) for x in jwb_pantau}
                        try:
                            nilai_pantau = {str(n.get("ID_Tugas", "")).strip()
                                            for n in baca_records_aman(sheet.worksheet("DB_Nilai_Tugas"))}
                        except Exception:
                            nilai_pantau = set()

                        saring = st.radio("Tampilkan:", ["Semua", "PR", "Tugas sesi", "Materi"], horizontal=True, key="pantau_saring")
                        baris = []
                        for t in reversed(semua_tugas):
                            if saring == "PR" and not adalah_pr(t):
                                continue
                            if saring == "Tugas sesi" and (adalah_pr(t) or adalah_materi(t)):
                                continue
                            if saring == "Materi" and not adalah_materi(t):
                                continue
                            if "batal" in str(t.get("Status_Tugas", "")).lower():
                                label = "🚫 Dibatalkan"
                            else:
                                label = label_status(t, status_pantau, nilai_pantau)[1]
                            baris.append({
                                "Kategori": "PR" if adalah_pr(t) else ("Materi" if adalah_materi(t) else "Tugas sesi"),
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
                                      and label_status(t, status_pantau, nilai_pantau)[0] in ("belum", "draft", "materi")]
                        if bisa_batal:
                            with st.expander("🚫 Batalkan tugas yang salah kirim"):
                                peta_batal = {f"{t.get('Mapel')} | {t.get('Judul_Tugas')} | {t.get('Jenis_Tugas')} | {str(t.get('Tanggal', ''))[:10]}": t for t in bisa_batal}
                                pilih_batal = st.selectbox("Pilih tugas:", list(peta_batal.keys()), key="pantau_batal_pilih")
                                yakin_batal = st.checkbox("Saya yakin membatalkan tugas ini (siswa tidak akan melihatnya lagi).", key="pantau_batal_yakin")
                                if st.button("Batalkan tugas", disabled=not yakin_batal, key="pantau_batal_tombol"):
                                    ws_t = sheet.worksheet("Tugas_Sesi_Siswa_v2")
                                    kolom = ws_t.row_values(1)
                                    if "Status_Tugas" in kolom:
                                        ws_t.update_cell(peta_batal[pilih_batal]["_baris"], kolom.index("Status_Tugas") + 1, "Dibatalkan")
                                        st.success("Tugas dibatalkan.")
                                        st.rerun()
                                    else:
                                        st.error("Kolom Status_Tugas tidak ditemukan.")
                    except Exception as e:
                        st.error(f"Pantauan belum dapat ditampilkan: {e}")
                elif cari_pantau:
                    st.warning("Siswa aktif tidak ditemukan.")
                else:
                    st.info("Ketik nama siswa untuk melihat tugas dan PR.")

        elif menu_tutor == "📊 Portofolio Siswa":
                st.header("📊 Portofolio & Pemeriksaan Jawaban Siswa")

                try:
                    ws_jawaban = sheet.worksheet("DB_Jawaban_Siswa")
                    jawaban_records = baca_jawaban_tergabung(ws_jawaban)
                except gspread.WorksheetNotFound:
                    jawaban_records = []

                if jawaban_records:
                    st.subheader("Jawaban yang menunggu pemeriksaan")
                    menunggu = [
                        x for x in jawaban_records
                        if "Menunggu" in str(x.get("Status", ""))
                    ]
                    if menunggu:
                        try:
                            info_tgs = {str(t.get("ID_Tugas", "")).strip(): t for t in get_student_tasks()}
                        except Exception:
                            info_tgs = {}

                        def _label_jwb(x):
                            tg = info_tgs.get(str(x.get("ID_Tugas", "")).strip(), {})
                            kat = "PR" if adalah_pr(tg) else "Tugas"
                            return f"{x.get('Nama_Siswa')} | {kat} {tg.get('Mapel', '')} - {tg.get('Judul_Tugas', x.get('ID_Tugas'))} | {x.get('ID_Jawaban')}"
                        opsi_jwb = {_label_jwb(x): x for x in menunggu}
                        pilih_jwb = st.selectbox("Pilih jawaban siswa:", list(opsi_jwb.keys()))
                        item = opsi_jwb[pilih_jwb]
                        st.write(f"**Siswa:** {item.get('Nama_Siswa')}")
                        lampiran_item = baca_lampiran_jawaban(item.get("ID_Tugas", ""), item.get("ID_Siswa", ""))
                        if lampiran_item:
                            st.markdown("**📎 Lampiran jawaban siswa:**")
                            for lamp in lampiran_item:
                                st.markdown(f"[Buka {lamp.get('Nama_File', 'lampiran')}]({lamp.get('URL_Drive', '')})")
                        else:
                            st.caption("Tidak ada lampiran foto/PDF pada pengiriman ini.")
                        try:
                            jawaban_dict = json.loads(item.get("Jawaban_JSON", "{}"))
                        except (ValueError, TypeError):
                            jawaban_dict = {}
                        st.write("**Jawaban siswa:**")
                        st.json(jawaban_dict)
                        tugas_terpilih = info_tgs.get(str(item.get("ID_Tugas", "")).strip(), {})
                        try:
                            soal_untuk_nilai = json.loads(tugas_terpilih.get("Soal_JSON", "") or "[]")
                            if not isinstance(soal_untuk_nilai, list):
                                soal_untuk_nilai = []
                        except (ValueError, TypeError):
                            soal_untuk_nilai = []
                        hasil_otomatis = hitung_nilai_objektif(soal_untuk_nilai, jawaban_dict) if soal_untuk_nilai else {
                            "skor_objektif": None, "jumlah_objektif": 0,
                            "jumlah_benar_penuh": 0, "soal_manual": [], "rincian": []
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

                        nilai_awal = int(round(hasil_otomatis["skor_objektif"] or 0)) if semua_objektif else 0
                        with st.form("form_penilaian_jawaban"):
                            if semua_objektif:
                                st.caption("Semua soal dapat dinilai otomatis. Tutor tetap dapat mengubah nilai akhir.")
                            nilai = st.number_input("Nilai akhir (0–100):", min_value=0, max_value=100, value=nilai_awal)
                            catatan = st.text_area("Catatan tutor:")
                            simpan_nilai = st.form_submit_button("Simpan Penilaian")
                            if simpan_nilai:
                                ws_nilai = get_or_create_worksheet(
                                    "DB_Nilai_Tugas",
                                    [
                                        "ID_Nilai", "ID_Jawaban", "ID_Tugas",
                                        "Nama_Siswa", "Nilai", "Catatan",
                                        "Tutor", "Waktu_Penilaian"
                                    ]
                                )
                                ws_nilai.append_row([
                                    "NIL-" + uuid.uuid4().hex[:10].upper(),
                                    item.get("ID_Jawaban"),
                                    item.get("ID_Tugas"),
                                    item.get("Nama_Siswa"),
                                    nilai,
                                    catatan,
                                    st.session_state.tutor_nama,
                                    waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
                                ])
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
                                st.success("Penilaian tersimpan.")
                                st.rerun()

                    else:
                        st.info("Tidak ada jawaban yang menunggu pemeriksaan.")
                else:
                    st.info("Belum ada jawaban online dari siswa.")

                st.markdown("---")
                st.subheader("Rekap latihan lama")
                nama_portofolio = st.text_input("Cari nama siswa untuk melihat rekap:", key="nama_portofolio")
                if nama_portofolio:
                    try:
                        ws_r = sheet.worksheet("Riwayat_Latihan")
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

            # -------------------------------------------------
            # TAB 3: MATERI TAMBAHAN
            # -------------------------------------------------
        elif menu_tutor == "📚 Materi Tambahan":
                st.header("➕ Materi & Soal Tambahan")
                try:
                    siswa_pilihan_ekstra = get_siswa_aktif()
                except Exception as e:
                    siswa_pilihan_ekstra = []
                    st.error(f"Daftar siswa belum dapat dibaca: {e}")
                cari_ekstra = st.text_input(
                    "🔍 Cari nama siswa tujuan:",
                    key="cari_siswa_materi_ekstra",
                    placeholder="Ketik nama siswa..."
                ).strip().lower()
                hasil_ekstra = [
                    nama for nama in siswa_pilihan_ekstra
                    if cari_ekstra and cari_ekstra in str(nama).lower()
                ]
                nama_target_siswa = ""
                if cari_ekstra:
                    if hasil_ekstra:
                        nama_target_siswa = st.selectbox(
                            "Pilih siswa yang cocok:",
                            hasil_ekstra,
                            key="pilih_siswa_materi_ekstra"
                        )
                    else:
                        st.warning("Nama siswa tidak ditemukan.")
                else:
                    st.info("Ketik nama siswa untuk mencari penerima materi.")
                with st.form("form_materi_tambahan"):
                    mapel_ekstra = st.selectbox("Mata Pelajaran:", MAPEL_OPTIONS)
                    judul_materi = st.text_input("Judul Materi / Topik:")
                    link_materi_ekstra = st.text_area("Link Modul / Flipbook / Soal (satu link per baris, opsional):")
                    file_materi_ekstra = st.file_uploader(
                        "Atau unggah PDF, gambar, audio listening, atau video:",
                        type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg", "webp",
                              "mp4", "mov", "webm", "m4v", "mp3", "wav", "m4a", "ogg", "aac"],
                        accept_multiple_files=True,
                        key="upload_materi_ekstra"
                    )
                    if st.form_submit_button("🚀 Kirim Materi Ekstra"):
                        links_ekstra = [x.strip() for x in link_materi_ekstra.splitlines() if x.strip()]
                        files_ekstra = list(file_materi_ekstra or [])
                        if not nama_target_siswa:
                            st.error("Pilih siswa tujuan.")
                        elif not judul_materi.strip():
                            st.error("Judul materi wajib diisi.")
                        elif not links_ekstra and not files_ekstra:
                            st.error("Masukkan link atau unggah minimal satu file materi.")
                        elif any(not l.lower().startswith(("http://", "https://")) for l in links_ekstra):
                            st.error("Setiap link harus diawali https://")
                        elif any(len(f.getvalue()) > 20 * 1024 * 1024 for f in files_ekstra):
                            st.error("Ukuran tiap file maksimal 20 MB.")
                        else:
                            try:
                                entri_materi = []
                                for f in files_ekstra:
                                    url = upload_lampiran_ke_drive(f.getvalue(), f.name, f.type or "application/octet-stream")
                                    entri_materi.append(f"{jenis_dari_mime(f.type, f.name)}::{url}")
                                entri_materi.extend(f"link::{l}" for l in links_ekstra)
                                ws_tugas = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS)
                                if not header_cocok(ws_tugas.row_values(1), TASK_HEADERS):
                                    raise ValueError("Header Tugas_Sesi_Siswa_v2 tidak sesuai. Data tidak ditulis.")
                                ws_tugas.append_row([
                                    "TGS-" + uuid.uuid4().hex[:10].upper(),
                                    waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
                                    nama_target_siswa, mapel_ekstra, judul_materi.strip(),
                                    "Materi Tambahan", "Upload / Link Modul / Flipbook / Audio / Video",
                                    f"[Materi Ekstra] {judul_materi.strip()}",
                                    "|".join(entri_materi),
                                    0, "", "[]", "Diberikan", st.session_state.tutor_nama
                                ])
                                st.success("Materi tambahan berhasil dikirim.")
                            except Exception as e:
                                st.error(f"Gagal mengirim materi: {e}")

        elif menu_tutor == "🕒 Kehadiran Siswa":
                st.header("🕒 Kehadiran dan Waktu Belajar")
                tutor_id = st.session_state.get("tutor_id", "")
                if not tutor_id:
                    st.error("Pencatatan kehadiran belum bisa digunakan karena ID_Tutor akun ini belum terhubung dengan Data_Tutor.")
                else:
                    try:
                        allowed_ids = siswa_tutor_terhubung(tutor_id)
                        student_records = baca_records_aman(sheet.worksheet("Data_Siswa"))
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
                                    if active_rec:
                                        st.info(f"Sesi aktif sejak pukul **{active_rec.get('Waktu_Hadir', '-')}** pada {active_rec.get('Tanggal_Sesi', '-')}")
                                        if st.button("✅ Tandai Selesai Belajar", type="primary", key=f"finish_att_{sid}"):
                                            ok, msg = tandai_selesai_belajar(sid, tutor_id)
                                            (st.success if ok else st.error)(msg)
                                            st.rerun()
                                    else:
                                        catatan_hadir = st.text_input("Catatan kehadiran (opsional):", key=f"attendance_note_{sid}")
                                        if st.button("🟢 Catat Hadir / Mulai Belajar", type="primary", key=f"start_att_{sid}"):
                                            ok, msg = catat_kehadiran(sid, tutor_id, st.session_state.tutor_nama, catatan_hadir)
                                            (st.success if ok else st.error)(msg)
                                            st.rerun()
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


        elif menu_tutor == "📨 Pesan Orang Tua":
            st.header("📨 Pesan dari Orang Tua")
            try:
                allowed_ids = siswa_tutor_terhubung(st.session_state.get("tutor_id", ""))
                siswa_rows = baca_records_aman(sheet.worksheet("Data_Siswa"))
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
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "🎁 Undian Hadiah", "👥 Kelola Status Akun", "📚 Arsip Bank Soal",
            "🔑 Reset PIN", "🔐 Keamanan Owner", "➕ Tambah Siswa"
        ])

        with tab6:
            st.header("➕ Pendaftaran Siswa Baru")
            st.caption("Isi satu formulir saja. ID dibuat otomatis dan data disimpan ke Data_Siswa.")
            try:
                ws_daftar = sheet.worksheet("Data_Siswa")
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
                        "Jenjang *", ["TK", "SD", "SMP", "SMA"],
                        key="tambah_siswa_jenjang"
                    )
                    kelas_opsi = {
                        "TK": ["Kelompok A", "Kelompok B"],
                        "SD": [f"Kelas {i}" for i in range(1, 7)],
                        "SMP": [f"Kelas {i}" for i in range(7, 10)],
                        "SMA": [f"Kelas {i}" for i in range(10, 13)],
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

                                    hasil_append = ws_daftar.append_row(
                                        row_baru, value_input_option="USER_ENTERED"
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
                                        st.success(
                                            f"Terverifikasi tersimpan di Google Sheets: "
                                            f"{nama_input} — {id_submit}."
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

        with tab1:
            data_siswa_all = baca_records_aman(sheet.worksheet("Data_Siswa"))
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

        with tab2:
            ws_siswa = sheet.worksheet("Data_Siswa")
            records_siswa = baca_records_aman(ws_siswa)
            if records_siswa:
                kolom_tampil = [
                    c for c in ["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]
                    if c in records_siswa[0]
                ]
                st.dataframe(pd.DataFrame(records_siswa)[kolom_tampil], use_container_width=True)
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

        with tab3:
            try:
                ws_bank = sheet.worksheet("Bank_Soal_Master")
                st.dataframe(pd.DataFrame(baca_records_aman(ws_bank)).drop(columns=["_baris"], errors="ignore"), use_container_width=True)
            except Exception as e:
                st.error(f"Bank soal belum dapat dibuka: {e}")

        with tab4:
            st.caption("Owner dapat membuat PIN pengganti. PIN langsung disimpan dalam bentuk HASH; pengguna dapat menggantinya lagi setelah login.")
            jenis_akun = st.radio("Jenis akun", ["Siswa", "Tutor / Orang Tua"], horizontal=True, key="owner_jenis_reset")
            if jenis_akun == "Siswa":
                ws_reset = sheet.worksheet("Akun_Pengguna")
                ws_siswa_reset = sheet.worksheet("Data_Siswa")
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
                ws_reset = sheet.worksheet("Akun_Pengguna")
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
                            simpan_pin_baru(ws_reset, pilihan_reset[target_reset], field_pin_reset, pin_reset)
                            st.success("PIN akun berhasil direset dan disimpan sebagai HASH.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Reset PIN gagal: {exc}")
            else:
                st.info("Tidak ada akun yang dapat dipilih pada kategori ini.")

        with tab5:
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
                form_ganti_pin(ws_owner_security, owner_pin_record, "Nilai", "owner")
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
        relasi_rows = baca_records_aman(sheet.worksheet("Relasi_Orangtua_Siswa"))
        siswa_rows = baca_records_aman(sheet.worksheet("Data_Siswa"))

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
            try:
                akun_rows = baca_records_aman(sheet.worksheet("Akun_Pengguna"))
                akun = next((
                    r for r in akun_rows
                    if str(r.get("ID_User", "")).strip().upper() == id_wali_login
                    and verifikasi_pin(pin_ortu, r.get("PIN_Password", ""))[0]
                ), None)

                if akun:
                    cocok_pin, pin_lama_plain = verifikasi_pin(pin_ortu, akun.get("PIN_Password", ""))
                    if cocok_pin and pin_lama_plain:
                        upgrade_pin_lama(sheet.worksheet("Akun_Pengguna"), akun, "PIN_Password", pin_ortu)

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
                        ortu_rows = baca_records_aman(sheet.worksheet("Data_Orangtua"))
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

        if st.session_state.get("ortu_baris"):
            akun_ortu_aktif = next((r for r in baca_records_aman(sheet.worksheet("Akun_Pengguna")) if int(r.get("_baris", 0)) == int(st.session_state.ortu_baris)), None)
            if akun_ortu_aktif:
                form_ganti_pin(sheet.worksheet("Akun_Pengguna"), akun_ortu_aktif, "PIN_Password", "ortu")

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
             "💬 Pesan untuk Tutor"],
            label_visibility="visible",
            key="menu_navigasi_ortu"
        )
        st.sidebar.markdown("---")
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
                ws_riwayat = sheet.worksheet("Riwayat_Latihan")
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
                ws_jurnal = sheet.worksheet("Form Responses 1")
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
            data_tabel_ortu = []
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                for r in baca_records_aman(ws_r):
                    if _norm_text(r.get("Nama_Siswa", "")) == _norm_text(nama_anak_aktif):
                        data_tabel_ortu.append({
                            "Tanggal": str(r.get("Waktu_Selesai", ""))[:10],
                            "Mapel": r.get("Mapel"),
                            "Aktivitas": r.get("Topik_Kuis"),
                            "Skor": r.get("Skor"),
                            "Evaluasi": r.get("Detail_Salah")
                        })
            except Exception:
                pass

            if data_tabel_ortu:
                st.dataframe(pd.DataFrame(data_tabel_ortu), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada data rekap nilai.")

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
