import os
import pygame


def _draw_button(tela, rect, text, font, mouse_pos, pressed=False):
    hover = rect.collidepoint(mouse_pos)
    base = (55, 64, 92)
    hov = (80, 92, 132)
    click = (42, 50, 75)
    color = click if pressed else (hov if hover else base)

    pygame.draw.rect(tela, color, rect, border_radius=16)
    pygame.draw.rect(tela, (170, 188, 235), rect, 3, border_radius=16)

    txt = font.render(text, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def TelaInicial(tela, relogio, estados, config, info=None):
    fonte_path = os.path.join("Fontes", "FontePadrão.ttf")
    fonte_titulo = pygame.font.Font(fonte_path, 78)
    fonte_sub = pygame.font.Font(fonte_path, 28)
    fonte_btn = pygame.font.Font(fonte_path, 34)

    W, H = tela.get_size()
    btn_w, btn_h = 320, 90

    btn_jogar = pygame.Rect(0, 0, btn_w, btn_h)
    btn_config = pygame.Rect(0, 0, btn_w, btn_h)
    btn_sair = pygame.Rect(0, 0, btn_w, btn_h)
    btn_jogar.center = (W // 2, H // 2 + 10)
    btn_config.center = (W // 2, H // 2 + 130)
    btn_sair.center = (W // 2, H // 2 + 250)

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Inicio", False):
        relogio.tick(config.get("FPS", 60))
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        pressed_jogar = False
        pressed_config = False
        pressed_sair = False

        for e in events:
            if e.type == pygame.QUIT:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if btn_jogar.collidepoint(e.pos):
                    pressed_jogar = True
                elif btn_config.collidepoint(e.pos):
                    pressed_config = True
                elif btn_sair.collidepoint(e.pos):
                    pressed_sair = True
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if btn_jogar.collidepoint(e.pos):
                    estados["Inicio"] = False
                    estados["Tematica"] = True
                    rodando = False
                elif btn_config.collidepoint(e.pos):
                    estados["Inicio"] = False
                    estados["Config"] = True
                    estados["RetornoConfig"] = "Inicio"
                    rodando = False
                elif btn_sair.collidepoint(e.pos):
                    estados["Rodando"] = False
                    rodando = False

        tela.fill((14, 14, 22))

        title = fonte_titulo.render("ROLL", True, (236, 242, 255))
        subtitle = fonte_sub.render("Escolha seu caminho", True, (168, 184, 220))
        tela.blit(title, title.get_rect(center=(W // 2, H // 2 - 130)))
        tela.blit(subtitle, subtitle.get_rect(center=(W // 2, H // 2 - 65)))

        _draw_button(tela, btn_jogar, "JOGAR", fonte_btn, mouse_pos, pressed_jogar)
        _draw_button(tela, btn_config, "CONFIG", fonte_btn, mouse_pos, pressed_config)
        _draw_button(tela, btn_sair, "SAIR", fonte_btn, mouse_pos, pressed_sair)

        pygame.display.flip()

    return
