import pygame

from Brawl_Stars.Brawl import CORES_RARIDADE, gerar_imagem_cartucho_grid


STAT_FIELDS = [
    ("vida", "HP"),
    ("dano_fisico", "Atk"),
    ("dano_especial", "SpA"),
    ("defesa_fisica", "Def"),
    ("defesa_especial", "SpD"),
    ("mana", "Man"),
    ("regeneracao", "Reg"),
    ("velocidade", "Vel"),
    ("perfuracao", "Perf"),
]

DICE_TYPE_LABEL = {
    "spa": "Dano Especial",
    "spd": "Defesa Especial",
    "atk": "Dano Físico",
    "def": "Defesa Física",
    "per": "Perfuração",
    "reg": "Regeneração",
    "man": "Mana",
    "vel": "Velocidade",
    "": "-",
}

DICE_TYPE_COLOR = {
    "spa": (165, 90, 220),
    "spd": (95, 200, 245),
    "atk": (240, 110, 70),
    "def": (235, 195, 80),
    "per": (220, 80, 95),
    "reg": (80, 220, 120),
    "man": (60, 110, 235),
    "vel": (170, 170, 170),
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


def _render_wrapped_center(surf, font, text, color, rect):
    words = str(text or "").split()
    lines = []
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if font.size(t)[0] <= rect.w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    if not lines:
        return

    line_h = font.get_height() + 2
    total_h = len(lines) * line_h
    y = rect.y + (rect.h - total_h) // 2
    for ln in lines:
        ts = font.render(ln, True, color)
        surf.blit(ts, ts.get_rect(centerx=rect.centerx, y=y))
        y += line_h


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

    st = getattr(cartucho, "stats", {}) or {}
    atributos = []
    for key, label in STAT_FIELDS:
        val = _as_int(st.get(key, 0))
        if val != 0:
            atributos.append(f"{label} {val}")

    left_x = panel_rect.x + 12
    stats_y = panel_rect.y + 112
    for i, txt in enumerate(atributos[:8]):
        ty = stats_y + i * 20
        t = fonte_micro.render(txt, True, (232, 232, 240))
        surf.blit(t, (left_x, ty))

    desc_rect = pygame.Rect(panel_rect.x + 108, panel_rect.y + 110, panel_rect.w - 118, 96)
    pygame.draw.rect(surf, (28, 28, 36), desc_rect, border_radius=8)
    pygame.draw.rect(surf, (75, 75, 95), desc_rect, 1, border_radius=8)

    desc = str(getattr(cartucho, "descricao", "") or "").strip()
    desc_txt = desc if desc else "Sem habilidade"
    desc_color = (220, 220, 230) if desc else (145, 145, 165)
    _render_wrapped_center(surf, fonte_micro, desc_txt, desc_color, desc_rect.inflate(-10, -8))

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
    t_tipo = fonte_micro.render(tipo_label, True, (255, 255, 255))
    surf.blit(t_tipo, (sq_x + 6, dice_rect.y + (dice_rect.h - t_tipo.get_height()) // 2))
