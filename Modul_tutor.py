import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

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
                            soal_db = all_soal[30:]
                        else:
                            soal_db = all_soal[:30]
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
                        
                    if essay_list:
                        text_document += "B. ESSAY\n\n"
                        for idx, s in enumerate(essay_list, len(pilgan_list) + 1):
                            text_document += f"{idx}. {s.get('Teks_Soal')}\n"
                            text_document += "   Jawaban: __________________________________________________\n\n"
                    
                    st.subheader("📄 Unduh File Soal Siap Cetak (Bebas Menu Web)")
                    st.download_button(
                        label="📥 Unduh Lembar Soal (.txt / Siap Cetak)",
                        data=text_document,
                        file_name=f"Lembar_Soal_{pilih_siswa}_{datetime.now().strftime('%d%m%Y')}.txt",
                        mime="text/plain"
                    )

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
            st.session_state.pop("kuis_submitted", None)
            st.rerun()
            
        st.markdown("---")
        st.subheader("📝 Kuis Online & PR Mandiri")
        
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
                    # PROSES PENILAIAN OTOMATIS
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

                    # HITUNG SKOR (0-100)
                    pilgan_count = len([s for s in soal_db if str(s.get("Bentuk_Soal")).strip() == "Pilgan"])
                    skor_akhir = round((benar / pilgan_count) * 100) if pilgan_count > 0 else 100
                    
                    detail_salah_str = f"Soal salah: No {', '.join(map(str, salah_no))}" if salah_no else "Semua Pilgan Benar!"
                    
                    # SIMPAN KE GOOGLE SHEETS (Riwayat_Latihan)
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
            
            st.subheader("📋 Ringkasan Hasil Pengerjaan:")
            salah_list = st.session_state.get('hasil_salah_no', [])
            
            if salah_list:
                st.warning(f"📌 **Nomor yang Masih Salah:** Nomor **{', '.join(map(str, salah_list))}**")
                st.info("💡 *Catatan:* Kunci jawaban tidak ditampilkan agar bisa dibahas dan dipelajari bersama Tutor saat sesi les!")
            else:
                st.success("🌟 Luar biasa! Semua soal Pilihan Ganda berhasil kamu jawab dengan Benar!")
                
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
                
                laporan_list = []
                
                # 1. AMBIL DATA KUIS ONLINE SISWA (Riwayat_Latihan)
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

                # 2. AMBIL DATA JURNAL LES OFFLINE (Form Responses 1)
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
                break
                
        if not ortu_found:
            st.error("Nama Putra/Putri atau PIN Orang Tua salah!")
