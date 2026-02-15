# Painel_Sinergia.py
import pygame
import colorsys
from Loja import SHOP_SLOTS, SHOP_PAD, SHOP_GAP, SHOP_BUTTON_H
from Banco import BANK_CARD_H

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

def _color_for_synergy(sym: str):
    s = _norm_sym(sym)

    # algoritmo determinístico igual ao da grid
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
        self.hovered_synergy = None
        self._item_rects = {}
        self._recalc_layout()

    def _recalc_layout(self):
        W = self.tela.get_width()
        H = self.tela.get_height()
        shop_h = (SHOP_PAD * 2 + SHOP_SLOTS * BANK_CARD_H + (SHOP_SLOTS - 1) * SHOP_GAP + SHOP_BUTTON_H + 60)
        painel_h = max(SYNERGY_PANEL_H, H - shop_h)
        self.rect = pygame.Rect(W - RIGHT_PANEL_W, 0, RIGHT_PANEL_W, painel_h)

    # NOVO: relação direta com o PlayerEstrategista (se fornecido)
    def draw(self, surf, font_title, font_item, grid_occ: dict, player=None):
        draw_round_rect(surf, PANEL_BG, self.rect, 0, 0)
        pygame.draw.rect(surf, PANEL_BORDER, self.rect, 3)

        x = self.rect.x + 18
        y = self.rect.y + 18

        title = font_title.render("SINERGIAS", True, TEXT)
        surf.blit(title, (x, y))
        y += 46

        self._item_rects.clear()
        self.hovered_synergy = None

        # base: todas as sinergias em campo
        total_counts = {}
        for cartucho in grid_occ.values():
            for s in getattr(cartucho, "sinergias", []):
                total_counts[s] = total_counts.get(s, 0) + 1

        active_counts = {}
        if player is not None and hasattr(player, "sinergias_ativas") and isinstance(player.sinergias_ativas, dict):
            active_counts = {k: int(v) for k, v in player.sinergias_ativas.items()}

        if not total_counts:
            t = font_item.render("Nenhuma ainda.", True, TEXT_SUB)
            surf.blit(t, (x, y))
            return

        items = sorted(total_counts.items(), key=lambda kv: (-kv[1], str(kv[0]).lower()))
        shown = 0
        mouse_pos = pygame.mouse.get_pos()
        for syn, n in items:
            if shown >= 10:
                break

            syn_norm = _norm_sym(syn)
            is_active = syn_norm in active_counts
            color = _color_for_synergy(syn) if is_active else (255, 255, 255)

            active_n = active_counts.get(syn_norm, 0)
            tag = f" ({active_n})" if is_active else ""
            s = font_item.render(f"{str(syn).title()}  [{n}]{tag}", True, color)
            item_rect = s.get_rect(topleft=(x, y))
            surf.blit(s, item_rect.topleft)
            self._item_rects[syn_norm] = item_rect
            if item_rect.collidepoint(mouse_pos):
                self.hovered_synergy = syn_norm

            y += 28
            shown += 1
