"""
Quoridor Chase: Lockdown - System Configuration & Hyperparameters
Grup BESAR: Amadeus Ian Gunadi, Christian Owen Tengkawan, Michelle Mercy Phe, Muhammad Althaf Hilmi
Week 1 - Task 1.2: Pemodelan State Space & P.E.A.S
"""

# Board Geometry
GRID_SIZE = 9
MIN_COORD = 0
MAX_COORD = GRID_SIZE - 1

# Initial Agent Positions (S0)
AI_START_POS = (4, 4)
RUNNER_START_POSITIONS = [(0, 4), (8, 4)]
RESPAWN_CANDIDATE_CORNERS = [(0, 0), (0, 8), (8, 0), (8, 8)]

# Game Match & Turn Timers
MATCH_DURATION_SECONDS = 300  # 5 minutes maximum
SHOT_CLOCK_SECONDS = 10.0     # 10s shot clock per decision
MAX_SIMULATION_TURNS = 60     # Safety cutoff for simulation

# Mechanics & Cooldowns
SMASH_COOLDOWN_INITIAL = 0    # 0 = READY (Overload)
SMASH_COOLDOWN_RESET = 3      # 3 turns cooldown after Juggernaut Smash
SOLO_WALL_LIFETIME = 2        # Solo wall expires after 2 turns
INITIAL_RUNNER_ROPES = [1, 1] # 1 rope item per runner
ACTIVE_ORB_TARGET_COUNT = 3   # Always maintain 3 data orbs on board
WALL_SPAN_TILES = 2           # Standard Quoridor wall length: spans 2 tiles

# Scoring Constants
POINTS_AI_TAG = 40
POINTS_RUNNER_ORB = 15

# Heuristic Function Weights (Bab 2.3 Proposal)
# h(s) = w1*JarakRunners + w2*AksesOrb + w3*SkillBonus - w4*SisaRope + w5*Confinement + ScoreDiff
W1_CLOSEST_RUNNER = 32.0
W1_SECOND_RUNNER = 4.0
W2_ORB_ACCESS = 4.0
W3_SKILL_READY_BONUS = 25.0
W3_SKILL_COOLDOWN_PENALTY = -5.0
W4_ROPE_PENALTY = 18.0
W5_CONFINEMENT_SCALE = 35.0
SCORE_DIFF_WEIGHT = 20.0

# Terminal Utility Values U(s)
UTILITY_AI_WIN = 1000.0
UTILITY_RUNNER_WIN = -1000.0
UTILITY_DRAW = 0.0

# UI Design Tokens (Reference: https://ucking.vercel.app/)
THEME_TOKENS = {
    "paper": "#f3efe5",
    "ink": "#18241f",
    "forest": "#18392f",
    "orange": "#ef6b3a",
    "yellow": "#f3bf43",
    "line": "#cfc7b7",
    "white": "#fffdf7",
    "success": "#267354",
    "danger": "#b63d32",
    "blue": "#4a89a8",
    "cyber_bg": "#090d16",
    "cyber_panel": "#111827",
    "cyber_border": "#1e293b",
    "ai_crimson": "#ef4444",
    "runner_cyan": "#06b6d4",
    "runner_sky": "#38bdf8",
    "orb_gold": "#facc15",
}

