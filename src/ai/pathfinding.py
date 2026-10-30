import heapq

def manhattan_distance(pos1, pos2):
    """Fungsi heuristik dasar untuk A* pada grid orthogonal."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def skill_aware_a_star(state, start_pos, target_pos, initial_smash_ready=True):
    """
    Algoritma 3D A* Pathfinding.
    State direpresentasikan sebagai (x, y, has_smash).
    """
    # Priority Queue: (f_score, g_score, (x, y), has_smash)
    open_set = []
    heapq.heappush(open_set, (0, 0, start_pos, initial_smash_ready))
    
    # Dictionary untuk menyimpan cost terkecil menuju suatu state (x, y, has_smash)
    g_scores = {(start_pos, initial_smash_ready): 0}
    
    # Grid boundaries
    grid_size = state.grid_size
    
    while open_set:
        _, current_g, current_pos, has_smash = heapq.heappop(open_set)
        
        # Jika sudah mencapai target
        if current_pos == target_pos:
            return current_g
            
        # Periksa 4 arah ortogonal
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = current_pos[0] + dx, current_pos[1] + dy
            
            # Pastikan masih di dalam grid
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                neighbor_pos = (nx, ny)
                
                # Cek apakah ada tembok yang menghalangi pergerakan ini
                # (Asumsi: ada metode is_wall_between di state)
                wall_blocking = state.is_wall_between(current_pos, neighbor_pos)
                
                # Logika 3D State Transisi
                if not wall_blocking:
                    # Jalan bebas hambatan
                    new_smash_status = has_smash
                    move_cost = 1
                elif wall_blocking and has_smash:
                    # Menembus tembok menggunakan Juggernaut Smash
                    new_smash_status = False
                    move_cost = 1 # Atau bisa diberi penalti cost jika diperlukan
                else:
                    # Terhalang tembok dan tidak punya skill Smash
                    continue 
                
                tentative_g = current_g + move_cost
                neighbor_state = (neighbor_pos, new_smash_status)
                
                # Jika menemukan rute yang lebih cepat ke state tersebut
                if neighbor_state not in g_scores or tentative_g < g_scores[neighbor_state]:
                    g_scores[neighbor_state] = tentative_g
                    f_score = tentative_g + manhattan_distance(neighbor_pos, target_pos)
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor_pos, new_smash_status))
                    
    # Jika tidak ada jalan sama sekali (terkurung sempurna)
    return float('inf')