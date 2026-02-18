import pygame
import random

from Tabuleiro import Tabuleiro
from Player import PlayerBatalha, PlayerEstrategista, ATRIBUTOS
from VisualEffects import aplicar_filtro_luminosidade
from CombatMath import execute_round
from BattleAnimation import build_anim_steps, draw_acao_batalha, calc_collision_t


def _draw_pause_btn(tela, rect, label, font, mouse_pos):
    hover = rect.collidepoint(mouse_pos)
    color = (80, 92, 132) if hover else (55, 64, 92)
    pygame.draw.rect(tela, color, rect, border_radius=12)
    pygame.draw.rect(tela, (170, 188, 235), rect, 2, border_radius=12)
    txt = font.render(label, True, (242, 246, 255))
    tela.blit(txt, txt.get_rect(center=rect.center))


def _draw_status(tela, texto, timer_s):
    fonte = pygame.font.Font("Fontes/FontePadrão.ttf", 34)
    t = fonte.render(f"{texto}: {timer_s}s", True, (245, 245, 245))
    tela.blit(t, (tela.get_width() // 2 - t.get_width() // 2, 18))


def TelaBatalha(tela, relogio, estados, config, info=None):
    tabuleiro = Tabuleiro(tela)

    p1_compartilhado = PlayerEstrategista("PLAYER", lado="aliado", ouro_inicial=0)
    dados_player = (info or {}).get("player_aliado") if isinstance(info, dict) else None
    if isinstance(dados_player, dict):
        p1_compartilhado.carregar_estado_compartilhado(dados_player)

    nome_player = str(p1_compartilhado.nome or "PLAYER")
    nivel_player = 2
    if isinstance(dados_player, dict):
        nivel_player = max(1, int(dados_player.get("nivel", nivel_player) or nivel_player))
    p1 = PlayerBatalha(nome_player, lado="aliado", nivel=nivel_player)
    p2 = PlayerBatalha("Inimigo", lado="inimigo", nivel=p1.nivel)

    vida_player = max(1, int(p1_compartilhado.vida_max or 1))
    p1.vida_max = vida_player
    p1.vida = max(0, min(vida_player, int(p1_compartilhado.vida or vida_player)))

    vida_ref = max(200, int(p1_compartilhado.vida_max or 0))
    p2.vida_max = int(vida_ref * random.uniform(0.85, 1.15))
    p2.vida = p2.vida_max

    ativos_aliados = [a for a in ATRIBUTOS if p1_compartilhado.dados_selecionados.get(a)]
    for attr in ativos_aliados[:p1.max_ativos()]:
        p1.toggle_attr_ativo(attr)
    if not p1.ativos_lista():
        p1.toggle_attr_ativo("regeneracao")
        p1.toggle_attr_ativo("dano_fisico")
        p1.toggle_attr_ativo("dano_magico")

    for attr in ATRIBUTOS:
        base_player = int(p1_compartilhado.totais.get(attr, 0))
        p1.set_base(attr, base_player)
        if base_player <= 0:
            p2.set_base(attr, random.randint(0, 40))
        else:
            p2.set_base(attr, int(base_player * random.uniform(0.8, 1.2)))

    p1.ouro = int(p1_compartilhado.ouro)
    p1.set_percentuais(p1_compartilhado.percentuais)
    p2.set_percentuais(p1_compartilhado.percentuais)

    ativos_inimigos = random.sample(ATRIBUTOS, k=min(p2.max_ativos(), len(ATRIBUTOS)))
    for attr in ativos_inimigos:
        p2.toggle_attr_ativo(attr)

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

    def iniciar_round(agora):
        tabuleiro.limpar_tabuleiro()
        tabuleiro.mao_aliada = p1.get_dados_ativos_para_lancar()
        tabuleiro.mao_inimiga = p2.get_dados_ativos_para_lancar()
        tabuleiro.set_lado_ativo("aliado")
        # inimigo já lança para o jogador ter 8s para responder
        tabuleiro.lancar_automatico("inimigo", agora)

    fonte_pausa = pygame.font.Font("Fontes/FontePadrão.ttf", 30)
    pausa_ativa = False
    btn_quitar = pygame.Rect(0, 0, 240, 70)
    btn_voltar = pygame.Rect(0, 0, 240, 70)
    btn_config = pygame.Rect(0, 0, 240, 70)

    fase = "escolha"
    fase_inicio = pygame.time.get_ticks()
    fase_duracao = 8000
    anim_steps = []
    anim_idx = 0
    anim_inicio = 0
    anim_step_ms = 4200
    vencedor_nome = None
    fim_delay_ms = 1200
    fim_inicio = 0
    bonus_vitoria = 8
    iniciar_round(fase_inicio)

    def aplicar_efeito_acao(acao):
        atacante = p1 if acao["attacker"] == p1.nome else p2
        defensor = p1 if acao["defender"] == p1.nome else p2

        if acao["kind"] == "regen":
            if atacante.vida > 0 and acao["heal"] > 0:
                atacante.vida = min(atacante.vida_max, atacante.vida + acao["heal"])
            return

        if acao.get("damage", 0) > 0 and defensor.vida > 0:
            defensor.vida = max(0, defensor.vida - acao["damage"])
        if acao.get("heal", 0) > 0:
            atacante.vida = min(atacante.vida_max, atacante.vida + acao["heal"])

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
                    estados["Batalha"] = False
                    estados["Inicio"] = True
                    rodando = False
                elif btn_voltar.collidepoint(e.pos):
                    pausa_ativa = False
                elif btn_config.collidepoint(e.pos):
                    estados["Batalha"] = False
                    estados["Config"] = True
                    estados["RetornoConfig"] = "Batalha"
                    rodando = False

        p1.update(agora)
        p2.update(agora)

        if not pausa_ativa:
            p1.handle_events(events, mouse_pos, lado_ficha="esquerda")
            p2.handle_events(events, mouse_pos, lado_ficha="direita")
            tabuleiro.set_lado_ativo("aliado")
            tabuleiro.update(events, agora)

        if tabuleiro.esta_estavel():
            aplicar_somas_nos_players(agora)

        if not pausa_ativa and vencedor_nome is None:
            fase_elapsed = agora - fase_inicio
            if fase == "escolha":
                if fase_elapsed >= fase_duracao:
                    if tabuleiro.mao_aliada:
                        tabuleiro.lancar_automatico("aliado", agora)
                    fase = "pre_dano"
                    fase_inicio = agora
                    fase_duracao = 12000
            elif fase == "pre_dano" and fase_elapsed >= fase_duracao and tabuleiro.esta_estavel():
                vida_p1_pre = p1.vida
                vida_p2_pre = p2.vida
                resultado = execute_round(p1, p2)
                anim_steps = build_anim_steps(resultado["logs"])
                p1.vida = vida_p1_pre
                p2.vida = vida_p2_pre
                anim_idx = 0
                anim_inicio = agora
                fase = "animacao"
            elif fase == "animacao":
                if anim_idx < len(anim_steps):
                    acao = anim_steps[anim_idx]
                    t_anim = min(1.0, (agora - anim_inicio) / max(1, anim_step_ms))
                    if t_anim >= 1.0 and not acao["applied"]:
                        aplicar_efeito_acao(acao)
                        acao["applied"] = True
                        if p1.vida <= 0:
                            vencedor_nome = p2.nome
                            fim_inicio = agora
                        elif p2.vida <= 0:
                            vencedor_nome = p1.nome
                            fim_inicio = agora
                        anim_idx += 1
                        anim_inicio = agora
                else:
                    if p1.vida <= 0:
                        vencedor_nome = p2.nome
                        fim_inicio = agora
                    elif p2.vida <= 0:
                        vencedor_nome = p1.nome
                        fim_inicio = agora
                    else:
                        fase = "escolha"
                        fase_inicio = agora
                        fase_duracao = 8000
                        iniciar_round(agora)

        if not pausa_ativa:
            p1.draw_ficha(tela, agora, lado="esquerda", pos=(18, tela.get_height() - p1.FICHA_H - 18), mostrar_botoes=True)
            p2.draw_ficha(tela, agora, lado="direita", pos=(tela.get_width() - p2.FICHA_W - 18, 18), mostrar_botoes=True)

            timer_s = max(0, (fase_duracao - (agora - fase_inicio) + 999) // 1000)
            if vencedor_nome:
                _draw_status(tela, f"Vencedor: {vencedor_nome}", 0)
            elif fase == "escolha":
                _draw_status(tela, "Escolha e lance os dados", timer_s)
            elif fase == "pre_dano":
                _draw_status(tela, "Preparando danos", timer_s)
            else:
                _draw_status(tela, "Aplicação de danos", timer_s)

            if fase == "animacao" and anim_idx < len(anim_steps):
                pos_por_nome = {
                    p1.nome: (18 + p1.FICHA_W // 2, tela.get_height() - p1.FICHA_H // 2 - 18),
                    p2.nome: (tela.get_width() - p2.FICHA_W // 2 - 18, 18 + p2.FICHA_H // 2),
                }
                acao_atual = anim_steps[anim_idx]
                if "collide_t" not in acao_atual:
                    pa = pos_por_nome.get(acao_atual["attacker"])
                    pd = pos_por_nome.get(acao_atual["defender"])
                    if pa is not None and pd is not None:
                        acao_atual["collide_t"] = calc_collision_t(pa, pd)
                progresso = min(1.0, (agora - anim_inicio) / max(1, anim_step_ms))
                draw_acao_batalha(tela, acao_atual, progresso, pos_por_nome)

        if vencedor_nome and not pausa_ativa and (agora - fim_inicio) >= fim_delay_ms:
            if isinstance(info, dict):
                if vencedor_nome == p1.nome:
                    p1_compartilhado.ouro = int(p1_compartilhado.ouro) + bonus_vitoria
                p1_compartilhado.vida = int(max(0, p1.vida))
                p1_compartilhado.vida_max = int(max(1, p1.vida_max))
                info["player_aliado"] = p1_compartilhado.exportar_estado_compartilhado()
            estados["Batalha"] = False
            estados["Estrategista"] = True
            rodando = False

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
