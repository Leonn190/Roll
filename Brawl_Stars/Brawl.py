# Brawl_Stars/Brawl.py
import os
import re
import csv
import unicodedata
import pygame

# ============================================================
# CAMINHOS
# ============================================================
BASE_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.join(BASE_DIR, "Cartuchos")
CSV_PATH = os.path.join(BASE_DIR, "Brawl_Stats.csv")

# ============================================================
# CONFIG VISUAL
# ============================================================
CORES_RARIDADE = {
    "comum": (140, 140, 150),
    "incomum": (70, 190, 110),
    "raro": (80, 140, 235),
    "épico": (165, 90, 220),
    "lendário": (245, 210, 90),
    "mítico": (230, 80, 80),
}

UI_PRETO = (0, 0, 0)
UI_BRANCO = (255, 255, 255)

# --- AJUSTES (como você pediu agora) ---
BORDA_PRETA_ESP = 3          # borda fina PRETA (uma só)
BARRA_NOME_ALPHA = 180       # faixa preta do nome MAIS OPACA

# ============================================================
# CSV -> CARTUCHOS (com stats)
# ============================================================
_RARIDADE_MAP = {
    "comum": "comum",
    "incomum": "incomum",
    "raro": "raro",
    "epico": "épico",
    "épico": "épico",
    "lendario": "lendário",
    "lendário": "lendário",
    "mitico": "mítico",
    "mítico": "mítico",
}

def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def slugify_id(nome: str) -> str:
    """
    ID/arquivo seguro:
      - minúsculo
      - sem acentos
      - espaços/pontuação viram _
      - só [a-z0-9_]
    """
    s = (nome or "").strip().lower()
    s = _strip_accents(s)
    s = s.replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _parse_int(v: str):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None

def _normalizar_raridade(r: str) -> str:
    key = _strip_accents((r or "").strip().lower())
    return _RARIDADE_MAP.get(key, "comum")

def carregar_cartuchos_de_csv(caminho_csv: str) -> list[dict]:
    """
    Lê Brawl_Stats.csv e devolve CARTUCHOS no padrão:
      {
        "id": "...",
        "nome": "NOME",
        "raridade": "épico|raro|...",
        "características": ["Sinergia1", "Sinergia2", ...],
        "imagem": "<slug>_portrait.png",
        "stats": { ... }
      }
    """
    cartuchos: list[dict] = []

    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"CSV não encontrado: {caminho_csv}")

    with open(caminho_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            nome_raw = (row.get("Nome") or "").strip()
            if not nome_raw:
                continue

            slug = slugify_id(nome_raw)

            # sinergias (somente as não vazias), na ordem 1..4
            sinergias = []
            for k in ("Sinergia 1", "Sinergia 2", "Sinergia 3", "Sinergia 4"):
                val = (row.get(k) or "").strip()
                if val:
                    sinergias.append(val)

            rar = _normalizar_raridade(row.get("Raridade"))

            stats = {
                "vida": _parse_int(row.get("Vida")),
                "dano_fisico": _parse_int(row.get("Dano fisico")),
                "dano_especial": _parse_int(row.get("Dano Especial")),
                "defesa_fisica": _parse_int(row.get("Defesa fisica")),
                "defesa_especial": _parse_int(row.get("Defesa especial")),
                "mana": _parse_int(row.get("Mana")),
                "regeneracao": _parse_int(row.get("Regeneração")),
                "velocidade": _parse_int(row.get("Velocidade")),
                "perfuracao": _parse_int(row.get("Perfuração")),
                "total": _parse_int(row.get("total")),
            }

            cartuchos.append({
                "id": slug,
                "nome": nome_raw.upper(),
                "raridade": rar,                       # bate com CORES_RARIDADE (com acento)
                "características": sinergias,          # sinergias do CSV
                "imagem": f"{slug}_portrait.png",      # sempre "<nome>_portrait.png" (em slug)
                "stats": stats,                        # stats completos
            })

    return cartuchos

# ------------------------------------------------------------
# DADOS (agora vem do CSV)
# ------------------------------------------------------------
CARTUCHOS = carregar_cartuchos_de_csv(CSV_PATH)
DECK_DEFS = [dict(c) for c in CARTUCHOS]

# ============================================================
# CACHE
# ============================================================
_cache_imgs: dict[str, pygame.Surface | None] = {}
_cache_cartuchos: dict[tuple, pygame.Surface] = {}
_cache_grid: dict[tuple, pygame.Surface] = {}

# ============================================================
# HELPERS
# ============================================================
def _carregar_imagem(nome_arquivo: str) -> pygame.Surface | None:
    if not nome_arquivo:
        return None
    if nome_arquivo in _cache_imgs:
        return _cache_imgs[nome_arquivo]

    caminho = os.path.join(IMG_DIR, nome_arquivo)
    if not os.path.exists(caminho):
        _cache_imgs[nome_arquivo] = None
        return None

    img = pygame.image.load(caminho).convert_alpha()
    _cache_imgs[nome_arquivo] = img
    return img

def _cobrir_crop_central(img: pygame.Surface | None, w: int, h: int) -> pygame.Surface:
    """Corta centralizado pra preencher (cover) mantendo proporção."""
    if img is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        return s

    iw, ih = img.get_width(), img.get_height()
    if iw <= 0 or ih <= 0:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        return s

    escala = max(w / iw, h / ih)
    nw, nh = int(iw * escala), int(ih * escala)
    scaled = pygame.transform.smoothscale(img, (nw, nh))

    x = (nw - w) // 2
    y = (nh - h) // 2

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(scaled, (-x, -y))
    return out

def _cor_raridade(raridade: str):
    r = (raridade or "comum").lower().strip()
    return CORES_RARIDADE.get(r, CORES_RARIDADE["comum"])

def _render_text_scaled(font: pygame.font.Font, text: str, color, scale: float):
    surf = font.render(text, True, color)
    if scale >= 0.999:
        return surf
    w = max(1, int(surf.get_width() * scale))
    h = max(1, int(surf.get_height() * scale))
    return pygame.transform.smoothscale(surf, (w, h))

# ============================================================
# API: cartucho (loja/banco)
# ============================================================
def gerar_imagem_cartucho(
    dados: dict,
    tamanho: tuple[int, int],
    fonte_nome: pygame.font.Font,
    fonte_carac: pygame.font.Font
) -> pygame.Surface:
    """
    Regras:
      - FUNDO = cor da raridade
      - IMAGEM começa no (0,0) e cobre a área (sem margem)
      - faixa do nome por cima (preta)
      - borda PRETA fina por cima de tudo (uma só)
    """
    w, h = int(tamanho[0]), int(tamanho[1])

    nome = str(dados.get("nome", "???")).upper()
    raridade = str(dados.get("raridade", "comum")).lower().strip()

    caracs = dados.get("características", [])
    if not isinstance(caracs, (list, tuple)):
        caracs = []
    caracs = [str(x) for x in caracs][:4]

    arquivo_img = str(dados.get("imagem", "")).strip()

    chave = ("CARD", nome, raridade, tuple(caracs), arquivo_img, w, h, BORDA_PRETA_ESP, BARRA_NOME_ALPHA)
    if chave in _cache_cartuchos:
        return _cache_cartuchos[chave]

    cor_r = _cor_raridade(raridade)

    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    # 1) FUNDO raridade
    surf.fill(cor_r)

    # 2) IMAGEM por cima, SEM margem
    img = _carregar_imagem(arquivo_img)
    portrait = _cobrir_crop_central(img, w, h)
    surf.blit(portrait, (0, 0))

    # 3) faixa do nome
    barra_h = int(h * 0.20)
    barra = pygame.Rect(0, h - barra_h, w, barra_h)
    barra_s = pygame.Surface((barra.w, barra.h), pygame.SRCALPHA)
    barra_s.fill((0, 0, 0, BARRA_NOME_ALPHA))
    surf.blit(barra_s, barra.topleft)

    # nome menor
    tn = _render_text_scaled(fonte_nome, nome, UI_BRANCO, scale=0.82)
    surf.blit(tn, tn.get_rect(center=barra.center))

    # 4) características (canto direito)
    x_right = w - (BORDA_PRETA_ESP + 6)
    y = BORDA_PRETA_ESP + 6
    for t in caracs:
        texto = fonte_carac.render(t, True, UI_BRANCO)
        sombra = fonte_carac.render(t, True, (0, 0, 0))
        surf.blit(sombra, sombra.get_rect(topright=(x_right + 1, y + 1)))
        surf.blit(texto, texto.get_rect(topright=(x_right, y)))
        y += texto.get_height() + 2

    # 5) BORDA PRETA
    if BORDA_PRETA_ESP > 0:
        pygame.draw.rect(surf, UI_PRETO, pygame.Rect(0, 0, w, h), BORDA_PRETA_ESP)

    _cache_cartuchos[chave] = surf
    return surf

# ============================================================
# API: cartucho da GRID (só imagem)
# ============================================================
def gerar_imagem_cartucho_grid(dados: dict, tamanho: tuple[int, int]) -> pygame.Surface:
    """
    GRID (sempre QUADRADA):
      - FUNDO = cor da raridade
      - IMAGEM por cima SEM margem (cover total)
      - BORDA PRETA fina por cima (uma só)
    """
    lado = int(min(tamanho[0], tamanho[1]))
    w = h = lado

    raridade = str(dados.get("raridade", "comum")).lower().strip()
    arquivo_img = str(dados.get("imagem", "")).strip()

    chave = ("GRID", raridade, arquivo_img, lado, BORDA_PRETA_ESP)
    if chave in _cache_grid:
        return _cache_grid[chave]

    cor_r = _cor_raridade(raridade)

    surf = pygame.Surface((lado, lado), pygame.SRCALPHA)

    # 1) FUNDO raridade
    surf.fill(cor_r)

    # 2) IMAGEM por cima
    img = _carregar_imagem(arquivo_img)
    portrait = _cobrir_crop_central(img, lado, lado)
    surf.blit(portrait, (0, 0))

    # 3) BORDA PRETA por último
    if BORDA_PRETA_ESP > 0:
        pygame.draw.rect(surf, UI_PRETO, pygame.Rect(0, 0, lado, lado), BORDA_PRETA_ESP)

    _cache_grid[chave] = surf
    return surf
