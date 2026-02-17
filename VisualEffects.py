import pygame


def aplicar_filtro_luminosidade(tela, luminosidade):
    """Aplica filtro global:
    - 75: sem filtro
    - >75: clareia com branco (leve até 100)
    - <75: escurece com preto
    """
    valor = max(0, min(100, int(luminosidade)))
    if valor == 75:
        return

    overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)

    if valor > 75:
        # no máximo bem leve (até alpha 55)
        alpha = int(((valor - 75) / 25) * 55)
        overlay.fill((255, 255, 255, alpha))
    else:
        # escurece progressivamente até alpha 170
        alpha = int(((75 - valor) / 75) * 170)
        overlay.fill((0, 0, 0, alpha))

    tela.blit(overlay, (0, 0))
