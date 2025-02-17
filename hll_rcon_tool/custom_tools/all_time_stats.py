"""
all_time_stats.py

A plugin for HLL CRCON (https://github.com/MarechJ/hll_rcon_tool)
that displays a player's all-time stats on chat command

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

from datetime import datetime
import logging

from sqlalchemy.sql import text

from rcon.models import enter_session
from rcon.player_history import get_player_profile
from rcon.rcon import Rcon, StructuredLogLineWithMetaData

# Configuration (you must review/change these !)
# -----------------------------------------------------------------------------

# Should we display the stats to every player on connect ?
# True or False
ENABLED = True

# Strings translations
# Available : 0 for english, 1 for french, 2 for german, 3 for polish
LANG = 1

# Translations
# format is : "key": ["english", "french", "german", "polish"]
# ----------------------------------------------
TRANSL = {
    "years": ["years", "années", "Jahre", "Lata"],
    "monthes": ["monthes", "mois", "Monate", "Miesiące"],
    "days": ["days", "jours", "Tage", "Dni"],
    "playedgames": ["played games", "parties jouées", "gespielte Spiele", "Rozegranych gier"],
    "cumulatedplaytime": ["cumulated play time", "temps de jeu cumulé", "kumulierte Spielzeit", "Łączny czas gry"],
    "favoriteweapons": ["favorite weapons", "armes favorites", "Lieblingswaffen", "Ulubione bronie"],
    "victims": ["victims", "victimes", "Opfer", "Ofiary"],
    "nemesis": ["nemesis", "nemesis", "Nemesis", "Nemesis"],
    "kills": ["kills", "kills", "tötet", "zabójstwa"],
    "deaths": ["deaths", "morts", "todesfälle", "śmierci"],
    "ratio": ["ratio", "ratio", "verhältnis", "średnia"],
}

# (End of configuration)
# -----------------------------------------------------------------------------
QUERIES = {
    "tot_games": "SELECT COUNT(*) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
    "tot_kills": "SELECT SUM(kills) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
    "tot_teamkills": "SELECT SUM(teamkills) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
    "tot_deaths": "SELECT SUM(deaths) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
    "tot_deaths_by_tk": "SELECT SUM(deaths_by_tk) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
    "most_killed": """
        SELECT key AS player_name, SUM(value::int) AS total_kills, count(*)
        FROM public.player_stats, jsonb_each_text(most_killed)
        WHERE playersteamid_id = :db_player_id
        GROUP BY key
        ORDER BY total_kills DESC
        LIMIT 3
    """,
    "most_death_by": """
        SELECT key AS player_name, SUM(value::int) AS total_kills, count(*)
        FROM public.player_stats, jsonb_each_text(death_by)
        WHERE playersteamid_id = :db_player_id
        GROUP BY key
        ORDER BY total_kills DESC
        LIMIT 3
    """,
}

def format_hours_minutes_seconds(hours: int, minutes: int, seconds: int) -> str:
    """
    Formats the hours, minutes, and seconds as XXhXXmXXs.
    """
    return f"{int(hours):02d}h{int(minutes):02d}m{int(seconds):02d}s"

def readable_duration(seconds: int) -> str:
    """
    Returns a human-readable string (years, months, days, XXhXXmXXs)
    from a number of seconds.
    """
    seconds = int(seconds)

    years, remaining_seconds_in_year = divmod(seconds, 31536000)
    months, remaining_seconds_in_month = divmod(remaining_seconds_in_year, 2592000)
    days, remaining_seconds_in_day = divmod(remaining_seconds_in_month, 86400)
    hours, remaining_seconds_in_hour = divmod(remaining_seconds_in_day, 3600)
    remaining_seconds = divmod(remaining_seconds_in_hour, 60)

    time_string = []

    if years > 0:
        time_string.append(f"{years} {TRANSL['years'][LANG]}")
    if months > 0:
        time_string.append(f"{months} {TRANSL['months'][LANG]}")
    if days > 0:
        time_string.append(f"{days} {TRANSL['days'][LANG]}")

    if any([years, months, days]):
        time_string.append(",")

    time_string.append(format_hours_minutes_seconds(hours, minutes, remaining_seconds))

    return " ".join(filter(None, time_string))

def get_player_profile_data(player_id):
    """
    Retrieves the main data of the player profile.
    """
    player_profile_data = get_player_profile(player_id=player_id, nb_sessions=0)
    if not player_profile_data:
        return None
    return player_profile_data

def fetch_player_id(sess, player_id):
    """
    Retrieve the player ID from the database.
    """
    player_id_query = "SELECT s.id FROM steam_id_64 AS s WHERE s.steam_id_64 = :player_id"
    result = sess.execute(text(player_id_query), {"player_id": player_id}).fetchone()
    if not result:
        return None
    return result[0]

def execute_queries(sess, params):
    """
    Runs queries to retrieve statistics.
    """
    results = {}
    for key, query in QUERIES.items():
        results[key] = sess.execute(text(query), params).fetchall()
    return results

def get_player_database_stats(player_id):
    """
    Retrieves statistics from the database for a given player.
    """
    with enter_session() as sess:
        db_player_id = fetch_player_id(sess, player_id)
        if db_player_id is None:
            return None
        params = {"db_player_id": db_player_id}
        return execute_queries(sess, params)

def format_top_results(rows, limit, pattern):
    return "\n".join(pattern.format(*row) for row in rows[:limit])

def generate_message(player_name, player_profile_data, database_stats):
    """
    Generates a simplified message for console servers.
    """
    total_playtime_seconds = player_profile_data["total_playtime_seconds"]

    tot_games = int(database_stats["tot_games"][0][0])
    tot_kills = int(database_stats["tot_kills"][0][0])
    tot_teamkills = int(database_stats["tot_teamkills"][0][0])
    tot_deaths = int(database_stats["tot_deaths"][0][0])
    most_killed = format_top_results(database_stats["most_killed"], 3, "{} : {:d} ({:d} games)")
    most_death_by = format_top_results(database_stats["most_death_by"], 3, "{} : {:d} ({:d} games)")

    ratio_kd = round(((tot_kills - tot_teamkills) / max(1, tot_deaths)), 2)

    message = (
        f"▒ {player_name} ▒\n"
        "\n"
        f"{TRANSL['playedgames'][LANG]} : {tot_games}\n"
        f"{TRANSL['cumulatedplaytime'][LANG]} : {readable_duration(total_playtime_seconds)}\n"
        f"{ratio_kd} {TRANSL['ratio'][LANG]} ({tot_kills} {TRANSL['kills'][LANG]} / {tot_deaths} {TRANSL['deaths'][LANG]}) \n"
        "\n"
        f"{TRANSL['victims'][LANG]} :\n"
        f"{most_killed}\n"
        "\n"
        f"{TRANSL['nemesis'][LANG]} :\n"
        f"{most_death_by}\n"
    )

    return message

def all_time_stats(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    Collects and displays statistics.
    """
    if not (player_id := struct_log["player_id_1"]) or not (player_name := struct_log["player_name_1"]):
        logger.error("No player_id or player_name")
        return

    try:
        player_profile_data = get_player_profile_data(player_id)
        if player_profile_data is None:
            return

        database_stats = get_player_database_stats(player_id)
        if database_stats is None:
            return

        message = generate_message(player_name, player_profile_data, database_stats)

        rcon.message_player(
            player_name=player_name,
            player_id=player_id,
            message=message,
            by="all_time_stats",
            save_message=False
        )

    except Exception as error:
        logger.error(error, exc_info=True)

def all_time_stats_on_connected(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    Call the message on player's connection
    """
    if ENABLED:
        all_time_stats(rcon, struct_log)

logger = logging.getLogger('rcon')