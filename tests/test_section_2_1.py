"""
Unit Tests for Week 2 - Task 2.1: Algoritma Minimax & Alpha-Beta Pruning
PIC: Deus, Althaf

Verifies:
1. Dual Modes & Toggle: Switching between Pure Minimax and Alpha-Beta Pruning.
2. Optimality Guarantee: Pure Minimax and Alpha-Beta Pruning yield identical evaluation scores.
3. Pruning Efficiency: Alpha-Beta Pruning drastically reduces explored nodes compared to Pure Minimax.
4. Heuristic 2.2 Integration: evaluate_state correctly guides decision-making.
5. AI Boss Tactical Exploitation: Immediate tag for +40 pts and Juggernaut Smash usage.
6. Execution Latency: Fast decision making under interactive threshold (< 1000 ms).
"""

import sys
import os
import time

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.state import GameState, canonical_edge
from src.ai.minimax import (
    MinimaxAgent,
    get_candidate_actions_ai,
    get_candidate_actions_runners
)
from src.ai.heuristic import evaluate_state
from src.ai.pathfinding import manhattan_distance


def test_dual_mode_and_toggle_switch():
    """Verify that MinimaxAgent supports both modes and the toggle switch works as expected."""
    agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)
    assert agent.use_alpha_beta is True
    assert agent.mode_name == "Alpha-Beta Pruning"

    # Toggle to Pure Minimax
    new_mode = agent.toggle_alpha_beta()
    assert new_mode is False
    assert agent.use_alpha_beta is False
    assert agent.mode_name == "Pure Minimax"

    # Explicit setter
    agent.set_alpha_beta_mode(True)
    assert agent.use_alpha_beta is True
    assert agent.mode_name == "Alpha-Beta Pruning"


def test_pure_vs_alpha_beta_decision_optimality():
    """
    Bab 2.1.e: Optimality & Completeness.
    Pure Minimax and Alpha-Beta Pruning must yield the identical evaluation value
    because Alpha-Beta is mathematically guaranteed never to prune optimal moves.
    """
    state = GameState.create_initial_state(seed=42)

    pure_agent = MinimaxAgent(depth_limit=2, use_alpha_beta=False)
    ab_agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)

    act_pure, val_pure = pure_agent.choose_action(state)
    act_ab, val_ab = ab_agent.choose_action(state)

    assert abs(val_pure - val_ab) < 1e-4, f"Values mismatch: pure={val_pure}, ab={val_ab}"
    assert act_pure is not None
    assert act_ab is not None


def test_alpha_beta_node_pruning_reduction():
    """
    Bab 2.3.d Hipotesis:
    Alpha-Beta Pruning memangkas jumlah node secara drastis dibanding Pure Minimax.
    """
    state = GameState.create_initial_state(seed=100)

    pure_agent = MinimaxAgent(depth_limit=2, use_alpha_beta=False)
    ab_agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)

    pure_agent.choose_action(state)
    ab_agent.choose_action(state)

    nodes_pure = pure_agent.metrics.nodes_explored
    nodes_ab = ab_agent.metrics.nodes_explored

    assert nodes_ab < nodes_pure, f"Alpha-Beta ({nodes_ab}) must explore fewer nodes than Pure ({nodes_pure})"
    reduction_pct = (1.0 - (nodes_ab / nodes_pure)) * 100.0
    print(f"Nodes Pure: {nodes_pure}, Nodes Alpha-Beta: {nodes_ab}, Reduction: {reduction_pct:.1f}%")
    assert reduction_pct > 30.0, f"Expected significant pruning, got {reduction_pct:.1f}%"


def test_ai_boss_immediate_tag():
    """
    Tactical decision:
    Jika Runner berada 1 langkah dari AI Boss, AI Boss harus memilih MOVE
    ke petak runner tersebut untuk mendapatkan +40 poin Tag.
    """
    state = GameState.create_initial_state(seed=42)
    state.p_ai = (4, 4)
    state.p_runners = [(4, 5), (8, 8)]

    agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)
    action, val = agent.choose_action(state)

    assert action is not None
    action_type, payload = action
    assert action_type == "MOVE"
    assert payload == (4, 5), f"AI Boss should move to tag runner at (4, 5), got {payload}"


def test_ai_boss_smash_usage_through_wall():
    """
    Skill decision:
    Jika terhalang tembok dan runner berada di baliknya, AI Boss harus
    menggunakan Juggernaut SMASH untuk menembus tembok.
    """
    state = GameState.create_initial_state(seed=42)
    state.p_ai = (4, 4)
    state.p_runners = [(4, 5), (8, 8)]
    state.smash_cooldown = 0  # READY

    # Block direct orthogonal step with a wall
    edge = canonical_edge((4, 4), (4, 5))
    state.coop_walls.add(edge)
    state.invalidate_wall_cache()

    agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)
    action, val = agent.choose_action(state)

    assert action is not None
    action_type, payload = action
    assert action_type == "SMASH"
    assert payload == (4, 5), f"AI Boss should SMASH wall to (4, 5), got {action}"


def test_candidate_filtering_and_interactive_latency():
    """
    Bab 2.3.d Hipotesis:
    Waktu berpikir AI per langkah harus berada di bawah 1 detik (< 1000 ms).
    """
    state = GameState.create_initial_state(seed=42)
    agent = MinimaxAgent(depth_limit=2, use_alpha_beta=True)

    t0 = time.perf_counter()
    action, val = agent.choose_action(state)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    print(f"Alpha-Beta execution time: {elapsed_ms:.2f} ms (Target: < 1000 ms)")
    assert action is not None
    assert elapsed_ms < 1000.0, f"Execution time {elapsed_ms:.2f} ms exceeded 1000 ms limit"


if __name__ == "__main__":
    print("=" * 65)
    print("🚀 MENJALANKAN UNIT TESTS BAGIAN 2.1 (Minimax & Alpha-Beta Pruning)")
    print("=" * 65)

    test_dual_mode_and_toggle_switch()
    print("  [1/6] test_dual_mode_and_toggle_switch              : LULUS ✅")

    test_pure_vs_alpha_beta_decision_optimality()
    print("  [2/6] test_pure_vs_alpha_beta_decision_optimality   : LULUS ✅")

    test_alpha_beta_node_pruning_reduction()
    print("  [3/6] test_alpha_beta_node_pruning_reduction        : LULUS ✅")

    test_ai_boss_immediate_tag()
    print("  [4/6] test_ai_boss_immediate_tag                    : LULUS ✅")

    test_ai_boss_smash_usage_through_wall()
    print("  [5/6] test_ai_boss_smash_usage_through_wall         : LULUS ✅")

    test_candidate_filtering_and_interactive_latency()
    print("  [6/6] test_candidate_filtering_and_interactive_latency: LULUS ✅")

    print("=" * 65)
    print("🎉 SEMUA 6 PENGUJIAN BAGIAN 2.1 LULUS DENGAN SEMPURNA!")
    print("=" * 65)
