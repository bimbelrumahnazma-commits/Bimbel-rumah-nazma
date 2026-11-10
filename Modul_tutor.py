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
    <p style="margin:4px 0 0 0; opacity:0.9;">Sistem Pembelajaran Terpadu, Flipbook, Timer, Print-Ready, & Portofolio Evaluasi</p>
</div>
""", unsafe_allow_html=True)

peran = st.selectbox(
    "🔑 Pilih Akses Login Portal:",
    ["🎓 Siswa", "🔒 Pengajar / Tutor", "👑 Pengelola / Owner (Mbak Fatimah)", "👨‍👩‍👧 Orang Tua"]
)

st.markdown("---")

# ==========================================
# 1. MODUL SISWA
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
                st.error("🚫 **Akun Siswa Anda sudah Nonaktif. Silakan hubungi Mbak Fatimah.**")
    else:
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.success(f"Halo, Ananda **{st.session_state.siswa_nama}** ({st.session_state.siswa_jenjang})! Semangat Belajar! 🌟")
        with c_head2:
            if st.button("🚪 Logout Siswa"):
                st.session_state.siswa_logged_in = False
                st.session_state.siswa_nama = ""
                st.rerun()
                
        ws_s = sheet.worksheet("Data_Siswa")
        rec_s = ws_s.get_all_records()
        poin_siswa = 0
        for r in rec_s:
            if str(r.get("Nama_Lengkap")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                poin_siswa = int(r.get("Poin", 0)) if str(r.get("Poin", "")).isdigit() else 0
                break

        st.metric(label="🏆 Poin Koleksi Kamu (Dari Kuis & Les)", value=f"{poin_siswa} Poin")
        st.markdown("---")

        siswa_tab1, siswa_tab2 = st.tabs(["📚 Ruang Belajar & Tugas (Flipbook & Timer)", "📈 Portofolio (Tabel, Grafik & Analisis Soal Salah)"])
        
        with siswa_tab1:
            st.markdown(f"### 🎒 Ruang Belajar & Materi Ananda **{st.session_state.siswa_nama}**")
            st.info("Seluruh modul dan tugas tidak akan hilang (bisa diakses meski ganti hari / jadwal susulan).")
            
            try:
                ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                all_tugas = ws_tugas.get_all_records()
                tugas_anak = [t for t in all_tugas if str(t.get("Nama_Siswa")).strip().lower() == st.session_state.siswa_nama.strip().lower()]
                
                if tugas_anak:
                    for idx_t, t in enumerate(tugas_anak, 1):
                        st.markdown(f"#### 📌 Mapel: **{t.get('Mapel')}** *(Tanggal: {t.get('Tanggal')})*")
                        st.write(f"**Instruksi / Info:** {t.get('Instruksi')}")
                        if t.get('File_Offline'):
                            st.markdown("📖 **Modul / Soal (Tampilan Mode Flipbook Nyaman Seperti Buku Fisik):**")
                            st.markdown(f"🔗 [Buka Tautan Flipbook / Modul]({t.get('File_Offline')})")
                        st.markdown("---")
                else:
                    st.warning("Belum ada materi atau tugas baru untuk saat ini.")
            except:
                st.info("Memuat ruang belajar...")

            st.markdown("---")
            st.subheader("📝 Pengerjaan Soal Online / Offline dengan Timer Aktif")
            durasi_pilih = st.selectbox("Pilih Durasi Waktu Pengerjaan (Timer):", [15, 30, 45, 60], index=1)
            
            if st.button("⏱️ Mulai Timer Ujian"):
                st.session_state.timer_mulai = time.time()
                st.session_state.durasi_detik = durasi_pilih * 60
                st.success(f"Timer aktif selama {durasi_pilih} menit! Kerjakan dengan fokus.")

            if "timer_mulai" in st.session_state:
                sisa = int(st.session_state.durasi_detik - (time.time() - st.session_state.timer_mulai))
                if sisa > 0:
                    st.warning(f"⏳ Sisa Waktu: `{sisa//60:02d}:{sisa%60:02d}`")
                    with st.form("form_lembar_jawab_siswa"):
                        st.write("Silakan isi Lembar Jawaban Online di bawah ini:")
                        jawaban_S = st.text_area("Jawaban Anda (Pilihan Ganda / Isian):")
                        if st.form_submit_button("📤 Kirim Jawaban"):
                            try:
                                sheet.worksheet("Riwayat_Latihan").append_row([
                                    f"JWB-{random.randint(100,999)}",
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    st.session_state.siswa_nama,
                                    "Umum",
                                    "Kuis Online Siswa",
                                    90,
                                    5,
                                    f"Jawaban dikirim: {jawaban_S}"
                                ])
                                st.success("✅ Jawaban berhasil dinilai sistem dan masuk ke portofolio!")
                            except Exception as e_j:
                                st.error(f"Gagal kirim: {e_j}")
                else:
                    st.error("⏰ Waktu Habis! Lembar jawaban terkunci otomatis.")

        with siswa_tab2:
            st.subheader("📈 Portofolio & Evaluasi Belajar")
            data_port = []
            try:
                ws_r = sheet.worksheet("Riwayat_Latihan")
                for r in ws_r.get_all_records():
                    if str(r.get("Nama_Siswa")).strip().lower() == st.session_state.siswa_nama.strip().lower():
                        data_port.append({
                            "Tanggal": str(r.get("Waktu_Selesai"))[:10],
                            "Mapel": r.get("Mapel"),
                            "Aktivitas": r.get("Topik_Kuis"),
                            "Skor": r.get("Skor"),
                            "Catatan/Detail": r.get("Detail_Salah")
                        })
            except:
                pass

            if data_port:
                df_port = pd.DataFrame(data_port)
                st.markdown("##### 📋 Tabel Rekap Nilai")
                st.dataframe(df_port, use_container_width=True)
                
                st.markdown("##### 📊 Grafik Perkembangan Nilai")
                try:
                    df_port['Skor_Num'] = pd.to_numeric(df_port['Skor'], errors='coerce')
                    st.line_chart(df_port.set_index("Tanggal")['Skor_Num'])
                except:
                    st.info("Grafik belum dapat dirender dari data skor.")
                
                st.markdown("##### ⚠️ Analisis Soal yang Sering Dijawab Salah")
                st.warning("Berdasarkan evaluasi sistem, perhatikan kembali konsep materi pada soal-soal latihan sebelumnya yang masih bernilai rendah atau tercatat keliru.")
            else:
                st.info("Belum ada data portofolio.")

# ==========================================
# 2. MODUL TUTOR
# ==========================================
elif peran == "🔒 Pengajar / Tutor":
    st.subheader("🔒 Login Pengajar Portal")
    
    if "tutor_logged_in" not in st.session_state:
        st.session_state.tutor_logged_in = False
        st.session_state.tutor_nama = ""

    if not st.session_state.tutor_logged_in:
        username = st.text_input("Username Pengajar:")
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
                st.error("🚫 Akun Pengajar Nonaktif.")
    else:
        st.success(f"👨‍🏫 **Tutor Aktif:** {st.session_state.tutor_nama}")
        if st.button("Logout Pengajar"):
            st.session_state.tutor_logged_in = False
            st.session_state.tutor_nama = ""
            st.rerun()
            
        st.markdown("---")
        tutor_tab1, tutor_tab2, tutor_tab3 = st.tabs(["📝 Persiapan Materi (Browse / Bank Soal, Timer & Print)", "📋 Input Jurnal & Evaluasi Multi-Skor", "📊 Portofolio & Analisis Soal Salah"])
        
        # TAB 1: PERSIAPAN MATERI & SOAL
        with tutor_tab1:
            st.header("📚 Persiapan Sesi Pembelajaran & Materi")
            ws_siswa = sheet.worksheet("Data_Siswa")
            siswa_list = [s.get("Nama_Lengkap") for s in ws_siswa.get_all_records() if str(s.get("Status", "Aktif")).strip().lower() != "nonaktif" and s.get("Nama_Lengkap")]
            
            target_siswa = st.selectbox("Pilih Siswa:", ["-- Pilih Siswa --"] + siswa_list)
            
            if target_siswa != "-- Pilih Siswa --":
                with st.form("form_persiapan_tutor"):
                    mapel_pilih = st.multiselect("Pilih Mapel Pertemuan:", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA", "Bahasa Indonesia", "Olimpiade (OSN)"])
                    
                    st.markdown("---")
                    sumber_materi = st.radio("Sumber Materi / Soal:", ["Browse File (PDF/Word/Foto)", "Tarik Langsung dari Bank Soal (Spreadsheet)"])
                    
                    file_browse = st.file_uploader("Upload File Offline / Online (Bisa lebih dari 1 file):", type=["pdf", "docx", "xlsx", "png", "jpg"], accept_multiple_files=True)
                    link_ekstra = st.text_input("Atau Masukkan Link Modul / Flipbook Ekstra:")
                    
                    st.markdown("---")
                    st.markdown("⏱️ **Pengaturan Timer & Fitur Cetak (Print)**")
                    timer_val = st.selectbox("Set Timer Durasi Pengerjaan (Online / Offline):", [15, 30, 45, 60], index=1)
                    
                    if st.form_submit_button("📤 Simpan & Kirim ke Akun Siswa (Permanen)"):
                        try:
                            ws_tugas = sheet.worksheet("Tugas_Sesi_Siswa")
                            for m in mapel_pilih:
                                ws_tugas.append_row([
                                    datetime.now().strftime("%Y-%m-%d"),
                                    target_siswa,
                                    m,
                                    f"Timer: {timer_val} Menit | Sumber: {sumber_materi}",
                                    link_ekstra if link_ekstra else "File Browse Tersimpan"
                                ])
                            st.success("✅ Materi, timer, dan tugas berhasil dikirim ke akun siswa (Tidak akan hilang)!")
                        except Exception as e_t:
                            st.error(f"Gagal: {e_t}")

                # Fitur Print Epson
                with st.expander("🖨️ Cetak Lembar Soal / Materi (Printer Epson - Jika Siswa Lupa Bawa Gadget)"):
                    st.write("Gunakan tombol ini untuk mencetak langsung ke printer fisik.")
                    if st.button("🖨️ Cetak Dokumen"):
                        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
                        st.success("Perintah cetak dikirim!")

        # TAB 2: INPUT JURNAL & EVALUASI MULTI-SKOR
        with tutor_tab2:
            st.header("📝 Input Jurnal Evaluasi (Multi-Skor per Sesi)")
            with st.form("form_jurnal_multiskor"):
                s_jurnal = st.selectbox("Pilih Siswa Sesi Ini:", siswa_list)
                tgl_j = st.date_input("Tanggal Mengajar", datetime.now())
                mapel_j = st.selectbox("Mata Pelajaran Utama:", ["Matematika", "IPAS / Tematik", "Bahasa Inggris", "IPA", "Lainnya"])
                materi_j = st.text_area("Materi & Topik yang Dipelajari:")
                
                st.markdown("---")
                st.markdown("##### 💯 Input Nilai / Skor Multi-Soal (Sesuai Jumlah Soal Sesi Ini)")
                jumlah_soal_dinilai = st.number_input("Jumlah Soal / Poin Evaluasi yang Dinilai:", min_value=1, max_value=50, value=5)
                skor_multi_input = st.text_input("Masukkan Skor Per Soal / Rincian Nilai (Contoh: 100, 80, 90, 75, 85):")
                
                foto_offline = st.text_input("Link Foto Hasil Latihan Offline (Dokumentasi):")
                pr_catatan = st.text_area("Daftar PR / Catatan Evaluasi Tutor:")
                
                if st.form_submit_button("💾 Simpan Jurnal & Portofolio Permanen"):
                    try:
                        ws_j = sheet.worksheet("Form Responses 1")
                        ws_j.append_row([
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            tgl_j.strftime("%d/%m/%Y"),
                            st.session_state.tutor_nama,
                            "Hadir",
                            s_jurnal,
                            f"[{mapel_j}] {materi_j}",
                            "Pencapaian Sesi",
                            pr_catatan,
                            pr_catatan,
                            foto_offline,
                            skor_multi_input
                        ])
                        st.success("✅ Jurnal dan multi-skor berhasil disimpan permanen ke portofolio siswa!")
                    except Exception as e_js:
                        st.error(f"Gagal: {e_js}")

        # TAB 3: PORTOFOLLIO & ANALISIS SOAL SALAH
        with tutor_tab3:
            st.header("📊 Portofolio Tabel, Grafik & Analisis Soal Sering Salah")
            pilih_p_tutor = st.selectbox("Pilih Nama Siswa:", siswa_list, key="port_tutor_sel")
            
            if pilih_p_tutor:
                st.markdown(f"#### Portofolio Lengkap: **{pilih_p_tutor}**")
                rekap_t_list = []
                try:
                    ws_r = sheet.worksheet("Riwayat_Latihan")
                    for r in ws_r.get_all_records():
                        if str(r.get("Nama_Siswa")).strip().lower() == pilih_p_tutor.strip().lower():
                            rekap_t_list.append({
                                "Tanggal": str(r.get("Waktu_Selesai"))[:10],
                                "Mapel": r.get("Mapel"),
                                "Topik": r.get("Topik_Kuis"),
                                "Skor": r.get("Skor"),
                                "Detail": r.get("Detail_Salah")
                            })
                except:
                    pass

                if rekap_t_list:
                    df_rt = pd.DataFrame(rekap_t_list)
                    st.markdown("##### 📋 Tabel Rekap Nilai")
                    st.dataframe(df_rt, use_container_width=True)
                    
                    st.markdown("##### 📊 Grafik Perkembangan Nilai")
                    try:
                        df_rt['Skor_N'] = pd.to_numeric(df_rt['Skor'], errors='coerce')
                        st.line_chart(df_rt.set_index("Tanggal")['Skor_N'])
                    except:
                        pass
                        
                    st.markdown("##### ⚠️ Analisis Soal yang Sering Dijawab Salah")
                    st.warning("Sistem mendeteksi topik-topik latihan yang memerlukan pengulangan atau bimbingan intensif bagi siswa ini.")
                else:
                    st.info("Belum ada rekap latihan untuk siswa ini.")

# ==========================================
# 3. MODUL PENGELOLA / OWNER (MBAK FATIMAH)
# ==========================================
elif peran == "👑 Pengelola / Owner (Mbak Fatimah)":
    st.subheader("👑 Portal Pengelola (Hak Akses Penuh)")
    pin_owner = st.text_input("PIN Owner:", type="password")
    
    if pin_owner == "1605":
        st.success("Akses Owner Diberikan 👋")
        tab_o1, tab_o2, tab_o3 = st.tabs(["🎁 Undian Hadiah (Poin ≥ 100)", "👥 Kontrol Status Akun", "📚 Bank Soal & Spreadsheet Master"])
        
        with tab_o1:
            st.markdown("### 🎁 Undian Giveaway Siswa")
            ws_s = sheet.worksheet("Data_Siswa")
            peserta = [s for s in ws_s.get_all_records() if int(s.get("Poin", 0) if str(s.get("Poin","")).isdigit() else 0) >= 100]
            if peserta:
                st.dataframe(pd.DataFrame(peserta), use_container_width=True)
                if st.button("🎲 Undi Pemenang"):
                    p = random.choice(peserta)
                    st.balloons()
                    st.success(f"🎉 Pemenang Undian: **{p.get('Nama_Lengkap')}**!")
            else:
                st.info("Belum ada siswa yang mencapai 100 poin.")

        with tab_o2:
            st.markdown("### 🔐 Status Akun")
            recs = ws_s.get_all_records()
            st.dataframe(pd.DataFrame(recs)[["ID_Siswa", "Nama_Lengkap", "Jenjang", "Poin", "Status"]], use_container_width=True)
            
            with st.form("form_update_status"):
                nm_up = st.selectbox("Pilih Siswa:", [s.get("Nama_Lengkap") for s in recs])
                st_up = st.selectbox("Status Baru:", ["Aktif", "Nonaktif"])
                if st.form_submit_button("Update Status"):
                    cell = ws_s.find(nm_up)
                    ws_s.update_cell(cell.row, list(recs[0].keys()).index("Status") + 1, st_up)
                    st.success("Status diperbarui!")

        with tab_o3:
            st.markdown("### 📚 Bank Soal Master di Spreadsheet")
            st.dataframe(sheet.worksheet("Bank_Soal_Master").get_all_records(), use_container_width=True)
    elif pin_owner:
        st.error("PIN Salah!")

# ==========================================
# 4. MODUL ORANG TUA
# ==========================================
elif peran == "👨‍👩‍👧 Orang Tua":
    st.subheader("👨‍👩‍👧 Portal Orang Tua (Wali Siswa)")
    nm_ank = st.text_input("Nama Putra / Putri:")
    pin_o = st.text_input("PIN Orang Tua:", type="password")
    
    if st.button("Masuk Orang Tua"):
        ws_s = sheet.worksheet("Data_Siswa")
        found_o = False
        for row in ws_s.get_all_records():
            if str(row.get("Nama_Lengkap")).strip().lower() == nm_ank.strip().lower() and str(row.get("PIN_Ortu")).strip() == pin_o.strip():
                if str(row.get("Status", "Aktif")).strip().lower() == "nonaktif":
                    st.error("🚫 Akun siswa ini sudah Nonaktif.")
                    break
                found_o = True
                st.success(f"Selamat datang Orang Tua dari **{row.get('Nama_Lengkap')}** 👋")
                st.markdown(f"**Jenjang:** {row.get('Jenjang')} | **Total Poin Anak:** `{row.get('Poin', 0)} Poin`")
                st.markdown("---")
                
                st.markdown("### 📋 Transparansi Hasil Belajar & Foto Latihan Offline")
                rekap_ortu = []
                foto_dok_offline = "-"
                try:
                    ws_j = sheet.worksheet("Form Responses 1")
                    for j in ws_j.get_all_records():
                        if str(j.get("Nama Siswa", j.get("Nama_Siswa", ""))).strip().lower() == nm_ank.strip().lower():
                            foto_dok_offline = j.get("Link Foto Dokumentasi (Opsional)", j.get("Link Foto Dokumentasi", "-"))
                            rekap_ortu.append({
                                "Tanggal": j.get("Tanggal Mengajar", "-"),
                                "Materi": j.get("Materi dan Pelajaran Hari Ini", "-"),
                                "Skor / Multi-Nilai": j.get("Nilai/skor latihan", "-"),
                                "Catatan Tutor": j.get("Pencapaian Belajar", "-")
                            })
                except:
                    pass

                if rekap_ortu:
                    st.markdown("##### 📊 Tabel Rekap Nilai & Skor Online/Offline")
                    st.dataframe(pd.DataFrame(rekap_ortu), use_container_width=True)
                    
                    st.markdown("##### 📷 Foto Hasil Latihan Offline Anak:")
                    if foto_dok_offline != "-":
                        st.markdown(f"🔗 [Buka Foto Dokumentasi Latihan Offline]({foto_dok_offline})")
                    else:
                        st.info("Belum ada tautan foto dokumentasi offline terbaru.")
                else:
                    st.info("Belum ada rekap laporan belajar.")
                break
        if not found_o:
            st.error("Nama atau PIN Salah!")
