import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- SETTING HALAMAN ---
st.set_page_config(page_title="Input Celah Belajar - Bimbel Rumah Nazma", page_icon="✏️", layout="centered")

# --- KONEKSI DATABASE GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    url_db = "https://docs.google.com/spreadsheets/d/17JI1x966HfVG4YpfzCz_bssBwOmUTIJFbRutl0qyIZE/edit?usp=drivesdk"
    return client.open_by_url(url_db)

sheet = init_connection()

# --- SISTEM LOGIN TUTOR ---
st.title("✏️ Portal Pengajar Bimbel Rumah Nazma")
st.write("Pencatatan Celah Belajar & Diagnostik Sesi Les Offline")

if "user_logged_in" not in st.session_state:
    st.session_state.user_logged_in = False
    st.session_state.user_data = None

if not st.session_state.user_logged_in:
    st.subheader("🔒 Login Pengajar")
    username_input = st.text_input("Username:")
    pin_input = st.text_input("PIN / Password:", type="password")
    
    if st.button("Masuk"):
        sheet_akun = sheet.worksheet("Akun_Pengguna")
        data_akun = sheet_akun.get_all_records()
        
        user_found = False
        for user in data_akun:
            if str(user['Username']).strip() == username_input.strip() and str(user['PIN_Password']).strip() == pin_input.strip():
                st.session_state.user_logged_in = True
                st.session_state.user_data = user
                user_found = True
                st.rerun()
                break
                
        if not user_found:
            st.error("Username atau PIN salah. Silakan coba lagi.")

else:
    user = st.session_state.user_data
    st.success(f"Selamat bertugas, **{user['Nama_Pengguna']}** ({user['Level_Akses']}) 👋")
    
    if st.button("Keluar / Logout"):
        st.session_state.user_logged_in = False
        st.session_state.user_data = None
        st.rerun()

    st.markdown("---")

    # --- FORM INPUT CELAH BELAJAR ---
    st.subheader("📝 Form Diagnostik Pertemuan Offline")

    sheet_siswa = sheet.worksheet("Data_Siswa")
    data_siswa = sheet_siswa.get_all_records()
    daftar_nama_siswa = [s['Nama_Lengkap'] for s in data_siswa if s['Status'] == 'Aktif']

    with st.form(key="form_celah_belajar"):
        tanggal = st.date_input("Tanggal Les:", datetime.date.today())
        nama_siswa = st.selectbox("Nama Siswa:", daftar_nama_siswa)
        mapel = st.selectbox("Mata Pelajaran:", ["Matematika", "IPA", "Fisika", "Kimia", "Bahasa Inggris", "Tematik/Calistung"])
        topik_belum_paham = st.text_area("Topik/Materi yang Belum Dipahami (Celah Belajar):", 
                                        placeholder="Contoh: Perkalian bersusun 3 angka, Konversi desimal ke pecahan")
        tingkat_celah = st.select_slider("Tingkat Hambatan:", options=["Rendah", "Sedang", "Tinggi"])
        status_tuntas = st.selectbox("Status Evaluasi:", ["Dalam Proses", "Perlu Remedial", "Selesai"])
        
        submit_button = st.form_submit_button(label="💾 Simpan Catatan Celah Belajar")

    if submit_button:
        if not topik_belum_paham.strip():
            st.warning("Mohon isi topik yang belum dipahami siswa.")
        else:
            sheet_celah = sheet.worksheet("Celah_Belajar")
            semua_catatan = sheet_celah.get_all_records()
            id_baru = f"CLH-{len(semua_catatan) + 1:03d}"
            
            baris_baru = [
                id_baru,
                str(tanggal),
                nama_siswa,
                mapel,
                topik_belum_paham,
                tingkat_celah,
                user['Nama_Pengguna'],
                status_tuntas
            ]
            
            sheet_celah.append_row(baris_baru)
            st.balloons()
            st.success(f"Catatan celah belajar untuk **{nama_siswa}** berhasil disimpan ke Google Sheets!")

    if user['Level_Akses'] == 'Tutor 1':
        st.markdown("---")
        st.subheader("📊 Rekap Seluruh Celah Belajar (Akses Tutor 1)")
        sheet_celah = sheet.worksheet("Celah_Belajar")
        st.dataframe(sheet_celah.get_all_records())
