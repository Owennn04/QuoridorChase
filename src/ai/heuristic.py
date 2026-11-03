from config import (
    W1_CLOSEST_RUNNER, W1_SECOND_RUNNER, W2_ORB_ACCESS,
    W3_SKILL_READY_BONUS, W3_SKILL_COOLDOWN_PENALTY, W4_ROPE_PENALTY,
    W5_CONFINEMENT_SCALE, SCORE_DIFF_WEIGHT,
    UTILITY_AI_WIN, UTILITY_RUNNER_WIN, UTILITY_DRAW
)
from .pathfinding import skill_aware_a_star
from engine.rules import get_valid_steps

def calculate_confinement(state, start_pos, max_depth=15):
    """
    Algoritma Flood-Fill untuk menghitung luas area yang bisa diakses Runner.
    Hanya menghitung kurungan jika runner benar-benar terhalang oleh tembok fisik,
    bukan hanya karena berdiri di pinggir atau sudut batas grid arena (False Confinement).
    """
    # 1. Jika tidak ada tembok aktif sama sekali di papan, tidak ada kurungan
    walls = state.all_walls()
    if not walls:
        return 0

    # 2. Periksa apakah ada tembok dalam radius interaksi dekat dengan start_pos (radius <= 2)
    sx, sy = start_pos
    has_nearby_wall = False
    for (c1, c2) in walls:
        if (abs(c1[0] - sx) + abs(c1[1] - sy) <= 2) or (abs(c2[0] - sx) + abs(c2[1] - sy) <= 2):
            has_nearby_wall = True
            break

    if not has_nearby_wall:
        return 0

    # 3. Hitung hambatan arah langkah langsung akibat tembok (immediate mobility restriction)
    blocked_by_wall = 0
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = sx + dx, sy + dy
        if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
            if state.is_blocked(start_pos, (nx, ny)):
                blocked_by_wall += 1

    # 4. Hitung Flood-Fill jika memang terdeteksi ada tembok di dekat pemain
    visited = set([start_pos])
    queue = [start_pos]
    
    while queue and len(visited) < max_depth:
        curr = queue.pop(0)
        for next_pos in get_valid_steps(state, curr):
            if next_pos not in visited:
                visited.add(next_pos)
                queue.append(next_pos)
                
    # Semakin sedikit sel yang bisa diakses, semakin tinggi nilai kurungannya
    flood_confinement = max_depth - len(visited)
    return flood_confinement + (blocked_by_wall * 2)

def evaluate_state(state):
    """
    Fungsi Evaluasi Heuristik h(s) untuk AI Boss.
    Berdasarkan formulasi: w1*JarakRunners + w2*AksesOrb + w3*SkillBonus - w4*SisaRope + w5*Confinement
    Semakin tinggi nilai kembalian, semakin menguntungkan bagi AI Boss.
    """
    # 1. Goal Test (Terminal State Evaluation)
    if state.time_remaining <= 0 or getattr(state, "turn_count", 0) >= 60 or state.is_terminal():
        if state.score_ai > state.score_runners:
            return UTILITY_AI_WIN
        elif state.score_runners > state.score_ai:
            return UTILITY_RUNNER_WIN
        else:
            return UTILITY_DRAW
            
    h_score = 0.0
    
    # Status skill Juggernaut Smash
    has_smash = (state.smash_cooldown == 0)
    
    # 2. Parameter W1: JarakRunners(s)
    # AI Boss berusaha memperkecil jarak dengan target
    dist_r1 = skill_aware_a_star(state, state.p_ai, state.p_runners[0], has_smash)
    dist_r2 = skill_aware_a_star(state, state.p_ai, state.p_runners[1], has_smash)
    
    distances = sorted([dist_r1, dist_r2])
    closest_dist = distances[0]
    second_dist = distances[1]
    
    if closest_dist != float('inf'):
        h_score += (20 - closest_dist) * W1_CLOSEST_RUNNER
    if second_dist != float('inf'):
        h_score += (20 - second_dist) * W1_SECOND_RUNNER
        
    # 3. Parameter W2: AksesOrb(s)
    # Menilai jarak Runners ke Orbs aktif
    min_orb_dist = float('inf')
    for runner_pos in state.p_runners:
        for orb_pos in state.orbs:
            dist = skill_aware_a_star(state, runner_pos, orb_pos, initial_smash_ready=False)
            if dist < min_orb_dist:
                min_orb_dist = dist
    
    if min_orb_dist != float('inf'):
        h_score += min_orb_dist * W2_ORB_ACCESS
        
    # 4. Parameter W3: SkillBonus(s)
    # AI cenderung menyimpan skill untuk momen krusial
    if has_smash:
        h_score += W3_SKILL_READY_BONUS
    else:
        h_score += state.smash_cooldown * W3_SKILL_COOLDOWN_PENALTY
        
    # 5. Parameter W4: SisaRope(s)
    # AI waspada jika Runner masih punya Grappling Rope
    total_ropes = sum(state.runner_ropes)
    h_score -= total_ropes * W4_ROPE_PENALTY
    
    # 6. Parameter W5: Confinement Score
    # Menghitung tingkat kurungan untuk Runner 1 dan Runner 2
    conf_r1 = calculate_confinement(state, state.p_runners[0])
    conf_r2 = calculate_confinement(state, state.p_runners[1])
    h_score += (conf_r1 + conf_r2) * W5_CONFINEMENT_SCALE
    
    # 7. Selisih Poin Aktual
    score_diff = state.score_ai - state.score_runners
    h_score += score_diff * SCORE_DIFF_WEIGHT
    
    return h_score