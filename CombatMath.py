import random

def _clamp(v, a, b):
    return a if v < a else b if v > b else v


def _total(player, attr):
    return float(player.get_total(attr))


def _pct(player, key, default=0):
    return float(getattr(player, "percentuais", {}).get(key, default))


def _hit(attacker):
    return random.random() <= _clamp(_pct(attacker, "assertividade", 100) / 100.0, 0.0, 1.0)


def _crit_multiplier(attacker):
    chance = _clamp(_pct(attacker, "chance_crit", 0) / 100.0, 0.0, 1.0)
    if random.random() > chance:
        return 1.0
    return 1.0 + max(0.0, _pct(attacker, "dano_crit", 0) / 100.0)


def _damage_after_mods(base_damage, attacker, defender):
    if base_damage <= 0:
        return 0

    amp = 1.0 + (_pct(attacker, "amp_dano", 0) / 100.0)
    red = max(0.0, 1.0 - (_pct(defender, "red_dano", 0) / 100.0))
    final_damage = max(0.0, base_damage * amp * red * _crit_multiplier(attacker))
    return int(round(final_damage))


def _effective_defenses(defender):
    pen = max(0.0, _total(defender, "penetracao"))
    half_pen = pen / 2.0
    df = max(0.0, _total(defender, "defesa_fisica") - half_pen)
    dm = max(0.0, _total(defender, "defesa_magica") - half_pen)
    return df, dm


def _compute_hit(attacker, defender, kind):
    if not _hit(attacker):
        return {"kind": kind, "hit": False, "damage": 0, "heal": 0}

    df, dm = _effective_defenses(defender)
    if kind == "fisico":
        raw = max(0.0, _total(attacker, "dano_fisico") - df)
    else:
        raw = max(0.0, _total(attacker, "dano_magico") - dm)

    damage = _damage_after_mods(raw, attacker, defender)
    vamp = max(0.0, _pct(attacker, "vampirismo", 0) / 100.0)
    heal = int(round(damage * vamp))
    return {"kind": kind, "hit": True, "damage": damage, "heal": heal}


def _hit_slots(attacker, defender):
    """
    Quantos golpes o atacante encaixa antes do defensor agir.
    >=3x velocidade: encaixa físico + mágico.
    >=2x velocidade: encaixa apenas físico antes da resposta.
    caso contrário: 1 (ordem alternada padrão).
    """
    a_spd = max(1.0, _total(attacker, "velocidade"))
    d_spd = max(1.0, _total(defender, "velocidade"))
    ratio = a_spd / d_spd
    if ratio >= 3.0:
        return 2
    if ratio >= 2.0:
        return 1
    return 0


def execute_round(attacker, defender):
    """
    Ordem da rodada:
    1) prioridade por velocidade
    2) físico, resposta física
    3) mágico, resposta mágica
    4) regeneração bruta
    """
    a_spd = _total(attacker, "velocidade")
    d_spd = _total(defender, "velocidade")

    first, second = (attacker, defender) if a_spd >= d_spd else (defender, attacker)
    logs = []

    first_pre_hits = _hit_slots(first, second)

    def apply(att, deff, kind):
        hit = _compute_hit(att, deff, kind)
        if hit["damage"] > 0:
            deff.vida = max(0, deff.vida - hit["damage"])
        if hit["heal"] > 0:
            att.vida = min(att.vida_max, att.vida + hit["heal"])
        logs.append((att.nome, deff.nome, hit))

    # fase física
    apply(first, second, "fisico")
    if second.vida > 0 and first_pre_hits < 1:
        apply(second, first, "fisico")

    # fase mágica
    if second.vida > 0 and first_pre_hits >= 2:
        apply(first, second, "magico")

    if first.vida > 0 and second.vida > 0 and first_pre_hits < 2:
        apply(first, second, "magico")
        if second.vida > 0:
            apply(second, first, "magico")

    # regeneração bruta no fim
    for p in (attacker, defender):
        regen = max(0, int(round(_total(p, "regeneracao"))))
        if regen > 0 and p.vida > 0:
            p.vida = min(p.vida_max, p.vida + regen)
            logs.append((p.nome, p.nome, {"kind": "regen", "hit": True, "damage": 0, "heal": regen}))

    return {
        "logs": logs,
        "vencedor": attacker if defender.vida <= 0 else defender if attacker.vida <= 0 else None,
        "ordem_inicial": (first.nome, second.nome),
    }
