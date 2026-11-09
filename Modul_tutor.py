import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import pandas as pd

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
st.caption("Sistem Manajemen Pembelajaran, Portofolio & Keamanan Akun")

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
            is_active = True
            
            for row in data:
                if str(row.get("Username")).strip().lower() == username.strip().lower() and str(row.get("PIN_Password")).strip() == pin.strip():
                    user_found = True
                    status_user = str(row.get("Status", "Aktif")).strip().lower()
                    if status_user == "nonaktif":
                        is_active = False
                    else:
                        st.session_state.tutor_logged_in = True
                        st.session_state.tutor_nama = row.get("Nama_Pengguna")
                        st.rerun()
                    break
            
            if not user_found:
                st.error("Username atau PIN Pengajar salah!")
            elif not is_active:
                st.error("🚫 **Akun Anda sudah Nonaktif.** Silakan hubungi Mbak Fatimah (Pengelola Bimbel).")
    else:
        st.success(f"👨‍🏫 **Tutor Aktif:** {st.session_state.tutor_nama}")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.rerun()
            
        st.markdown("---")
        
        tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs(["📝 Jurnal & Celah Belajar Hari Ini", "📊 Portofolio & Grafik Progress Siswa", "➕ Tambah Soal Baru"])
        
        with tutor_tab1:
            st.header("📖 Diari Kelemahan & Jurnal Mengajar Sesi Hari Ini")
            st.subheader("🔍 Cari Nama Siswa yang Diajar Hari Ini")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            
            # FILTER HANYA SISWA AKTIF
            siswa_aktif = [s.get("Nama_Lengkap") for s in data_siswa_all if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            search_query = st.text_input("Ketik Nama / Panggilan Siswa (misal: Aisyah / Adeva / Nazma):").strip().lower()
            selected_siswa = None
            
            if search_query:
                hasil_pencarian = [s for s in siswa_aktif if search_query in str(s).strip().lower()]
                
                if hasil_pencarian:
                    pilihan = st.selectbox("Pilih Siswa dari Hasil Pencarian:", ["-- Pilih Siswa --"] + hasil_pencarian)
                    if pilihan != "-- Pilih Siswa --":
                        selected_siswa = pilihan
                else:
                    st.warning(f"Siswa aktif dengan nama '{search_query}' tidak ditemukan di Data Siswa.")
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
                        foto_link = st.text_input("Link Foto Dokumentasi (Bisa beberapa, pisahkan dengan koma)", placeholder="https://drive.google.com/..., https://drive.google.com/...")
                    
                    submitted = st.form_submit_button("💾 Simpan Jurnal & Rekam Kelemahan")
                    
                    if submitted:
                        try:
                            ws_jurnal = None
                            for tab_name in ["Form Responses 1", "Form_Responses_1", "Jurnal_Mengajar"]:
                                try:
                                    ws_jurnal = sheet.worksheet(tab_name)
                                    break
                                except:
                                    pass
                            
                            if not ws_jurnal:
                                ws_jurnal = sheet.add_worksheet(title="Form Responses 1", rows="1000", cols="15")
                                ws_jurnal.append_row([
                                    "Timestamp", "Tanggal Mengajar", "Nama TUtor", "Kehadiran", "Nama Siswa",
                                    "Materi dan Pelajaran Hari Ini", "Pencapaian Belajar", "Kendala Belajar Anak",
                                    "tugas & Latihan (PR)", "Dokumentasi/ Foto hasil Belajar", "Nilai/skor latihan"
                                ])
                            
                            ws_jurnal.append_row([
                                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                tgl.strftime("%d/%m/%Y"),
                                st.session_state.tutor_nama if st.session_state.tutor_nama else "Pengelola",
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
                                try:
                                    ws_celah = sheet.worksheet("Celah_Belajar")
                                    last_id = len(ws_celah.get_all_records()) + 1
                                    ws_celah.append_row([
                                        f"CLH-{last_id:03d}",
                                        tgl.strftime("%Y-%m-%d"),
                                        selected_siswa,
                                        mapel,
                                        kendala,
                                        tingkat_celah,
                                        st.session_state.tutor_nama if st.session_state.tutor_nama else "Pengelola",
                                        "Dalam Proses"
                                    ])
                                except:
                                    pass
                            
                            st.success("✅ Jurnal, Nilai, & Celah Belajar Berhasil Disimpan!")
                        except Exception as ex:
                            st.error(f"Gagal menyimpan data: {ex}")

        with tutor_tab2:
            st.header("📊 Portofolio & Histori Progress Siswa Berkelanjutan")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            pilih_siswa_histori = st.selectbox("Pilih Nama Siswa untuk Melihat Portofolio Lengkap:", ["-- Pilih Siswa --"] + [s.get("Nama_Lengkap") for s in data_siswa_all if s.get("Nama_Lengkap")])
            
            if pilih_siswa_histori != "-- Pilih Siswa --":
                st.subheader(f"📈 Grafik Perkembangan Nilai: Ananda {pilih_siswa_histori}")
                
                data_grafik = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == pilih_siswa_histori.strip().lower():
                            try:
                                val_skor = float(r.get("Skor", 0))
                                data_grafik.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": val_skor})
                            except:
                                pass
                except:
                    pass

                try:
                    ws_j = sheet.worksheet("Form Responses 1")
                    for j in ws_j.get_all_records():
                        val_nama = str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower()
                        if val_nama == pilih_siswa_histori.strip().lower():
                            try:
                                val_skor = float(j.get("Nilai/skor latihan", j.get("Skor", 0)))
                                data_grafik.append({"Tanggal": str(j.get("Tanggal Mengajar", j.get("Tanggal", ""))), "Skor": val_skor})
                            except:
                                pass
                except:
                    pass

                if data_grafik:
                    df_grafik = pd.DataFrame(data_grafik)
                    st.line_chart(df_grafik.set_index("Tanggal")["Skor"])
                else:
                    st.info("Belum cukup data nilai untuk membuat grafik.")
                
                st.markdown("---")
                st.subheader(f"📜 Histori Seluruh Sesi Mengajar Terdahulu")
                try:
                    ws_j = sheet.worksheet("Form Responses 1")
                    jurnal_all = [j for j in ws_j.get_all_records() if str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower() == pilih_siswa_histori.strip().lower()]
                    if jurnal_all:
                        for idx, j in enumerate(reversed(jurnal_all), 1):
                            with st.expander(f"Sesi {j.get('Tanggal Mengajar', '-')} | Mapel & Materi: {j.get('Materi dan Pelajaran Hari Ini', '-')} (Skor: {j.get('Nilai/skor latihan', '-')})"):
                                st.write(f"👨‍🏫 **Tutor:** {j.get('Nama TUtor', '-')}")
                                st.write(f"🌟 **Pencapaian:** {j.get('Pencapaian Belajar', '-')}")
                                st.write(f"💡 **Catatan Kelemahan:** {j.get('Kendala Belajar Anak', '-')}")
                                st.write(f"📝 **PR:** {j.get('tugas & Latihan (PR)', '-')}")
                    else:
                        st.info("Belum ada histori jurnal mengajar sebelumnya.")
                except:
                    st.info("Belum ada histori terrekam.")

        with tutor_tab3:
            st.header("➕ Tambah Soal Baru ke Bank Soal Master")
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
    st.subheader("👑 Portal Kurikulum & Manajemen Akun (Mbak Fatimah)")
    pin_owner = st.text_input("Masukkan PIN Akses Pengelola:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Pengelola Diizinkan 👋")
        tab1, tab2, tab3 = st.tabs(["👥 Kelola Status Akun (Aktif / Nonaktif)", "📅 Plotting Soal & Cetak", "📚 Master Bank Soal"])
        
        # TAB KELOLA AKUN (DEACTIVE / ACTIVE)
        with tab1:
            st.markdown("### 🔐 Status Aktif / Nonaktif Akun Siswa & Tutor")
            st.caption("Jika siswa atau tutor sudah keluar/tidak aktif, ubah statusnya menjadi 'Nonaktif'. Mereka tidak akan bisa login lagi, namun riwayat belajarnya tidak akan hilang.")
            
            sub_ak1, sub_ak2 = st.tabs(["🎓 Status Siswa", "👨‍🏫 Status Tutor / Pengajar"])
            
            with sub_ak1:
                ws_siswa = sheet.worksheet("Data_Siswa")
                records_siswa = ws_siswa.get_all_records()
                df_siswa = pd.DataFrame(records_siswa)
                
                st.dataframe(df_siswa[["ID_Siswa", "Nama_Lengkap", "Jenjang", "Kelas", "Status"]])
                
                with st.form("form_status_siswa"):
                    pilih_s_nama = st.selectbox("Pilih Siswa yang Ingin Diubah Statusnya:", [s.get("Nama_Lengkap") for s in records_siswa if s.get("Nama_Lengkap")])
                    status_s_baru = st.selectbox("Set Status Baru:", ["Aktif", "Nonaktif"])
                    btn_u_siswa = st.form_submit_button("💾 Update Status Siswa")
                    
                    if btn_u_siswa:
                        try:
                            cell = ws_siswa.find(pilih_s_nama)
                            col_status_idx = list(records_siswa[0].keys()).index("Status") + 1
                            ws_siswa.update_cell(cell.row, col_status_idx, status_s_baru)
                            st.success(f"✅ Status Ananda **{pilih_s_nama}** berhasil diubah menjadi **{status_s_baru}**!")
                        except Exception as ex:
                            st.error(f"Gagal mengupdate status: {ex}")

            with sub_ak2:
                ws_user = sheet.worksheet("Akun_Pengguna")
                records_user = ws_user.get_all_records()
                df_user = pd.DataFrame(records_user)
                
                if "Status" not in df_user.columns:
                    ws_user.update_cell(1, len(records_user[0]) + 1, "Status")
                    records_user = ws_user.get_all_records()
                    df_user = pd.DataFrame(records_user)
                    
                st.dataframe(df_user[["ID_User", "Nama_Pengguna", "Level_Akses", "Username", "Status"]])
                
                with st.form("form_status_tutor"):
                    pilih_t_nama = st.selectbox("Pilih Tutor yang Ingin Diubah Statusnya:", [t.get("Nama_Pengguna") for t in records_user if t.get("Nama_Pengguna")])
                    status_t_baru = st.selectbox("Set Status Baru:", ["Aktif", "Nonaktif"])
                    btn_u_tutor = st.form_submit_button("💾 Update Status Tutor")
                    
                    if btn_u_tutor:
                        try:
                            cell = ws_user.find(pilih_t_nama)
                            col_status_idx = list(records_user[0].keys()).index("Status") + 1
                            ws_user.update_cell(cell.row, col_status_idx, status_t_baru)
                            st.success(f"✅ Status Tutor **{pilih_t_nama}** berhasil diubah menjadi **{status_t_baru}**!")
                        except Exception as ex:
                            st.error(f"Gagal mengupdate status: {ex}")

        with tab2:
            ws_siswa = sheet.worksheet("Data_Siswa")
            all_siswa = ws_siswa.get_all_records()
            st.markdown("### 🌙 Setting Soal & PR Durasi Terukur untuk Siswa")
            pilih_siswa = st.selectbox("Pilih Siswa Target:", ["-- Pilih Siswa --"] + [s.get("Nama_Lengkap") for s in all_siswa if s.get("Nama_Lengkap")])
            
            if pilih_siswa != "-- Pilih Siswa --":
                topik_options = [
                    "IPAS Bab 4: Berkenalan dengan Energi (25 Soal Nazma)",
                    "Latihan Matematika Kelas 7 (30 Soal Master)"
                ]
                selected_topik = st.selectbox("Pilih Topik Soal Berkesinambungan:", topik_options)
                jenis_soal = st.radio("Media Soal:", ["Online (Kuis HP / PR Siswa)", "Offline (Cetak / Buku Latihan)"])
                
                durasi_menit = st.number_input("⏱️ Set Durasi Waktu Kuis (Menit):", min_value=5, max_value=180, value=30, step=5)
                
                if st.button("📌 Tugaskan Soal ke Siswa"):
                    if jenis_soal == "Online (Kuis HP / PR Siswa)":
                        st.success(f"✅ Soal '{selected_topik}' berhasil ditugaskan ke {pilih_siswa} secara online!")
                    else:
                        st.session_state["show_print_preview"] = True

                if jenis_soal == "Offline (Cetak / Buku Latihan)" and st.session_state.get("show_print_preview", False):
                    try:
                        ws_master = sheet.worksheet("Bank_Soal_Master")
                        all_soal = ws_master.get_all_records()
                        soal_db = all_soal[30:] if "IPAS" in selected_topik else all_soal[:30]
                    except:
                        soal_db = []
                    
                    pilgan_list = [s for s in soal_db if str(s.get('Bentuk_Soal')).strip() == "Pilgan"]
                    essay_list = [s for s in soal_db if str(s.get('Bentuk_Soal')).strip() == "Essay"]
                    
                    text_document = f"BIMBEL RUMAH NAZMA\nLEMBAR LATIHAN SOAL (OFFLINE)\n"
                    text_document += f"--------------------------------------------------\n"
                    text_document += f"Nama Siswa : {pilih_siswa}\t\tTanggal : {datetime.now().strftime('%d/%m/%Y')}\n"
                    text_document += f"Topik      : {selected_topik}\tParaf Tutor: _________\n"
                    text_document += f"--------------------------------------------------\n\n"
                    text_document += "A. PILIHAN GANDA\n\n"
                    
                    for idx, s in enumerate(pilgan_list, 1):
                        text_document += f"{idx}. {s.get('Teks_Soal')}\n"
                        if s.get('Opsi_Jawaban'):
                            opsi = [o.strip() for o in str(s.get('Opsi_Jawaban')).split("|")]
                            text_document += f"   {'   '.join(opsi)}\n"
                        text_document += "\n"
                    
                    st.download_button(
                        label="📥 Unduh Lembar Soal (.txt / Siap Cetak)",
                        data=text_document,
                        file_name=f"Lembar_Soal_{pilih_siswa}_{datetime.now().strftime('%d%m%Y')}.txt",
                        mime="text/plain"
                    )

        with tab3:
            st.markdown("### 📚 Master Bank Soal Bimbel")
            try:
                ws_master = sheet.worksheet("Bank_Soal_Master")
                data_master = ws_master.get_all_records()
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
                        st.rerun()
                    break
            
            if not siswa_found:
                st.error("Nama Siswa atau PIN Siswa salah!")
            elif not is_active:
                st.error("🚫 **Akun Siswa Anda sudah Nonaktif.** Silakan hubungi Mbak Fatimah.")
    else:
        st.success(f"Selamat Datang, Ananda **{st.session_state.siswa_nama}**! 👋")
        if st.button("Logout Siswa"):
            st.session_state.siswa_logged_in = False
            st.session_state.siswa_nama = ""
            st.session_state.pop("start_time", None)
            st.session_state.pop("kuis_submitted", None)
            st.rerun()
            
        st.markdown("---")
        siswa_tab1, siswa_tab2 = st.tabs(["📝 Kuis Online Hari Ini", "📈 Grafik Progress Nilai Saya"])
        
        with siswa_tab1:
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
                    st.markdown("### Soal Latihan Kuis")
                    
                    try:
                        ws_master = sheet.worksheet("Bank_Soal_Master")
                        all_soal = ws_master.get_all_records()
                        
                        if str(st.session_state.siswa_nama).strip().lower() == "nazma":
                            soal_db = all_soal[30:]
                            topik_nama = "IPAS Bab 4: Berkenalan dengan Energi"
                            mapel_nama = "IPAS"
                        else:
                            soal_db = all_soal[:30]
                            topik_nama = "Latihan Matematika Kelas 7"
                            mapel_nama = "Matematika"
                    except:
                        soal_db = []
                    
                    jawaban_user = {}
                    if soal_db:
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
                                jawaban_user[idx] = st.radio(f"Pilih Jawaban No {idx}:", opsi_list, key=f"soal_{idx}")
                            elif str(s.get('Bentuk_Soal')).strip() == "Essay":
                                jawaban_user[idx] = st.text_area(f"Ketik Jawaban No {idx}:", key=f"soal_{idx}")
                            
                            st.markdown("---")
                    else:
                        st.info("Belum ada soal online yang ditugaskan.")
                        
                    submitted = st.form_submit_button("🚀 Kirim Jawaban Kuis")
                    if submitted and soal_db:
                        total_soal = len(soal_db)
                        benar = 0
                        salah_no = []
                        detail_per_soal = []
                        
                        for idx, s in enumerate(soal_db, 1):
                            kunci_raw = str(s.get("Kunci_Jawaban", "")).strip().upper()
                            user_ans = str(jawaban_user.get(idx, "")).strip()
                            
                            if str(s.get("Bentuk_Soal")).strip() == "Pilgan":
                                user_huruf = user_ans[0].upper() if user_ans else ""
                                if user_huruf == kunci_raw:
                                    benar += 1
                                    detail_per_soal.append((idx, True))
                                else:
                                    salah_no.append(idx)
                                    detail_per_soal.append((idx, False))
                            else:
                                detail_per_soal.append((idx, "Essay"))

                        pilgan_count = len([s for s in soal_db if str(s.get("Bentuk_Soal")).strip() == "Pilgan"])
                        skor_akhir = round((benar / pilgan_count) * 100) if pilgan_count > 0 else 100
                        detail_salah_str = f"Soal salah: No {', '.join(map(str, salah_no))}" if salah_no else "Semua Pilgan Benar!"
                        
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
                        st.session_state.hasil_detail = detail_per_soal
                        st.session_state.hasil_salah_no = salah_no
                        st.rerun()

            elif st.session_state.get("kuis_submitted", False):
                st.balloons()
                st.success(f"🎉 **Kuis Berhasil Dikirim!**")
                st.markdown(f"### 💯 Skor Kamu: `{st.session_state.get('hasil_skor', 0)} / 100`")
                
                salah_list = st.session_state.get('hasil_salah_no', [])
                if salah_list:
                    st.warning(f"📌 **Nomor yang Masih Salah:** Nomor **{', '.join(map(str, salah_list))}**")
                    st.info("💡 Kunci jawaban tidak ditampilkan agar bisa dibahas bersama Tutor saat les!")
                else:
                    st.success("🌟 Luar biasa! Semua soal Pilihan Ganda berhasil dijawab dengan Benar!")
                    
                st.markdown("---")
                st.write("Detail Status Jawaban:")
                for no, status in st.session_state.get('hasil_detail', []):
                    if status is True:
                        st.write(f"* Soal No. {no}: ✅ **BENAR**")
                    elif status is False:
                        st.write(f"* Soal No. {no}: ❌ **SALAH**")
                    else:
                        st.write(f"* Soal No. {no}: 📝 **ESSAY** (Akan diperiksa Tutor)")
            else:
                st.error("⏰ **Waktu Kuis Telah Habis!** Form kuis dikunci secara otomatis.")
                
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
                st.info("Belum ada grafik riwayat nilai kuis online.")

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
        is_active = True
        
        for row in data_siswa:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                ortu_found = True
                status_siswa = str(row.get("Status", "Aktif")).strip().lower()
                
                if status_siswa == "nonaktif":
                    is_active = False
                else:
                    st.success(f"Selamat datang Orang Tua dari Ananda **{row.get('Nama_Lengkap')}** 👋")
                    st.markdown(f"**Jenjang:** {row.get('Jenjang')} (Kelas {row.get('Kelas')}) | **Mapel:** {row.get('Mapel_Diambil')}")
                    st.markdown("---")
                    
                    ortu_tab1, ortu_tab2 = st.tabs(["📋 Sesi Belajar Terbaru", "📈 Grafik & Histori Lengkap"])
                    
                    with ortu_tab1:
                        laporan_list = []
                        
                        try:
                            ws_riwayat = sheet.worksheet("Riwayat_Latihan")
                            data_riwayat = ws_riwayat.get_all_records()
                            for r in data_riwayat:
                                if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                    laporan_list.append({
                                        'Tanggal': r.get('Waktu_Selesai', '-'),
                                        'Tutor': 'Sistem Kuis Online',
                                        'Materi': f"[{r.get('Mapel')}] {r.get('Topik_Kuis')}",
                                        'Skor': r.get('Skor', '-'),
                                        'PR': 'Kuis Online Aplikasi',
                                        'Pencapaian': f"Selesai Kuis Online ({r.get('Total_Soal')} Soal)",
                                        'Kendala': r.get('Detail_Salah', '-'),
                                        'Foto': ''
                                    })
                        except:
                            pass

                        try:
                            ws_jurnal = None
                            for tab_name in ["Form Responses 1", "Form_Responses_1", "Jurnal_Mengajar"]:
                                try:
                                    ws_jurnal = sheet.worksheet(tab_name)
                                    break
                                except:
                                    pass
                            
                            if ws_jurnal:
                                data_jurnal = ws_jurnal.get_all_records()
                                for j in data_jurnal:
                                    val_nama = str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower()
                                    if val_nama == nama_anak.strip().lower() or nama_anak.strip().lower() in val_nama:
                                        laporan_list.append({
                                            'Tanggal': j.get('Tanggal Mengajar', j.get('Tanggal', '-')),
                                            'Tutor': j.get('Nama TUtor', j.get('Nama_Tutor', '-')),
                                            'Materi': j.get('Materi dan Pelajaran Hari Ini', j.get('Materi', '-')),
                                            'Skor': j.get('Nilai/skor latihan', j.get('Skor', '-')),
                                            'PR': j.get('tugas & Latihan (PR)', j.get('PR', '-')),
                                            'Pencapaian': j.get('Pencapaian Belajar', j.get('Pencapaian', '-')),
                                            'Kendala': j.get('Kendala Belajar Anak', j.get('Kendala', '-')),
                                            'Foto': str(j.get('Dokumentasi/ Foto hasil Belajar', j.get('Foto', '')))
                                        })
                        except:
                            pass

                        if laporan_list:
                            laporan_terbaru = laporan_list[-1]
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"📅 **Tanggal:** {laporan_terbaru.get('Tanggal')}")
                                st.write(f"👨‍🏫 **Tutor / Sumber:** {laporan_terbaru.get('Tutor')}")
                                st.write(f"📚 **Materi & Mapel:** {laporan_terbaru.get('Materi')}")
                            with col2:
                                st.write(f"💯 **Nilai / Skor Latihan:** {laporan_terbaru.get('Skor')}")
                                st.write(f"📝 **PR / Jenis Tugas:** {laporan_terbaru.get('PR')}")
                            
                            st.markdown("**🌟 Pencapaian Belajar:**")
                            st.info(laporan_terbaru.get('Pencapaian'))
                            
                            if str(laporan_terbaru.get('Kendala')).strip() and str(laporan_terbaru.get('Kendala')) != "-":
                                st.markdown("**💡 Catatan / Kendala Belajar:**")
                                st.warning(laporan_terbaru.get('Kendala'))
                                
                            foto_url_raw = laporan_terbaru.get('Foto', '')
                            if foto_url_raw and "http" in foto_url_raw:
                                st.markdown("**📷 Foto Dokumentasi Hasil Belajar:**")
                                urls = [u.strip() for u in foto_url_raw.split(",") if u.strip()]
                                for idx, u in enumerate(urls, 1):
                                    st.markdown(f"👉 [Klik di sini untuk melihat Foto Dokumentasi {idx}]({u})")
                        else:
                            st.info("Belum ada catatan sesi belajar untuk Ananda.")
                    
                    with ortu_tab2:
                        st.subheader(f"📈 Grafik Progress Nilai Ananda {nama_anak}")
                        data_grafik_ortu = []
                        try:
                            ws_r = sheet.worksheet("Riwayat_Latihan")
                            for r in ws_r.get_all_records():
                                if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                                    try:
                                        val_skor = float(r.get("Skor", 0))
                                        data_grafik_ortu.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": val_skor})
                                    except:
                                        pass
                        except:
                            pass
                        
                        if data_grafik_ortu:
                            df_ortu = pd.DataFrame(data_grafik_ortu)
                            st.line_chart(df_ortu.set_index("Tanggal")["Skor"])
                        else:
                            st.info("Belum ada histori grafik nilai.")
                break
                
        if not ortu_found:
            st.error("Nama Putra/Putri atau PIN Orang Tua salah!")
        elif not is_active:
            st.error("🚫 **Akun Ananda sudah Nonaktif.** Silakan hubungi Mbak Fatimah.")
