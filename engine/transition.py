"""
Transition Model T(s, a) and Turn Cycle for Quoridor Chase: Lockdown.
PIC: Deus, Althaf (Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S)

Handles:
- Deterministic state mutation T(s, a) -> s'
- Co-op Wall Welding (simultaneous runner wall placement -> permanent)
- Solo Wall decay (2 turns duration)
- Grappling Rope consumption & single-use mechanics
- Juggernaut Smash wall obliteration & 3-turn cooldown reset
- Data Orb pickup & replacement spawning
- AI Tagging & Runner Phase-Blink respawn
- Turn alternation and match clock progression
"""

from typing import Tuple, Optional

try:
    from config import (
        SMASH_COOLDOWN_RESET,
        SOLO_WALL_LIFETIME,
        POINTS_AI_TAG,
        POINTS_RUNNER_ORB
    )
except ImportError:
    try:
        from ..config import (
            SMASH_COOLDOWN_RESET,
            SOLO_WALL_LIFETIME,
            POINTS_AI_TAG,
            POINTS_RUNNER_ORB
        )
    except ImportError:
        from quoridor_chase.config import (
            SMASH_COOLDOWN_RESET,
            SOLO_WALL_LIFETIME,
            POINTS_AI_TAG,
            POINTS_RUNNER_ORB
        )

try:
    from engine.state import GameState, Cell, WallEdge, canonical_edge
    from engine.rules import wall_to_edges
except ImportError:
    try:
        from .state import GameState, Cell, WallEdge, canonical_edge
        from .rules import wall_to_edges
    except ImportError:
        from state import GameState, Cell, WallEdge, canonical_edge
        from rules import wall_to_edges

Action = Tuple[str, any]


def apply_ai_action(state: GameState, action: Action) -> GameState:
    """Execute AI Boss action on a cloned state."""
    new_state = state.clone()
    action_type, payload = action

    if action_type == "MOVE":
        dest: Cell = payload
        new_state.p_ai = dest
        # Check Tag on either runner
        for r_idx in range(len(new_state.p_runners)):
            if new_state.p_ai == new_state.p_runners[r_idx]:
                new_state.score_ai += POINTS_AI_TAG
                new_state.respawn_runner(r_idx)

    elif action_type == "SMASH":
        dest: Cell = payload
        edge = canonical_edge(new_state.p_ai, dest)
        # Destroy wall permanently from all wall sets
        if edge in new_state.solo_walls:
            del new_state.solo_walls[edge]
        new_state.coop_walls.discard(edge)

        # Obliterate companion segment if part of a placed 2-tile wall
        for w_key in list(new_state.placed_walls.keys()):
            w_edges = wall_to_edges(w_key[0], w_key[1], w_key[2])
            if edge in w_edges:
                for we in w_edges:
                    if we in new_state.solo_walls:
                        del new_state.solo_walls[we]
                    new_state.coop_walls.discard(we)
                del new_state.placed_walls[w_key]

        new_state.invalidate_wall_cache()

        new_state.p_ai = dest
        new_state.smash_cooldown = SMASH_COOLDOWN_RESET

        # Check Tag on either runner
        for r_idx in range(len(new_state.p_runners)):
            if new_state.p_ai == new_state.p_runners[r_idx]:
                new_state.score_ai += POINTS_AI_TAG
                new_state.respawn_runner(r_idx)

    elif action_type == "WALL":
        # Support 2-tile wall (orient, x, y) or single edge
        if isinstance(payload, (tuple, list)) and len(payload) == 3 and isinstance(payload[0], str):
            edges = wall_to_edges(payload[0], payload[1], payload[2])
            for e in edges:
                new_state.solo_walls[e] = SOLO_WALL_LIFETIME
            new_state.placed_walls[(payload[0], payload[1], payload[2])] = (SOLO_WALL_LIFETIME, "AI")
        else:
            new_state.solo_walls[payload] = SOLO_WALL_LIFETIME
        new_state.invalidate_wall_cache()

    # Pass turn to Runners
    new_state.current_turn = "R1"
    return new_state


def apply_runner_action(
    state: GameState,
    runner_idx: int,
    action: Action,
    coop_partner_wall: Optional[any] = None
) -> GameState:
    """Execute a single runner's action on a cloned state."""
    new_state = state.clone()
    action_type, payload = action

    if action_type == "MOVE":
        dest: Cell = payload
        new_state.p_runners[runner_idx] = dest
        # Check Data Orb collection
        if dest in new_state.orbs:
            new_state.score_runners += POINTS_RUNNER_ORB
            new_state.orbs.remove(dest)
            new_state.spawn_replacement_orb()

    elif action_type == "ROPE":
        dest: Cell = payload
        if new_state.runner_ropes[runner_idx] > 0:
            new_state.runner_ropes[runner_idx] -= 1
            new_state.p_runners[runner_idx] = dest
            # Check Data Orb collection
            if dest in new_state.orbs:
                new_state.score_runners += POINTS_RUNNER_ORB
                new_state.orbs.remove(dest)
                new_state.spawn_replacement_orb()

    elif action_type == "WALL":
        # Support 2-tile wall (orient, x, y) or single edge
        if isinstance(payload, (tuple, list)) and len(payload) == 3 and isinstance(payload[0], str):
            edges = list(wall_to_edges(payload[0], payload[1], payload[2]))
            w_key = (payload[0], payload[1], payload[2])
        else:
            edges = [payload]
            w_key = None

        is_welded = (coop_partner_wall is not None and coop_partner_wall == payload)
        for e in edges:
            if is_welded:
                if e in new_state.solo_walls:
                    del new_state.solo_walls[e]
                new_state.coop_walls.add(e)
            else:
                new_state.solo_walls[e] = SOLO_WALL_LIFETIME

        if w_key is not None:
            new_state.placed_walls[w_key] = (-1, "COOP") if is_welded else (SOLO_WALL_LIFETIME, "RUNNER")

        new_state.invalidate_wall_cache()

    return new_state


def apply_team_runners_action(state: GameState, action: Action) -> GameState:
    """
    Execute Team Runners collective action in adversarial search.
    Action format: (('MOVE', c1), ('MOVE', c2)) or ('TEAM_DUAL', (act_r1, act_r2))
    """
    new_state = state.clone()
    action_type = action[0]

    if action_type == "TEAM_DUAL":
        _, (act_r1, act_r2) = action
        wall1 = act_r1[1] if act_r1[0] == "WALL" else None
        wall2 = act_r2[1] if act_r2[0] == "WALL" else None

        # Apply Runner 1
        new_state = apply_runner_action(new_state, 0, act_r1, coop_partner_wall=wall2)
        # Apply Runner 2
        new_state = apply_runner_action(new_state, 1, act_r2, coop_partner_wall=wall1)

    elif action_type in ("MOVE", "ROPE", "WALL"):
        # Single representative runner action
        new_state = apply_runner_action(new_state, 0, action)

    # Maintenance after full round
    new_state = step_turn_cycle(new_state)
    new_state.current_turn = "AI"
    return new_state


def apply_action(state: GameState, action: Action, is_max: Optional[bool] = None) -> GameState:
    """
    Universal Transition Model T(s, a).
    If is_max is True (or current_turn == 'AI'), executes AI Boss action.
    Else executes Runners team action.
    """
    if is_max is True or (is_max is None and state.current_turn == "AI"):
        return apply_ai_action(state, action)
    else:
        return apply_team_runners_action(state, action)


def step_turn_cycle(state: GameState, elapsed_seconds: float = 0.0) -> GameState:
    """Handle end-of-round maintenance, wall decays, timers and status updates."""
    state.turn_count += 1

    # Solo walls decay by 1 turn
    expired = []
    for edge, ttl in list(state.solo_walls.items()):
        if ttl <= 1:
            expired.append(edge)
        else:
            state.solo_walls[edge] = ttl - 1
    for edge in expired:
        del state.solo_walls[edge]
    if expired:
        state.invalidate_wall_cache()

    # Decay placed_walls duration
    expired_pw = []
    for w, val in list(state.placed_walls.items()):
        ttl = val[0] if isinstance(val, (tuple, list)) else val
        owner = val[1] if isinstance(val, (tuple, list)) else "RUNNER"
        if ttl > 0:
            if ttl <= 1:
                expired_pw.append(w)
            else:
                state.placed_walls[w] = (ttl - 1, owner)
    for w in expired_pw:
        del state.placed_walls[w]

    # AI Boss turn starting: cooldown decay
    if state.smash_cooldown > 0:
        state.smash_cooldown -= 1

    # Decrement match time by actual elapsed time
    if elapsed_seconds > 0.0:
        state.time_remaining = max(0.0, state.time_remaining - elapsed_seconds)
    if state.time_remaining <= 0 or state.turn_count >= state.grid_size * 10:
        state.is_game_over = True
        if state.score_ai > state.score_runners:
            state.winner = "AI Boss"
        elif state.score_runners > state.score_ai:
            state.winner = "Runners"
        else:
            state.winner = "Draw"
    return state

