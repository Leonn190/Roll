# Loja.py
import pygame
import random

from Cartucho import Cartucho
from Banco import BANK_CARD_W, BANK_CARD_H

RIGHT_PANEL_W = 240

PANEL_BG = (18, 18, 24)
PANEL_BORDER = (80, 80, 95)
TEXT = (245, 245, 245)

BTN_BG = (26, 26, 34)
BTN_BORDER = (90, 90, 110)
BTN_HOVER = (40, 40, 56)
GOLD = (255, 215, 90)
MUTED = (180, 180, 195)

SHOP_SLOTS = 3
SHOP_PAD = 14
SHOP_GAP = 12
SHOP_BUTTON_H = 44

# custos (pedido)
RARITY_COST = {
    "comum": 2,
    "incomum": 3,
    "raro": 4,
    "épico": 5,
    "epico": 5,
    "lendário": 6,
    "lendario": 6,
    "mítico": 7,
    "mitico": 7,
}

REROLL_COST = 1

def draw_round_rect(surf, color, rect, width=0, radius=12):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)

def _norm(s: str) -> str:
    return str(s).strip().lower()

def _get_raridade(cartucho) -> str:
    # tenta cartucho.raridade, cartucho.dados["raridade"], cartucho.to_def()["raridade"]
    r = getattr(cartucho, "raridade", None)
    if r:
        return _norm(r)

    dados = getattr(cartucho, "dados", {}) or {}
    r = dados.get("raridade", None)
    if r:
        return _norm(r)

    try:
        d = cartucho.to_def()
        r = d.get("raridade", None)
        if r:
            return _norm(r)
    except Exception:
        pass

    return "comum"

def _cost_for_cartucho(cartucho) -> int:
    rar = _get_raridade(cartucho)
    return int(RARITY_COST.get(rar, 2))


def _sell_value_for_cartucho(cartucho) -> int:
    # venda devolve custo de compra - 1 (mínimo 0)
    return max(0, _cost_for_cartucho(cartucho) - 1)


class Loja:
    def __init__(self, tela, deck_defs: list[dict]):
        self.tela = tela
        self.deck_defs = deck_defs

        self.rect = pygame.Rect(0, 0, 10, 10)
        self.slot_rects = []
        self.cartuchos = [None] * SHOP_SLOTS
        self.btn_reroll = pygame.Rect(0, 0, 10, SHOP_BUTTON_H)

        # player (ouro)
        self.player = None
        self.gasto_total = 0

        self._recalc_layout()
        self.reroll(free=True)  # primeira rolagem não cobra (não foi pedido cobrar)

    # ------------ player hook ------------
    def set_player(self, player):
        self.player = player

    def _recalc_layout(self):
        W = self.tela.get_width()
        H = self.tela.get_height()

        total_h = (SHOP_PAD * 2 + SHOP_SLOTS * BANK_CARD_H + (SHOP_SLOTS - 1) * SHOP_GAP + SHOP_BUTTON_H + 60)
        self.rect = pygame.Rect(W - RIGHT_PANEL_W, H - total_h, RIGHT_PANEL_W, total_h)
        self._layout_slots()

    def _layout_slots(self):
        self.slot_rects.clear()

        x = self.rect.x + (self.rect.w - BANK_CARD_W) // 2
        y = self.rect.y + 44

        for i in range(SHOP_SLOTS):
            self.slot_rects.append(pygame.Rect(x, y, BANK_CARD_W, BANK_CARD_H))
            y += BANK_CARD_H + SHOP_GAP

        self.btn_reroll = pygame.Rect(self.rect.x + SHOP_PAD, y + 8, self.rect.w - 2 * SHOP_PAD, SHOP_BUTTON_H)

    def _new_cartucho_from_def(self, d: dict):
        c = Cartucho(d, BANK_CARD_W, BANK_CARD_H)
        c.location = "loja"
        return c

    def _put_def_back(self, cartucho: Cartucho):
        self.deck_defs.append(cartucho.to_def())

    def reroll(self, free: bool = False):
        # custo do reroll
        if not free:
            if self.player is None:
                return
            if getattr(self.player, "ouro", 0) < REROLL_COST:
                return
            self.player.ouro -= REROLL_COST
            self.gasto_total += REROLL_COST

        # devolve os atuais pro deck
        for i in range(SHOP_SLOTS):
            if self.cartuchos[i] is not None:
                self._put_def_back(self.cartuchos[i])
                self.cartuchos[i] = None

        random.shuffle(self.deck_defs)
        for i in range(SHOP_SLOTS):
            if not self.deck_defs:
                break
            d = self.deck_defs.pop()
            self.cartuchos[i] = self._new_cartucho_from_def(d)
            self.cartuchos[i].set_location_shop(self.slot_rects[i])

    def sell_drop_here(self, mouse_pos):
        # soltar dentro do painel vende (mecânica de ouro da venda não foi pedida aqui)
        return self.rect.collidepoint(mouse_pos)

    def handle_click(self, mouse_pos):
        # reroll gasta 1 ouro
        if self.btn_reroll.collidepoint(mouse_pos):
            self.reroll(free=False)

    def pick_at_pos(self, mouse_pos):
        """
        Clique numa carta da loja -> COMPRA se tiver ouro suficiente:
        comum=2, incomum=3, raro=4, épico=5, lendário=6, mítico=7
        """
        for i in range(SHOP_SLOTS - 1, -1, -1):
            c = self.cartuchos[i]
            if c is None:
                continue
            if c.rect.collidepoint(mouse_pos):
                cost = _cost_for_cartucho(c)

                if self.player is None:
                    return None
                if getattr(self.player, "ouro", 0) < cost:
                    return None

                self.player.ouro -= cost
                self.gasto_total += cost

                self.cartuchos[i] = None
                c.location = "banco"
                return c
        return None

    def sell_value_for_cartucho(self, cartucho) -> int:
        return _sell_value_for_cartucho(cartucho)

    def draw(self, surf, fonte_titulo, fonte_item, fonte_nome=None, fonte_carac=None):
        self._recalc_layout()

        draw_round_rect(surf, PANEL_BG, self.rect, 0, 0)
        pygame.draw.rect(surf, PANEL_BORDER, self.rect, 3)

        t = fonte_titulo.render("LOJA", True, TEXT)
        surf.blit(t, (self.rect.x + SHOP_PAD, self.rect.y + 10))

        gasto_txt = fonte_item.render(f"Gasto: {int(self.gasto_total)}g", True, GOLD)
        surf.blit(gasto_txt, (self.rect.right - SHOP_PAD - gasto_txt.get_width(), self.rect.y + 16))

        for sr in self.slot_rects:
            draw_round_rect(surf, (12, 12, 16), sr, 0, 12)
            draw_round_rect(surf, (40, 40, 50), sr, 2, 12)

        fonte_nome = fonte_nome or fonte_item
        fonte_carac = fonte_carac or fonte_item

        for i, c in enumerate(self.cartuchos):
            if c is None:
                continue
            if not c.dragging:
                c.set_rect(self.slot_rects[i])
            c.draw(surf, fonte_nome, fonte_carac, compact=False)

            cost = _cost_for_cartucho(c)
            badge = pygame.Rect(c.rect.x + 6, c.rect.y + 6, 52, 24)
            draw_round_rect(surf, (12, 12, 16), badge, 0, 8)
            draw_round_rect(surf, (115, 95, 45), badge, 2, 8)
            ctxt = fonte_item.render(f"{cost}g", True, GOLD)
            surf.blit(ctxt, ctxt.get_rect(center=badge.center))

        mx, my = pygame.mouse.get_pos()
        hovering = self.btn_reroll.collidepoint((mx, my))
        draw_round_rect(surf, BTN_HOVER if hovering else BTN_BG, self.btn_reroll, 0, 10)
        draw_round_rect(surf, BTN_BORDER, self.btn_reroll, 2, 10)

        label = fonte_item.render(f"REROLL ({REROLL_COST}g)", True, TEXT)
        surf.blit(label, label.get_rect(center=self.btn_reroll.center))
