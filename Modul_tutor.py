import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import pandas as pd
import random
import json
import uuid
import re
import requests
import base64
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

# Tiga jalur sumber materi / soal untuk tugas
SUMBER_BANK = "Bank Soal Bersama (Spreadsheet)"
SUMBER_DRIVE = "Link Google Drive / Flipbook"
SUMBER_UPLOAD = "Upload dari perangkat"

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
    .stApp { background-color: #f8f9fa; }
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def waktu_lokal():
    """Waktu WIB. Dipakai untuk SEMUA timestamp agar konsisten (server Streamlit memakai UTC)."""
    return datetime.now(ZoneInfo("Asia/Jakarta"))


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


try:
    client = init_connection()
    sheet = client.open_by_url(
        "https://docs.google.com/spreadsheets/d/17JI1x966HfVG4YpfzCz_bssBwOmUTIJFbRutl0qyIZE/edit"
    )
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
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
    """Ambil worksheet; buat jika belum ada. Header hanya dibuat untuk sheet baru/kosong."""
    try:
        ws = sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=rows, cols=cols)

    values = ws.get_all_values()
    if not values:
        ws.append_row(headers)
    return ws


def baca_records_aman(ws):
    """Baca sheet sebagai daftar dict.
    - Aman untuk header kosong/duplikat (tidak seperti get_all_records).
    - Semua nilai tetap berupa teks (PIN seperti 0123 tidak kehilangan angka 0).
    - Setiap baris diberi kunci '_baris' = nomor baris ASLI di sheet, supaya
      update/penandaan tidak meleset walaupun ada baris kosong di tengah data."""
    values = ws.get_all_values()
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
        rec["_baris"] = nomor_baris
        records.append(rec)
    return records


def header_cocok(actual, expected):
    """Bandingkan header sheet dengan struktur yang diharapkan.
    Kolom kosong di ujung kanan dan spasi berlebih diabaikan."""
    a = [str(x).strip() for x in actual]
    while a and a[-1] == "":
        a.pop()
    return a == list(expected)


def get_siswa_aktif():
    """Nama siswa aktif dari Data_Siswa."""
    rows = baca_records_aman(sheet.worksheet("Data_Siswa"))
    return [
        str(s.get("Nama_Lengkap", "")).strip()
        for s in rows
        if str(s.get("Status", "Aktif")).strip().lower() not in ["nonaktif", "tidak aktif"]
        and str(s.get("Nama_Lengkap", "")).strip()
    ]


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
        try:
            pasangan = json.loads(raw)
        except (ValueError, TypeError):
            raise ValueError("Kolom Opsi_Jawaban bukan JSON yang valid: " + str(q.get("Kode_Soal", "")))
        if not isinstance(pasangan, dict) or not isinstance(pasangan.get("kolom_A"), dict) or not isinstance(pasangan.get("kolom_B"), dict):
            raise ValueError("Format menjodohkan tidak valid: " + str(q.get("Kode_Soal", "")))
        opsi = []
    return {
        "ID_Soal": str(q.get("Kode_Soal", "")),
        "Jenjang": str(q.get("Jenjang", "")), "Kelas": str(q.get("Kelas", "")),
        "Mapel": str(q.get("Mapel", "")), "Topik": str(q.get("Bab_Atau_Topik", "")),
        "Bentuk_Soal": bentuk, "Teks_Soal": str(q.get("Teks_Soal", "")),
        "Url_Gambar": str(q.get("URL_Gambar", "")), "Opsi_List": opsi,
        "Pasangan": pasangan, "Kunci": str(q.get("Kunci_Jawaban", "")),
        "Pembahasan": str(q.get("Pembahasan", "")),
    }


# =========================================================
# LAMPIRAN: BANYAK FILE, FLIPBOOK, PRATINJAU
# =========================================================
def drive_id_dari_url(url):
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url) or re.search(r"[?&]id=([A-Za-z0-9_-]+)", url)
    return m.group(1) if m else None


def img_url(url):
    """Ubah link Drive menjadi link gambar yang bisa ditampilkan; link lain dibiarkan."""
    url = str(url or "").strip()
    fid = drive_id_dari_url(url) if "drive.google.com" in url else None
    return f"https://lh3.googleusercontent.com/d/{fid}=w1200" if fid else url


def jenis_dari_mime(mime, nama=""):
    m = (mime or "").lower()
    n = (nama or "").lower()
    if m.startswith("image/") or n.endswith((".png", ".jpg", ".jpeg")):
        return "img"
    if m == "application/pdf" or n.endswith(".pdf"):
        return "pdf"
    return "doc"


def parse_lampiran(teks):
    """'img::https://..|pdf::https://..' -> [('img', 'https://..'), ...].
    Data lama (satu URL polos) tetap terbaca sebagai 'link'."""
    hasil = []
    for bagian in str(teks or "").split("|"):
        bagian = bagian.strip()
        if not bagian:
            continue
        if "::" in bagian:
            jenis, url = bagian.split("::", 1)
        else:
            jenis, url = "link", bagian
        url = url.strip()
        if url.lower().startswith(("http://", "https://")):
            hasil.append((jenis.strip(), url))
    return hasil


def flipbook_gambar(urls, tinggi=700):
    """Flipbook: foto-foto menjadi halaman buku yang bisa dibalik / digeser."""
    imgs = json.dumps([img_url(u) for u in urls])
    html = """
<style>
  body { margin:0; font-family:sans-serif; background:#2b2b2b; }
  #book { margin:0 auto; }
  .page { background:#fff; }
  .page img { width:100%; height:100%; object-fit:contain; display:block; }
  .nav { text-align:center; padding:10px; color:#fff; }
  .nav button { padding:8px 14px; border:0; border-radius:8px; margin:0 6px; font-size:15px; }
</style>
<div id="book"></div>
<div class="nav">
  <button onclick="pf.flipPrev()">◀ Sebelumnya</button>
  <span id="info"></span>
  <button onclick="pf.flipNext()">Berikutnya ▶</button>
</div>
<script src="https://cdn.jsdelivr.net/npm/page-flip@2.0.7/dist/js/page-flip.browser.js"></script>
<script>
  const imgs = __IMGS__;
  const book = document.getElementById('book');
  imgs.forEach(src => {
    const d = document.createElement('div');
    d.className = 'page';
    d.innerHTML = '<img src="' + src + '">';
    book.appendChild(d);
  });
  const pf = new St.PageFlip(book, {
    width: 420, height: 588, size: 'stretch',
    minWidth: 260, maxWidth: 520, minHeight: 360, maxHeight: 728,
    showCover: false, usePortrait: true, mobileScrollSupport: false
  });
  pf.loadFromHTML(document.querySelectorAll('.page'));
  const info = document.getElementById('info');
  const total = pf.getPageCount();
  info.textContent = '1 / ' + total;
  pf.on('flip', e => { info.textContent = (e.data + 1) + ' / ' + total; });
</script>
""".replace("__IMGS__", imgs)
    components.html(html, height=tinggi)


def tampilkan_lampiran_siswa(link_or_file):
    """Tampilkan semua lampiran tugas: foto jadi flipbook, PDF/dokumen/link jadi pratinjau."""
    teks = str(link_or_file or "").strip()
    if not teks:
        return
    items = parse_lampiran(teks)
    if not items:
        st.info(f"Lampiran tercatat: {teks}. Tautan materi belum tersedia, hubungi tutor.")
        return

    st.markdown("#### 📖 Materi dari Tutor")
    gambar = [u for j, u in items if j == "img"]
    lainnya = [u for j, u in items if j != "img"]

    if gambar:
        flipbook_gambar(gambar)
    for u in lainnya:
        fid = drive_id_dari_url(u) if "drive.google.com" in u else None
        src_iframe = f"https://drive.google.com/file/d/{fid}/preview" if fid else u
        components.iframe(src_iframe, height=720, scrolling=True)
        st.markdown(f"[↗ Buka materi di tab baru]({u})")


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


def get_attendance_worksheet():
    ws = get_or_create_worksheet("Kehadiran_Sesi", KEHADIRAN_HEADERS, rows="3000", cols="12")
    if not header_cocok(ws.row_values(1), KEHADIRAN_HEADERS):
        raise ValueError("Header Kehadiran_Sesi tidak sesuai struktur database. Data tidak ditulis.")
    return ws


def get_attendance_corrections_worksheet():
    ws = get_or_create_worksheet("Riwayat_Koreksi_Kehadiran", KOREKSI_HEADERS, rows="2000", cols="8")
    if not header_cocok(ws.row_values(1), KOREKSI_HEADERS):
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
    """Cari sesi 'Hadir' yang belum selesai. Mengembalikan nomor baris ASLI di sheet."""
    ws = get_attendance_worksheet()
    records = baca_records_aman(ws)
    for rec in reversed(records):
        if (str(rec.get("ID_Siswa", "")).strip() == str(id_siswa).strip()
                and (not id_tutor or str(rec.get("ID_Tutor", "")).strip() == str(id_tutor).strip())
                and str(rec.get("Status_Kehadiran", "")).strip().lower() == "hadir"
                and not str(rec.get("Waktu_Selesai_Belajar", "")).strip()):
            return ws, rec["_baris"], rec
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
    nilai_baru = str(nilai_baru).strip()
    if kolom in ("Waktu_Hadir", "Waktu_Selesai_Belajar"):
        if not nilai_baru and kolom == "Waktu_Hadir":
            return False, "Waktu hadir tidak boleh kosong."
        if nilai_baru and not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d:[0-5]\d", nilai_baru):
            return False, "Format waktu harus HH:MM:SS, contoh 15:30:00."
    ws = get_attendance_worksheet()
    headers = ws.row_values(1)
    cell = ws.find(str(id_kehadiran))
    if not cell:
        return False, "Data kehadiran tidak ditemukan."
    col_num = headers.index(kolom) + 1
    nilai_lama = str(ws.cell(cell.row, col_num).value or "")
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
    if not header_cocok(ws.row_values(1), ANSWER_HEADERS):
        raise ValueError("Header DB_Jawaban_Siswa tidak sesuai. Struktur yang dibutuhkan: " + ", ".join(ANSWER_HEADERS))
    return ws


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
    """Simpan jawaban per soal. Tulis sekaligus (batch) agar tidak melebihi kuota Google Sheets.
    Draft TIDAK akan menimpa jawaban yang sudah dikirim / sudah dinilai."""
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
        return False  # jawaban sudah dikirim / dinilai: tidak boleh diubah lagi

    updates, new_rows = [], []
    for nomor, jawaban in answers.items():
        nomor = str(nomor)
        if jawaban is None:
            jawaban = ""
        teks = json.dumps(jawaban, ensure_ascii=False) if isinstance(jawaban, (list, dict)) else str(jawaban)
        waktu_kirim = now if submitted else ""
        values = [teks, status, now, waktu_kirim]
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


def normalisasi_opsi(teks):
    if not teks:
        return []
    return [x.strip() for x in str(teks).split("|") if x.strip()]


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
if peran == "🎓 Siswa":
    st.subheader("🎓 Login Portal Siswa")

    if "siswa_logged_in" not in st.session_state:
        st.session_state.siswa_logged_in = False
        st.session_state.siswa_nama = ""
        st.session_state.siswa_jenjang = ""
        st.session_state.siswa_id = ""

    if not st.session_state.siswa_logged_in:
        nama_siswa = st.text_input("Nama Lengkap / Panggilan Siswa:")
        pin_siswa = st.text_input("PIN Siswa (4 Angka):", type="password")

        if st.button("🚀 Masuk ke Akun Siswa"):
            data = baca_records_aman(sheet.worksheet("Data_Siswa"))
            siswa_found = False
            is_active = True
            for row in data:
                if (
                    str(row.get("Nama_Lengkap", "")).strip().lower() == nama_siswa.strip().lower()
                    and str(row.get("PIN_Siswa", "")).strip() == pin_siswa.strip()
                ):
                    siswa_found = True
                    status_siswa = str(row.get("Status", "Aktif")).strip().lower()
                    if status_siswa == "nonaktif":
                        is_active = False
                    else:
                        st.session_state.siswa_logged_in = True
                        st.session_state.siswa_nama = row.get("Nama_Lengkap")
                        st.session_state.siswa_id = str(row.get("ID_Siswa", "")).strip()
                        st.session_state.siswa_jenjang = str(row.get("Jenjang", "SD")).strip().upper()
                        st.rerun()
                    break
            if not siswa_found:
                st.error("Nama Siswa atau PIN Siswa salah!")
            elif not is_active:
                st.error("🚫 Akun Siswa Anda sudah Nonaktif. Silakan hubungi pengelola.")

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
                st.rerun()

        try:
            tugas_anak = [
                t for t in get_student_tasks()
                if str(t.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
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

        jawaban_siswa = [
            x for x in jawaban_records
            if str(x.get("ID_Siswa", "")).strip() == str(st.session_state.siswa_id).strip()
            or str(x.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
        ]
        status_by_task = {}
        for ans in jawaban_siswa:
            status_by_task[str(ans.get("ID_Tugas", ""))] = str(ans.get("Status", "Draft"))

        # Nilai dibaca sekali dan dipakai ulang di tab Hasil Penilaian
        try:
            nilai_records = baca_records_aman(sheet.worksheet("DB_Nilai_Tugas"))
        except gspread.WorksheetNotFound:
            nilai_records = []
        marked_ids = {str(n.get("ID_Tugas", "")) for n in nilai_records}

        total = len(tugas_anak)
        # Tugas yang sudah dinilai juga termasuk "sudah dikirim"
        submitted = sum(
            1 for t in tugas_anak
            if any(x in status_by_task.get(str(t.get("ID_Tugas", "")), "").lower() for x in ("dikirim", "dinilai"))
        )
        marked = sum(1 for t in tugas_anak if str(t.get("ID_Tugas", "")) in marked_ids)
        draft_count = sum(1 for t in tugas_anak if status_by_task.get(str(t.get("ID_Tugas", "")), "").lower() == "draft")
        pending = max(total - submitted - draft_count, 0)

        st.markdown("### 🏠 Beranda Belajar")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tugas diberikan", total)
        m2.metric("Belum dikerjakan", pending)
        m3.metric("Draft jawaban", draft_count)
        m4.metric("Sudah dinilai", marked)

        tab_tugas, tab_nilai, tab_riwayat = st.tabs([
            "📚 Materi & Tugas", "📝 Hasil Penilaian", "📈 Riwayat Belajar"
        ])

        with tab_tugas:
            st.markdown(f"### 🎒 Tugas Belajar Ananda {nama_aktif}")
            if st.session_state.get("_galat_simpan"):
                st.warning("Jawaban terakhir belum tersimpan otomatis: " + str(st.session_state.pop("_galat_simpan")))
            if not tugas_anak:
                st.info("Belum ada tugas yang diberikan Tutor.")
            else:
                for t in tugas_anak:
                    task_id = str(t.get("ID_Tugas", ""))
                    status = status_by_task.get(task_id, "Belum dikerjakan")
                    status_low = status.lower()
                    terkunci = ("dikirim" in status_low) or ("dinilai" in status_low)
                    judul_kartu = t.get("Judul_Tugas") or t.get("Instruksi") or "Tugas"
                    with st.expander(
                        f"{t.get('Mapel', 'Mapel')} · {judul_kartu} · {status}",
                        expanded=False
                    ):
                        timer_txt = str(t.get("Timer_Menit", "")).strip()
                        st.write(f"**Instruksi Tutor:** {t.get('Instruksi') or '-'}")
                        st.write(f"**Diberikan:** {t.get('Tanggal') or '-'}")
                        if str(t.get("Tenggat", "")).strip():
                            st.write(f"**Tenggat:** {t.get('Tenggat')}")
                        st.write(f"**Durasi:** {'Tanpa timer' if timer_txt in ('', '0') else timer_txt + ' menit'}")

                        tampilkan_lampiran_siswa(t.get("File_Offline", ""))

                        soal_json = str(t.get("Soal_JSON", "") or "")
                        try:
                            daftar_soal = json.loads(soal_json) if soal_json else []
                        except (ValueError, TypeError):
                            daftar_soal = []

                        if daftar_soal:
                            st.markdown("#### 📝 Lembar Jawaban Online")
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

                                # Setiap soal menyimpan DIRINYA SENDIRI ke tugas yang benar
                                def _simpan_satu(nilai, question_no=i, tid=task_id):
                                    try:
                                        simpan_jawaban_per_soal(
                                            tid, st.session_state.get("siswa_id", ""),
                                            {str(question_no): nilai}, submitted=False
                                        )
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
                                    st.multiselect(
                                        f"Pilih jawaban nomor {i}:",
                                        opsi, default=default_m,
                                        key=qkey, on_change=_update_answer, disabled=terkunci
                                    )
                                elif "pilihan ganda" in bentuk:
                                    tersimpan = old_answer.get(str(i))
                                    st.radio(
                                        f"Pilih jawaban nomor {i}:",
                                        opsi, index=opsi.index(tersimpan) if tersimpan in opsi else None,
                                        key=qkey, on_change=_update_answer, disabled=terkunci
                                    )
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
                                        for kode, teks_kiri in kiri.items():
                                            pilihan = ["— Pilih —"] + list(kanan.keys())
                                            nilai_lama = str(jawaban_lama.get(kode, "— Pilih —")) or "— Pilih —"
                                            pilihan_aktif = st.selectbox(
                                                f"{kode}. {teks_kiri}", pilihan,
                                                index=pilihan.index(nilai_lama) if nilai_lama in pilihan else 0,
                                                format_func=lambda x, d=kanan: x if x == "— Pilih —" else f"{x}. {d[x]}",
                                                key=f"{qkey}_{kode}", on_change=_update_pasangan,
                                                disabled=terkunci)
                                            jawaban_pasangan[kode] = "" if pilihan_aktif == "— Pilih —" else pilihan_aktif
                                        st.session_state[qkey] = jawaban_pasangan
                                elif "benar" in bentuk:
                                    nilai_default = old_answer.get(str(i))
                                    pilihan_bs = ["Benar", "Salah"]
                                    st.radio(
                                        f"Jawaban nomor {i}:",
                                        pilihan_bs, index=pilihan_bs.index(nilai_default) if nilai_default in pilihan_bs else None,
                                        horizontal=True, key=qkey, on_change=_update_answer, disabled=terkunci
                                    )
                                else:
                                    st.text_area(
                                        f"Jawaban nomor {i}:",
                                        value=str(old_answer.get(str(i), "")),
                                        key=qkey, on_change=_update_answer, disabled=terkunci
                                    )

                            if not terkunci:
                                current_answers = {}
                                for i in range(1, len(daftar_soal) + 1):
                                    v = st.session_state.get(f"student_{task_id}_{i}", "")
                                    current_answers[str(i)] = "" if v is None else v
                                belum = [n for n, v in current_answers.items() if jawaban_kosong(v)]
                                boleh_kirim = True
                                if belum:
                                    st.warning("Soal nomor " + ", ".join(belum) + " belum dijawab.")
                                    boleh_kirim = st.checkbox(
                                        "Saya yakin ingin mengirim walaupun masih ada soal yang kosong.",
                                        key=f"yakin_{task_id}"
                                    )
                                if st.button("📤 Kirim Jawaban", key=f"submit_{task_id}", disabled=not boleh_kirim):
                                    ok = simpan_pengiriman_jawaban(task_id, st.session_state.get("siswa_id", ""), current_answers)
                                    if ok:
                                        st.success("Jawaban berhasil dikirim. Tutor akan memeriksanya.")
                                    else:
                                        st.info("Jawaban untuk tugas ini sudah dikirim sebelumnya.")
                                    st.rerun()
                        elif not str(t.get("File_Offline", "")).strip():
                            st.info("Tugas ini tidak memiliki soal digital maupun lampiran. Hubungi Tutor.")
                        else:
                            st.info("Tugas ini tidak memiliki soal digital. Kerjakan melalui materi/lampiran yang diberikan Tutor.")

        with tab_nilai:
            st.markdown("### 📝 Hasil Penilaian Tutor")
            info_tugas = {str(t.get("ID_Tugas", "")): t for t in tugas_anak}
            hasil_nilai = [
                n for n in nilai_records
                if str(n.get("ID_Tugas", "")) in info_tugas
            ]
            if hasil_nilai:
                for n in reversed(hasil_nilai):
                    tg = info_tugas.get(str(n.get("ID_Tugas", "")), {})
                    st.markdown(f"**{tg.get('Mapel', 'Tugas')} — {tg.get('Judul_Tugas') or n.get('ID_Tugas', '')}**")
                    st.metric("Nilai", n.get("Nilai", "-"))
                    st.write(f"Catatan Tutor: {n.get('Catatan', '-')}")
                    st.caption(f"Diperiksa oleh {n.get('Tutor', '-')} · {n.get('Waktu_Penilaian', '-')}")
                    st.divider()
            else:
                st.info("Belum ada hasil penilaian dari Tutor.")

        with tab_riwayat:
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

            for row in data:
                if (
                    str(row.get("Username", "")).strip().lower() == username.strip().lower()
                    and str(row.get("PIN_Password", "")).strip() == pin.strip()
                ):
                    user_found = True
                    status_tutor = str(row.get("Status", "Aktif")).strip().lower()
                    if status_tutor == "nonaktif":
                        is_active = False
                    else:
                        st.session_state.tutor_logged_in = True
                        st.session_state.tutor_nama = str(row.get("Nama_Pengguna", "")).strip()
                        st.session_state.tutor_user_id = str(row.get("ID_User", "")).strip()
                        st.session_state.tutor_id = resolve_tutor_id(row)
                        st.rerun()
                    break

            if not user_found:
                st.error("Username atau PIN salah!")
            elif not is_active:
                st.error("🚫 Akun Pengajar Anda sudah Nonaktif.")

    else:
        st.success(f"👨‍🏫 Tutor Aktif: **{st.session_state.tutor_nama}**")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.session_state.tutor_id = ""
            st.session_state.tutor_user_id = ""
            st.rerun()

        if not st.session_state.get("tutor_id"):
            st.warning("ID tutor belum dapat dicocokkan dengan Data_Tutor. Fitur kehadiran dinonaktifkan sampai ID_User pada Akun_Pengguna cocok dengan Data_Tutor, atau nama akun sama persis dengan Nama_Tutor.")

        tutor_tab1, tutor_tab2, tutor_tab3, tutor_tab4 = st.tabs([
            "📝 Persiapan Sesi & Bank Soal",
            "📊 Portofolio Siswa",
            "➕ Materi Tambahan",
            "🕒 Kehadiran Siswa"
        ])

        # -------------------------------------------------
        # TAB 1: KONFIGURASI TUGAS DAN EVALUASI SESI (VERSI 2)
        # -------------------------------------------------
        with tutor_tab1:
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
                    # Widget biasa (bukan st.form) supaya pilihan sumber langsung mengubah isian di bawahnya.
                    n_form = st.session_state.get("form_n", 0)
                    k = f"{selected_siswa}_{n_form}"

                    mapel_tugas = st.selectbox("Mata pelajaran:", MAPEL_OPTIONS, key=f"mp_{k}")
                    judul_tugas = st.text_input("Judul / topik tugas:", key=f"jd_{k}")
                    jenis_tugas = st.radio("Jenis pengerjaan:", ["Online", "Offline"], horizontal=True, key=f"jn_{k}")
                    sumber_tugas = st.radio(
                        "Sumber materi / soal:",
                        [SUMBER_BANK, SUMBER_DRIVE, SUMBER_UPLOAD],
                        key=f"sm_{k}"
                    )
                    instruksi_tugas = st.text_area("Instruksi untuk siswa:", key=f"in_{k}")
                    timer_tugas = st.selectbox(
                        "Durasi pengerjaan:", [0, 15, 30, 45, 60, 90, 120], index=2,
                        format_func=lambda x: "Tanpa timer" if x == 0 else f"{x} menit", key=f"tm_{k}"
                    )
                    tenggat_tugas = st.date_input("Tanggal tenggat:", value=waktu_lokal().date(), key=f"tg_{k}")

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
                            # Pilihan soal memakai kode soal; kuncinya ikut filter agar pilihan lama
                            # tidak "nyasar" ke soal lain saat filter berubah.
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
                        link_tugas = st.text_area(
                            "Link Google Drive / Flipbook (satu link per baris):",
                            placeholder="https://...", key=f"lk_{k}"
                        )

                    else:  # SUMBER_UPLOAD
                        file_tugas = st.file_uploader(
                            "Pilih file dari perangkat (boleh banyak):",
                            type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
                            accept_multiple_files=True,
                            key=f"up_{k}"
                        )

                    tambah_draft = st.button("Tambahkan ke daftar tugas", key=f"tambah_{k}")

                    if tambah_draft:
                        link_list = [x.strip() for x in link_tugas.splitlines() if x.strip()]
                        daftar_file = list(file_tugas or [])
                        total_byte = sum(len(f.getvalue()) for f in daftar_file)

                        if not judul_tugas.strip():
                            st.error("Judul / topik tugas wajib diisi.")
                        elif sumber_tugas == SUMBER_BANK and not soal_dipilih:
                            st.error("Pilih minimal satu soal dari Bank Soal.")
                        elif sumber_tugas == SUMBER_DRIVE and not link_list:
                            st.error("Masukkan minimal satu link Drive / Flipbook.")
                        elif sumber_tugas == SUMBER_DRIVE and any(not l.lower().startswith(("http://", "https://")) for l in link_list):
                            st.error("Setiap link harus diawali https://")
                        elif sumber_tugas == SUMBER_UPLOAD and not daftar_file:
                            st.error("Pilih minimal satu file yang akan dilampirkan.")
                        elif any(len(f.getvalue()) > 10 * 1024 * 1024 for f in daftar_file):
                            st.error("Ukuran tiap lampiran maksimal 10 MB. Kompres file lalu unggah kembali.")
                        elif total_byte > 40 * 1024 * 1024:
                            st.error("Total lampiran satu tugas maksimal 40 MB. Bagi menjadi beberapa tugas.")
                        else:
                            # Isi file disimpan sementara di draft; file diunggah ke Drive
                            # saat Tutor menekan tombol Simpan & Kirim Semua Tugas.
                            files = [
                                {"name": f.name, "bytes": f.getvalue(),
                                 "mime": f.type or "application/octet-stream"}
                                for f in daftar_file
                            ]
                            st.session_state[draft_key].append({
                                "Mapel": mapel_tugas,
                                "Judul": judul_tugas.strip(),
                                "Jenis": jenis_tugas,
                                "Sumber": sumber_tugas,
                                "Instruksi": instruksi_tugas.strip(),
                                "Timer": timer_tugas,
                                "Tenggat": tenggat_tugas.strftime("%Y-%m-%d"),
                                "Links": link_list,
                                "Files": files,
                                "Soal": soal_dipilih
                            })
                            st.session_state["form_n"] = n_form + 1  # kosongkan isian setelah ditambahkan
                            st.success("Tugas masuk ke daftar draft. Tekan Simpan & Kirim setelah semua tugas selesai ditambahkan.")
                            st.rerun()

                daftar_draft = st.session_state[draft_key]
                st.markdown("### 📋 Daftar tugas yang akan dikirim")
                if daftar_draft:
                    for i, item in enumerate(daftar_draft, 1):
                        with st.expander(f"{i}. {item['Mapel']} — {item['Judul']} ({item['Jenis']})"):
                            st.write(f"Sumber: {item['Sumber']}")
                            st.write(f"Timer: {'Tanpa timer' if item['Timer'] == 0 else str(item['Timer']) + ' menit'} | Tenggat: {item['Tenggat']}")
                            st.write(f"Jumlah soal: {len(item['Soal'])}")
                            for l in item["Links"]:
                                st.write(f"Link: {l}")
                            for f in item["Files"]:
                                st.info(f"Lampiran siap diunggah ke Google Drive saat tugas dikirim: {f['name']}")
                    col_kirim, col_hapus = st.columns(2)
                    with col_kirim:
                        if st.button("📤 Simpan & Kirim Semua Tugas", type="primary", key=f"kirim_semua_{selected_siswa}"):
                            try:
                                ws_tugas = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS)
                                if not header_cocok(ws_tugas.row_values(1), TASK_HEADERS):
                                    st.error("Header Tugas_Sesi_Siswa_v2 berbeda dari struktur yang diperlukan. Data tidak ditulis agar tidak bergeser.")
                                else:
                                    # Unggah seluruh lampiran terlebih dahulu. Baris tugas baru
                                    # ditulis setelah semua unggahan berhasil.
                                    hasil_kirim = []
                                    for item in daftar_draft:
                                        entri = []
                                        for f in item["Files"]:
                                            url = upload_lampiran_ke_drive(f["bytes"], f["name"], f["mime"])
                                            entri.append(f"{jenis_dari_mime(f['mime'], f['name'])}::{url}")
                                        for l in item["Links"]:
                                            entri.append(f"link::{l}")
                                        hasil_kirim.append((item, "|".join(entri)))

                                    now_txt = waktu_lokal().strftime("%Y-%m-%d %H:%M:%S")
                                    baris_baru = []
                                    for item, file_info in hasil_kirim:
                                        id_tugas = "TGS-" + uuid.uuid4().hex[:10].upper()
                                        baris_baru.append([
                                            id_tugas, now_txt, selected_siswa,
                                            item["Mapel"], item["Judul"], item["Jenis"], item["Sumber"], item["Instruksi"],
                                            file_info, item["Timer"], item["Tenggat"], json.dumps(item["Soal"], ensure_ascii=False),
                                            "Diberikan", st.session_state.tutor_nama
                                        ])
                                    ws_tugas.append_rows(baris_baru, value_input_option="RAW")
                                    st.session_state[draft_key] = []
                                    st.success(f"{len(hasil_kirim)} tugas berhasil disimpan untuk {selected_siswa}. Lampiran yang dipilih sudah diunggah ke Google Drive.")
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
                # Tanggal dan pilihan mapel dipindah KELUAR form: widget di dalam st.form tidak
                # memicu tampilan ulang, sehingga kolom evaluasi per mapel tidak pernah muncul.
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
                    if not mapel_diajarkan:
                        st.error("Pilih minimal satu mata pelajaran yang diajarkan sebelum menyimpan jurnal.")
                    else:
                        try:
                            ws_sesi = get_or_create_worksheet("Jurnal_Sesi_Tutor_v2", ["ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Kondisi_Siswa", "Keaktifan", "Kendala_Umum", "Rekomendasi", "Handover", "Dokumentasi"])
                            id_sesi = "SES-" + uuid.uuid4().hex[:10].upper()
                            ws_sesi.append_row([id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, kondisi_siswa, keaktifan, kendala_umum, rekomendasi, handover, dokumentasi])
                            ws_eval = get_or_create_worksheet("Evaluasi_Mapel_Tutor_v2", ["ID_Evaluasi", "ID_Sesi", "Tanggal", "Nama_Siswa", "Tutor", "Mapel", "Materi", "Target", "Capaian", "Penguatan", "Nilai"])
                            baris_eval = [
                                ["EVL-" + uuid.uuid4().hex[:10].upper(), id_sesi, tanggal_sesi.strftime("%Y-%m-%d"), selected_siswa, st.session_state.tutor_nama, mp, ev["Materi"], ev["Target"], ev["Capaian"], ev["Penguatan"], ev["Nilai"]]
                                for mp, ev in evaluasi_mapel.items()
                            ]
                            if baris_eval:
                                ws_eval.append_rows(baris_eval)
                            st.success("Jurnal sesi dan evaluasi per mapel berhasil disimpan.")
                        except Exception as e:
                            st.error(f"Gagal menyimpan jurnal/evaluasi: {e}")

        # -------------------------------------------------
        # TAB 2: PORTOFOLIO DAN PENILAIAN JAWABAN
        # -------------------------------------------------
        with tutor_tab2:
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
                    opsi_jwb = {
                        f"{x.get('ID_Jawaban')} | {x.get('Nama_Siswa')} | {x.get('ID_Tugas')}": x
                        for x in menunggu
                    }
                    pilih_jwb = st.selectbox("Pilih jawaban siswa:", list(opsi_jwb.keys()))
                    item = opsi_jwb[pilih_jwb]
                    st.write(f"**Siswa:** {item.get('Nama_Siswa')}")
                    try:
                        jawaban_dict = json.loads(item.get("Jawaban_JSON", "{}"))
                    except (ValueError, TypeError):
                        jawaban_dict = {}
                    st.write("**Jawaban siswa:**")
                    st.json(jawaban_dict)
                    with st.form("form_penilaian_jawaban"):
                        nilai = st.number_input("Nilai (0–100):", min_value=0, max_value=100, value=0)
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
                            # Tandai seluruh baris soal pada penugasan/siswa sebagai sudah dinilai (sekali tulis).
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
        with tutor_tab3:
            st.header("➕ Materi & Soal Tambahan")
            try:
                siswa_pilihan_ekstra = get_siswa_aktif()
            except Exception as e:
                siswa_pilihan_ekstra = []
                st.error(f"Daftar siswa belum dapat dibaca: {e}")
            with st.form("form_materi_tambahan"):
                # Dipilih dari daftar (bukan diketik) agar tidak salah ketik nama siswa.
                nama_target_siswa = st.selectbox("Siswa Tujuan:", siswa_pilihan_ekstra) if siswa_pilihan_ekstra else ""
                mapel_ekstra = st.selectbox(
                    "Mata Pelajaran:",
                    MAPEL_OPTIONS
                )
                judul_materi = st.text_input("Judul Materi / Topik:")
                link_materi_ekstra = st.text_area("Link Modul / Flipbook / Soal (satu link per baris):")
                if st.form_submit_button("🚀 Kirim Materi Ekstra"):
                    links_ekstra = [x.strip() for x in link_materi_ekstra.splitlines() if x.strip()]
                    if not nama_target_siswa:
                        st.error("Pilih siswa tujuan.")
                    elif not judul_materi.strip():
                        st.error("Judul materi wajib diisi.")
                    elif not links_ekstra or any(not l.lower().startswith(("http://", "https://")) for l in links_ekstra):
                        st.error("Masukkan minimal satu link, dan setiap link harus diawali https://")
                    else:
                        try:
                            ws_tugas = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS)
                            if not header_cocok(ws_tugas.row_values(1), TASK_HEADERS):
                                raise ValueError("Header Tugas_Sesi_Siswa_v2 tidak sesuai. Data tidak ditulis.")
                            ws_tugas.append_row([
                                "TGS-" + uuid.uuid4().hex[:10].upper(),
                                waktu_lokal().strftime("%Y-%m-%d %H:%M:%S"),
                                nama_target_siswa,
                                mapel_ekstra,
                                judul_materi.strip(),
                                "Materi Tambahan",
                                "Link Modul / Flipbook / Soal",
                                f"[Materi Ekstra] {judul_materi.strip()}",
                                "|".join(f"link::{l}" for l in links_ekstra),
                                0,
                                "",
                                "[]",
                                "Diberikan",
                                st.session_state.tutor_nama
                            ])
                            st.success("Materi tambahan berhasil dikirim.")
                        except Exception as e:
                            st.error(f"Gagal mengirim materi: {e}")

        # -------------------------------------------------
        # TAB 4: KEHADIRAN SISWA
        # -------------------------------------------------
        with tutor_tab4:
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
                        opsi_siswa = {
                            f"{r.get('Nama_Lengkap', 'Tanpa nama')} · {r.get('ID_Siswa', '')}": r
                            for r in pilihan_siswa
                        }
                        pilihan_label = st.selectbox("Pilih siswa yang hadir:", list(opsi_siswa.keys()), key="attendance_student_select")
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
                                        nilai_koreksi = st.selectbox("Nilai baru:", ["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"], index=["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"].index(nilai_awal) if nilai_awal in ["Hadir", "Selesai Belajar", "Tidak Hadir", "Izin"] else 0, key=f"corr_val_{sid}_{kolom_koreksi}")
                                    else:
                                        nilai_koreksi = st.text_input("Nilai baru (format HH:MM:SS):", value=nilai_awal, key=f"corr_val_{sid}_{kolom_koreksi}")
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


# =========================================================
# 3. MODUL OWNER
# =========================================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola Bimbel")
    pin_owner = st.text_input("PIN Pengelola:", type="password")

    # PIN sebaiknya disimpan di Streamlit Secrets (owner_pin = "..."), bukan di kode GitHub.
    # Jika belum diatur, PIN lama dipakai sementara agar akses tidak terkunci.
    OWNER_PIN = str(st.secrets.get("owner_pin", "")).strip()
    if not OWNER_PIN:
        OWNER_PIN = "1605"
        st.warning("PIN Pengelola masih memakai bawaan di kode. Tambahkan owner_pin di Streamlit Secrets lalu ganti PIN-nya.")

    if pin_owner == OWNER_PIN:
        st.success("Akses diizinkan.")
        tab1, tab2, tab3 = st.tabs([
            "🎁 Undian Hadiah", "👥 Kelola Status Akun", "📚 Arsip Bank Soal"
        ])

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
                    # Pakai ID_Siswa (bukan nama) agar yang diubah pasti baris siswa yang dipilih.
                    opsi_status = {
                        f"{s.get('Nama_Lengkap')} · {s.get('ID_Siswa', '')}": s
                        for s in records_siswa if s.get("Nama_Lengkap")
                    }
                    pilih_nama = st.selectbox("Pilih Siswa:", list(opsi_status.keys()))
                    status_baru = st.selectbox("Status:", ["Aktif", "Nonaktif"])
                    if st.form_submit_button("Update Status"):
                        headers = ws_siswa.row_values(1)
                        if "Status" in headers:
                            baris = opsi_status[pilih_nama]["_baris"]
                            ws_siswa.update_cell(baris, headers.index("Status") + 1, status_baru)
                            st.success("Status berhasil diperbarui.")
                            st.rerun()
                        else:
                            st.error("Kolom Status tidak ditemukan di Data_Siswa.")
            else:
                st.info("Data siswa kosong.")

        with tab3:
            try:
                ws_bank = sheet.worksheet("Bank_Soal_Master")
                df_bank = pd.DataFrame(baca_records_aman(ws_bank)).drop(columns=["_baris"], errors="ignore")
                st.dataframe(df_bank, use_container_width=True)
            except Exception as e:
                st.error(f"Bank soal belum dapat dibuka: {e}")
    elif pin_owner:
        st.error("PIN salah.")


# =========================================================
# 4. MODUL ORANG TUA
# =========================================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua (Wali Siswa)")
    nama_anak = st.text_input("Nama Putra/Putri:")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")

    if st.button("Masuk Orang Tua"):
        data_siswa = baca_records_aman(sheet.worksheet("Data_Siswa"))
        ortu_found = False
        akun_nonaktif = False

        for row in data_siswa:
            if (
                str(row.get("Nama_Lengkap", "")).strip().lower() == nama_anak.strip().lower()
                and str(row.get("PIN_Ortu", "")).strip() == pin_ortu.strip()
            ):
                if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                    st.error("Akun siswa ini sudah Nonaktif.")
                    akun_nonaktif = True
                    break

                ortu_found = True
                id_anak_ortu = str(row.get("ID_Siswa", "")).strip()
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(
                    f"**Jenjang:** {row.get('Jenjang')} | "
                    f"**Poin:** {row.get('Poin', 0)}"
                )
                st.markdown("---")

                ortu_tab1, ortu_tab2, ortu_tab3 = st.tabs([
                    "📋 Transparansi Sesi & PR",
                    "📈 Rekap Nilai & Evaluasi",
                    "🕒 Kehadiran Anak"
                ])

                with ortu_tab1:
                    laporan_list = []
                    try:
                        ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                        for r in baca_records_aman(ws_riwayat):
                            if str(r.get("Nama_Siswa", "")).strip().lower() == nama_anak.strip().lower():
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
                            val_nama = str(
                                j.get("Nama Siswa", j.get("Nama_Siswa", ""))
                            ).strip().lower()
                            if val_nama == nama_anak.strip().lower():
                                laporan_list.append({
                                    "Tanggal": j.get("Tanggal Mengajar", j.get("Tanggal", "-")),
                                    "Materi": j.get(
                                        "Materi dan Pelajaran Hari Ini",
                                        j.get("Materi", "-")
                                    ),
                                    "Skor": j.get(
                                        "Nilai/skor latihan",
                                        j.get("Skor", "-")
                                    ),
                                    "Catatan": j.get("Pencapaian Belajar", "-")
                                })
                    except Exception:
                        pass

                    if laporan_list:
                        lap = laporan_list[-1]
                        st.write(f"📅 **Tanggal:** {lap.get('Tanggal')}")
                        st.write(f"📚 **Materi:** {lap.get('Materi')}")
                        st.write(f"💯 **Skor:** {lap.get('Skor')}")
                        st.info(f"**Catatan tutor:** {lap.get('Catatan')}")
                    else:
                        st.info("Belum ada catatan sesi terbaru.")

                with ortu_tab2:
                    data_tabel_ortu = []
                    try:
                        ws_r = sheet.worksheet("Riwayat_Latihan")
                        for r in baca_records_aman(ws_r):
                            if str(r.get("Nama_Siswa", "")).strip().lower() == nama_anak.strip().lower():
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
                        st.dataframe(pd.DataFrame(data_tabel_ortu), use_container_width=True)
                    else:
                        st.info("Belum ada data rekap nilai.")

                with ortu_tab3:
                    tampilkan_riwayat_kehadiran(id_anak_ortu, "Riwayat Kehadiran Anak")
                break

        if not ortu_found and not akun_nonaktif:
            st.error("Nama atau PIN salah.")
