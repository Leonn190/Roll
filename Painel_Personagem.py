import pygame
import os

from Brawl_Stars.Brawl import CORES_RARIDADE, gerar_imagem_cartucho_grid

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
    fonte_micro = fontes["micro"]

    pygame.draw.rect(surf, (20, 20, 26), panel_rect, border_radius=12)
    pygame.draw.rect(surf, (90, 90, 110), panel_rect, 2, border_radius=12)

    portrait_rect = pygame.Rect(panel_rect.x + 10, panel_rect.y + 10, 92, 92)
    img = gerar_imagem_cartucho_grid(cartucho.dados, (portrait_rect.w, portrait_rect.h))
    surf.blit(img, portrait_rect.topleft)

    info_x = portrait_rect.right + 10
    nome = fonte_titulo.render(cartucho.nome, True, (245, 245, 250))
    nome_pos = (info_x, panel_rect.y + 10)
    surf.blit(nome, nome_pos)

    stars = max(0, min(3, int(getattr(cartucho, "estrelas", 0) or 0)))
    if stars > 0:
        icon_size = max(10, min(18, nome.get_height() - 2))
        icon = _get_star_icon(icon_size)
        sx = nome_pos[0] + nome.get_width() + 8
        sy = nome_pos[1] + (nome.get_height() - icon_size) // 2
        for i in range(stars):
            pos = (sx + i * (icon_size + 2), sy)
            if icon is not None:
                surf.blit(icon, pos)
            else:
                fb = fonte_micro.render("★", True, (255, 230, 120))
                surf.blit(fb, pos)

    raridade = str(getattr(cartucho, "raridade", "comum") or "comum").upper()
    tr = fonte_micro.render(f"Raridade: {raridade}", True, _raridade_cor(cartucho))
    rar_y = panel_rect.y + 38
    surf.blit(tr, (info_x, rar_y))

    syns = list(getattr(cartucho, "sinergias", []) or [])
    syn_x = info_x + tr.get_width() + 12
    syn_text = " / ".join(syns) if syns else "Sem sinergia"
    syn_color = (210, 210, 225) if syns else (165, 165, 180)
    syn_rect = pygame.Rect(
        syn_x,
        panel_rect.y + 8,
        panel_rect.right - 12 - syn_x,
        portrait_rect.bottom - panel_rect.y - 8,
    )
    if syn_rect.w > 20:
        _render_wrapped_center(surf, fonte_micro, syn_text, syn_color, syn_rect)


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

    desc_rect = pygame.Rect(panel_rect.x + 108, panel_rect.y + 96, panel_rect.w - 118, 78)
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
    dice_rect = pygame.Rect(desc_rect.x, desc_rect.bottom + 8, desc_rect.w, 30)
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
