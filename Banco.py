# Banco.py
import pygame

# ============================================================
# CONFIG
# ============================================================
RIGHT_PANEL_W = 240
BOTTOM_BANK_H = 210
MARGIN = 26

BANK_BG = (18, 18, 24)
BANK_BORDER = (80, 80, 95)
TEXT = (245, 245, 245)

BANK_SLOTS = 12

BANK_CARD_W = 160
BANK_CARD_H = 120

BANK_GAP = 14

# hover (zoom suave animado)
HOVER_SCALE = 1.18
HOVER_RAISE = 14

# animação do hover
HOVER_SMOOTH_SPEED = 14.0  # maior = mais rápido (suave ainda)


# ============================================================
# HELPERS
# ============================================================
def clamp(x, a, b):
    return a if x < a else b if x > b else x

def draw_round_rect(surf, color, rect, width=0, radius=12):
    pygame.draw.rect(surf, color, rect, width, border_radius=radius)


def _exp_smooth(current: float, target: float, dt: float, speed: float) -> float:
    # aproxima exponencial: frame-rate independent
    if dt <= 0:
        return current
    k = 1.0 - pow(2.718281828, -speed * dt)
    return current + (target - current) * k


# ============================================================
# CLASSE
# ============================================================
class Banco:
    def __init__(self, tela):
        self.tela = tela
        self.slots_n = BANK_SLOTS

        self.rect = pygame.Rect(0, 0, 10, 10)
        self.slot_rects = []
        self.slots = [None] * self.slots_n

        # player (novo sistema)
        self.player = None

        # hover
        self._hover_idx = None
        self._hover_scale = 1.0
        self._last_ms = None

        # fonte cache
        self._fonte_carac = pygame.font.SysFont(None, 18, bold=True)

        self._recalc_layout()
        self.recompactar()  # garante layout correto mesmo vazio

    # ------------ player hook ------------
    def set_player(self, player):
        self.player = player

    def _recalc_layout(self):
        W = self.tela.get_width()
        H = self.tela.get_height()

        x = MARGIN
        y = H - BOTTOM_BANK_H + 18
        w = W - RIGHT_PANEL_W - 2 * MARGIN
        h = BOTTOM_BANK_H - 36
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))

    def _cartas_atuais(self):
        # mantém a ordem dos slots (da esquerda p direita)
        return [c for c in self.slots if c is not None]

    def _rebuild_slot_rects_for_n(self, n_cards: int):
        """
        Cria rects APENAS para n_cards (não mostra 12 buracos fixos).
        Não sobrepõe se couber; sobrepõe só se precisar.
        """
        self.slot_rects.clear()

        n = max(0, int(n_cards))
        if n == 0:
            return

        preferred_step = BANK_CARD_W + BANK_GAP

        if n == 1:
            step = 0
        else:
            max_step = (self.rect.w - BANK_CARD_W) / (n - 1)
            if max_step >= preferred_step:
                step = preferred_step
            else:
                step = max_step
                step = max(step, 46)

        total_w = BANK_CARD_W + (n - 1) * step
        start_x = self.rect.x + (self.rect.w - total_w) / 2
        y = self.rect.y + (self.rect.h - BANK_CARD_H) // 2

        for i in range(n):
            x = int(start_x + i * step)
            self.slot_rects.append(pygame.Rect(x, y, BANK_CARD_W, BANK_CARD_H))

    def recompactar(self):
        """
        Junta cartas pra esquerda (mantendo ordem) e reatribui bank_index.
        Depois recalcula rects e aplica nos cartuchos.
        """
        cartas = self._cartas_atuais()

        self.slots = [None] * self.slots_n
        for i, c in enumerate(cartas):
            self.slots[i] = c
            c.bank_index = i
            c.location = "banco"

        self._rebuild_slot_rects_for_n(len(cartas))

        for i, c in enumerate(cartas):
            if i < len(self.slot_rects):
                c.set_location_bank(i, self.slot_rects[i])

    def add_to_first_free(self, cartucho):
        idx = None
        for i in range(self.slots_n):
            if self.slots[i] is None:
                idx = i
                break
        if idx is None:
            return False

        self.slots[idx] = cartucho
        cartucho.location = "banco"
        cartucho.bank_index = idx
        cartucho.grid_pos = None

        self.recompactar()
        return True

    def return_to_slot(self, cartucho):
        """
        Volta pro banco e depois recompata (pra preencher buracos).
        """
        idx = cartucho.bank_index
        if idx is None:
            return self.add_to_first_free(cartucho)

        idx = clamp(idx, 0, self.slots_n - 1)
        if self.slots[idx] is None:
            self.slots[idx] = cartucho
        else:
            return self.add_to_first_free(cartucho)

        cartucho.location = "banco"
        cartucho.bank_index = idx
        cartucho.grid_pos = None

        self.recompactar()
        return True

    def pick_at_pos(self, mouse_pos):
        """
        Retira do banco (pra arrastar) e recompata o resto.
        Importante: cheque do fim pro começo (carta de cima “ganha”).
        """
        self.recompactar()
        cartas = self._cartas_atuais()

        for i in range(len(cartas) - 1, -1, -1):
            c = cartas[i]
            if c is None:
                continue
            if c.rect.collidepoint(mouse_pos):
                bi = c.bank_index
                if bi is not None and 0 <= bi < self.slots_n:
                    self.slots[bi] = None
                c.bank_index = bi
                self.recompactar()
                return c
        return None

    def _compute_hover(self, mouse_pos):
        self._hover_idx = None
        cartas = self._cartas_atuais()
        for i in range(len(cartas) - 1, -1, -1):
            c = cartas[i]
            if c and (not c.dragging) and c.rect.collidepoint(mouse_pos):
                self._hover_idx = i
                break

    def draw(self, surf, font_title):
        self._recalc_layout()
        self.recompactar()

        draw_round_rect(surf, BANK_BG, self.rect, 0, 14)
        draw_round_rect(surf, BANK_BORDER, self.rect, 3, 14)

        title = font_title.render("BANCO", True, TEXT)
        surf.blit(title, (self.rect.x + 14, self.rect.y - 30))

        mouse_pos = pygame.mouse.get_pos()
        self._compute_hover(mouse_pos)

        # dt para animação suave do hover
        now = pygame.time.get_ticks()
        if self._last_ms is None:
            self._last_ms = now
        dt = max(0.0, (now - self._last_ms) / 1000.0)
        self._last_ms = now

        target_scale = HOVER_SCALE if (self._hover_idx is not None) else 1.0
        self._hover_scale = _exp_smooth(self._hover_scale, target_scale, dt, HOVER_SMOOTH_SPEED)

        cartas = self._cartas_atuais()

        # desenha fundo “slots” apenas onde tem carta
        for i, c in enumerate(cartas):
            sr = self.slot_rects[i]
            draw_round_rect(surf, (12, 12, 16), sr, 0, 12)
            draw_round_rect(surf, (40, 40, 50), sr, 2, 12)

        # desenha TODAS exceto a hover
        for i, c in enumerate(cartas):
            if c is None or c.dragging:
                continue
            if i == self._hover_idx:
                continue
            c.set_rect(self.slot_rects[i])
            c.draw(surf, font_title, self._fonte_carac, compact=False)

        # desenha hover por último e ampliada (por cima) — agora animada
        if self._hover_idx is not None and 0 <= self._hover_idx < len(cartas):
            c = cartas[self._hover_idx]
            if c and (not c.dragging):
                base = self.slot_rects[self._hover_idx]

                scale = self._hover_scale
                scaled_w = int(round(base.w * scale))
                scaled_h = int(round(base.h * scale))
                scaled = pygame.Rect(0, 0, scaled_w, scaled_h)
                scaled.center = base.center
                scaled.y -= int(round(HOVER_RAISE * ((scale - 1.0) / (HOVER_SCALE - 1.0) if HOVER_SCALE > 1.0 else 1.0)))

                old = c.rect.copy()
                c.set_rect(scaled)
                c.draw(surf, font_title, self._fonte_carac, compact=False)
                c.set_rect(old)
