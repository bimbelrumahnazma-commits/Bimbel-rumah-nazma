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

# Fungsi ambil data berdasarkan tab
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
    # 1. GERBANG PEMILIHAN PERAN (ROLE) DI AWAL (SIDEBAR)
    # ----------------------------------------------------
    st.sidebar.header("🔐 Akses Masuk Portal")
    peran = st.sidebar.selectbox(
        "Pilih Sebagai:",
        [
            "👨‍🏫 Tutor / Pengajar",
            "👑 Owner / Admin",
            "🎓 Siswa",
            "👪 Wali Murid"
        ]
    )
    
    st.sidebar.markdown("---")
    
    # ----------------------------------------------------
    # JIKA MASUK SEBAGAI TUTOR / OWNER (PANEL BANK SOAL & MENGAJAR)
    # ----------------------------------------------------
    if peran in ["👨‍🏫 Tutor / Pengajar", "👑 Owner / Admin"]:
        st.sidebar.header("🎯 Sesi Pengajaran Aktif")
        nama_siswa_ajar = st.sidebar.text_input("Nama Siswa yang Dibimbing:")
        
        if nama_siswa_ajar:
            st.sidebar.success(f"Sedang mengajar: **{nama_siswa_ajar}**")
            
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Pilih Jalur Bank Soal")
        
        menu_bank = st.sidebar.radio(
            "Pilih Kategori Bank Soal:",
            [
                "📖 Jalur 1: Materi & Konsep Harian",
                "📝 Jalur 2: Paket Soal & Tryout",
                "🏆 Jalur Khusus: Olimpiade Sains (OSN)",
                "📊 Catatan Progres / Evaluasi Siswa"
            ]
        )
        
        # TAB 1: JALUR 1 (MATERI & KISI-KISI)
        if menu_bank == "📖 Jalur 1: Materi & Konsep Harian":
            st.subheader("📖 Pencarian Bank Soal Materi & Konsep Harian (Jalur 1)")
            if nama_siswa_ajar:
                st.info(f"💡 Tips: Cari soal yang sesuai untuk materi harian siswa **{nama_siswa_ajar}**.")
                
            df_materi = load_data_from_sheet("Bank_Soal_Materi")
            if not df_materi.empty:
                col1, col2 = st.columns(2)
                with col1:
                    filter_jenjang = st.text_input("Filter Jenjang / Mapel (cth: SD / Matematika):")
                with col2:
                    filter_bab = st.text_input("Filter Bab / Topik:")
                    
                df_tampil = df_materi.copy()
                if filter_jenjang:
                    df_tampil = df_tampil[df_tampil['Jenjang_Dan_Mapel'].astype(str).str.contains(filter_jenjang, case=False, na=False)]
                if filter_bab:
                    df_tampil = df_tampil[df_tampil['Bab_Atau_Topik'].astype(str).str.contains(filter_bab, case=False, na=False)]
                    
                st.write(f"Menemukan **{len(df_tampil)}** soal dari database.")
                st.dataframe(df_tampil, use_container_width=True)
            else:
                st.warning("Belum ada data di tab `Bank_Soal_Materi`[span_0](start_span)[span_0](end_span). Silakan isi melalui Google Sheets.")

        # TAB 2: JALUR 2 (PAKET SOAL & TRYOUT)
        elif menu_bank == "📝 Jalur 2: Paket Soal & Tryout":
            st.subheader("📝 Pencarian Paket Soal & Tryout Full (Jalur 2)")
            df_paket = load_data_from_sheet("Bank_Soal_Paket")
            if not df_paket.empty:
                filter_kategori = st.text_input("Cari Kategori Ujian (cth: TKA, TOEFL, SKD):")
                df_tampil = df_paket.copy()
                if filter_kategori:
                    df_tampil = df_tampil[df_tampil['Jenjang_Dan_Kategori'].astype(str).str.contains(filter_kategori, case=False, na=False)]
                    
                st.write(f"Menemukan **{len(df_tampil)}** soal paket.")
                st.dataframe(df_tampil, use_container_width=True)
            else:
                st.warning("Belum ada data di tab `Bank_Soal_Paket`[span_1](start_span)[span_1](end_span). Silakan isi melalui Google Sheets.")

        # TAB 3: OLIMPIADE SAINS (OSN)
        elif menu_bank == "🏆 Jalur Khusus: Olimpiade Sains (OSN)":
            st.subheader("🏆 Bank Soal Pembinaan Olimpiade Sains (OSN)")
            df_osn = load_data_from_sheet("Bank_Soal_Olimpiade")
            if not df_osn.empty:
                filter_osn = st.text_input("Cari Bidang / Jenjang Olimpiade (cth: Matematika, Fisika, SD, SMA):")
                df_tampil = df_osn.copy()
                if filter_osn:
                    df_tampil = df_tampil[df_tampil['Jenjang_Dan_Bidang'].astype(str).str.contains(filter_osn, case=False, na=False)]
                    
                st.write(f"Menemukan **{len(df_tampil)}** soal olimpiade lengkap dengan pembahasannya.")
                st.dataframe(df_tampil, use_container_width=True)
            else:
                st.warning("Belum ada data di tab `Bank_Soal_Olimpiade`[span_2](start_span)[span_2](end_span). Silakan isi melalui Google Sheets.")

        # TAB 4: CATATAN PROGRES / EVALUASI
        elif menu_bank == "📊 Catatan Progres / Evaluasi Siswa":
            st.subheader("📊 Catatan Progres & Riwayat Belajar Siswa")
            with st.form("form_progres"):
                p_nama = st.text_input("Nama Siswa:", value=nama_siswa_ajar)
                p_mapel = st.text_input("Mata Pelajaran / Program:")
                p_skor = st.number_input("Skor / Nilai Latihan:", 0, 100, 0)
                p_catatan = st.text_area("Catatan Perkembangan / Kendala:")
                
                simpan_progres = st.form_submit_button("Simpan Catatan Sesi")
                if simpan_progres:
                    if p_nama:
                        st.success(f"Catatan progres untuk **{p_nama}** berhasil dicatat untuk sesi ini!")
                    else:
                        st.warning("Mohon isi nama siswa terlebih dahulu.")

    # ----------------------------------------------------
    # JIKA MASUK SEBAGAI SISWA / WALI MURID
    # ----------------------------------------------------
    else:
        st.subheader(f"👋 Selamat Datang di Portal {peran} Bimbel Rumah Nazma")
        st.write("Silakan pilih program belajar yang ingin diakses:")
        
        pilihan_siswa = st.selectbox("Pilih Menu:", ["Materi Harian (Jalur 1)", "Latihan Paket & Tryout (Jalur 2)", "Olimpiade Sains (OSN)"])
        if pilihan_siswa == "Materi Harian (Jalur 1)":
            st.info("Menampilkan daftar materi belajar harian...")
        elif pilihan_siswa == "Latihan Paket & Tryout (Jalur 2)":
            st.info("Menampilkan paket latihan soal dan simulasi ujian...")
        else:
            st.info("Menampilkan modul pembinaan soal olimpiade sains...")

if __name__ == "__main__":
    main()
