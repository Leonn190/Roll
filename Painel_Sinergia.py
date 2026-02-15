# Painel_Sinergia.py
import pygame
import colorsys
from Loja import SHOP_SLOTS, SHOP_PAD, SHOP_GAP, SHOP_BUTTON_H
from Banco import BANK_CARD_H
from Brawl_Stars.Brawl import DECK_DEFS, CORES_RARIDADE, gerar_imagem_cartucho_grid

RIGHT_PANEL_W = 240
SYNERGY_PANEL_H = 360

PANEL_BG = (18, 18, 24)
PANEL_BORDER = (80, 80, 95)

TEXT = (245, 245, 245)
TEXT_SUB = (210, 210, 220)

SYNERGY_THRESHOLD = 2  # mantido (mas agora o painel pode usar as conectadas do player)

RARITY_ORDER = {
    "comum": 0,
    "incomum": 1,
    "raro": 2,
    "épico": 3,
    "mítico": 4,
    "lendário": 5,
}

def draw_round_rect(surf, color, rect, width=0, radius=12):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def _draw_text_with_outline(surf, font, text, color, outline_color, topleft, esp=1):
    base = font.render(text, True, color)
    x, y = topleft
    for ox in range(-esp, esp + 1):
        for oy in range(-esp, esp + 1):
            if ox == 0 and oy == 0:
                continue
            sombra = font.render(text, True, outline_color)
            surf.blit(sombra, (x + ox, y + oy))
    surf.blit(base, topleft)


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
        self._tooltip = None
        self._all_brawlers_defs = list(DECK_DEFS)
        self._synergy_meta = self._build_synergy_meta(self._all_brawlers_defs)
        self._recalc_layout()

    def _build_synergy_meta(self, brawlers_defs):
        meta = {}
        for d in brawlers_defs:
            raridade = str(d.get("raridade", "comum")).strip().lower()
            ordem = RARITY_ORDER.get(raridade, 0)
            for s in (d.get("características", []) or []):
                nome = str(s).strip()
                if not nome:
                    continue
                key = _norm_sym(nome)
                it = meta.setdefault(key, {
                    "nome": nome,
                    "raridade": raridade,
                    "ordem": ordem,
                })
                if ordem > it["ordem"]:
                    it["ordem"] = ordem
                    it["raridade"] = raridade
        return meta

    def _draw_synergy_tooltip(self, surf, font_item, mouse_pos):
        if not self._tooltip:
            return

        titulo = str(self._tooltip.get("titulo", "Sinergia"))
        integrantes = list(self._tooltip.get("integrantes", []) or [])

        t_titulo = font_item.render(titulo, True, TEXT)

        icon_size = 32
        pad = 10
        cols = 6
        rows = max(1, (len(integrantes) + cols - 1) // cols)

        grid_w = cols * icon_size + max(0, cols - 1) * 6
        used_cols = cols if integrantes else 1
        if integrantes and len(integrantes) < cols:
            used_cols = len(integrantes)
            grid_w = used_cols * icon_size + max(0, used_cols - 1) * 6

        w = max(t_titulo.get_width() + pad * 2, grid_w + pad * 2)
        h = pad * 2 + t_titulo.get_height() + 8 + rows * icon_size + max(0, rows - 1) * 6

        tip = pygame.Rect(mouse_pos[0] + 16, mouse_pos[1] + 14, w, h)
        if tip.right > surf.get_width() - 8:
            tip.x = mouse_pos[0] - w - 16
        if tip.bottom > surf.get_height() - 8:
            tip.y = surf.get_height() - h - 8

        draw_round_rect(surf, (15, 15, 20), tip, 0, 10)
        pygame.draw.rect(surf, (120, 120, 140), tip, 2, border_radius=10)

        surf.blit(t_titulo, (tip.x + pad, tip.y + pad))
        y0 = tip.y + pad + t_titulo.get_height() + 8
        pygame.draw.line(surf, (90, 90, 110), (tip.x + 8, y0 - 4), (tip.right - 8, y0 - 4), 1)

        if not integrantes:
            vazio = font_item.render("Sem brawlers", True, TEXT_SUB)
            surf.blit(vazio, (tip.x + pad, y0 + 2))
            return

        for idx, d in enumerate(integrantes):
            row = idx // cols
            col = idx % cols
            xx = tip.x + pad + col * (icon_size + 6)
            yy = y0 + row * (icon_size + 6)
            icon = gerar_imagem_cartucho_grid(d, (icon_size, icon_size))
            surf.blit(icon, (xx, yy))
            raridade = str(d.get("raridade", "comum")).strip().lower()
            borda = CORES_RARIDADE.get(raridade, (70, 70, 90))
            pygame.draw.rect(surf, borda, pygame.Rect(xx, yy, icon_size, icon_size), 2, border_radius=6)

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
        self._tooltip = None

        # base: sinergias em campo
        total_counts = {}
        for cartucho in grid_occ.values():
            for s in getattr(cartucho, "sinergias", []):
                total_counts[s] = total_counts.get(s, 0) + 1

        active_counts = {}
        if player is not None and hasattr(player, "sinergias_ativas") and isinstance(player.sinergias_ativas, dict):
            active_counts = {k: int(v) for k, v in player.sinergias_ativas.items()}

        items = []
        for syn_norm, meta in self._synergy_meta.items():
            qtd = int(total_counts.get(syn_norm, 0))
            is_active = syn_norm in active_counts
            has_on_grid = qtd > 0
            items.append((
                syn_norm,
                str(meta.get("nome", syn_norm)).title(),
                int(meta.get("ordem", 0)),
                str(meta.get("raridade", "comum")).lower(),
                qtd,
                is_active,
                has_on_grid,
            ))

        if not items:
            t = font_item.render("Nenhuma ainda.", True, TEXT_SUB)
            surf.blit(t, (x, y))
            return

        items.sort(key=lambda it: (-it[2], it[1].lower()))
        shown = 0
        mouse_pos = pygame.mouse.get_pos()
        for syn_norm, nome, _, raridade, n, is_active, has_on_grid in items:
            if shown >= 10:
                break

            if has_on_grid:
                color = _color_for_synergy(nome) if is_active else (220, 220, 235)
            else:
                color = (110, 110, 125)

            shown_n = active_counts.get(syn_norm, n) if is_active else n
            texto = f"{nome}  [{shown_n}]"
            ts = font_item.render(texto, True, color)
            icon_rect = pygame.Rect(x, y + 3, 14, 14)
            icon_color = color if has_on_grid else (80, 80, 96)
            pygame.draw.rect(surf, icon_color, icon_rect, border_radius=4)
            pygame.draw.rect(surf, CORES_RARIDADE.get(raridade, (70, 70, 90)), icon_rect, 2, border_radius=4)

            text_pos = (x + 22, y)
            item_rect = ts.get_rect(topleft=text_pos)
            _draw_text_with_outline(surf, font_item, texto, color, (0, 0, 0), text_pos, esp=1)
            self._item_rects[syn_norm] = item_rect
            if item_rect.collidepoint(mouse_pos):
                self.hovered_synergy = syn_norm
                integrantes = []
                for d in self._all_brawlers_defs:
                    sins = [str(s2).strip().lower() for s2 in (d.get("características", []) or [])]
                    if syn_norm in sins:
                        integrantes.append(d)

                self._tooltip = {
                    "titulo": f"{nome} ({len(integrantes)})",
                    "integrantes": integrantes,
                }

            y += 24
            shown += 1

        self._draw_synergy_tooltip(surf, font_item, mouse_pos)
