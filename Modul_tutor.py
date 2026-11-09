function buatHeaderOtomatis() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Data konfigurasi tab dan header masing-masing
  var targetTab = {
    "Bank_Soal_Materi": ["Kode_Materi", "Jenjang_Dan_Mapel", "Bab_Atau_Topik", "Bentuk_Soal", "Capaian_Kompetensi", "Teks_Soal", "URL_Gambar", "Opsi_Jawaban", "Kunci_Jawaban"],
    "Bank_Soal_Paket": ["Kode_Paket", "Jenjang_Dan_Kategori", "Nomor_Paket", "Bentuk_Soal", "Teks_Soal", "URL_Gambar", "Opsi_Jawaban", "Kunci_Jawaban", "Bobot_Nilai"],
    "Bank_Soal_Olimpiade": ["Kode_Olimpiade", "Jenjang_Dan_Bidang", "Tingkat_Seleksi", "Bentuk_Soal", "Teks_Soal", "URL_Gambar", "Opsi_Jawaban", "Kunci_Jawaban", "Pembahasan_Lengkap"]
  };
  
  for (var namaTab in targetTab) {
    var sheet = ss.getSheetByName(namaTab);
    // Jika tab belum ada, buat baru secara otomatis
    if (!sheet) {
      sheet = ss.insertSheet(namaTab);
    }
    // Masukkan header ke baris 1 secara otomatis
    var headers = targetTab[namaTab];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }
}
