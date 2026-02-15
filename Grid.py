# Grid.py
import pygame
import math
import colorsys
import os

from Painel_Personagem import draw_painel_personagem
from Brawl_Stars.Brawl import gerar_imagem_cartucho_grid


# ============================================================
# CONFIG
# ============================================================
GRID_COLS = 10
GRID_ROWS = 10

CELL_W = 80
CELL_H = 60

RIGHT_PANEL_W = 280
BOTTOM_BANK_H = 210
MARGIN = 26

BG = (14, 14, 18)

GRID_LINE = (95, 95, 115)
GRID_LINE_ALPHA = 90
GRID_BORDER = (110, 110, 130)

HOVER_BAD = (235, 70, 70)
PLACE_YELLOW = (255, 230, 120)

SYNERGY_STROKE = 9

# ZOOM (simples, sempre centraliza)
ZOOM_MIN = 0.65
ZOOM_MAX = 1.85
ZOOM_STEP = 1.12

# ============================================================
# HELPERS
# ============================================================
def _norm_sym(x) -> str:
    return str(x).strip().lower()

def _get_syms(cartucho):
    raw = getattr(cartucho, "sinergias", None) or getattr(cartucho, "synergies", []) or []
    return [_norm_sym(s) for s in raw]

def _blink_strength(ms: int, period_ms: int = 520) -> float:
    t = (ms % period_ms) / period_ms
    return 0.5 - 0.5 * math.cos(t * math.tau)

def draw_glow_rect(surf, rect, color, strength=1.0):
    s = max(0.0, min(1.0, strength))
    for i in range(5):
        alpha = int(26 * s) + (4 - i) * int(18 * s)
        if alpha <= 0:
            continue
        glow = pygame.Surface((rect.w + i * 8, rect.h + i * 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color, alpha), glow.get_rect(), border_radius=10)
        surf.blit(glow, (rect.x - i * 4, rect.y - i * 4))


# ============================================================
# CORES POR SINERGIA (MESMO ALGORITMO DO PAINEL)
# ============================================================
def _color_for_synergy(sym: str, cache: dict):
    s = _norm_sym(sym)
    if s in cache:
        return cache[s]
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    hue = (h % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.60, 1.00)
    col = (int(r * 255), int(g * 255), int(b * 255))
    cache[s] = col
    return col


# ============================================================
# GRID
# ============================================================
class Grid:
    """
    REGRAS:
      - Grid imaginária (divisórias só quando arrasta)
      - 1º cartucho livre
      - Depois: adjacente a 1+ ocupado e conecta com TODOS os vizinhos adjacentes
      - Retas (sem L): sinergia ativa só se já foi usada numa conexão real
      - 1 reta (row/col) pode pertencer a APENAS 1 sinergia
    """
    def __init__(self, tela):
        self.tela = tela
        self.cols, self.rows = GRID_COLS, GRID_ROWS

        self.base_cell = int(min(CELL_W, CELL_H))
        self.zoom = 1.0
        self.cell_w = self.cell_h = self.base_cell

        self.occ = {}  # (c,r) -> Cartucho
        self.origin = (0, 0)
        self._recalc_layout()

        self.banco = self.loja = self.painel_sinergia = None
        self.dragging = None

        # NOVO: referência opcional ao PlayerEstrategista (para painel e futuras migrações)
        self.player = None

        self.fonte_path = os.path.join("Fontes", "FontePadrão.ttf")
        self.fonte_titulo = pygame.font.Font(self.fonte_path, 28)
        self.fonte_item   = pygame.font.Font(self.fonte_path, 20)
        self.fonte_nome   = pygame.font.Font(self.fonte_path, 20)
        self.fonte_carac  = pygame.font.Font(self.fonte_path, 15)
        self.fonte_hover_titulo = pygame.font.Font(self.fonte_path, 20)
        self.fonte_hover_txt = pygame.font.Font(self.fonte_path, 16)
        self.fonte_hover_micro = pygame.font.Font(self.fonte_path, 14)

        self._valid_cells = set()
        self._active_cache = None
        self._active_cache_tick = -1

        # ---------------- flag para recalcular stats do campo
        self.campo_dirty = True

        # ---------------- cores dinâmicas das sinergias (estáveis)
        self._syn_color_cache = {}

        # arrasto de dado (da grade para a ficha do player)
        self.dragging_dado = None
        self._dragging_dado_icon = None

    # ---------------- API para a Tela_Estrategista / Player
    def get_cartuchos_em_campo(self):
        return list(self.occ.values())

    def remove_at(self, c, r):
        if (c, r) in self.occ:
            del self.occ[(c, r)]
            self.campo_dirty = True

    # ---------------- refs / layout ----------------
    def set_refs(self, banco, loja, painel_sinergia, player=None):
        self.banco, self.loja, self.painel_sinergia = banco, loja, painel_sinergia
        if player is not None:
            self.player = player

    def _ui_rects(self):
        W, H = self.tela.get_width(), self.tela.get_height()
        right = pygame.Rect(W - RIGHT_PANEL_W - MARGIN, MARGIN, RIGHT_PANEL_W, H - 2 * MARGIN)
        bottom = pygame.Rect(MARGIN, H - BOTTOM_BANK_H - MARGIN, W - 2 * MARGIN, BOTTOM_BANK_H)
        return right, bottom

    def _can_zoom_here(self, mouse_pos):
        right, bottom = self._ui_rects()
        return not (right.collidepoint(mouse_pos) or bottom.collidepoint(mouse_pos))

    def _apply_zoom_centered(self, direction: int):
        old = self.zoom
        if direction > 0:
            self.zoom = min(ZOOM_MAX, self.zoom * ZOOM_STEP)
        else:
            self.zoom = max(ZOOM_MIN, self.zoom / ZOOM_STEP)
        if abs(self.zoom - old) < 1e-6:
            return
        self.cell_w = self.cell_h = max(8, int(self.base_cell * self.zoom))
        self._recalc_layout()

    def _recalc_layout(self):
        W, H = self.tela.get_width(), self.tela.get_height()
        grid_w, grid_h = self.cols * self.cell_w, self.rows * self.cell_h
        area_w = W - RIGHT_PANEL_W - 2 * MARGIN
        area_h = H - BOTTOM_BANK_H - 2 * MARGIN
        self.origin = (int(MARGIN + (area_w - grid_w) // 2), int(MARGIN + (area_h - grid_h) // 2))

    # ---------------- geometry ----------------
    def rect(self):
        x, y = self.origin
        return pygame.Rect(x, y, self.cols * self.cell_w, self.rows * self.cell_h)

    def cell_rect(self, c, r):
        x, y = self.origin
        return pygame.Rect(x + c * self.cell_w, y + r * self.cell_h, self.cell_w, self.cell_h)

    def in_cell(self, pos):
        gr = self.rect()
        if not gr.collidepoint(pos):
            return None
        mx, my = pos
        return int((mx - gr.x) // self.cell_w), int((my - gr.y) // self.cell_h)

    def neighbors4(self, c, r):
        for dc, dr in ((1,0), (-1,0), (0,1), (0,-1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                yield (nc, nr)

    # ---------------- active synergies ----------------
    def _active_synergy_positions(self):
        pos = {}
        for (c, r), a in self.occ.items():
            sa = set(_get_syms(a))
            for (dc, dr) in ((1, 0), (0, 1)):
                b = self.occ.get((c + dc, r + dr))
                if not b:
                    continue
                for s in (sa & set(_get_syms(b))):
                    st = pos.setdefault(s, set())
                    st.add((c, r))
                    st.add((c + dc, r + dr))
        return pos

    def _get_active_cached(self, tick_ms: int):
        if self._active_cache_tick == tick_ms and self._active_cache is not None:
            return self._active_cache
        self._active_cache_tick = tick_ms
        self._active_cache = self._active_synergy_positions()
        return self._active_cache

    def _line_ok(self, existing: set, new_cell):
        if not existing:
            return True
        nc, nr = new_cell
        if len(existing) == 1:
            c0, r0 = next(iter(existing))
            return nr == r0 or nc == c0
        rows = {r for _, r in existing}
        cols = {c for c, _ in existing}
        if len(rows) == 1:
            return nr == next(iter(rows))
        if len(cols) == 1:
            return nc == next(iter(cols))
        return False

    def _line_owners(self, active_pos: dict):
        owners = {}
        for s, positions in active_pos.items():
            if not positions or len(positions) < 2:
                continue
            rows = {r for _, r in positions}
            cols = {c for c, _ in positions}
            if len(rows) == 1:
                owners[("H", next(iter(rows)))] = s
            elif len(cols) == 1:
                owners[("V", next(iter(cols)))] = s
        return owners

    def _conn_line_key(self, c, r, nc, nr):
        if nr == r:
            return ("H", r)
        return ("V", c)

    def _line_free_for(self, owners: dict, key, synergy: str):
        cur = owners.get(key)
        return (cur is None) or (cur == synergy)

    def _tipo_dado_para_attr(self, tipo: str):
        t = str(tipo or "").strip().lower()
        return {
            "atk": "dano_fisico",
            "spa": "dano_magico",
            "def": "defesa_fisica",
            "spd": "defesa_magica",
            "reg": "regeneracao",
            "man": "mana",
            "vel": "velocidade",
            "per": "penetracao",
        }.get(t)

    def _pick_dado_cartucho_grid(self, mouse_pos):
        cell = self.in_cell(mouse_pos)
        if not cell:
            return None
        cartucho = self.occ.get(cell)
        if not cartucho:
            return None
        tipo = str(getattr(cartucho, "tipo_dado", "") or "").strip().lower()
        attr = self._tipo_dado_para_attr(tipo)
        if not attr:
            return None
        faces = list(getattr(cartucho, "dado", []) or [])
        if not faces:
            return None
        return {"cartucho": cartucho, "attr": attr, "tipo": tipo, "faces": faces}

    # ---------------- placement rules ----------------
    def can_place(self, cartucho, c, r):
        if not (0 <= c < self.cols and 0 <= r < self.rows) or (c, r) in self.occ:
            return False

        # Impede duplicar o mesmo personagem no campo.
        new_id = str(getattr(cartucho, "id", "") or "").strip().lower()
        new_nome = str(getattr(cartucho, "nome", "") or "").strip().lower()
        for existente in self.occ.values():
            ex_id = str(getattr(existente, "id", "") or "").strip().lower()
            ex_nome = str(getattr(existente, "nome", "") or "").strip().lower()
            if (new_id and ex_id == new_id) or (new_nome and ex_nome == new_nome):
                return False

        if not self.occ:
            return True

        s_new = _get_syms(cartucho)
        if not s_new:
            return False

        neighbor_cells = [(nc, nr) for (nc, nr) in self.neighbors4(c, r) if (nc, nr) in self.occ]
        if not neighbor_cells:
            return False

        active = self._active_synergy_positions()
        owners = self._line_owners(active)

        for (nc, nr) in neighbor_cells:
            other = self.occ[(nc, nr)]
            shared = set(s_new) & set(_get_syms(other))
            if not shared:
                return False

            key = self._conn_line_key(c, r, nc, nr)

            ok = False
            for s in shared:
                if not self._line_free_for(owners, key, s):
                    continue
                if (s not in active) or self._line_ok(active[s], (c, r)):
                    ok = True
                    break
            if not ok:
                return False

        return True

    def place(self, cartucho, c, r):
        self.occ[(c, r)] = cartucho
        cartucho.set_location_grid(c, r, self.cell_rect(c, r))
        self.campo_dirty = True

    # ---------------- events ----------------
    def _recompute_valid_cells(self):
        self._valid_cells.clear()
        if not self.dragging:
            return
        for rr in range(self.rows):
            for cc in range(self.cols):
                if self.can_place(self.dragging, cc, rr):
                    self._valid_cells.add((cc, rr))

    def _handle_events(self, events, mouse_pos):
        if not (self.banco and self.loja and self.painel_sinergia):
            return

        for e in events:
            if e.type == pygame.MOUSEWHEEL and self._can_zoom_here(mouse_pos):
                if e.y > 0:
                    self._apply_zoom_centered(+1)
                elif e.y < 0:
                    self._apply_zoom_centered(-1)
                continue

            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button in (4, 5) and self._can_zoom_here(mouse_pos):
                    self._apply_zoom_centered(+1 if e.button == 4 else -1)
                    continue

                if e.button == 1:
                    dado_pick = self._pick_dado_cartucho_grid(mouse_pos)
                    if dado_pick is not None:
                        self.dragging_dado = dado_pick
                        cartucho = dado_pick.get("cartucho")
                        self._dragging_dado_icon = gerar_imagem_cartucho_grid(getattr(cartucho, "dados", {}) or {}, (42, 42))
                        if self.player is not None and hasattr(self.player, "set_dado_drag_preview"):
                            self.player.set_dado_drag_preview(dado_pick)
                        continue

                    if self.loja.btn_reroll.collidepoint(mouse_pos):
                        self.loja.handle_click(mouse_pos)
                        continue

                    # Compra direta da loja para o banco
                    if any(s is None for s in self.banco.slots):
                        bought = self.loja.pick_at_pos(mouse_pos)
                        if bought is not None:
                            self.banco.add_to_first_free(bought)
                            self.campo_dirty = True
                            continue

                    picked = self.banco.pick_at_pos(mouse_pos)
                    if picked:
                        self.dragging = picked
                        self.dragging.start_drag(mouse_pos)
                        self._recompute_valid_cells()

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if self.dragging_dado is not None:
                    if self.player is not None and hasattr(self.player, "drop_dado_em_attr"):
                        self.player.drop_dado_em_attr(mouse_pos, self.dragging_dado)
                    self.dragging_dado = None
                    self._dragging_dado_icon = None
                    if self.player is not None and hasattr(self.player, "set_dado_drag_preview"):
                        self.player.set_dado_drag_preview(None)
                    continue

                if self.dragging:
                    if self.loja.sell_drop_here(mouse_pos):
                        self.dragging.stop_drag()
                        sell_value = 0
                        if hasattr(self.loja, "sell_value_for_cartucho"):
                            sell_value = self.loja.sell_value_for_cartucho(self.dragging)
                        if hasattr(self.loja, "player") and self.loja.player is not None:
                            self.loja.player.ouro = getattr(self.loja.player, "ouro", 0) + sell_value
                        self.loja.deck_defs.append(self.dragging.to_def())
                        self.dragging = None
                        self._valid_cells.clear()
                        self.campo_dirty = True
                        continue

                    cell = self.in_cell(mouse_pos)
                    if cell and self.can_place(self.dragging, *cell):
                        self.place(self.dragging, *cell)
                        self.dragging.stop_drag()
                        self.dragging = None
                        self._valid_cells.clear()
                    else:
                        self.dragging.stop_drag()
                        self.banco.return_to_slot(self.dragging)
                        self.dragging = None
                        self._valid_cells.clear()

            elif e.type == pygame.MOUSEMOTION:
                if self.dragging:
                    self.dragging.drag_update(mouse_pos)

    # ---------------- draw ----------------
    def _draw_grid_base(self, surf):
        pygame.draw.rect(surf, GRID_BORDER, self.rect(), 3)

    def _draw_grid_dividers(self, surf):
        gr = self.rect()
        overlay = pygame.Surface((gr.w, gr.h), pygame.SRCALPHA)
        for c in range(1, self.cols):
            x = c * self.cell_w
            pygame.draw.line(overlay, (*GRID_LINE, GRID_LINE_ALPHA), (x, 0), (x, gr.h), 2)
        for r in range(1, self.rows):
            y = r * self.cell_h
            pygame.draw.line(overlay, (*GRID_LINE, GRID_LINE_ALPHA), (0, y), (gr.w, y), 2)
        surf.blit(overlay, (gr.x, gr.y))

    # ============================
    # CONTORNO "ELÁSTICO" COMO NA IMAGEM:
    # - cada sinergia desenha APENAS o perímetro externo (sem linhas internas)
    # - se uma célula tem 2 sinergias, terá 2 contornos sobrepostos (um por sinergia)
    # - quando sobrepõe, é literalmente um desenho por cima do outro (sem mesclar/split)
    # ============================
    def _components_4(self, cells: set):
        visited = set()
        comps = []
        for start in cells:
            if start in visited:
                continue
            stack = [start]
            visited.add(start)
            comp = {start}
            while stack:
                c, r = stack.pop()
                for nc, nr in self.neighbors4(c, r):
                    if (nc, nr) in cells and (nc, nr) not in visited:
                        visited.add((nc, nr))
                        stack.append((nc, nr))
                        comp.add((nc, nr))
            comps.append(comp)
        return comps

    def _perimeter_edges(self, comp: set):
        edges = []
        for (c, r) in comp:
            rect = self.cell_rect(c, r)
            x1, y1, x2, y2 = rect.left, rect.top, rect.right, rect.bottom

            if (c, r - 1) not in comp: edges.append((x1, y1, x2, y1))  # top
            if (c, r + 1) not in comp: edges.append((x1, y2, x2, y2))  # bottom
            if (c - 1, r) not in comp: edges.append((x1, y1, x1, y2))  # left
            if (c + 1, r) not in comp: edges.append((x2, y1, x2, y2))  # right

        return edges

    def _draw_synergy_outlines(self, surf, active_pos: dict, agora_ms: int, hovered_synergy: str | None = None):
        if not active_pos:
            return

        thick = SYNERGY_STROKE
        rad = max(2, thick // 2)

        # ordem estável para sobreposição previsível
        items = sorted(active_pos.items(), key=lambda kv: kv[0])

        hover_pulse = 0.78 + 0.28 * _blink_strength(agora_ms, period_ms=640)

        non_hover = []
        hover_item = None
        for sym, pos_set in items:
            if hovered_synergy is not None and _norm_sym(sym) == _norm_sym(hovered_synergy):
                hover_item = (sym, pos_set)
            else:
                non_hover.append((sym, pos_set))

        draw_order = non_hover + ([hover_item] if hover_item else [])

        for sym, pos_set in draw_order:
            if not pos_set:
                continue
            color = _color_for_synergy(sym, self._syn_color_cache)
            is_hover = hovered_synergy is not None and _norm_sym(sym) == _norm_sym(hovered_synergy)
            draw_thick = thick + 4 if is_hover else thick
            draw_color = (
                min(255, int(color[0] * hover_pulse)),
                min(255, int(color[1] * hover_pulse)),
                min(255, int(color[2] * hover_pulse)),
            ) if is_hover else color

            for comp in self._components_4(set(pos_set)):
                for (x1, y1, x2, y2) in self._perimeter_edges(comp):
                    pygame.draw.line(surf, draw_color, (x1, y1), (x2, y2), draw_thick)
                    pygame.draw.circle(surf, draw_color, (x1, y1), max(2, draw_thick // 2))
                    pygame.draw.circle(surf, draw_color, (x2, y2), max(2, draw_thick // 2))

    def _draw_placed_cartuchos(self, surf):
        for (c, r), cartucho in self.occ.items():
            if cartucho.dragging:
                continue
            cartucho.set_rect(self.cell_rect(c, r))
        for cartucho in self.occ.values():
            cartucho.draw(surf, self.fonte_nome, self.fonte_carac, compact=True)

    def _draw_highlights(self, surf, mouse_pos, agora_ms: int):
        if not self.dragging:
            return

        self._draw_grid_dividers(surf)

        blink = _blink_strength(agora_ms)
        glow_strength = 0.35 + 0.65 * blink

        for (c, r) in self._valid_cells:
            rect = self.cell_rect(c, r)
            draw_glow_rect(surf, rect, PLACE_YELLOW, strength=glow_strength)
            pygame.draw.rect(surf, PLACE_YELLOW, rect, 3)

        cell = self.in_cell(mouse_pos)
        if cell:
            rect = self.cell_rect(*cell)
            pygame.draw.rect(surf, PLACE_YELLOW if cell in self._valid_cells else HOVER_BAD, rect, 5)

    def _draw_banco(self, surf):
        self.banco.draw(surf, self.fonte_titulo)

    def _draw_right_panel(self, surf):
        self.painel_sinergia.draw(surf, self.fonte_titulo, self.fonte_item, self.occ, player=self.player)
        self.loja.draw(surf, self.fonte_titulo, self.fonte_item,
                       fonte_nome=self.fonte_item, fonte_carac=self.fonte_carac)

    def _draw_dragging(self, surf, mouse_pos):
        if not self.dragging:
            return
        cell = self.in_cell(mouse_pos)
        hl = PLACE_YELLOW if (cell and self.can_place(self.dragging, *cell)) else (HOVER_BAD if cell else None)
        self.dragging.draw(surf, self.fonte_nome, self.fonte_carac, highlight=hl, compact=False)



    def _draw_dragging_dado(self, surf, mouse_pos):
        if not self.dragging_dado:
            return
        cartucho = self.dragging_dado.get("cartucho")
        if not cartucho:
            return

        if self._dragging_dado_icon is None:
            self._dragging_dado_icon = gerar_imagem_cartucho_grid(getattr(cartucho, "dados", {}) or {}, (42, 42))

        icon = self._dragging_dado_icon
        box = icon.get_rect(center=(mouse_pos[0] + 18, mouse_pos[1] + 8))
        glow = box.inflate(10, 10)
        pygame.draw.rect(surf, (255, 255, 255), glow, 1, border_radius=6)
        surf.blit(icon, box)

    
    def _all_visible_cartuchos(self):
        cards = []

        for c in self.occ.values():
            if not getattr(c, "dragging", False):
                cards.append(c)

        for c in getattr(self.loja, "cartuchos", []):
            if c is not None and not getattr(c, "dragging", False):
                cards.append(c)

        for c in getattr(self.banco, "slots", []):
            if c is not None and not getattr(c, "dragging", False):
                cards.append(c)

        return cards

    def _hovered_cartucho(self, mouse_pos):
        for c in reversed(self._all_visible_cartuchos()):
            if c.rect.collidepoint(mouse_pos):
                return c
        return None

    def _draw_hover_ficha(self, surf, cartucho):
        if cartucho is None:
            return

        if not (self.banco and self.loja):
            return

        panel_w, panel_h = 420, 220
        x = self.loja.rect.x - panel_w - 14
        y = self.banco.rect.y - panel_h - 8
        x = max(10, x)
        y = max(10, y)
        panel = pygame.Rect(x, y, panel_w, panel_h)

        draw_painel_personagem(
            surf,
            panel,
            cartucho,
            {
                "titulo": self.fonte_hover_titulo,
                "txt": self.fonte_hover_txt,
                "micro": self.fonte_hover_micro,
            },
        )

    # ---------------- main ----------------
    def update(self, events, agora, mouse_pos):
        self._handle_events(events, mouse_pos)
        self._recalc_layout()

        if self.dragging:
            self._recompute_valid_cells()

        self.tela.fill(BG)
        self._draw_grid_base(self.tela)

        self._draw_banco(self.tela)
        self._draw_right_panel(self.tela)

        active = self._get_active_cached(agora)
        hovered = getattr(self.painel_sinergia, "hovered_synergy", None) if self.painel_sinergia else None
        self._draw_synergy_outlines(self.tela, active, agora, hovered)

        self._draw_placed_cartuchos(self.tela)
        self._draw_highlights(self.tela, mouse_pos, agora)
        self._draw_dragging(self.tela, mouse_pos)
        self._draw_dragging_dado(self.tela, mouse_pos)
        hovered_cartucho = self._hovered_cartucho(mouse_pos)
        self._draw_hover_ficha(self.tela, hovered_cartucho)
