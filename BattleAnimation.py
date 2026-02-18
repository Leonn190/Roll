import math
import pygame

DANO_CORES = {
    "fisico": (255, 140, 40),
    "magico": (175, 70, 255),
    "regen": (80, 220, 120),
}

RAIO_ATAQUE = 30
RAIO_DEFESA = 24
RAIO_ATAQUE_POS_COLISAO = 26
RAIO_ATAQUE_MIN = 10


def _lerp(a, b, t):
    return a + (b - a) * t


def _proj_pos(origem, destino, t):
    return (_lerp(origem[0], destino[0], t), _lerp(origem[1], destino[1], t))


def _cor_texto_contraste(cor_fundo):
    r, g, b = cor_fundo
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return (20, 20, 24) if luminancia > 150 else (248, 248, 252)


def _dist(a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.hypot(dx, dy)


def _draw_valor(tela, pos, valor, cor=(255, 255, 255)):
    if valor is None:
        return
    texto = str(int(valor))
    font = pygame.font.Font("Fontes/FontePadrão.ttf", 22)
    surf_contorno = font.render(texto, True, (0, 0, 0))
    surf = font.render(texto, True, cor)
    rect = surf.get_rect(center=(int(pos[0]), int(pos[1])))
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        tela.blit(surf_contorno, rect.move(dx, dy))
    tela.blit(surf, rect)


def draw_bola_ataque(tela, pos, raio, cor, valor=None):
    x, y = int(pos[0]), int(pos[1])

    spikes = 12
    pts = []
    for i in range(spikes * 2):
        ang = (math.pi * 2 * i) / float(spikes * 2)
        r = raio + 8 if i % 2 == 0 else max(raio - 3, 3)
        pts.append((int(x + math.cos(ang) * r), int(y + math.sin(ang) * r)))

    pygame.draw.polygon(tela, cor, pts)
    pygame.draw.polygon(tela, (255, 255, 255), pts, 2)
    pygame.draw.circle(tela, (250, 250, 250), (x, y), max(3, raio // 4))
    _draw_valor(tela, (x, y), valor, _cor_texto_contraste(cor))


def draw_bola_defesa(tela, pos, raio, cor, valor=None):
    x, y = int(pos[0]), int(pos[1])
    pygame.draw.circle(tela, cor, (x, y), raio)
    pygame.draw.circle(tela, (245, 245, 255), (x, y), raio, 2)
    _draw_valor(tela, (x, y), valor, _cor_texto_contraste(cor))


def build_anim_steps(logs):
    steps = []
    for nome_a, nome_d, info_hit in logs:
        steps.append(
            {
                "attacker": nome_a,
                "defender": nome_d,
                "kind": info_hit.get("kind", "fisico"),
                "hit": bool(info_hit.get("hit", True)),
                "damage": int(info_hit.get("damage", 0) or 0),
                "raw_damage": int(info_hit.get("raw_damage", info_hit.get("damage", 0)) or 0),
                "defense_block": int(info_hit.get("defense_block", 0) or 0),
                "heal": int(info_hit.get("heal", 0) or 0),
                "applied": False,
            }
        )
    return steps


def draw_acao_batalha(tela, acao, t, pos_por_nome):
    atacante = pos_por_nome.get(acao["attacker"])
    defensor = pos_por_nome.get(acao["defender"])
    if atacante is None or defensor is None:
        return

    kind = acao.get("kind", "fisico")
    if kind == "regen":
        raio = 21
        loop_t = min(1.0, t)
        ida_t = loop_t * 2.0 if loop_t <= 0.5 else (1.0 - loop_t) * 2.0
        ang = math.pi * ida_t
        r = 40
        p_saida = (atacante[0] + math.cos(ang) * r, atacante[1] - math.sin(ang) * (r * 0.6))
        draw_bola_defesa(tela, p_saida, raio, DANO_CORES["regen"], acao.get("heal", 0))
        return

    cor = DANO_CORES.get(kind, (230, 230, 230))
    bg = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    bg.fill((*cor, 40))
    tela.blit(bg, (0, 0))

    collide_t = float(acao.get("collide_t", 0.5))
    ataque_total = acao.get("raw_damage", acao.get("damage", 0))
    ataque_final = acao.get("damage", 0)
    defesa_valor = acao.get("defense_block", 0)
    p_impacto = _proj_pos(atacante, defensor, collide_t)

    if t <= collide_t:
        fase = min(1.0, t / max(0.001, collide_t))
        p_ataque = _proj_pos(atacante, defensor, fase * collide_t)
        p_defesa = _proj_pos(defensor, atacante, fase * collide_t)
        draw_bola_ataque(tela, p_ataque, RAIO_ATAQUE, cor, ataque_total)
        # defesa some no exato frame da colisão
        if t < collide_t:
            draw_bola_defesa(tela, p_defesa, RAIO_DEFESA, (225, 228, 238), defesa_valor)
        return

    hit = bool(acao.get("hit", True))
    if hit:
        resto_t = (t - collide_t) / max(0.001, 1.0 - collide_t)

        # 1) após colisão, ataque segue para a ficha e vai reduzindo pelo bloqueio
        if resto_t <= 0.35:
            fase_ida = resto_t / 0.35
            p_ataque = _proj_pos(p_impacto, defensor, fase_ida)
            valor_animado = max(ataque_final, round(_lerp(ataque_total, ataque_final, fase_ida)))
            raio = int(_lerp(RAIO_ATAQUE_POS_COLISAO, 20, fase_ida))
            draw_bola_ataque(tela, p_ataque, raio, cor, valor_animado)
            return

        # 2) na ficha, ataque vai sumindo enquanto o dano é "aplicado"
        fase_aplica = min(1.0, (resto_t - 0.35) / 0.65)
        valor_animado = max(0, round(_lerp(ataque_final, 0, fase_aplica)))
        raio = int(_lerp(20, RAIO_ATAQUE_MIN, fase_aplica))
        draw_bola_ataque(tela, defensor, raio, cor, valor_animado)
    else:
        # errou: as duas bolas somem após cruzar
        sumir_t = (t - collide_t) / max(0.001, 1.0 - collide_t)
        if sumir_t < 0.4:
            p_ataque = _proj_pos(atacante, defensor, collide_t)
            p_defesa = _proj_pos(defensor, atacante, collide_t)
            draw_bola_ataque(tela, p_ataque, RAIO_ATAQUE_MIN, cor, 0)
            draw_bola_defesa(tela, p_defesa, max(8, RAIO_DEFESA - 8), (225, 228, 238), 0)


def calc_collision_t(atacante, defensor, *, raio_ataque=RAIO_ATAQUE, raio_defesa=RAIO_DEFESA):
    # aproximação por amostragem curta para sincronizar colisão visual
    for i in range(1, 100):
        t = i / 100.0
        p_ataque = _proj_pos(atacante, defensor, t)
        p_defesa = _proj_pos(defensor, atacante, t)
        if _dist(p_ataque, p_defesa) <= (raio_ataque + raio_defesa):
            return t
    return 0.5
