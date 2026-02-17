import os
import pygame

from ConfigStore import save_config


def _draw_button(tela, rect, text, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (80, 92, 132) if hover else (55, 64, 92)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (170, 188, 235), rect, 2, border_radius=12)
    txt = font.render(text, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def _draw_setting_row(tela, y, label, key, config, fonte_label, fonte_valor, mouse_pos):
    W = tela.get_width()
    left_btn = pygame.Rect(W // 2 - 260, y, 64, 56)
    right_btn = pygame.Rect(W // 2 + 196, y, 64, 56)

    txt_label = fonte_label.render(label, True, (230, 236, 250))
    tela.blit(txt_label, (W // 2 - 180, y + 10))

    value = str(config.get(key, 0))
    txt_val = fonte_valor.render(value, True, (255, 255, 255))
    tela.blit(txt_val, txt_val.get_rect(center=(W // 2 + 120, y + 28)))

    _draw_button(tela, left_btn, "-", fonte_valor, mouse_pos)
    _draw_button(tela, right_btn, "+", fonte_valor, mouse_pos)

    return left_btn, right_btn


def TelaConfig(tela, relogio, estados, config, info=None):
    fonte_path = os.path.join("Fontes", "FontePadrão.ttf")
    fonte_titulo = pygame.font.Font(fonte_path, 62)
    fonte_label = pygame.font.Font(fonte_path, 34)
    fonte_valor = pygame.font.Font(fonte_path, 38)
    fonte_btn = pygame.font.Font(fonte_path, 30)

    W, H = tela.get_size()
    btn_voltar = pygame.Rect(0, 0, 240, 78)
    btn_voltar.center = (W // 2, H - 120)

    ajustes = {
        "Volume": 5,
        "FPS": 30,
        "Luminosidade": 5,
    }
    limites = {
        "Volume": (0, 100),
        "FPS": (30, 240),
        "Luminosidade": (0, 100),
    }

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Config", False):
        relogio.tick(config.get("FPS", 60))
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        botoes = {}

        tela.fill((14, 14, 22))
        title = fonte_titulo.render("Configurações", True, (236, 242, 255))
        tela.blit(title, title.get_rect(center=(W // 2, 150)))

        botoes["Volume-"] , botoes["Volume+"] = _draw_setting_row(
            tela, 290, "Volume", "Volume", config, fonte_label, fonte_valor, mouse_pos
        )
        botoes["FPS-"] , botoes["FPS+"] = _draw_setting_row(
            tela, 390, "FPS", "FPS", config, fonte_label, fonte_valor, mouse_pos
        )
        botoes["Luminosidade-"] , botoes["Luminosidade+"] = _draw_setting_row(
            tela, 490, "Luminosidade", "Luminosidade", config, fonte_label, fonte_valor, mouse_pos
        )

        _draw_button(tela, btn_voltar, "VOLTAR", fonte_btn, mouse_pos)

        for e in events:
            if e.type == pygame.QUIT:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                estados["Config"] = False
                estados[estados.get("RetornoConfig", "Inicio")] = True
                rodando = False
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if btn_voltar.collidepoint(e.pos):
                    estados["Config"] = False
                    estados[estados.get("RetornoConfig", "Inicio")] = True
                    rodando = False
                    break

                for chave, rect in botoes.items():
                    if not rect.collidepoint(e.pos):
                        continue
                    nome = chave[:-1]
                    oper = chave[-1]
                    min_v, max_v = limites[nome]
                    passo = ajustes[nome]
                    atual = int(config.get(nome, min_v))
                    novo = atual - passo if oper == "-" else atual + passo
                    config[nome] = max(min_v, min(max_v, novo))
                    save_config(config)

        pygame.display.flip()

    return
