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
├── config.py                                        # Konstanta geometri 9x9, timer, skor, cooldown, bobot heuristik
├── engine/
│   ├── __init__.py                                  # Paket engine & export fungsi utama
│   ├── state.py                                     # Class GameState (S), S0, clone, terminal, utility U(s)
│   ├── rules.py                                     # Aturan gerak ortogonal, Smash, Rope, BFS No-Cage
│   └── transition.py                                # Model transisi T(s,a), wall decay, welding, scoring
├── src/ai/
│   ├── __init__.py                                  # Ekspor paket AI cerdas
│   ├── minimax.py                                   # Minimax & Alpha-Beta Pruning (Dual Mode Toggle), Candidate Filtering
│   ├── pathfinding.py                               # 3D A* Pathfinding (x, y, has_smash)
│   └── heuristic.py                                 # Fungsi evaluasi h(s) lengkap (W1-W5, Confinement, Rope)
├── tests/
│   ├── test_section_1_2.py                          # 8 Unit test untuk verifikasi Bagian 1.2
│   └── test_section_2_1.py                          # 6 Unit test untuk verifikasi Bagian 2.1 (Dual mode, pruning, latency)
├── docs/
│   └── Bagian_1_2_Pemodelan_State_Space_dan_PEAS.md # Dokumen formal spesifikasi P.E.A.S & State Space
├── Bagian_1_2_Pemodelan_State_Space_dan_PEAS.ipynb  # Notebook interaktif demonstrasi mekanik game
└── Bagian_2_1_Minimax_dan_Alpha_Beta.ipynb          # Notebook interaktif dengan Tombol Toggle Mode Minimax & Alpha-Beta
```

---

## Cara Menjalankan Pengujian

1. **Jalankan Unit Test Bagian 1.2:**
   ```bash
   py -c "import sys; sys.modules['pytest']=type('pytest',(),{}); import tests.test_section_1_2 as t; [getattr(t, f)() for f in dir(t) if f.startswith('test_')]; print('Semua test 1.2 Lulus!')"
   ```

2. **Jalankan Unit Test Bagian 2.1:**
   ```bash
   py -c "import tests.test_section_2_1 as t; [getattr(t, f)() for f in dir(t) if f.startswith('test_')]; print('Semua test 2.1 Lulus!')"
   ```

3. **Jalankan Notebook Interaktif:**
   Buka file `Bagian_2_1_Minimax_dan_Alpha_Beta.ipynb` di VS Code / Jupyter Lab untuk mencoba tombol toggle interaktif antara Alpha-Beta Pruning dan Pure Minimax secara visual.
