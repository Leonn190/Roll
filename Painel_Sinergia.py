# Painel_Sinergia.py
import pygame
import colorsys

RIGHT_PANEL_W = 240
SYNERGY_PANEL_H = 360

PANEL_BG = (18, 18, 24)
PANEL_BORDER = (80, 80, 95)

TEXT = (245, 245, 245)
TEXT_SUB = (210, 210, 220)

SYNERGY_THRESHOLD = 2  # mantido (mas agora o painel pode usar as conectadas do player)

def draw_round_rect(surf, color, rect, width=0, radius=12):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

# =========================
# MESMA COR DA GRID
# =========================
def _norm_sym(x) -> str:
    return str(x).strip().lower()

_SYNERGY_COLORS = {
    "controle":   (90, 170, 255),
    "explosão":   (255, 110, 110),
    "explosao":   (255, 110, 110),
    "tanque":     (110, 255, 160),
    "velocidade": (255, 200, 110),
    "atirador":   (200, 140, 255),
    "invocador":  (120, 240, 255),
    "brawler":    (255, 160, 220),
}

def _color_for_synergy(sym: str):
    s = _norm_sym(sym)
    if s in _SYNERGY_COLORS:
        return _SYNERGY_COLORS[s]
    # fallback determinístico (igual ao da grid)
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.60, 1.00)
    return (int(r * 255), int(g * 255), int(b * 255))


class PainelSinergia:
    def __init__(self, tela):
        self.tela = tela
        self.rect = pygame.Rect(0, 0, 10, 10)
        self._recalc_layout()

    def _recalc_layout(self):
        W = self.tela.get_width()
        self.rect = pygame.Rect(W - RIGHT_PANEL_W, 0, RIGHT_PANEL_W, SYNERGY_PANEL_H)

    # NOVO: relação direta com o PlayerEstrategista (se fornecido)
    def draw(self, surf, font_title, font_item, grid_occ: dict, player=None):
        draw_round_rect(surf, PANEL_BG, self.rect, 0, 0)
        pygame.draw.rect(surf, PANEL_BORDER, self.rect, 3)

        x = self.rect.x + 18
        y = self.rect.y + 18

        title = font_title.render("SINERGIAS", True, TEXT)
        surf.blit(title, (x, y))
        y += 46

        # Se tiver player, prioriza as sinergias CONECTADAS (ativas) dele
        if player is not None and hasattr(player, "sinergias_ativas") and isinstance(player.sinergias_ativas, dict):
            counts = dict(player.sinergias_ativas)
        else:
            # fallback: contagem simples (mantido)
            counts = {}
            for cartucho in grid_occ.values():
                for s in getattr(cartucho, "sinergias", []):
                    counts[s] = counts.get(s, 0) + 1

        if not counts:
            t = font_item.render("Nenhuma ainda.", True, TEXT_SUB)
            surf.blit(t, (x, y))
            return

        items = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0]).lower()))
        shown = 0
        for syn, n in items:
            if shown >= 10:
                break

            # cor = mesma da grid (sem amarelo/inativo)
            color = _color_for_synergy(syn)

            # (mantém threshold pra “sugerir” ativo/inativo só no texto, sem mudar cor)
            tag = "" if int(n) >= SYNERGY_THRESHOLD else " (fraca)"
            s = font_item.render(f"{syn}  ({n}){tag}", True, color)
            surf.blit(s, (x, y))
            y += 28
            shown += 1
