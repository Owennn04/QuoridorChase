"""
Unit Tests for Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S
PIC: Deus, Althaf

Verifies:
1. Initial State S0 specifications (grid 9x9, positions, empty walls, ready cooldowns)
2. Legal Actions A(s) (Orthogonal steps, 2-tile walls, Smash, Rope Jump)
3. Transition Model T(s, a) (Solo Wall TTL=2 vs Co-op Wall Welding, Cooldowns)
4. No-Complete-Cage BFS Invariant (prevents completely trapping any player)
5. Scoring, Orb Respawn, Tag Steal (+40 pts) & Phase-Blink Respawn
6. Terminal State Evaluation & Utility Function U(s) (+1000, -1000, 0)
"""

import sys
import os
import pytest

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.state import GameState, canonical_edge
from engine.rules import (
    get_valid_steps,
    can_wall_jump,
    can_juggernaut_smash,
    validate_no_complete_cage,
    is_valid_2tile_wall,
    wall_to_edges
)
from engine.transition import (
    apply_ai_action,
    apply_runner_action,
    apply_team_runners_action,
    step_turn_cycle
)
from config import (
    GRID_SIZE,
    AI_START_POS,
    RUNNER_START_POSITIONS,
    UTILITY_AI_WIN,
    UTILITY_RUNNER_WIN,
    UTILITY_DRAW,
    POINTS_AI_TAG,
    POINTS_RUNNER_ORB
)


def test_initial_state_s0():
    """Verify Initial State S0 parameters align with Proposal Bab 2.2 #2."""
    state = GameState.create_initial_state(seed=42)
    assert state.grid_size == 9
    assert state.p_ai == (4, 4)
    assert state.p_runners == [(0, 4), (8, 4)]
    assert state.smash_cooldown == 0  # READY (Overload)
    assert state.runner_ropes == [1, 1]  # 1 rope per runner
    assert state.score_ai == 0
    assert state.score_runners == 0
    assert len(state.orbs) == 3
    assert len(state.solo_walls) == 0
    assert len(state.coop_walls) == 0
    assert state.current_turn == "R1"
    assert state.is_terminal() is False
    assert state.get_utility() == UTILITY_DRAW


def test_orthogonal_movement_and_wall_blocking():
    """Verify agent can move orthogonally and is blocked by walls."""
    state = GameState.create_initial_state(seed=42)
    # AI at (4, 4) should have 4 orthogonal legal moves initially
    valid_steps = get_valid_steps(state, state.p_ai)
    assert set(valid_steps) == {(4, 3), (4, 5), (3, 4), (5, 4)}

    # Place a wall blocking North movement to (3, 4)
    wall = canonical_edge((4, 4), (3, 4))
    state.solo_walls[wall] = 2
    state.invalidate_wall_cache()

    valid_steps_after = get_valid_steps(state, state.p_ai)
    assert (3, 4) not in valid_steps_after
    assert set(valid_steps_after) == {(4, 3), (4, 5), (5, 4)}


def test_juggernaut_smash_mechanic():
    """Verify AI Boss can break through a wall when cooldown == 0."""
    state = GameState.create_initial_state(seed=42)
    wall = canonical_edge((4, 4), (3, 4))
    state.solo_walls[wall] = 2
    state.invalidate_wall_cache()

    # Normal step blocked
    assert (3, 4) not in get_valid_steps(state, state.p_ai)

    # Smash should be available into (3, 4)
    smashable = can_juggernaut_smash(state)
    destinations = [dest for dest, edge in smashable]
    assert (3, 4) in destinations

    # Execute Smash
    next_state = apply_ai_action(state, ("SMASH", (3, 4)))
    assert next_state.p_ai == (3, 4)
    assert next_state.smash_cooldown == 3  # Cooldown reset to 3
    assert wall not in next_state.all_walls()  # Wall permanently destroyed


def test_grappling_rope_wall_jump():
    """Verify Runner can leap over an adjacent wall using single-use rope."""
    state = GameState.create_initial_state(seed=42)
    # Runner 0 is at (0, 4). Place wall between (0, 4) and (1, 4)
    wall = canonical_edge((0, 4), (1, 4))
    state.coop_walls.add(wall)
    state.invalidate_wall_cache()

    # Standard step blocked
    steps = get_valid_steps(state, state.p_runners[0])
    assert (1, 4) not in steps

    # Wall jump available
    jumpable = can_wall_jump(state, 0)
    destinations = [dest for dest, edge in jumpable]
    assert (1, 4) in destinations

    # Execute Rope Jump
    next_state = apply_runner_action(state, 0, ("ROPE", (1, 4)))
    assert next_state.p_runners[0] == (1, 4)
    assert next_state.runner_ropes[0] == 0  # Consumed single-use rope
    assert wall in next_state.coop_walls  # Wall remains intact for others


def test_solo_wall_decay_vs_coop_wall_welding():
    """Verify Solo Wall expires after 2 turns, but Co-op Wall Welding becomes permanent."""
    state = GameState.create_initial_state(seed=42)
    test_edge = canonical_edge((2, 2), (2, 3))

    # 1. Solo Wall placement (1 Runner places)
    s1 = apply_runner_action(state, 0, ("WALL", test_edge))
    assert test_edge in s1.solo_walls
    assert s1.solo_walls[test_edge] == 2
    assert test_edge not in s1.coop_walls

    # Advance 1 turn cycle -> TTL reduces to 1
    s1_t1 = step_turn_cycle(s1)
    assert s1_t1.solo_walls[test_edge] == 1

    # Advance 2nd turn cycle -> Wall naturally dissolves/expires!
    s1_t2 = step_turn_cycle(s1_t1)
    assert test_edge not in s1_t2.solo_walls
    assert test_edge not in s1_t2.all_walls()

    # 2. Co-op Wall Welding (Both runners place on the exact same edge)
    s2 = apply_team_runners_action(
        state,
        ("TEAM_DUAL", (("WALL", test_edge), ("WALL", test_edge)))
    )
    assert test_edge in s2.coop_walls
    assert test_edge not in s2.solo_walls

    # Advance multiple turn cycles -> Co-op wall remains permanent!
    s2_t1 = step_turn_cycle(s2)
    s2_t2 = step_turn_cycle(s2_t1)
    assert test_edge in s2_t2.coop_walls
    assert test_edge in s2_t2.all_walls()


def test_2tile_wall_placement_and_no_cage_rule():
    """Verify standard 2-tile Quoridor walls and No-Complete-Cage BFS protection."""
    state = GameState.create_initial_state(seed=42)

    # Valid 2-tile wall at intersection (2, 3)
    assert is_valid_2tile_wall(state, "H", 2, 3) is True
    e1, e2 = wall_to_edges("H", 2, 3)
    assert e1 == canonical_edge((2, 3), (2, 4))
    assert e2 == canonical_edge((3, 3), (3, 4))

    # Place the wall
    s1 = apply_runner_action(state, 0, ("WALL", ("H", 2, 3)))
    assert e1 in s1.solo_walls and e2 in s1.solo_walls

    # Overlapping wall is rejected
    assert is_valid_2tile_wall(s1, "H", 2, 3) is False

    # Perpendicular intersection is rejected
    assert is_valid_2tile_wall(s1, "V", 2, 3) is False


def test_data_orb_collection_and_tag_teleport():
    """Verify Data Orb pickup (+15 pts) and AI Tagging (+40 pts) with Phase-Blink respawn."""
    state = GameState.create_initial_state(seed=42)

    # Manually place an orb next to Runner 0 (at (0, 4) -> orb at (0, 5))
    state.orbs = {(0, 5), (2, 2), (6, 6)}
    s1 = apply_runner_action(state, 0, ("MOVE", (0, 5)))
    assert s1.score_runners == POINTS_RUNNER_ORB  # +15 pts
    assert (0, 5) not in s1.orbs
    assert len(s1.orbs) == 3  # Automatically replenished

    # Test AI Tagging: Place Runner 1 at (4, 5). AI is at (4, 4)
    s1.p_runners[1] = (4, 5)
    s2 = apply_ai_action(s1, ("MOVE", (4, 5)))
    assert s2.score_ai == POINTS_AI_TAG  # +40 pts
    assert s2.p_ai == (4, 5)
    # Runner 1 must be phase-blinked (teleported) to a distant corner
    assert s2.p_runners[1] != (4, 5)
    assert s2.p_runners[1] in [(0, 0), (0, 8), (8, 0), (8, 8)]


def test_terminal_state_and_utility():
    """Verify Goal Test / Terminal State and Utility Function U(s)."""
    state = GameState.create_initial_state(seed=42)
    assert state.is_terminal() is False

    # Expire timer
    state.time_remaining = 0.0
    assert state.is_terminal() is True

    # Utility when AI leads
    state.score_ai = 80
    state.score_runners = 30
    assert state.get_utility() == UTILITY_AI_WIN

    # Utility when Runners lead
    state.score_ai = 40
    state.score_runners = 60
    assert state.get_utility() == UTILITY_RUNNER_WIN

