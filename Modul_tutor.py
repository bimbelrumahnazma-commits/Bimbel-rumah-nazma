import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Portal Bimbel Rumah Nazma", layout="centered", page_icon="✏️")

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
    # Menghubungkan ke Google Sheets Bimbel
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/17JI1x966HfVG4YpfzCz_bssBwOmUTIJFbRutl0qyIZE/edit")
except Exception as e:
    st.error(f"Gagal terhubung ke Google Sheets: {e}")
    st.stop()

# --- HEADER APLIKASI ---
st.title("✏️ Portal Bimbel Rumah Nazma")
st.caption("Sistem Log & Pemantauan Belajar Siswa")

# --- PILIHAN PERAN LOGIN ---
peran = st.selectbox(
    "Pilih Akses Login:",
    ["🔒 Pengajar / Tutor", "🎓 Siswa", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# --- MENU LOGIN PENGAJAR ---
if peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar")
    username = st.text_input("Username Pengajar (misal: mei / rifky):")
    pin = st.text_input("PIN / Password:", type="password")
    
    if st.button("Masuk Pengajar"):
        ws = sheet.worksheet("Akun_Pengguna")
        data = ws.get_all_records()
        user_found = False
        for row in data:
            if str(row.get("Username")).strip().lower() == username.strip().lower() and str(row.get("PIN_Password")).strip() == pin.strip():
                user_found = True
                nama = row.get("Nama_Pengguna")
                st.success(f"Selamat datang, {nama}!")
                st.info("Fitur Input Celah Belajar & Jurnal Pengajar siap digunakan.")
                break
        if not user_found:
            st.error("Username atau PIN Pengajar salah!")

# --- MENU LOGIN SISWA ---
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
                st.info("Menu Bank Soal & Riwayat Kuis Latihan Siswa.")
                break
        if not siswa_found:
            st.error("Nama Siswa atau PIN Siswa salah!")

# --- MENU LOGIN ORANG TUA ---
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Login Orang Tua")
    nama_anak = st.text_input("Nama Putra/Putri (misal: Aisyah / Adeva):")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws = sheet.worksheet("Data_Siswa")
        data = ws.get_all_records()
        ortu_found = False
        for row in data:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari Ananda {row.get('Nama_Lengkap')}.")
                st.info("Laporan Grafik Perkembangan Belajar & Celah Belajar Ananda.")
                break
        if not ortu_found:
            st.error("Nama Putra/Putri atau PIN Orang Tua salah!")
