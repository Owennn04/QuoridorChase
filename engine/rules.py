"""
Rule enforcement, action validation, and cage prevention for Quoridor Chase.
PIC: Deus, Althaf (Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S)

Covers:
- Orthogonal movement across unblocked planar grid edges
- Grappling Rope (Wall Jump) single-use leap
- Juggernaut Smash through wall destruction
- Standard 2-tile wall placement & intersection verification
- Classical Quoridor "No-Complete-Cage" BFS invariant
"""

from collections import deque
from typing import List, Tuple, Optional, Set

try:
    from engine.state import GameState, Cell, WallEdge, canonical_edge
except ImportError:
    try:
        from .state import GameState, Cell, WallEdge, canonical_edge
    except ImportError:
        from state import GameState, Cell, WallEdge, canonical_edge

Action = Tuple[str, any]


def get_valid_steps(state: GameState, pos: Cell) -> List[Cell]:
    """Return all adjacent cells reachable via unblocked orthogonal movement."""
    valid = []
    x, y = pos
    for nx, ny, is_blocked in state.get_adjacent_cells(x, y):
        if not is_blocked:
            valid.append((nx, ny))
    return valid


def can_wall_jump(state: GameState, runner_idx: int) -> List[Tuple[Cell, WallEdge]]:
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


def can_juggernaut_smash(state: GameState) -> List[Tuple[Cell, WallEdge]]:
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


def has_path_bfs(state: GameState, start: Cell, target: Cell, extra_wall: Optional[WallEdge] = None) -> bool:
    """Standard BFS checking if an unblocked path exists between start and target."""
    if start == target:
        return True
    walls = state.all_walls()
    if extra_wall:
        walls = walls | {extra_wall}
    visited: Set[Cell] = {start}
    queue: deque[Cell] = deque([start])

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


def get_reachable_component_size(state: GameState, start: Cell, extra_wall: Optional[WallEdge] = None) -> int:
    """Return number of cells reachable from start via BFS."""
    walls = state.all_walls()
    if extra_wall:
        walls = walls | {extra_wall}
    visited: Set[Cell] = {start}
    queue: deque[Cell] = deque([start])

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


def wall_to_edges(orient: str, x: int, y: int) -> Tuple[WallEdge, WallEdge]:
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


def validate_no_complete_cage_edges(state: GameState, candidate_edges: List[WallEdge]) -> bool:
    """Validate that adding candidate_edges does not completely trap any player."""
    walls = state.all_walls()
    for e in candidate_edges:
        if e in walls:
            return False
    combined_walls = walls | set(candidate_edges)

    def comp_size(start: Cell) -> int:
        visited = {start}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < state.grid_size and 0 <= ny < state.grid_size:
                    nbr = (nx, ny)
                    if nbr not in visited:
                        edge = canonical_edge((cx, cy), nbr)
                        if edge not in combined_walls:
                            visited.add(nbr)
                            q.append(nbr)
        return len(visited)

    if comp_size(state.p_ai) < 4:
        return False
    for r_pos in state.p_runners:
        if comp_size(r_pos) < 4:
            return False
    return True


def is_valid_2tile_wall(state: GameState, orient: str, x: int, y: int) -> bool:
    """Check if 2-tile wall placement (orient, x, y) is legal under standard Quoridor rules."""
    g = state.grid_size
    if not (0 <= x < g - 1 and 0 <= y < g - 1):
        return False
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


def get_all_valid_2tile_walls(state: GameState) -> List[Tuple[str, int, int]]:
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


def validate_no_complete_cage(state: GameState, candidate_edge: WallEdge) -> bool:
    """
    Classical Quoridor Invariant:
    A wall placement is illegal if it completely traps any player in a zero-escape cage
    or severs all access. In our 9x9 arena, each player must retain reachability to at least 4 cells.
    """
    if candidate_edge in state.all_walls():
        return False
    # Verify AI Boss has room to navigate
    if get_reachable_component_size(state, state.p_ai, candidate_edge) < 4:
        return False
    # Verify both runners have room to navigate
    for r_pos in state.p_runners:
        if get_reachable_component_size(state, r_pos, candidate_edge) < 4:
            return False
    return True


def get_valid_wall_placements(state: GameState, center: Optional[Cell] = None, max_radius: int = 2) -> List[WallEdge]:
    """
    Candidate Wall Filtering:
    Enumerate edges within max_radius of center that do not violate the no-cage rule.
    If center is None, enumerates across board.
    """
    valid_walls: List[WallEdge] = []
    current_walls = state.all_walls()
    g = state.grid_size

    if center is not None:
        cx, cy = center
        x_min, x_max = max(0, cx - max_radius), min(g - 1, cx + max_radius)
        y_min, y_max = max(0, cy - max_radius), min(g - 1, cy + max_radius)
    else:
        x_min, x_max = 0, g - 1
        y_min, y_max = 0, g - 1

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            # Check horizontal wall between (x, y) and (x, y+1)
            if y + 1 < g:
                h_edge = canonical_edge((x, y), (x, y + 1))
                if h_edge not in current_walls and validate_no_complete_cage(state, h_edge):
                    valid_walls.append(h_edge)
            # Check vertical wall between (x, y) and (x+1, y)
            if x + 1 < g:
                v_edge = canonical_edge((x, y), (x + 1, y))
                if v_edge not in current_walls and validate_no_complete_cage(state, v_edge):
                    valid_walls.append(v_edge)

    return valid_walls

