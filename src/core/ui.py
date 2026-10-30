import pygame
import sys
from config import (
    GRID_SIZE, THEME_TOKENS, 
    AI_START_POS, RUNNER_START_POSITIONS
)

# Konversi warna HEX dari config ke format RGB yang dipahami Pygame
def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

# Setup konstanta tampilan
CELL_SIZE = 60
WALL_THICKNESS = 15
WINDOW_SIZE = (GRID_SIZE * CELL_SIZE) + (GRID_SIZE * WALL_THICKNESS) + WALL_THICKNESS

class GameUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption("Quoridor Chase: Lockdown")
        
        # Load warna dari config
        self.color_bg = hex_to_rgb(THEME_TOKENS["cyber_bg"])
        self.color_grid = hex_to_rgb(THEME_TOKENS["cyber_panel"])
        self.color_border = hex_to_rgb(THEME_TOKENS["cyber_border"])
        
        self.color_ai = hex_to_rgb(THEME_TOKENS["ai_crimson"])
        self.color_runner = hex_to_rgb(THEME_TOKENS["runner_cyan"])
        self.color_orb = hex_to_rgb(THEME_TOKENS["orb_gold"])
        
        # Posisi sementara untuk testing visual
        self.ai_pos = AI_START_POS
        self.runner_positions = RUNNER_START_POSITIONS
        self.orbs = [(2, 2), (2, 6), (6, 4)] # Contoh posisi orb acak awal

    def _get_pixel_pos(self, row, col):
        """Fungsi helper untuk mendapatkan koordinat piksel dari posisi grid (X, Y)"""
        x = WALL_THICKNESS + col * (CELL_SIZE + WALL_THICKNESS)
        y = WALL_THICKNESS + row * (CELL_SIZE + WALL_THICKNESS)
        return x, y

    def draw_board(self):
        self.screen.fill(self.color_bg)
        
        # 1. Menggambar petak grid 9x9
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                x, y = self._get_pixel_pos(row, col)
                pygame.draw.rect(self.screen, self.color_grid, (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, self.color_border, (x, y, CELL_SIZE, CELL_SIZE), 1)

        # 2. Menggambar Data Orbs (Lingkaran emas)
        for orb_r, orb_c in self.orbs:
            x, y = self._get_pixel_pos(orb_r, orb_c)
            center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
            pygame.draw.circle(self.screen, self.color_orb, center, CELL_SIZE // 4)

        # 3. Menggambar Runners (Lingkaran cyan)
        for r_row, r_col in self.runner_positions:
            x, y = self._get_pixel_pos(r_row, r_col)
            center = (x + CELL_SIZE // 2, y + CELL_SIZE // 2)
            pygame.draw.circle(self.screen, self.color_runner, center, CELL_SIZE // 3)
            
        # 4. Menggambar AI Boss (Lingkaran merah)
        ai_x, ai_y = self._get_pixel_pos(self.ai_pos[0], self.ai_pos[1])
        ai_center = (ai_x + CELL_SIZE // 2, ai_y + CELL_SIZE // 2)
        pygame.draw.circle(self.screen, self.color_ai, ai_center, CELL_SIZE // 2.5)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.draw_board()
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    ui = GameUI()
    ui.run()