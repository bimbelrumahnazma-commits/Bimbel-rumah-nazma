import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# Konfigurasi halaman
st.set_page_config(
    page_title="Portal Bimbel Rumah Nazma",
    page_icon="📚",
    layout="wide"
)

# Fungsi untuk menghubungkan ke Google Sheets
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# Fungsi untuk mengambil data dari tab tertentu
def load_data_from_sheet(sheet_name):
    try:
        client = init_connection()
        spreadsheet = client.open("Data_Bimbel_Rumah_Nazma_Rapi")
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def main():
    st.title("📚 Portal Pembelajaran Bimbel Rumah Nazma")
    st.markdown("---")
    
    # Sidebar untuk Menu Navigasi Utama
    st.sidebar.header("Navigasi Portal")
    menu_pilihan = st.sidebar.selectbox(
        "Pilih Jalur Belajar:",
        [
            "🏠 Beranda Utama",
            "📖 Jalur 1: Materi & Kisi-Kisi Harian",
            "📝 Jalur 2: Paket Soal & Tryout Full",
            "🏆 Jalur Khusus: Olimpiade Sains (OSN)"
        ]
    )
    
    if menu_pilihan == "🏠 Beranda Utama":
        st.subheader("Selamat Datang di Portal Resmi Bimbel Rumah Nazma!")
        st.write("""
        Portal ini dirancang khusus untuk mendukung kegiatan belajar siswa secara terstruktur.
        Silakan pilih jalur belajar di menu sebelah kiri untuk mulai mengakses materi harian, 
        latihan paket soal, tryout berstandar skala nilai asli, hingga pembinaan olimpiade.
        """)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**Jalur 1**\nFokus penguasaan konsep dasar per bab & materi harian sekolah.")
        with col2:
            st.success("**Jalur 2**\nSimulasi paket latihan & tryout full dengan skala nilai asli (TKA, TOEFL, SKD).")
        with col3:
            st.warning("**Olimpiade (OSN)**\nPembinaan soal penalaran tingkat tinggi (SD - SMA) lengkap dengan pembahasannya.")
            
    elif menu_pilihan == "📖 Jalur 1: Materi & Kisi-Kisi Harian":
        st.subheader("📖 Jalur 1: Penguasaan Materi & Kisi-Kisi Per Bab")
        jenjang = st.selectbox("Pilih Jenjang:", ["PAUD / TK", "Sekolah Dasar (SD)", "Sekolah Menengah Pertama (SMP)", "Sekolah Menengah Atas (SMA)"])
        mapel = st.text_input("Masukkan Mata Pelajaran:")
        
        df_materi = load_data_from_sheet("Bank_Soal_Materi")
        if not df_materi.empty:
            st.success("Database Bank Soal Materi berhasil dimuat!")
            st.dataframe(df_materi.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Materi`. Silakan isi soal melalui Google Sheets.")
        
    elif menu_pilihan == "📝 Jalur 2: Paket Soal & Tryout Full":
        st.subheader("📝 Jalur 2: Latihan Paket & Simulasi Ujian")
        kategori_ujian = st.selectbox("Pilih Program Ujian:", ["TKA (Tes Kemampuan Akademik)", "TOEFL", "SKD CPNS / Kedinasan", "UTBK / Ujian Mandiri"])
        nomor_paket = st.selectbox("Pilih Sesi Latihan:", ["Paket 1", "Paket 2", "Paket 3", "Paket 4", "Paket 5", "Tryout Full (Skala Asli)"])
        
        df_paket = load_data_from_sheet("Bank_Soal_Paket")
        if not df_paket.empty:
            st.success("Database Bank Soal Paket berhasil dimuat!")
            st.dataframe(df_paket.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Paket`. Silakan isi soal melalui Google Sheets.")
        
    elif menu_pilihan == "🏆 Jalur Khusus: Olimpiade Sains (OSN)":
        st.subheader("🏆 Pembinaan Olimpiade Sains Nasional (OSN)")
        jenjang_osn = st.selectbox("Pilih Jenjang Olimpiade:", ["SD", "SMP", "SMA"])
        bidang_osn = st.selectbox("Pilih Bidang Sains:", ["Matematika", "Fisika", "Kimia", "Biologi", "Astronomi", "Ekonomi"])
        
        df_olimpiade = load_data_from_sheet("Bank_Soal_Olimpiade")
        if not df_olimpiade.empty:
            st.success("Database Bank Soal Olimpiade berhasil dimuat!")
            st.dataframe(df_olimpiade.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Olimpiade`. Silakan isi soal melalui Google Sheets.")

if __name__ == "__main__":
    main()
