import os
import pygame

from VisualEffects import aplicar_filtro_luminosidade


def _draw_button(tela, rect, text, font, mouse_pos, enabled=True):
    hover = rect.collidepoint(mouse_pos)

    if enabled:
        base = (55, 64, 92)
        hov = (80, 92, 132)
        border = (170, 188, 235)
        txt_col = (242, 246, 255)
    else:
        base = (40, 42, 52)
        hov = base
        border = (95, 102, 126)
        txt_col = (168, 172, 186)

    color = hov if hover and enabled else base

    pygame.draw.rect(tela, color, rect, border_radius=16)
    pygame.draw.rect(tela, border, rect, 3, border_radius=16)

    txt = font.render(text, True, txt_col)
    tela.blit(txt, txt.get_rect(center=rect.center))


def TelaTematica(tela, relogio, estados, config, info=None):
    fonte_path = os.path.join("Fontes", "FontePadrão.ttf")
    fonte_titulo = pygame.font.Font(fonte_path, 62)
    fonte_sub = pygame.font.Font(fonte_path, 28)
    fonte_btn = pygame.font.Font(fonte_path, 30)

    W, H = tela.get_size()

    btn_brawl = pygame.Rect(0, 0, 460, 100)
    btn_voltar = pygame.Rect(0, 0, 260, 78)
    btn_brawl.center = (W // 2, H // 2 + 20)
    btn_voltar.center = (W // 2, H // 2 + 170)

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Tematica", False):
        relogio.tick(config.get("FPS", 60))
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        for e in events:
            if e.type == pygame.QUIT:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                estados["Tematica"] = False
                estados["Inicio"] = True
                rodando = False
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if btn_brawl.collidepoint(e.pos):
                    estados["Tematica"] = False
                    estados["Estrategista"] = True
                    rodando = False
                elif btn_voltar.collidepoint(e.pos):
                    estados["Tematica"] = False
                    estados["Inicio"] = True
                    rodando = False

        tela.fill((14, 14, 22))

        title = fonte_titulo.render("Escolha a Temática", True, (236, 242, 255))
        subtitle = fonte_sub.render("Mais opções em breve", True, (168, 184, 220))
        tela.blit(title, title.get_rect(center=(W // 2, H // 2 - 130)))
        tela.blit(subtitle, subtitle.get_rect(center=(W // 2, H // 2 - 80)))

        _draw_button(tela, btn_brawl, "BRAWL STARS", fonte_btn, mouse_pos, enabled=True)
        _draw_button(tela, btn_voltar, "VOLTAR", fonte_btn, mouse_pos, enabled=True)

        aplicar_filtro_luminosidade(tela, config.get("Luminosidade", 75))
        pygame.display.flip()

    return
