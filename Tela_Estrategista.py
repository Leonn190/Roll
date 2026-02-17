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
from VisualEffects import aplicar_filtro_luminosidade


def _draw_btn_teste(tela, rect, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (120, 72, 168) if hover else (88, 50, 130)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (212, 178, 248), rect, 2, border_radius=12)
    txt = font.render("Pronto", True, (248, 240, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def _draw_pause_btn(tela, rect, label, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (80, 92, 132) if hover else (55, 64, 92)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (170, 188, 235), rect, 2, border_radius=12)
    txt = font.render(label, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def TelaEstrategista(tela, relogio, estados, config, info=None):
    grid = Grid(tela)
    banco = Banco(tela)

    deck_defs = [dict(d) for d in DECK_DEFS]
    loja = Loja(tela, deck_defs)
    painel = PainelSinergia(tela)

    # player “dono” da tela
    player = PlayerEstrategista("ALIADO", lado="aliado", ouro_inicial=10)

    dados_player = (info or {}).get("player_aliado") if isinstance(info, dict) else None
    if isinstance(dados_player, dict) and hasattr(player, "carregar_estado_compartilhado"):
        player.carregar_estado_compartilhado(dados_player)

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
    fonte_pausa = pygame.font.Font("Fontes/FontePadrão.ttf", 30)
    btn_teste_batalha = pygame.Rect(0, 0, 220, 52)

    pausa_ativa = False
    btn_quitar = pygame.Rect(0, 0, 240, 70)
    btn_voltar = pygame.Rect(0, 0, 240, 70)
    btn_config = pygame.Rect(0, 0, 240, 70)

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
                pausa_ativa = not pausa_ativa
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if pausa_ativa:
                    if btn_quitar.collidepoint(e.pos):
                        estados["Estrategista"] = False
                        estados["Inicio"] = True
                        rodando = False
                    elif btn_voltar.collidepoint(e.pos):
                        pausa_ativa = False
                    elif btn_config.collidepoint(e.pos):
                        estados["Estrategista"] = False
                        estados["Config"] = True
                        estados["RetornoConfig"] = "Estrategista"
                        rodando = False
                elif btn_teste_batalha.collidepoint(e.pos):
                    if isinstance(info, dict) and hasattr(player, "exportar_estado_compartilhado"):
                        info["player_aliado"] = player.exportar_estado_compartilhado()
                    estados["Estrategista"] = False
                    estados["Batalha"] = True
                    rodando = False

        grid_rect = grid.rect()
        btn_teste_batalha.center = (grid_rect.centerx, grid_rect.bottom + 30)

        if not pausa_ativa:
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

        if not pausa_ativa:
            # ficha no topo esquerdo
            if hasattr(player, "draw_ficha"):
                player.draw_ficha(tela, agora, pos=(18, 18))

            # dado arrastado deve ficar na frente da ficha do player
            if hasattr(grid, "draw_dragging_dado_overlay"):
                grid.draw_dragging_dado_overlay(tela, mouse_pos)

            _draw_btn_teste(tela, btn_teste_batalha, fonte_btn, mouse_pos)

        if pausa_ativa:
            escurecer = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            escurecer.fill((0, 0, 0, 190))
            tela.blit(escurecer, (0, 0))

            cx, cy = tela.get_width() // 2, tela.get_height() // 2
            btn_quitar.center = (cx, cy - 90)
            btn_voltar.center = (cx, cy)
            btn_config.center = (cx, cy + 90)
            _draw_pause_btn(tela, btn_quitar, "Quitar", fonte_pausa, mouse_pos)
            _draw_pause_btn(tela, btn_voltar, "Voltar", fonte_pausa, mouse_pos)
            _draw_pause_btn(tela, btn_config, "Config", fonte_pausa, mouse_pos)

        aplicar_filtro_luminosidade(tela, config.get("Luminosidade", 75))
        pygame.display.flip()

    return
