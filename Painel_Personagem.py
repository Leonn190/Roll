import pygame

from Brawl_Stars.Brawl import CORES_RARIDADE, gerar_imagem_cartucho_grid


STAT_FIELDS = [
    ("vida", "HP"),
    ("dano_fisico", "Atk"),
    ("dano_especial", "SpA"),
    ("defesa_fisica", "Def"),
    ("defesa_especial", "SpD"),
    ("mana", "Mana"),
    ("regeneracao", "Regen"),
    ("velocidade", "Vel"),
    ("perfuracao", "Perf"),
]

DICE_TYPE_LABEL = {
    "spa": "Dano Especial",
    "spd": "Defesa Especial",
    "atk": "Dano Físico",
    "def": "Defesa Física",
    "per": "Perfuração",
    "": "-",
}

DICE_TYPE_COLOR = {
    "spa": (165, 90, 220),
    "spd": (95, 200, 245),
    "atk": (240, 110, 70),
    "def": (235, 195, 80),
    "per": (220, 80, 95),
    "": (80, 80, 95),
}


def _as_int(v):
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _raridade_cor(cartucho):
    rar = str(getattr(cartucho, "raridade", "comum") or "comum").lower().strip()
    return CORES_RARIDADE.get(rar, CORES_RARIDADE["comum"])


def draw_painel_personagem(surf, panel_rect, cartucho, fontes):
    """Desenha a ficha de hover de personagem."""
    fonte_titulo = fontes["titulo"]
    fonte_txt = fontes["txt"]
    fonte_micro = fontes["micro"]

    pygame.draw.rect(surf, (20, 20, 26), panel_rect, border_radius=12)
    pygame.draw.rect(surf, (90, 90, 110), panel_rect, 2, border_radius=12)

    portrait_rect = pygame.Rect(panel_rect.x + 10, panel_rect.y + 10, 92, 92)
    img = gerar_imagem_cartucho_grid(cartucho.dados, (portrait_rect.w, portrait_rect.h))
    surf.blit(img, portrait_rect.topleft)

    nome = fonte_titulo.render(cartucho.nome, True, (245, 245, 250))
    surf.blit(nome, (portrait_rect.right + 10, panel_rect.y + 10))

    raridade = str(getattr(cartucho, "raridade", "comum") or "comum").upper()
    tr = fonte_micro.render(f"Raridade: {raridade}", True, _raridade_cor(cartucho))
    surf.blit(tr, (portrait_rect.right + 10, panel_rect.y + 36))

    syns = list(getattr(cartucho, "sinergias", []) or [])
    if syns:
        if len(syns) > 2:
            syn_linha1 = " / ".join(syns[:2])
            syn_linha2 = " / ".join(syns[2:])
            s1 = fonte_txt.render(syn_linha1, True, (210, 210, 225))
            s2 = fonte_txt.render(syn_linha2, True, (210, 210, 225))
            surf.blit(s1, (portrait_rect.right + 10, panel_rect.y + 56))
            surf.blit(s2, (portrait_rect.right + 10, panel_rect.y + 76))
        else:
            syn = fonte_txt.render(" / ".join(syns), True, (210, 210, 225))
            surf.blit(syn, (portrait_rect.right + 10, panel_rect.y + 62))
    else:
        syn = fonte_txt.render("Sem sinergia", True, (210, 210, 225))
        surf.blit(syn, (portrait_rect.right + 10, panel_rect.y + 62))

    # atributos: apenas os não zerados
    st = getattr(cartucho, "stats", {}) or {}
    atributos = []
    for key, label in STAT_FIELDS:
        val = _as_int(st.get(key, 0))
        if val != 0:
            atributos.append(f"{label} {val}")

    stats_y = panel_rect.y + 108
    for i, txt in enumerate(atributos[:6]):
        tx = panel_rect.x + 10 + (i % 2) * 145
        ty = stats_y + (i // 2) * 20
        t = fonte_micro.render(txt, True, (232, 232, 240))
        surf.blit(t, (tx, ty))

    # bloco de dado no fundo
    tipo = str(getattr(cartucho, "tipo_dado", "") or "").strip().lower()
    dado = list(getattr(cartucho, "dado", []) or [])
    while len(dado) < 6:
        dado.append("-")
    dado = dado[:6]

    dado_bg = DICE_TYPE_COLOR.get(tipo, DICE_TYPE_COLOR[""])
    dice_rect = pygame.Rect(panel_rect.x + 10, panel_rect.bottom - 44, panel_rect.w - 20, 30)
    pygame.draw.rect(surf, dado_bg, dice_rect, border_radius=8)
    pygame.draw.rect(surf, (18, 18, 22), dice_rect, 2, border_radius=8)

    sq_size = 20
    sq_gap = 4
    sq_x = dice_rect.x + 8
    sq_y = dice_rect.y + (dice_rect.h - sq_size) // 2
    for face in dado:
        sq = pygame.Rect(sq_x, sq_y, sq_size, sq_size)
        pygame.draw.rect(surf, (20, 20, 26), sq, border_radius=4)
        pygame.draw.rect(surf, (230, 230, 235), sq, 1, border_radius=4)
        txt = fonte_micro.render(str(face), True, (245, 245, 250))
        surf.blit(txt, txt.get_rect(center=sq.center))
        sq_x += sq_size + sq_gap

    tipo_label = DICE_TYPE_LABEL.get(tipo, "-")
    t_tipo = fonte_micro.render(f"{tipo.upper() or '-'} ({tipo_label})", True, (255, 255, 255))
    surf.blit(t_tipo, (sq_x + 6, dice_rect.y + (dice_rect.h - t_tipo.get_height()) // 2))
