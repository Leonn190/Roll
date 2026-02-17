import pygame
import os
import random
import math
from collections import deque

# ============================================================
# CONFIG
# ============================================================
W, H = 1920, 1080
BOARD_SIZE = 10
CELL_SIZE = 90
BOARD_W = BOARD_SIZE * CELL_SIZE
BOARD_H = BOARD_SIZE * CELL_SIZE
BOARD_ORIGIN = ((W - BOARD_W) // 2, (H - BOARD_H) // 2)

DADO_TAM = 65

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

_BORDA_INIMIGO = (235, 70, 70)   # vermelho
_BORDA_ALIADO  = (20, 20, 20)    # padrão (preto)


class Tabuleiro:
    # ---------- lançamento ----------
    NORMAL_MAX = 3
    NORMAL_PESOS = [0.20, 0.48, 0.24, 0.08]
    FORTE_MAX = 5
    FORTE_PESOS = [0.05, 0.12, 0.18, 0.22, 0.23, 0.20]

    ANIM_NORMAL = dict(dur_ms=850,  troca_min_ms=35, troca_max_ms=170, spin_total_deg=3 * 360, trail_len=9)
    ANIM_FORTE  = dict(dur_ms=1150, troca_min_ms=20, troca_max_ms=120, spin_total_deg=6 * 360, trail_len=12)

    # ---------- push ----------
    PUSH_MS = 140

    def __init__(self, tela: pygame.Surface):
        self.tela = tela
        self.operacional = True

        # grid: None ou {"attr","pot","valor","lado"}  lado: "aliado" | "inimigo"
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

        # mãos separadas
        self.mao_aliada = []   # [{"attr","pot","faces"}, ...]
        self.mao_inimiga = []  # idem

        # “mão ativa” (quem está lançando agora)
        self.lado_ativo = "aliado"  # "aliado" ou "inimigo"

        # animações
        self.fly = []   # dados lançados
        self.push = []  # dados empurrados (slide)

        # listas coletáveis (você pediu “um self para dados inimigos e aliados”)
        # -> aqui são listas dos DADOS FIXADOS no tabuleiro, no formato da célula (dict)
        self.dados_aliados = []
        self.dados_inimigos = []

        self._dado_cache = {}  # cache da face/cor
        self.hover = None

    # ============================================================
    # API pública
    # ============================================================
    def limpar_tabuleiro(self):
        self.grid = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.fly.clear()
        self.push.clear()
        self._rebuild_listas_dados()

    def set_lado_ativo(self, lado: str):
        if lado in ("aliado", "inimigo"):
            self.lado_ativo = lado

    def add_dado_mao(self, attr: str, faces, pot="normal", lado=None):
        """
        lado:
          - None => adiciona na mão do lado_ativo atual
          - "aliado" / "inimigo" => força para uma mão específica
        """
        if attr not in DICE_TYPES:
            raise ValueError(f"attr inválido: {attr}")
        faces = list(faces) if faces else [1]
        d = {"attr": attr, "pot": str(pot), "faces": faces}

        alvo = self.lado_ativo if lado is None else lado
        if alvo == "inimigo":
            self.mao_inimiga.append(d)
        else:
            self.mao_aliada.append(d)

    def remover_dado_mao(self, index: int, lado=None):
        """
        Remove 1 dado da mão (por índice).
        lado:
          - None => remove da mão do lado_ativo
          - "aliado" / "inimigo" => remove da mão específica
        """
        alvo = self.lado_ativo if lado is None else lado
        lst = self.mao_inimiga if alvo == "inimigo" else self.mao_aliada
        if 0 <= index < len(lst):
            return lst.pop(index)
        return None

    def renovar_mao_3_aleatorios(self, lado=None):
        """
        (extra teste) Renova a mão com 3 dados aleatórios.
        """
        alvo = self.lado_ativo if lado is None else lado
        lst = self.mao_inimiga if alvo == "inimigo" else self.mao_aliada
        lst.clear()

        attrs = list(DICE_TYPES.keys())
        for _ in range(3):
            attr = random.choice(attrs)
            # faces simples (você pode mudar depois)
            faces = [1, 2, 3, 4, 5, 6]
            pot = "rnd"
            lst.append({"attr": attr, "pot": pot, "faces": faces})


    def lancar_automatico(self, lado: str, agora_ms: int):
        """Lança toda a mão do lado informado em uma célula aleatória."""
        if lado not in ("aliado", "inimigo"):
            return
        self.lado_ativo = lado
        base_cell = (random.randint(0, BOARD_SIZE - 1), random.randint(0, BOARD_SIZE - 1))
        base_pos = self._grid_center(base_cell[0], base_cell[1])
        self._lancar_mao(base_pos, base_cell, agora_ms, modo="normal")

    # ============================================================
    # update: processa eventos + atualiza animações + desenha
    # (com teclas extras de teste dentro da classe)
    # ============================================================
    def update(self, events, agora_ms: int):
        # -------- eventos --------
        for event in events:
            if event.type == pygame.KEYDOWN:
                # ========= EXTRA (teste) =========
                # R: limpar tabuleiro
                if event.key == pygame.K_r:
                    self.limpar_tabuleiro()

                # T: renovar mão (3 aleatórios) do lado ativo
                elif event.key == pygame.K_t:
                    self.renovar_mao_3_aleatorios()

                # U: alterna operacional
                elif event.key == pygame.K_u:
                    self.operacional = not self.operacional

                # Y: alterna lado ativo (aliado <-> inimigo)
                elif event.key == pygame.K_y:
                    self.lado_ativo = "inimigo" if self.lado_ativo == "aliado" else "aliado"
                # =================================

                # (mantém compatível: L também limpa, se quiser)
                elif event.key == pygame.K_l:
                    self.limpar_tabuleiro()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not self.operacional:
                    continue
                if not self._inside_board(event.pos):
                    continue

                cell = self._pixel_to_grid(event.pos)
                if cell is None:
                    continue

                if event.button == 1:
                    self._lancar_mao(event.pos, cell, agora_ms, modo="normal")
                elif event.button == 3:
                    self._lancar_mao(event.pos, cell, agora_ms, modo="forte")

        # -------- hover (só se operacional) --------
        if self.operacional:
            self.hover = self._pixel_to_grid(pygame.mouse.get_pos())
        else:
            self.hover = None

        # -------- atualiza animações --------
        self._update_fly(agora_ms)
        self._update_push(agora_ms)

        # -------- desenha --------
        self._draw()

    # ============================================================
    # Helpers
    # ============================================================
    def _clamp(self, x, a, b):
        return a if x < a else b if x > b else x

    def _ease_out_cubic(self, t):
        return 1 - (1 - t) ** 3

    def _inside_board(self, pos):
        x, y = pos
        bx, by = BOARD_ORIGIN
        return (bx <= x < bx + BOARD_W) and (by <= y < by + BOARD_H)

    def _pixel_to_grid(self, pos):
        x, y = pos
        bx, by = BOARD_ORIGIN
        if not (bx <= x < bx + BOARD_W and by <= y < by + BOARD_H):
            return None
        col = (x - bx) // CELL_SIZE
        row = (y - by) // CELL_SIZE
        return int(col), int(row)

    def _grid_center(self, c, r):
        return (
            BOARD_ORIGIN[0] + c * CELL_SIZE + CELL_SIZE // 2,
            BOARD_ORIGIN[1] + r * CELL_SIZE + CELL_SIZE // 2
        )

    def _in_bounds(self, c, r):
        return 0 <= c < BOARD_SIZE and 0 <= r < BOARD_SIZE

    def _escolher_offset_por_dist(self, max_dist, pesos_por_dist):
        dist = random.choices(range(max_dist + 1), weights=pesos_por_dist, k=1)[0]
        if dist == 0:
            return 0, 0

        candidatos = []
        for dx in range(-dist, dist + 1):
            for dy in range(-dist, dist + 1):
                if max(abs(dx), abs(dy)) == dist:
                    candidatos.append((dx, dy))
        return random.choice(candidatos)

    def _dir_from_center(self, cell):
        c, r = cell
        center_c = (BOARD_SIZE - 1) / 2.0
        center_r = (BOARD_SIZE - 1) / 2.0
        vx = c - center_c
        vy = r - center_r
        if abs(vx) >= abs(vy):
            return (1, 0) if vx >= 0 else (-1, 0)
        else:
            return (0, 1) if vy >= 0 else (0, -1)

    def _rebuild_listas_dados(self):
        self.dados_aliados = []
        self.dados_inimigos = []
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                cell = self.grid[r][c]
                if cell is None:
                    continue
                if cell.get("lado") == "inimigo":
                    self.dados_inimigos.append(cell)
                else:
                    self.dados_aliados.append(cell)

    # ============================================================
    # Surface dado (todo colorido) + borda por lado
    # ============================================================
    def _criar_surface_dado(self, face, tam, cor_fill, lado):
        # cache precisa considerar lado (borda muda)
        key = (int(face), int(tam), tuple(cor_fill), lado)
        if key in self._dado_cache:
            return self._dado_cache[key]

        surf = pygame.Surface((tam, tam), pygame.SRCALPHA)
        r = pygame.Rect(0, 0, tam, tam)

        # corpo
        pygame.draw.rect(surf, cor_fill, r, border_radius=12)

        # borda: inimigo vermelho, aliado preto
        borda = _BORDA_INIMIGO if lado == "inimigo" else _BORDA_ALIADO
        pygame.draw.rect(surf, borda, r, 4, border_radius=12)

        # número
        font = pygame.font.Font(os.path.join("Fontes", "FontePadrão.ttf"), int(tam * 0.75))
        txt_shadow = font.render(str(face), True, (0, 0, 0))
        txt = font.render(str(face), True, (255, 255, 255))

        rect = txt.get_rect(center=(tam // 2, tam // 2))
        rect_s = rect.copy()
        rect_s.x += 2
        rect_s.y += 2

        surf.blit(txt_shadow, rect_s)
        surf.blit(txt, rect)

        self._dado_cache[key] = surf
        return surf

    # ============================================================
    # Push animado
    # ============================================================
    def _queue_push_anim(self, from_c, from_r, to_c, to_r, cell_dict, agora):
        self.push.append({
            "cell": cell_dict,
            "from_pos": self._grid_center(from_c, from_r),
            "to_pos": self._grid_center(to_c, to_r),
            "t0": agora,
            "dur": self.PUSH_MS,
        })

    def _push_chain_animated(self, start_c, start_r, dc, dr, agora):
        chain = []
        c, r = start_c, start_r
        while self._in_bounds(c, r) and self.grid[r][c] is not None:
            chain.append((c, r))
            c += dc
            r += dr

        if not chain:
            return

        beyond_in = self._in_bounds(c, r)

        if beyond_in:
            for i in range(len(chain) - 1, -1, -1):
                sc, sr = chain[i]
                tc, tr = sc + dc, sr + dr
                cell = self.grid[sr][sc]
                self.grid[tr][tc] = cell
                self._queue_push_anim(sc, sr, tc, tr, cell, agora)
            self.grid[start_r][start_c] = None
        else:
            last_c, last_r = chain[-1]
            self.grid[last_r][last_c] = None

            for i in range(len(chain) - 2, -1, -1):
                sc, sr = chain[i]
                tc, tr = sc + dc, sr + dr
                cell = self.grid[sr][sc]
                self.grid[tr][tc] = cell
                self._queue_push_anim(sc, sr, tc, tr, cell, agora)

            self.grid[start_r][start_c] = None

    def _colocar_com_empurrao_animado(self, c, r, novo_cell, dc, dr, agora):
        if self.grid[r][c] is not None:
            self._push_chain_animated(c, r, dc, dr, agora)
        self.grid[r][c] = novo_cell
        # atualiza listas coletáveis
        self._rebuild_listas_dados()

    # ============================================================
    # Lançamento
    # ============================================================
    def _lancar_mao(self, base_pos, base_cell, agora, modo):
        # escolhe mão conforme lado ativo
        mao = self.mao_inimiga if self.lado_ativo == "inimigo" else self.mao_aliada
        if not mao:
            return

        if modo == "normal":
            maxd, pesos, anim = self.NORMAL_MAX, self.NORMAL_PESOS, self.ANIM_NORMAL
        else:
            maxd, pesos, anim = self.FORTE_MAX, self.FORTE_PESOS, self.ANIM_FORTE

        base_c, base_r = base_cell

        # direção do push: normal = pra fora, forte = pro centro
        dc, dr = self._dir_from_center(base_cell)
        if modo == "forte":
            dc, dr = -dc, -dr
        if dc == 0 and dr == 0:
            dc = 1

        usados = set()
        alvos = []
        tent = 0
        n = len(mao)

        while len(alvos) < n and tent < 2200:
            tent += 1
            dx, dy = self._escolher_offset_por_dist(maxd, pesos)
            c = self._clamp(base_c + dx, 0, BOARD_SIZE - 1)
            r = self._clamp(base_r + dy, 0, BOARD_SIZE - 1)
            if (c, r) in usados:
                continue
            usados.add((c, r))
            alvos.append((c, r))
            if len(usados) >= BOARD_SIZE * BOARD_SIZE:
                break

        while len(alvos) < n:
            alvos.append((base_c, base_r))

        for dado, (tc, tr) in zip(mao, alvos):
            faces = dado["faces"]
            face_atual = random.choice(faces)
            face_final = random.choice(faces)

            self.fly.append({
                "dado": dado,
                "lado": self.lado_ativo,

                "pos": (float(base_pos[0]), float(base_pos[1])),
                "start_pos": (float(base_pos[0]), float(base_pos[1])),
                "target_pos": self._grid_center(tc, tr),
                "target_cell": (tc, tr),

                "face": face_atual,
                "face_final": face_final,

                "rolando": True,
                "t_inicio": agora,
                "t_ultima_troca": agora,

                "dur_ms": anim["dur_ms"],
                "troca_min_ms": anim["troca_min_ms"],
                "troca_max_ms": anim["troca_max_ms"],
                "spin_total_deg": anim["spin_total_deg"],

                "angulo": 0.0,
                "angulo_final": 0.0,

                "trail": deque(maxlen=anim["trail_len"]),

                "impacto": False,
                "t_impacto": 0,
                "impacto_ms": 180,

                "push_dc": dc,
                "push_dr": dr,
            })

        mao.clear()

    # ============================================================
    # Update animações
    # ============================================================
    def _update_fly(self, agora):
        rest = []
        for s in self.fly:
            if s["rolando"]:
                t = (agora - s["t_inicio"]) / s["dur_ms"]
                t = self._clamp(t, 0.0, 1.0)
                e = self._ease_out_cubic(t)

                s["trail"].appendleft(s["pos"])

                troca_ms = s["troca_min_ms"] + (s["troca_max_ms"] - s["troca_min_ms"]) * e
                if agora - s["t_ultima_troca"] >= troca_ms:
                    s["face"] = random.choice(s["dado"]["faces"])
                    s["t_ultima_troca"] = agora

                sx, sy = s["start_pos"]
                tx, ty = s["target_pos"]
                s["pos"] = (sx + (tx - sx) * e, sy + (ty - sy) * e)

                s["angulo"] = (1 - e) * s["spin_total_deg"] + e * s["angulo_final"]

                if t >= 1.0:
                    s["rolando"] = False
                    s["face"] = s["face_final"]
                    s["pos"] = s["target_pos"]
                    s["angulo"] = s["angulo_final"]
                    s["trail"].clear()
                    s["impacto"] = True
                    s["t_impacto"] = agora

            elif s["impacto"]:
                dt = (agora - s["t_impacto"]) / s["impacto_ms"]
                dt = self._clamp(dt, 0.0, 1.0)
                yoff = -math.sin(math.pi * dt) * 10.0
                tx, ty = s["target_pos"]
                s["pos"] = (tx, ty + yoff)

                if dt >= 1.0:
                    s["impacto"] = False
                    s["pos"] = s["target_pos"]

            terminou = (not s["rolando"]) and (not s["impacto"])
            if terminou:
                c, r = s["target_cell"]
                d = s["dado"]
                cell = {"attr": d["attr"], "pot": d["pot"], "valor": s["face_final"], "lado": s["lado"]}
                self._colocar_com_empurrao_animado(c, r, cell, s["push_dc"], s["push_dr"], agora)
            else:
                rest.append(s)

        self.fly = rest

        # ============================================================
    # Coleta de dados do grid (para aplicar nos players)
    # ============================================================
    def get_somas_por_lado(self):
        """
        Retorna:
          {
            "aliado":  {attr: soma_valores, ...},
            "inimigo": {attr: soma_valores, ...}
          }
        Somente do que está FIXO no grid (não considera fly/push em voo).
        """
        somas = {
            "aliado":  {k: 0 for k in DICE_TYPES.keys()},
            "inimigo": {k: 0 for k in DICE_TYPES.keys()},
        }

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                cell = self.grid[r][c]
                if cell is None:
                    continue

                lado = cell.get("lado", "aliado")
                attr = cell.get("attr")
                val = int(cell.get("valor", 0))

                if lado not in somas:
                    lado = "aliado"
                if attr in somas[lado]:
                    somas[lado][attr] += val

        return somas

    def esta_estavel(self):
        """
        True quando não tem animação rolando (fly/push vazios).
        Use isso se quiser aplicar stats só quando parar tudo.
        """
        return (len(self.fly) == 0) and (len(self.push) == 0)


    def _update_push(self, agora):
        rest = []
        for p in self.push:
            t = (agora - p["t0"]) / p["dur"]
            if t < 1.0:
                rest.append(p)
        self.push = rest

    # ============================================================
    # Draw
    # ============================================================
    def _draw(self):
        tela = self.tela
        tela.fill((18, 18, 22))

        # grid + hover + dados fixos
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                cor = (190, 190, 190) if (r + c) % 2 == 0 else (120, 120, 120)
                rect = pygame.Rect(
                    BOARD_ORIGIN[0] + c * CELL_SIZE,
                    BOARD_ORIGIN[1] + r * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE
                )
                pygame.draw.rect(tela, cor, rect)

                if self.hover == (c, r):
                    pygame.draw.rect(tela, (255, 230, 120), rect, 5)

                cell = self.grid[r][c]
                if cell is not None:
                    cor_fill = DICE_TYPES[cell["attr"]]
                    lado = cell.get("lado", "aliado")
                    img = self._criar_surface_dado(cell["valor"], DADO_TAM, cor_fill, lado)
                    tela.blit(img, img.get_rect(center=self._grid_center(c, r)))

        pygame.draw.rect(
            tela,
            (60, 60, 70),
            (BOARD_ORIGIN[0], BOARD_ORIGIN[1], BOARD_W, BOARD_H),
            5
        )

        # push overlay
        for p in self.push:
            t = (pygame.time.get_ticks() - p["t0"]) / p["dur"]
            t = self._clamp(t, 0.0, 1.0)
            e = self._ease_out_cubic(t)

            fx, fy = p["from_pos"]
            tx, ty = p["to_pos"]
            pos = (fx + (tx - fx) * e, fy + (ty - fy) * e)

            cell = p["cell"]
            cor_fill = DICE_TYPES[cell["attr"]]
            lado = cell.get("lado", "aliado")
            img = self._criar_surface_dado(cell["valor"], DADO_TAM, cor_fill, lado)
            tela.blit(img, img.get_rect(center=pos))

        # fly overlay
        for s in self.fly:
            cor_fill = DICE_TYPES[s["dado"]["attr"]]
            lado = s.get("lado", "aliado")
            base = self._criar_surface_dado(s["face"], DADO_TAM, cor_fill, lado)

            if s["rolando"]:
                for i, pos in enumerate(s["trail"]):
                    alpha = max(0, 110 - i * 14)
                    if alpha <= 0:
                        break
                    ghost = base.copy()
                    ghost.set_alpha(alpha)
                    tela.blit(ghost, ghost.get_rect(center=pos))

            scale = 1.0
            if s["impacto"]:
                dt = self._clamp((pygame.time.get_ticks() - s["t_impacto"]) / s["impacto_ms"], 0.0, 1.0)
                scale = 1.0 - 0.06 * math.sin(math.pi * dt)

            img = pygame.transform.rotozoom(base, s["angulo"], scale)
            tela.blit(img, img.get_rect(center=s["pos"]))
