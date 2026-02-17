import pygame

from Tabuleiro import Tabuleiro
from Player import PlayerBatalha, ATRIBUTOS


def _draw_pause_btn(tela, rect, label, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (80, 92, 132) if hover else (55, 64, 92)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (170, 188, 235), rect, 2, border_radius=12)
    txt = font.render(label, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def TelaBatalha(tela, relogio, estados, config, info=None):
    tabuleiro = Tabuleiro(tela)

    # players
    p1 = PlayerBatalha("Aliado", lado="aliado", nivel=3)   # nivel 3 => 3 dados ativos
    p2 = PlayerBatalha("Inimigo", lado="inimigo", nivel=3)

    # vida/base (exemplo)
    p1.vida_max, p1.vida = 120, 92
    p2.vida_max, p2.vida = 140, 140

    p1.set_base("regeneracao", 380)
    p1.set_base("dano_fisico", 120)
    p1.set_base("mana", 210)

    p2.set_base("defesa_magica", 300)
    p2.set_base("dano_magico", 160)
    p2.set_base("velocidade", 90)

    # exemplo: liga 3 atributos iniciais pra cada (dentro do limite do nível)
    p1.toggle_attr_ativo("regeneracao")
    p1.toggle_attr_ativo("dano_fisico")
    p1.toggle_attr_ativo("mana")

    p2.toggle_attr_ativo("defesa_magica")
    p2.toggle_attr_ativo("dano_magico")
    p2.toggle_attr_ativo("velocidade")

    # cache pra aplicar intensificadores apenas quando mudar
    last_somas = {
        "aliado": {a: 0 for a in ATRIBUTOS},
        "inimigo": {a: 0 for a in ATRIBUTOS},
    }

    def aplicar_somas_nos_players(agora):
        nonlocal last_somas
        somas = tabuleiro.get_somas_por_lado()

        for attr in ATRIBUTOS:
            novo = int(somas["aliado"].get(attr, 0))
            if novo != last_somas["aliado"][attr]:
                p1.set_intensificador(attr, novo, agora)
                last_somas["aliado"][attr] = novo

        for attr in ATRIBUTOS:
            novo = int(somas["inimigo"].get(attr, 0))
            if novo != last_somas["inimigo"][attr]:
                p2.set_intensificador(attr, novo, agora)
                last_somas["inimigo"][attr] = novo

    fonte_pausa = pygame.font.Font("Fontes/FontePadrão.ttf", 30)
    pausa_ativa = False
    btn_quitar = pygame.Rect(0, 0, 240, 70)
    btn_voltar = pygame.Rect(0, 0, 240, 70)
    btn_config = pygame.Rect(0, 0, 240, 70)

    rodando = True
    while rodando and estados.get("Rodando", True) and estados.get("Batalha", False):
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
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and pausa_ativa:
                if btn_quitar.collidepoint(e.pos):
                    estados["Rodando"] = False
                    rodando = False
                elif btn_voltar.collidepoint(e.pos):
                    estados["Batalha"] = False
                    estados["Estrategista"] = True
                    rodando = False
                elif btn_config.collidepoint(e.pos):
                    estados["Batalha"] = False
                    estados["Config"] = True
                    estados["RetornoConfig"] = "Batalha"
                    rodando = False

        # players atualizam animações
        p1.update(agora)
        p2.update(agora)

        # clique nos botões de status (ativa/inativa)
        # (isso NÃO interfere no Tabuleiro; só muda quais dados vão pra mão)
        p1.handle_events(events, mouse_pos, lado_ficha="esquerda")
        p2.handle_events(events, mouse_pos, lado_ficha="direita")

        # monta a mão do tabuleiro a partir do lado ativo
        # (ex: se tabuleiro.lado_ativo == "aliado", pega ativos do p1)
        if tabuleiro.lado_ativo == "aliado":
            tabuleiro.mao_aliada = p1.get_dados_ativos_para_lancar()
        else:
            tabuleiro.mao_inimiga = p2.get_dados_ativos_para_lancar()

        # tabuleiro processa eventos + anima + desenha
        if not pausa_ativa:
            tabuleiro.update(events, agora)

        # aplica intensificadores vindos do tabuleiro
        if tabuleiro.esta_estavel():
            aplicar_somas_nos_players(agora)

        # desenha fichas por cima
        p1.draw_ficha(tela, agora, lado="esquerda")
        p2.draw_ficha(tela, agora, lado="direita")

        if pausa_ativa:
            overlay = pygame.Surface(tela.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            tela.blit(overlay, (0, 0))

            cx, cy = tela.get_width() // 2, tela.get_height() // 2
            btn_quitar.center = (cx, cy - 90)
            btn_voltar.center = (cx, cy)
            btn_config.center = (cx, cy + 90)
            _draw_pause_btn(tela, btn_quitar, "Quitar", fonte_pausa, mouse_pos)
            _draw_pause_btn(tela, btn_voltar, "Voltar", fonte_pausa, mouse_pos)
            _draw_pause_btn(tela, btn_config, "Config", fonte_pausa, mouse_pos)

        pygame.display.flip()

    return
