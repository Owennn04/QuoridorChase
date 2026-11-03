"""
Interactive Pygame UI for Quoridor Chase: Lockdown.
Menyediakan GUI interaktif lengkap dengan:
- Papan Grid 9x9 dengan visual Cyber/Lockdown
- Pion AI Boss (Crimson), Runner 1 (Cyan), Runner 2 (Sky Blue), dan Data Orbs (Gold)
- Render Tembok Dinamis: Solo Wall (Orange/Amber) dan Co-op Wall Welding (Purple/Cyan permanen)
- Kontrol Pemain: Klik Mouse atau Arrow Keys / WASD untuk bergerak
- Fitur Wall Placement Mode (tekan W, klik untuk pasang tembok 2-tile, tekan R untuk rotasi H/V)
- Fitur Grappling Rope Jump (tekan E)
- Giliran AI Otomatis menggunakan Algoritma Minimax / Alpha-Beta Pruning
- Dashboard HUD: Skor, Timer, Cooldown Smash, Item Rope, dan Telemetri AI (Nodes, Cutoffs, Latensi)
- Mode Auto-Play (tekan P) untuk simulasi otomatis berkelanjutan
"""

import os
import sys
import time
import pygame

# Memastikan root project ada di sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import (
    GRID_SIZE,
    THEME_TOKENS,
    AI_START_POS,
    RUNNER_START_POSITIONS,
    ACTIVE_ORB_TARGET_COUNT,
    MATCH_DURATION_SECONDS,
    SOLO_WALL_LIFETIME
)
from engine.state import GameState, canonical_edge
from engine.rules import (
    get_valid_steps,
    can_wall_jump,
    can_juggernaut_smash,
    is_valid_2tile_wall,
    wall_to_edges
)
from engine.transition import (
    apply_runner_action,
    apply_ai_action,
    step_turn_cycle
)
from src.ai.minimax import (
    MinimaxAgent,
    get_candidate_actions_runners
)
from src.ai.pathfinding import manhattan_distance


def hex_to_rgb(hex_code):
    """Konversi string HEX (#RRGGBB) ke tuple (R, G, B)."""
    hex_code = hex_code.lstrip("#")
    return (
        int(hex_code[0:2], 16),
        int(hex_code[2:4], 16),
        int(hex_code[4:6], 16)
    )


# Ukuran Dimensi Layar & Papan
CELL_SIZE = 54
WALL_THICKNESS = 12
BOARD_MARGIN_X = 20
BOARD_MARGIN_Y = 20

BOARD_PIXEL_WIDTH = (GRID_SIZE * CELL_SIZE) + ((GRID_SIZE + 1) * WALL_THICKNESS)
BOARD_PIXEL_HEIGHT = BOARD_PIXEL_WIDTH

PANEL_WIDTH = 360
WINDOW_WIDTH = BOARD_PIXEL_WIDTH + PANEL_WIDTH + (BOARD_MARGIN_X * 2)
WINDOW_HEIGHT = BOARD_PIXEL_HEIGHT + (BOARD_MARGIN_Y * 2)


class GameUI:
    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Quoridor Chase: Lockdown - AI Adversarial Arena")
        self.clock = pygame.time.Clock()

        # Inisialisasi Font
        self.font_title = pygame.font.SysFont("Trebuchet MS", 18, bold=True)
        self.font_header = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 12)
        self.font_small = pygame.font.SysFont("Consolas", 11)
        self.font_pawn = pygame.font.SysFont("Arial", 13, bold=True)

        # Inisialisasi Warna dari THEME_TOKENS
        self.color_bg = hex_to_rgb(THEME_TOKENS.get("cyber_bg", "#090d16"))
        self.color_panel = hex_to_rgb(THEME_TOKENS.get("cyber_panel", "#111827"))
        self.color_border = hex_to_rgb(THEME_TOKENS.get("cyber_border", "#1e293b"))
        self.color_ai = hex_to_rgb(THEME_TOKENS.get("ai_crimson", "#ef4444"))
        self.color_runner1 = hex_to_rgb(THEME_TOKENS.get("runner_cyan", "#06b6d4"))
        self.color_runner2 = hex_to_rgb(THEME_TOKENS.get("runner_sky", "#38bdf8"))
        self.color_orb = hex_to_rgb(THEME_TOKENS.get("orb_gold", "#facc15"))
        self.color_solo_wall = hex_to_rgb(THEME_TOKENS.get("orange", "#ef6b3a"))
        self.color_coop_wall = (168, 85, 247)  # Neon Purple untuk Co-op Welded Wall
        self.color_text = hex_to_rgb(THEME_TOKENS.get("white", "#fffdf7"))
        self.color_green = (34, 197, 94)
        self.color_yellow = (234, 179, 8)
        self.color_gray = (148, 163, 184)
        self.color_highlight = (16, 185, 129, 120)  # Green translucent

        # Objek State & AI
        self.state = GameState.create_initial_state(seed=42)
        self.ai_agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)

        # Status Kontrol Pemain
        self.wall_mode = False          # Mode pasang tembok (tekan W)
        self.wall_orient = "H"          # Orientasi tembok: 'H' atau 'V'
        self.rope_mode = False          # Mode loncat tembok (tekan E)
        self.auto_play = False          # Mode auto-simulasi (tekan P)
        self.auto_timer = 0.0           # Timer untuk auto-step
        self.ai_wait_timer = 0.0        # Jeda waktu sebelum AI bergerak agar terlihat natural
        self.ai_delay_seconds = 0.35    # Delay 350ms untuk giliran AI

        # Log Pesan & Telemetri
        self.messages = [
            "Selamat datang di Quoridor Chase: Lockdown!",
            "Giliran dimulai oleh Runner 1 (R1).",
            "Gunakan Mouse atau Panah/WASD untuk melangkah."
        ]
        self.last_ai_metrics = {
            "mode": self.ai_agent.mode_name,
            "action": None,
            "eval": 0.0,
            "nodes": 0,
            "cutoffs": 0,
            "time_ms": 0.0
        }

    # =========================================================================
    # Helper Koordinat & Hit-Testing
    # =========================================================================

    def _get_cell_rect(self, r, c):
        """Menghitung koordinat piksel (x, y, w, h) untuk sel (r, c)."""
        px = BOARD_MARGIN_X + WALL_THICKNESS + c * (CELL_SIZE + WALL_THICKNESS)
        py = BOARD_MARGIN_Y + WALL_THICKNESS + r * (CELL_SIZE + WALL_THICKNESS)
        return pygame.Rect(px, py, CELL_SIZE, CELL_SIZE)

    def _get_cell_from_pixel(self, mx, my):
        """Mendeteksi sel grid (r, c) dari posisi kursor mouse."""
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                rect = self._get_cell_rect(r, c)
                if rect.collidepoint(mx, my):
                    return (r, c)
        return None

    def _get_intersection_from_pixel(self, mx, my):
        """Mendeteksi perempatan/groove terdekat (r, c) untuk penempatan tembok 2-tile."""
        best_inter = None
        min_dist_sq = 28 * 28  # Radius deteksi 28 piksel
        for r in range(GRID_SIZE - 1):
            for c in range(GRID_SIZE - 1):
                # Titik tengah perempatan antara sel (r, c) dan (r+1, c+1)
                ix = BOARD_MARGIN_X + (c + 1) * (CELL_SIZE + WALL_THICKNESS) + (WALL_THICKNESS // 2)
                iy = BOARD_MARGIN_Y + (r + 1) * (CELL_SIZE + WALL_THICKNESS) + (WALL_THICKNESS // 2)
                dist_sq = (mx - ix) ** 2 + (my - iy) ** 2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    best_inter = (r, c)
        return best_inter

    def log_message(self, text):
        """Menambahkan pesan ke riwayat notifikasi HUD."""
        self.messages.append(text)
        if len(self.messages) > 4:
            self.messages.pop(0)

    # =========================================================================
    # Logika Interaksi Pemain & Transisi Turn
    # =========================================================================

    def handle_cell_click(self, target_cell):
        """Menangani klik pada petak grid untuk pergerakan atau loncatan."""
        if self.state.is_game_over:
            return

        if self.state.current_turn == "R1":
            runner_idx = 0
            curr_pos = self.state.p_runners[0]
        elif self.state.current_turn == "R2":
            runner_idx = 1
            curr_pos = self.state.p_runners[1]
        else:
            return  # Giliran AI Boss

        # 1. Mode Grappling Rope
        if self.rope_mode:
            jump_moves = can_wall_jump(self.state, runner_idx)
            valid_destinations = [dest for dest, _ in jump_moves]
            if target_cell in valid_destinations:
                self.state = apply_runner_action(self.state, runner_idx, ("ROPE", target_cell))
                self.log_message(f"Runner {runner_idx+1} melompati tembok pakai Rope ke {target_cell}!")
                self.rope_mode = False
                self._advance_runner_turn()
            else:
                self.log_message(f"Petak {target_cell} tidak dapat dilompati dengan Rope!")
            return

        # 2. Pergerakan Normal
        valid_steps = get_valid_steps(self.state, curr_pos)
        if target_cell in valid_steps:
            # Cek apakah sel ditempati runner lain
            other_idx = 1 if runner_idx == 0 else 0
            if target_cell == self.state.p_runners[other_idx]:
                self.log_message(f"Petak {target_cell} sudah ditempati rekan Runner {other_idx+1}!")
                return

            self.state = apply_runner_action(self.state, runner_idx, ("MOVE", target_cell))
            self.log_message(f"Runner {runner_idx+1} melangkah ke {target_cell}.")
            self._advance_runner_turn()
        else:
            self.log_message(f"Langkah ke {target_cell} tidak valid / terhalang tembok!")

    def handle_wall_click(self, intersection):
        """Menangani klik untuk memasang tembok 2-tile."""
        if self.state.is_game_over:
            return

        if self.state.current_turn == "R1":
            runner_idx = 0
        elif self.state.current_turn == "R2":
            runner_idx = 1
        else:
            return

        r, c = intersection
        orient = self.wall_orient

        if is_valid_2tile_wall(self.state, orient, r, c):
            self.state = apply_runner_action(self.state, runner_idx, ("WALL", (orient, r, c)))
            self.log_message(f"Runner {runner_idx+1} memasang tembok {orient} di ({r}, {c})!")
            self.wall_mode = False
            self._advance_runner_turn()
        else:
            self.log_message(f"Tembok di ({orient}, {r}, {c}) melanggar aturan (tabrakan/mengurung)!")

    def handle_arrow_move(self, dr, dc):
        """Menangani pergerakan menggunakan tombol panah atau WASD."""
        if self.state.is_game_over:
            return

        if self.state.current_turn == "R1":
            curr_pos = self.state.p_runners[0]
        elif self.state.current_turn == "R2":
            curr_pos = self.state.p_runners[1]
        else:
            return

        target = (curr_pos[0] + dr, curr_pos[1] + dc)
        if 0 <= target[0] < GRID_SIZE and 0 <= target[1] < GRID_SIZE:
            self.handle_cell_click(target)

    def _advance_runner_turn(self):
        """Memajukan giliran setelah runner selesai mengambil aksi."""
        if self.state.current_turn == "R1":
            self.state.current_turn = "R2"
            self.log_message("Sekarang giliran Runner 2 (R2).")
        elif self.state.current_turn == "R2":
            # Putaran runners selesai, lakukan maintenance turn cycle
            self.state = step_turn_cycle(self.state, elapsed_seconds=2.0)
            self.state.current_turn = "AI"
            self.ai_wait_timer = time.time()
            self.log_message("Giliran Tim Runners selesai. AI Boss sedang berpikir...")

    def execute_ai_turn(self):
        """Mengeksekusi giliran AI Boss menggunakan Minimax / Alpha-Beta Pruning."""
        if self.state.is_game_over or self.state.current_turn != "AI":
            return

        t_start = time.perf_counter()
        best_act, best_val = self.ai_agent.choose_action(self.state)
        t_elapsed = (time.perf_counter() - t_start) * 1000.0

        if best_act is None:
            # Fallback jika tidak ada aksi
            valid = get_valid_steps(self.state, self.state.p_ai)
            best_act = ("MOVE", valid[0]) if valid else ("MOVE", self.state.p_ai)
            best_val = 0.0

        # Simpan telemetri pencarian
        metrics = self.ai_agent.metrics.to_dict()
        self.last_ai_metrics = {
            "mode": self.ai_agent.mode_name,
            "action": best_act,
            "eval": best_val,
            "nodes": metrics["nodes_explored"],
            "cutoffs": metrics["cutoffs"],
            "time_ms": round(t_elapsed, 1)
        }

        # Eksekusi aksi AI pada game state
        act_type, payload = best_act
        self.state = apply_ai_action(self.state, best_act)

        if act_type == "MOVE":
            self.log_message(f"AI Boss melangkah ke {payload}.")
        elif act_type == "SMASH":
            self.log_message(f"AI Boss MENGHANCURKAN TEMBOK dengan Smash ke {payload}!")
        elif act_type == "WALL":
            self.log_message(f"AI Boss memasang tembok di {payload}!")

        # Kembalikan giliran ke Runner 1
        self.state.current_turn = "R1"
        self.log_message("Ronde baru dimulai: Giliran Runner 1 (R1).")

    def execute_auto_step(self):
        """Menjalankan 1 langkah otomatis (untuk mode Auto-Play atau tekan Spasi)."""
        if self.state.is_game_over:
            return

        if self.state.current_turn in ("R1", "R2"):
            r_idx = 0 if self.state.current_turn == "R1" else 1
            r_pos = self.state.p_runners[r_idx]
            ai_pos = self.state.p_ai

            # Pilih langkah terbaik untuk runner: menjauhi AI & mendekati Orb
            valid = get_valid_steps(self.state, r_pos)
            if valid:
                def score_step(step):
                    d_ai = manhattan_distance(step, ai_pos)
                    d_orb = min([manhattan_distance(step, o) for o in self.state.orbs]) if self.state.orbs else 5
                    return (d_ai * 2.5) - (d_orb * 1.5)

                best_step = max(valid, key=score_step)
                self.state = apply_runner_action(self.state, r_idx, ("MOVE", best_step))
                self.log_message(f"Runner {r_idx+1} melangkah otomatis ke {best_step}.")
            self._advance_runner_turn()

        elif self.state.current_turn == "AI":
            self.execute_ai_turn()

    # =========================================================================
    # Rendering Visual (Papan, Pion, Tembok, HUD)
    # =========================================================================

    def draw(self, mouse_pos):
        """Render seluruh layar."""
        self.screen.fill(self.color_bg)

        # 1. Gambar Papan & Grid Petak
        self._draw_board(mouse_pos)

        # 2. Gambar Tembok-tembok Aktif
        self._draw_walls()

        # 3. Gambar Preview Penempatan Tembok (jika dalam Wall Mode)
        if self.wall_mode and not self.state.is_game_over:
            self._draw_wall_preview(mouse_pos)

        # 4. Gambar Data Orbs
        self._draw_orbs()

        # 5. Gambar Pion Pemain & AI Boss
        self._draw_pawns()

        # 6. Gambar Highlight Langkah Valid
        if not self.wall_mode and not self.state.is_game_over:
            self._draw_valid_moves_highlight(mouse_pos)

        # 7. Gambar Panel Dashboard HUD (Kanan)
        self._draw_hud_panel()

        # 8. Gambar Layar Game Over jika Permainan Selesai
        if self.state.is_game_over:
            self._draw_game_over_overlay()

        pygame.display.flip()

    def _draw_board(self, mouse_pos):
        """Menggambar papan petak 9x9 beserta nomor koordinat."""
        hover_cell = self._get_cell_from_pixel(mouse_pos[0], mouse_pos[1])

        # Gambar petak-petak papan
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                rect = self._get_cell_rect(r, c)
                is_hover = (hover_cell == (r, c)) and not self.wall_mode

                cell_color = (26, 36, 56) if is_hover else self.color_panel
                pygame.draw.rect(self.screen, cell_color, rect, border_radius=4)
                pygame.draw.rect(self.screen, self.color_border, rect, 1, border_radius=4)

        # Gambar label koordinat di tepi atas dan kiri
        for i in range(GRID_SIZE):
            # Label baris (0-8) di sisi kiri
            lbl_r = self.font_small.render(str(i), True, self.color_gray)
            py = BOARD_MARGIN_Y + WALL_THICKNESS + i * (CELL_SIZE + WALL_THICKNESS) + (CELL_SIZE // 2) - 6
            self.screen.blit(lbl_r, (BOARD_MARGIN_X - 14, py))

            # Label kolom (0-8) di sisi atas
            lbl_c = self.font_small.render(str(i), True, self.color_gray)
            px = BOARD_MARGIN_X + WALL_THICKNESS + i * (CELL_SIZE + WALL_THICKNESS) + (CELL_SIZE // 2) - 4
            self.screen.blit(lbl_c, (px, BOARD_MARGIN_Y - 16))

    def _draw_walls(self):
        """Menggambar semua tembok yang ada di papan."""
        # Gambar setiap edge dinding dari state.all_walls()
        for edge in self.state.all_walls():
            c1, c2 = edge
            # Tentukan warna: Co-op permanen (ungu) atau Solo wall (oranye)
            is_coop = edge in self.state.coop_walls
            wall_color = self.color_coop_wall if is_coop else self.color_solo_wall

            if c1[0] == c2[0]:
                # Tembok Vertikal antara c1 dan c2 (kolom bersebelahan)
                c_min = min(c1[1], c2[1])
                wx = BOARD_MARGIN_X + (c_min + 1) * (CELL_SIZE + WALL_THICKNESS)
                wy = BOARD_MARGIN_Y + WALL_THICKNESS + c1[0] * (CELL_SIZE + WALL_THICKNESS)
                rect = pygame.Rect(wx, wy, WALL_THICKNESS, CELL_SIZE)
                pygame.draw.rect(self.screen, wall_color, rect, border_radius=2)
            elif c1[1] == c2[1]:
                # Tembok Horizontal antara c1 dan c2 (baris bersebelahan)
                r_min = min(c1[0], c2[0])
                wx = BOARD_MARGIN_X + WALL_THICKNESS + c1[1] * (CELL_SIZE + WALL_THICKNESS)
                wy = BOARD_MARGIN_Y + (r_min + 1) * (CELL_SIZE + WALL_THICKNESS)
                rect = pygame.Rect(wx, wy, CELL_SIZE, WALL_THICKNESS)
                pygame.draw.rect(self.screen, wall_color, rect, border_radius=2)

        # Gambar sambungan perempatan untuk 2-tile wall di placed_walls
        for (orient, r, c), val in self.state.placed_walls.items():
            ttl = val[0] if isinstance(val, (tuple, list)) else val
            is_coop = (ttl == -1)
            wall_color = self.color_coop_wall if is_coop else self.color_solo_wall

            ix = BOARD_MARGIN_X + (c + 1) * (CELL_SIZE + WALL_THICKNESS)
            iy = BOARD_MARGIN_Y + (r + 1) * (CELL_SIZE + WALL_THICKNESS)
            pygame.draw.rect(self.screen, wall_color, (ix, iy, WALL_THICKNESS, WALL_THICKNESS))

    def _draw_wall_preview(self, mouse_pos):
        """Menggambar preview tembok saat kursor mendekati perempatan."""
        inter = self._get_intersection_from_pixel(mouse_pos[0], mouse_pos[1])
        if inter is None:
            return

        r, c = inter
        orient = self.wall_orient
        is_valid = is_valid_2tile_wall(self.state, orient, r, c)
        preview_color = (34, 197, 94, 180) if is_valid else (239, 68, 68, 180)

        # Hitung koordinat preview persegi panjang tembok
        if orient == "H":
            # Engine 'H' memblokir langkah horizontal -> Tembok VERTIKAL (tegak |)
            wx = BOARD_MARGIN_X + (c + 1) * (CELL_SIZE + WALL_THICKNESS)
            wy = BOARD_MARGIN_Y + WALL_THICKNESS + r * (CELL_SIZE + WALL_THICKNESS)
            w_w = WALL_THICKNESS
            w_h = (CELL_SIZE * 2) + WALL_THICKNESS
        else:
            # Engine 'V' memblokir langkah vertikal -> Tembok HORIZONTAL (mendatar -)
            wx = BOARD_MARGIN_X + WALL_THICKNESS + c * (CELL_SIZE + WALL_THICKNESS)
            wy = BOARD_MARGIN_Y + (r + 1) * (CELL_SIZE + WALL_THICKNESS)
            w_w = (CELL_SIZE * 2) + WALL_THICKNESS
            w_h = WALL_THICKNESS

        surf = pygame.Surface((w_w, w_h), pygame.SRCALPHA)
        surf.fill(preview_color)
        self.screen.blit(surf, (wx, wy))

    def _draw_orbs(self):
        """Menggambar Data Orbs (Lingkaran emas berkilau)."""
        pulse = int(abs(time.time() * 3 % 2 - 1) * 3)  # Efek pulsing ringan
        radius = (CELL_SIZE // 4) + pulse

        for orb_r, orb_c in self.state.orbs:
            rect = self._get_cell_rect(orb_r, orb_c)
            center = rect.center

            # Glow luar
            pygame.draw.circle(self.screen, (250, 204, 21, 50), center, radius + 4)
            # Inti Orb emas
            pygame.draw.circle(self.screen, self.color_orb, center, radius)
            pygame.draw.circle(self.screen, (254, 240, 138), center, radius - 2)

            # Simbol bintang kecil
            txt = self.font_small.render("✦", True, (113, 63, 18))
            self.screen.blit(txt, (center[0] - 4, center[1] - 7))

    def _draw_pawns(self):
        """Menggambar pion AI Boss dan Tim Runners."""
        radius = CELL_SIZE // 3

        # 1. Runner 1 (R1 - Cyan)
        r1_rect = self._get_cell_rect(self.state.p_runners[0][0], self.state.p_runners[0][1])
        r1_center = r1_rect.center
        is_r1_turn = (self.state.current_turn == "R1")
        if is_r1_turn:
            # Ring indikator giliran aktif
            pygame.draw.circle(self.screen, (255, 255, 255), r1_center, radius + 5, 2)
        pygame.draw.circle(self.screen, self.color_runner1, r1_center, radius)
        lbl_r1 = self.font_pawn.render("R1", True, (15, 23, 42))
        self.screen.blit(lbl_r1, (r1_center[0] - 8, r1_center[1] - 8))

        # 2. Runner 2 (R2 - Sky Blue)
        r2_rect = self._get_cell_rect(self.state.p_runners[1][0], self.state.p_runners[1][1])
        r2_center = r2_rect.center
        is_r2_turn = (self.state.current_turn == "R2")
        if is_r2_turn:
            pygame.draw.circle(self.screen, (255, 255, 255), r2_center, radius + 5, 2)
        pygame.draw.circle(self.screen, self.color_runner2, r2_center, radius)
        lbl_r2 = self.font_pawn.render("R2", True, (15, 23, 42))
        self.screen.blit(lbl_r2, (r2_center[0] - 8, r2_center[1] - 8))

        # 3. AI Boss (Crimson Red)
        ai_rect = self._get_cell_rect(self.state.p_ai[0], self.state.p_ai[1])
        ai_center = ai_rect.center
        ai_radius = int(CELL_SIZE // 2.5)
        is_ai_turn = (self.state.current_turn == "AI")
        if is_ai_turn:
            pygame.draw.circle(self.screen, (255, 255, 255), ai_center, ai_radius + 5, 2)
        pygame.draw.circle(self.screen, self.color_ai, ai_center, ai_radius)
        # Efek inti smash jika siap (READY)
        if self.state.smash_cooldown == 0:
            pygame.draw.circle(self.screen, (254, 202, 202), ai_center, ai_radius - 4, 2)
        lbl_ai = self.font_pawn.render("AI", True, (255, 255, 255))
        self.screen.blit(lbl_ai, (ai_center[0] - 7, ai_center[1] - 8))

    def _draw_valid_moves_highlight(self, mouse_pos):
        """Menampilkan indikator hijau pada petak-petak yang dapat dituju oleh runner aktif."""
        if self.state.current_turn not in ("R1", "R2"):
            return

        runner_idx = 0 if self.state.current_turn == "R1" else 1
        curr_pos = self.state.p_runners[runner_idx]

        if self.rope_mode:
            jump_moves = can_wall_jump(self.state, runner_idx)
            destinations = [dest for dest, _ in jump_moves]
            dot_color = (168, 85, 247)  # Ungu untuk Rope
        else:
            destinations = get_valid_steps(self.state, curr_pos)
            dot_color = (34, 197, 94)    # Hijau untuk normal step

        for dest in destinations:
            rect = self._get_cell_rect(dest[0], dest[1])
            # Lingkaran kecil penanda petak valid
            pygame.draw.circle(self.screen, dot_color, rect.center, 7)
            pygame.draw.circle(self.screen, (255, 255, 255), rect.center, 7, 1)

    def _draw_hud_panel(self):
        """Menggambar panel informasi di sisi kanan (Skor, Status, Telemetri AI, Kontrol)."""
        px = BOARD_PIXEL_WIDTH + (BOARD_MARGIN_X * 2)
        py = BOARD_MARGIN_Y
        pw = PANEL_WIDTH - 20
        ph = BOARD_PIXEL_HEIGHT

        # Background panel
        panel_rect = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(self.screen, self.color_panel, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.color_border, panel_rect, 1, border_radius=8)

        cy = py + 14

        # 1. Judul Game
        title = self.font_title.render("QUORIDOR CHASE", True, self.color_text)
        self.screen.blit(title, (px + 14, cy))
        cy += 20
        subtitle = self.font_small.render("Lockdown - AI Adversarial Arena", True, self.color_gray)
        self.screen.blit(subtitle, (px + 14, cy))
        cy += 24

        # Garis pembatas
        pygame.draw.line(self.screen, self.color_border, (px + 14, cy), (px + pw - 14, cy))
        cy += 12

        # 2. Status Giliran Saat Ini (Turn Banner)
        curr_turn = self.state.current_turn
        if curr_turn == "R1":
            turn_text = "GILIRAN: RUNNER 1 (R1)"
            turn_color = self.color_runner1
        elif curr_turn == "R2":
            turn_text = "GILIRAN: RUNNER 2 (R2)"
            turn_color = self.color_runner2
        else:
            turn_text = "GILIRAN: AI BOSS"
            turn_color = self.color_ai

        banner_rect = pygame.Rect(px + 14, cy, pw - 28, 28)
        pygame.draw.rect(self.screen, (30, 41, 59), banner_rect, border_radius=4)
        pygame.draw.rect(self.screen, turn_color, banner_rect, 1, border_radius=4)
        t_surf = self.font_header.render(turn_text, True, turn_color)
        self.screen.blit(t_surf, (px + 22, cy + 6))
        cy += 38

        # 3. Papan Skor
        box_rect = pygame.Rect(px + 14, cy, pw - 28, 54)
        pygame.draw.rect(self.screen, (15, 23, 42), box_rect, border_radius=4)
        cy_box = cy + 8
        ai_score_str = f"AI Boss  : {self.state.score_ai} Pts"
        run_score_str = f"Runners  : {self.state.score_runners} Pts"
        self.screen.blit(self.font_header.render(ai_score_str, True, self.color_ai), (px + 24, cy_box))
        self.screen.blit(self.font_header.render(run_score_str, True, self.color_runner1), (px + 24, cy_box + 20))
        cy += 64

        # 4. Status Skill & Item
        smash_txt = "READY (OVERLOAD)" if self.state.smash_cooldown == 0 else f"Cooldown {self.state.smash_cooldown} turn"
        smash_col = self.color_green if self.state.smash_cooldown == 0 else self.color_solo_wall
        self.screen.blit(self.font_small.render(f"Smash AI  : ", True, self.color_gray), (px + 14, cy))
        self.screen.blit(self.font_small.render(smash_txt, True, smash_col), (px + 90, cy))
        cy += 16

        r1_rope_txt = f"{self.state.runner_ropes[0]}x Sisa" if self.state.runner_ropes[0] > 0 else "Habis"
        r2_rope_txt = f"{self.state.runner_ropes[1]}x Sisa" if self.state.runner_ropes[1] > 0 else "Habis"
        self.screen.blit(self.font_small.render(f"Rope R1   : {r1_rope_txt} | Rope R2: {r2_rope_txt}", True, self.color_gray), (px + 14, cy))
        cy += 20

        # Garis pembatas
        pygame.draw.line(self.screen, self.color_border, (px + 14, cy), (px + pw - 14, cy))
        cy += 10

        # 5. Telemetri AI Minimax / Alpha-Beta
        self.screen.blit(self.font_header.render("TELEMETRI AI MINIMAX", True, self.color_yellow), (px + 14, cy))
        cy += 18
        m = self.last_ai_metrics
        self.screen.blit(self.font_body.render(f"Mode    : {m['mode']}", True, self.color_text), (px + 14, cy))
        cy += 15
        self.screen.blit(self.font_body.render(f"Keputusan: {m['action']}", True, self.color_text), (px + 14, cy))
        cy += 15
        self.screen.blit(self.font_body.render(f"Node    : {m['nodes']} diuji ({m['cutoffs']} cutoffs)", True, self.color_text), (px + 14, cy))
        cy += 15
        self.screen.blit(self.font_body.render(f"Latensi : {m['time_ms']} ms (Eval: {m['eval']:.1f})", True, self.color_text), (px + 14, cy))
        cy += 22

        # Garis pembatas
        pygame.draw.line(self.screen, self.color_border, (px + 14, cy), (px + pw - 14, cy))
        cy += 10

        # 6. Notifikasi Log Pertandingan
        self.screen.blit(self.font_header.render("LOG PERTANDINGAN", True, self.color_text), (px + 14, cy))
        cy += 18
        for msg in self.messages[-3:]:
            txt = self.font_small.render(f"• {msg}", True, self.color_gray)
            self.screen.blit(txt, (px + 14, cy))
            cy += 15
        cy += 8

        # Garis pembatas
        pygame.draw.line(self.screen, self.color_border, (px + 14, cy), (px + pw - 14, cy))
        cy += 10

        # 7. Petunjuk Tombol Kontrol
        self.screen.blit(self.font_header.render("PANDUAN KONTROL", True, self.color_text), (px + 14, cy))
        cy += 18
        orient_label = "Tegak (|)" if self.wall_orient == "H" else "Mendatar (-)"
        controls = [
            ("Klik Petak / Panah", "Melangkah"),
            ("Tombol [W]", f"Mode Tembok ({'AKTIF: ' + orient_label if self.wall_mode else 'OFF'})"),
            ("Tombol [R] / Klik Kanan", f"Putar Tembok ({orient_label})"),
            ("Tombol [E]", f"Mode Rope Jump ({'AKTIF' if self.rope_mode else 'OFF'})"),
            ("Tombol [SPASI]", "Langkah Manual"),
            ("Tombol [P]", f"Auto-Play ({'ON' if self.auto_play else 'OFF'})"),
            ("Tombol [A]", f"Toggle Alpha-Beta"),
            ("Tombol [F1]", "Reset Ulang Permainan")
        ]
        for key, desc in controls:
            k_surf = self.font_small.render(key, True, self.color_yellow)
            d_surf = self.font_small.render(f": {desc}", True, self.color_text)
            self.screen.blit(k_surf, (px + 14, cy))
            self.screen.blit(d_surf, (px + 14 + k_surf.get_width(), cy))
            cy += 14

    def _draw_game_over_overlay(self):
        """Menampilkan banner Game Over saat permainan selesai."""
        overlay = pygame.Surface((BOARD_PIXEL_WIDTH, BOARD_PIXEL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((9, 13, 22, 220))
        self.screen.blit(overlay, (BOARD_MARGIN_X, BOARD_MARGIN_Y))

        cx = BOARD_MARGIN_X + (BOARD_PIXEL_WIDTH // 2)
        cy = BOARD_MARGIN_Y + (BOARD_PIXEL_HEIGHT // 2) - 40

        winner = self.state.winner if self.state.winner else "Game Over"
        txt_win = self.font_title.render(f"PERMAINAN SELESAI!", True, (255, 255, 255))
        txt_res = self.font_header.render(f"Pemenang: {winner}", True, self.color_yellow)
        txt_score = self.font_body.render(
            f"Skor Akhir - AI Boss: {self.state.score_ai} | Runners: {self.state.score_runners}",
            True, (255, 255, 255)
        )
        txt_prompt = self.font_small.render("Tekan [F1] untuk memulai pertandingan baru", True, self.color_gray)

        self.screen.blit(txt_win, (cx - (txt_win.get_width() // 2), cy))
        self.screen.blit(txt_res, (cx - (txt_res.get_width() // 2), cy + 30))
        self.screen.blit(txt_score, (cx - (txt_score.get_width() // 2), cy + 55))
        self.screen.blit(txt_prompt, (cx - (txt_prompt.get_width() // 2), cy + 85))

    # =========================================================================
    # Game Loop Utama
    # =========================================================================

    def run(self):
        """Loop utama aplikasi Pygame."""
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0
            mouse_pos = pygame.mouse.get_pos()

            # --- 1. Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Klik Kiri
                        if self.wall_mode:
                            inter = self._get_intersection_from_pixel(event.pos[0], event.pos[1])
                            if inter is not None:
                                self.handle_wall_click(inter)
                        else:
                            cell = self._get_cell_from_pixel(event.pos[0], event.pos[1])
                            if cell is not None:
                                self.handle_cell_click(cell)

                    elif event.button == 3:  # Klik Kanan
                        # Rotasi orientasi tembok H / V
                        self.wall_orient = "V" if self.wall_orient == "H" else "H"
                        lbl = "Tegak (|)" if self.wall_orient == "H" else "Mendatar (-)"
                        self.log_message(f"Orientasi tembok diubah ke: {lbl}")

                elif event.type == pygame.KEYDOWN:
                    # Reset Game (F1)
                    if event.key == pygame.K_F1:
                        self.state = GameState.create_initial_state(seed=42)
                        self.wall_mode = False
                        self.rope_mode = False
                        self.auto_play = False
                        self.log_message("Permainan di-reset ke kondisi awal S0.")

                    # Toggle Wall Mode (W)
                    elif event.key == pygame.K_w:
                        self.wall_mode = not self.wall_mode
                        self.rope_mode = False
                        lbl = "Tegak (|)" if self.wall_orient == "H" else "Mendatar (-)"
                        status = f"AKTIF ({lbl})" if self.wall_mode else "NON-AKTIF"
                        self.log_message(f"Mode pasang tembok: {status}")

                    # Rotasi Tembok (R)
                    elif event.key == pygame.K_r:
                        self.wall_orient = "V" if self.wall_orient == "H" else "H"
                        lbl = "Tegak (|)" if self.wall_orient == "H" else "Mendatar (-)"
                        self.log_message(f"Orientasi tembok: {lbl}")

                    # Toggle Rope Jump Mode (E)
                    elif event.key == pygame.K_e:
                        self.rope_mode = not self.rope_mode
                        self.wall_mode = False
                        status = "AKTIF" if self.rope_mode else "NON-AKTIF"
                        self.log_message(f"Mode Grappling Rope: {status}")

                    # Langkah Manual (SPASI)
                    elif event.key == pygame.K_SPACE:
                        self.execute_auto_step()

                    # Toggle Auto-Play Simulation (P)
                    elif event.key == pygame.K_p:
                        self.auto_play = not self.auto_play
                        status = "AKTIF" if self.auto_play else "NON-AKTIF"
                        self.log_message(f"Mode Auto-Play: {status}")

                    # Toggle Alpha-Beta Mode (A)
                    elif event.key == pygame.K_a:
                        is_ab = self.ai_agent.toggle_alpha_beta()
                        self.log_message(f"AI Mode diubah: {self.ai_agent.mode_name}")

                    # Kontrol Pergerakan Panah
                    elif event.key in (pygame.K_UP, pygame.K_w) and not self.wall_mode:
                        self.handle_arrow_move(-1, 0)
                    elif event.key in (pygame.K_DOWN, pygame.K_s) and not self.wall_mode:
                        self.handle_arrow_move(1, 0)
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and not self.wall_mode:
                        self.handle_arrow_move(0, -1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and not self.wall_mode:
                        self.handle_arrow_move(0, 1)

            # --- 2. Update Otomatis (AI Turn & Auto-Play) ---
            if not self.state.is_game_over:
                # Giliran AI Boss otomatis dieksekusi setelah jeda singkat
                if self.state.current_turn == "AI":
                    if time.time() - self.ai_wait_timer >= self.ai_delay_seconds:
                        self.execute_ai_turn()

                # Mode Auto-Play
                elif self.auto_play:
                    self.auto_timer += dt
                    if self.auto_timer >= 0.6:  # Setiap 600ms melangkah
                        self.auto_timer = 0.0
                        self.execute_auto_step()

            # --- 3. Render Layar ---
            self.draw(mouse_pos)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    ui = GameUI()
    ui.run()