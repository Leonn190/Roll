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


def _armor_multiplier_lol(armor):
    if armor >= 0:
        return 100.0 / (100.0 + armor)
    return 2.0 - (100.0 / (100.0 - armor))


def _damage_after_mods(base_damage, attacker, defender):
    if base_damage <= 0:
        return 0

    amp = 1.0 + (_pct(attacker, "amp_dano", 0) / 100.0)
    red = max(0.0, 1.0 - (_pct(defender, "red_dano", 0) / 100.0))
    final_damage = max(0.0, base_damage * amp * red * _crit_multiplier(attacker))
    return int(round(final_damage))


def _effective_defenses(attacker, defender):
    pen_total = max(0.0, _total(attacker, "penetracao"))
    pen_split = pen_total / 2.0
    df = _total(defender, "defesa_fisica") - pen_split
    dm = _total(defender, "defesa_magica") - pen_split
    return df, dm


def _compute_hit(attacker, defender, kind):
    if not _hit(attacker):
        return {
            "kind": kind,
            "hit": False,
            "damage": 0,
            "heal": 0,
            "raw_damage": 0,
            "defense_block": 0,
        }

    df, dm = _effective_defenses(attacker, defender)
    if kind == "fisico":
        raw = max(0.0, _total(attacker, "dano_fisico"))
        mitigado = raw * _armor_multiplier_lol(df)
    else:
        raw = max(0.0, _total(attacker, "dano_magico"))
        mitigado = raw * _armor_multiplier_lol(dm)

    raw_damage = int(round(raw))
    damage = _damage_after_mods(mitigado, attacker, defender)
    defense_block = max(0, raw_damage - damage)
    vamp = max(0.0, _pct(attacker, "vampirismo", 0) / 100.0)
    heal = int(round(damage * vamp))
    return {
        "kind": kind,
        "hit": True,
        "damage": damage,
        "heal": heal,
        "raw_damage": raw_damage,
        "defense_block": defense_block,
    }


def _hit_slots(attacker, defender):
    a_spd = max(1.0, _total(attacker, "velocidade"))
    d_spd = max(1.0, _total(defender, "velocidade"))
    ratio = a_spd / d_spd
    if ratio >= 3.0:
        return 2
    if ratio >= 2.0:
        return 1
    return 0


def execute_round(attacker, defender):
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

    apply(first, second, "fisico")
    if second.vida > 0 and first_pre_hits < 1:
        apply(second, first, "fisico")

    if second.vida > 0 and first_pre_hits >= 2:
        apply(first, second, "magico")

    if first.vida > 0 and second.vida > 0 and first_pre_hits < 2:
        apply(first, second, "magico")
        if second.vida > 0:
            apply(second, first, "magico")

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
