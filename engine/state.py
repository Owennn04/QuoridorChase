"""
GameState representation for Quoridor Chase: Lockdown.
PIC: Deus, Althaf (Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S)

Implements:
- State Space S formalization
- Initial State S0 definition
- Fast shallow cloning for minimax tree expansion
- Adjacent cell query generator with wall detection
- Terminal evaluation and Utility Function U(s)
"""

import random

from config import (
    GRID_SIZE,
    AI_START_POS,
    RUNNER_START_POSITIONS,
    RESPAWN_CANDIDATE_CORNERS,
    SMASH_COOLDOWN_INITIAL,
    INITIAL_RUNNER_ROPES,
    INITIAL_RUNNER_WALLS,
    INITIAL_AI_WALLS,
    ACTIVE_ORB_TARGET_COUNT,
    MATCH_DURATION_SECONDS,
    MAX_SIMULATION_TURNS,
    UTILITY_AI_WIN,
    UTILITY_RUNNER_WIN,
    UTILITY_DRAW,
    POINTS_AI_TAG,
    POINTS_RUNNER_ORB
)

def canonical_edge(c1, c2):
    """Return edge with sorted endpoints to ensure unique canonical representation."""
    return (c1, c2) if c1 <= c2 else (c2, c1)


def edge_to_groove(edge):
    """Convert canonical edge to groove representation ('H'/'V', x, y)."""
    (x1, y1), (x2, y2) = edge
    if y1 == y2 and abs(x1 - x2) == 1:
        # Vertical wall between (min_x, y1) and (min_x + 1, y1)
        return ("V", min(x1, x2), y1)
    elif x1 == x2 and abs(y1 - y2) == 1:
        # Horizontal wall between (x1, min_y) and (x1, min_y + 1)
        return ("H", x1, min(y1, y2))
    raise ValueError(f"Edge {edge} is not adjacent orthogonal.")


def groove_to_edge(orient, x, y):
    """Convert groove representation to canonical edge."""
    if orient.upper() == "V":
        return canonical_edge((x, y), (x + 1, y))
    elif orient.upper() == "H":
        return canonical_edge((x, y), (x, y + 1))
    raise ValueError(f"Unknown groove orientation: {orient}")


class GameState:
    """
    Formal State Space representation for Quoridor Chase.
    S = <p_ai, p_runners, solo_walls, coop_walls, orbs, smash_cooldown, runner_ropes, score_ai, score_runners, current_turn>
    """
    __slots__ = (
        "grid_size",
        "p_ai",
        "p_runners",
        "solo_walls",
        "coop_walls",
        "orbs",
        "smash_cooldown",
        "runner_ropes",
        "runner_walls",
        "ai_walls",
        "runner_placed_walls",
        "ai_placed_walls",
        "score_ai",
        "score_runners",
        "current_turn",
        "turn_count",
        "time_remaining",
        "match_start_time",
        "placed_walls",
        "is_game_over",
        "winner",
        "_cached_all_walls"
    )

    def __init__(
        self,
        grid_size=GRID_SIZE,
        p_ai=AI_START_POS,
        p_runners=None,
        solo_walls=None,
        coop_walls=None,
        orbs=None,
        smash_cooldown=SMASH_COOLDOWN_INITIAL,
        runner_ropes=None,
        runner_walls=None,
        ai_walls=None,
        runner_placed_walls=None,
        ai_placed_walls=None,
        score_ai=0,
        score_runners=0,
        current_turn="R1",
        turn_count=0,
        time_remaining=float(MATCH_DURATION_SECONDS),
        match_start_time=None,
        placed_walls=None,
        is_game_over=False,
        winner=None
    ):
        self.grid_size = grid_size
        self.p_ai = p_ai
        self.p_runners = list(p_runners) if p_runners is not None else list(RUNNER_START_POSITIONS)
        self.solo_walls = dict(solo_walls) if solo_walls is not None else {}
        self.coop_walls = set(coop_walls) if coop_walls is not None else set()
        self.orbs = set(orbs) if orbs is not None else set()
        self.smash_cooldown = smash_cooldown
        self.runner_ropes = list(runner_ropes) if runner_ropes is not None else list(INITIAL_RUNNER_ROPES)
        self.runner_walls = list(runner_walls) if runner_walls is not None else [INITIAL_RUNNER_WALLS, INITIAL_RUNNER_WALLS]
        self.ai_walls = ai_walls if ai_walls is not None else INITIAL_AI_WALLS
        self.runner_placed_walls = [list(runner_placed_walls[0]), list(runner_placed_walls[1])] if runner_placed_walls is not None else [[], []]
        self.ai_placed_walls = list(ai_placed_walls) if ai_placed_walls is not None else []
        self.score_ai = score_ai
        self.score_runners = score_runners
        self.current_turn = current_turn
        self.turn_count = turn_count
        self.time_remaining = time_remaining
        self.match_start_time = match_start_time
        self.placed_walls = dict(placed_walls) if placed_walls is not None else {}
        self.is_game_over = is_game_over
        self.winner = winner
        self._cached_all_walls = None

    @classmethod
    def create_initial_state(cls, seed=42):
        """
        Create canonical initial state S0 (Proposal Bab 2.2 #2):
        - AI Boss at center (4, 4)
        - Runners at (0, 4) and (8, 4)
        - No active walls (W = emptyset)
        - 3 Data Orbs randomly spawned
        - Smash cooldown = 0 (READY)
        - Grappling Rope = 1 per runner
        - Scores = 0
        - Turn = R1
        """
        state = cls(
            grid_size=GRID_SIZE,
            p_ai=AI_START_POS,
            p_runners=list(RUNNER_START_POSITIONS),
            solo_walls={},
            coop_walls=set(),
            orbs=set(),
            smash_cooldown=SMASH_COOLDOWN_INITIAL,
            runner_ropes=list(INITIAL_RUNNER_ROPES),
            runner_walls=[INITIAL_RUNNER_WALLS, INITIAL_RUNNER_WALLS],
            ai_walls=INITIAL_AI_WALLS,
            runner_placed_walls=[[], []],
            ai_placed_walls=[],
            score_ai=0,
            score_runners=0,
            current_turn="R1",
            turn_count=0,
            time_remaining=float(MATCH_DURATION_SECONDS),
            is_game_over=False,
            winner=None
        )
        rng = random.Random(seed)
        # Populate initial orbs on empty cells
        occupied = {state.p_ai, state.p_runners[0], state.p_runners[1]}
        candidates = []
        for x in range(state.grid_size):
            for y in range(state.grid_size):
                if (x, y) not in occupied:
                    candidates.append((x, y))
        chosen = rng.sample(candidates, ACTIVE_ORB_TARGET_COUNT)
        state.orbs = set(chosen)
        return state

    def clone(self):
        """Fast shallow/field clone avoiding copy.deepcopy overhead."""
        cloned = GameState.__new__(GameState)
        cloned.grid_size = self.grid_size
        cloned.p_ai = self.p_ai
        cloned.p_runners = [self.p_runners[0], self.p_runners[1]]
        cloned.solo_walls = self.solo_walls.copy()
        cloned.coop_walls = self.coop_walls.copy()
        cloned.orbs = self.orbs.copy()
        cloned.smash_cooldown = self.smash_cooldown
        cloned.runner_ropes = [self.runner_ropes[0], self.runner_ropes[1]]
        cloned.runner_walls = [self.runner_walls[0], self.runner_walls[1]]
        cloned.ai_walls = self.ai_walls
        cloned.runner_placed_walls = [list(self.runner_placed_walls[0]), list(self.runner_placed_walls[1])]
        cloned.ai_placed_walls = list(self.ai_placed_walls)
        cloned.score_ai = self.score_ai
        cloned.score_runners = self.score_runners
        cloned.current_turn = self.current_turn
        cloned.turn_count = self.turn_count
        cloned.time_remaining = self.time_remaining
        cloned.match_start_time = self.match_start_time
        cloned.placed_walls = self.placed_walls.copy()
        cloned.is_game_over = self.is_game_over
        cloned.winner = self.winner
        cloned._cached_all_walls = None
        return cloned

    def all_walls(self):
        """Return the union of solo and co-op active wall edges."""
        if self._cached_all_walls is None:
            self._cached_all_walls = set(self.solo_walls.keys()) | self.coop_walls
        return self._cached_all_walls

    def invalidate_wall_cache(self):
        self._cached_all_walls = None

    def is_blocked(self, c1, c2):
        """Check if movement between cell c1 and adjacent cell c2 is blocked by a wall."""
        return canonical_edge(c1, c2) in self.all_walls()


    def get_adjacent_cells(self, x, y):
        """
        Yield (nx, ny, is_blocked_by_wall) for orthogonal adjacent in-bounds cells.
        """
        walls = self.all_walls()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size:
                edge = canonical_edge((x, y), (nx, ny))
                yield nx, ny, (edge in walls)

    def spawn_replacement_orb(self, rng=None):
        """Memunculkan Data Orb baru secara acak murni (fully random) di petak kosong."""
        occupied = {self.p_ai, self.p_runners[0], self.p_runners[1]} | self.orbs
        empty_cells = [
            (x, y) for x in range(self.grid_size) for y in range(self.grid_size)
            if (x, y) not in occupied
        ]
        if not empty_cells:
            return None

        if rng is not None:
            chosen = rng.choice(empty_cells)
        else:
            # Deterministic pseudo-random selection berbasis hash state agar
            # eksplorasi tree Minimax & Alpha-Beta konsisten (tidak terganggu oleh global RNG mutation)
            idx = (self.turn_count * 17 + len(self.all_walls()) * 7 + sum(x * 9 + y for x, y in self.orbs)) % len(empty_cells)
            chosen = empty_cells[idx]
        
        self.orbs.add(chosen)
        return chosen


    def respawn_runner(self, runner_idx):
        """Respawn tagged runner di petak pojok aman yang paling jauh dari AI Boss."""
        occupied = {self.p_ai, self.p_runners[1 - runner_idx]} | self.orbs
        candidates = [c for c in RESPAWN_CANDIDATE_CORNERS if c not in occupied]
        if not candidates:
            candidates = [
                (x, y) for x in range(self.grid_size) for y in range(self.grid_size)
                if (x, y) not in occupied
            ]
        
        dest = max(candidates, key=lambda c: abs(c[0] - self.p_ai[0]) + abs(c[1] - self.p_ai[1]))
        self.p_runners[runner_idx] = dest
        return dest

    def is_terminal(self):
        """Terminal condition: match timer expired, turn limit reached, or explicit game over."""
        return self.is_game_over or self.time_remaining <= 0 or self.turn_count >= MAX_SIMULATION_TURNS

    def get_utility(self):
        """
        Utility Function U(s) from proposal Bab 2.2 #6:
        U(s) = +1000 if score_ai > score_runners
        U(s) = -1000 if score_runners > score_ai
        U(s) = 0 if score_ai == score_runners
        """
        if self.score_ai > self.score_runners:
            return UTILITY_AI_WIN
        elif self.score_runners > self.score_ai:
            return UTILITY_RUNNER_WIN
        return UTILITY_DRAW

    def apply_action(self, action, is_max=None):
        """Execute action via Transition Model T(s, a)."""
        from engine.transition import apply_action as _apply_action
        return _apply_action(self, action, is_max=is_max)

    def to_dict(self):
        """Serialize state for JSON / WebSocket telemetry transmission."""
        return {
            "grid_size": self.grid_size,
            "p_ai": list(self.p_ai),
            "p_runners": [list(p) for p in self.p_runners],
            "solo_walls": [
                {"edge": [list(e[0]), list(e[1])], "turns_left": ttl, "groove": edge_to_groove(e)}
                for e, ttl in self.solo_walls.items()
            ],
            "coop_walls": [
                {"edge": [list(e[0]), list(e[1])], "groove": edge_to_groove(e)}
                for e in self.coop_walls
            ],
            "placed_walls": [
                {
                    "orient": w[0],
                    "x": w[1],
                    "y": w[2],
                    "turns_left": ttl[0] if isinstance(ttl, (tuple, list)) else ttl,
                    "owner": ttl[1] if isinstance(ttl, (tuple, list)) else ("COOP" if (ttl if isinstance(ttl, int) else ttl[0]) <= -1 else "RUNNER"),
                    "is_coop": (ttl[0] <= -1 if isinstance(ttl, (tuple, list)) else ttl <= -1)
                }
                for w, ttl in self.placed_walls.items()
            ],
            "orbs": [list(o) for o in self.orbs],
            "smash_cooldown": self.smash_cooldown,
            "smash_ready": (self.smash_cooldown == 0),
            "runner_ropes": list(self.runner_ropes),
            "score_ai": self.score_ai,
            "score_runners": self.score_runners,
            "current_turn": self.current_turn,
            "turn_count": self.turn_count,
            "time_remaining": round(self.time_remaining, 1),
            "match_started": (self.match_start_time is not None),
            "is_game_over": self.is_game_over,
            "winner": self.winner
        }
