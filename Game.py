import pygame
import sys
import ctypes

from ConfigStore import load_config

try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

pygame.init()

# ============================================================
# TELA / CLOCK
# ============================================================
tela = pygame.display.set_mode((1920, 1080))  # se quiser sem borda: pygame.NOFRAME
pygame.display.set_caption("Jogo - Protótipo")
relogio = pygame.time.Clock()

# ============================================================
# CONFIG / INFO
# ============================================================
config = load_config()

# ============================================================
# IMPORT DAS TELAS
# ============================================================
from Tela_Inicial import TelaInicial
from Tela_Tematica import TelaTematica
from Tela_Estrategista import TelaEstrategista
from Tela_Batalha import TelaBatalha
from Tela_Config import TelaConfig


def _estado_ativo(estados):
    for key in ("Inicio", "Tematica", "Estrategista", "Batalha", "Config"):
        if estados.get(key, False):
            return key
    return None


def _fade(tela, relogio, config, fade_in=True, dur_ms=320):
    W, H = tela.get_size()
    overlay = pygame.Surface((W, H))
    overlay.fill((0, 0, 0))

    passos = 24
    for i in range(passos + 1):
        relogio.tick(config.get("FPS", 60))
        t = i / passos
        alpha = int((1 - t) * 255) if fade_in else int(t * 255)
        overlay.set_alpha(max(0, min(255, alpha)))
        tela.blit(overlay, (0, 0))
        pygame.display.flip()
        pygame.time.delay(max(1, dur_ms // passos))


# ============================================================
# ESTADOS (ordem: Inicio -> Tematica -> Estrategista -> Batalha)
# ============================================================
estados = {
    "Rodando": True,
    "Inicio": True,
    "Tematica": False,
    "Estrategista": False,
    "Batalha": False,
    "Config": False,
    "RetornoConfig": "Inicio",
}

# ============================================================
# LOOP PRINCIPAL
# ============================================================
ultima_tela = None
while estados["Rodando"]:
    relogio.tick(config["FPS"])

    atual = _estado_ativo(estados)
    if atual is None:
        estados["Rodando"] = False
        break

    if atual != ultima_tela:
        _fade(tela, relogio, config, fade_in=True)
        ultima_tela = atual

    if estados.get("Inicio", False):
        TelaInicial(tela, relogio, estados, config)
    elif estados.get("Tematica", False):
        TelaTematica(tela, relogio, estados, config)
    elif estados.get("Estrategista", False):
        TelaEstrategista(tela, relogio, estados, config)
    elif estados.get("Batalha", False):
        TelaBatalha(tela, relogio, estados, config)
    elif estados.get("Config", False):
        TelaConfig(tela, relogio, estados, config)

    proxima = _estado_ativo(estados)
    if estados.get("Rodando", False) and proxima != ultima_tela:
        _fade(tela, relogio, config, fade_in=False)
        ultima_tela = None

pygame.quit()
sys.exit()
