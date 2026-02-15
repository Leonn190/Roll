# Cartucho.py
import os
import pygame
from Brawl_Stars.Brawl import gerar_imagem_cartucho, gerar_imagem_cartucho_grid

BORDA_PADRAO = (18, 18, 22)
STAR_ICON_PATH = os.path.join("Recursos", "Visual", "Icones", "estrela.png")
_STAR_ICON_CACHE = {}


def _get_star_icon(size: int):
    size = max(8, int(size))
    if size in _STAR_ICON_CACHE:
        return _STAR_ICON_CACHE[size]
    try:
        icon = pygame.image.load(STAR_ICON_PATH).convert_alpha()
        icon = pygame.transform.smoothscale(icon, (size, size))
    except Exception:
        icon = None
    _STAR_ICON_CACHE[size] = icon
    return icon

def _retangulo_arredondado(surf, cor, rect, esp=0, raio=12):
    pygame.draw.rect(surf, cor, rect, esp, border_radius=raio)

class Cartucho:
    def __init__(self, dados: dict, w: int, h: int):
        # guarda tudo que veio
        self.dados = dict(dados)

        # campos "fixos" e fáceis de acessar
        self.id = str(self.dados.get("id", "")).strip()
        self.nome = str(self.dados.get("nome", "???")).strip()
        self.raridade = str(self.dados.get("raridade", "comum")).strip().lower()
        self.imagem = str(self.dados.get("imagem", "")).strip()

        # stats (sempre dict)
        st = self.dados.get("stats", {})
        self.stats = dict(st) if isinstance(st, dict) else {}

        self.tipo_dado = str(self.dados.get("tipo_dado", "")).strip()
        self.descricao = str(self.dados.get("descricao", "")).strip()
        dado = self.dados.get("dado", [])
        if isinstance(dado, (list, tuple)):
            self.dado = [int(x) for x in dado if str(x).strip()]
        else:
            self.dado = []

        # sinergias (cacheadas e limpas)
        car = self.dados.get("características", [])
        if isinstance(car, (list, tuple)):
            self._sinergias = [str(x).strip() for x in car if str(x).strip()]
        else:
            self._sinergias = []

        self.rect = pygame.Rect(0, 0, w, h)

        self.location = "banco"  # "banco" | "grid" | "loja"
        self.bank_index = None
        self.grid_pos = None

        self.dragging = False
        self.drag_off = (0, 0)

        # evolução por sobreposição de cópias na grid
        self.estrelas = 0

    @property
    def estrelas_visiveis(self) -> int:
        return max(0, min(3, int(getattr(self, "estrelas", 0) or 0)))

    # --- acesso rápido ---
    @property
    def sinergias(self) -> list[str]:
        return list(self._sinergias)

    def get_stat(self, key: str, default=0):
        v = self.stats.get(key, None)
        if v is None or v == "":
            return default
        try:
            return int(v)
        except (ValueError, TypeError):
            return default

    def to_def(self):
        # devolve tudo (inclui stats etc.)
        return dict(self.dados)

    # Drag
    def start_drag(self, mouse_pos):
        self.dragging = True
        mx, my = mouse_pos
        self.drag_off = (mx - self.rect.x, my - self.rect.y)

    def drag_update(self, mouse_pos):
        if not self.dragging:
            return
        mx, my = mouse_pos
        ox, oy = self.drag_off
        self.rect.x = mx - ox
        self.rect.y = my - oy

    def stop_drag(self):
        self.dragging = False

    # Posição
    def set_rect(self, rect: pygame.Rect):
        self.rect = rect.copy()

    def set_location_bank(self, idx: int, slot_rect: pygame.Rect):
        self.location = "banco"
        self.bank_index = idx
        self.grid_pos = None
        self.set_rect(slot_rect)

    def set_location_shop(self, slot_rect: pygame.Rect):
        self.location = "loja"
        self.bank_index = None
        self.grid_pos = None
        self.set_rect(slot_rect)

    def set_location_grid(self, c: int, r: int, rect_in_grid: pygame.Rect):
        self.location = "grid"
        self.grid_pos = (c, r)
        self.bank_index = None
        self.set_rect(rect_in_grid)

    # Draw
    def draw(self, surf, fonte_nome, fonte_carac, *, highlight=None, compact=False):
        r = self.rect

        if compact:
            # GRID = só imagem do brawler (sem nome/sem características)
            img = gerar_imagem_cartucho_grid(self.dados, (r.w, r.h))
            surf.blit(img, r.topleft)

            stars = self.estrelas_visiveis
            if stars > 0:
                icon_size = max(14, min(22, r.w // 4))
                total_w = stars * icon_size + (stars - 1) * 2
                x0 = r.x + (r.w - total_w) // 2
                y0 = r.bottom - icon_size - 2
                icon = _get_star_icon(icon_size)
                for i in range(stars):
                    xx = x0 + i * (icon_size + 2)
                    if icon is not None:
                        surf.blit(icon, (xx, y0))
                    else:
                        fallback = fonte_carac.render("★", True, (255, 240, 140))
                        surf.blit(fallback, fallback.get_rect(center=(xx + icon_size // 2, y0 + icon_size // 2)))

            if highlight:
                _retangulo_arredondado(surf, highlight, r, 3, 10)
            return

        # BANCO/LOJA = cartucho estilo draft completo
        img = gerar_imagem_cartucho(self.dados, (r.w, r.h), fonte_nome, fonte_carac)
        surf.blit(img, r.topleft)

        if highlight:
            _retangulo_arredondado(surf, highlight, r, 4, 12)
