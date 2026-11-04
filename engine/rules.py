"""
Rule enforcement, action validation, and cage prevention for Quoridor Chase.
PIC: Deus, Althaf (Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S)

Covers:
- Orthogonal movement across unblocked planar grid edges
- Grappling Rope (Wall Jump) single-use leap
- Juggernaut Smash through wall destruction
- Standard 2-tile wall placement & intersection verification
- Co-op Wall Welding verification
- Classical Quoridor "No-Complete-Cage" BFS invariant
"""

from collections import deque

from engine.state import GameState, canonical_edge


def get_valid_steps(state, pos):
    """Return all adjacent cells reachable via unblocked orthogonal movement."""
    valid = []
    x, y = pos
    for nx, ny, is_blocked in state.get_adjacent_cells(x, y):
        if not is_blocked:
            valid.append((nx, ny))
    return valid


def can_wall_jump(state, runner_idx):
    """
    Check if the runner can use Grappling Rope to jump across an adjacent wall.
    Returns list of (destination_cell, jumped_wall_edge).
    """
    if state.runner_ropes[runner_idx] <= 0:
        return []
    pos = state.p_runners[runner_idx]
    x, y = pos
    results = []
    for nx, ny, is_blocked in state.get_adjacent_cells(x, y):
        if is_blocked:
            edge = canonical_edge(pos, (nx, ny))
            results.append(((nx, ny), edge))
    return results


def can_juggernaut_smash(state):
    """
    Check if AI Boss can use Juggernaut Smash to break through an adjacent wall.
    Returns list of (destination_cell, destroyed_wall_edge).
    """
    if state.smash_cooldown != 0:
        return []
    x, y = state.p_ai
    results = []
    for nx, ny, is_blocked in state.get_adjacent_cells(x, y):
        if is_blocked:
            edge = canonical_edge(state.p_ai, (nx, ny))
            results.append(((nx, ny), edge))
    return results


def has_path_bfs(state, start, target, extra_wall=None):
    """Standard BFS checking if an unblocked path exists between start and target."""
    if start == target:
        return True
    walls = state.all_walls()
    if extra_wall:
        walls = walls | {extra_wall}
    visited = {start}
    queue = deque([start])

    while queue:
        curr = queue.popleft()
        if curr == target:
            return True
        cx, cy = curr
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
                nbr = (nx, ny)
                if nbr not in visited:
                    edge = canonical_edge(curr, nbr)
                    if edge not in walls:
                        visited.add(nbr)
                        queue.append(nbr)
    return False


def get_reachable_component_size(state, start, extra_wall=None):
    """Return number of cells reachable from start via BFS."""
    walls = state.all_walls()
    if extra_wall:
        walls = walls | {extra_wall}
    visited = {start}
    queue = deque([start])

    while queue:
        curr = queue.popleft()
        cx, cy = curr
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
                nbr = (nx, ny)
                if nbr not in visited:
                    edge = canonical_edge(curr, nbr)
                    if edge not in walls:
                        visited.add(nbr)
                        queue.append(nbr)
    return len(visited)


def wall_to_edges(orient, x, y):
    """Convert a 2-tile wall at intersection (orient, x, y) to its two canonical grid edges."""
    if orient.upper() == "H":
        e1 = canonical_edge((x, y), (x, y + 1))
        e2 = canonical_edge((x + 1, y), (x + 1, y + 1))
        return (e1, e2)
    elif orient.upper() == "V":
        e1 = canonical_edge((x, y), (x + 1, y))
        e2 = canonical_edge((x, y + 1), (x + 1, y + 1))
        return (e1, e2)
    raise ValueError(f"Unknown orientation: {orient}")


def validate_no_complete_cage_edges(state, candidate_edges):
    """
    Classical Quoridor Invariant:
    A wall placement is illegal if it completely traps any player or closes off all paths.
    1. Every player (AI, R1, R2) must retain at least 1 valid unblocked orthogonal step.
    2. An unblocked path must exist between AI Boss and Runner 1.
    3. An unblocked path must exist between AI Boss and Runner 2.
    """
    if isinstance(candidate_edges, tuple) and len(candidate_edges) == 2 and isinstance(candidate_edges[0], tuple):
        candidate_edges = [candidate_edges]
    elif not isinstance(candidate_edges, (list, tuple, set)):
        candidate_edges = [candidate_edges]

    walls = state.all_walls()
    for e in candidate_edges:
        if e in walls:
            return False
    combined_walls = walls | set(candidate_edges)

    # 1. Pastikan setiap pemain punya minimal 1 langkah ortogonal legal yang tidak tertutup tembok
    def has_at_least_one_step(pos):
        cx, cy = pos
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
                edge = canonical_edge((cx, cy), (nx, ny))
                if edge not in combined_walls:
                    return True
        return False

    if not has_at_least_one_step(state.p_ai):
        return False
    for r_pos in state.p_runners:
        if not has_at_least_one_step(r_pos):
            return False

    # 2. Pastikan ada jalur bebas (BFS unblocked path) dari AI Boss ke setiap Runner
    def has_path(start, target):
        if start == target:
            return True
        visited = {start}
        q = deque([start])
        while q:
            curr = q.popleft()
            if curr == target:
                return True
            cx, cy = curr
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
                    nbr = (nx, ny)
                    if nbr not in visited:
                        edge = canonical_edge((cx, cy), nbr)
                        if edge not in combined_walls:
                            visited.add(nbr)
                            q.append(nbr)
        return False

    if not has_path(state.p_ai, state.p_runners[0]):
        return False
    if not has_path(state.p_ai, state.p_runners[1]):
        return False

    return True


def is_valid_coop_weld(state, orient, x, y, runner_idx=None):
    """
    Check if a 2-tile wall at intersection (orient, x, y) can be welded into a permanent Co-op Wall.

    Rules for Co-op Wall Welding:
    1. Coordinates must be within board limits: 0 <= x < g - 1, 0 <= y < g - 1.
    2. Runner must have walls remaining in inventory (runner_walls > 0).
    3. The wall edges must already exist as an active Solo Wall in state.solo_walls.
    4. The wall must not already be permanent in state.coop_walls.
    5. The wall must not belong to the AI Boss.
    6. If runner_idx is provided, the wall must not be solo-welded by the same runner alone.
    """
    g = state.grid_size
    if not (0 <= x < g - 1 and 0 <= y < g - 1):
        return False

    # Periksa kuota inventory tembok runner
    if runner_idx is not None and hasattr(state, "runner_walls"):
        if state.runner_walls[runner_idx] <= 0:
            return False

    e1, e2 = wall_to_edges(orient, x, y)

    # Must be currently present in solo_walls
    if e1 not in state.solo_walls or e2 not in state.solo_walls:
        return False

    # Must not already be welded into coop_walls
    if e1 in state.coop_walls or e2 in state.coop_walls:
        return False

    w_key = (orient.upper(), x, y)
    if w_key in state.placed_walls:
        val = state.placed_walls[w_key]
        ttl = val[0] if isinstance(val, (tuple, list)) else val
        owner = val[1] if isinstance(val, (tuple, list)) and len(val) > 1 else "RUNNER"
        if ttl == -1 or owner == "COOP":
            return False  # Already permanent
        if owner == "AI":
            return False  # Runners cannot weld AI walls
        if runner_idx is not None and owner == f"RUNNER_{runner_idx}":
            return False  # Requires partner runner to reinforce/weld

    return True


def is_valid_2tile_wall(state, orient, x, y, allow_coop_welding=False, runner_idx=None):
    """Check if 2-tile wall placement (orient, x, y) is legal under standard Quoridor rules."""
    g = state.grid_size
    if not (0 <= x < g - 1 and 0 <= y < g - 1):
        return False

    # Periksa kuota inventory tembok runner jika runner_idx diberikan
    if runner_idx is not None and hasattr(state, "runner_walls"):
        if state.runner_walls[runner_idx] <= 0:
            return False

    # Check Co-op Wall Welding opportunity
    if allow_coop_welding and is_valid_coop_weld(state, orient, x, y, runner_idx=runner_idx):
        return True

    e1, e2 = wall_to_edges(orient, x, y)
    all_w = state.all_walls()
    if e1 in all_w or e2 in all_w:
        return False
    # Check intersecting perpendicular wall crossing at same intersection
    cross_orient = "V" if orient.upper() == "H" else "H"
    ce1, ce2 = wall_to_edges(cross_orient, x, y)
    if ce1 in all_w and ce2 in all_w:
        return False
    return validate_no_complete_cage_edges(state, [e1, e2])


def get_all_valid_2tile_walls(state):
    """Enumerate all legal 2-tile walls across the board."""
    valid_walls = []
    g = state.grid_size
    for x in range(g - 1):
        for y in range(g - 1):
            if is_valid_2tile_wall(state, "H", x, y):
                valid_walls.append(("H", x, y))
            if is_valid_2tile_wall(state, "V", x, y):
                valid_walls.append(("V", x, y))
    return valid_walls
