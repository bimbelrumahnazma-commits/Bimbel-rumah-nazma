import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import pandas as pd
import random
import json
import uuid


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
    """Baca baris berdasarkan header; abaikan header kosong/duplikat agar tidak error."""
    values = ws.get_all_values()
    if not values:
        return []

    headers = [str(h).strip() for h in values[0]]
    hasil = []
    for row in values[1:]:
        if not any(str(v).strip() for v in row):
            continue
        item = {}
        for i, header in enumerate(headers):
            if not header:
                continue
            # Jika header duplikat, pertahankan nilai pertama yang tidak kosong.
            value = row[i] if i < len(row) else ""
            if header not in item or not item[header]:
                item[header] = value
        hasil.append(item)
    return hasil


TASK_HEADERS_V2 = [
    "ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Judul_Tugas",
    "Jenis_Tugas", "Sumber", "Instruksi", "File_Offline",
    "Timer_Menit", "Tenggat", "Soal_JSON", "Status_Tugas", "Tutor"
]


def get_tasks_worksheet():
    """Gunakan satu struktur tugas V2; tidak mengubah sheet tugas lama."""
    ws = get_or_create_worksheet("Tugas_Sesi_Siswa_v2", TASK_HEADERS_V2, cols="20")
    headers = ws.row_values(1)
    if headers != TASK_HEADERS_V2:
        raise ValueError(
            "Header Tugas_Sesi_Siswa_v2 tidak sesuai. Data lama tidak diubah. "
            "Periksa baris pertama sheet tersebut sebelum mengirim tugas."
        )
    return ws


def get_bank_soal():
    """Membaca Bank_Soal_Master_v2 sesuai kolom yang sudah disepakati."""
    ws = sheet.worksheet("Bank_Soal_Master_v2")
    records = baca_records_aman(ws)
    hasil = []
    for row in records:
        aktif = str(row.get("Aktif", "Ya")).strip().lower()
        if aktif not in ["tidak", "nonaktif", "false", "0"]:
            hasil.append(row)
    return hasil


def get_student_tasks():
    """Baca tugas V2. Sheet lama dibaca hanya sebagai kompatibilitas."""
    try:
        ws = sheet.worksheet("Tugas_Sesi_Siswa_v2")
        return baca_records_aman(ws)
    except gspread.WorksheetNotFound:
        try:
            ws = sheet.worksheet("Tugas_Sesi_Siswa")
            return baca_records_aman(ws)
        except gspread.WorksheetNotFound:
            return []


def get_answers_worksheet():
    return get_or_create_worksheet(
        "DB_Jawaban_Siswa",
        ["ID_Jawaban", "ID_Tugas", "Nama_Siswa",
         "Waktu_Kirim", "Jawaban_JSON", "Status"]
    )


def simpan_draft_jawaban():
    """Autosave jawaban per perubahan widget; satu record aktif per siswa dan tugas."""
    task_id = st.session_state.get("_draft_task_id", "")
    student = st.session_state.get("siswa_nama", "")
    answers = st.session_state.get("_draft_answers", {})
    if not task_id or not student:
        return
    ws = get_answers_worksheet()
    records = baca_records_aman(ws)
    found_row = None
    for idx, row in enumerate(records, start=2):
        if (str(row.get("ID_Tugas", "")) == task_id
                and str(row.get("Nama_Siswa", "")).strip().lower() == student.strip().lower()
                and str(row.get("Status", "")).lower() != "dikirim - menunggu penilaian"):
            found_row = idx
            break
    payload = json.dumps(answers, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if found_row:
        ws.update(f"D{found_row}:F{found_row}", [[now, payload, "Draft"]])
    else:
        ws.append_row([
            "JWB-" + uuid.uuid4().hex[:10].upper(), task_id, student,
            now, payload, "Draft"
        ])


def simpan_pengiriman_jawaban(task_id, student, answers):
    ws = get_answers_worksheet()
    records = baca_records_aman(ws)
    payload = json.dumps(answers, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, row in enumerate(records, start=2):
        if (str(row.get("ID_Tugas", "")) == task_id
                and str(row.get("Nama_Siswa", "")).strip().lower() == student.strip().lower()
                and str(row.get("Status", "")).lower() == "draft"):
            ws.update(f"D{idx}:F{idx}", [[now, payload, "Dikirim - Menunggu Penilaian"]])
            return
    ws.append_row([
        "JWB-" + uuid.uuid4().hex[:10].upper(), task_id, student,
        now, payload, "Dikirim - Menunggu Penilaian"
    ])


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
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

    if not st.session_state.siswa_logged_in:
        nama_siswa = st.text_input("Nama Lengkap / Panggilan Siswa:")
        pin_siswa = st.text_input("PIN Siswa (4 Angka):", type="password")

        if st.button("🚀 Masuk ke Akun Siswa"):
            ws = sheet.worksheet("Data_Siswa")
            data = baca_records_aman(ws)
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
            jawaban_records = baca_records_aman(jawaban_ws)
        except Exception as e:
            jawaban_records = []
            st.warning(f"Data jawaban belum dapat dibaca: {e}")

        jawaban_siswa = [
            x for x in jawaban_records
            if str(x.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
        ]
        status_by_task = {}
        for ans in jawaban_siswa:
            status_by_task[str(ans.get("ID_Tugas", ""))] = str(ans.get("Status", "Draft"))

        total = len(tugas_anak)
        submitted = sum(1 for t in tugas_anak if "dikirim" in status_by_task.get(str(t.get("ID_Tugas", "")), "").lower())
        marked_ids = {
            str(n.get("ID_Tugas", "")) for n in baca_records_aman(sheet.worksheet("DB_Nilai_Tugas"))
        } if "DB_Nilai_Tugas" in [w.title for w in sheet.worksheets()] else set()
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
            if not tugas_anak:
                st.info("Belum ada tugas yang diberikan Tutor.")
            else:
                for t in tugas_anak:
                    task_id = str(t.get("ID_Tugas", ""))
                    status = status_by_task.get(task_id, "Belum dikerjakan")
                    with st.expander(
                        f"{t.get('Mapel', 'Mapel')} · {t.get('Instruksi', 'Tugas')} · {status}",
                        expanded=False
                    ):
                        st.write(f"**Instruksi Tutor:** {t.get('Instruksi', '-')}")
                        st.write(f"**Diberikan:** {t.get('Tanggal', '-')}")
                        st.write(f"**Durasi:** {t.get('Timer_Menit', '-') } menit")
                        if t.get("File_Offline"):
                            link_or_file = str(t.get("File_Offline", ""))
                            if link_or_file.startswith("http"):
                                st.markdown(f"[📖 Buka materi / file]({link_or_file})")
                            else:
                                st.info(f"Lampiran tercatat: {link_or_file}. File belum tentu tersedia untuk dibuka.")
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

                            st.session_state["_draft_task_id"] = task_id
                            st.session_state["_draft_answers"] = dict(old_answer)
                            for i, soal in enumerate(daftar_soal, 1):
                                qkey = f"student_{task_id}_{i}"
                                bentuk = str(soal.get("Bentuk_Soal", "")).lower()
                                opsi = soal.get("Opsi_List", [])
                                st.markdown(f"**{i}. {soal.get('Teks_Soal', '')}**")
                                if soal.get("Url_Gambar"):
                                    st.image(soal["Url_Gambar"], use_container_width=True)

                                def _update_answer(question_no=i, widget_key=qkey):
                                    st.session_state.setdefault("_draft_answers", {})
                                    st.session_state["_draft_answers"][str(question_no)] = st.session_state.get(widget_key, "")
                                    simpan_draft_jawaban()

                                if "pilihan ganda kompleks" in bentuk:
                                    st.multiselect(
                                        f"Pilih jawaban nomor {i}:",
                                        opsi, default=old_answer.get(str(i), []),
                                        key=qkey, on_change=_update_answer
                                    )
                                elif "pilihan ganda" in bentuk:
                                    pilihan_default = old_answer.get(str(i), opsi[0] if opsi else None)
                                    st.radio(
                                        f"Pilih jawaban nomor {i}:",
                                        opsi, index=opsi.index(pilihan_default) if pilihan_default in opsi else 0,
                                        key=qkey, on_change=_update_answer
                                    )
                                elif "benar" in bentuk:
                                    nilai_default = old_answer.get(str(i), "Benar")
                                    pilihan_bs = ["Benar", "Salah"]
                                    st.radio(
                                        f"Jawaban nomor {i}:",
                                        pilihan_bs, index=pilihan_bs.index(nilai_default) if nilai_default in pilihan_bs else 0,
                                        horizontal=True, key=qkey, on_change=_update_answer
                                    )
                                else:
                                    st.text_area(
                                        f"Jawaban nomor {i}:",
                                        value=str(old_answer.get(str(i), "")),
                                        key=qkey, on_change=_update_answer
                                    )

                            if status.lower() != "dikirim - menunggu penilaian":
                                if st.button("📤 Kirim Jawaban", key=f"submit_{task_id}"):
                                    current_answers = {}
                                    for i in range(1, len(daftar_soal) + 1):
                                        current_answers[str(i)] = st.session_state.get(f"student_{task_id}_{i}", "")
                                    simpan_pengiriman_jawaban(task_id, nama_aktif, current_answers)
                                    st.success("Jawaban berhasil dikirim. Tutor akan memeriksanya.")
                                    st.rerun()
                            else:
                                st.info("Jawaban sudah dikirim dan sedang menunggu pemeriksaan Tutor.")
                        else:
                            st.info("Tugas ini tidak memiliki soal digital. Kerjakan melalui materi/lampiran yang diberikan Tutor.")

        with tab_nilai:
            st.markdown("### 📝 Hasil Penilaian Tutor")
            try:
                nilai_records = baca_records_aman(sheet.worksheet("DB_Nilai_Tugas"))
            except gspread.WorksheetNotFound:
                nilai_records = []
            hasil_nilai = [
                n for n in nilai_records
                if str(n.get("Nama_Siswa", "")).strip().lower() == nama_aktif.strip().lower()
            ]
            if hasil_nilai:
                for n in reversed(hasil_nilai):
                    st.markdown(f"**{n.get('Mapel', 'Tugas')} — {n.get('ID_Tugas', '')}**")
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
            except Exception as e:
                st.warning(f"Riwayat belajar belum dapat dibaca: {e}")


# =========================================================
# 2. MODUL TUTOR
# =========================================================
elif peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar Portal")

    if "tutor_logged_in" not in st.session_state:
        st.session_state.tutor_logged_in = False
        st.session_state.tutor_nama = ""

    if not st.session_state.tutor_logged_in:
        username = st.text_input("Username Pengajar:")
        pin = st.text_input("PIN / Password:", type="password")

        if st.button("Masuk Pengajar"):
            ws = sheet.worksheet("Akun_Pengguna")
            data = baca_records_aman(ws)
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
                        st.session_state.tutor_nama = row.get("Nama_Pengguna")
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
            st.rerun()

        tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs([
            "📝 Persiapan Sesi & Bank Soal",
            "📊 Portofolio Siswa",
            "➕ Materi Tambahan"
        ])

        # -------------------------------------------------
        # TAB 1: KONFIGURASI TUGAS DAN EVALUASI SESI (VERSI 2)
        # -------------------------------------------------
        with tutor_tab1:
            st.header("📖 Persiapan Sesi Pembelajaran")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = baca_records_aman(ws_siswa)
            siswa_aktif = [
                str(s.get("Nama_Lengkap", "")).strip()
                for s in data_siswa_all
                if str(s.get("Status", "Aktif")).strip().lower() not in ["nonaktif", "tidak aktif"]
                and str(s.get("Nama_Lengkap", "")).strip()
            ]

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
                    with st.form(f"form_tugas_baru_{selected_siswa}"):
                        mapel_tugas = st.selectbox(
                            "Mata pelajaran:",
                            MAPEL_OPTIONS
                        )
                        judul_tugas = st.text_input("Judul / topik tugas:")
                        jenis_tugas = st.radio("Jenis pengerjaan:", ["Online", "Offline"], horizontal=True)
                        sumber_tugas = st.selectbox(
                            "Sumber materi / soal:",
                            ["Bank Soal Bersama (Spreadsheet)", "Link Google Drive / Flipbook", "Upload dari perangkat"]
                        )
                        instruksi_tugas = st.text_area("Instruksi untuk siswa:")
                        timer_tugas = st.selectbox("Durasi pengerjaan:", [0, 15, 30, 45, 60, 90, 120], index=2, format_func=lambda x: "Tanpa timer" if x == 0 else f"{x} menit")
                        tenggat_tugas = st.date_input("Tanggal tenggat:", value=datetime.now().date())
                        link_tugas = st.text_input("Link Drive / Flipbook (jika digunakan):", placeholder="https://...")
                        file_tugas = st.file_uploader("Pilih file dari perangkat (opsional):", type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"], key=f"upload_tugas_{selected_siswa}")

                        bank = []
                        soal_dipilih = []
                        if sumber_tugas == "Bank Soal Bersama (Spreadsheet)":
                            try:
                                bank = get_bank_soal()
                                if bank:
                                    jenjang_filter = st.selectbox("Filter jenjang soal:", ["Semua"] + sorted({str(q.get("Jenjang", "")).strip() for q in bank if q.get("Jenjang")}))
                                    mapel_filter = st.selectbox("Filter mapel soal:", ["Semua"] + sorted({str(q.get("Mapel", "")).strip() for q in bank if q.get("Mapel")}))
                                    topik_filter = st.selectbox("Filter topik soal:", ["Semua"] + sorted({str(q.get("Topik", "")).strip() for q in bank if q.get("Topik")}))
                                    bank_filter = [q for q in bank if (jenjang_filter == "Semua" or str(q.get("Jenjang", "")).strip() == jenjang_filter) and (mapel_filter == "Semua" or str(q.get("Mapel", "")).strip() == mapel_filter) and (topik_filter == "Semua" or str(q.get("Topik", "")).strip() == topik_filter)]
                                    labels = [f"{q.get('ID_Soal', 'TANPA-ID')} | {str(q.get('Teks_Soal', ''))[:100]}" for q in bank_filter]
                                    selected_labels = st.multiselect("Pilih soal untuk tugas ini:", labels)
                                    for label in selected_labels:
                                        q = bank_filter[labels.index(label)]
                                        soal_dipilih.append({
                                            "ID_Soal": str(q.get("ID_Soal", "")),
                                            "Jenjang": str(q.get("Jenjang", "")),
                                            "Mapel": str(q.get("Mapel", "")),
                                            "Topik": str(q.get("Topik", "")),
                                            "Bentuk_Soal": str(q.get("Bentuk_Soal", "")),
                                            "Teks_Soal": str(q.get("Teks_Soal", "")),
                                            "Url_Gambar": str(q.get("Url_Gambar", "")),
                                            "Opsi_List": normalisasi_opsi(q.get("Opsi", "")),
                                            "Kunci": str(q.get("Kunci", ""))
                                        })
                                else:
                                    st.info("Bank Soal_Master_v2 belum berisi soal aktif.")
                            except Exception as e:
                                st.error(f"Bank soal belum dapat dibaca: {e}")
                        tambah_draft = st.form_submit_button("Tambahkan ke daftar tugas")

                    if tambah_draft:
                        if not judul_tugas.strip():
                            st.error("Judul / topik tugas wajib diisi.")
                        elif (
                            sumber_tugas == "Bank Soal Bersama (Spreadsheet)"
                            and not soal_dipilih
                            and file_tugas is None
                            and not link_tugas.strip()
                        ):
                            st.error(
                                "Pilih soal dari Bank Soal, atau lampirkan file / "
                                "masukkan link materi sebagai alternatif."
                            )
                        elif (
                            sumber_tugas == "Link Google Drive / Flipbook"
                            and not link_tugas.strip()
                            and file_tugas is None
                        ):
                            st.error("Masukkan link Drive / Flipbook atau lampirkan file dari perangkat.")
                        elif (
                            sumber_tugas == "Upload dari perangkat"
                            and file_tugas is None
                            and not link_tugas.strip()
                        ):
                            st.error("Pilih file yang akan dilampirkan atau masukkan link materi.")
                        else:
                            # File upload saat ini baru mencatat metadata; penyimpanan permanen
                            # memerlukan integrasi cloud pada tahap berikutnya.
                            file_meta = ""
                            if file_tugas is not None:
                                file_meta = file_tugas.name

                            sumber_final = sumber_tugas
                            if sumber_tugas == "Bank Soal Bersama (Spreadsheet)" and not soal_dipilih:
                                if file_tugas is not None and link_tugas.strip():
                                    sumber_final = "Upload perangkat + Link"
                                elif file_tugas is not None:
                                    sumber_final = "Upload dari perangkat"
                                elif link_tugas.strip():
                                    sumber_final = "Link Google Drive / Flipbook"

                            st.session_state[draft_key].append({
                                "Mapel": mapel_tugas,
                                "Judul": judul_tugas.strip(),
                                "Jenis": jenis_tugas,
                                "Sumber": sumber_final,
                                "Instruksi": instruksi_tugas.strip(),
                                "Timer": timer_tugas,
                                "Tenggat": tenggat_tugas.strftime("%Y-%m-%d"),
                                "Link": link_tugas.strip(),
                                "Nama_File": file_meta,
                                "Soal": soal_dipilih
                            })
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
                            if item["Link"]:
                                st.write(f"Link: {item['Link']}")
                            if item["Nama_File"]:
                                st.warning(f"File dipilih: {item['Nama_File']}. Isi file belum tersimpan permanen; diperlukan integrasi penyimpanan cloud.")
                    col_kirim, col_hapus = st.columns(2)
                    with col_kirim:
                        if st.button("📤 Simpan & Kirim Semua Tugas", type="primary", key=f"kirim_semua_{selected_siswa}"):
                            try:
                                ws_tugas = get_tasks_worksheet()
                                for item in daftar_draft:
                                    id_tugas = "TGS-" + uuid.uuid4().hex[:10].upper()
                                    file_info = item["Link"] or item["Nama_File"]
                                    ws_tugas.append_row([
                                        id_tugas, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_siswa,
                                        item["Mapel"], item["Judul"], item["Jenis"], item["Sumber"], item["Instruksi"],
                                        file_info, item["Timer"], item["Tenggat"], json.dumps(item["Soal"], ensure_ascii=False),
                                        "Diberikan", st.session_state.tutor_nama
                                    ])
                                st.session_state[draft_key] = []
                                st.success(f"{len(daftar_draft)} tugas berhasil disimpan untuk {selected_siswa}.")
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
                with st.form(f"form_jurnal_v2_{selected_siswa}"):
                    tanggal_sesi = st.date_input("Tanggal sesi:", datetime.now().date())
                    mapel_diajarkan = st.multiselect("Mata pelajaran yang diajarkan:", MAPEL_OPTIONS)
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
        with tutor_tab2:
            st.header("📊 Portofolio & Pemeriksaan Jawaban Siswa")

            try:
                ws_jawaban = sheet.worksheet("DB_Jawaban_Siswa")
                jawaban_records = baca_records_aman(ws_jawaban)
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
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ])
                            cell = ws_jawaban.find(item.get("ID_Jawaban"))
                            if cell:
                                headers = ws_jawaban.row_values(1)
                                status_col = headers.index("Status") + 1
                                ws_jawaban.update_cell(cell.row, status_col, "Sudah Dinilai")
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
            with st.form("form_materi_tambahan"):
                nama_target_siswa = st.text_input("Nama Siswa Tujuan:")
                mapel_ekstra = st.selectbox(
                    "Mata Pelajaran:",
                    MAPEL_OPTIONS
                )
                judul_materi = st.text_input("Judul Materi / Topik:")
                link_materi_ekstra = st.text_input("Link Modul / Flipbook / Soal:")
                if st.form_submit_button("🚀 Kirim Materi Ekstra"):
                    try:
                        ws_tugas = get_tasks_worksheet()
                        ws_tugas.append_row([
                            "TGS-" + uuid.uuid4().hex[:10].upper(),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            nama_target_siswa.strip(),
                            mapel_ekstra,
                            judul_materi.strip(),
                            "Offline",
                            "Materi Tambahan",
                            f"[Materi Ekstra] {judul_materi.strip()}",
                            link_materi_ekstra.strip(),
                            0,
                            "",
                            "[]",
                            "Diberikan",
                            st.session_state.tutor_nama
                        ])
                        st.success("Materi tambahan berhasil dikirim.")
                    except Exception as e:
                        st.error(f"Gagal mengirim materi: {e}")


# =========================================================
# 3. MODUL OWNER
# =========================================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola Bimbel")
    pin_owner = st.text_input("PIN Pengelola:", type="password")

    # Catatan keamanan: PIN hardcoded lama tetap dipertahankan untuk kompatibilitas tahap ini.
    # Pindahkan ke Streamlit Secrets sebelum aplikasi dipakai lebih luas.
    if pin_owner == "1605":
        st.success("Akses diizinkan.")
        tab1, tab2, tab3 = st.tabs([
            "🎁 Undian Hadiah", "👥 Kelola Status Akun", "📚 Arsip Bank Soal"
        ])

        with tab1:
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = baca_records_aman(ws_siswa)
            peserta_undian = []
            for s in data_siswa_all:
                try:
                    p_val = int(s.get("Poin", 0) or 0)
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
                    nama_tersedia = [
                        s.get("Nama_Lengkap") for s in records_siswa if s.get("Nama_Lengkap")
                    ]
                    pilih_nama = st.selectbox("Pilih Siswa:", nama_tersedia)
                    status_baru = st.selectbox("Status:", ["Aktif", "Nonaktif"])
                    if st.form_submit_button("Update Status"):
                        cell = ws_siswa.find(pilih_nama)
                        headers = ws_siswa.row_values(1)
                        if cell and "Status" in headers:
                            ws_siswa.update_cell(cell.row, headers.index("Status") + 1, status_baru)
                            st.success("Status berhasil diperbarui.")
                            st.rerun()
            else:
                st.info("Data siswa kosong.")

        with tab3:
            try:
                ws_bank = sheet.worksheet("Bank_Soal_Master_v2")
                st.dataframe(pd.DataFrame(baca_records_aman(ws_bank)), use_container_width=True)
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
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa = baca_records_aman(ws_siswa)
        ortu_found = False

        for row in data_siswa:
            if (
                str(row.get("Nama_Lengkap", "")).strip().lower() == nama_anak.strip().lower()
                and str(row.get("PIN_Ortu", "")).strip() == pin_ortu.strip()
            ):
                if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                    st.error("Akun siswa ini sudah Nonaktif.")
                    break

                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(
                    f"**Jenjang:** {row.get('Jenjang')} | "
                    f"**Poin:** {row.get('Poin', 0)}"
                )
                st.markdown("---")

                ortu_tab1, ortu_tab2 = st.tabs([
                    "📋 Transparansi Sesi & PR",
                    "📈 Rekap Nilai & Evaluasi"
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
                break

        if not ortu_found:
            st.error("Nama atau PIN salah.")
