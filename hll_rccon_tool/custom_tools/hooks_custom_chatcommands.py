"""
hooks_custom_topstats

A plugin for HLL CRCON (see : https://github.com/MarechJ/hll_rcon_tool)
that displays and rewards top players, based on their scores.

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from rcon.rcon import Rcon, StructuredLogLineWithMetaData


# Configuration (you must review/change these !)
# -----------------------------------------------------------------------------

# Translations
# Available : 0 for english, 1 for french, 2 for german
LANG = 0

# Gives a bonus to defense
# ie : 1.4 means "defense counts 1.4x more than offense"
OFFENSEDEFENSE_RATIO = 1.4
# Gives a bonus to support
COMBATSUPPORT_RATIO = 1.4


# Calling from chat
# ----------------------------------------

# Chat command
CHAT_COMMAND = "!top"

# How many tops in each category should we display ?
# Prefer 1-3 for a shorter message
TOPS_CHAT = 3

# Squads : display squad members for the nth top squads
# Prefer 0 for a shorter message
TOPS_CHAT_DETAIL_SQUADS = 1


# Displayed at MATCH END
# ----------------------------------------

# How many tops in each category should we display ?
# Prefer 1-3 for a shorter message
TOPS_MATCHEND = 3

# Squads : display squad members for the nth top squads
# Prefer 0 for a shorter message
TOPS_MATCHEND_DETAIL_SQUADS = 1

# Give VIPs at match's end to the best nth top in each :
# - commander (best combat + (support * COMBATSUPPORT_RATIO))
# - infantry (best offense * (defense * OFFENSEDEFENSE_RATIO))
# - infantry (best combat + (support * COMBATSUPPORT_RATIO))
# ie :
# 1 = gives a VIP to the top #1 players (3 VIPs awarded)
# 2 = gives a VIP to the top #1 and #2 players (6 VIPs awarded)
# 0 to disable
VIP_WINNERS = 1

# VIPs will be given if there is at least this number of players ingame
# 0 to disable (VIP will always be given)
# Recommended : the same number as your seed limit
SEED_LIMIT = 40

# How many VIP hours awarded ?
# If the player already has a VIP that ends AFTER this delay, VIP won't be given.
VIP_HOURS = 24

# VIP announce : local time
# Find you local timezone : https://utctime.info/timezone/
LOCAL_TIMEZONE = "Europe/Paris"
LOCAL_TIME_FORMAT = "%d/%m/%Y à %Hh%M"


# Translations
# "key" : ["english", "french", "german"]
# ----------------------------------------------

TRANSL = {
    "nostatsyet": ["No stats yet", "Pas de stats", "noch keine Statistiken"],
    "allies": ["all", "all", "all"],
    "axis": ["axe", "axe", "axe"],
    "best_players": ["Best players", "Meilleurs joueurs", "Beste Spieler"],
    "armycommander": ["Commander", "Commandant", "Kommandant"],
    "infantry": ["Infantry", "Infanterie", "Infanterie"],
    "tankers": ["Tankers", "Tankistes", "Panzerspieler"],
    "best_squads": ["Best squads", "Meilleures squads", "Beste Mannschaften"],
    "offense": ["attack", "attaque", "angriff"],
    "defense": ["defense", "défense", "verteidigung"],
    "combat": ["combat", "combat", "kampf"],
    "support": ["support", "soutien", "unterstützung"],
    "ratio": ["ratio", "ratio", "verhältnis"],
    "killrate": ["kills/min", "kills/min", "kills/min"],
    "vip_until": ["VIP until", "VIP jusqu'au", "VIP bis"],
    "already_vip": ["Already VIP !", "Déjà VIP !", "bereits VIP !"]
}


# (End of configuration)
# -----------------------------------------------------------------------------


def is_vip_for_less_than_xh(rcon: Rcon, player_id: str, vip_delay_hours: int):
    """
    returns 'true' if player has no VIP or a VIP that expires in less than vip_delay_hours,
    'false' if he has a VIP that expires in more than vip_delay_hours or no VIP at all.
    """
    actual_vips = rcon.get_vip_ids()
    for item in actual_vips:
        if item['player_id'] == player_id and item['vip_expiration'] is not None:
            vip_expiration_output = str(item['vip_expiration'])
            vip_expiration = datetime.fromisoformat(vip_expiration_output)
            if vip_expiration < datetime.now(timezone.utc) + timedelta(hours=vip_delay_hours):
                return True
            return False
    return True  # player wasn't in the actual VIP list


def get_top(
    rcon: Rcon,
    callmode: str,  # either "chat" or "matchend"
    calltype: str,  # either "player" or "squad"
    data_bucket: list,
    sortkey,
    first_data: str,
    second_data: str,
    third_data: str,
    fourth_data: str,
    squadtype_allplayers : list  # Observed squad type ("infantry" or "tankers") players sats
) -> str:
    """
    Returns a string, listing top players or squads, as calculated by sortkey
    ie :
    SomeGuy (Axe) : 240 ; 120
    SomeOtherGuy (All) : 230 ; 100
    """
    if callmode == "chat":
        tops_limit = TOPS_CHAT
        show_members = TOPS_CHAT_DETAIL_SQUADS
    if callmode == "matchend":
        server_status = rcon.get_status()  # Get the number of players -> give VIP if not in seed
        tops_limit = TOPS_MATCHEND
        show_members = TOPS_MATCHEND_DETAIL_SQUADS

    sorted_data = sorted(data_bucket, key=sortkey, reverse=True)
    output = ""
    iteration = 1
    for sample in sorted_data[:tops_limit]:
        if sortkey(sample) != 0:
            if fourth_data == "":  # real_offdef, teamplay, ratio
                if calltype == "squad":  # real_offdef, teamplay
                    output = output + "■ "
                output = output + f"{sample[first_data]} ({TRANSL[sample['team']][LANG]}): {sample[second_data]} ; {sample[third_data]}\n"
            else:  # killrate (players only)
                output = output + f"{sample[first_data]} ({TRANSL[sample['team']][LANG]}): {sortkey(sample)}\n"

            # Squad members
            if (
                calltype == "squad"
                and show_members > 0
                and iteration <= show_members
            ):
                for sample_vip in sorted_data[:show_members]:
                    best_players_names = [
                        data['name'] for data in squadtype_allplayers
                        if data.get('team') == sample_vip['team']
                        and data.get('unit_name') == sample_vip['name']
                    ]
                    best_players_str = '; '.join(best_players_names)
                    output = output + f"{best_players_str}\n"

        # Give VIP to players
        if (
            callmode == "matchend"
            and calltype == "player"
            and VIP_WINNERS > 0
            and VIP_HOURS > 0  # Security : avoids to give a 0 hour VIP
            and server_status["current_players"] >= SEED_LIMIT
            and iteration <= VIP_WINNERS
            and second_data != "kills"  # No VIP for top ratios and killrates
        ):
            if is_vip_for_less_than_xh(rcon, sample['player_id'], VIP_HOURS):
                output = output + give_xh_vip(rcon, sample['player_id'], VIP_HOURS)
            else:
                output = output + f"{TRANSL['already_vip'][LANG]}\n"

        iteration = iteration + 1

    return output


def give_xh_vip(rcon: Rcon, player_id: str, hours_awarded: int):
    """
        Gives a x hours VIP
        Returns a str that announces the VIP expiration (local) time
    """
    # Gives X hours VIP
    now_plus_xh = datetime.now(timezone.utc) + timedelta(hours=hours_awarded)
    now_plus_xh_vip_formatted = now_plus_xh.strftime('%Y-%m-%dT%H:%M:%SZ')
    rcon.add_vip(player_id, "top_player", now_plus_xh_vip_formatted)

    # Returns a string giving the new expiration date in local time
    now_plus_xh_utc = now_plus_xh.replace(tzinfo=ZoneInfo("UTC"))
    now_plus_xh_paris_tz = now_plus_xh_utc.astimezone(ZoneInfo(LOCAL_TIMEZONE))
    now_plus_xh_display_formatted = now_plus_xh_paris_tz.strftime(LOCAL_TIME_FORMAT)
    return f"{TRANSL['vip_until'][LANG]} {str(now_plus_xh_display_formatted)} !\n"


def message_all_players(rcon: Rcon, message: str):
    """
    Sends a message to all connected players
    """
    all_players_list = rcon.get_playerids()
    for player in all_players_list:
        player_name = player[0]
        player_id = player[1]
        try:
            rcon.message_player(
                player_name=player_name,
                player_id=player_id,
                message=message,
                by="top_stats",
            )
        except Exception:
            pass


def ratio(obj):
    """
    returns (kills/deaths) score
    """
    kills = int(obj["kills"])
    deaths = int(obj["deaths"])
    if deaths == 0:
        deaths = 1
    computed_ratio = (kills / deaths)
    return round(computed_ratio, 2)


def real_offdef(obj):
    """
    returns a combined offense * (defense * OFFENSEDEFENSE_RATIO) score
    """
    offense = int(obj["offense"])
    defense = int(obj["defense"])
    return int(offense * (defense * OFFENSEDEFENSE_RATIO))


def teamplay(obj):
    """
    returns a combined combat + (support * COMBATSUPPORT_RATIO) score
    """
    combat = int(obj["combat"])
    support = int(obj["support"])
    return int(combat + support * COMBATSUPPORT_RATIO)


def killrate(obj):
    """
    returns kills/playtime in minutes
    """
    kills = int(obj["kills"])
    offense = int(obj["offense"])
    defense = int(obj["defense"])
    if kills == 0:
        return 0
    if offense == 0 and defense == 0:
        return 0
    return round((kills / ((offense + defense) / 20)), 2)


def team_view_stats(rcon: Rcon):
    """
    Get the get_team_view data
    and gather the infos according to the squad types and soldier roles
    """
    get_team_view: dict = rcon.get_team_view()

    all_commanders = []
    all_players_infantry = []
    all_players_armor = []
    all_squads_infantry = []
    all_squads_armor = []

    for team in ["allies", "axis"]:

        if team in get_team_view:

            # Commanders
            if get_team_view[team]["commander"] is not None:
                all_commanders.append(get_team_view[team]["commander"])

            for squad in get_team_view[team]["squads"]:

                squad_data = get_team_view[team]["squads"][squad]
                squad_data["team"] = team

                # Infantry
                if squad_data["type"] == "infantry" or squad_data["type"] == "recon":
                    all_players_infantry.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_squads_infantry.append({squad: squad_data})

                # Armor
                elif squad_data["type"] == "armor":
                    all_players_armor.extend(squad_data["players"])
                    squad_data.pop("players", None)
                    all_squads_armor.append({squad: squad_data})

    return (
        all_commanders,
        all_players_infantry,
        all_players_armor,
        all_squads_infantry,
        all_squads_armor
    )


def stats_display(
        top_commanders_teamplay: str,
        top_infantry_offdef: str,
        top_infantry_teamplay: str,
        top_infantry_ratio: str,
        top_infantry_killrate: str,
        top_squads_infantry_offdef: str,
        top_squads_infantry_teamplay: str,
        top_squads_armor_offdef: str,
        top_squads_armor_teamplay: str,
) -> str:
    """
    Format the message sent
    """
    message = ""
    # players
    if (
        len(top_commanders_teamplay) != 0
        or len(top_infantry_offdef) != 0
        or len(top_infantry_teamplay) != 0
        or len(top_infantry_ratio) != 0
        or len(top_infantry_killrate) != 0
    ):
        message = f"█ {TRANSL['best_players'][LANG]} █\n\n"
        # players / commanders
        if len(top_commanders_teamplay) != 0:
            message += (
                f"▓ {TRANSL['armycommander'][LANG]} ▓\n\n"
                f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(COMBATSUPPORT_RATIO)}) ─\n{top_commanders_teamplay}\n"
            )
        # players / infantry
        if (
            len(top_infantry_offdef) != 0
            or len(top_infantry_teamplay) != 0
            or len(top_infantry_ratio) != 0
            or len(top_infantry_killrate) != 0
        ):
            message += f"▓ {TRANSL['infantry'][LANG]} ▓\n\n"
            if len(top_infantry_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(OFFENSEDEFENSE_RATIO)}) ─\n{top_infantry_offdef}\n"
            if len(top_infantry_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(COMBATSUPPORT_RATIO)}) ─\n{top_infantry_teamplay}\n"
            if len(top_infantry_ratio) != 0:
                message += f"─ {TRANSL['ratio'][LANG]} ─\n{top_infantry_ratio}\n"
            if len(top_infantry_killrate) != 0:
                message += f"─ {TRANSL['killrate'][LANG]} ─\n{top_infantry_killrate}\n"
    # squads
    if (
        len(top_squads_infantry_offdef) != 0
        or len(top_squads_infantry_teamplay) != 0
        or len(top_squads_armor_offdef) != 0
        or len(top_squads_armor_teamplay) != 0
    ):
        message += f"\n█ {TRANSL['best_squads'][LANG]} █\n\n"
        # squads / infantry
        if len(top_squads_infantry_offdef) != 0 or len(top_squads_infantry_teamplay) != 0:
            message += f"▓ {TRANSL['infantry'][LANG]} ▓\n\n"
            if len(top_squads_infantry_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(OFFENSEDEFENSE_RATIO)}) ─\n{top_squads_infantry_offdef}\n"
            if len(top_squads_infantry_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(COMBATSUPPORT_RATIO)}) ─\n{top_squads_infantry_teamplay}\n"
        # squads / armor
        if len(top_squads_armor_offdef) != 0 or len(top_squads_armor_teamplay) != 0:
            message += f"▓ {TRANSL['tankers'][LANG]} ▓\n\n"
            if len(top_squads_armor_offdef) != 0:
                message += f"─ {TRANSL['offense'][LANG]} * ({TRANSL['defense'][LANG]} * {str(OFFENSEDEFENSE_RATIO)}) ─\n{top_squads_armor_offdef}\n"
            if len(top_squads_armor_teamplay) != 0:
                message += f"─ {TRANSL['combat'][LANG]} + ({TRANSL['support'][LANG]} * {str(COMBATSUPPORT_RATIO)}) ─\n{top_squads_armor_teamplay}\n"

    # If no data yet
    if len(message) == 0:
        return f"{TRANSL['nostatsyet'][LANG]}"

    return message


def stats_gather(
    rcon: Rcon,
    callmode: str
):
    """
    Calls team_view_stats() and gathers data in players categories
    Then returns a tuple containing categories stats as calculated by get_top()
    """
    (
        all_commanders,
        all_players_infantry,
        all_players_armor,
        all_squads_infantry,
        all_squads_armor
    ) = team_view_stats(rcon)

    all_squads_infantry = [{'name': key, **value} for item in all_squads_infantry for key, value in item.items()]
    all_squads_armor = [{'name': key, **value} for item in all_squads_armor for key, value in item.items()]

    return (
        # Players (commanders)
        get_top(rcon, callmode, "player", all_commanders, teamplay, "name", "combat", "support", "", all_commanders),
        # Players (infantry)
        get_top(rcon, callmode, "player", all_players_infantry, real_offdef, "name", "offense", "defense", "", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, teamplay, "name", "combat", "support", "", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, ratio, "name", "kills", "deaths", "", all_players_infantry),
        get_top(rcon, callmode, "player", all_players_infantry, killrate, "name", "kills", "offense", "defense", all_players_infantry),
        # Squads (infantry)
        get_top(rcon, callmode, "squad", all_squads_infantry, real_offdef, "name", "offense", "defense", "", all_players_infantry),
        get_top(rcon, callmode, "squad", all_squads_infantry, teamplay, "name", "combat", "support", "", all_players_infantry),
        # Squads (armor)
        get_top(rcon, callmode, "squad", all_squads_armor, real_offdef, "name", "offense", "defense", "", all_players_armor),
        get_top(rcon, callmode, "squad", all_squads_armor, teamplay, "name", "combat", "support", "", all_players_armor),
    )


def stats_on_chat_command(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData
):
    """
    Sends actual top scores in an ingame message to the player who types the defined command in chat
    """
    chat_message: str|None = struct_log["sub_content"]
    if chat_message is None:
        return

    player_id: str|None = struct_log["player_id_1"]
    if player_id is None:
        return

    if struct_log["sub_content"] == CHAT_COMMAND:
        (
            top_commanders_teamplay,
            top_infantry_offdef,
            top_infantry_teamplay,
            top_infantry_ratio,
            top_infantry_killrate,
            top_squads_infantry_offdef,
            top_squads_infantry_teamplay,
            top_squads_armor_offdef,
            top_squads_armor_teamplay,
        ) = stats_gather(
            rcon = rcon,
            callmode = "chat"
        )

        message = stats_display(
            top_commanders_teamplay,
            top_infantry_offdef,
            top_infantry_teamplay,
            top_infantry_ratio,
            top_infantry_killrate,
            top_squads_infantry_offdef,
            top_squads_infantry_teamplay,
            top_squads_armor_offdef,
            top_squads_armor_teamplay,
        )

        rcon.message_player(
            player_id=player_id,
            message=message,
            by="top_stats",
            save_message=False
        )


def stats_on_match_end(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData
):
    """
    Sends final top players in an ingame message to all the players
    Gives VIP to the top players as configured
    """
    (
        top_commanders_teamplay,
        top_infantry_offdef,
        top_infantry_teamplay,
        top_infantry_ratio,
        top_infantry_killrate,
        top_squads_infantry_offdef,
        top_squads_infantry_teamplay,
        top_squads_armor_offdef,
        top_squads_armor_teamplay,
    ) = stats_gather(
        rcon = rcon,
        callmode = "matchend"
    )

    message = stats_display(
        top_commanders_teamplay,
        top_infantry_offdef,
        top_infantry_teamplay,
        top_infantry_ratio,
        top_infantry_killrate,
        top_squads_infantry_offdef,
        top_squads_infantry_teamplay,
        top_squads_armor_offdef,
        top_squads_armor_teamplay,
    )

    message_all_players(rcon, message)
