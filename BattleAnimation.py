import math
import pygame

DANO_CORES = {
    "fisico": (255, 140, 40),
    "magico": (175, 70, 255),
    "regen": (80, 220, 120),
}


def _lerp(a, b, t):
    return a + (b - a) * t


def _proj_pos(origem, destino, t):
    return (_lerp(origem[0], destino[0], t), _lerp(origem[1], destino[1], t))


def draw_bola_ataque(tela, pos, raio, cor):
    x, y = int(pos[0]), int(pos[1])
    pygame.draw.circle(tela, cor, (x, y), raio)
    pygame.draw.circle(tela, (250, 250, 250), (x, y), max(1, raio // 4))

    spikes = 10
    for i in range(spikes):
        ang = (math.pi * 2 * i) / float(spikes)
        ox = int(x + math.cos(ang) * (raio + 3))
        oy = int(y + math.sin(ang) * (raio + 3))
        tx = int(x + math.cos(ang) * (raio + 10))
        ty = int(y + math.sin(ang) * (raio + 10))
        pygame.draw.line(tela, cor, (ox, oy), (tx, ty), 2)


def draw_bola_defesa(tela, pos, raio, cor):
    x, y = int(pos[0]), int(pos[1])
    pygame.draw.circle(tela, cor, (x, y), raio)
    pygame.draw.circle(tela, (245, 245, 255), (x, y), raio, 2)


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
        offset = 28 + int(12 * math.sin(t * math.pi * 2.0))
        p_saida = (atacante[0] + offset, atacante[1] - 28)
        draw_bola_defesa(tela, p_saida, 14, DANO_CORES["regen"])
        return

    cor = DANO_CORES.get(kind, (230, 230, 230))
    bg = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
    bg.fill((*cor, 40))
    tela.blit(bg, (0, 0))

    p_ataque = _proj_pos(atacante, defensor, t)
    p_defesa = _proj_pos(defensor, atacante, min(1.0, t * 0.9))
    raio_ataque = 16 if acao.get("hit", True) else 12
    draw_bola_ataque(tela, p_ataque, raio_ataque, cor)
    draw_bola_defesa(tela, p_defesa, 13, (220, 220, 220))
