import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import pandas as pd
import random

# --- KONFIGURASI HALAMAN & TAMPILAN PROFESIONAL ---
st.set_page_config(
    page_title="Portal Bimbel Rumah Nazma",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
st.markdown("""
<div class="main-header">
    <h2 style="margin:0;">✨ Portal Bimbel Rumah Nazma</h2>
    <p style="margin:4px 0 0 0; opacity:0.9;">Sistem Pembelajaran Terpadu, Gamifikasi & Portofolio Berkelanjutan</p>
</div>
""", unsafe_allow_html=True)

peran = st.selectbox(
    "🔑 Pilih Akses Login Portal:",
    ["🎓 Siswa", "🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL SISWA (PILIH KATEGORI SOAL & KUIS)
# ==========================================
if peran == "🎓 Siswa":
    st.subheader("🎓 Login Portal Siswa")
    
    if "siswa_logged_in" not in st.session_state:
        st.session_state.siswa_logged_in = False
        st.session_state.siswa_nama = ""
        st.session_state.siswa_jenjang = ""

    if not st.session_state.siswa_logged_in:
        nama_siswa = st.text_input("Nama Lengkap / Panggilan Siswa:")
        pin_siswa = st.text_input("PIN Siswa (4 Angka):", type="password")
        
        if st.button("🚀 Masuk ke Akun Siswa"):
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
                        st.session_state.siswa_jenjang = str(row.get("Jenjang", "SD")).strip().upper()
                        st.rerun()
                    break
            
            if not siswa_found:
                st.error("Nama Siswa atau PIN Siswa salah!")
            elif not is_active:
                st.error("🚫 **Akun Siswa Anda sudah Nonaktif.**")
    else:
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.success(f"Halo, Ananda **{st.session_state.siswa_nama}** ({st.session_state.siswa_jenjang})! Semangat Belajar! 🌟")
        with c_head2:
            if st.button("🚪 Logout Siswa"):
                st.session_state.siswa_logged_in = False
                st.session_state.siswa_nama = ""
                st.session_state.pop("start_time", None)
                st.session_state.pop("kuis_submitted", None)
                st.rerun()
                
        ws_s = sheet.worksheet("Data_Siswa")
        rec_s = ws_s.get_all_records()
        poin_siswa = 0
        
        for r in rec_s:
            if str(r.get("Nama_Lengkap")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                poin_siswa = int(r.get("Poin", 0)) if str(r.get("Poin", "")).isdigit() else 0
                break

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🏆 Poin Koleksi Kamu", value=f"{poin_siswa} / 100 Poin")
            st.progress(min(poin_siswa / 100.0, 1.0))
            if poin_siswa >= 100:
                st.balloons()
                st.success("🎉 Poinmu Sudah ≥ 100! Kamu berhak ikut Undian Hadiah Mbak Fatimah! 🎁")

        with col_m2:
            st.info("💡 Pilih kategori latihan di bawah untuk mengasah kemampuanmu.")

        st.markdown("---")
        siswa_tab1, siswa_tab2 = st.tabs(["📝 Kuis Online & Pilih Kategori", "📈 Grafik Progress Nilai Saya"])
        
        with siswa_tab1:
            st.subheader("🎯 Pilih Kategori Soal Latihan")
            pilihan_kategori = st.selectbox("Filter Kategori Tes:", [
                "Otomatis Sesuai Jenjang Saya", 
                "Bahasa Inggris (Simple Past Tense)", 
                "IPA / IPAS & Usaha Energi", 
                "TOEFL (Listening/Structure/Reading)", 
                "UTBK (Skolastik & Literasi)", 
                "SKD (TWK, TIU, TKP)"
            ])

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
                    try:
                        ws_master = sheet.worksheet("Bank_Soal_Master")
                        all_soal = ws_master.get_all_records()
                        
                        # FILTER BERDASARKAN PILIHAN KATEGORI SISWA
                        if pilihan_kategori == "Bahasa Inggris (Simple Past Tense)":
                            soal_db = [s for s in all_soal if any(k in str(s.get("Teks_Soal", "")).lower() for k in ["i ___", "bali", "past", "did", "was", "were", "verb"])]
                            if not soal_db: soal_db = all_soal[80:130] # Sesuai bank soal B. Inggris
                            topik_nama = "Bahasa Inggris (Past Tense)"
                            mapel_nama = "Bahasa Inggris"
                        elif pilihan_kategori == "IPA / IPAS & Usaha Energi":
                            soal_db = [s for s in all_soal if any(k in str(s.get("Teks_Soal", "")).lower() for k in ["usaha", "energi", "tuas", "kelapa", "gaya"])]
                            if not soal_db: soal_db = all_soal[50:80]
                            topik_nama = "IPA / IPAS (Usaha & Tuas)"
                            mapel_nama = "IPA"
                        elif pilihan_kategori == "TOEFL (Listening/Structure/Reading)":
                            soal_db = [s for s in all_soal if "toefl" in str(s.get("Teks_Soal", "")).lower()]
                            topik_nama = "Simulasi TOEFL"
                            mapel_nama = "TOEFL"
                        elif pilihan_kategori == "UTBK (Skolastik & Literasi)":
                            soal_db = [s for s in all_soal if "utbk" in str(s.get("Teks_Soal", "")).lower()]
                            topik_nama = "Simulasi UTBK"
                            mapel_nama = "UTBK"
                        elif pilihan_kategori == "SKD (TWK, TIU, TKP)":
                            soal_db = [s for s in all_soal if any(k in str(s.get("Teks_Soal", "")).lower() for k in ["skd", "twk", "tiu", "tkp"])]
                            topik_nama = "Simulasi SKD CPNS"
                            mapel_nama = "SKD"
                        else: # Otomatis Sesuai Jenjang
                            jenjang_s = st.session_state.siswa_jenjang
                            if "SD" in jenjang_s or "TK" in jenjang_s:
                                soal_db = all_soal[50:130] # Soal SD / B. Inggris
                                topik_nama = "Latihan Harian SD"
                                mapel_nama = "Tematik"
                            else:
                                soal_db = all_soal[:50] # Soal IPA/Matematika SMP
                                topik_nama = "Latihan Harian SMP/SMA"
                                mapel_nama = "Matematika/IPA"
                    except:
                        soal_db = []
                    
                    jawaban_user = {}
                    if soal_db:
                        for idx, s in enumerate(soal_db[:20], 1): # Batasi max 20 soal tampil per sesi agar ringan
                            st.markdown(f"**Soal No. {idx}**")
                            st.write(s.get('Teks_Soal'))
                            if s.get('URL_Gambar'):
                                st.image(s.get('URL_Gambar'), caption="Gambar Soal", width=250)
                                
                            opsi_raw = str(s.get('Opsi_Jawaban', ''))
                            if opsi_raw and opsi_raw != "nan":
                                opsi_list = [o.strip() for o in opsi_raw.split("|") if o.strip()]
                                jawaban_user[idx] = st.radio(f"Pilih Jawaban No {idx}:", opsi_list, key=f"soal_{idx}")
                            else:
                                jawaban_user[idx] = st.text_input(f"Jawaban No {idx}:", key=f"soal_{idx}")
                            st.markdown("---")
                    else:
                        st.info("Belum ada soal pada kategori ini.")
                        
                    submitted = st.form_submit_button("🚀 Kirim Jawaban Kuis")
                    if submitted and soal_db:
                        total_soal = min(len(soal_db), 20)
                        benar = 0
                        salah_no = []
                        
                        for idx, s in enumerate(soal_db[:20], 1):
                            kunci_raw = str(s.get("Kunci_Jawaban", "")).strip().upper()
                            user_ans = str(jawaban_user.get(idx, "")).strip().upper()
                            
                            if user_ans.startswith(kunci_raw) or user_ans == kunci_raw:
                                benar += 1
                            else:
                                salah_no.append(idx)

                        skor_akhir = round((benar / total_soal) * 100) if total_soal > 0 else 100
                        
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
                                f"Salah di no: {salah_no}" if salah_no else "Semua Benar"
                            ])
                        except:
                            pass
                        
                        st.session_state.kuis_submitted = True
                        st.session_state.hasil_skor = skor_akhir
                        st.session_state.hasil_salah_no = salah_no
                        st.rerun()

            elif st.session_state.get("kuis_submitted", False):
                st.balloons()
                st.success(f"🎉 **Kuis Berhasil Dikirim!**")
                st.markdown(f"### 💯 Skor Kamu: `{st.session_state.get('hasil_skor', 0)} / 100`")
            else:
                st.error("⏰ Waktu Kuis Telah Habis!")
                
        with siswa_tab2:
            st.subheader(f"📈 Grafik Progress Nilai Ananda {st.session_state.siswa_nama}")
            data_grafik_siswa = []
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                for r in ws_r.get_all_records():
                    if str(r.get("Nama_Siswa")).strip().lower() == str(st.session_state.siswa_nama).strip().lower():
                        try:
                            data_grafik_siswa.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": float(r.get("Skor", 0))})
                        except:
                            pass
            except:
                pass
            
            if data_grafik_siswa:
                st.line_chart(pd.DataFrame(data_grafik_siswa).set_index("Tanggal")["Skor"])
            else:
                st.info("Belum ada grafik riwayat nilai.")

# ==========================================
# 2. MODUL TUTOR (DENGAN BROWSE SOAL & CETAK OFFLINE)
# ==========================================
elif peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar Portal")
    
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
                    if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                        is_active = False
                    else:
                        st.session_state.tutor_logged_in = True
                        st.session_state.tutor_nama = row.get("Nama_Pengguna")
                        st.rerun()
                    break
            if not user_found:
                st.error("Username atau PIN salah!")
            elif not is_active:
                st.error("🚫 Akun Anda sudah Nonaktif.")
    else:
        st.success(f"👨‍🏫 **Tutor Aktif:** {st.session_state.tutor_nama}")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.rerun()
            
        st.markdown("---")
        tutor_tab1, tutor_tab2, tutor_tab3, tutor_tab4 = st.tabs([
            "📝 Jurnal & Kontrol Games", 
            "📊 Portofolio Siswa", 
            "📂 Browse & Cetak Soal Offline", 
            "➕ Tambah Soal Baru"
        ])
        
        with tutor_tab1:
            st.header("📖 Diari Kelemahan, Jurnal & Kontrol Games Kelas")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            siswa_aktif = [s.get("Nama_Lengkap") for s in data_siswa_all if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            search_query = st.text_input("🔍 Ketik Nama Siswa yang Sedang Diajar:").strip().lower()
            selected_siswa = None
            
            if search_query:
                hasil_pencarian = [s for s in siswa_aktif if search_query in str(s).strip().lower()]
                if hasil_pencarian:
                    pilihan = st.selectbox("Pilih Siswa:", ["-- Pilih Siswa --"] + hasil_pencarian)
                    if pilihan != "-- Pilih Siswa --":
                        selected_siswa = pilihan
                else:
                    st.warning("Siswa aktif tidak ditemukan.")
            else:
                st.info("💡 Ketik nama siswa di atas untuk mulai menginput jurnal atau memberikan poin games interaktif.")
            
            if selected_siswa:
                st.markdown("---")
                st.subheader(f"🎮 Panel Kelola Games & Poin untuk: {selected_siswa}")
                with st.form("form_tambah_poin_tutor"):
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        jenis_game = st.selectbox("Jenis Modifikasi Games / Tantangan:", [
                            "Kuis Cepat Lisan (Berhitung/Sains)",
                            "Tantangan Logika / Teka-teki",
                            "Games Papan Tulis (Berebut Jawab)",
                            "Bonus Keaktifan Diskusi"
                        ])
                    with col_g2:
                        poin_tambahan = st.number_input("Jumlah Poin Reward:", min_value=5, max_value=50, value=10, step=5)
                        
                    catatan_game = st.text_input("Catatan Keberhasilan Siswa:")
                    if st.form_submit_button("➕ Tambahkan Poin ke Akun Siswa"):
                        try:
                            for idx_s, row_s in enumerate(data_siswa_all, 2):
                                if str(row_s.get("Nama_Lengkap")).strip().lower() == selected_siswa.strip().lower():
                                    current_poin = int(row_s.get("Poin", 0)) if str(row_s.get("Poin", "")).isdigit() else 0
                                    new_poin = current_poin + int(poin_tambahan)
                                    col_p_idx = list(row_s.keys()).index("Poin") + 1 if "Poin" in row_s else 9
                                    ws_siswa.update_cell(idx_s, col_p_idx, new_poin)
                                    st.success(f"✅ Berhasil menambahkan **+{poin_tambahan} Poin** untuk {selected_siswa}! Total Poin: {new_poin}")
                                    break
                        except Exception as ex_p:
                            st.error(f"Gagal memperbarui poin: {ex_p}")

                st.markdown("---")
                st.subheader(f"📝 Input Jurnal Belajar Sesi Ini ({selected_siswa})")
                with st.form("form_jurnal"):
                    tgl = st.date_input("Tanggal Mengajar", datetime.now())
                    mapel = st.selectbox("Mata Pelajaran", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA", "TOEFL", "UTBK", "SKD"])
                    materi = st.text_area("Materi & Pelajaran Hari Ini")
                    pencapaian = st.text_area("Pencapaian Belajar Siswa")
                    kendala = st.text_area("Celah / Kendala Belajar Baru")
                    tingkat_celah = st.select_slider("Tingkat Celah", options=["Rendah", "Sedang", "Tinggi"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        skor = st.text_input("Nilai / Skor Latihan Offline")
                        pr = st.text_input("Tugas / PR")
                    with col2:
                        foto_link = st.text_input("Link Foto Dokumentasi (Opsional)")
                    
                    if st.form_submit_button("💾 Simpan Jurnal & Catatan"):
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
                            st.success("✅ Jurnal Berhasil Disimpan!")
                        except Exception as ex:
                            st.error(f"Gagal: {ex}")

        with tutor_tab2:
            st.header("📊 Portofolio & Histori Sesi Siswa")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            pilih_siswa_histori = st.selectbox("Pilih Nama Siswa:", ["-- Pilih Siswa --"] + [s.get("Nama_Lengkap") for s in data_siswa_all if s.get("Nama_Lengkap")])
            
            if pilih_siswa_histori != "-- Pilih Siswa --":
                st.subheader(f"📈 Grafik Perkembangan Nilai: {pilih_siswa_histori}")
                data_grafik = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == pilih_siswa_histori.strip().lower():
                            data_grafik.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": float(r.get("Skor", 0))})
                except:
                    pass
                if data_grafik:
                    st.line_chart(pd.DataFrame(data_grafik).set_index("Tanggal")["Skor"])
                else:
                    st.info("Belum ada data nilai.")

        # TAB 3: BROWSE & PRINT SOAL OFFLINE
        with tutor_tab3:
            st.header("📂 Browse & Print Bank Soal Offline")
            st.caption("Tutor dapat melihat, menyaring, dan menyiapkan soal dari master database untuk dicetak (Print) atau dibagikan ke siswa.")
            
            try:
                ws_m = sheet.worksheet("Bank_Soal_Master")
                all_bank_soal = ws_m.get_all_records()
            except:
                all_bank_soal = []

            filter_tipe_soal = st.selectbox("Filter Kumpulan Soal:", [
                "Semua Soal Master", 
                "Bahasa Inggris (Past Tense)", 
                "IPA / Usaha & Tuas", 
                "Soal Esai / Pilgan"
            ])

            if all_bank_soal:
                filtered_soal = all_bank_soal
                if "Inggris" in filter_tipe_soal:
                    filtered_soal = all_bank_soal[80:130] if len(all_bank_soal) >= 130 else all_bank_soal
                elif "IPA" in filter_tipe_soal:
                    filtered_soal = all_bank_soal[50:80] if len(all_bank_soal) >= 80 else all_bank_soal
                
                st.info(f"Menampilkan {len(filtered_soal)} butir soal siap cetak:")
                
                for idx, fs in enumerate(filtered_soal, 1):
                    with st.expander(f"Soal No. {idx} ({fs.get('Bentuk_Soal')})"):
                        st.write(f"**Pertanyaan:** {fs.get('Teks_Soal')}")
                        if fs.get('Opsi_Jawaban'):
                            st.write(f"**Pilihan:** {fs.get('Opsi_Jawaban')}")
                        st.success(f"**Kunci Jawaban:** {fs.get('Kunci_Jawaban')}")
            else:
                st.warning("Belum ada data soal di database.")

        with tutor_tab4:
            st.header("➕ Tambah Soal Baru ke Master Bank Soal")
            with st.form("form_tambah_soal"):
                bentuk = st.selectbox("Bentuk Soal:", ["Pilgan", "Essay"])
                teks_soal = st.text_area("Teks Soal:")
                url_gambar = st.text_input("Link Gambar (Opsional):")
                opsi = st.text_input("Opsi Jawaban (Pisahkan dengan | ):", placeholder="A. ... | B. ... | C. ... | D. ...")
                kunci = st.text_input("Kunci Jawaban:")
                if st.form_submit_button("Simpan Soal"):
                    sheet.worksheet("Bank_Soal_Master").append_row([bentuk, teks_soal, url_gambar, opsi, kunci])
                    st.success("Soal berhasil disimpan ke database!")

# ==========================================
# 3. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola Bimbel")
    pin_owner = st.text_input("PIN Pengelola:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Diizinkan 👋")
        tab1, tab2, tab3 = st.tabs(["🎁 Undian Hadiah Siswa (Poin ≥ 100)", "👥 Kelola Status Akun", "📚 Master Bank Soal"])
        
        with tab1:
            st.markdown("### 🎁 Pengundian Hadiah Giveaway")
            ws_siswa = sheet.worksheet("Data_Siswa")
            data_siswa_all = ws_siswa.get_all_records()
            peserta_undian = [s for s in data_siswa_all if int(s.get("Poin", 0) if str(s.get("Poin", "")).isdigit() else 0) >= 100]
            if peserta_undian:
                st.dataframe(pd.DataFrame(peserta_undian))
                if st.button("🎲 Undi Pemenang Sekarang!"):
                    pemenang = random.choice(peserta_undian)
                    st.balloons()
                    st.success(f"🎉 PEMENANG GIVEAWAY: **{pemenang['Nama_Lengkap']}** ({pemenang['Jenjang']})!")
            else:
                st.info("Belum ada siswa mencapai 100 poin.")
        with tab2:
            st.dataframe(pd.DataFrame(ws_siswa.get_all_records())[["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]])
        with tab3:
            st.dataframe(sheet.worksheet("Bank_Soal_Master").get_all_records())
    elif pin_owner:
        st.error("PIN Salah!")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua")
    nama_anak = st.text_input("Nama Putra/Putri:")
    pin_ortu = st.text_input("PIN Orang Tua (4 Angka):", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws_siswa = sheet.worksheet("Data_Siswa")
        data_siswa = ws_siswa.get_all_records()
        ortu_found = False
        
        for row in data_siswa:
            if str(row.get("Nama_Lengkap")).strip().lower() == nama_anak.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_ortu.strip():
                ortu_found = True
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(f"**Jenjang:** {row.get('Jenjang')} | **Poin Undian:** `{row.get('Poin', 0)} Poin`")
                st.markdown("---")
                
                data_g_ortu = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == nama_anak.strip().lower():
                            data_g_ortu.append({"Tanggal": str(r.get("Waktu_Selesai"))[:10], "Skor": float(r.get("Skor", 0))})
                except:
                    pass
                if data_g_ortu:
                    st.line_chart(pd.DataFrame(data_g_ortu).set_index("Tanggal")["Skor"])
                else:
                    st.info("Belum ada data grafik nilai.")
                break
        if not ortu_found:
            st.error("Nama atau PIN Salah!")
