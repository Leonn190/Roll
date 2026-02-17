# Tela_Estrategista.py
import pygame
import random

from Grid import Grid
from Banco import Banco, BANK_CARD_W, BANK_CARD_H
from Loja import Loja
from Painel_Sinergia import PainelSinergia
from Cartucho import Cartucho

from Player import PlayerEstrategista
from Brawl_Stars.Brawl import DECK_DEFS


def _draw_btn_teste(tela, rect, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (120, 72, 168) if hover else (88, 50, 130)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (212, 178, 248), rect, 2, border_radius=12)
    txt = font.render("Teste: Batalha", True, (248, 240, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def TelaEstrategista(tela, relogio, estados, config, info=None):
    grid = Grid(tela)
    banco = Banco(tela)

    deck_defs = [dict(d) for d in DECK_DEFS]
    loja = Loja(tela, deck_defs)
    painel = PainelSinergia(tela)

    # player “dono” da tela
    player = PlayerEstrategista("ALIADO", lado="aliado", ouro_inicial=10)

    # liga referências no player (se existir)
    if hasattr(player, "set_refs"):
        player.set_refs(grid=grid, banco=banco, loja=loja, painel=painel)

    # liga o player no banco/loja (se existir)
    if hasattr(banco, "set_player"):
        banco.set_player(player)
    if hasattr(loja, "set_player"):
        loja.set_player(player)

    # passa o player direto para a grid (pra painel e futuras migrações)
    # (não quebra se a Grid ignorar o parâmetro)
    try:
        grid.set_refs(banco, loja, painel, player=player)
    except TypeError:
        grid.set_refs(banco, loja, painel)
        # fallback: se grid tiver atributo player
        try:
            grid.player = player
        except Exception:
            pass

    # banco inicial: 8 cartas aleatórias
    start_defs = [dict(d) for d in random.sample(DECK_DEFS, k=min(8, len(DECK_DEFS)))]
    for d in start_defs:
        banco.add_to_first_free(Cartucho(d, BANK_CARD_W, BANK_CARD_H))

    # força recálculo inicial
    if not hasattr(grid, "campo_dirty"):
        grid.campo_dirty = True
    else:
        grid.campo_dirty = True

    fonte_btn = pygame.font.Font("Fontes/FontePadrão.ttf", 22)
    btn_teste_batalha = pygame.Rect(16, 92, 220, 52)

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Estrategista", False):
        relogio.tick(config.get("FPS", 60))
        agora = pygame.time.get_ticks()

        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for e in events:
            if e.type == pygame.QUIT:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if btn_teste_batalha.collidepoint(e.pos):
                    estados["Estrategista"] = False
                    estados["Batalha"] = True
                    rodando = False

        # grid continua fazendo drag/place por enquanto
        grid.update(events, agora, mouse_pos)

        # recalcula stats/sinergias só quando o campo muda
        if getattr(grid, "campo_dirty", False):
            if hasattr(player, "sync_from_grid"):
                player.sync_from_grid(agora)
            elif hasattr(player, "atualizar_da_grid"):
                player.atualizar_da_grid(grid, agora)
            grid.campo_dirty = False

        # animações do player
        if hasattr(player, "update"):
            player.update(agora)

        # ficha no topo esquerdo
        if hasattr(player, "draw_ficha"):
            player.draw_ficha(tela, agora, pos=(18, 18))

        # dado arrastado deve ficar na frente da ficha do player
        if hasattr(grid, "draw_dragging_dado_overlay"):
            grid.draw_dragging_dado_overlay(tela, mouse_pos)

        _draw_btn_teste(tela, btn_teste_batalha, fonte_btn, mouse_pos)

        pygame.display.flip()

    return
