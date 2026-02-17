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

PERCENT_ICONS = {
    "amp_dano": "AmpDano.png",
    "red_dano": "RedDano.png",
    "assertividade": "Asse.png",
    "vampirismo": "Vamp.png",
    "chance_crit": "CrC.png",
    "dano_crit": "CrD.png",
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
    COMBATE_SLOTS_TOTAL = 4
    COMBATE_SLOTS_LIBERADOS = 2
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
        self.percentuais = {k: 0 for k, _ in PERCENT_LABELS}
        self.percentuais["assertividade"] = 100

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
        self._ativos_ordem = []

        # cache de retângulos clicáveis por frame
        self._attr_rects = {}

        # fontes (lazy)
        self._font_nome = None
        self._font_small = None
        self._font_big = None
        self._font_hp = None
        self._font_tiny = None
        self._percent_icons = {}

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
            if attr in self._ativos_ordem:
                self._ativos_ordem.remove(attr)
            return

        # quando lotado, troca pelo mais antigo
        if len(self.ativos) >= self.max_ativos():
            antigo = self._ativos_ordem.pop(0)
            self.ativos.remove(antigo)

        self.ativos.add(attr)
        self._ativos_ordem.append(attr)

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
    def get_rect(self, tela: pygame.Surface, *, lado: str, pos=None):
        if pos is not None:
            return pygame.Rect(int(pos[0]), int(pos[1]), self.FICHA_W, self.FICHA_H)
        margin = 18
        y = tela.get_height() - self.FICHA_H - margin
        x = margin if lado == "esquerda" else tela.get_width() - self.FICHA_W - margin
        return pygame.Rect(x, y, self.FICHA_W, self.FICHA_H)

    def set_percentuais(self, valores: dict | None):
        if not isinstance(valores, dict):
            return
        for key, _ in PERCENT_LABELS:
            self.percentuais[key] = int(valores.get(key, self.percentuais.get(key, 0)) or 0)

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
        self._font_tiny = pygame.font.Font(self.FONTE_PATH, 14)

    def _get_percent_icon(self, key: str, size: int):
        cache_key = (key, int(size))
        if cache_key in self._percent_icons:
            return self._percent_icons[cache_key]

        fname = PERCENT_ICONS.get(key)
        if not fname:
            self._percent_icons[cache_key] = None
            return None

        path = os.path.join("Recursos", "Visual", "Icones", fname)
        try:
            icon = pygame.image.load(path).convert_alpha()
            icon = pygame.transform.smoothscale(icon, (size, size))
        except Exception:
            icon = None

        self._percent_icons[cache_key] = icon
        return icon

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
    def draw_ficha(self, tela: pygame.Surface, agora_ms: int, *, lado: str, pos=None, mostrar_botoes=True):
        self._ensure_fonts()
        painel = self.get_rect(tela, lado=lado, pos=pos)

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
        footer_h = 90
        cell_h = (h - (grid_top - y) - self.PAD - footer_h - gap * (rows - 1)) // rows

        mouse_pos = pygame.mouse.get_pos()

        # reset rects clicáveis
        self._attr_rects = {}

        if not mostrar_botoes:
            stats_top = grid_top
            lh = 24
            for i, (key, label) in enumerate(PERCENT_LABELS):
                txt = self._font_small.render(f"{label}: {int(self.percentuais.get(key, 0))}%", True, (220, 225, 235))
                tela.blit(txt, (cx + 8, stats_top + i * lh))
            return

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

        py = grid_top + rows * cell_h + (rows - 1) * gap + 8
        cols_p = 3
        icon_size = 24
        col_w = (w - self.PAD * 2 - gap * (cols_p - 1)) // cols_p
        for idx, (key, _label) in enumerate(PERCENT_LABELS):
            col = idx % cols_p
            row = idx // cols_p
            px = cx + col * (col_w + gap)
            by = py + row * (icon_size + 10)

            val = int(self.percentuais.get(key, 0))
            icon = self._get_percent_icon(key, icon_size)
            rect = pygame.Rect(px, by, icon_size, icon_size)
            pygame.draw.rect(tela, (32, 32, 40), rect, border_radius=7)
            pygame.draw.rect(tela, (90, 90, 110), rect, 1, border_radius=7)
            if icon is not None:
                tela.blit(icon, rect.topleft)

            val_txt = self._font_tiny.render(f"{val}%", True, (220, 220, 235))
            tela.blit(val_txt, (rect.right + 5, rect.y + (icon_size - val_txt.get_height()) // 2))

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
    COMBATE_SLOTS_TOTAL = 4
    COMBATE_SLOTS_LIBERADOS = 2
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
        self.percentuais["assertividade"] = 100
        self._percent_rects = {}
        self._percent_icons = {}

        # seleção de personagens para o combate
        self.combate_slots = [None] * self.COMBATE_SLOTS_TOTAL
        self._combate_rects = {}

        # fontes
        self._font_nome = None
        self._font_small = None
        self._font_big = None
        self._font_hp = None
        self._font_tiny = None
        self._font_micro = None

    # ----------------------------
    # refs
    # ----------------------------
    def set_refs(self, *, grid, banco, loja, painel):
        self.grid = grid
        self.banco = banco
        self.loja = loja
        self.painel = painel

    def exportar_estado_compartilhado(self):
        return {
            "nome": str(self.nome),
            "lado": str(self.lado),
            "ouro": int(self.ouro),
            "vida_max": int(self.vida_max),
            "vida": int(self.vida),
            "totais": {k: int(self.totais.get(k, 0)) for k in ATRIBUTOS},
            "percentuais": {k: int(self.percentuais.get(k, 0)) for k, _ in PERCENT_LABELS},
            "nivel": int(self.COMBATE_SLOTS_LIBERADOS),
            "ativos": [a for a in ATRIBUTOS if self.dados_selecionados.get(a)],
        }

    def carregar_estado_compartilhado(self, dados: dict):
        if not isinstance(dados, dict):
            return

        self.nome = str(dados.get("nome", self.nome))
        self.lado = str(dados.get("lado", self.lado))
        self.ouro = int(dados.get("ouro", self.ouro) or 0)
        self.vida_max = int(dados.get("vida_max", self.vida_max) or 0)
        self.vida = int(dados.get("vida", self.vida) or 0)

        totais = dados.get("totais") or {}
        for attr in ATRIBUTOS:
            self.totais[attr] = int(totais.get(attr, self.totais.get(attr, 0)) or 0)
            self.display_val[attr] = float(self.totais[attr])
            self.anim[attr]["on"] = False

        percentuais = dados.get("percentuais") or {}
        for key, _ in PERCENT_LABELS:
            self.percentuais[key] = int(percentuais.get(key, self.percentuais.get(key, 0)) or 0)

        self.dados_selecionados = {k: [] for k in ATRIBUTOS}
        ativos = dados.get("ativos") or []
        for attr in ativos:
            if attr in self.dados_selecionados:
                self.dados_selecionados[attr] = [{"faces": [1, 2, 3, 4, 5, 6], "cartucho": None}]

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

    def _get_percent_icon(self, key: str, size: int):
        cache_key = (key, int(size))
        if cache_key in self._percent_icons:
            return self._percent_icons[cache_key]

        fname = PERCENT_ICONS.get(key)
        if not fname:
            self._percent_icons[cache_key] = None
            return None

        path = os.path.join("Recursos", "Visual", "Icones", fname)
        try:
            icon = pygame.image.load(path).convert_alpha()
            icon = pygame.transform.smoothscale(icon, (size, size))
        except Exception:
            icon = None
        self._percent_icons[cache_key] = icon
        return icon

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

        em_campo_ids = {id(c) for c in cartuchos}
        self.combate_slots = [c if (c is not None and id(c) in em_campo_ids) else None for c in self.combate_slots]

        escalados = []
        vistos = set()
        for c in self.combate_slots:
            if c is None:
                continue
            if id(c) in vistos:
                continue
            vistos.add(id(c))
            escalados.append(c)

        def acumula_cartucho(c):
            nonlocal vida_total
            mult = self._star_mult(c)
            vida_total += int(round(self._get_stat(c, "vida") * mult))
            soma["dano_fisico"]   += int(round(self._get_stat(c, "dano_fisico") * mult))
            soma["dano_magico"]   += int(round(self._get_stat(c, "dano_especial") * mult))
            soma["defesa_fisica"] += int(round(self._get_stat(c, "defesa_fisica") * mult))
            soma["defesa_magica"] += int(round(self._get_stat(c, "defesa_especial") * mult))
            soma["regeneracao"]   += int(round(self._get_stat(c, "regeneracao") * mult))
            soma["mana"]          += int(round(self._get_stat(c, "mana") * mult))
            soma["velocidade"]    += int(round(self._get_stat(c, "velocidade") * mult))
            soma["penetracao"]    += int(round(self._get_stat(c, "perfuracao") * mult))

        for c in cartuchos:
            acumula_cartucho(c)

        # personagens escalados para combate aplicam seus status em dobro
        for c in escalados:
            acumula_cartucho(c)

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

    def drop_combatente_em_slot(self, mouse_pos, cartucho):
        if cartucho is None or not self._combate_rects:
            return False

        alvo = None
        for idx, rect in self._combate_rects.items():
            if rect.collidepoint(mouse_pos):
                alvo = idx
                break

        if alvo is None:
            return False
        if alvo >= self.COMBATE_SLOTS_LIBERADOS:
            return False

        for i, atual in enumerate(self.combate_slots):
            if atual is cartucho:
                self.combate_slots[i] = None

        self.combate_slots[alvo] = cartucho
        return True

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

        self._percent_rects = {}
        py = grid_top + rows * cell_h + (rows - 1) * gap + 8
        cols_p, rows_p = 3, 2
        icon_size = 24
        col_w = (w - self.PAD * 2 - gap * (cols_p - 1)) // cols_p
        for idx, (key, label) in enumerate(PERCENT_LABELS):
            col = idx % cols_p
            row = idx // cols_p
            px = cx + col * (col_w + gap)
            by = py + row * (icon_size + 10)

            val = int(self.percentuais.get(key, 0))
            icon = self._get_percent_icon(key, icon_size)
            rect = pygame.Rect(px, by, icon_size, icon_size)

            pygame.draw.rect(tela, (32, 32, 40), rect, border_radius=7)
            pygame.draw.rect(tela, (90, 90, 110), rect, 1, border_radius=7)
            if icon is not None:
                tela.blit(icon, rect.topleft)

            val_txt = self._font_tiny.render(f"{val}%", True, (220, 220, 235))
            tela.blit(val_txt, (rect.right + 5, rect.y + (icon_size - val_txt.get_height()) // 2))

            self._percent_rects[key] = rect

        for key, label in PERCENT_LABELS:
            rect = self._percent_rects.get(key)
            if rect and rect.collidepoint(mouse_pos):
                tip = self._font_tiny.render(label, True, (245, 245, 250))
                tip_rect = tip.get_rect()
                box = pygame.Rect(mouse_pos[0] + 12, mouse_pos[1] + 10, tip_rect.w + 12, tip_rect.h + 8)
                if box.right > tela.get_width() - 6:
                    box.x = mouse_pos[0] - box.w - 12
                if box.bottom > tela.get_height() - 6:
                    box.y = mouse_pos[1] - box.h - 10
                pygame.draw.rect(tela, (14, 14, 20), box, border_radius=8)
                pygame.draw.rect(tela, (120, 120, 145), box, 1, border_radius=8)
                tela.blit(tip, (box.x + 6, box.y + 4))
                break

        # slots de seleção para combate (abaixo da ficha)
        self._combate_rects = {}
        title = self._font_small.render("Escalação de Combate", True, (228, 228, 238))
        slots_top = painel.bottom + 12
        tela.blit(title, (painel.x + 4, slots_top))

        slot_size = 66
        slot_gap = 10
        start_x = painel.x + 6
        start_y = slots_top + title.get_height() + 8

        for idx in range(self.COMBATE_SLOTS_TOTAL):
            col = idx % 2
            row = idx // 2
            sx = start_x + col * (slot_size + slot_gap)
            sy = start_y + row * (slot_size + slot_gap)
            rect = pygame.Rect(sx, sy, slot_size, slot_size)
            self._combate_rects[idx] = rect

            unlocked = idx < self.COMBATE_SLOTS_LIBERADOS
            bg = (26, 26, 32) if unlocked else (20, 20, 24)
            bd = (110, 110, 132) if unlocked else (70, 70, 82)
            pygame.draw.rect(tela, bg, rect, border_radius=10)
            pygame.draw.rect(tela, bd, rect, 2, border_radius=10)

            cartucho = self.combate_slots[idx]
            if cartucho is not None and unlocked:
                icon = gerar_imagem_cartucho_grid(getattr(cartucho, "dados", {}) or {}, (slot_size - 8, slot_size - 8))
                tela.blit(icon, (rect.x + 4, rect.y + 4))
                pygame.draw.rect(tela, (255, 220, 120), rect, 2, border_radius=10)
            elif not unlocked:
                lock = self._font_tiny.render("BLOQ", True, (140, 140, 155))
                tela.blit(lock, lock.get_rect(center=rect.center))
