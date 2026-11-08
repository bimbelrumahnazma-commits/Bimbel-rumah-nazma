import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="Portal Bimbel Rumah Nazma", layout="wide", page_icon="✏️")

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
st.title("✏️ Portal Bimbel Rumah Nazma")
st.caption("Sistem Manajemen Pembelajaran & Diari Berkelanjutan")

# --- PILIHAN PERAN LOGIN ---
peran = st.selectbox(
    "Pilih Akses Login:",
    ["🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "🎓 Siswa", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL TUTOR / PENGAJAR (KAK RIFKY / KAK MEI)
# ==========================================
if peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar")
    
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
            for row in data:
                if str(row.get("Username")).strip().lower() == username.strip().lower() and str(row.get("PIN_Password")).strip() == pin.strip():
                    user_found = True
                    st.session_state.tutor_logged_in = True
                    st.session_state.tutor_nama = row.get("Nama_Pengguna")
                    st.rerun()
                    break
            if not user_found:
                st.error("Username atau PIN Pengajar salah!")
    else:
        st.success(f"👨‍🏫 **Tutor Aktif:** {st.session_state.tutor_nama}")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.rerun()
            
        st.markdown("---")
        st.header("📖 Diari Kelemahan & Jurnal Mengajar Sesi Hari Ini")
        
        st.subheader("🔍 Cari Nama Siswa yang Diajar Hari Ini")
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa_all = ws_siswa.get_all_records()
        
        search_query = st.text_input("Ketik Nama / Panggilan Siswa (misal: Aisyah / Adeva):").strip().lower()
        selected_siswa = None
        
        if search_query:
            hasil_pencarian = [
                s.get("Nama_Lengkap") for s in data_siswa_all 
                if search_query in str(s.get("Nama_Lengkap")).strip().lower()
            ]
            
            if hasil_pencarian:
                pilihan = st.selectbox("Pilih Siswa dari Hasil Pencarian:", ["-- Pilih Siswa --"] + hasil_pencarian)
                if pilihan != "-- Pilih Siswa --":
                    selected_siswa = pilihan
            else:
                st.warning(f"Siswa dengan nama '{search_query}' tidak ditemukan di Data Siswa.")
        else:
            st.info("💡 Ketik nama siswa di kolom pencarian di atas untuk melihat catatan kelemahan & menginput jurnal hari ini.")
        
        if selected_siswa:
            st.markdown("---")
            st.subheader(f"🔍 Rekam Jejak Kelemahan Ananda: {selected_siswa}")
            
            try:
                ws_celah = sheet.worksheet("Celah_Belajar")
                celah_data = ws_celah.get_all_records()
                celah_siswa = [c for c in celah_data if str(c.get("Nama_Siswa")).strip().lower() == selected_siswa.strip().lower()]
                
                if celah_siswa:
                    st.warning("⚠️ **PERHATIAN UNTUK TUTOR HARI INI (Catatan Sesi Sebelumnya):**")
                    for idx, c in enumerate(reversed(celah_siswa[-3:]), 1):
                        st.markdown(f"""
                        * **{c.get('Tanggal')}** | Mapel: **{c.get('Mapel')}** | Oleh: **{c.get('Tutor_Pengajar')}**
                          * 📌 **Topik Belum Paham:** {c.get('Topik_Belum_Paham')}
                          * 🚨 **Tingkat Celah:** {c.get('Tingkat_Celah')} | Status: `{c.get('Status_Tuntas')}`
                        """)
                else:
                    st.info("ℹ️ Belum ada catatan celah belajar khusus untuk siswa ini.")
            except Exception as e:
                st.write("Belum dapat memuat histori celah belajar.")
            
            st.markdown("---")
            st.subheader(f"📝 Input Jurnal Belajar Sesi Hari Ini ({selected_siswa})")
            
            with st.form("form_jurnal"):
                tgl = st.date_input("Tanggal Mengajar", datetime.now())
                mapel = st.selectbox("Mata Pelajaran", ["Matematika", "IPA (Fisika/Kimia/Biologi)", "Bahasa Inggris", "Tematik / Calistung", "Lainnya"])
                materi = st.text_area("Materi & Pelajaran Hari Ini", placeholder="Misal: Penjumlahan pecahan beda penyebut & latihan bangun datar")
                pencapaian = st.text_area("Pencapaian Belajar Siswa", placeholder="Misal: Sudah paham menyamakan penyebut, perkalian masih lancar")
                kendala = st.text_area("Celah / Kendala Belajar Baru (Untuk Tutor Berikutnya)", placeholder="Misal: Masih sering keliru saat mengubah pecahan campuran ke biasa")
                tingkat_celah = st.select_slider("Tingkat Celah Kelemahan Baru", options=["Rendah", "Sedang", "Tinggi"])
                
                col1, col2 = st.columns(2)
                with col1:
                    skor = st.text_input("Nilai / Skor Latihan Offline", placeholder="Misal: 85")
                    pr = st.text_input("Tugas / PR (Offline/Online)", placeholder="Misal: Mengerjakan 5 soal latihan pecahan di buku")
                with col2:
                    foto_link = st.text_input("Link Foto Dokumentasi (Google Drive)", placeholder="https://drive.google.com/...")
                
                submitted = st.form_submit_button("💾 Simpan Jurnal & Rekam Kelemahan")
                
                if submitted:
                    try:
                        ws_jurnal = sheet.worksheet("Form Responses 1")
                        ws_jurnal.append_row([
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            tgl.strftime("%d/%m/%Y"),
                            st.session_state.tutor_nama,
                            "Hadir",
                            selected_siswa,
                            f"[{mapel}] {materi}",
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
                                mapel,
                                kendala,
                                tingkat_celah,
                                st.session_state.tutor_nama,
                                "Dalam Proses"
                            ])
                        
                        st.success("✅ Jurnal & Celah Belajar Berhasil Disimpan!")
                    except Exception as ex:
                        st.error(f"Gagal menyimpan data: {ex}")

# ==========================================
# 2. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Kurikulum & Perencanaan (Mbak Fatimah)")
    pin_owner = st.text_input("Masukkan PIN Akses Pengelola:", type="password")
    
    # PIN Pengelola default
    if pin_owner == "1605":
        st.success("Akses Pengelola Diizinkan 👋")
        tab1, tab2 = st.tabs(["📅 Persiapan Jadwal & Soal Besok", "📚 Bank Topik Soal Master"])
        
        ws_siswa = sheet.worksheet("Data_Siswa")
        all_siswa = ws_siswa.get_all_records()
        
        with tab1:
            st.markdown("### 🌙 Setting Soal & PR Siswa untuk Besok")
            pilih_siswa = st.selectbox("Pilih Siswa Target:", ["-- Pilih Siswa --"] + [s.get("Nama_Lengkap") for s in all_siswa])
            
            if pilih_siswa != "-- Pilih Siswa --":
                # Ambil celah terakhir
                try:
                    ws_celah = sheet.worksheet("Celah_Belajar")
                    celah_data = ws_celah.get_all_records()
                    celah_siswa = [c for c in celah_data if str(c.get("Nama_Siswa")).strip().lower() == pilih_siswa.strip().lower()]
                    
                    if celah_siswa:
                        st.info(f"📌 **Celah Belajar Terakhir Ananda {pilih_siswa}:** {celah_siswa[-1].get('Topik_Belum_Paham')}")
                except:
                    pass
                
                # Form Persiapan Soal
                ws_topik = sheet.worksheet("Bank_Topik_Soal")
                topik_list = [t.get("Nama_Topik") for t in ws_topik.get_all_records()]
                
                selected_topik = st.selectbox("Pilih Topik Soal Berkesinambungan:", topik_list)
                jenis_soal = st.radio("Media Soal Besok:", ["Offline (Cetak/Latihan Buku)", "Online (PR Malam Siswa)"])
                catatan_soal = st.text_area("Instruksi / Detail Soal untuk Tutor/Siswa:", placeholder="Misal: Kerjakan 5 soal perkalian bersusun & pemanasan pecahan campuran")
                
                if st.button("📌 Plot Jadwal & Soal untuk Besok"):
                    st.success(f"✅ Soal '{selected_topik}' ({jenis_soal}) berhasil di-plot untuk ananda {pilih_siswa}!")
        
        with tab2:
            st.markdown("### 📚 Daftar Master Bank Topik Soal Bimbel")
            try:
                ws_topik = sheet.worksheet("Bank_Topik_Soal")
                st.dataframe(ws_topik.get_all_records())
            except Exception as e:
                st.write("Gagal memuat bank topik soal.")
    elif pin_owner:
        st.error("PIN Pengelola Salah!")

# ==========================================
# 3. MODUL SISWA
# ==========================================
elif peran == "🎓 Siswa":
    st.subheader("🎓 Login Siswa")
    nama_siswa = st.text_input("Nama Siswa (misal: Aisyah / Adeva):")
    pin_siswa = st.text_input("PIN Siswa (4 Angka):", type="password")
    
    if st.button("Masuk Siswa"):
        ws = sheet.worksheet("Data_Siswa")
        data = ws.get_all_records()
        siswa_found = False
        for row in data:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_siswa.strip().lower() and str(row.get("PIN_Siswa")).strip() == pin_siswa.strip():
                siswa_found = True
                st.success(f"Halo {row.get('Nama_Lengkap')}! Selamat belajar.")
                st.write(f"**Kelas:** {row.get('Jenjang')} - Kelas {row.get('Kelas')}")
                st.write(f"**Mapel:** {row.get('Mapel_Diambil')}")
                st.info("Menu Kuis & PR Online Siap Dikembangkan di Tahap 3 (Anti-Cheat).")
                break
        if not siswa_found:
            st.error("Nama Siswa atau PIN Siswa salah!")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua")
    nama_anak = st.text_input("Nama Putra/Putri (misal: Aisyah / Adeva / Sherin):")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa = ws_siswa.get_all_records()
        ortu_found = False
        
        for row in data_siswa:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari Ananda **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(f"**Jenjang:** {row.get('Jenjang')} (Kelas {row.get('Kelas')}) | **Mapel:** {row.get('Mapel_Diambil')}")
                st.markdown("---")
                st.subheader("📋 Laporan Hasil Belajar Sesi Terbaru")
                
                try:
                    ws_jurnal = sheet.worksheet("Form Responses 1")
                    data_jurnal = ws_jurnal.get_all_records()
                    
                    laporan_anak = [
                        j for j in data_jurnal 
                        if str(j.get("Nama Siswa", "")).strip().lower() == nama_anak.strip().lower()
                    ]
                    
                    if laporan_anak:
                        laporan_terbaru = laporan_anak[-1]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"📅 **Tanggal:** {laporan_terbaru.get('Tanggal Mengajar', '-')}")
                            st.write(f"👨‍🏫 **Tutor Pengajar:** {laporan_terbaru.get('Nama TUtor', '-')}")
                            st.write(f"📚 **Materi & Mapel:** {laporan_terbaru.get('Materi dan Pelajaran Hari Ini', '-')}")
                        with col2:
                            st.write(f"💯 **Nilai / Skor Latihan:** {laporan_terbaru.get('Nilai/skor latihan', '-')}")
                            st.write(f"📝 **PR / Tugas Online:** {laporan_terbaru.get('tugas & Latihan (PR)', '-')}")
                        
                        st.markdown("**🌟 Pencapaian Belajar:**")
                        st.info(laporan_terbaru.get("Pencapaian Belajar", "-"))
                        
                        if laporan_terbaru.get("Kendala Belajar Anak"):
                            st.markdown("**💡 Catatan / Kendala Belajar:**")
                            st.warning(laporan_terbaru.get("Kendala Belajar Anak"))
                            
                        foto_url = str(laporan_terbaru.get("Dokumentasi/ Foto hasil Belajar", ""))
                        if foto_url and "drive.google.com" in foto_url:
                            st.markdown("**📷 Foto Dokumentasi Hasil Belajar:**")
                            urls = [u.strip() for u in foto_url.split(",") if u.strip()]
                            for idx, u in enumerate(urls, 1):
                                st.markdown(f"👉 [Klik di sini untuk melihat Foto Dokumentasi {idx}]({u})")
                    else:
                        st.info("Belum ada catatan sesi belajar untuk Ananda.")
                except Exception as ex:
                    st.warning("Data detail sesi belum tersedia di jurnal.")
                break
                
        if not ortu_found:
            st.error("Nama Putra/Putri atau PIN Orang Tua salah!")
