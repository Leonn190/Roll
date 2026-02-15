import pygame

from Tabuleiro import Tabuleiro
from Player import PlayerBatalha, ATRIBUTOS


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
                estados["Rodando"] = False
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
        tabuleiro.update(events, agora)

        # aplica intensificadores vindos do tabuleiro
        if tabuleiro.esta_estavel():
            aplicar_somas_nos_players(agora)

        # desenha fichas por cima
        p1.draw_ficha(tela, agora, lado="esquerda")
        p2.draw_ficha(tela, agora, lado="direita")

        pygame.display.flip()

    return
