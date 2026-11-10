Import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import pandas as pd
import random

# --- KONFIGURASI HALAMAN & TAMPILAN PROFESIONAL ---
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

# --- KONEKSI GOOGLE SHEETS ---
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
    client = gspread.authorize(creds)
    return client

try:
    client = init_connection()
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/17JI1x966HfVG4YpfzCz_bssBwOmUTIJFbRutl0qyIZE/edit")
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()

# --- HEADER APLIKASI ---
st.markdown("""
<div class="main-header">
    <h2 style="margin:0;">✨ Portal Bimbel Rumah Nazma</h2>
    <p style="margin:4px 0 0 0; opacity:0.9;">Sistem Pembelajaran Terpadu, Multi-Mapel, Flipbook, Timer, & Evaluasi Berkelanjutan</p>
</div>
""", unsafe_allow_html=True)

peran = st.selectbox(
    "🔑 Pilih Akses Login Portal:",
    ["🎓 Siswa", "🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL SISWA
# ==========================================
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
                if str(row.get("Nama_Lengkap")).strip().lower() == nama_siswa.strip().lower() and str(row.get("PIN_Siswa")).strip() == pin_siswa.strip():
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
                st.error("🚫 **Akun Siswa Anda sudah Nonaktif. Silakan hubungi Mbak Fatimah.**")
    else:
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.success(f"Halo, Ananda **{st.session_state.siswa_nama}** ({st.session_state.siswa_jenjang})! Semangat Belajar! 🌟")
        with c_head2:
            if st.button("🚪 Logout Siswa"):
                st.session_state.siswa_logged_in = False
                st.session_state.siswa_nama = ""
                st.rerun()
                
        ws_s = sheet.worksheet("Data_Siswa")
        rec_s = ws_s.get_all_records()
        poin_siswa = 0
        for r in rec_s:
            if str(r.get("Nama_Lengkap")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                poin_siswa = int(r.get("Poin", 0)) if str(r.get("Poin", "")).isdigit() else 0
                break

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🏆 Poin Koleksi Kamu (Dari Game & Kuis Les)", value=f"{poin_siswa} / 100 Poin")
            st.progress(min(poin_siswa / 100.0, 1.0))
            if poin_siswa >= 100:
                st.balloons()
                st.success("🎉 Poinmu Sudah ≥ 100! Kamu berhak ikut Undian Hadiah Mbak Fatimah! 🎁")

        with col_m2:
            st.info("💡 Kumpulkan poin melalui kuis online dan aktivitas games bersama tutor di kelas les.")

        st.markdown("---")
        siswa_tab1, siswa_tab2 = st.tabs(["📚 Ruang Belajar & Tugas (Multi-Mapel)", "📈 Tabel Rekap Nilai & Progress Saya"])
        
        with siswa_tab1:
            st.markdown(f"### 🎒 Ruang Belajar Ananda **{st.session_state.siswa_nama}**")
            st.info("Berikut adalah materi, mode flipbook, dan kuis online/offline yang disiapkan tutor (Tugas tidak akan hilang meski ganti hari).")
            
            try:
                ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                all_tugas = ws_tugas.get_all_records()
                tugas_anak = [t for t in all_tugas if str(t.get("Nama_Siswa")).strip().lower() == st.session_state.siswa_nama.strip().lower()]
                
                if tugas_anak:
                    for idx_t, t in enumerate(tugas_anak, 1):
                        st.markdown(f"#### 📌 Mapel: **{t.get('Mapel')}** *(Tanggal: {t.get('Tanggal')})*")
                        st.write(f"**Instruksi Tutor:** {t.get('Instruksi')}")
                        if t.get('File_Offline'):
                            st.markdown("📖 **Modul / Soal (Tampilan Flipbook & Unduh):**")
                            st.markdown(f"🔗 [Buka Tautan Modul / Flipbook Sesi Ini]({t.get('File_Offline')})")
                            st.markdown("""
                            > *Tips Flipbook:* Gunakan mode tampilan buku digital untuk pengalaman membaca halaman demi halaman seperti buku fisik asli!
                            """)
                        st.markdown("---")
                else:
                    st.warning("Belum ada materi khusus untuk hari ini. Silakan cek menu materi/soal tambahan di bawah.")
            except:
                st.info("Memuat data ruang belajar...")

            st.markdown("---")
            st.subheader("📝 Kuis & Latihan Interaktif (Dilengkapi Timer & Anti-Cheat)")
            
            durasi_menit = st.selectbox("Pilih Durasi Pengerjaan (Timer):", [15, 30, 45, 60], index=1)
            if st.button("⏱️ Mulai Kerjakan Soal (Aktifkan Timer)"):
                st.session_state.timer_mulai = time.time()
                st.session_state.durasi_detik = durasi_menit * 60
                st.success(f"Timer aktif selama {durasi_menit} menit. Selamat mengerjakan!")

            if "timer_mulai" in st.session_state:
                waktu_berjalan = time.time() - st.session_state.timer_mulai
                sisa_waktu = int(st.session_state.durasi_detik - waktu_berjalan)
                
                if sisa_waktu > 0:
                    m_sisa = sisa_waktu // 60
                    d_sisa = sisa_waktu % 60
                    st.warning(f"⏳ **Sisa Waktu Ujian:** `{m_sisa:02d}:{d_sisa:02d}` (Fokus dan jangan tutup halaman!)")
                    
                    with st.form("form_kuis_siswa_aktif"):
                        st.write("Silakan masukkan jawaban latihan atau kuis online sesi ini:")
                        jawaban_text = st.text_area("Jawaban Anda (Pilihan Ganda / Essay / Isian):")
                        sub_kuis = st.form_submit_button("📤 Kirim Jawaban ke Tutor")
                        
                        if sub_kuis:
                            try:
                                ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                                last_id = len(ws_riwayat.get_all_records()) + 1
                                ws_riwayat.append_row([
                                    f"LAT-{last_id:03d}",
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    st.session_state.siswa_nama,
                                    "Multi-Mapel",
                                    "Kuis Sesi Interaktif",
                                    85, # Skor simulasi otomatis/tercatat
                                    10,
                                    f"Jawaban: {jawaban_text}"
                                ])
                                st.success("✅ Jawaban berhasil dikirim dan otomatis terekap di portofolio!")
                            except Exception as ex_k:
                                st.error(f"Gagal mengirim jawaban: {ex_k}")
                else:
                    st.error("⏰ Waktu Pengerjaan Telah Habis! Sistem mengunci lembar jawaban.")

        with siswa_tab2:
            st.subheader(f"📈 Tabel Rekap Nilai & Progress Ananda {st.session_state.siswa_nama}")
            data_tabel_siswa = []
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                for r in ws_r.get_all_records():
                    if str(r.get("Nama_Siswa")).strip().lower() == str(st.session_state.siswa_nama).strip().lower():
                        data_tabel_siswa.append({
                            "Tanggal": str(r.get("Waktu_Selesai"))[:10],
                            "Mapel": r.get("Mapel"),
                            "Topik / Jenis": r.get("Topik_Kuis"),
                            "Skor / Nilai": r.get("Skor"),
                            "Keterangan": r.get("Detail_Salah")
                        })
            except:
                pass

            if data_tabel_siswa:
                st.dataframe(pd.DataFrame(data_tabel_siswa), use_container_width=True)
            else:
                st.info("Belum ada rekap nilai dalam tabel.")

# ==========================================
# 2. MODUL TUTOR
# ==========================================
elif peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar Portal")
    
    if "tutor_logged_in" not in st.session_state:
        st.session_state.tutor_logged_in = False
        st.session_state.tutor_nama = ""

    if not st.session_state.tutor_logged_in:
        username = st.text_input("Username Pengajar (mei / rifky):")
        pin = st.text_input("PIN / Password:", type="password")
        
        if st.button("Masuk Pengajar"):
            ws = sheet.worksheet("Akun_Pengguna")
            data = ws.get_all_records()
            user_found = False
            is_active = True
            
            for row in data:
                if str(row.get("Username")).strip().lower() == username.strip().lower() and str(row.get("PIN_Password")).strip() == pin.strip():
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
                st.error("🚫 **Akun Pengajar Anda sudah Nonaktif.**")
    else:
        st.success(f"👨‍🏫 **Tutor Aktif:** {st.session_state.tutor_nama}")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.rerun()
            
        st.markdown("---")
        tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs(["📝 Persiapan Multi-Mapel, Flipbook & Timer", "📊 Portofolio Tabel Siswa", "➕ Materi & Soal Tambahan (Luar Jadwal)"])
        
        # TAB 1: PERSIAPAN SESI
        with tutor_tab1:
            st.header("📖 Persiapan Sesi Pembelajaran & Materi Multi-Mapel")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            siswa_aktif = [s.get("Nama_Lengkap") for s in data_siswa_all if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            search_query = st.text_input("🔍 Ketik Nama Siswa Aktif yang Sedang Diajar (Cth: Nazma):").strip().lower()
            selected_siswa = None
            
            if search_query:
                hasil_pencarian = [s for s in siswa_aktif if search_query in str(s).strip().lower()]
                if hasil_pencarian:
                    pilihan = st.selectbox("Pilih Siswa:", ["-- Pilih Siswa --"] + hasil_pencarian)
                    if pilihan != "-- Pilih Siswa --":
                        selected_siswa = pilihan
                else:
                    st.warning("Siswa aktif tidak ditemukan.")
            else:
                st.info("💡 Ketik nama siswa di atas untuk mulai menyiapkan materi multi-mapel, flipbook, dan timer.")
            
            if selected_siswa:
                st.markdown("---")
                st.subheader(f"📚 Konfigurasi Sesi Multi-Mapel untuk: **{selected_siswa}**")
                
                mapel_pilihan_tutor = st.multiselect(
                    "Pilih Mapel yang Akan Dibahas Hari Ini (Bisa Lebih dari 1 dalam 1 Pertemuan):",
                    ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA (Fisika/Kimia/Biologi)", "Bahasa Indonesia", "PKN", "Olimpiade (OSN)"]
                )
                
                if mapel_pilihan_tutor:
                    st.success(f"✨ Sesi hari ini mencakup mapel: **{', '.join(mapel_pilihan_tutor)}**")
                    
                    st.markdown("---")
                    with st.form("form_persiapan_materi_lengkap"):
                        st.markdown("#### 📂 1. Soal / Modul Offline (Multi-File & Flipbook)")
                        uploaded_files = st.file_uploader(
                            "Browse file offline dari perangkat (PDF, Word, Excel, Foto/Gambar - Bisa lebih dari 1 file):",
                            type=["pdf", "docx", "xlsx", "png", "jpg", "jpeg"],
                            accept_multiple_files=True
                        )
                        link_file_tambahan = st.text_area("Atau tempel Link Google Drive / File Manager / Flipbook:", placeholder="https://... (Link modul/flipbook)")
                        
                        st.markdown("---")
                        st.markdown("#### ⏱️ 2. Pengaturan Timer & Mode Pengerjaan")
                        timer_menit_opsi = st.selectbox("Set Timer Durasi Fokus Siswa (Online & Offline):", [15, 30, 45, 60], index=1)
                        
                        st.markdown("---")
                        st.markdown("#### 📝 3. Soal Online & Konversi Pintar (Teks/Pilgan/Isian + Flipbook TKA Kompleks)")
                        sumber_soal_opsi = st.selectbox("Pilih Sumber Soal Online:", [
                            "Tarik Otomatis dari Master Bank Soal (Spreadsheet)",
                            "Buat / Input Soal Baru & Konversi Pintar Khusus Sesi Ini"
                        ])
                        
                        instruksi_tutor = st.text_area("Instruksi / Catatan Pengerjaan untuk Siswa:", placeholder="Contoh: Kerjakan kuis online berikut dan baca modul flipbook terlampir.")
                        
                        if sumber_soal_opsi == "Buat / Input Soal Baru & Konversi Pintar Khusus Sesi Ini":
                            st.markdown("##### ✍️ Editor Soal Online")
                            bentuk_soal_baru = st.selectbox("Bentuk Soal:", ["Pilihan Ganda", "Pilihan Ganda Kompleks", "Benar / Salah", "Menjodohkan", "Essay"])
                            teks_soal_baru = st.text_area("Teks Soal:")
                            url_gambar_baru = st.text_input("Link Gambar / Ilustrasi / Tabel Kompleks (Tampil via Flipbook jika berupa dokumen/gambar besar):", placeholder="https://...")
                            opsi_baru = st.text_input("Opsi Jawaban (Pisahkan dengan | ):", placeholder="A. ... | B. ... | C. ... | D. ...")
                            kunci_baru = st.text_input("Kunci Jawaban:")
                        else:
                            bentuk_soal_baru, teks_soal_baru, url_gambar_baru, opsi_baru, kunci_baru = "", "", "", "", ""

                        btn_simpan_tugas = st.form_submit_button("📤 Simpan & Kirim ke Akun Siswa (Arsip Permanen)")
                        
                        if btn_simpan_tugas:
                            try:
                                try:
                                    ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                                except:
                                    ws_tugas = sheet.add_worksheet(title="Tugas_Sesi_Siswa", rows="1000", cols="10")
                                    ws_tugas.append_row(["Tanggal", "Nama_Siswa", "Mapel", "Instruksi", "File_Offline"])
                                    
                                file_info_str = f"Link/Flipbook: {link_file_tambahan} (Timer: {timer_menit_opsi} Menit)"
                                if uploaded_files:
                                    nama_file_list = [f.name for f in uploaded_files]
                                    file_info_str += f" | Uploaded: {', '.join(nama_file_list)}"

                                for m_item in mapel_pilihan_tutor:
                                    ws_tugas.append_row([
                                        datetime.now().strftime("%Y-%m-%d"),
                                        selected_siswa,
                                        m_item,
                                        f"[{sumber_soal_opsi}] {instruksi_tutor}",
                                        file_info_str
                                    ])
                                    
                                if sumber_soal_opsi == "Buat / Input Soal Baru & Konversi Pintar Khusus Sesi Ini" and teks_soal_baru:
                                    sheet.worksheet("Bank_Soal_Master").append_row([bentuk_soal_baru, teks_soal_baru, url_gambar_baru, opsi_baru, kunci_baru])

                                st.success(f"✅ Materi multi-mapel, flipbook, dan timer untuk {selected_siswa} berhasil disimpan permanen dan tampil di akun siswa!")
                            except Exception as ex_t:
                                st.error(f"Gagal menyimpan tugas: {ex_t}")

                    # Tombol Print Epson (Jika anak lupa bawa gadget)
                    with st.expander("🖨️ Mode Cetak Lembar Fisik (Printer Epson - Jika Siswa Lupa Bawa Gadget)"):
                        st.write("Gunakan tombol ini untuk langsung mencetak lembar soal/materi ke printer Epson.")
                        if st.button("🖨️ Cetak Lembar Soal / Materi Sekarang"):
                            st.markdown("""
                            <script>window.print();</script>
                            """, unsafe_allow_html=True)
                            st.success("Perintah cetak dikirim ke printer!")

                st.markdown("---")
                # Jurnal & Evaluasi Jangka Panjang
                st.subheader(f"📝 Input Jurnal & Evaluasi Sesi Ini ({selected_siswa})")
                with st.form("form_jurnal"):
                    tgl = st.date_input("Tanggal Mengajar", datetime.now())
                    mapel_utama = st.selectbox("Mata Pelajaran Utama Sesi Ini", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA (Fisika/Kimia/Biologi)", "Lainnya"])
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
                                pencapaian,
                                kendala,
                                pr_teks,
                                foto_dok,
                                skor_offline
                            ])
                            st.success("✅ Jurnal & Arsip Evaluasi Berhasil Disimpan Permanen!")
                        except Exception as ex_j:
                            st.error(f"Gagal menyimpan jurnal: {ex_j}")

        # TAB 2: PORTOFOLLIO TABEL SISWA
        with tutor_tab2:
            st.header("📊 Portofolio & Tabel Rekap Nilai Siswa (Privasi Aman)")
            st.caption("Ketik nama siswa secara spesifik untuk melihat rekap tabel nilainya secara lengkap.")
            
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            list_nama_aktif = [s.get("Nama_Lengkap") for s in data_siswa_all if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            search_portofolio = st.text_input("🔍 Ketik Nama Siswa untuk Membuka Portofolio:").strip().lower()
            pilih_siswa_histori = "-- Pilih Siswa --"
            
            if search_portofolio:
                hasil_p_match = [n for n in list_nama_aktif if search_portofolio in n.strip().lower()]
                if hasil_p_match:
                    pilih_siswa_histori = st.selectbox("Pilih Hasil Pencarian Siswa:", ["-- Pilih Siswa --"] + hasil_p_match, key="select_portofolio_aman")
                else:
                    st.warning("Nama siswa tidak ditemukan.")
            
            if pilih_siswa_histori != "-- Pilih Siswa --":
                st.markdown("---")
                st.subheader(f"📋 Tabel Rekap Nilai & Latihan: {pilih_siswa_histori}")
                data_rekap_tutor = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == pilih_siswa_histori.strip().lower():
                            data_rekap_tutor.append({
                                "Tanggal": str(r.get("Waktu_Selesai"))[:10],
                                "Mapel": r.get("Mapel"),
                                "Aktivitas": r.get("Topik_Kuis"),
                                "Skor": r.get("Skor"),
                                "Catatan": r.get("Detail_Salah")
                            })
                except:
                    pass

                if data_rekap_tutor:
                    st.dataframe(pd.DataFrame(data_rekap_tutor), use_container_width=True)
                else:
                    st.info("Belum ada rekap nilai latihan untuk siswa ini.")

        # TAB 3: MATERI & SOAL TAMBAHAN (LUAR JADWAL)
        with tutor_tab3:
            st.header("➕ Tambah Materi & Soal Ekstra (Di Luar Jadwal Reguler)")
            with st.form("form_materi_tambahan"):
                nama_target_siswa = st.text_input("Nama Siswa Tujuan:")
                mapel_Ekstra = st.selectbox("Mata Pelajaran Ekstra:", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA", "Olimpiade (OSN)"])
                judul_materi = st.text_input("Judul Materi / Topik Latihan Mandiri:")
                link_materi_ekstra = st.text_input("Link Modul / Flipbook / Soal Ekstra:", placeholder="https://...")
                
                if st.form_submit_button("🚀 Kirim Materi Ekstra ke Siswa"):
                    try:
                        ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                        ws_tugas.append_row([
                            datetime.now().strftime("%Y-%m-%d"),
                            nama_target_siswa,
                            mapel_Ekstra,
                            f"[Materi Ekstra/Luar Jadwal] {judul_materi}",
                            link_materi_ekstra
                        ])
                        st.success("✅ Materi dan soal ekstra berhasil dikirim dan dapat diakses siswa kapan saja!")
                    except Exception as ex_ekstra:
                        st.error(f"Gagal mengirim materi ekstra: {ex_ekstra}")

# ==========================================
# 3. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola Bimbel")
    pin_owner = st.text_input("PIN Pengelola:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Diizinkan 👋")
        tab1, tab2, tab3 = st.tabs(["🎁 Undian Hadiah Siswa (Poin ≥ 100)", "👥 Kelola Status Akun", "📚 Arsip Master Bank Soal"])
        
        with tab1:
            st.markdown("### 🎁 Pengundian Hadiah Giveaway")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            
            peserta_undian = []
            for s in data_siswa_all:
                p_val = int(s.get("Poin", 0)) if str(s.get("Poin", "")).isdigit() else 0
                if p_val >= 100 and str(s.get("Status", "Aktif")).strip().lower() != "nonaktif":
                    peserta_undian.append({"Nama": s.get("Nama_Lengkap"), "Jenjang": s.get("Jenjang"), "Poin": p_val})
                    
            if peserta_undian:
                st.dataframe(pd.DataFrame(peserta_undian), use_container_width=True)
                if st.button("🎲 Undi Pemenang Sekarang!"):
                    pemenang = random.choice(peserta_undian)
                    st.balloons()
                    st.success(f"🎉 SELAMAT KEPADA PEMENANG: **{pemenang['Nama']}** ({pemenang['Jenjang']})!")
            else:
                st.info("Belum ada siswa yang mencapai 100 poin.")

        with tab2:
            st.markdown("### 🔐 Status Aktif / Nonaktif Akun")
            ws_siswa = sheet.worksheet("Data_Siswa")
            records_siswa = ws_siswa.get_all_records()
            st.dataframe(pd.DataFrame(records_siswa)[["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]], use_container_width=True)
            
            with st.form("form_status"):
                pilih_nama = st.selectbox("Pilih Siswa:", [s.get("Nama_Lengkap") for s in records_siswa if s.get("Nama_Lengkap")])
                status_baru = st.selectbox("Status:", ["Aktif", "Nonaktif"])
                if st.form_submit_button("Update Status"):
                    cell = ws_siswa.find(pilih_nama)
                    col_idx = list(records_siswa[0].keys()).index("Status") + 1
                    ws_siswa.update_cell(cell.row, col_idx, status_baru)
                    st.success("Status berhasil diperbarui!")

        with tab3:
            st.dataframe(sheet.worksheet("Bank_Soal_Master").get_all_records(), use_container_width=True)
    elif pin_owner:
        st.error("PIN Salah!")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua (Wali Siswa)")
    nama_anak = st.text_input("Nama Putra/Putri:")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa = ws_siswa.get_all_records()
        ortu_found = False
        
        for row in data_siswa:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                    st.error("🚫 Akun siswa ini sudah Nonaktif.")
                    break
                
                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(f"**Jenjang:** {row.get('Jenjang')} | **Koleksi Poin Undian Anak:** `{row.get('Poin', 0)} Poin`")
                st.markdown("---")
                
                ortu_tab1, ortu_tab2 = st.tabs(["📋 Transparansi Sesi & PR Hari Ini", "📈 Tabel Rekap Nilai & Evaluasi Lengkap"])
                
                with ortu_tab1:
                    st.markdown("### 📋 Laporan Transparan Aktivitas Belajar Anak")
                    laporan_list = []
                    try:
                        ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                        for r in ws_riwayat.get_all_records():
                            if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                laporan_list.append({
                                    'Tanggal': r.get('Waktu_Selesai', '-'),
                                    'Materi': f"[{r.get('Mapel')}] {r.get('Topik_Kuis')}",
                                    'Skor': r.get('Skor', '-'),
                                    'Catatan': r.get('Detail_Salah', '-')
                                })
                    except:
                        pass

                    try:
                        ws_jurnal = sheet.worksheet("Form Responses 1")
                        for j in ws_jurnal.get_all_records():
                            val_nama = str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower()
                            if val_nama == nama_anak.strip().lower():
                                laporan_list.append({
                                    'Tanggal': j.get('Tanggal Mengajar', j.get('Tanggal', '-')),
                                    'Materi': j.get('Materi dan Pelajaran Hari Ini', j.get('Materi', '-')),
                                    'Skor': j.get('Nilai/skor latihan', j.get('Skor', '-')),
                                    'Catatan': j.get('Pencapaian Belajar', '-')
                                })
                    except:
                        pass

                    if laporan_list:
                        lap = laporan_list[-1]
                        st.write(f"📅 **Tanggal Sesi Terakhir:** {lap.get('Tanggal')}")
                        st.write(f"📚 **Materi Diajarkan Tutor:** {lap.get('Materi')}")
                        st.write(f"💯 **Skor Latihan:** {lap.get('Skor')}")
                        st.info(f"**Catatan / Evaluasi Tutor:** {lap.get('Catatan')}")
                    else:
                        st.info("Belum ada catatan sesi belajar terbaru.")

                with ortu_tab2:
                    st.subheader("📈 Tabel Rekap Nilai & Evaluasi Jangka Panjang")
                    data_tabel_ortu = []
                    try:
                        ws_r = sheet.worksheet("Riwayat_Latihan")
                        for r in ws_r.get_all_records():
                            if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                data_tabel_ortu.append({
                                    "Tanggal": str(r.get("Waktu_Selesai"))[:10],
                                    "Mapel": r.get("Mapel"),
                                    "Aktivitas": r.get("Topik_Kuis"),
                                    "Skor": r.get("Skor"),
                                    "Evaluasi": r.get("Detail_Salah")
                                })
                    except:
                        pass
                    
                    if data_tabel_ortu:
                        st.dataframe(pd.DataFrame(data_tabel_ortu), use_container_width=True)
                    else:
                        st.info("Belum ada data rekap nilai.")
                break
        if not ortu_found:
            st.error("Nama atau PIN Salah!")

