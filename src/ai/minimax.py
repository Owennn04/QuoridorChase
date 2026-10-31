"""
Adversarial Search: Minimax with Alpha-Beta Pruning & Candidate Move Filtering.
PIC: Deus, Althaf (Week 2 - Task 2.1: Algoritma Minimax & Alpha-Beta)

Features:
- Dual Modes:
  1. Alpha-Beta Pruning (Default & Recommended)
  2. Pure Minimax (Baseline comparison / Ablation study)
- Toggle switch / method to easily activate/deactivate Alpha-Beta Pruning
- Integrated with Task 2.2 Heuristic (evaluate_state from src.ai.heuristic)
- Candidate Move Filtering (prunes massive wall placement branching factor)
- Move Ordering heuristic (evaluates promising moves first for max pruning)
- Detailed search metrics (nodes explored, cutoffs, execution time)
"""

from __future__ import annotations
import time
import math
from typing import Tuple, List, Dict, Optional, Callable, Any

try:
    from engine.state import GameState, Cell, WallEdge, canonical_edge
    from engine.rules import (
        get_valid_steps,
        can_wall_jump,
        can_juggernaut_smash,
        is_valid_2tile_wall,
        validate_no_complete_cage_edges,
        wall_to_edges
    )
    from engine.transition import apply_action, apply_ai_action, apply_team_runners_action
    from config import (
        GRID_SIZE,
        UTILITY_AI_WIN,
        UTILITY_RUNNER_WIN,
        UTILITY_DRAW,
        POINTS_AI_TAG,
        POINTS_RUNNER_ORB
    )
    from src.ai.heuristic import evaluate_state
    from src.ai.pathfinding import manhattan_distance
except ImportError:
    try:
        from ...engine.state import GameState, Cell, WallEdge, canonical_edge
        from ...engine.rules import (
            get_valid_steps,
            can_wall_jump,
            can_juggernaut_smash,
            is_valid_2tile_wall,
            validate_no_complete_cage_edges,
            wall_to_edges
        )
        from ...engine.transition import apply_action, apply_ai_action, apply_team_runners_action
        from ...config import (
            GRID_SIZE,
            UTILITY_AI_WIN,
            UTILITY_RUNNER_WIN,
            UTILITY_DRAW,
            POINTS_AI_TAG,
            POINTS_RUNNER_ORB
        )
        from .heuristic import evaluate_state
        from .pathfinding import manhattan_distance
    except ImportError:
        from engine.state import GameState, Cell, WallEdge, canonical_edge
        from engine.rules import (
            get_valid_steps,
            can_wall_jump,
            can_juggernaut_smash,
            is_valid_2tile_wall,
            validate_no_complete_cage_edges,
            wall_to_edges
        )
        from engine.transition import apply_action, apply_ai_action, apply_team_runners_action
        from config import (
            GRID_SIZE,
            UTILITY_AI_WIN,
            UTILITY_RUNNER_WIN,
            UTILITY_DRAW,
            POINTS_AI_TAG,
            POINTS_RUNNER_ORB
        )
        from src.ai.heuristic import evaluate_state
        from src.ai.pathfinding import manhattan_distance

Action = Tuple[str, Any]


def get_candidate_actions_ai(
    state: GameState,
    max_walls: int = 4,
    wall_radius: int = 2
) -> List[Action]:
    """
    Candidate Move Filtering for AI Boss (Node MAX).
    
    Filters and orders legal actions:
    1. MOVE: Orthogonal adjacent steps (prioritizing steps closer to runners).
    2. SMASH: Juggernaut Smash if ready (prioritizing smashing toward closest runner).
    3. WALL: Focused 2-tile walls placed within tactical radius around runners
             or intercepting paths to orbs (capped at max_walls).
    """
    actions: List[Tuple[float, Action]] = []
    
    r1_pos = state.p_runners[0]
    r2_pos = state.p_runners[1]
    
    # --- 1. MOVE Actions ---
    valid_steps = get_valid_steps(state, state.p_ai)
    for step in valid_steps:
        # Check if step lands on a runner (immediate tag!)
        if step == r1_pos or step == r2_pos:
            priority = 1000.0  # Top priority
        else:
            d = min(manhattan_distance(step, r1_pos), manhattan_distance(step, r2_pos))
            priority = 100.0 - d
        actions.append((priority, ("MOVE", step)))

    # --- 2. SMASH Actions ---
    smash_moves = can_juggernaut_smash(state)
    for dest, _ in smash_moves:
        if dest == r1_pos or dest == r2_pos:
            priority = 1000.0  # Immediate smash tag!
        else:
            d = min(manhattan_distance(dest, r1_pos), manhattan_distance(dest, r2_pos))
            curr_d = min(manhattan_distance(state.p_ai, r1_pos), manhattan_distance(state.p_ai, r2_pos))
            priority = 110.0 - d if d < curr_d else 80.0 - d
        actions.append((priority, ("SMASH", dest)))

    # --- 3. Candidate WALL Actions (Filtered) ---
    if max_walls > 0:
        candidate_walls: List[Tuple[float, Action]] = []
        g = state.grid_size
        focus_targets = [r1_pos, r2_pos]
        tested_walls = set()
        
        for tx, ty in focus_targets:
            x_min = max(0, tx - wall_radius)
            x_max = min(g - 2, tx + wall_radius)
            y_min = max(0, ty - wall_radius)
            y_max = min(g - 2, ty + wall_radius)
            
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    for orient in ("H", "V"):
                        wall_key = (orient, x, y)
                        if wall_key in tested_walls:
                            continue
                        tested_walls.add(wall_key)
                        
                        if is_valid_2tile_wall(state, orient, x, y):
                            dist_to_runner = min(
                                abs(x - tx) + abs(y - ty) for tx, ty in focus_targets
                            )
                            score = 50.0 - dist_to_runner
                            candidate_walls.append((score, ("WALL", wall_key)))
                            
        candidate_walls.sort(key=lambda item: item[0], reverse=True)
        actions.extend(candidate_walls[:max_walls])

    # Sort all actions by priority descending (Move Ordering for max pruning)
    actions.sort(key=lambda item: item[0], reverse=True)
    return [act for _, act in actions]


def get_candidate_actions_runners(
    state: GameState,
    max_combinations: int = 8
) -> List[Action]:
    """
    Candidate Move Filtering for Team Runners (Node MIN).
    
    Generates joint moves for both runners: ('TEAM_DUAL', (act_r1, act_r2))
    Each runner considers:
    1. Orthogonal MOVE (away from AI Boss, toward closest active orb)
    2. ROPE jump (escape wall if AI Boss is close)
    3. WALL placement (defensive wall or Co-op Wall Welding)
    
    Combinations are scored and capped at max_combinations to prevent
    combinatorial explosion.
    """
    ai_pos = state.p_ai
    
    def get_individual_moves(r_idx: int) -> List[Tuple[float, Action]]:
        r_pos = state.p_runners[r_idx]
        moves: List[Tuple[float, Action]] = []
        
        # 1. Normal Steps
        valid_steps = get_valid_steps(state, r_pos)
        for step in valid_steps:
            dist_ai = manhattan_distance(step, ai_pos)
            min_orb_dist = min([manhattan_distance(step, o) for o in state.orbs]) if state.orbs else 10
            score = (dist_ai * 3.0) - (min_orb_dist * 2.0)
            moves.append((score, ("MOVE", step)))
            
        # 2. Rope Jump
        if state.runner_ropes[r_idx] > 0:
            jump_moves = can_wall_jump(state, r_idx)
            for dest, _ in jump_moves:
                dist_ai = manhattan_distance(dest, ai_pos)
                curr_dist = manhattan_distance(r_pos, ai_pos)
                if dist_ai > curr_dist:
                    min_orb_dist = min([manhattan_distance(dest, o) for o in state.orbs]) if state.orbs else 10
                    score = (dist_ai * 4.0) - (min_orb_dist * 2.0) + 10.0
                    moves.append((score, ("ROPE", dest)))
                    
        # 3. Defensive Wall
        cx, cy = (r_pos[0] + ai_pos[0]) // 2, (r_pos[1] + ai_pos[1]) // 2
        for orient in ("H", "V"):
            wx = max(0, min(state.grid_size - 2, cx))
            wy = max(0, min(state.grid_size - 2, cy))
            if is_valid_2tile_wall(state, orient, wx, wy):
                moves.append((5.0, ("WALL", (orient, wx, wy))))

        moves.sort(key=lambda m: m[0], reverse=True)
        return moves[:4]

    moves_r1 = get_individual_moves(0)
    moves_r2 = get_individual_moves(1)

    dual_actions: List[Tuple[float, Action]] = []
    for score1, act1 in moves_r1:
        for score2, act2 in moves_r2:
            combined_score = score1 + score2
            if act1[0] == "WALL" and act2[0] == "WALL" and act1[1] == act2[1]:
                combined_score += 30.0  # Co-op welding makes wall permanent!
            
            dual_actions.append((combined_score, ("TEAM_DUAL", (act1, act2))))

    dual_actions.sort(key=lambda a: a[0], reverse=True)
    return [act for _, act in dual_actions[:max_combinations]]


class SearchMetrics:
    """Telemetry and diagnostics for adversarial tree search."""
    def __init__(self):
        self.nodes_explored = 0
        self.cutoffs = 0
        self.max_depth_reached = 0
        self.execution_time_ms = 0.0
        self.mode = "ALPHA_BETA"

    def reset(self, mode: str = "ALPHA_BETA"):
        self.nodes_explored = 0
        self.cutoffs = 0
        self.max_depth_reached = 0
        self.execution_time_ms = 0.0
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "nodes_explored": self.nodes_explored,
            "cutoffs": self.cutoffs,
            "max_depth_reached": self.max_depth_reached,
            "execution_time_ms": round(self.execution_time_ms, 2)
        }


class MinimaxAgent:
    """
    Minimax Adversarial Agent with Alpha-Beta Pruning Toggle.
    PIC: Deus, Althaf (Task 2.1)
    
    Modes:
    - use_alpha_beta = True  -> Alpha-Beta Pruning (Optimal & fast)
    - use_alpha_beta = False -> Pure Minimax (Exhaustive search baseline)
    """

    def __init__(
        self,
        depth_limit: int = 2,
        use_alpha_beta: bool = True,
        use_candidate_filtering: bool = True,
        eval_fn: Optional[Callable[[GameState], float]] = None
    ):
        self.depth_limit = depth_limit
        self.use_alpha_beta = use_alpha_beta
        self.use_candidate_filtering = use_candidate_filtering
        # Default to Task 2.2 Heuristic (evaluate_state)
        self.eval_fn = eval_fn if eval_fn is not None else evaluate_state
        self.metrics = SearchMetrics()

    # --- Mode Toggle Controls ---
    def set_alpha_beta_mode(self, enabled: bool) -> None:
        """Explicitly switch Alpha-Beta Pruning ON (True) or OFF (False)."""
        self.use_alpha_beta = bool(enabled)

    def toggle_alpha_beta(self) -> bool:
        """Toggle Alpha-Beta Pruning mode. Returns new state (True=ON, False=OFF)."""
        self.use_alpha_beta = not self.use_alpha_beta
        return self.use_alpha_beta

    @property
    def mode_name(self) -> str:
        """Return human-readable mode name."""
        return "Alpha-Beta Pruning" if self.use_alpha_beta else "Pure Minimax"

    # --- Search Execution ---
    def choose_action(
        self,
        state: GameState,
        depth: Optional[int] = None
    ) -> Tuple[Optional[Action], float]:
        """
        Main decision-making function for AI Boss.
        Returns (best_action, best_evaluation_score).
        """
        search_depth = depth if depth is not None else self.depth_limit
        mode_str = "ALPHA_BETA" if self.use_alpha_beta else "PURE_MINIMAX"
        self.metrics.reset(mode=mode_str)
        t_start = time.perf_counter()

        if self.use_alpha_beta:
            best_action, best_val = self._minimax_alpha_beta_root(state, search_depth)
        else:
            best_action, best_val = self._minimax_pure_root(state, search_depth)

        self.metrics.execution_time_ms = (time.perf_counter() - t_start) * 1000.0
        return best_action, best_val

    # =========================================================================
    # Mode 1: Pure Minimax (Without Pruning)
    # =========================================================================

    def _minimax_pure_root(self, state: GameState, depth: int) -> Tuple[Optional[Action], float]:
        self.metrics.nodes_explored += 1
        actions = self._get_actions(state, is_max=True)
        if not actions or depth == 0 or state.is_terminal():
            return None, self.eval_fn(state)

        best_action: Optional[Action] = None
        best_val = -math.inf

        for action in actions:
            succ = apply_action(state, action, is_max=True)
            val = self._minimax_pure(succ, depth - 1, is_max=False)
            if val > best_val:
                best_val = val
                best_action = action

        return best_action, best_val

    def _minimax_pure(self, state: GameState, depth: int, is_max: bool) -> float:
        self.metrics.nodes_explored += 1
        if depth == 0 or state.is_terminal():
            return self.eval_fn(state)

        if is_max:
            max_val = -math.inf
            for action in self._get_actions(state, is_max=True):
                succ = apply_action(state, action, is_max=True)
                val = self._minimax_pure(succ, depth - 1, is_max=False)
                if val > max_val:
                    max_val = val
            return max_val
        else:
            min_val = math.inf
            for action in self._get_actions(state, is_max=False):
                succ = apply_action(state, action, is_max=False)
                val = self._minimax_pure(succ, depth - 1, is_max=True)
                if val < min_val:
                    min_val = val
            return min_val

    # =========================================================================
    # Mode 2: Alpha-Beta Pruning Minimax
    # =========================================================================

    def _minimax_alpha_beta_root(
        self,
        state: GameState,
        depth: int
    ) -> Tuple[Optional[Action], float]:
        self.metrics.nodes_explored += 1
        actions = self._get_actions(state, is_max=True)
        if not actions or depth == 0 or state.is_terminal():
            return None, self.eval_fn(state)

        best_action: Optional[Action] = None
        alpha = -math.inf
        beta = math.inf

        for action in actions:
            succ = apply_action(state, action, is_max=True)
            val = self._alpha_beta(succ, depth - 1, alpha, beta, is_max=False)
            if val > alpha:
                alpha = val
                best_action = action

        return best_action, alpha

    def _alpha_beta(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        is_max: bool
    ) -> float:
        self.metrics.nodes_explored += 1
        if depth == 0 or state.is_terminal():
            return self.eval_fn(state)

        if is_max:
            value = -math.inf
            for action in self._get_actions(state, is_max=True):
                succ = apply_action(state, action, is_max=True)
                value = max(value, self._alpha_beta(succ, depth - 1, alpha, beta, is_max=False))
                alpha = max(alpha, value)
                if alpha >= beta:
                    self.metrics.cutoffs += 1
                    break  # Beta cutoff
            return value
        else:
            value = math.inf
            for action in self._get_actions(state, is_max=False):
                succ = apply_action(state, action, is_max=False)
                value = min(value, self._alpha_beta(succ, depth - 1, alpha, beta, is_max=True))
                beta = min(beta, value)
                if beta <= alpha:
                    self.metrics.cutoffs += 1
                    break  # Alpha cutoff
            return value

    # =========================================================================
    # Action Generation & Candidate Filtering
    # =========================================================================

    def _get_actions(self, state: GameState, is_max: bool) -> List[Action]:
        """Generate candidate actions according to configuration."""
        if is_max:
            if self.use_candidate_filtering:
                return get_candidate_actions_ai(state, max_walls=4, wall_radius=2)
            else:
                acts: List[Action] = []
                for s in get_valid_steps(state, state.p_ai):
                    acts.append(("MOVE", s))
                for d, _ in can_juggernaut_smash(state):
                    acts.append(("SMASH", d))
                return acts
        else:
            if self.use_candidate_filtering:
                return get_candidate_actions_runners(state, max_combinations=8)
            else:
                acts = []
                for s1 in get_valid_steps(state, state.p_runners[0]):
                    for s2 in get_valid_steps(state, state.p_runners[1]):
                        acts.append(("TEAM_DUAL", (("MOVE", s1), ("MOVE", s2))))
                return acts if acts else [("MOVE", state.p_runners[0])]
