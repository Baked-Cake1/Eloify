"""Extended features for Eloify:
- Light/Dark themes and accent color presets
- Board skins (premade + custom RGB creator) and piece visual styles
- 300–4010 Elo scale bar with pointer arrow
- Per-game & aggregate Move-Quality Elo (ACPL & Accuracy %)
- Non-blocking low-resource LiveEvalWorker & stronger ReplayEvalWorker
- Cross-platform Engine Data Tracking (CPU %, Memory MB, Threads, NPS)
- Tournament ETA estimation & formatting
"""
import math
import os
import sys
import threading
import time
from collections import deque

import chess
import chess.engine
import pygame

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
ELO_SCALE_MIN = 300
ELO_SCALE_MAX = 4010
CHESS_CLOCK_SECONDS = 30.0

# ----------------------------------------------------------------------
# THEMES (DARK / LIGHT) & ACCENTS
# ----------------------------------------------------------------------
ACCENT_PRESETS = {
    "emerald": {
        "label": "Emerald",
        "dark":  (100, 200, 160),
        "light": (22, 148, 104),
    },
    "ocean": {
        "label": "Ocean Blue",
        "dark":  (88, 166, 255),
        "light": (28, 108, 214),
    },
    "purple": {
        "label": "Royal Purple",
        "dark":  (172, 124, 255),
        "light": (116, 60, 210),
    },
    "crimson": {
        "label": "Crimson Coral",
        "dark":  (245, 108, 116),
        "light": (206, 48, 64),
    },
    "amber": {
        "label": "Amber Gold",
        "dark":  (245, 186, 66),
        "light": (196, 122, 12),
    },
    "cyan": {
        "label": "Cyan Teal",
        "dark":  (66, 210, 226),
        "light": (12, 142, 164),
    },
}

ACCENT_ORDER = ("emerald", "ocean", "purple", "crimson", "amber", "cyan")


def get_theme_palette(mode="dark", accent_key="emerald"):
    """Return a complete UI color dictionary for ('dark'|'light', accent_key)."""
    mode = "light" if str(mode).lower() == "light" else "dark"
    preset = ACCENT_PRESETS.get(accent_key, ACCENT_PRESETS["emerald"])
    accent = preset["light"] if mode == "light" else preset["dark"]

    if mode == "light":
        return {
            "mode":           "light",
            "accent_key":     accent_key if accent_key in ACCENT_PRESETS else "emerald",
            "BACKGROUND":     (238, 242, 248),
            "PANEL":          (255, 255, 255),
            "PANEL_HOVER":    (228, 234, 244),
            "BORDER":         (196, 204, 218),
            "TEXT_COLOR":     (24, 30, 42),
            "DIM_TEXT":       (96, 106, 124),
            "ACCENT":         accent,
            "GOLD":           (196, 132, 14),
            "ERROR_COLOR":    (205, 52, 62),
            "WIN_COLOR":      (26, 150, 72),
            "LOSS_COLOR":     (205, 58, 66),
            "DRAW_COLOR":     (105, 114, 130),
            "SELECTION_BG":   tuple(max(0, min(255, int(c * 0.35 + 165))) for c in accent),
            "FIELD_BG":       (246, 248, 252),
            "FIELD_BORDER":   (180, 190, 206),
            "LIST_BG":        (244, 247, 252),
            "LIST_ROW_HOVER": (228, 235, 246),
            "LIST_ROW_SEL":   tuple(max(0, min(255, int(c * 0.25 + 190))) for c in accent),
        }

    return {
        "mode":           "dark",
        "accent_key":     accent_key if accent_key in ACCENT_PRESETS else "emerald",
        "BACKGROUND":     (22, 24, 30),
        "PANEL":          (34, 38, 48),
        "PANEL_HOVER":    (46, 52, 66),
        "BORDER":         (60, 66, 80),
        "TEXT_COLOR":     (225, 228, 235),
        "DIM_TEXT":       (140, 148, 165),
        "ACCENT":         accent,
        "GOLD":           (255, 210, 90),
        "ERROR_COLOR":    (230, 110, 110),
        "WIN_COLOR":      (120, 210, 130),
        "LOSS_COLOR":     (230, 110, 110),
        "DRAW_COLOR":     (180, 185, 195),
        "SELECTION_BG":   (55, 95, 135),
        "FIELD_BG":       (20, 24, 30),
        "FIELD_BORDER":   (70, 76, 90),
        "LIST_BG":        (26, 30, 38),
        "LIST_ROW_HOVER": (40, 46, 56),
        "LIST_ROW_SEL":   tuple(max(24, int(c * 0.42)) for c in accent),
    }


# ----------------------------------------------------------------------
# BOARD SKINS & CUSTOM BOARD COLORS
# ----------------------------------------------------------------------
BOARD_SKINS = {
    "classic_wood":     ("Classic Wood",     (238, 216, 183), (171, 122, 89)),
    "tournament_green": ("Tournament Green", (235, 236, 208), (115, 149, 82)),
    "ocean_ice":        ("Ocean Ice",        (222, 235, 247), (112, 150, 188)),
    "slate":            ("Slate",            (208, 214, 224), (98, 110, 128)),
    "walnut":           ("Walnut & Ivory",   (245, 233, 210), (132, 86, 60)),
    "amethyst":         ("Amethyst",         (234, 224, 245), (132, 98, 170)),
    "custom":           ("Custom",           (238, 216, 183), (171, 122, 89)),
}

BOARD_SKIN_ORDER = (
    "classic_wood",
    "tournament_green",
    "ocean_ice",
    "slate",
    "walnut",
    "amethyst",
    "custom",
)


def _clamp_rgb(rgb):
    return (
        max(0, min(255, int(rgb[0]))),
        max(0, min(255, int(rgb[1]))),
        max(0, min(255, int(rgb[2]))),
    )


def resolve_board_colors(skin_key="classic_wood", custom_light=(238, 216, 183),
                         custom_dark=(171, 122, 89)):
    if skin_key == "custom" or skin_key not in BOARD_SKINS:
        return _clamp_rgb(custom_light), _clamp_rgb(custom_dark)
    _, light, dark = BOARD_SKINS[skin_key]
    return light, dark


# ----------------------------------------------------------------------
# PIECE STYLES
# ----------------------------------------------------------------------
PIECE_STYLES = {
    "classic_2tone":  "Classic 2-Tone",
    "neo_vector":     "Vector Neo",
    "unicode":        "Unicode Classic",
    "minimal_tokens": "Minimal Tokens",
    "cyber_glow":     "Neon Glow",
}

PIECE_STYLE_ORDER = (
    "classic_2tone",
    "neo_vector",
    "unicode",
    "minimal_tokens",
    "cyber_glow",
)

SOLID_GLYPHS = {
    "P": "♟", "N": "♞", "B": "♝", "R": "♜", "Q": "♛", "K": "♚",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

TRADITIONAL_GLYPHS = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}


def _draw_vector_piece(surf, symbol, size, fill_col, stroke_col, accent_col=None):
    """Draw a crisp geometric chess piece onto `surf` (scaled for `size`)."""
    ptype = symbol.upper()
    cx = size // 2
    s = size / 64.0
    lw = max(2, int(round(2.4 * s)))

    def pt(px, py):
        return (int(round(px * s)), int(round(py * s)))

    # Pedestal base common to all pieces
    base_poly = [pt(14, 56), pt(50, 56), pt(47, 50), pt(17, 50)]
    pygame.draw.polygon(surf, fill_col, base_poly)
    pygame.draw.polygon(surf, stroke_col, base_poly, lw)

    if ptype == "P":
        body = [pt(20, 50), pt(44, 50), pt(38, 34), pt(26, 34)]
        pygame.draw.polygon(surf, fill_col, body)
        pygame.draw.polygon(surf, stroke_col, body, lw)
        collar = pygame.Rect(int(22 * s), int(30 * s), int(20 * s), max(3, int(5 * s)))
        pygame.draw.rect(surf, fill_col, collar, border_radius=max(2, int(2 * s)))
        pygame.draw.rect(surf, stroke_col, collar, lw, border_radius=max(2, int(2 * s)))
        pygame.draw.circle(surf, fill_col, pt(32, 21), max(4, int(9 * s)))
        pygame.draw.circle(surf, stroke_col, pt(32, 21), max(4, int(9 * s)), lw)

    elif ptype == "R":
        pillar = [pt(19, 50), pt(45, 50), pt(42, 26), pt(22, 26)]
        pygame.draw.polygon(surf, fill_col, pillar)
        pygame.draw.polygon(surf, stroke_col, pillar, lw)
        crown = [
            pt(17, 26), pt(47, 26), pt(47, 14), pt(41, 14), pt(41, 19),
            pt(35, 19), pt(35, 14), pt(29, 14), pt(29, 19), pt(23, 19),
            pt(23, 14), pt(17, 14),
        ]
        pygame.draw.polygon(surf, fill_col, crown)
        pygame.draw.polygon(surf, stroke_col, crown, lw)

    elif ptype == "N":
        knight = [
            pt(18, 50), pt(46, 50), pt(44, 34), pt(40, 22),
            pt(35, 12), pt(28, 16), pt(16, 26), pt(18, 32),
            pt(27, 29), pt(23, 40),
        ]
        pygame.draw.polygon(surf, fill_col, knight)
        pygame.draw.polygon(surf, stroke_col, knight, lw)
        pygame.draw.circle(surf, stroke_col, pt(29, 21), max(1, int(2.2 * s)))

    elif ptype == "B":
        body = [pt(19, 50), pt(45, 50), pt(39, 36), pt(25, 36)]
        pygame.draw.polygon(surf, fill_col, body)
        pygame.draw.polygon(surf, stroke_col, body, lw)
        mitre = pygame.Rect(int(21 * s), int(15 * s), int(22 * s), int(24 * s))
        pygame.draw.ellipse(surf, fill_col, mitre)
        pygame.draw.ellipse(surf, stroke_col, mitre, lw)
        pygame.draw.circle(surf, fill_col, pt(32, 12), max(2, int(3.5 * s)))
        pygame.draw.circle(surf, stroke_col, pt(32, 12), max(2, int(3.5 * s)), max(1, lw - 1))
        pygame.draw.line(surf, stroke_col, pt(28, 23), pt(36, 31), lw)

    elif ptype == "Q":
        crown = [
            pt(18, 50), pt(46, 50), pt(51, 20), pt(40, 32),
            pt(32, 16), pt(24, 32), pt(13, 20),
        ]
        pygame.draw.polygon(surf, fill_col, crown)
        pygame.draw.polygon(surf, stroke_col, crown, lw)
        for qx, qy in ((13, 18), (32, 14), (51, 18)):
            pygame.draw.circle(surf, accent_col or fill_col, pt(qx, qy), max(2, int(3.2 * s)))
            pygame.draw.circle(surf, stroke_col, pt(qx, qy), max(2, int(3.2 * s)), max(1, lw - 1))

    elif ptype == "K":
        body = [
            pt(18, 50), pt(46, 50), pt(48, 30), pt(38, 24),
            pt(32, 28), pt(26, 24), pt(16, 30),
        ]
        pygame.draw.polygon(surf, fill_col, body)
        pygame.draw.polygon(surf, stroke_col, body, lw)
        pygame.draw.line(surf, stroke_col, (cx, int(8 * s)), (cx, int(23 * s)), lw + 1)
        pygame.draw.line(surf, stroke_col, pt(26, 14), pt(38, 14), lw + 1)


def render_styled_piece(symbol, size, style="classic_2tone", piece_font_getter=None,
                        text_font_getter=None, accent=(100, 200, 160)):
    """Render a chess piece surface of roughly `size x size` for `style`."""
    is_white = symbol.isupper()
    size = max(16, int(size))

    if style == "minimal_tokens":
        out = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
        c = (size + 4) // 2
        r = size // 2 - 2
        fill = (246, 247, 250) if is_white else (32, 36, 44)
        rim = (40, 46, 58) if is_white else (215, 222, 235)
        txt_col = (24, 28, 38) if is_white else (242, 245, 250)
        pygame.draw.circle(out, (0, 0, 0, 70), (c + 1, c + 2), r)
        pygame.draw.circle(out, fill, (c, c), r)
        pygame.draw.circle(out, rim, (c, c), r, max(2, size // 18))
        pygame.draw.circle(out, accent, (c, c), max(4, r - 4), 1)
        font = (text_font_getter(int(size * 0.50), True)
                if text_font_getter is not None
                else pygame.font.SysFont("Arial", int(size * 0.50), bold=True))
        lbl = font.render(symbol.upper(), True, txt_col)
        out.blit(lbl, lbl.get_rect(center=(c, c)))
        return out

    if style in ("neo_vector", "cyber_glow"):
        ss = size * 2
        hi = pygame.Surface((ss, ss), pygame.SRCALPHA)
        if style == "cyber_glow":
            fill_col = (235, 250, 255) if is_white else (18, 22, 32)
            stroke_col = (24, 40, 56) if is_white else accent
            glow = pygame.Surface((ss, ss), pygame.SRCALPHA)
            glow_col = (*accent, 95) if not is_white else (255, 255, 255, 95)
            _draw_vector_piece(glow, symbol, ss, glow_col, glow_col, accent_col=accent)
            hi.blit(glow, (0, 2))
            _draw_vector_piece(hi, symbol, ss, fill_col, stroke_col, accent_col=accent)
        else:
            fill_col = (248, 246, 240) if is_white else (36, 40, 48)
            stroke_col = (30, 32, 38) if is_white else (225, 230, 238)
            _draw_vector_piece(hi, symbol, ss, fill_col, stroke_col)
        try:
            return pygame.transform.smoothscale(hi, (size, size))
        except Exception:
            return pygame.transform.scale(hi, (size, size))

    font = (piece_font_getter(size)
            if piece_font_getter is not None
            else pygame.font.SysFont("Segoe UI Symbol", size))

    if style == "unicode":
        glyph = TRADITIONAL_GLYPHS[symbol]
        fg = font.render(glyph, True, (15, 15, 18))
        sh = font.render(glyph, True, (240, 240, 240) if not is_white else (55, 55, 55))
        w, h = fg.get_size()
        out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        out.blit(sh, (1, 1))
        out.blit(fg, (0, 0))
        return out

    # Default: "classic_2tone" — solid glyph with crisp 8-way outline so White is
    # bright ivory and Black is deep obsidian on any square color!
    glyph = SOLID_GLYPHS[symbol]
    fill_color = (250, 248, 242) if is_white else (28, 31, 38)
    outline_color = (24, 26, 32) if is_white else (232, 236, 242)
    core = font.render(glyph, True, fill_color)
    if core.get_width() <= 2:
        return render_styled_piece(symbol, size, style="neo_vector", accent=accent)
    rim = font.render(glyph, True, outline_color)
    w, h = core.get_size()
    out = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        out.blit(rim, (2 + ox, 2 + oy))
    out.blit(core, (2, 2))
    return out


# ----------------------------------------------------------------------
# ELO SCALE BAR (300 – 4010) WITH ARROW INDICATOR
# ----------------------------------------------------------------------
def elo_scale_fraction(rating, lo=ELO_SCALE_MIN, hi=ELO_SCALE_MAX):
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (float(rating) - float(lo)) / float(hi - lo)))


def draw_elo_scale_bar(surface, rect, rating, palette, show_endpoints=False, font_getter=None):
    """Draw a 300–4010 Elo scale bar inside `rect` with a pointer arrow at `rating`."""
    frac = elo_scale_fraction(rating)
    bar_h = max(5, min(8, rect.h - 6))
    bar_y = rect.bottom - bar_h
    bar_rect = pygame.Rect(rect.x, bar_y, rect.w, bar_h)

    track_col = (52, 58, 72) if palette.get("mode") == "dark" else (210, 218, 230)
    pygame.draw.rect(surface, track_col, bar_rect, border_radius=bar_h // 2)

    fill_w = max(3, int(round(rect.w * frac)))
    accent = palette.get("ACCENT", (100, 200, 160))
    gold = palette.get("GOLD", (255, 210, 90))
    fill_col = gold if rating >= 3600 else accent
    pygame.draw.rect(
        surface,
        fill_col,
        pygame.Rect(rect.x, bar_y, fill_w, bar_h),
        border_radius=bar_h // 2,
    )

    # Pointer arrow (▼) pointing directly at `arrow_x`
    arrow_x = rect.x + int(round(rect.w * frac))
    arrow_x = max(rect.x + 3, min(rect.right - 3, arrow_x))
    tip_y = bar_y - 1
    top_y = max(rect.y, tip_y - 6)
    half_w = 4
    arrow_col = gold if rating >= 3600 else palette.get("TEXT_COLOR", (230, 232, 240))
    pygame.draw.polygon(
        surface,
        arrow_col,
        [(arrow_x, tip_y), (arrow_x - half_w, top_y), (arrow_x + half_w, top_y)],
    )
    pygame.draw.line(surface, arrow_col, (arrow_x, bar_y), (arrow_x, bar_rect.bottom - 1), 2)

    if show_endpoints and font_getter is not None:
        f = font_getter(10, False)
        dim = palette.get("DIM_TEXT", (140, 148, 165))
        s_lo = f.render(str(ELO_SCALE_MIN), True, dim)
        s_hi = f.render(str(ELO_SCALE_MAX), True, dim)
        surface.blit(s_lo, (rect.x, bar_rect.bottom + 2))
        surface.blit(s_hi, (rect.right - s_hi.get_width(), bar_rect.bottom + 2))


# ----------------------------------------------------------------------
# POSITION EVALUATION & MOVE-QUALITY ELO RATING
# ----------------------------------------------------------------------
_PST_PAWN = (
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
)

_PST_MINOR = (
    -40,-30,-20,-20,-20,-20,-30,-40,
    -30,-10,  0,  5,  5,  0,-10,-30,
    -20,  5, 15, 20, 20, 15,  5,-20,
    -20,  5, 20, 25, 25, 20,  5,-20,
    -20, 10, 20, 25, 25, 20, 10,-20,
    -20,  5, 15, 20, 20, 15,  5,-20,
    -30,-10,  0,  5,  5,  0,-10,-30,
    -40,-30,-20,-20,-20,-20,-30,-40,
)

_PIECE_CP = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   0,
}


def evaluate_board_static_cp(board):
    """Fast static evaluation from White's POV: returns (white_cp, mate_in_white)."""
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return (-10000, -1)
        return (10000, 1)
    if board.is_stalemate() or board.is_insufficient_material():
        return (0, None)

    score = 0
    for sq, piece in board.piece_map().items():
        val = _PIECE_CP.get(piece.piece_type, 0)
        idx = (sq ^ 56) if piece.color == chess.WHITE else sq
        if piece.piece_type == chess.PAWN:
            val += _PST_PAWN[idx]
        elif piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            val += _PST_MINOR[idx]
        if piece.color == chess.WHITE:
            score += val
        else:
            score -= val
    if board.is_check():
        score += -35 if board.turn == chess.WHITE else 35
    return (score, None)


def score_to_white_cp(pov_score):
    """Convert a `chess.engine.PovScore` to `(white_cp, mate_in_white)`."""
    if pov_score is None:
        return (0, None)
    w = pov_score.white()
    mate = w.mate()
    if mate is not None:
        cp = 10000 - abs(mate) * 50 if mate > 0 else -10000 + abs(mate) * 50
        return (cp, mate)
    cp = w.score(mate_score=10000)
    return (0 if cp is None else int(cp), None)


def eval_bar_white_fraction(white_cp, mate_in=None):
    """Map White's evaluation to [0.03, 0.97] (or 0.0 / 1.0 on forced mate)."""
    if mate_in is not None:
        if mate_in > 0:
            return 1.0 if mate_in <= 1 else 0.97
        if mate_in < 0:
            return 0.0 if mate_in >= -1 else 0.03
    clamped = max(-1500.0, min(1500.0, float(white_cp)))
    frac = 1.0 / (1.0 + math.exp(-0.00368 * clamped))
    return max(0.03, min(0.97, frac))


def format_eval_label(white_cp, mate_in=None):
    if mate_in is not None:
        if mate_in == 0:
            return "1-0" if white_cp > 0 else "0-1"
        sign = "+" if mate_in > 0 else "-"
        return f"{sign}M{abs(mate_in)}"
    pawns = float(white_cp) / 100.0
    return f"{pawns:+.1f}"


def cp_to_win_pct(cp):
    """Map centipawns (mover's POV) to expected win percentage [0, 100]."""
    clamped = max(-1200.0, min(1200.0, float(cp)))
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * clamped)) - 1.0)


def classify_cpl(cpl):
    if cpl <= 15:
        return "Best"
    if cpl <= 40:
        return "Good"
    if cpl <= 90:
        return "Inaccuracy"
    if cpl <= 200:
        return "Mistake"
    return "Blunder"


def acpl_to_elo(acpl, accuracy_pct=None):
    """Map Average Centipawn Loss (and accuracy %) smoothly onto [300, 4050] Elo."""
    acpl = max(0.0, float(acpl))
    base = 3550.0 * math.exp(-0.0112 * acpl) + 260.0
    if accuracy_pct is not None:
        base += (float(accuracy_pct) - 70.0) * 4.2
    return round(max(300.0, min(4050.0, base)), 1)


def compute_game_move_quality_elo(ply_records, target_is_white):
    """Compute per-game Move-Quality Elo, Accuracy %, and ACPL for Target's moves.

    Also annotates each ply in `ply_records` with `cpl` and `quality` if missing.
    Returns dict: `{"move_quality_elo": float, "accuracy_pct": float, "acpl": float, "target_moves": int}`
    or `None` if Target made 0 moves.
    """
    cpls = []
    accuracies = []

    for ply in ply_records:
        mover_white = ply.get("mover_is_white", True)
        before_w = ply.get("eval_before_cp")
        after_w = ply.get("eval_after_cp")
        if before_w is None:
            before_w, _ = evaluate_board_static_cp(chess.Board(ply["fen_before"]))
            ply["eval_before_cp"] = before_w
        if after_w is None:
            after_w, mate_after = evaluate_board_static_cp(chess.Board(ply["fen_after"]))
            ply["eval_after_cp"] = after_w
            if ply.get("mate_after") is None:
                ply["mate_after"] = mate_after

        mover_before = before_w if mover_white else -before_w
        mover_after = after_w if mover_white else -after_w

        # Cap extreme already-decided positions so sacrifices when +900 -> +700 don't look like blunders
        win_before = cp_to_win_pct(mover_before)
        win_after = cp_to_win_pct(mover_after)
        win_loss = max(0.0, win_before - win_after)

        raw_cpl = max(0.0, min(500.0, float(mover_before - mover_after)))
        # Scale down CPL when win probability barely changed (e.g. +800 to +650)
        if abs(mover_before) > 500 and win_loss < 5.0:
            raw_cpl = min(raw_cpl, win_loss * 8.0)

        acc = 103.1668 * math.exp(-0.04354 * win_loss) - 3.1669
        acc = max(0.0, min(100.0, acc))

        ply["cpl"] = round(raw_cpl, 1)
        ply["accuracy"] = round(acc, 1)
        ply["quality"] = classify_cpl(raw_cpl)

        if mover_white == bool(target_is_white):
            cpls.append(raw_cpl)
            accuracies.append(acc)

    if not cpls:
        return None

    avg_cpl = sum(cpls) / len(cpls)
    avg_acc = sum(accuracies) / len(accuracies)
    mq_elo = acpl_to_elo(avg_cpl, avg_acc)
    return {
        "move_quality_elo": mq_elo,
        "accuracy_pct":     round(avg_acc, 1),
        "acpl":             round(avg_cpl, 1),
        "target_moves":     len(cpls),
    }


def aggregate_move_quality_elo(game_records):
    """Aggregate Move-Quality Elo weighted by target move count across games."""
    total_moves = 0
    weighted_cpl = 0.0
    weighted_acc = 0.0
    for g in game_records or ():
        mq = g.get("move_quality")
        if not mq:
            continue
        n = max(1, int(mq.get("target_moves", 1)))
        total_moves += n
        weighted_cpl += float(mq.get("acpl", 0.0)) * n
        weighted_acc += float(mq.get("accuracy_pct", 0.0)) * n
    if total_moves == 0:
        return None
    acpl = weighted_cpl / total_moves
    acc = weighted_acc / total_moves
    return {
        "move_quality_elo": acpl_to_elo(acpl, acc),
        "accuracy_pct":     round(acc, 1),
        "acpl":             round(acpl, 1),
        "target_moves":     total_moves,
    }


# ----------------------------------------------------------------------
# SAFE ENGINE SHUTDOWN HELPER
# ----------------------------------------------------------------------
def abort_and_close_engine(eng, quit_timeout=0.5):
    if eng is None:
        return
    protocol = getattr(eng, "protocol", None)
    loop = getattr(protocol, "loop", None)
    if loop is not None and protocol is not None:
        def _abort(proto=protocol):
            try:
                proto.send_line("stop")
            except Exception:
                pass
            tr = getattr(proto, "transport", None)
            if tr is not None:
                try:
                    tr.kill()
                except Exception:
                    pass
        try:
            loop.call_soon_threadsafe(_abort)
        except Exception:
            pass
    old_timeout = getattr(eng, "timeout", 1.0)
    try:
        eng.timeout = quit_timeout
        eng.quit()
    except Exception:
        pass
    finally:
        try:
            eng.timeout = old_timeout
        except Exception:
            pass
        try:
            eng.close()
        except Exception:
            pass


# ----------------------------------------------------------------------
# NON-BLOCKING LIVE EVALUATION WORKER & REPLAY EVALUATION WORKER
# ----------------------------------------------------------------------
class LiveEvalWorker(threading.Thread):
    """Analyses live board FENs on a dedicated low-thread, low-hash adjudicator.

    Never touches or delays `TournamentWorker` searches.
    """

    def __init__(self, adjudicator_path, protocol_cls=None):
        super().__init__(daemon=True)
        self.adjudicator_path = adjudicator_path
        self.protocol_cls = protocol_cls or chess.engine.UciProtocol
        self.running = True
        self._event = threading.Event()
        self._desired_fen = chess.STARTING_FEN
        self._last_done_fen = None
        self.white_cp = 0
        self.mate_in = None
        self.source = "static"
        self.cache = {}
        self._engine = None

    def request_fen(self, fen):
        if fen and fen != self._desired_fen:
            self._desired_fen = fen
            if fen in self.cache:
                self.white_cp, self.mate_in = self.cache[fen]
            self._event.set()

    def get_eval(self, fen=None):
        if fen and fen in self.cache:
            return self.cache[fen]
        return (self.white_cp, self.mate_in)

    def stop(self):
        self.running = False
        self._event.set()
        eng = self._engine
        if eng is not None:
            protocol = getattr(eng, "protocol", None)
            loop = getattr(protocol, "loop", None)
            if loop is not None and protocol is not None:
                def _abort(proto=protocol):
                    try:
                        proto.send_line("stop")
                    except Exception:
                        pass
                    tr = getattr(proto, "transport", None)
                    if tr is not None:
                        try:
                            tr.kill()
                        except Exception:
                            pass
                try:
                    loop.call_soon_threadsafe(_abort)
                except Exception:
                    pass

    def _try_launch(self):
        if not self.adjudicator_path:
            return None
        if (not isinstance(self.adjudicator_path, (list, tuple))
                and not os.path.isfile(self.adjudicator_path)):
            return None
        try:
            eng = chess.engine.SimpleEngine.popen(self.protocol_cls, self.adjudicator_path)
            opts = {}
            if "Threads" in eng.options:
                opts["Threads"] = 1
            if "Hash" in eng.options:
                opts["Hash"] = 16
            if "Use Sleeping Threads" in eng.options:
                opts["Use Sleeping Threads"] = True
            if opts:
                try:
                    eng.configure(opts)
                except Exception:
                    pass
            eng.ping()
            self.source = "engine"
            return eng
        except Exception:
            return None

    def run(self):
        self._engine = self._try_launch()
        try:
            while self.running:
                fen = self._desired_fen
                if fen == self._last_done_fen:
                    self._event.wait(timeout=0.10)
                    self._event.clear()
                    continue
                try:
                    board = chess.Board(fen)
                except Exception:
                    self._last_done_fen = fen
                    continue
                if board.is_game_over(claim_draw=True):
                    cp, mate = evaluate_board_static_cp(board)
                elif self._engine is not None:
                    try:
                        info = self._engine.analyse(
                            board, chess.engine.Limit(time=0.04, depth=10)
                        )
                        cp, mate = score_to_white_cp(info.get("score"))
                    except Exception:
                        cp, mate = evaluate_board_static_cp(board)
                else:
                    cp, mate = evaluate_board_static_cp(board)
                if len(self.cache) > 2048:
                    self.cache.clear()
                self.cache[fen] = (cp, mate)
                self.white_cp = cp
                self.mate_in = mate
                self._last_done_fen = fen
        finally:
            eng = self._engine
            self._engine = None
            abort_and_close_engine(eng)


class ReplayEvalWorker(threading.Thread):
    """Stronger Stockfish evaluation worker used in the post-tournament Replay Viewer."""

    def __init__(self, adjudicator_path, threads=4, hash_mb=256, protocol_cls=None):
        super().__init__(daemon=True)
        self.adjudicator_path = adjudicator_path
        self.threads = max(1, int(threads))
        self.hash_mb = max(32, int(hash_mb))
        self.protocol_cls = protocol_cls or chess.engine.UciProtocol
        self.running = True
        self._event = threading.Event()
        self._desired_fen = chess.STARTING_FEN
        self._last_done_fen = None
        self.white_cp = 0
        self.mate_in = None
        self.depth = 0
        self.engine_ready = False
        self.cache = {}
        self._engine = None

    def request_fen(self, fen):
        if not fen:
            return
        if fen in self.cache:
            self.white_cp, self.mate_in, self.depth = self.cache[fen]
        if fen != self._desired_fen:
            self._desired_fen = fen
            self._event.set()

    def get_eval(self, fen):
        if fen in self.cache:
            return self.cache[fen]
        cp, mate = evaluate_board_static_cp(chess.Board(fen))
        return (cp, mate, 0)

    def stop(self):
        self.running = False
        self._event.set()
        eng = self._engine
        if eng is not None:
            protocol = getattr(eng, "protocol", None)
            loop = getattr(protocol, "loop", None)
            if loop is not None and protocol is not None:
                def _abort(proto=protocol):
                    try:
                        proto.send_line("stop")
                    except Exception:
                        pass
                    tr = getattr(proto, "transport", None)
                    if tr is not None:
                        try:
                            tr.kill()
                        except Exception:
                            pass
                try:
                    loop.call_soon_threadsafe(_abort)
                except Exception:
                    pass

    def _try_launch(self):
        if not self.adjudicator_path:
            return None
        if (not isinstance(self.adjudicator_path, (list, tuple))
                and not os.path.isfile(self.adjudicator_path)):
            return None
        try:
            eng = chess.engine.SimpleEngine.popen(self.protocol_cls, self.adjudicator_path)
            opts = {}
            if "Threads" in eng.options:
                t = self.threads
                if eng.options["Threads"].max is not None:
                    t = min(t, eng.options["Threads"].max)
                opts["Threads"] = max(1, t)
            if "Hash" in eng.options:
                h = self.hash_mb
                if eng.options["Hash"].max is not None:
                    h = min(h, eng.options["Hash"].max)
                opts["Hash"] = max(16, h)
            if "Use Sleeping Threads" in eng.options:
                opts["Use Sleeping Threads"] = True
            if opts:
                try:
                    eng.configure(opts)
                except Exception:
                    pass
            eng.ping()
            self.engine_ready = True
            return eng
        except Exception:
            return None

    def run(self):
        self._engine = self._try_launch()
        try:
            while self.running:
                fen = self._desired_fen
                if fen == self._last_done_fen:
                    self._event.wait(timeout=0.10)
                    self._event.clear()
                    continue
                if fen in self.cache and self.cache[fen][2] >= 16:
                    self.white_cp, self.mate_in, self.depth = self.cache[fen]
                    self._last_done_fen = fen
                    continue
                try:
                    board = chess.Board(fen)
                except Exception:
                    self._last_done_fen = fen
                    continue
                if board.is_game_over(claim_draw=True):
                    cp, mate = evaluate_board_static_cp(board)
                    depth = 99
                elif self._engine is not None:
                    try:
                        info = self._engine.analyse(
                            board, chess.engine.Limit(time=0.25, depth=18)
                        )
                        cp, mate = score_to_white_cp(info.get("score"))
                        depth = int(info.get("depth") or 18)
                    except Exception:
                        cp, mate = evaluate_board_static_cp(board)
                        depth = 0
                else:
                    cp, mate = evaluate_board_static_cp(board)
                    depth = 0
                if len(self.cache) > 2048:
                    self.cache.clear()
                self.cache[fen] = (cp, mate, depth)
                self.white_cp = cp
                self.mate_in = mate
                self.depth = depth
                self._last_done_fen = fen
        finally:
            eng = self._engine
            self._engine = None
            abort_and_close_engine(eng)


# ----------------------------------------------------------------------
# ENGINE DATA TRACKING (CPU %, MEMORY MB, THREADS, NPS)
# ----------------------------------------------------------------------
def extract_engine_pid(engine):
    if engine is None:
        return None
    protocol = getattr(engine, "protocol", None)
    transport = getattr(protocol, "transport", None)
    if transport is not None and hasattr(transport, "get_pid"):
        try:
            return transport.get_pid()
        except Exception:
            pass
    proc = getattr(transport, "_proc", None)
    return getattr(proc, "pid", None)


class EngineResourceTracker:
    """Samples CPU %, RSS Memory (MB), OS thread count, and UCI NPS of an engine."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._pid = None
        self._ps_proc = None
        self._last_proc_jiffies = None
        self._last_wall_time = None
        self.live_cpu_pct = 0.0
        self.live_ram_mb = 0.0
        self.live_threads = 0
        self.live_nps = 0
        self._cpu_samples = []
        self._ram_samples = []
        self.peak_cpu_pct = 0.0
        self.peak_ram_mb = 0.0
        self._game_cpu = []
        self._game_ram = []

    def start_game(self):
        self._game_cpu = []
        self._game_ram = []

    def finish_game(self):
        if not self._game_cpu and not self._game_ram:
            return None
        return {
            "avg_cpu_pct":  round(sum(self._game_cpu) / max(1, len(self._game_cpu)), 1),
            "peak_cpu_pct": round(max(self._game_cpu, default=0.0), 1),
            "avg_ram_mb":   round(sum(self._game_ram) / max(1, len(self._game_ram)), 1),
            "peak_ram_mb":  round(max(self._game_ram, default=0.0), 1),
        }

    def summary(self):
        return {
            "live_cpu_pct": round(self.live_cpu_pct, 1),
            "live_ram_mb":  round(self.live_ram_mb, 1),
            "live_threads": int(self.live_threads),
            "live_nps":     int(self.live_nps),
            "avg_cpu_pct":  round(sum(self._cpu_samples) / max(1, len(self._cpu_samples)), 1)
                            if self._cpu_samples else 0.0,
            "peak_cpu_pct": round(self.peak_cpu_pct, 1),
            "avg_ram_mb":   round(sum(self._ram_samples) / max(1, len(self._ram_samples)), 1)
                            if self._ram_samples else 0.0,
            "peak_ram_mb":  round(self.peak_ram_mb, 1),
            "samples":      len(self._ram_samples),
        }

    def sample(self, engine=None, pid=None, latest_nps=None):
        if latest_nps is not None and latest_nps > 0:
            self.live_nps = int(latest_nps)
        if pid is None:
            pid = extract_engine_pid(engine)
        if not pid:
            return self.summary()

        cpu_pct, ram_mb, threads = self._read_os_metrics(pid)
        if ram_mb is not None:
            self.live_cpu_pct = max(0.0, cpu_pct or 0.0)
            self.live_ram_mb = max(0.0, ram_mb)
            self.live_threads = max(1, threads or 1)
            self._cpu_samples.append(self.live_cpu_pct)
            self._ram_samples.append(self.live_ram_mb)
            self._game_cpu.append(self.live_cpu_pct)
            self._game_ram.append(self.live_ram_mb)
            if self.live_cpu_pct > self.peak_cpu_pct:
                self.peak_cpu_pct = self.live_cpu_pct
            if self.live_ram_mb > self.peak_ram_mb:
                self.peak_ram_mb = self.live_ram_mb
        return self.summary()

    def _read_os_metrics(self, pid):
        try:
            import psutil
            if self._pid != pid or self._ps_proc is None:
                self._pid = pid
                self._ps_proc = psutil.Process(pid)
                self._ps_proc.cpu_percent(None)
            procs = [self._ps_proc]
            try:
                procs.extend(self._ps_proc.children(recursive=True))
            except Exception:
                pass
            cpu_total = 0.0
            rss_bytes = 0
            threads = 0
            for p in procs:
                try:
                    cpu_total += p.cpu_percent(None)
                    rss_bytes += p.memory_info().rss
                    threads += p.num_threads()
                except Exception:
                    continue
            return (cpu_total, rss_bytes / (1024.0 * 1024.0), max(1, threads))
        except Exception:
            pass

        if sys.platform.startswith("linux"):
            try:
                with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
                    stat_txt = f.read()
                rparen = stat_txt.rfind(")")
                fields = stat_txt[rparen + 2:].split()
                utime = int(fields[11])
                stime = int(fields[12])
                num_threads = int(fields[17])
                rss_pages = int(fields[21])
                clk_tck = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
                page_sz = os.sysconf("SC_PAGESIZE") if hasattr(os, "sysconf") else 4096
                now = time.monotonic()
                total_ticks = utime + stime
                cpu = 0.0
                if self._pid == pid and self._last_proc_jiffies is not None and self._last_wall_time:
                    dt = max(1e-3, now - self._last_wall_time)
                    cpu = ((total_ticks - self._last_proc_jiffies) / float(clk_tck)) / dt * 100.0
                self._pid = pid
                self._last_proc_jiffies = total_ticks
                self._last_wall_time = now
                ram = (rss_pages * page_sz) / (1024.0 * 1024.0)
                return (max(0.0, cpu), ram, max(1, num_threads))
            except Exception:
                return (None, None, None)

        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes

                class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                    ]

                class FILETIME(ctypes.Structure):
                    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                                ("dwHighDateTime", wintypes.DWORD)]

                kernel32 = ctypes.windll.kernel32
                psapi = ctypes.windll.psapi
                handle = kernel32.OpenProcess(0x0410, False, int(pid))
                if not handle:
                    return (None, None, None)
                try:
                    pmc = PROCESS_MEMORY_COUNTERS()
                    pmc.cb = ctypes.sizeof(pmc)
                    ram = None
                    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
                        ram = pmc.WorkingSetSize / (1024.0 * 1024.0)
                    c_t, e_t, k_t, u_t = FILETIME(), FILETIME(), FILETIME(), FILETIME()
                    cpu = 0.0
                    if kernel32.GetProcessTimes(handle, ctypes.byref(c_t), ctypes.byref(e_t),
                                                ctypes.byref(k_t), ctypes.byref(u_t)):
                        kern = (k_t.dwHighDateTime << 32) | k_t.dwLowDateTime
                        user = (u_t.dwHighDateTime << 32) | u_t.dwLowDateTime
                        total_100ns = kern + user
                        now = time.monotonic()
                        if (self._pid == pid and self._last_proc_jiffies is not None
                                and self._last_wall_time):
                            dt = max(1e-3, now - self._last_wall_time)
                            cpu = ((total_100ns - self._last_proc_jiffies) * 1e-7) / dt * 100.0
                        self._pid = pid
                        self._last_proc_jiffies = total_100ns
                        self._last_wall_time = now
                    return (max(0.0, cpu), ram, 1)
                finally:
                    kernel32.CloseHandle(handle)
            except Exception:
                return (None, None, None)

        return (None, None, None)


# ----------------------------------------------------------------------
# ETA ESTIMATION & OPPONENT DISPLAY NAME HELPERS
# ----------------------------------------------------------------------
def friendly_opponent_label(path, rating=None):
    if not path:
        return "Opponent"
    base = os.path.splitext(os.path.basename(path))[0]
    parent = os.path.basename(os.path.dirname(path))
    if parent.lower() in ("windows", "64", "gcc", "amd 64", "stockfish"):
        grand = os.path.basename(os.path.dirname(os.path.dirname(path)))
        if grand and grand.lower() not in ("chess", "engines", "stockfish"):
            return grand
    if parent and parent.lower().startswith("stockfish "):
        return parent
    return base


def estimate_tournament_eta_seconds(elapsed_s, games_played, total_games,
                                    time_per_move=0.1, current_move_number=0,
                                    extra_playlist_engines=0, base_pool_games=0):
    remaining_current = max(0, int(total_games) - int(games_played))
    extra_games = max(0, int(extra_playlist_engines)) * max(0, int(base_pool_games))
    total_remaining_games = remaining_current + extra_games
    if total_remaining_games <= 0:
        return 0.0

    prior_per_game = max(0.5, 68.0 * float(time_per_move))
    partial = min(0.92, max(0.0, float(current_move_number) / 70.0))
    effective_done = float(games_played) + partial

    if effective_done >= 0.75 and elapsed_s > 0.1:
        observed_per_game = float(elapsed_s) / effective_done
        weight = min(1.0, effective_done / 4.0)
        sec_per_game = weight * observed_per_game + (1.0 - weight) * prior_per_game
    else:
        sec_per_game = prior_per_game

    eta = (remaining_current - partial) * sec_per_game + extra_games * sec_per_game
    return max(0.0, eta)


def format_eta(seconds):
    if seconds is None:
        return "—"
    sec = max(0, int(round(float(seconds))))
    if sec <= 0:
        return "00:00"
    if sec >= 3600:
        h = sec // 3600
        m = (sec % 3600) // 60
        return f"~{h}h {m:02d}m"
    return f"~{sec // 60:02d}:{sec % 60:02d}"
