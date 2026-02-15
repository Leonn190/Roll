import pygame
import sys
import os
import ctypes

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
config = {
    "FPS": 180,
}

# ============================================================
# IMPORT DAS TELAS
# ============================================================
from Tela_Estrategista import TelaEstrategista
from Tela_Batalha import TelaBatalha

# ============================================================
# ESTADOS (ordem: Estrategista -> Batalha)
# ============================================================
estados = {
    "Rodando": True,
    "Estrategista": True,
    "Batalha": False,
}

# ============================================================
# LOOP PRINCIPAL
# ============================================================
while estados["Rodando"]:
    relogio.tick(config["FPS"])

    if estados.get("Estrategista", False):
        TelaEstrategista(tela, relogio, estados, config)

    elif estados.get("Batalha", False):
        TelaBatalha(tela, relogio, estados, config)

pygame.quit()
sys.exit()


