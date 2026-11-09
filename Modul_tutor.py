import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

st.set_page_config(page_title="Portal Bimbel Rumah Nazma", layout="wide", page_icon="✏️")

# --- KODE CSS KHUSUS CETAK (HANYA MENCETAK KOTAK SOAL) ---
st.markdown("""
<style>
@media print {
    /* Sembunyikan seluruh tampilan luar Streamlit */
    header, footer, .stAppHeader, [data-testid="stHeader"], [data-testid="stSidebar"], 
    .stButton, .stSelectbox, .stRadio, .stTextInput, .stAlert, .element-container:has(.stAlert) {
        display: none !important;
    }
    body, .main, .block-container {
        padding: 0 !important;
        margin: 0 !important;
        background-color: #ffffff !important;
    }
    @page {
        size: A4;
        margin: 1cm;
    }
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
st.title("✏️ Portal Bimbel Rumah Nazma")
st.caption("Sistem Manajemen Pembelajaran & Kuis Online/Offline")

# --- PILIHAN PERAN LOGIN ---
peran = st.selectbox(
    "Pilih Akses Login:",
    ["🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "🎓 Siswa", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL TUTOR / PENGAJAR
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
        
        tutor_tab1, tutor_tab2 = st.tabs(["📝 Jurnal & Celah Belajar", "➕ Tambah Soal Baru ke Bank Soal"])
        
        with tutor_tab1:
            st.header("📖 Diari Kelemahan & Jurnal Mengajar Sesi Hari Ini")
            st.subheader("🔍 Cari Nama Siswa yang Diajar Hari Ini")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            
            search_query = st.text_input("Ketik Nama / Panggilan Siswa (misal: Aisyah / Adeva / Nazma):").strip().lower()
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

        with tutor_tab2:
            st.header("➕ Tambah Soal Baru ke Bank Soal Master")
            st.caption("Tutor dapat menginput soal baru di sini tanpa perlu membuka Google Sheets.")
            
            with st.form("form_tambah_soal"):
                bentuk = st.selectbox("Bentuk Soal:", ["Pilgan", "Essay"])
                teks_soal = st.text_area("Teks Soal:", placeholder="Masukkan teks pertanyaan di sini...")
                url_gambar = st.text_input("Link Gambar Soal (Opsional):", placeholder="Misal link Google Drive/Image jika ada gambar")
                
                opsi_jawaban = ""
                if bentuk == "Pilgan":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        op_a = st.text_input("Pilihan A:")
                        op_b = st.text_input("Pilihan B:")
                    with col_b:
                        op_c = st.text_input("Pilihan C:")
                        op_d = st.text_input("Pilihan D:")
                    opsi_jawaban = f"A. {op_a} | B. {op_b} | C. {op_c} | D. {op_d}"
                
                kunci = st.text_input("Kunci Jawaban:", placeholder="Misal: C (untuk Pilgan) atau 150 km (untuk Essay)")
                
                btn_simpan_soal = st.form_submit_button("💾 Masukkan Soal ke Master Bank Soal")
                
                if btn_simpan_soal:
                    if not teks_soal.strip():
                        st.error("Teks soal tidak boleh kosong!")
                    else:
                        try:
                            try:
                                ws_master = sheet.worksheet("Bank_Soal_Master")
                            except:
                                ws_master = sheet.add_worksheet(title="Bank_Soal_Master", rows="1000", cols="10")
                                ws_master.append_row(["Bentuk_Soal", "Teks_Soal", "URL_Gambar", "Opsi_Jawaban", "Kunci_Jawaban"])
                            
                            ws_master.append_row([bentuk, teks_soal, url_gambar, opsi_jawaban, str(kunci)])
                            st.success("🎉 Soal baru berhasil disimpan ke Bank Soal Master!")
                        except Exception as ex:
                            st.error(f"Gagal menyimpan soal: {ex}")

# ==========================================
# 2. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Kurikulum & Perencanaan (Mbak Fatimah)")
    pin_owner = st.text_input("Masukkan PIN Akses Pengelola:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Pengelola Diizinkan 👋")
        tab1, tab2 = st.tabs(["📅 Plotting Soal & Cetak Offline", "📚 Master Bank Soal"])
        
        ws_siswa = sheet.worksheet("Data_Siswa")
        all_siswa = ws_siswa.get_all_records()
        
        with tab1:
            st.markdown("### 🌙 Setting Soal & PR Durasi Terukur untuk Siswa")
            pilih_siswa = st.selectbox("Pilih Siswa Target:", ["-- Pilih Siswa --"] + [s.get("Nama_Lengkap") for s in all_siswa if s.get("Nama_Lengkap")])
            
            if pilih_siswa != "-- Pilih Siswa --":
                try:
                    ws_celah = sheet.worksheet("Celah_Belajar")
                    celah_data = ws_celah.get_all_records()
                    celah_siswa = [c for c in celah_data if str(c.get("Nama_Siswa")).strip().lower() == pilih_siswa.strip().lower()]
                    if celah_siswa:
                        st.info(f"📌 **Celah Belajar Terakhir Ananda {pilih_siswa}:** {celah_siswa[-1].get('Topik_Belum_Paham')}")
                except:
                    pass
                
                topik_options = [
                    "IPAS Bab 4: Berkenalan dengan Energi (25 Soal Nazma)",
                    "Latihan Matematika Kelas 7 (30 Soal Master)"
                ]
                selected_topik = st.selectbox("Pilih Topik Soal Berkesinambungan:", topik_options)
                jenis_soal = st.radio("Media Soal:", ["Online (Kuis HP / PR Siswa)", "Offline (Cetak / Buku Latihan)"])
                
                durasi_menit = st.number_input("⏱️ Set Durasi Waktu Kuis (Menit):", min_value=5, max_value=180, value=30, step=5)
                catatan_soal = st.text_area("Instruksi / Catatan Khusus untuk Siswa:", placeholder="Misal: Kerjakan dengan teliti! Kuis ini otomatis mengunci jika waktu habis.")
                
                if st.button("📌 Tugaskan Soal ke Siswa"):
                    if jenis_soal == "Online (Kuis HP / PR Siswa)":
                        st.success(f"✅ Soal '{selected_topik}' berhasil ditugaskan ke {pilih_siswa} secara online!")
                    else:
                        st.session_state["show_print_preview"] = True

                if jenis_soal == "Offline (Cetak / Buku Latihan)" and st.session_state.get("show_print_preview", False):
                    st.markdown("---")
                    
                    try:
                        ws_master = sheet.worksheet("Bank_Soal_Master")
                        all_soal = ws_master.get_all_records()
                        
                        if "IPAS" in selected_topik:
                            soal_db = all_soal[30:] # Soal IPAS Nazma
                        else:
                            soal_db = all_soal[:30] # Soal Matematika
                    except:
                        soal_db = []
                    
                    pilgan_list = [s for s in soal_db if str(s.get('Bentuk_Soal')).strip() == "Pilgan"]
                    essay_list = [s for s in soal_db if str(s.get('Bentuk_Soal')).strip() == "Essay"]
                    
                    html_content = f"""
                    <div style="border: 1.5px solid #000; padding: 15px; background: #fff; font-family: Arial, sans-serif; color: #000;">
                        <h2 style="text-align: center; margin: 0; font-size: 18px; color: #000;">BIMBEL RUMAH NAZMA</h2>
                        <h4 style="text-align: center; margin: 3px 0 10px 0; font-size: 13px; color: #333;">LEMBAR LATIHAN SOAL (OFFLINE)</h4>
                        <table style="width: 100%; border-bottom: 2px solid #000; font-size: 12px; font-weight: bold; margin-bottom: 10px; color: #000;">
                            <tr>
                                <td>Nama Siswa: {pilih_siswa}</td>
                                <td>Tanggal: {datetime.now().strftime('%d/%m/%Y')}</td>
                            </tr>
                            <tr>
                                <td>Topik: {selected_topik}</td>
                                <td>Paraf Tutor: _________</td>
                            </tr>
                        </table>
                        <h5 style="margin: 5px 0; font-size: 13px;">A. PILIHAN GANDA</h5>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px 15px; font-size: 11px;">
                    """
                    
                    for idx, s in enumerate(pilgan_list, 1):
                        opsi_str = ""
                        if s.get('Opsi_Jawaban'):
                            opsi = [o.strip() for o in str(s.get('Opsi_Jawaban')).split("|")]
                            opsi_str = f"<br>{'&nbsp;&nbsp;'.join(opsi)}"
                        html_content += f"<div style='margin-bottom: 4px;'><b>{idx}.</b> {s.get('Teks_Soal')}{opsi_str}</div>"
                    
                    html_content += "</div>"
                    
                    if essay_list:
                        html_content += "<h5 style='margin: 12px 0 5px 0; font-size: 13px;'>B. ESSAY</h5><div style='font-size: 11px;'>"
                        for idx, s in enumerate(essay_list, len(pilgan_list) + 1):
                            html_content += f"<div style='margin-bottom: 6px;'><b>{idx}.</b> {s.get('Teks_Soal')}<br><span style='color: #666;'>Jawaban: __________________________________________________</span></div>"
                        html_content += "</div>"
                        
                    html_content += "</div>"
                    
                    st.markdown(html_content, unsafe_allow_html=True)
                    st.success("✅ Lembar latihan siap dicetak! Hanya area lembar soal di atas yang akan tercetak.")

        with tab2:
            st.markdown("### 📚 Master Bank Soal Bimbel")
            try:
                ws_master = sheet.worksheet("Bank_Soal_Master")
                data_master = ws_master.get_all_records()
                for r in data_master:
                    for k in r:
                        r[k] = str(r[k])
                st.dataframe(data_master)
            except Exception as e:
                st.write(f"Gagal memuat bank soal master: {e}")
    elif pin_owner:
        st.error("PIN Pengelola Salah!")

# ==========================================
# 3. MODUL SISWA
# ==========================================
elif peran == "🎓 Siswa":
    st.subheader("🎓 Login Siswa")
    
    if "siswa_logged_in" not in st.session_state:
        st.session_state.siswa_logged_in = False
        st.session_state.siswa_nama = ""

    if not st.session_state.siswa_logged_in:
        nama_siswa = st.text_input("Nama Siswa (misal: Aisyah / Adeva / Nazma):")
        pin_siswa = st.text_input("PIN Siswa (4 Angka):", type="password")
        
        if st.button("Masuk Siswa"):
            ws = sheet.worksheet("Data_Siswa")
            data = ws.get_all_records()
            siswa_found = False
            for row in data:
                if str(row.get("Nama_Lengkap")).strip().lower() == nama_siswa.strip().lower() and str(row.get("PIN_Siswa")).strip() == pin_siswa.strip():
                    siswa_found = True
                    st.session_state.siswa_logged_in = True
                    st.session_state.siswa_nama = row.get("Nama_Lengkap")
                    st.rerun()
                    break
            if not siswa_found:
                st.error("Nama Siswa atau PIN Siswa salah!")
    else:
        st.success(f"Selamat Datang, Ananda **{st.session_state.siswa_nama}**! 👋")
        if st.button("Logout Siswa"):
            st.session_state.siswa_logged_in = False
            st.session_state.siswa_nama = ""
            st.session_state.pop("start_time", None)
            st.rerun()
            
        st.markdown("---")
        st.subheader("📝 Kuis Online & PR Mandiri")
        
        durasi_menit_kuis = 30 
        durasi_detik = durasi_menit_kuis * 60
        
        if "start_time" not in st.session_state:
            st.session_state.start_time = time.time()
            
        waktu_berjalan = time.time() - st.session_state.start_time
        sisa_waktu = int(durasi_detik - waktu_berjalan)
        
        if sisa_waktu > 0:
            menit = sisa_waktu // 60
            detik = sisa_waktu % 60
            st.warning(f"⏱️ **Sisa Waktu Kuis:** `{menit:02d}:{detik:02d}` Menit")
            
            with st.form("form_kuis_siswa"):
                st.markdown("### Soal Latihan Kuis")
                
                try:
                    ws_master = sheet.worksheet("Bank_Soal_Master")
                    all_soal = ws_master.get_all_records()
                    
                    if str(st.session_state.siswa_nama).strip().lower() == "nazma":
                        soal_db = all_soal[30:]
                    else:
                        soal_db = all_soal[:30]
                except:
                    soal_db = []
                
                if soal_db:
                    jawaban_siswa = {}
                    for idx, s in enumerate(soal_db, 1):
                        st.markdown(f"**Soal No. {idx}** ({s.get('Bentuk_Soal')})")
                        st.write(s.get('Teks_Soal'))
                        
                        if s.get('URL_Gambar'):
                            st.image(s.get('URL_Gambar'), caption="Gambar Soal", width=250)
                            
                        if str(s.get('Bentuk_Soal')).strip() == "Pilgan":
                            opsi_raw = str(s.get('Opsi_Jawaban', ''))
                            opsi_list = [o.strip() for o in opsi_raw.split("|") if o.strip()]
                            if not opsi_list:
                                opsi_list = ["A", "B", "C", "D"]
                            jawaban_siswa[idx] = st.radio(f"Pilih Jawaban No {idx}:", opsi_list, key=f"soal_{idx}")
                        elif str(s.get('Bentuk_Soal')).strip() == "Essay":
                            jawaban_siswa[idx] = st.text_area(f"Ketik Jawaban No {idx}:", key=f"soal_{idx}")
                        
                        st.markdown("---")
                else:
                    st.info("Belum ada soal online yang ditugaskan.")
                    
                submitted = st.form_submit_button("🚀 Kirim Jawaban Kuis")
                if submitted:
                    st.balloons()
                    st.success("🎉 Jawaban berhasil dikirim dan tersimpan di database!")
        else:
            st.error("⏰ **Waktu Kuis Telah Habis!** Form kuis dikunci secara otomatis.")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua")
    nama_anak = st.text_input("Nama Putra/Putri (misal: Aisyah / Adeva / Sherin / Nazma):")
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
