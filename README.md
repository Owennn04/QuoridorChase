# Quoridor Chase: Lockdown

**Course:** Artificial Intelligence (Semester 5) — Universitas Ciputra  
**Kelompok:** Grup BESAR  
1. **Amadeus Ian Gunadi (Deus)** — `0706012410051`
2. **Christian Owen Tengkawan (Owen)** — `0706012410048`
3. **Michelle Mercy Phe (Michelle)** — `0706012410010`
4. **Muhammad Althaf Hilmi (Althaf)** — `0706012410065`

---

## Progress Timeline & PIC

| Week | Bagian | Deskripsi | PIC | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Week 1** | **1.1 Persiapan & Arsitektur Sistem** | Menyiapkan lingkungan pengembangan, repositori, dan kerangka dasar. | Owen | Selesai |
| **Week 1** | **1.2 Pemodelan State Space & P.E.A.S** | Merumuskan state space, aturan main, model transisi, dan spesifikasi P.E.A.S secara mendetail. | **Deus, Althaf** | **Selesai** |
| **Week 2** | **2.1 Algoritma Minimax & Alpha-Beta** | Mengimplementasikan algoritma Minimax, Alpha-Beta Pruning (Dual Mode Toggle), serta Candidate Move Filtering. | **Deus, Althaf** | **Selesai** |
| **Week 2** | **2.2 A* Pathfinding & Heuristik** | Mengembangkan A* Pathfinding (X, Y, Has_Smash) serta fungsi evaluasi heuristik h(s) berbasis Confinement Score dan Rope-Awareness. | Michelle, Owen | Selesai |
| **Week 3** | **3.1 Simulasi & Pengujian Performa** | Melakukan simulasi pertandingan uji coba, mengukur win rate, eksplorasi node, dan execution time. | Michelle | Planned |
| **Week 3** | **3.2 Analisis & Penyusunan Laporan** | Menganalisis hasil evaluasi sistem, perbaikan bug, dan finalisasi laporan akhir proposal. | Seluruh Tim | Planned |

---

## Struktur Direktori Proyek

```text
QuoridorChase/
├── config.py                 # Konstanta geometri 9x9, timer, skor, cooldown, bobot heuristik
├── requirements.txt          # Dependensi eksternal (pygame-ce)
├── readme.txt                # Panduan instruksi, library, IDE, dan setup cara menjalankan
├── README.md                 # Dokumentasi ringkas proyek
├── engine/
│   ├── __init__.py           # Paket engine & export fungsi utama
│   ├── state.py              # Class GameState (S), S0, clone, terminal, utility U(s)
│   ├── rules.py              # Aturan gerak ortogonal, Smash, Rope, BFS No-Cage
│   └── transition.py         # Model transisi T(s,a), wall decay, welding, scoring
└── src/
    ├── ai/
    │   ├── __init__.py       # Ekspor paket AI
    │   ├── minimax.py        # Minimax & Alpha-Beta Pruning (Dual Mode Toggle)
    │   ├── pathfinding.py    # 3D A* Pathfinding (x, y, has_smash)
    │   └── heuristic.py      # Fungsi evaluasi h(s) berbasis Confinement Score & Rope
    └── core/
        └── ui.py             # GUI Interaktif Pygame (Visual board, HUD, controls)
```

---

## Cara Menjalankan Game

1. **Instal Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Jalankan Aplikasi GUI Game:**
   ```bash
   python -m src.core.ui
   ```

3. **Kontrol Utama:**
   - **WASD / Tombol Panah**: Bergerak ortogonal
   - **W / Klik Kiri Mouse**: Memasang tembok rintangan
   - **R**: Memutar orientasi tembok (horizontal/vertikal)
   - **E**: Grappling Rope (melompati rintangan)
   - **Space**: Smash Attack (menghancurkan rintangan)
   - **P**: Toggle Auto-Play AI
   - **T**: Toggle Mode Alpha-Beta Pruning / Pure Minimax
   - **F1**: Reset ke State Awal (S0)
   - **ESC**: Keluar permainan
