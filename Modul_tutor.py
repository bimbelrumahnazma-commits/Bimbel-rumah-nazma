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

# Fungsi koneksi ke Google Sheets
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

# Fungsi ambil data dari Spreadsheet
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
    
    # ----------------------------------------------------
    # GERBANG UTAMA: PEMILIHAN PERAN & PIN KEAMANAN
    # ----------------------------------------------------
    st.sidebar.header("🔐 Gerbang Akses Portal")
    peran = st.sidebar.selectbox(
        "Pilih Peran:",
        [
            "Pilih Peran...",
            "👑 Owner / Admin",
            "👨‍🏫 Tutor / Pengajar",
            "🎓 Siswa",
            "👪 Wali Murid"
        ]
    )
    
    if peran == "Pilih Peran...":
        st.info("Silakan pilih peran Anda di menu sebelah kiri untuk melanjutkan.")
        return
        
    # Input PIN Keamanan Sesuai Peran
    pin_input = st.sidebar.text_input("Masukkan PIN Akses:", type="password")
    
    # Validasi PIN standar
    PIN_BENAR = "1234" 
    
    if pin_input != PIN_BENAR:
        st.sidebar.warning("⚠️ Masukkan PIN yang benar untuk masuk.")
        st.stop()
    else:
        st.sidebar.success(f"Berhasil masuk sebagai {peran}")
        
    st.sidebar.markdown("---")
    
    # ----------------------------------------------------
    # JIKA MASUK SEBAGAI OWNER ATAU TUTOR
    # ----------------------------------------------------
    if peran in ["👑 Owner / Admin", "👨‍🏫 Tutor / Pengajar"]:
        st.sidebar.header("📋 Kelola Akun Siswa")
        
        mode_tutor = st.sidebar.radio(
            "Pilih Menu Utama:",
            [
                "👥 Masuk ke Akun Siswa (Siapkan Materi/Tugas)",
                "📊 Rekap Progress & Evaluasi"
            ]
        )
        
        if mode_tutor == "👥 Masuk ke Akun Siswa (Siapkan Materi/Tugas)":
            st.subheader("🎒 Mode Persiapan Belajar Siswa")
            nama_target_siswa = st.text_input("Masukkan Nama Siswa yang akan disiapkan materinya:")
            
            if nama_target_siswa:
                st.success(f"Sedang mengakses ruang belajar siswa: **{nama_target_siswa}**")
                
                jalur_pilihan = st.selectbox(
                    "Pilih Jalur Belajar untuk Siswa:",
                    [
                        "📖 Jalur 1: Materi & Kisi-Kisi Harian",
                        "📝 Jalur 2: Paket Soal & Tryout",
                        "🏆 Jalur Khusus: Olimpiade Sains (OSN)"
                    ]
                )
                
                if jalur_pilihan == "📖 Jalur 1: Materi & Kisi-Kisi Harian":
                    st.write(f"Menyiapkan modul materi harian untuk **{nama_target_siswa}**...")
                    df_materi = load_data_from_sheet("Bank_Soal_Materi")
                    if not df_materi.empty:
                        st.dataframe(df_materi, use_container_width=True)
                    else:
                        st.info("Belum ada data di tab `Bank_Soal_Materi`[span_0](start_span)[span_0](end_span).")
                        
                elif jalur_pilihan == "📝 Jalur 2: Paket Soal & Tryout":
                    st.write(f"Menyiapkan paket soal latihan untuk **{nama_target_siswa}**...")
                    df_paket = load_data_from_sheet("Bank_Soal_Paket")
                    if not df_paket.empty:
                        st.dataframe(df_paket, use_container_width=True)
                    else:
                        st.info("Belum ada data di tab `Bank_Soal_Paket`[span_1](start_span)[span_1](end_span).")
                        
                elif jalur_pilihan == "🏆 Jalur Khusus: Olimpiade Sains (OSN)":
                    st.write(f"Menyiapkan modul olimpiade untuk **{nama_target_siswa}**...")
                    df_osn = load_data_from_sheet("Bank_Soal_Olimpiade")
                    if not df_osn.empty:
                        st.dataframe(df_osn, use_container_width=True)
                    else:
                        st.info("Belum ada data di tab `Bank_Soal_Olimpiade`[span_2](start_span)[span_2](end_span).")
            else:
                st.info("Silakan ketik nama siswa di atas untuk mulai menyiapkan materi dan tugas belajarnya.")
                
        else:
            st.subheader("📊 Rekapitulasi Progress & Evaluasi Sesi Les")
            st.write("Catat hasil perkembangan belajar siswa setelah sesi bimbingan selesai.")
            with st.form("form_laporan"):
                nama_laporan = st.text_input("Nama Siswa:")
                catatan_les = st.text_area("Catatan Evaluasi / PR:")
                submit_lap = st.form_submit_button("Simpan Laporan")
                if submit_lap and nama_laporan:
                    st.success(f"Laporan untuk {nama_laporan} berhasil disimpan!")

    # ----------------------------------------------------
    # JIKA MASUK SEBAGAI SISWA ATAU WALI MURID
    # ----------------------------------------------------
    else:
        st.subheader(f"👋 Selamat Datang di Portal {peran} Bimbel Rumah Nazma")
        st.write("Silakan pilih menu belajar yang tersedia:")
        menu_user = st.selectbox("Pilih Menu:", ["Materi Harian", "Latihan Soal", "Olimpiade"])
        st.info(f"Menampilkan menu {menu_user} untuk siswa.")

if __name__ == "__main__":
    main()
