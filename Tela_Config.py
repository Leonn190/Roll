import os
import pygame

from ConfigStore import save_config
from VisualEffects import aplicar_filtro_luminosidade


SLIDER_W = 420
SLIDER_H = 10
KNOB_R = 14


def _draw_button(tela, rect, text, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (80, 92, 132) if hover else (55, 64, 92)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (170, 188, 235), rect, 2, border_radius=12)
    txt = font.render(text, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def _draw_slider_row(tela, y, label, key, config, limites, fonte_label, fonte_valor, mouse_pos):
    W = tela.get_width()
    min_v, max_v = limites[key]
    valor = int(config.get(key, min_v))

    txt_label = fonte_label.render(label, True, (230, 236, 250))
    tela.blit(txt_label, (W // 2 - 300, y - 16))

    trilho = pygame.Rect(W // 2 - 60, y, SLIDER_W, SLIDER_H)
    pygame.draw.rect(tela, (56, 66, 98), trilho, border_radius=6)

    progresso = 0 if max_v == min_v else (valor - min_v) / (max_v - min_v)
    preenchido = pygame.Rect(trilho.x, trilho.y, int(trilho.w * progresso), trilho.h)
    pygame.draw.rect(tela, (110, 140, 210), preenchido, border_radius=6)

    knob_x = trilho.x + int(trilho.w * progresso)
    knob = pygame.Rect(0, 0, KNOB_R * 2, KNOB_R * 2)
    knob.center = (knob_x, trilho.centery)
    hover_knob = knob.collidepoint(mouse_pos)
    pygame.draw.circle(tela, (220, 230, 255) if hover_knob else (190, 205, 245), knob.center, KNOB_R)

    txt_val = fonte_valor.render(str(valor), True, (255, 255, 255))
    tela.blit(txt_val, txt_val.get_rect(midleft=(trilho.right + 24, trilho.centery)))

    area_interacao = trilho.inflate(0, 34)
    return area_interacao, knob, trilho


def _valor_por_posicao_x(x, trilho, min_v, max_v):
    if trilho.w <= 0:
        return min_v
    t = (x - trilho.x) / trilho.w
    t = max(0.0, min(1.0, t))
    return int(round(min_v + t * (max_v - min_v)))


def TelaConfig(tela, relogio, estados, config, info=None):
    fonte_path = os.path.join("Fontes", "FontePadrão.ttf")
    fonte_titulo = pygame.font.Font(fonte_path, 62)
    fonte_label = pygame.font.Font(fonte_path, 34)
    fonte_valor = pygame.font.Font(fonte_path, 32)
    fonte_btn = pygame.font.Font(fonte_path, 30)

    W, H = tela.get_size()
    btn_voltar = pygame.Rect(0, 0, 240, 78)
    btn_voltar.center = (W // 2, H - 120)

    limites = {
        "Volume": (0, 100),
        "FPS": (30, 240),
        "Luminosidade": (0, 100),
    }

    slider_rows = [
        (290, "Volume", "Volume"),
        (390, "FPS", "FPS"),
        (490, "Claridade", "Luminosidade"),
    ]

    slider_info = {}
    arrastando = None

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Config", False):
        relogio.tick(config.get("FPS", 60))
        events = pygame.event.get()
        mouse_pos = pygame.mouse.get_pos()

        tela.fill((14, 14, 22))
        title = fonte_titulo.render("Configurações", True, (236, 242, 255))
        tela.blit(title, title.get_rect(center=(W // 2, 150)))

        slider_info.clear()
        for y, label, key in slider_rows:
            area, knob, trilho = _draw_slider_row(
                tela, y, label, key, config, limites, fonte_label, fonte_valor, mouse_pos
            )
            slider_info[key] = (area, knob, trilho)

        _draw_button(tela, btn_voltar, "VOLTAR", fonte_btn, mouse_pos)

        for e in events:
            if e.type == pygame.QUIT:
                estados["Rodando"] = False
                rodando = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                estados["Config"] = False
                estados[estados.get("RetornoConfig", "Inicio")] = True
                rodando = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for key, (area, knob, trilho) in slider_info.items():
                    if area.collidepoint(e.pos) or knob.collidepoint(e.pos):
                        arrastando = key
                        min_v, max_v = limites[key]
                        config[key] = _valor_por_posicao_x(e.pos[0], trilho, min_v, max_v)
                        save_config(config)
                        break
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if btn_voltar.collidepoint(e.pos):
                    estados["Config"] = False
                    estados[estados.get("RetornoConfig", "Inicio")] = True
                    rodando = False
                    break
                arrastando = None
            elif e.type == pygame.MOUSEMOTION and arrastando:
                _, _, trilho = slider_info[arrastando]
                min_v, max_v = limites[arrastando]
                novo = _valor_por_posicao_x(e.pos[0], trilho, min_v, max_v)
                if novo != int(config.get(arrastando, min_v)):
                    config[arrastando] = novo
                    save_config(config)

        aplicar_filtro_luminosidade(tela, config.get("Luminosidade", 75))
        pygame.display.flip()

    return
