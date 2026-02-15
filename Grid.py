# Grid.py
import pygame
import math
import colorsys

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
# CORES POR SINERGIA (SEM PREDEFINIÇÃO)
# - geradas "na hora", mas estáveis e diferentes entre si
# ============================================================
def _hash32(s: str) -> int:
    # FNV-1a 32-bit (determinístico)
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h

def _hue_dist(a: float, b: float) -> float:
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)

def _color_from_hue(hue: float):
    r, g, b = colorsys.hsv_to_rgb(hue % 1.0, 0.70, 1.00)
    return (int(r * 255), int(g * 255), int(b * 255))

def _assign_distinct_hue(base_hue: float, used_hues: list[float], min_dist: float = 0.10) -> float:
    # tenta manter bem diferente das já usadas; gira por golden ratio se necessário
    hue = base_hue % 1.0
    if not used_hues:
        return hue
    golden = 0.61803398875
    for _ in range(40):
        if all(_hue_dist(hue, uh) >= min_dist for uh in used_hues):
            return hue
        hue = (hue + golden) % 1.0
    return hue

def _color_for_synergy(sym: str, cache: dict, used_hues: list):
    s = _norm_sym(sym)
    if s in cache:
        return cache[s]
    h = _hash32(s)
    base_hue = (h % 360) / 360.0
    hue = _assign_distinct_hue(base_hue, used_hues, min_dist=0.12)
    used_hues.append(hue)
    col = _color_from_hue(hue)
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

        self.fonte_titulo = pygame.font.SysFont(None, 34, bold=True)
        self.fonte_item   = pygame.font.SysFont(None, 26, bold=True)
        self.fonte_nome   = pygame.font.SysFont(None, 22, bold=True)
        self.fonte_carac  = pygame.font.SysFont(None, 18, bold=True)

        self._valid_cells = set()
        self._active_cache = None
        self._active_cache_tick = -1

        # ---------------- flag para recalcular stats do campo
        self.campo_dirty = True

        # ---------------- cores dinâmicas das sinergias (estáveis)
        self._syn_color_cache = {}

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

    # ---------------- placement rules ----------------
    def can_place(self, cartucho, c, r):
        if not (0 <= c < self.cols and 0 <= r < self.rows) or (c, r) in self.occ:
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

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging:
                if self.loja.sell_drop_here(mouse_pos):
                    self.dragging.stop_drag()
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

            elif e.type == pygame.MOUSEMOTION and self.dragging:
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

    def _draw_synergy_outlines(self, surf, active_pos: dict):
        if not active_pos:
            return

        thick = SYNERGY_STROKE
        rad = max(2, thick // 2)

        # garante cores "diferentes" no runtime (sem tabela fixa)
        used_hues = []
        # ordem estável (e previsível) — importante pra sobreposição parecer consistente
        items = sorted(active_pos.items(), key=lambda kv: kv[0])

        for sym, pos_set in items:
            if not pos_set:
                continue
            color = _color_for_synergy(sym, self._syn_color_cache, used_hues)

            for comp in self._components_4(set(pos_set)):
                for (x1, y1, x2, y2) in self._perimeter_edges(comp):
                    pygame.draw.line(surf, color, (x1, y1), (x2, y2), thick)
                    pygame.draw.circle(surf, color, (x1, y1), rad)
                    pygame.draw.circle(surf, color, (x2, y2), rad)

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
        for c in self.banco.slots:
            if c and c is not self.dragging:
                c.draw(surf, self.fonte_nome, self.fonte_carac, compact=False)

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

    # ---------------- main ----------------
    def update(self, events, agora, mouse_pos):
        self._handle_events(events, mouse_pos)
        self._recalc_layout()

        if self.dragging:
            self._recompute_valid_cells()

        self.tela.fill(BG)
        self._draw_grid_base(self.tela)

        active = self._get_active_cached(agora)
        self._draw_synergy_outlines(self.tela, active)

        self._draw_placed_cartuchos(self.tela)
        self._draw_highlights(self.tela, mouse_pos, agora)
        self._draw_banco(self.tela)
        self._draw_right_panel(self.tela)
        self._draw_dragging(self.tela, mouse_pos)
