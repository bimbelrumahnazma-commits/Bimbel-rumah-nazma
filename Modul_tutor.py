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


def get_bank_soal():
    """Membaca Bank_Soal_Master_v2 sesuai kolom yang sudah disepakati."""
    ws = sheet.worksheet("Bank_Soal_Master_v2")
    records = ws.get_all_records()
    hasil = []
    for row in records:
        aktif = str(row.get("Aktif", "Ya")).strip().lower()
        if aktif not in ["tidak", "nonaktif", "false", "0"]:
            hasil.append(row)
    return hasil


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
            data = ws.get_all_records()
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
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.success(
                f"Halo, Ananda **{st.session_state.siswa_nama}** "
                f"({st.session_state.siswa_jenjang})! Semangat Belajar! 🌟"
            )
        with c_head2:
            if st.button("🚪 Logout Siswa"):
                st.session_state.siswa_logged_in = False
                st.session_state.siswa_nama = ""
                st.session_state.siswa_jenjang = ""
                st.rerun()

        ws_s = sheet.worksheet("Data_Siswa")
        rec_s = ws_s.get_all_records()
        poin_siswa = 0
        for r in rec_s:
            if str(r.get("Nama_Lengkap", "")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                try:
                    poin_siswa = int(r.get("Poin", 0) or 0)
                except (ValueError, TypeError):
                    poin_siswa = 0
                break

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("🏆 Poin Koleksi Kamu", f"{poin_siswa} / 100 Poin")
            st.progress(min(max(poin_siswa / 100.0, 0), 1))
            if poin_siswa >= 100:
                st.balloons()
                st.success("🎉 Poinmu sudah mencapai 100! Kamu berhak ikut undian hadiah!")
        with col_m2:
            st.info("💡 Kumpulkan poin melalui kuis online dan aktivitas belajar bersama tutor.")

        st.markdown("---")
        siswa_tab1, siswa_tab2 = st.tabs([
            "📚 Ruang Belajar & Tugas",
            "📈 Rekap Nilai & Progress"
        ])

        with siswa_tab1:
            st.markdown(f"### 🎒 Ruang Belajar Ananda **{st.session_state.siswa_nama}**")
            st.info("Tugas yang diberikan tutor akan ditampilkan di sini.")

            try:
                # Tampilkan tugas dari sheet versi baru terlebih dahulu.
                try:
                    ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa_v2")
                except gspread.WorksheetNotFound:
                    ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")

                all_tugas = ws_tugas.get_all_records()
                tugas_anak = [
                    t for t in all_tugas
                    if str(t.get("Nama_Siswa", "")).strip().lower()
                    == st.session_state.siswa_nama.strip().lower()
                ]

                if tugas_anak:
                    for t in tugas_anak:
                        st.markdown(
                            f"#### 📌 {t.get('Mapel', '-')} "
                            f"— {t.get('Tanggal', '-')}"
                        )
                        st.write(f"**Instruksi Tutor:** {t.get('Instruksi', '-')}")
                        if t.get("File_Offline"):
                            st.markdown(f"[📖 Buka Modul / Flipbook]({t.get('File_Offline')})")

                        soal_json = t.get("Soal_JSON", "")
                        if soal_json:
                            try:
                                daftar_soal = json.loads(soal_json)
                            except (ValueError, TypeError):
                                daftar_soal = []

                            if daftar_soal:
                                st.markdown("**📝 Soal Online**")
                                with st.form(f"jawab_{t.get('ID_Tugas', uuid.uuid4().hex)}"):
                                    jawaban = {}
                                    for i, soal in enumerate(daftar_soal, 1):
                                        st.write(f"**{i}. {soal.get('Teks_Soal', '')}**")
                                        if soal.get("Url_Gambar"):
                                            st.image(soal["Url_Gambar"], use_container_width=True)

                                        bentuk = str(soal.get("Bentuk_Soal", "")).lower()
                                        opsi = soal.get("Opsi_List", [])

                                        if "pilihan ganda kompleks" in bentuk:
                                            jawaban[str(i)] = st.multiselect(
                                                f"Pilih jawaban nomor {i}:",
                                                opsi,
                                                key=f"ans_{t.get('ID_Tugas')}_{i}"
                                            )
                                        elif "pilihan ganda" in bentuk:
                                            jawaban[str(i)] = st.radio(
                                                f"Pilih jawaban nomor {i}:",
                                                opsi,
                                                key=f"ans_{t.get('ID_Tugas')}_{i}"
                                            )
                                        elif "benar" in bentuk:
                                            jawaban[str(i)] = st.radio(
                                                f"Jawaban nomor {i}:",
                                                ["Benar", "Salah"],
                                                horizontal=True,
                                                key=f"ans_{t.get('ID_Tugas')}_{i}"
                                            )
                                        elif "menjodohkan" in bentuk:
                                            jawaban[str(i)] = st.text_area(
                                                f"Pasangan jawaban nomor {i} (tulis pasangan):",
                                                key=f"ans_{t.get('ID_Tugas')}_{i}"
                                            )
                                        else:
                                            jawaban[str(i)] = st.text_area(
                                                f"Jawaban nomor {i}:",
                                                key=f"ans_{t.get('ID_Tugas')}_{i}"
                                            )

                                    if st.form_submit_button("📤 Kirim Jawaban"):
                                        ws_jawaban = get_or_create_worksheet(
                                            "DB_Jawaban_Siswa",
                                            [
                                                "ID_Jawaban", "ID_Tugas", "Nama_Siswa",
                                                "Waktu_Kirim", "Jawaban_JSON", "Status"
                                            ]
                                        )
                                        ws_jawaban.append_row([
                                            "JWB-" + uuid.uuid4().hex[:10].upper(),
                                            t.get("ID_Tugas", ""),
                                            st.session_state.siswa_nama,
                                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            json.dumps(jawaban, ensure_ascii=False),
                                            "Dikirim - Menunggu Penilaian"
                                        ])
                                        st.success("Jawaban terkirim. Nilai akan diberikan tutor setelah diperiksa.")
                        st.markdown("---")
                else:
                    st.info("Belum ada tugas yang diberikan tutor.")
            except Exception as e:
                st.warning(f"Tugas belum dapat dimuat: {e}")

        with siswa_tab2:
            st.subheader(f"📈 Rekap Nilai {st.session_state.siswa_nama}")
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                data_tabel_siswa = []
                for r in ws_r.get_all_records():
                    if str(r.get("Nama_Siswa", "")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                        data_tabel_siswa.append({
                            "Tanggal": str(r.get("Waktu_Selesai", ""))[:10],
                            "Mapel": r.get("Mapel"),
                            "Topik / Jenis": r.get("Topik_Kuis"),
                            "Skor / Nilai": r.get("Skor"),
                            "Keterangan": r.get("Detail_Salah")
                        })
                if data_tabel_siswa:
                    st.dataframe(pd.DataFrame(data_tabel_siswa), use_container_width=True)
                else:
                    st.info("Belum ada rekap nilai.")
            except Exception as e:
                st.info(f"Rekap nilai belum tersedia: {e}")


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
            data = ws.get_all_records()
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
            data_siswa_all = ws_siswa.get_all_records()
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
                                ws_tugas = get_or_create_worksheet(
                                    "Tugas_Sesi_Siswa_v2",
                                    ["ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Judul_Tugas", "Jenis_Tugas", "Sumber", "Instruksi", "File_Offline", "Timer_Menit", "Tenggat", "Soal_JSON", "Status_Tugas", "Tutor"]
                                )
                                headers_now = ws_tugas.row_values(1)
                                required_headers = ["ID_Tugas", "Tanggal", "Nama_Siswa", "Mapel", "Judul_Tugas", "Jenis_Tugas", "Sumber", "Instruksi", "File_Offline", "Timer_Menit", "Tenggat", "Soal_JSON", "Status_Tugas", "Tutor"]
                                if headers_now != required_headers:
                                    st.error("Header Tugas_Sesi_Siswa_v2 berbeda dari struktur yang diperlukan. Data tidak ditulis agar tidak bergeser.")
                                else:
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
                jawaban_records = ws_jawaban.get_all_records()
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
                    for r in ws_r.get_all_records():
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
                        ws_tugas = get_or_create_worksheet(
                            "Tugas_Sesi_Siswa",
                            ["Tanggal", "Nama_Siswa", "Mapel", "Instruksi", "File_Offline"]
                        )
                        ws_tugas.append_row([
                            datetime.now().strftime("%Y-%m-%d"),
                            nama_target_siswa,
                            mapel_ekstra,
                            f"[Materi Ekstra] {judul_materi}",
                            link_materi_ekstra
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
            data_siswa_all = ws_siswa.get_all_records()
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
            records_siswa = ws_siswa.get_all_records()
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
                st.dataframe(pd.DataFrame(ws_bank.get_all_records()), use_container_width=True)
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
        data_siswa = ws_siswa.get_all_records()
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
                        for r in ws_riwayat.get_all_records():
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
                        for j in ws_jurnal.get_all_records():
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
                        for r in ws_r.get_all_records():
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
