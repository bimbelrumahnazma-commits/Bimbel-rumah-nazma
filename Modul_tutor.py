import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import pandas as pd
import random
import json
import uuid

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
        # TAB 1: PERSIAPAN DAN BANK SOAL
        # -------------------------------------------------
        with tutor_tab1:
            st.header("📖 Persiapan Sesi Pembelajaran")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            siswa_aktif = [
                s.get("Nama_Lengkap") for s in data_siswa_all
                if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif"
                and s.get("Nama_Lengkap")
            ]

            search_query = st.text_input("🔍 Cari nama siswa yang sedang diajar:").strip().lower()
            selected_siswa = None

            if search_query:
                hasil_pencarian = [
                    s for s in siswa_aktif if search_query in str(s).strip().lower()
                ]
                if hasil_pencarian:
                    pilihan = st.selectbox("Pilih Siswa:", ["-- Pilih Siswa --"] + hasil_pencarian)
                    if pilihan != "-- Pilih Siswa --":
                        selected_siswa = pilihan
                else:
                    st.warning("Siswa aktif tidak ditemukan.")
            else:
                st.info("Ketik nama siswa untuk menyiapkan materi dan tugas.")

            if selected_siswa:
                st.markdown("---")
                st.subheader(f"📚 Konfigurasi Tugas untuk: **{selected_siswa}**")

                mapel_pilihan_tutor = st.multiselect(
                    "Pilih mata pelajaran:",
                    [
                        "Matematika", "IPAS / Tematik", "Bahasa Inggris",
                        "IPA (Fisika/Kimia/Biologi)", "Bahasa Indonesia",
                        "PKN", "Olimpiade (OSN)"
                    ]
                )

                uploaded_files = st.file_uploader(
                    "Unggah file modul/soal dari perangkat (PDF, Word, Excel, gambar):",
                    type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
                    accept_multiple_files=True
                )
                link_file_tambahan = st.text_input(
                    "Link modul / Flipbook (opsional):",
                    placeholder="https://..."
                )
                timer_menit_opsi = st.selectbox(
                    "Durasi pengerjaan (menit):", [15, 30, 45, 60], index=1
                )
                instruksi_tutor = st.text_area("Instruksi untuk siswa:")

                st.markdown("---")
                st.subheader("📚 Pilih Soal dari Bank Soal Bersama")

                try:
                    bank = get_bank_soal()
                    if not bank:
                        st.info("Bank Soal_Master_v2 belum berisi soal aktif.")
                    else:
                        kolom = st.columns(3)
                        with kolom[0]:
                            filter_jenjang = st.selectbox(
                                "Filter jenjang:",
                                ["Semua"] + sorted({
                                    str(x.get("Jenjang", "")).strip()
                                    for x in bank if x.get("Jenjang")
                                })
                            )
                        with kolom[1]:
                            filter_mapel = st.selectbox(
                                "Filter mapel:",
                                ["Semua"] + sorted({
                                    str(x.get("Mapel", "")).strip()
                                    for x in bank if x.get("Mapel")
                                })
                            )
                        with kolom[2]:
                            filter_topik = st.selectbox(
                                "Filter topik:",
                                ["Semua"] + sorted({
                                    str(x.get("Topik", "")).strip()
                                    for x in bank if x.get("Topik")
                                })
                            )

                        bank_terfilter = []
                        for soal in bank:
                            if filter_jenjang != "Semua" and str(soal.get("Jenjang", "")).strip() != filter_jenjang:
                                continue
                            if filter_mapel != "Semua" and str(soal.get("Mapel", "")).strip() != filter_mapel:
                                continue
                            if filter_topik != "Semua" and str(soal.get("Topik", "")).strip() != filter_topik:
                                continue
                            bank_terfilter.append(soal)

                        pilihan_soal = []
                        for i, soal in enumerate(bank_terfilter):
                            id_soal = str(soal.get("ID_Soal", f"BARIS-{i+1}"))
                            label = f"{id_soal} | {soal.get('Mapel', '-')} | {str(soal.get('Teks_Soal', ''))[:85]}"
                            pilihan_soal.append(label)

                        if pilihan_soal:
                            dipilih = st.multiselect(
                                "Pilih satu atau beberapa soal untuk tugas ini:",
                                pilihan_soal
                            )
                            daftar_soal_terpilih = []
                            for label in dipilih:
                                idx = pilihan_soal.index(label)
                                soal = bank_terfilter[idx]
                                daftar_soal_terpilih.append({
                                    "ID_Soal": str(soal.get("ID_Soal", "")),
                                    "Jenjang": str(soal.get("Jenjang", "")),
                                    "Mapel": str(soal.get("Mapel", "")),
                                    "Topik": str(soal.get("Topik", "")),
                                    "Bentuk_Soal": str(soal.get("Bentuk_Soal", "")),
                                    "Teks_Soal": str(soal.get("Teks_Soal", "")),
                                    "Url_Gambar": str(soal.get("Url_Gambar", "")),
                                    "Opsi_List": normalisasi_opsi(soal.get("Opsi", "")),
                                    "Kunci": str(soal.get("Kunci", ""))
                                })

                            if daftar_soal_terpilih:
                                st.caption(f"{len(daftar_soal_terpilih)} soal dipilih.")
                                with st.expander("Pratinjau soal yang dipilih"):
                                    for no, q in enumerate(daftar_soal_terpilih, 1):
                                        st.write(f"**{no}. {q['Teks_Soal']}**")
                                        if q["Url_Gambar"]:
                                            st.image(q["Url_Gambar"], use_container_width=True)
                                        if q["Opsi_List"]:
                                            for opsi in q["Opsi_List"]:
                                                st.write(f"- {opsi}")
                        else:
                            daftar_soal_terpilih = []
                            st.warning("Tidak ada soal yang cocok dengan filter.")
                except Exception as e:
                    daftar_soal_terpilih = []
                    st.error(f"Gagal membaca Bank_Soal_Master_v2: {e}")

                st.markdown("---")
                st.subheader("✍️ Tambah Soal Baru ke Bank Soal")
                with st.expander("Buka editor soal baru"):
                    with st.form("form_soal_baru_bank"):
                        jenjang_baru = st.selectbox("Jenjang soal:", ["PAUD", "TK", "SD", "SMP", "SMA"])
                        mapel_baru = st.text_input("Mata pelajaran:")
                        topik_baru = st.text_input("Topik:")
                        bentuk_baru = st.selectbox(
                            "Bentuk soal:",
                            [
                                "Pilihan Ganda", "Pilihan Ganda Kompleks",
                                "Benar / Salah", "Menjodohkan",
                                "Isian Singkat", "Essay"
                            ]
                        )
                        teks_baru = st.text_area("Teks soal:")
                        gambar_baru = st.text_input("URL gambar (opsional):")
                        opsi_baru = st.text_input("Opsi jawaban, pisahkan dengan tanda |")
                        kunci_baru = st.text_input("Kunci jawaban (untuk tutor):")
                        simpan_soal_baru = st.form_submit_button("Simpan ke Bank Soal Bersama")

                        if simpan_soal_baru:
                            if not mapel_baru.strip() or not teks_baru.strip():
                                st.error("Mata pelajaran dan teks soal wajib diisi.")
                            else:
                                try:
                                    ws_bank = sheet.worksheet("Bank_Soal_Master_v2")
                                    id_baru = "SOAL-" + uuid.uuid4().hex[:8].upper()
                                    ws_bank.append_row([
                                        id_baru, jenjang_baru, mapel_baru.strip(),
                                        topik_baru.strip(), bentuk_baru,
                                        teks_baru.strip(), gambar_baru.strip(),
                                        opsi_baru.strip(), kunci_baru.strip(), "Ya"
                                    ])
                                    st.success(f"Soal {id_baru} berhasil ditambahkan ke bank soal.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menyimpan soal: {e}")

                st.markdown("---")
                if st.button("📤 Kirim Tugas ke Siswa", type="primary"):
                    if not mapel_pilihan_tutor:
                        st.error("Pilih minimal satu mata pelajaran.")
                    elif not daftar_soal_terpilih and not link_file_tambahan and not uploaded_files:
                        st.error("Pilih soal dari bank atau masukkan modul/link terlebih dahulu.")
                    else:
                        try:
                            file_info = link_file_tambahan.strip()
                            if uploaded_files:
                                nama_upload = ", ".join([f.name for f in uploaded_files])
                                if file_info:
                                    file_info += " | "
                                file_info += "Nama file terpilih: " + nama_upload
                                st.warning(
                                    "File dari perangkat baru tercatat namanya pada tahap ini; "
                                    "isi file belum disimpan permanen. Fitur penyimpanan cloud akan ditambahkan pada tahap berikutnya."
                                )

                            jumlah_tugas = 0
                            for mapel in mapel_pilihan_tutor:
                                soal_mapel = [
                                    q for q in daftar_soal_terpilih
                                    if not q.get("Mapel") or q.get("Mapel") == mapel
                                    or (mapel == "IPA (Fisika/Kimia/Biologi)" and q.get("Mapel") == "IPA")
                                ]
                                # Jika filter soal berasal dari mapel lain, tetap sertakan hanya jika tutor memilih satu mapel.
                                if not soal_mapel and len(mapel_pilihan_tutor) == 1:
                                    soal_mapel = daftar_soal_terpilih

                                task_id = simpan_tugas_dan_soal(
                                    selected_siswa, mapel, instruksi_tutor,
                                    timer_menit_opsi, soal_mapel,
                                    file_info, st.session_state.tutor_nama
                                )
                                jumlah_tugas += 1

                            st.success(
                                f"{jumlah_tugas} tugas berhasil dibuat untuk {selected_siswa}. "
                                "Tugas tersimpan di Google Sheets."
                            )
                        except Exception as e:
                            st.error(f"Gagal menyimpan tugas: {e}")

                st.markdown("---")
                st.subheader(f"📝 Jurnal & Evaluasi Sesi ({selected_siswa})")
                with st.form("form_jurnal"):
                    tgl = st.date_input("Tanggal Mengajar", datetime.now().date())
                    mapel_utama = st.selectbox(
                        "Mata Pelajaran Utama:",
                        [
                            "Matematika", "IPAS / Tematik", "Bahasa Inggris",
                            "IPA (Fisika/Kimia/Biologi)", "Lainnya"
                        ]
                    )
                    materi = st.text_area("Materi & Pelajaran Hari Ini")
                    pencapaian = st.text_area("Pencapaian Belajar Siswa")
                    kendala = st.text_area("Catatan Evaluasi / Kendala Belajar")
                    col_j1, col_j2 = st.columns(2)
                    with col_j1:
                        skor_offline = st.text_input("Nilai / Skor Latihan Offline")
                        pr_teks = st.text_input("Daftar PR / Tugas Rumah")
                    with col_j2:
                        foto_dok = st.text_input("Link Foto Dokumentasi (Opsional)")

                    if st.form_submit_button("💾 Simpan Jurnal Permanen"):
                        try:
                            ws_jurnal = sheet.worksheet("Form Responses 1")
                            ws_jurnal.append_row([
                                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                tgl.strftime("%d/%m/%Y"),
                                st.session_state.tutor_nama,
                                "Hadir",
                                selected_siswa,
                                f"[{mapel_utama}] {materi}",
                                pencapaian, kendala, pr_teks, foto_dok, skor_offline
                            ])
                            st.success("Jurnal berhasil disimpan.")
                        except Exception as e:
                            st.error(f"Gagal menyimpan jurnal: {e}")

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
                    ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA", "Olimpiade (OSN)"]
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
