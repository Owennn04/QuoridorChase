# Dokumen Spesifikasi Desain & Formalisasi Bagian 1.2
## Proyek: Quoridor Chase: Lockdown
**Mata Kuliah:** Artificial Intelligence (Semester 5) — Universitas Ciputra  
**Tim:** Grup BESAR  
**Penanggung Jawab (PIC) Bagian 1.2:**  
1. **Amadeus Ian Gunadi (Deus)** — `0706012410051`  
2. **Muhammad Althaf Hilmi (Althaf)** — `0706012410065`  

---

## 1. Pendahuluan & Latar Belakang Desain

Permainan *Quoridor Chase: Lockdown* merupakan modifikasi asimetris dari permainan strategi abstrak *Quoridor*. Dalam varian ini, **2 pemain manusia kooperatif (*Runners*)** berhadapan dengan **1 agen cerdas (*AI Boss*)** di atas papan planar grid berukuran $9 \times 9$.

Tujuan utama tim Runners adalah mengumpulkan *Data Orbs* (poin) dan bertahan hidup selama mungkin dari kejaran AI Boss, sementara AI Boss bertujuan mengejar dan menangkap (*tag*) para Runners serta memblokir jalur pelarian mereka.

Dokumen ini merumuskan secara mendalam dan matematis seluruh komponen **Bagian 1.2: Pemodelan State Space & P.E.A.S**, yang menjadi landasan utama bagi algoritma pencarian adversarial (*Minimax*, *Alpha-Beta Pruning*, dan *A\* Pathfinding*) pada tahap-tahap berikutnya.

---

## 2. Spesifikasi P.E.A.S (*Intelligent Agent Framework*)

Agen cerdas (khususnya AI Boss) dimodelkan menggunakan kerangka kerja P.E.A.S (*Performance Measure, Environment, Actuator, Sensor*):

### 2.1 Performance Measure ($P$)
Fungsi performa mengukur keberhasilan AI Boss dalam menjalankan perannya:
1. **Rasio Kemenangan (*Win Rate*):** Persentase kemenangan AI Boss terhadap tim Runners pada akhir batas waktu 5 menit.
2. **Selisih Skor Kumulatif (*Score Differential*):** Selisih antara poin tangkapan AI Boss ($+40$ poin/tangkapan) dan total poin orb yang dikumpulkan Runners ($+15$ poin/orb).
3. **Efisiensi Waktu Berpikir (*Latency*):** Waktu respon rata-rata per langkah tetap di bawah ambang batas interaktif ($< 1$ detik per langkah).
4. **Efisiensi Eksplorasi Node (*Search Reduction*):** Jumlah node pohon pencarian yang dievaluasi dengan pemangkasan *Alpha-Beta Pruning* dibandingkan *Minimax* murni.

### 2.2 Environment ($E$)
* **Arena:** Grid planar 2 dimensi $9 \times 9$ (81 petak sel) dengan koordinat $(r, c) \in \{0..8\} \times \{0..8\}$.
* **Entitas:** 2 Runners (manusia, kooperatif), 1 AI Boss (adversarial), dan 3 *Data Orbs* aktif.
* **Tembok Dinamis:** Tembok ditempatkan di antara petak (alur/*groove*). Tembok dapat berupa *Solo Wall* (temporer, $TTL = 2$ giliran), *Co-op Wall Welding* (permanen), atau tembok AI Boss. Tembok dapat dihancurkan oleh skill *Juggernaut Smash*.
* **Batas Waktu Pertandingan:** Total waktu pertandingan maksimal 5 menit (300 detik) dengan batas waktu per giliran (*shot clock*) 10 detik.

#### Sifat Lingkungan (*Environment Properties*):
1. **Fully Observable:** Agen AI memiliki akses lengkap ke seluruh kondisi papan: koordinat semua agen, posisi semua tembok aktif, lokasi semua orb, cooldown skill, dan sisa item pemain tanpa *fog of war*.
2. **Deterministic:** Setiap aksi yang diambil agen (perpindahan posisi, peletakan tembok, atau penggunaan skill) menghasilkan *state* baru yang pasti tanpa ada faktor probabilitas atau dadu acak.
3. **Multi-Agent (Adversarial & Cooperative):** Lingkungan terdiri dari 3 agen interaktif. Hubungan antara AI Boss vs Runners adalah *adversarial zero-sum competitive*, sedangkan hubungan antar kedua Runner adalah *pure cooperative*.
4. **Sequential:** Keputusan dan aksi dieksekusi secara bergantian berbasis giliran (*turn-based*), di mana langkah agen di masa sekarang mempengaruhi pilihan langkah di masa depan.
5. **Semi-Dynamic:** Status fisik papan tidak berubah selama agen sedang melakukan kalkulasi pencarian (*thinking time*), namun terdapat jam batas waktu total (5 menit) yang terus berjalan mundur.
6. **Discrete:** Ruang keadaan, waktu giliran, lokasi sel, orientasi alur tembok, dan daftar aksi terdefinisi secara terpisah (*discrete*) dan terhingga.

### 2.3 Actuator ($A$)
* **AI Boss:**
  * `MOVE(direction)`: Berpindah 1 petak ortogonal (Utara, Selatan, Timur, Barat) yang tidak terhalang tembok.
  * `WALL(orientation, x, y)`: Menempatkan tembok 2 petak pada koordinat alur yang legal.
  * `SMASH(direction)`: Menggunakan skill *Juggernaut Smash* (bila cooldown = 0) untuk melangkah menembus dan menghancurkan satu segmen tembok.
* **Runners:**
  * `MOVE(direction)`: Berpindah 1 petak ortogonal yang terbuka.
  * `WALL(orientation, x, y)`: Memasang tembok temporer (*Solo Wall*, hilang dalam 2 giliran), atau membentuk *Co-op Wall Welding* (permanen) jika kedua Runner memasang di segmen yang sama.
  * `ROPE(direction)`: Menggunakan item *Grappling Rope* (sekali pakai per pemain) untuk melompati tembok yang menghalangi ke sel kosong di seberangnya.

### 2.4 Sensor ($S$)
Agen mendeteksi keadaan lingkungan melalui data state:
* Koordinat posisi AI Boss $(x_{\text{AI}}, y_{\text{AI}})$ dan kedua Runners $(x_{R1}, y_{R1})$, $(x_{R2}, y_{R2})$.
* Himpunan semua segmen tembok aktif (baik *solo* beserta sisa durasinya maupun *coop*).
* Posisi seluruh *Data Orbs* aktif di grid.
* Status nilai *cooldown* skill *Juggernaut Smash* (0 = READY / Overload).
* Jumlah sisa *Grappling Rope* masing-masing Runner.
* Skor sementara (AI vs Runners) dan sisa waktu pertandingan.

---

## 3. Formalisasi Matematis State Space

Pemodelan formal ruang masalah didefinisikan ke dalam 5 tupel utama:

$$\mathcal{M} = \langle S, S_0, A(s), T(s, a), U(s) \rangle$$

### 3.1 State Space ($S$)
Setiap keadaan permainan $s \in S$ direpresentasikan sebagai tupel:

$$s = \langle p_{\text{AI}}, p_{R1}, p_{R2}, W_{\text{solo}}, W_{\text{coop}}, \mathcal{O}, c_{\text{smash}}, \mathbf{r}_{\text{rope}}, \text{turn}, \text{score}_{\text{AI}}, \text{score}_{\text{Runners}}, t_{\text{remain}} \rangle$$

Di mana:
* $p_{\text{AI}} \in \{0..8\} \times \{0..8\}$: Koordinat sel AI Boss.
* $p_{R1}, p_{R2} \in \{0..8\} \times \{0..8\}$: Koordinat sel Runner 1 dan Runner 2.
* $W_{\text{solo}} = \{ (e, ttl) \mid e \in E_{\text{groove}}, ttl \in \{1, 2\} \}$: Himpunan segmen tembok temporer beserta sisa masa aktif giliran.
* $W_{\text{coop}} \subseteq E_{\text{groove}}$: Himpunan segmen tembok permanen hasil *Co-op Wall Welding*.
* $\mathcal{O} \subset \{0..8\} \times \{0..8\}$: Himpunan koordinat *Data Orbs* aktif ($|\mathcal{O}| = 3$).
* $c_{\text{smash}} \in \{0, 1, 2, 3\}$: Nilai cooldown skill Smash ($0 = \text{READY}$).
* $\mathbf{r}_{\text{rope}} \in \{0, 1\}^2$: Jumlah sisa item *Grappling Rope* untuk Runner 1 dan Runner 2.
* $\text{turn} \in \{\text{R1}, \text{R2}, \text{AI}\}$: Penunjuk giliran aktif.
* $\text{score}_{\text{AI}}, \text{score}_{\text{Runners}} \in \mathbb{N}_0$: Skor kumulatif kedua belah pihak.
* $t_{\text{remain}} \in \mathbb{R}^+$: Sisa waktu pertandingan dalam detik.

### 3.2 Initial State ($S_0$)
Keadaan awal permainan dispesifikasikan secara kanonikal:
* $p_{\text{AI}} = (4, 4)$ (Pusat grid).
* $p_{R1} = (0, 4)$ dan $p_{R2} = (8, 4)$ (Sisi berlawanan).
* $W_{\text{solo}} = \emptyset$ dan $W_{\text{coop}} = \emptyset$ (Belum ada tembok terpasang).
* $\mathcal{O} = \{o_1, o_2, o_3\}$ ditempatkan secara acak pada sel kosong.
* $c_{\text{smash}} = 0$ (Skill siap digunakan seketika).
* $\mathbf{r}_{\text{rope}} = [1, 1]$ (Masing-masing Runner membawa 1 item).
* $\text{score}_{\text{AI}} = 0$, $\text{score}_{\text{Runners}} = 0$.
* $\text{turn} = \text{R1}$ (Giliran dibuka oleh Runner 1).
* $t_{\text{remain}} = 300.0$ detik.

### 3.3 Action Space ($A(s)$)
Aksi legal yang dapat dipilih agen tergantung pada peran dan keadaan $s$:

#### Aksi AI Boss ($A_{\text{AI}}(s)$):
1. **Langkah Ortogonal:**
   $$A_{\text{move}} = \{ (\text{MOVE}, (x', y')) \mid (x', y') \in \text{Adj}(p_{\text{AI}}) \land \text{edge}(p_{\text{AI}}, (x', y')) \notin (W_{\text{solo}} \cup W_{\text{coop}}) \}$$
2. **Penempatan Tembok 2 Petak:**
   $$A_{\text{wall}} = \{ (\text{WALL}, (\text{orient}, x, y)) \mid \text{IsValid2TileWall}(s, \text{orient}, x, y) \}$$
3. **Juggernaut Smash:**
   $$A_{\text{smash}} = \{ (\text{SMASH}, (x', y')) \mid c_{\text{smash}} = 0 \land (x', y') \in \text{Adj}(p_{\text{AI}}) \land \text{edge}(p_{\text{AI}}, (x', y')) \in (W_{\text{solo}} \cup W_{\text{coop}}) \}$$

#### Aksi Runners ($A_{\text{Runner}, i}(s)$):
1. **Langkah Ortogonal:** Berpindah ke sel tetangga yang tidak diblokir tembok.
2. **Penempatan Tembok:** Menempatkan tembok yang valid (*Solo Wall* jika sendiri, *Co-op* jika bersamaan).
3. **Grappling Rope:**
   $$A_{\text{rope}} = \{ (\text{ROPE}, (x', y')) \mid \mathbf{r}_{\text{rope}}[i] > 0 \land (x', y') \in \text{Adj}(p_{Ri}) \land \text{edge}(p_{Ri}, (x', y')) \in (W_{\text{solo}} \cup W_{\text{coop}}) \}$$

### 3.4 Model Transisi ($T(s, a) \to s'$)
Model transisi mendefinisikan perubahan keadaan deterministik:
* **Perpindahan Posisi:** $p_{\text{agen}}' \leftarrow \text{dest}$.
* **Pengambilan Orb:** Jika $p_{Ri}' \in \mathcal{O}$, maka $\text{score}_{\text{Runners}} \leftarrow \text{score}_{\text{Runners}} + 15$, hapus orb yang terambil, dan munculkan orb pengganti pada sel kosong terjauh dari AI Boss.
* **Tangkapan AI (*Tag & Teleport*):** Jika $p_{\text{AI}}' = p_{Ri}$, maka $\text{score}_{\text{AI}} \leftarrow \text{score}_{\text{AI}} + 40$. Runner tidak mati/dieliminasi, melainkan mengalami *Phase-Blink* (teleportasi aman) ke sudut terjauh yang belum terisi.
* **Peluruhan Tembok (*Wall Decay*):** Pada setiap siklus giliran, nilai $ttl$ pada semua segmen $W_{\text{solo}}$ berkurang 1. Segmen dengan $ttl = 0$ otomatis terhapus dari papan. Tembok $W_{\text{coop}}$ bersifat permanen.
* **Cooldown Smash:** Bila AI melakukan `SMASH`, cooldown diset ke 3. Pada akhir giliran penuh, cooldown berkurang 1 hingga mencapai 0.

### 3.5 Goal Test & Utility Function ($U(s)$)
Kondisi terminal (*Terminal State*) tercapai bila:
$$s \text{ is terminal} \iff (t_{\text{remain}} \le 0) \lor (\text{turn\_count} \ge \text{MAX\_TURNS}) \lor \text{is\_game\_over}$$

Nilai *Utility* dihitung dari sudut pandang node MAX (AI Boss):
$$U(s) = \begin{cases} 
+1000 & \text{jika } \text{score}_{\text{AI}} > \text{score}_{\text{Runners}} \quad (\text{Kemenangan AI Boss}) \\
-1000 & \text{jika } \text{score}_{\text{Runners}} > \text{score}_{\text{AI}} \quad (\text{Kemenangan Runners}) \\
0 & \text{jika } \text{score}_{\text{AI}} = \text{score}_{\text{Runners}} \quad (\text{Seri / Draw})
\end{cases}$$

---

## 4. Aturan Invarian: *No-Complete-Cage BFS*

Sesuai aturan kanonikal *Quoridor*, tidak boleh ada penempatan tembok yang mengurung pemain secara total hingga tidak memiliki jalan keluar (*zero-escape cage*).

Dalam implementasi *Quoridor Chase*, setiap kandidat tembok divalidasi menggunakan algoritma *Breadth-First Search (BFS)*:
$$\text{ReachableCells}(p_{\text{agen}}, W \cup \{e_{\text{candidate}}\}) \ge 4$$

Jika penempatan tembok menyebabkan komponen terhubung dari AI Boss atau salah satu Runner memiliki ukuran $< 4$ petak, aksi penempatan tembok tersebut diklasifikasikan sebagai **ilegal** dan ditolak oleh mesin game.

---

## 5. Implementasi Modul Kode Python

Seluruh spesifikasi di atas telah diwujudkan dalam paket kode modular di dalam folder `engine/` dan `config.py`:

```text
QuoridorChase/
├── config.py             # Konstanta board 9x9, timer, skor, cooldown, bobot heuristik
├── engine/
│   ├── __init__.py       # Ekspor antarmuka publik mesin game
│   ├── state.py          # Class GameState (S), S0, cloning cepat, serialisasi, utility
│   ├── rules.py          # Validasi aksi legal, BFS No-Complete-Cage, Smash, Rope Jump
│   └── transition.py     # Model transisi T(s,a), wall decay, welding, tag & teleport
├── tests/
│   └── test_section_1_2.py # Pytest komprehensif menguji seluruh mekanik Bagian 1.2
└── docs/
    └── Bagian_1_2_Pemodelan_State_Space_dan_PEAS.md
```

### Hasil Verifikasi Unit Test (`tests/test_section_1_2.py`)
Semua 8 skenario pengujian utama berhasil lulus 100%:
1. `test_initial_state_s0`: Memvalidasi seluruh properti $S_0$.
2. `test_orthogonal_movement_and_wall_blocking`: Memvalidasi pergerakan ortogonal dan pencegahan menembus tembok.
3. `test_juggernaut_smash_mechanic`: Memvalidasi penghancuran tembok permanen dan reset cooldown ke 3.
4. `test_grappling_rope_wall_jump`: Memvalidasi lompatan tembok dan konsumsi item rope sekali pakai.
5. `test_solo_wall_decay_vs_coop_wall_welding`: Memvalidasi peluruhan solo wall ($TTL = 2$) serta permanensi co-op wall welding.
6. `test_2tile_wall_placement_and_no_cage_rule`: Memvalidasi tembok 2 petak dan invarian BFS anti-kurungan.
7. `test_data_orb_collection_and_tag_teleport`: Memvalidasi perolehan $+15$ poin orb dan $+40$ poin tagging dengan respawn sudut.
8. `test_terminal_state_and_utility`: Memvalidasi evaluasi kondisi akhir dan fungsi utilitas $U(s) \in \{+1000, -1000, 0\}$.

