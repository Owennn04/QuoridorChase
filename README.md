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
| **Week 2** | **2.1 Algoritma Minimax & Alpha-Beta** | Mengimplementasikan algoritma Minimax, Alpha-Beta Pruning, serta Candidate Move Filtering. | Deus, Althaf | Next |
| **Week 2** | **2.2 A* Pathfinding & Heuristik** | Mengembangkan A* Pathfinding (X, Y, Has_Smash) serta fungsi evaluasi heuristik h(s) berbasis Confinement Score dan Rope-Awareness. | Michelle, Owen | Next |
| **Week 3** | **3.1 Simulasi & Pengujian Performa** | Melakukan simulasi pertandingan uji coba, mengukur win rate, eksplorasi node, dan execution time. | Michelle | Planned |
| **Week 3** | **3.2 Analisis & Penyusunan Laporan** | Menganalisis hasil evaluasi sistem, perbaikan bug, dan finalisasi laporan akhir proposal. | Seluruh Tim | Planned |

---

## Struktur Direktori (Bagian 1.2)

```text
QuoridorChase/
├── config.py                                        # Konstanta geometri 9x9, timer, skor, cooldown
├── engine/
│   ├── __init__.py                                  # Paket engine & export fungsi utama
│   ├── state.py                                     # Class GameState (S), S0, clone, terminal, utility U(s)
│   ├── rules.py                                     # Aturan gerak ortogonal, Smash, Rope, BFS No-Cage
│   └── transition.py                                # Model transisi T(s,a), wall decay, welding, scoring
├── tests/
│   └── test_section_1_2.py                          # 8 Unit test Pytest untuk verifikasi Bagian 1.2
├── docs/
│   └── Bagian_1_2_Pemodelan_State_Space_dan_PEAS.md # Dokumen formal spesifikasi P.E.A.S & State Space
└── Bagian_1_2_Pemodelan_State_Space_dan_PEAS.ipynb  # Notebook interaktif demonstrasi mekanik game
```

---

## Cara Menjalankan Pengujian

1. **Jalankan Unit Test dengan Pytest:**
   ```bash
   python -m pytest tests/test_section_1_2.py -v
   ```

2. **Jalankan Notebook Interaktif:**
   Buka file `Bagian_1_2_Pemodelan_State_Space_dan_PEAS.ipynb` di VS Code / Jupyter Lab dan jalankan setiap cell secara berurutan.
