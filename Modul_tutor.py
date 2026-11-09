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
    
    st.sidebar.header("📋 Menu Sesi Les")
    nama_siswa = st.sidebar.text_input("Nama Siswa:")
    
    menu_pilihan = st.sidebar.selectbox(
        "Pilih Jalur Belajar:",
        [
            "🏠 Beranda Utama",
            "📖 Jalur 1: Materi & Kisi-Kisi Harian",
            "📝 Jalur 2: Paket Soal & Tryout Full",
            "🏆 Jalur Khusus: Olimpiade Sains (OSN)",
            "📊 Input Evaluasi Hasil Les"
        ]
    )
    
    if menu_pilihan == "🏠 Beranda Utama":
        st.subheader("Selamat Datang di Portal Resmi Bimbel Rumah Nazma!")
        st.write("""
        Portal ini dirancang untuk mengelola materi, bank soal, serta rekapan evaluasi 
        hasil belajar siswa secara terstruktur dan terhubung langsung ke Google Sheets.
        """)
        
    elif menu_pilihan == "📖 Jalur 1: Materi & Kisi-Kisi Harian":
        st.subheader("📖 Jalur 1: Penguasaan Materi & Kisi-Kisi Per Bab")
        jenjang = st.selectbox("Pilih Jenjang:", ["PAUD / TK", "Sekolah Dasar (SD)", "Sekolah Menengah Pertama (SMP)", "Sekolah Menengah Atas (SMA)"])
        mapel = st.text_input("Masukkan Mata Pelajaran:")
        
        df_materi = load_data_from_sheet("Bank_Soal_Materi")
        if not df_materi.empty:
            st.success("Database Bank Soal Materi berhasil dimuat!")
            st.dataframe(df_materi.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Materi`[span_0](start_span)[span_0](end_span).")
        
    elif menu_pilihan == "📝 Jalur 2: Paket Soal & Tryout Full":
        st.subheader("📝 Jalur 2: Latihan Paket & Simulasi Ujian")
        kategori_ujian = st.selectbox("Pilih Program Ujian:", ["TKA (Tes Kemampuan Akademik)", "TOEFL", "SKD CPNS / Kedinasan", "UTBK / Ujian Mandiri"])
        nomor_paket = st.selectbox("Pilih Sesi Latihan:", ["Paket 1", "Paket 2", "Paket 3", "Paket 4", "Paket 5", "Tryout Full (Skala Asli)"])
        
        df_paket = load_data_from_sheet("Bank_Soal_Paket")
        if not df_paket.empty:
            st.success("Database Bank Soal Paket berhasil dimuat!")
            st.dataframe(df_paket.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Paket`[span_1](start_span)[span_1](end_span).")
        
    elif menu_pilihan == "🏆 Jalur Khusus: Olimpiade Sains (OSN)":
        st.subheader("🏆 Pembinaan Olimpiade Sains Nasional (OSN)")
        jenjang_osn = st.selectbox("Pilih Jenjang Olimpiade:", ["SD", "SMP", "SMA"])
        bidang_osn = st.selectbox("Pilih Bidang Sains:", ["Matematika", "Fisika", "Kimia", "Biologi", "Astronomi", "Ekonomi"])
        
        df_olimpiade = load_data_from_sheet("Bank_Soal_Olimpiade")
        if not df_olimpiade.empty:
            st.success("Database Bank Soal Olimpiade berhasil dimuat!")
            st.dataframe(df_olimpiade.head())
        else:
            st.info("Belum ada data soal di tab `Bank_Soal_Olimpiade`[span_2](start_span)[span_2](end_span).")
            
    elif menu_pilihan == "📊 Input Evaluasi Hasil Les":
        st.subheader("📊 Form Rekapitulasi Sesi Setelah Les")
        st.write("Gunakan form di bawah ini untuk mencatat hasil pencapaian belajar siswa agar tersimpan aman.")
        
        with st.form("form_evaluasi"):
            input_nama = st.text_input("Nama Siswa:", value=nama_siswa)
            input_kategori = st.selectbox("Kategori Belajar:", ["Jalur 1 - Materi", "Jalur 2 - Paket/Tryout", "Olimpiade (OSN)"])
            input_skor = st.number_input("Perolehan Skor / Nilai:", min_value=0, max_value=100, value=0)
            input_catatan = st.text_area("Catatan Evaluasi / Kendala Siswa:")
            
            submitted = st.form_submit_button("Simpan Data ke Spreadsheet")
            if submitted:
                if input_nama:
                    try:
                        client = init_connection()
                        spreadsheet = client.open("Data_Bimbel_Rumah_Nazma_Rapi")
                        # Memastikan atau menggunakan tab rekap (bisa disesuaikan namanya)
                        worksheet = spreadsheet.worksheet("Data_Siswa")
                        worksheet.append_row([input_nama, input_kategori, input_skor, input_catatan])
                        st.success(f"Data evaluasi untuk {input_nama} berhasil disimpan ke Spreadsheet!")
                    except Exception as e:
                        st.error(f"Gagal menyimpan data: {e}")
                else:
                    st.warning("Mohon isi nama siswa terlebih dahulu.")

if __name__ == "__main__":
    main()
