import streamlit as st
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
    <p style="margin:4px 0 0 0; opacity:0.9;">Sistem Pembelajaran Terpadu, Multi-Mapel, Gamifikasi & Portofolio Berkelanjutan</p>
</div>
""", unsafe_allow_html=True)

peran = st.selectbox(
    "🔑 Pilih Akses Login Portal:",
    ["🎓 Siswa", "🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL SISWA (AKSES MULTI-MAPEL & KUIS)
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
                st.session_state.pop("start_time", None)
                st.session_state.pop("kuis_submitted", None)
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
        siswa_tab1, siswa_tab2 = st.tabs(["📚 Materi & Kuis Sesi Hari Ini (Multi-Mapel)", "📈 Grafik Progress Nilai Saya"])
        
        with siswa_tab1:
            st.markdown(f"### 🎒 Ruang Belajar Ananda **{st.session_state.siswa_nama}**")
            st.info("Berikut adalah materi, file offline, dan kuis multi-mapel yang telah disiapkan oleh tutor untuk pertemuan hari ini.")
            
            # Menampilkan tugas/materi multi-mapel yang disiapkan tutor untuk siswa ini
            try:
                ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                all_tugas = ws_tugas.get_all_records()
                tugas_anak = [t for t in all_tugas if str(t.get("Nama_Siswa")).strip().lower() == st.session_state.siswa_nama.strip().lower()]
                
                if tugas_anak:
                    for idx_t, t in enumerate(tugas_anak, 1):
                        st.markdown(f"#### 📌 Mapel: **{t.get('Mapel')}** *(Tanggal: {t.get('Tanggal')})*")
                        st.write(f"**Instruksi Tutor:** {t.get('Instruksi')}")
                        if t.get('File_Offline'):
                            st.markdown(f"📎 **File / Modul Offline Sesi Ini:** [{t.get('File_Offline')}]({t.get('File_Offline')})")
                        st.markdown("---")
                else:
                    st.warning("Belum ada materi multi-mapel khusus yang diunggah untuk hari ini. Silakan kerjakan latihan kuis standar di bawah:")
            except:
                st.info("Memuat data ruang belajar...")

            st.markdown("---")
            st.subheader("📝 Kuis Online Interaktif")
            durasi_menit_kuis = 30 
            durasi_detik = durasi_menit_kuis * 60
            
            if "start_time" not in st.session_state:
                st.session_state.start_time = time.time()
                
            waktu_berjalan = time.time() - st.session_state.start_time
            sisa_waktu = int(durasi_detik - waktu_berjalan)
            
            if sisa_waktu > 0 and not st.session_state.get("kuis_submitted", False):
                menit = sisa_waktu // 60
                detik = sisa_waktu % 60
                st.warning(f"⏱️ **Sisa Waktu Kuis:** `{menit:02d}:{detik:02d}` Menit")
                
                with st.form("form_kuis_siswa"):
                    try:
                        ws_master = sheet.worksheet("Bank_Soal_Master")
                        all_soal = ws_master.get_all_records()
                        jenjang_s = st.session_state.siswa_jenjang
                        
                        if "SD" in jenjang_s or "TK" in jenjang_s:
                            soal_db = [s for s in all_soal if "IPAS" in str(s.get("Teks_Soal")) or "SD" in str(s.get("Bentuk_Soal"))]
                            if not soal_db:
                                soal_db = all_soal[:10]
                            topik_nama = "IPAS & Tematik Dasar SD"
                            mapel_nama = "IPAS"
                        else:
                            soal_db = [s for s in all_soal if "Matematika" in str(s.get("Teks_Soal")) or len(all_soal) <= 20]
                            if not soal_db:
                                soal_db = all_soal[:10]
                            topik_nama = "Matematika & Sains SMP/SMA"
                            mapel_nama = "Matematika"
                    except:
                        soal_db = []
                    
                    jawaban_user = {}
                    if soal_db:
                        for idx, s in enumerate(soal_db, 1):
                            bentuk_soal = str(s.get("Bentuk_Soal", "Pilihan Ganda")).strip()
                            st.markdown(f"**Soal No. {idx}** *({bentuk_soal})*")
                            st.write(s.get('Teks_Soal'))
                            
                            # Dukungan Soal Bergambar
                            if s.get('URL_Gambar'):
                                st.image(s.get('URL_Gambar'), caption="Ilustrasi Soal", width=300)
                                
                            opsi_raw = str(s.get('Opsi_Jawaban', ''))
                            
                            # Render berdasarkan ragam bentuk soal
                            if bentuk_soal == "Pilihan Ganda" or opsi_raw and opsi_raw != "nan":
                                opsi_list = [o.strip() for o in opsi_raw.split("|") if o.strip()]
                                jawaban_user[idx] = st.radio(f"Pilih Jawaban No {idx}:", opsi_list, key=f"soal_{idx}")
                                
                            elif bentuk_soal == "Pilihan Ganda Kompleks":
                                opsi_list = [o.strip() for o in opsi_raw.split("|") if o.strip()]
                                st.write("*(Pilih semua jawaban yang benar)*")
                                sub_ans = []
                                for o_item in opsi_list:
                                    if st.checkbox(o_item, key=f"kompleks_{idx}_{o_item}"):
                                        sub_ans.append(o_item)
                                jawaban_user[idx] = " | ".join(sub_ans)
                                
                            elif bentuk_soal == "Benar / Salah":
                                jawaban_user[idx] = st.radio(f"Tentukan Benar/Salah No {idx}:", ["Benar", "Salah"], key=f"bs_{idx}")
                                
                            elif bentuk_soal == "Menjodohkan":
                                jawaban_user[idx] = st.text_input(f"Tuliskan pasangan jawaban Menjodohkan No {idx}:", key=f"jodoh_{idx}")
                                
                            else: # Essay
                                jawaban_user[idx] = st.text_area(f"Jawaban Essay No {idx}:", key=f"essay_{idx}")
                                
                            st.markdown("---")
                    else:
                        st.info("Belum ada soal kuis online.")
                        
                    submitted = st.form_submit_button("🚀 Kirim Jawaban Kuis")
                    if submitted and soal_db:
                        total_soal = len(soal_db)
                        benar = 0
                        salah_no = []
                        
                        for idx, s in enumerate(soal_db, 1):
                            kunci_raw = str(s.get("Kunci_Jawaban", "")).strip().upper()
                            user_ans = str(jawaban_user.get(idx, "")).strip().upper()
                            
                            if user_ans.startswith(kunci_raw) or user_ans == kunci_raw:
                                benar += 1
                            else:
                                salah_no.append(idx)

                        skor_akhir = round((benar / total_soal) * 100) if total_soal > 0 else 100
                        detail_salah_str = f"Soal salah: No {', '.join(map(str, salah_no))}" if salah_no else "Semua Benar!"
                        
                        try:
                            try:
                                ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                            except:
                                ws_riwayat = sheet.add_worksheet(title="Riwayat_Latihan", rows="1000", cols="10")
                                ws_riwayat.append_row(["ID_Latihan", "Waktu_Selesai", "Nama_Siswa", "Mapel", "Topik_Kuis", "Skor", "Total_Soal", "Detail_Salah"])
                                
                            last_id = len(ws_riwayat.get_all_records()) + 1
                            ws_riwayat.append_row([
                                f"LAT-{last_id:03d}",
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                st.session_state.siswa_nama,
                                mapel_nama,
                                topik_nama,
                                skor_akhir,
                                total_soal,
                                detail_salah_str
                            ])
                        except Exception as ex_save:
                            st.error(f"Gagal menyimpan riwayat: {ex_save}")
                        
                        st.session_state.kuis_submitted = True
                        st.session_state.hasil_skor = skor_akhir
                        st.session_state.hasil_salah_no = salah_no
                        st.rerun()

            elif st.session_state.get("kuis_submitted", False):
                st.balloons()
                st.success(f"🎉 **Kuis Berhasil Dikirim!**")
                st.markdown(f"### 💯 Skor Kamu: `{st.session_state.get('hasil_skor', 0)} / 100`")
                salah_list = st.session_state.get('hasil_salah_no', [])
                if salah_list:
                    st.warning(f"📌 **Nomor yang Masih Salah:** Nomor **{', '.join(map(str, salah_list))}** (Diskusikan dengan Tutor saat les!)")
                else:
                    st.success("🌟 Luar biasa! Semua soal Berhasil dijawab dengan Benar!")
            else:
                st.error("⏰ Waktu Kuis Telah Habis!")
                
        with siswa_tab2:
            st.subheader(f"📈 Grafik Progress Nilai Ananda {st.session_state.siswa_nama}")
            data_grafik_siswa = []
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                for r in ws_r.get_all_records():
                    if str(r.get("Nama_Siswa")).strip().lower() == str(st.session_state.siswa_nama).strip().lower():
                        try:
                            val_skor = float(r.get("Skor", 0))
                            data_grafik_siswa.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": val_skor})
                        except:
                            pass
            except:
                pass
            
            if data_grafik_siswa:
                df_siswa = pd.DataFrame(data_grafik_siswa)
                st.line_chart(df_siswa.set_index("Tanggal")["Skor"])
            else:
                st.info("Belum ada grafik riwayat nilai.")

# ==========================================
# 2. MODUL TUTOR (DENGAN VALIDASI STATUS AKTIF & PERSIAPAN MULTI-MAPEL LENGKAP)
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
                    # Validasi ketat status tutor harus aktif
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
        tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs(["📝 Persiapan Multi-Mapel & Jurnal", "📊 Portofolio Sesi Siswa", "➕ Tambah Soal Master"])
        
        # TAB 1: PERSIAPAN MULTI-MAPEL, SOAL ONLINE/OFFLINE, CETAK FISIK & JURNAL
        with tutor_tab1:
            st.header("📖 Persiapan Sesi Pembelajaran & Materi Multi-Mapel")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            # Hanya ambil siswa yang aktif
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
                st.info("💡 Ketik nama siswa di atas untuk mulai menyiapkan materi multi-mapel, soal, dan jurnal.")
            
            if selected_siswa:
                st.markdown("---")
                st.subheader(f"📚 Konfigurasi Sesi Multi-Mapel untuk: **{selected_siswa}**")
                
                # 1. Pemilihan Multi-Mapel (2-3 Mapel per Pertemuan)
                mapel_pilihan_tutor = st.multiselect(
                    "Pilih Mapel yang Akan Dibahas Hari Ini (Bisa Lebih dari 1 dalam 1 Pertemuan):",
                    ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA (Fisika/Kimia/Biologi)", "Bahasa Indonesia", "PKN", "Olimpiade (OSN)"]
                )
                
                if mapel_pilihan_tutor:
                    st.success(f"✨ Sesi hari ini mencakup mapel: **{', '.join(mapel_pilihan_tutor)}**")
                    
                    with st.form("form_persiapan_materi"):
                        st.markdown("### 🛠️ Siapkan Tugas & Soal (Online & Offline Multi-File)")
                        
                        sumber_soal = st.selectbox("Pilih Sumber Soal Online:", [
                            "Ambil Otomatis dari Master Bank Soal (Spreadsheet)",
                            "Buat/Input Instruksi & Soal Manual untuk Sesi Ini"
                        ])
                        
                        instruksi_tutor = st.text_area("Instruksi / Catatan Pengerjaan untuk Siswa:", placeholder="Contoh: Kerjakan soal latihan online di akunmu dan pelajari file materi terlampir.")
                        
                        # Browse / Input File Offline dari Drive / File Manager (Mendukung Multi-File)
                        link_file_offline = st.text_area("Link File/Modul Offline (Drive / File Manager - Bisa lebih dari 1 link pisahkan dengan baris baru):", placeholder="https://drive.google.com/... (File Mapel 1)\nhttps://drive.google.com/... (File Mapel 2)")
                        
                        btn_simpan_tugas = st.form_submit_button("📤 Simpan & Kirim Materi ke Akun Siswa")
                        
                        if btn_simpan_tugas:
                            try:
                                try:
                                    ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                                except:
                                    ws_tugas = sheet.add_worksheet(title="Tugas_Sesi_Siswa", rows="1000", cols="10")
                                    ws_tugas.append_row(["Tanggal", "Nama_Siswa", "Mapel", "Instruksi", "File_Offline"])
                                    
                                for m_item in mapel_pilihan_tutor:
                                    ws_tugas.append_row([
                                        datetime.now().strftime("%Y-%m-%d"),
                                        selected_siswa,
                                        m_item,
                                        f"[{sumber_soal}] {instruksi_tutor}",
                                        link_file_offline
                                    ])
                                st.success(f"✅ Materi multi-mapel untuk {selected_siswa} berhasil dikirim dan otomatis tampil di akun siswa!")
                            except Exception as ex_t:
                                st.error(f"Gagal menyimpan tugas: {ex_t}")

                    # Mode Cetak Lembar Latihan Fisik (Backup jika anak tidak membawa gadget)
                    with st.expander("🖨️ Mode Cetak Lembar Latihan Fisik (Printer Epson)"):
                        st.write("Gunakan fitur ini untuk mencetak lembar soal langsung ke kertas jika siswa tidak membawa gadget.")
                        if st.button("🖨️ Cetak Lembar Soal Sekarang"):
                            st.markdown("""
                            <script>
                                window.print();
                            </script>
                            """, unsafe_allow_html=True)
                            st.success("Perintah cetak dikirim! Jika dialog cetak tidak muncul, silakan tekan `Ctrl + P` pada keyboard Anda.")

                st.markdown("---")
                # 2. PANEL KONTROL GAMES & POIN OLEH TUTOR
                st.subheader(f"🎮 Panel Kelola Games & Poin untuk: {selected_siswa}")
                with st.form("form_tambah_poin_tutor"):
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        jenis_game = st.selectbox("Jenis Modifikasi Games / Tantangan:", [
                            "Kuis Cepat Lisan (Berhitung/Sains)",
                            "Tantangan Logika / Teka-teki",
                            "Games Papan Tulis (Berebut Jawab)",
                            "Bonus Keaktifan Diskusi"
                        ])
                    with col_g2:
                        poin_tambahan = st.number_input("Jumlah Poin Reward:", min_value=5, max_value=50, value=10, step=5)
                        
                    catatan_game = st.text_input("Catatan Keberhasilan Siswa:", placeholder="Misal: Berhasil menjawab 3 soal tantangan perkalian dengan cepat")
                    btn_beri_poin = st.form_submit_button("➕ Tambahkan Poin ke Akun Siswa")
                    
                    if btn_beri_poin:
                        try:
                            for idx_s, row_s in enumerate(data_siswa_all, 2):
                                if str(row_s.get("Nama_Lengkap")).strip().lower() == selected_siswa.strip().lower():
                                    current_poin = int(row_s.get("Poin", 0)) if str(row_s.get("Poin", "")).isdigit() else 0
                                    new_poin = current_poin + int(poin_tambahan)
                                    col_p_idx = list(row_s.keys()).index("Poin") + 1 if "Poin" in row_s else 9
                                    ws_siswa.update_cell(idx_s, col_p_idx, new_poin)
                                    st.success(f"✅ Berhasil menambahkan **+{poin_tambahan} Poin** ({jenis_game}) untuk {selected_siswa}! Total Poin sekarang: {new_poin}")
                                    break
                        except Exception as ex_p:
                            st.error(f"Gagal memperbarui poin: {ex_p}")

                st.markdown("---")
                # 3. INPUT JURNAL BELAJAR SESI INI
                st.subheader(f"📝 Input Jurnal Belajar Sesi Ini ({selected_siswa})")
                with st.form("form_jurnal"):
                    tgl = st.date_input("Tanggal Mengajar", datetime.now())
                    mapel_utama = st.selectbox("Mata Pelajaran Utama Sesi Ini", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA (Fisika/Kimia/Biologi)", "Lainnya"])
                    materi = st.text_area("Materi & Pelajaran Hari Ini (Bisa ditulis beberapa mapel sekaligus)")
                    pencapaian = st.text_area("Pencapaian Belajar Siswa")
                    kendala = st.text_area("Celah / Kendala Belajar Baru")
                    tingkat_celah = st.select_slider("Tingkat Celah", options=["Rendah", "Sedang", "Tinggi"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        skor = st.text_input("Nilai / Skor Latihan Offline")
                        pr = st.text_input("Tugas / PR")
                    with col2:
                        foto_link = st.text_input("Link Foto Dokumentasi (Opsional)")
                    
                    if st.form_submit_button("💾 Simpan Jurnal & Catatan"):
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
                                pr,
                                foto_link,
                                skor
                            ])
                            if kendala.strip():
                                ws_celah = sheet.worksheet("Celah_Belajar")
                                last_id = len(ws_celah.get_all_records()) + 1
                                ws_celah.append_row([
                                    f"CLH-{last_id:03d}",
                                    tgl.strftime("%Y-%m-%d"),
                                    selected_siswa,
                                    mapel_utama,
                                    kendala,
                                    tingkat_celah,
                                    st.session_state.tutor_nama,
                                    "Dalam Proses"
                                ])
                            st.success("✅ Jurnal & Catatan Berhasil Disimpan!")
                        except Exception as ex:
                            st.error(f"Gagal: {ex}")

        # TAB 2: PORTOFOLIO TERKUNCI (AMAN DARI DATA RAHASIA TERBUKA SEMUA)
        with tutor_tab2:
            st.header("📊 Portofolio & Histori Sesi Siswa (Privasi Aman)")
            st.caption("Pilih nama siswa di bawah ini secara spesifik untuk melihat portofolio pribadinya saja.")
            
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            # Hanya tampilkan nama siswa aktif untuk dipilih secara spesifik
            list_nama_aktif = [s.get("Nama_Lengkap") for s in data_siswa_all if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            pilih_siswa_histori = st.selectbox("Pilih Nama Siswa:", ["-- Pilih Siswa --"] + list_nama_aktif)
            
            if pilih_siswa_histori != "-- Pilih Siswa --":
                st.subheader(f"📈 Grafik Perkembangan Nilai: {pilih_siswa_histori}")
                data_grafik = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == pilih_siswa_histori.strip().lower():
                            data_grafik.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": float(r.get("Skor", 0))})
                except:
                    pass

                try:
                    ws_j = sheet.worksheet("Form Responses 1")
                    for j in ws_j.get_all_records():
                        if str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower() == pilih_siswa_histori.strip().lower():
                            data_grafik.append({"Tanggal": str(j.get("Tanggal Mengajar", j.get("Tanggal", ""))), "Skor": float(j.get("Nilai/skor latihan", j.get("Skor", 0)) or 0)})
                except:
                    pass

                if data_grafik:
                    df_grafik = pd.DataFrame(data_grafik)
                    st.line_chart(df_grafik.set_index("Tanggal")["Skor"])
                else:
                    st.info("Belum ada data nilai untuk siswa ini.")

                st.markdown("---")
                st.subheader("📜 Histori Jurnal Mengajar Sebelumnya")
                try:
                    ws_j = sheet.worksheet("Form Responses 1")
                    jurnal_all = [j for j in ws_j.get_all_records() if str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower() == pilih_siswa_histori.strip().lower()]
                    for j in reversed(jurnal_all):
                        st.info(f"📅 **{j.get('Tanggal Mengajar', j.get('Tanggal', '-'))}** | Materi: {j.get('Materi dan Pelajaran Hari Ini', j.get('Materi', '-'))} | Skor: {j.get('Nilai/skor latihan', j.get('Skor', '-'))}")
                except:
                    pass

        # TAB 3: TAMBAH SOAL MASTER (MENDUKUNG BERBAGAI BENTUK SOAL & GAMBAR)
        with tutor_tab3:
            st.header("➕ Tambah Soal Baru ke Master Bank Soal (Lengkap & Bergambar)")
            with st.form("form_tambah_soal"):
                bentuk = st.selectbox("Bentuk Soal:", [
                    "Pilihan Ganda", 
                    "Pilihan Ganda Kompleks", 
                    "Benar / Salah", 
                    "Menjodohkan", 
                    "Essay"
                ])
                teks_soal = st.text_area("Teks Soal:")
                url_gambar = st.text_input("Link Gambar / Ilustrasi Soal (Opsional):", placeholder="https://... (Link gambar dari Drive/Imgur)")
                opsi = st.text_input("Opsi Jawaban (Pisahkan dengan | ):", placeholder="A. Jawaban 1 | B. Jawaban 2 | C. Jawaban 3 | D. Jawaban 4")
                kunci = st.text_input("Kunci Jawaban:", placeholder="Masukkan kunci (Misal: A, atau Benar, atau Pasangan)")
                
                if st.form_submit_button("Simpan Soal ke Bank Soal"):
                    try:
                        sheet.worksheet("Bank_Soal_Master").append_row([bentuk, teks_soal, url_gambar, opsi, kunci])
                        st.success("✅ Soal baru dengan ragam format berhasil disimpan ke database!")
                    except Exception as ex_bs:
                        st.error(f"Gagal menyimpan soal: {ex_bs}")

# ==========================================
# 3. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola Bimbel")
    pin_owner = st.text_input("PIN Pengelola:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Diizinkan 👋")
        tab1, tab2, tab3 = st.tabs(["🎁 Undian Hadiah Siswa (Poin ≥ 100)", "👥 Kelola Status Akun", "📚 Master Bank Soal"])
        
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
                st.dataframe(pd.DataFrame(peserta_undian))
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
            st.dataframe(pd.DataFrame(records_siswa)[["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]])
            
            with st.form("form_status"):
                pilih_nama = st.selectbox("Pilih Siswa:", [s.get("Nama_Lengkap") for s in records_siswa if s.get("Nama_Lengkap")])
                status_baru = st.selectbox("Status:", ["Aktif", "Nonaktif"])
                if st.form_submit_button("Update Status"):
                    cell = ws_siswa.find(pilih_nama)
                    col_idx = list(records_siswa[0].keys()).index("Status") + 1
                    ws_siswa.update_cell(cell.row, col_idx, status_baru)
                    st.success("Status berhasil diperbarui!")

        with tab3:
            st.dataframe(sheet.worksheet("Bank_Soal_Master").get_all_records())
    elif pin_owner:
        st.error("PIN Salah!")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua")
    nama_anak = st.text_input("Nama Putra/Putri:")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa = ws_siswa.get_all_records()
        ortu_found = False
        
        for row in data_siswa:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                # Validasi status aktif siswa
                if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                    st.error("🚫 Akun siswa ini sudah Nonaktif.")
                    break
                
                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(f"**Jenjang:** {row.get('Jenjang')} | **Koleksi Poin Undian Anak:** `{row.get('Poin', 0)} Poin`")
                st.markdown("---")
                
                ortu_tab1, ortu_tab2 = st.tabs(["📋 Sesi Belajar Terbaru", "📈 Grafik & Histori Lengkap"])
                
                with ortu_tab1:
                    laporan_list = []
                    try:
                        ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                        for r in ws_riwayat.get_all_records():
                            if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                laporan_list.append({
                                    'Tanggal': r.get('Waktu_Selesai', '-'),
                                    'Tutor': 'Kuis Online',
                                    'Materi': f"[{r.get('Mapel')}] {r.get('Topik_Kuis')}",
                                    'Skor': r.get('Skor', '-'),
                                    'Pencapaian': f"Selesai Kuis ({r.get('Total_Soal')} Soal)",
                                    'Kendala': r.get('Detail_Salah', '-')
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
                                    'Tutor': j.get('Nama Tutor', j.get('Nama TUtor', '-')),
                                    'Materi': j.get('Materi dan Pelajaran Hari Ini', j.get('Materi', '-')),
                                    'Skor': j.get('Nilai/skor latihan', j.get('Skor', '-')),
                                    'Pencapaian': j.get('Pencapaian Belajar', '-'),
                                    'Kendala': j.get('Kendala Belajar Anak', '-')
                                })
                    except:
                        pass

                    if laporan_list:
                        lap = laporan_list[-1]
                        st.write(f"📅 **Tanggal:** {lap.get('Tanggal')} | 📚 **Materi:** {lap.get('Materi')}")
                        st.write(f"💯 **Skor:** {lap.get('Skor')}")
                        st.info(f"**Pencapaian:** {lap.get('Pencapaian')}")
                        if lap.get('Kendala') and lap.get('Kendala') != "-":
                            st.warning(f"**Catatan/Kendala:** {lap.get('Kendala')}")
                    else:
                        st.info("Belum ada catatan sesi belajar.")

                with ortu_tab2:
                    st.subheader("📈 Grafik Nilai Pembelajaran")
                    data_g_ortu = []
                    try:
                        ws_r = sheet.worksheet("Riwayat_Latihan")
                        for r in ws_r.get_all_records():
                            if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                data_g_ortu.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": float(r.get("Skor", 0))})
                    except:
                        pass
                    
                    if data_g_ortu:
                        st.line_chart(pd.DataFrame(data_g_ortu).set_index("Tanggal")["Skor"])
                    else:
                        st.info("Belum ada data grafik.")
                break
        if not ortu_found:
            st.error("Nama atau PIN Salah!")
