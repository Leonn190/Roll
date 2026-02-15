import pygame
import os
import math
from Brawl_Stars.Brawl import gerar_imagem_cartucho_grid

ATRIBUTOS = [
    "dano_fisico",
    "dano_magico",
    "defesa_fisica",
    "defesa_magica",
    "regeneracao",
    "mana",
    "velocidade",
    "penetracao",
]

DICE_TYPES = {
    "dano_fisico":   (255, 140,  40),
    "dano_magico":   (175,  70, 255),
    "defesa_fisica": (255, 210,  70),
    "defesa_magica": (120, 215, 255),
    "regeneracao":   ( 80, 220, 120),
    "mana":          ( 40,  85, 220),
    "velocidade":    (170, 170, 170),
    "penetracao":    (235,  70,  70),
}

LABELS = {
    "dano_fisico": "Dano Físico",
    "dano_magico": "Dano Mágico",
    "defesa_fisica": "Defesa Fís.",
    "defesa_magica": "Defesa Mág.",
    "regeneracao": "Regeneração",
    "mana": "Mana",
    "velocidade": "Velocidade",
    "penetracao": "Penetração",
}

PERCENT_LABELS = [
    ("amp_dano", "Amplificação de dano"),
    ("red_dano", "Redução de dano"),
    ("assertividade", "Assertividade"),
    ("vampirismo", "Vampirismo"),
    ("chance_crit", "Chance de crit"),
    ("dano_crit", "Dano crit"),
]


def _lerp(a, b, t):
    return a + (b - a) * t

def _clamp(x, a, b):
    return a if x < a else b if x > b else x

def _ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def _blend(c1, c2, t):
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )

def _lighten(c, amt):
    # amt: 0..1, mistura pra branco
    return _blend(c, (255, 255, 255), _clamp(amt, 0.0, 1.0))


class PlayerBatalha:
    # ficha fixa
    FICHA_W = 350
    FICHA_H = 500
    PAD = 14
    GAP = 10

    # animações
    NUM_ANIM_MS = 220
    FLASH_MS = 260

    # cores
    FUNDO_PAINEL = (25, 25, 30)
    BORDA_PAINEL = (80, 80, 95)
    FUNDO_CARD = (18, 18, 22)
    BORDA_CARD = (55, 55, 65)

    # número amarelo quando potencializado
    COR_POT = (255, 230, 120)
    COR_NUM = (255, 255, 255)

    # fonte
    FONTE_PATH = os.path.join("Fontes", "FontePadrão.ttf")

    def __init__(self, nome: str, *, lado: str, nivel: int = 1):
        """
        lado: "aliado" ou "inimigo" (apenas para uso externo/organização)
        """
        self.nome = nome
        self.lado = lado

        self.nivel = max(1, int(nivel))  # limite de dados ativos

        # vida
        self.vida_max = 100
        self.vida = 100

        # ouro (não desenha ainda)
        self.ouro = 0

        # personagens
        self.personagens = []

        # base e intensificador por atributo (do tabuleiro)
        self.base = {k: 10.0 for k in ATRIBUTOS}
        self.intens = {k: 0 for k in ATRIBUTOS}

        # animação numérica/flash
        self.display_val = {k: self._calc_total(k) for k in ATRIBUTOS}
        self.anim = {
            k: {"from": self.display_val[k], "to": self.display_val[k], "t0": 0, "on": False}
            for k in ATRIBUTOS
        }
        self.flash_t0 = {k: -10_000 for k in ATRIBUTOS}

        # cada player tem 1 dado por atributo (faces você ajusta depois)
        self.dados_por_attr = {k: {"attr": k, "faces": [1, 2, 3, 4, 5, 6], "pot": "std"} for k in ATRIBUTOS}

        # quais estão em uso (ativos)
        self.ativos = set()  # conjunto de attrs ativos

        # cache de retângulos clicáveis por frame
        self._attr_rects = {}

        # fontes (lazy)
        self._font_nome = None
        self._font_small = None
        self._font_big = None
        self._font_hp = None

    # ----------------------------
    # cálculo
    # ----------------------------
    def _calc_total(self, attr: str) -> float:
        b = float(self.base.get(attr, 0.0))
        mult = 1.0 + 0.10 * float(self.intens.get(attr, 0))
        return b * mult

    def get_total(self, attr: str) -> float:
        return self._calc_total(attr)

    # ----------------------------
    # base/intensificador (do tabuleiro)
    # ----------------------------
    def set_base(self, attr: str, valor: float):
        if attr not in self.base:
            return
        self.base[attr] = float(valor)
        if not self.anim[attr]["on"]:
            self.display_val[attr] = self._calc_total(attr)

    def set_intensificador(self, attr: str, novo: int, agora_ms: int):
        if attr not in self.intens:
            return
        novo = int(novo)
        antigo = int(self.intens[attr])
        if novo == antigo:
            return

        old_total = float(self.display_val[attr])
        self.intens[attr] = novo
        new_total = float(self._calc_total(attr))

        self.anim[attr]["from"] = old_total
        self.anim[attr]["to"] = new_total
        self.anim[attr]["t0"] = agora_ms
        self.anim[attr]["on"] = True

        if novo > antigo:
            self.flash_t0[attr] = agora_ms

    def update(self, agora_ms: int):
        for attr in ATRIBUTOS:
            a = self.anim[attr]
            if not a["on"]:
                continue
            t = (agora_ms - a["t0"]) / self.NUM_ANIM_MS
            if t >= 1.0:
                t = 1.0
                a["on"] = False
            e = _ease_out_cubic(_clamp(t, 0.0, 1.0))
            self.display_val[attr] = _lerp(a["from"], a["to"], e)

    # ----------------------------
    # dados ativos (botões)
    # ----------------------------
    def max_ativos(self):
        return self.nivel

    def ativos_lista(self):
        # ordem fixa pra previsível
        return [a for a in ATRIBUTOS if a in self.ativos]

    def toggle_attr_ativo(self, attr: str):
        if attr not in ATRIBUTOS:
            return

        if attr in self.ativos:
            self.ativos.remove(attr)
            return

        # se tá cheio, não liga mais (você pode preferir "trocar o mais antigo")
        if len(self.ativos) >= self.max_ativos():
            return

        self.ativos.add(attr)

    def get_dados_ativos_para_lancar(self):
        """
        Retorna lista de dicts no formato que o Tabuleiro espera:
        [{"attr","pot","faces"}, ...]
        """
        out = []
        for attr in self.ativos_lista():
            d = self.dados_por_attr[attr]
            out.append({"attr": d["attr"], "pot": d.get("pot", "std"), "faces": list(d.get("faces", [1]))})
        return out

    # ----------------------------
    # posição ficha
    # ----------------------------
    def get_rect(self, tela: pygame.Surface, *, lado: str):
        margin = 18
        y = tela.get_height() - self.FICHA_H - margin
        x = margin if lado == "esquerda" else tela.get_width() - self.FICHA_W - margin
        return pygame.Rect(x, y, self.FICHA_W, self.FICHA_H)

    # ----------------------------
    # fonte
    # ----------------------------
    def _ensure_fonts(self):
        if self._font_nome is not None:
            return

        self._font_nome = pygame.font.Font(self.FONTE_PATH, 32)
        self._font_hp = pygame.font.Font(self.FONTE_PATH, 26)
        self._font_small = pygame.font.Font(self.FONTE_PATH, 18)
        self._font_big = pygame.font.Font(self.FONTE_PATH, 40)

    # ----------------------------
    # eventos: clique nos botões de atributo
    # ----------------------------
    def handle_events(self, events, mouse_pos, *, lado_ficha: str):
        """
        Chame isso na TelaBatalha antes do draw, porque os rects são preenchidos no draw_ficha.
        Então, aqui só consome clique se já existir rect daquela frame.
        """
        if not self._attr_rects:
            return

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                # clique dentro da ficha?
                # checa botões
                for attr, rect in self._attr_rects.items():
                    if rect.collidepoint(mouse_pos):
                        self.toggle_attr_ativo(attr)
                        return

    # ----------------------------
    # draw ficha (botões + hover + cores)
    # ----------------------------
    def draw_ficha(self, tela: pygame.Surface, agora_ms: int, *, lado: str):
        self._ensure_fonts()
        painel = self.get_rect(tela, lado=lado)

        pygame.draw.rect(tela, self.FUNDO_PAINEL, painel, border_radius=14)
        pygame.draw.rect(tela, self.BORDA_PAINEL, painel, 3, border_radius=14)

        x, y, w, h = painel
        cx = x + self.PAD
        cy = y + self.PAD

        # nome
        nome_s = self._font_nome.render(self.nome, True, (245, 245, 245))
        tela.blit(nome_s, (cx, cy))
        cy += nome_s.get_height() + 10

        # barra de vida (mais grossa + número maior)
        bar_h = 24
        bar_w = w - self.PAD * 2
        bar = pygame.Rect(cx, cy, bar_w, bar_h)
        pygame.draw.rect(tela, (45, 45, 55), bar, border_radius=10)

        ratio = 0.0 if self.vida_max <= 0 else max(0.0, min(1.0, self.vida / self.vida_max))
        fill = pygame.Rect(cx, cy, int(bar_w * ratio), bar_h)
        pygame.draw.rect(tela, (80, 220, 120), fill, border_radius=10)
        pygame.draw.rect(tela, (10, 10, 10), bar, 2, border_radius=10)

        vida_txt = f"{int(self.vida)}/{int(self.vida_max)}"
        vida_s = self._font_hp.render(vida_txt, True, (255, 255, 255))
        tela.blit(vida_s, vida_s.get_rect(center=bar.center))

        cy += bar_h + 14

        # grid 2 colunas x 4 linhas (botões)
        cols, rows = 2, 4
        gap = self.GAP
        grid_top = cy

        cell_w = (w - self.PAD * 2 - gap * (cols - 1)) // cols
        cell_h = (h - (grid_top - y) - self.PAD - gap * (rows - 1)) // rows

        mouse_pos = pygame.mouse.get_pos()

        # reset rects clicáveis
        self._attr_rects = {}

        for idx, attr in enumerate(ATRIBUTOS):
            col = idx % cols
            row = idx // cols
            bx = cx + col * (cell_w + gap)
            by = grid_top + row * (cell_h + gap)
            cell = pygame.Rect(bx, by, cell_w, cell_h)

            self._attr_rects[attr] = cell

            base_cor = DICE_TYPES.get(attr, (200, 200, 200))

            # hover
            hovered = cell.collidepoint(mouse_pos)

            # se ativo, fundo levemente pintado pela cor do atributo
            ativo = (attr in self.ativos)

            # fundo base
            pygame.draw.rect(tela, self.FUNDO_CARD, cell, border_radius=12)

            if ativo:
                # mistura com a cor do atributo (leve)
                fill_cor = _blend(self.FUNDO_CARD, base_cor, 0.22)
                if hovered:
                    fill_cor = _lighten(fill_cor, 0.08)
                pygame.draw.rect(tela, fill_cor, cell, border_radius=12)
            else:
                # inativo: só hover leve
                if hovered:
                    hover_cor = _lighten(self.FUNDO_CARD, 0.08)
                    pygame.draw.rect(tela, hover_cor, cell, border_radius=12)

            # borda: cor do atributo, com flash se aumentou
            ft = (agora_ms - self.flash_t0[attr]) / self.FLASH_MS
            ft = _clamp(ft, 0.0, 1.0)
            flash_strength = 1.0 - ft
            cor_borda = _blend(base_cor, (255, 255, 255), 0.60 * flash_strength)

            pygame.draw.rect(tela, cor_borda, cell, 3, border_radius=12)

            # label
            label = LABELS.get(attr, attr)
            tlabel = self._font_small.render(label, True, (235, 235, 235))
            tela.blit(tlabel, (bx + 10, by + 8))

            # número (branco ou amarelo se potencializado)
            val = self.display_val[attr]
            vtxt = str(int(round(val)))

            # cor do número:
            # - padrão: branco
            # - se intensificador > 0: amarelo
            num_color = self.COR_POT if self.intens.get(attr, 0) > 0 else self.COR_NUM

            tnum = self._font_big.render(vtxt, True, num_color)
            center_y = by + (cell_h // 2) + 8
            tela.blit(tnum, tnum.get_rect(center=(bx + cell_w // 2, center_y)))

class PlayerEstrategista:
    """
    Agora este Player é o "dono" da tela:
      - guarda refs: grid, banco, loja, painel
      - guarda ouro e stats
      - calcula sinergias conectadas (ativas) a partir do grid
      - expõe update/draw e sync_from_grid

    Por enquanto a Grid ainda faz drag/placemente. Depois a gente migra pra cá sem dor.
    """

    # ficha fixa (compacta, topo esquerdo)
    FICHA_W = 350
    FICHA_H = 500
    PAD = 14
    GAP = 10

    NUM_ANIM_MS = 220

    FUNDO_PAINEL = (25, 25, 30)
    BORDA_PAINEL = (80, 80, 95)
    FUNDO_CARD = (18, 18, 22)
    BORDA_CARD = (55, 55, 65)

    COR_NUM = (255, 255, 255)

    FONTE_PATH = os.path.join("Fontes", "FontePadrão.ttf")

    def __init__(self, nome: str, *, lado: str = "aliado", ouro_inicial: int = 10):
        self.nome = nome
        self.lado = lado

        # refs (serão setadas na tela)
        self.grid = None
        self.banco = None
        self.loja = None
        self.painel = None

        # economia (simples)
        self.ouro = int(ouro_inicial)

        # vida baseada na soma da vida dos brawlers em campo
        self.vida_max = 0
        self.vida = 0

        # somas
        self.totais = {k: 0 for k in ATRIBUTOS}

        # sinergias ativas (conectadas de verdade)
        self.sinergias_ativas = {}  # nome_normalizado -> contagem de brawlers envolvidos

        # animação numérica
        self.display_val = {k: 0.0 for k in ATRIBUTOS}
        self.anim = {k: {"from": 0.0, "to": 0.0, "t0": 0, "on": False} for k in ATRIBUTOS}

        # dados alocados manualmente via arrasto na grid
        self.dados_selecionados = {k: [] for k in ATRIBUTOS}
        self._attr_rects = {}
        self._drag_preview_dado = None

        # stats percentuais (fixos inicialmente)
        self.percentuais = {k: 0 for k, _ in PERCENT_LABELS}

        # fontes
        self._font_nome = None
        self._font_small = None
        self._font_big = None
        self._font_hp = None
        self._font_micro = None

    # ----------------------------
    # refs
    # ----------------------------
    def set_refs(self, *, grid, banco, loja, painel):
        self.grid = grid
        self.banco = banco
        self.loja = loja
        self.painel = painel

    # ----------------------------
    # fontes
    # ----------------------------
    def _ensure_fonts(self):
        if self._font_nome is not None:
            return

        self._font_nome = pygame.font.Font(self.FONTE_PATH, 30)
        self._font_hp = pygame.font.Font(self.FONTE_PATH, 24)
        self._font_small = pygame.font.Font(self.FONTE_PATH, 18)
        self._font_big = pygame.font.Font(self.FONTE_PATH, 36)
        self._font_micro = pygame.font.Font(self.FONTE_PATH, 16)
        self._font_tiny = pygame.font.Font(self.FONTE_PATH, 14)

    # ----------------------------
    # helpers stats
    # ----------------------------
    def _get_stat(self, cartucho, key: str) -> int:
        st = getattr(cartucho, "stats", None)
        if isinstance(st, dict):
            v = st.get(key, 0)
        else:
            dados = getattr(cartucho, "dados", {}) or {}
            st2 = dados.get("stats", {}) or {}
            v = st2.get(key, 0)

        if v is None or v == "":
            return 0
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    def _star_mult(self, cartucho) -> float:
        estrelas = max(0, int(getattr(cartucho, "estrelas", 0) or 0))
        return 1.0 + 0.5 * estrelas

    def _set_total_animado(self, attr: str, novo_val: int, agora_ms: int):
        novo_val = int(novo_val)
        atual_vis = float(self.display_val.get(attr, 0.0))

        if int(round(atual_vis)) == novo_val and not self.anim[attr]["on"]:
            self.totais[attr] = novo_val
            self.display_val[attr] = float(novo_val)
            return

        self.totais[attr] = novo_val
        self.anim[attr]["from"] = atual_vis
        self.anim[attr]["to"] = float(novo_val)
        self.anim[attr]["t0"] = agora_ms
        self.anim[attr]["on"] = True

    # ----------------------------
    # coleta campo (grid)
    # ----------------------------
    def get_cartuchos_em_campo(self):
        if not self.grid:
            return []
        # sua Grid usa self.occ {(c,r): Cartucho}
        occ = getattr(self.grid, "occ", None)
        if isinstance(occ, dict):
            return list(occ.values())
        # fallback se você mudar depois
        fn = getattr(self.grid, "get_cartuchos_em_campo", None)
        if callable(fn):
            return fn()
        return []

    def _normaliza(self, s: str) -> str:
        return str(s).strip().lower()

    def _get_sinergias_cartucho(self, cartucho):
        # seu Cartucho tem property sinergias baseada em dados["características"]
        raw = getattr(cartucho, "sinergias", None)
        if raw is None:
            dados = getattr(cartucho, "dados", {}) or {}
            raw = dados.get("características", []) or []
        if not isinstance(raw, (list, tuple)):
            return []
        return [self._normaliza(x) for x in raw if str(x).strip()]

    def _calcula_sinergias_ativas_conectadas(self):
        """
        Sinergia "ativa" = só se existe conexão adjacente real (igual sua regra do contorno).
        Aqui eu calculo a partir de adjacências na occ, contando brawlers envolvidos.
        """
        if not self.grid:
            return {}

        occ = getattr(self.grid, "occ", {}) or {}
        if not isinstance(occ, dict) or not occ:
            return {}

        active_pos = {}  # sym -> set[(c,r)]
        for (c, r), a in occ.items():
            sa = set(self._get_sinergias_cartucho(a))
            # só direita/baixo pra evitar dupla contagem
            for dc, dr in ((1, 0), (0, 1)):
                b = occ.get((c + dc, r + dr))
                if not b:
                    continue
                sb = set(self._get_sinergias_cartucho(b))
                shared = sa & sb
                for sym in shared:
                    st = active_pos.setdefault(sym, set())
                    st.add((c, r))
                    st.add((c + dc, r + dr))

        # transforma em contagem de brawlers envolvidos
        return {sym: len(pos_set) for sym, pos_set in active_pos.items()}

    # ----------------------------
    # sync: recalcula tudo do campo
    # ----------------------------
    def sync_from_grid(self, agora_ms: int):
        cartuchos = self.get_cartuchos_em_campo()

        vida_total = 0
        soma = {k: 0 for k in ATRIBUTOS}

        for c in cartuchos:
            mult = self._star_mult(c)

            vida_total += self._get_stat(c, "vida")

            soma["dano_fisico"]   += int(round(self._get_stat(c, "dano_fisico") * mult))
            soma["dano_magico"]   += int(round(self._get_stat(c, "dano_especial") * mult))
            soma["defesa_fisica"] += int(round(self._get_stat(c, "defesa_fisica") * mult))
            soma["defesa_magica"] += int(round(self._get_stat(c, "defesa_especial") * mult))
            soma["regeneracao"]   += self._get_stat(c, "regeneracao")
            soma["mana"]          += self._get_stat(c, "mana")
            soma["velocidade"]    += self._get_stat(c, "velocidade")
            soma["penetracao"]    += self._get_stat(c, "perfuracao")

        self.vida_max = int(vida_total)
        self.vida = self.vida_max

        for attr in ATRIBUTOS:
            self._set_total_animado(attr, soma[attr], agora_ms)

        # sinergias conectadas
        self.sinergias_ativas = self._calcula_sinergias_ativas_conectadas()

    def drop_dado_em_attr(self, mouse_pos, dado_info: dict):
        """Recebe um dado arrastado da grid e tenta alocar em um atributo da ficha."""
        if not self._attr_rects:
            return False

        attr_src = str((dado_info or {}).get("attr", "")).strip()
        if attr_src not in ATRIBUTOS:
            return False

        for attr, rect in self._attr_rects.items():
            if not rect.collidepoint(mouse_pos):
                continue
            if attr != attr_src:
                return False

            faces = list((dado_info or {}).get("faces", []) or [])
            cartucho = (dado_info or {}).get("cartucho")
            self.dados_selecionados[attr] = [{
                "faces": faces[:6],
                "cartucho": cartucho,
            }]
            return True

        return False

    # ----------------------------
    # update
    # ----------------------------
    def update(self, agora_ms: int):
        for attr in ATRIBUTOS:
            a = self.anim[attr]
            if not a["on"]:
                continue
            t = (agora_ms - a["t0"]) / self.NUM_ANIM_MS
            if t >= 1.0:
                t = 1.0
                a["on"] = False
            e = _ease_out_cubic(_clamp(t, 0.0, 1.0))
            self.display_val[attr] = _lerp(a["from"], a["to"], e)

    def set_dado_drag_preview(self, dado_info: dict | None):
        self._drag_preview_dado = dado_info

    # ----------------------------
    # desenho
    # ----------------------------
    def get_rect(self, *, pos=(18, 18)):
        x, y = pos
        return pygame.Rect(int(x), int(y), self.FICHA_W, self.FICHA_H)

    def draw_ficha(self, tela: pygame.Surface, agora_ms: int, *, pos=(18, 18)):
        self._ensure_fonts()
        painel = self.get_rect(pos=pos)

        pygame.draw.rect(tela, self.FUNDO_PAINEL, painel, border_radius=14)
        pygame.draw.rect(tela, self.BORDA_PAINEL, painel, 3, border_radius=14)

        x, y, w, h = painel
        cx = x + self.PAD
        cy = y + self.PAD

        # Nome + ouro (simples)
        nome_s = self._font_nome.render(self.nome, True, (245, 245, 245))
        tela.blit(nome_s, (cx, cy))

        ouro_txt = f"Ouro: {int(self.ouro)}"
        ouro_s = self._font_small.render(ouro_txt, True, (210, 210, 220))
        tela.blit(ouro_s, (x + w - self.PAD - ouro_s.get_width(), cy + 6))

        cy += nome_s.get_height() + 10

        # Barra de vida
        bar_h = 22
        bar_w = w - self.PAD * 2
        bar = pygame.Rect(cx, cy, bar_w, bar_h)
        pygame.draw.rect(tela, (45, 45, 55), bar, border_radius=10)

        ratio = 0.0 if self.vida_max <= 0 else max(0.0, min(1.0, self.vida / self.vida_max))
        fill = pygame.Rect(cx, cy, int(bar_w * ratio), bar_h)
        pygame.draw.rect(tela, (80, 220, 120), fill, border_radius=10)
        pygame.draw.rect(tela, (10, 10, 10), bar, 2, border_radius=10)

        vida_txt = f"{int(self.vida)}/{int(self.vida_max)}"
        vida_s = self._font_hp.render(vida_txt, True, (255, 255, 255))
        tela.blit(vida_s, vida_s.get_rect(center=bar.center))

        cy += bar_h + 10

        # Grid 2x4 com atributos
        cols, rows = 2, 4
        gap = self.GAP
        grid_top = cy

        cell_w = (w - self.PAD * 2 - gap * (cols - 1)) // cols
        footer_h = 90
        cell_h = (h - (grid_top - y) - self.PAD - footer_h - gap * (rows - 1)) // rows

        mouse_pos = pygame.mouse.get_pos()
        self._attr_rects = {}

        for idx, attr in enumerate(ATRIBUTOS):
            col = idx % cols
            row = idx // cols
            bx = cx + col * (cell_w + gap)
            by = grid_top + row * (cell_h + gap)
            cell = pygame.Rect(bx, by, cell_w, cell_h)
            self._attr_rects[attr] = cell

            base_cor = DICE_TYPES.get(attr, (200, 200, 200))
            hovered = cell.collidepoint(mouse_pos)
            drag_attr = str((self._drag_preview_dado or {}).get("attr", "")).strip()
            is_drag_target = bool(self._drag_preview_dado) and (drag_attr == attr)
            pulse = (pygame.time.get_ticks() % 620) / 620.0
            pulse = 0.45 + 0.55 * (0.5 - 0.5 * math.cos(pulse * math.tau))

            pygame.draw.rect(tela, self.FUNDO_CARD, cell, border_radius=12)
            if hovered:
                pygame.draw.rect(tela, _lighten(self.FUNDO_CARD, 0.08), cell, border_radius=12)

            if is_drag_target:
                glow = cell.inflate(10, 10)
                alpha = int(80 + 120 * pulse)
                gsurf = pygame.Surface((glow.w, glow.h), pygame.SRCALPHA)
                pygame.draw.rect(gsurf, (*base_cor, alpha), gsurf.get_rect(), border_radius=16)
                tela.blit(gsurf, glow.topleft)

            pygame.draw.rect(tela, base_cor, cell, 3, border_radius=12)
            if is_drag_target:
                thick = 3 + int(2 * pulse)
                pygame.draw.rect(tela, (255, 245, 170), cell, thick, border_radius=12)

            label = LABELS.get(attr, attr)
            tlabel = self._font_small.render(label, True, (235, 235, 235))
            tela.blit(tlabel, (bx + 10, by + 8))

            val = float(self.display_val[attr])
            vtxt = str(int(round(val)))
            tnum = self._font_big.render(vtxt, True, self.COR_NUM)
            center_y = by + (cell_h // 2) + 8
            tela.blit(tnum, tnum.get_rect(center=(bx + cell_w // 2, center_y)))

            dados_qtd = len(self.dados_selecionados.get(attr, []))
            if dados_qtd > 0:
                icon_size = 22
                max_icons = max(1, (cell_w - 20) // (icon_size + 4))
                x0 = bx + 10
                y0 = by + cell_h - icon_size - 8
                for dado in self.dados_selecionados[attr][:max_icons]:
                    cartucho = dado.get("cartucho")
                    dados = getattr(cartucho, "dados", {}) if cartucho is not None else {}
                    icon = gerar_imagem_cartucho_grid(dados or {}, (icon_size, icon_size))
                    tela.blit(icon, (x0, y0))
                    x0 += icon_size + 4

        py = grid_top + rows * cell_h + (rows - 1) * gap + 6
        for key, label in PERCENT_LABELS:
            val = int(self.percentuais.get(key, 0))
            txt = self._font_tiny.render(f"{label}: {val}%", True, (195, 195, 210))
            tela.blit(txt, (cx + 2, py))
            py += txt.get_height() + 1
