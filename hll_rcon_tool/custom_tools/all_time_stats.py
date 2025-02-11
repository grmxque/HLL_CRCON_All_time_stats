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
DISPLAY_ON_CONNECT = True

# The command the players have to enter in chat to display their stats
CHAT_COMMAND = ["!me"]

# Strings translations
# Available : 0 for english, 1 for french, 2 for german, 3 for polish
LANG = 0

# Translations
# format is : "key": ["english", "french", "german", "polish"]
# ----------------------------------------------
TRANSL = {
    "years": ["years", "années", "Jahre", "Lata"],
    "monthes": ["monthes", "mois", "Monate", "Miesiące"],
    "weeks": ["weeks", "semaines", "Wochen", "Tygodnie"],
    "days": ["days", "jours", "Tage", "Dni"],
    "hours": ["hours", "heures", "Dienststunden", "Godziny"],
    "minutes": ["minutes", "minutes", "Minuten", "Minuty"],
    "seconds": ["seconds", "secondes", "Sekunden", "Sekundy"],
    "nopunish": ["None ! Well done !", "Aucune ! Félicitations !", "Keiner! Gut gemacht!", "Brak! Dobra robota!"],
    "firsttimehere": ["first time here", "tu es venu(e) il y a", "zum ersten Mal hier", "Pierwszy raz tutaj"],
    "gamesessions": ["game sessions", "sessions de jeu", "Spielesitzungen", "Sesji"],
    "playedgames": ["played games", "parties jouées", "gespielte Spiele", "Rozegranych gier"],
    "cumulatedplaytime": ["cumulated play time", "temps de jeu cumulé", "kumulierte Spielzeit", "Łączny czas gry"],
    "averagesession": ["average session", "session moyenne", "Durchschnittliche Sitzung", "Średnio na sesje"],
    "punishments": ["punishments", "punitions", "Strafen", "Kary"],
    "averages": ["averages", "moyennes", "Durchschnittswerte", "Średnie"],
    "favoriteweapons": ["favorite weapons", "armes favorites", "Lieblingswaffen", "Ulubione bronie"],
    "victims": ["victims", "victimes", "Opfer", "Ofiary"],
    "nemesis": ["nemesis", "nemesis", "Nemesis", "Nemesis"],
    "combat": ["combat", "combat", "kampf", "walka"],
    "offense": ["attack", "attaque", "angriff", "ofensywa"],
    "defense": ["defense", "défense", "verteidigung", "defensywa"],
    "support": ["support", "soutien", "unterstützung", "wsparcie"],
    "totals": ["totals", "totaux", "Gesamtsummen", "Łącznie"],
    "kills": ["kills", "kills", "tötet", "zabójstwa"],
    "deaths": ["deaths", "morts", "todesfälle", "śmierci"],
    "ratio": ["ratio", "ratio", "verhältnis", "średnia"],
}

# (End of configuration)
# -----------------------------------------------------------------------------


def readable_duration(seconds: int) -> str:
    """
    returns a human readable string (years, monthes, days, XXhXXmXXs)
    from a number of seconds
    """
    years, lessthanayearseconds = divmod(seconds, 31536000)
    monthes, lessthanamonthseconds = divmod(lessthanayearseconds, 2592000)
    days, lessthanadayseconds = divmod(lessthanamonthseconds, 86400)
    hours, lessthananhourseconds = divmod(lessthanadayseconds, 3600)
    minutes, seconds = divmod(lessthananhourseconds, 60)

    time_string = ""
    if years > 0:
        time_string += f"{int(years)} {TRANSL['years'][LANG]}"

    if monthes > 0:
        if years > 0:
            time_string += ", "
        time_string += f"{int(monthes)} {TRANSL['monthes'][LANG]}"

    if days > 0:
        if years > 0 or monthes > 0:
            time_string += ", "
        time_string += f"{int(days)} {TRANSL['days'][LANG]}"

    if years > 0 or monthes > 0 or days > 0:
        time_string += ", "
    if hours > 0:
        time_string += f"{int(hours)}h"
    else:
        time_string += "0h"

    if minutes > 0:
        if minutes < 10:
            time_string += "0"
        time_string += f"{int(minutes)}m"
    else:
        time_string += "00m"

    if seconds > 0:
        if seconds < 10:
            time_string += "0"
        time_string += f"{int(seconds)}s"
    else:
        time_string += "00s"

    return time_string


def all_time_stats_on_connected(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    Call the message on player's connection
    """
    if DISPLAY_ON_CONNECT:
        all_time_stats(rcon, struct_log)


def all_time_stats_on_chat_command(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    Call the message on chat command
    """
    if not (chat_message := struct_log["sub_content"]):
       logger.error("No sub_content in CHAT log")
       return
    if chat_message in CHAT_COMMAND:
        all_time_stats(rcon, struct_log)


def all_time_stats(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """
    get data from profile and database and return it in an ingame message
    """
    if not (player_id := struct_log["player_id_1"]) or \
       not (player_name := struct_log["player_name_1"]):
       logger.error("No player_id or player_name")
       return

    try:
        player_profile_data = get_player_profile(player_id=player_id, nb_sessions=0)
        if player_profile_data is None:
            logger.error("No player_profile_data")
            return

        created = player_profile_data["created"]
        sessions_count = player_profile_data["sessions_count"]
        total_playtime_seconds = player_profile_data["total_playtime_seconds"]
        kicks = player_profile_data["penalty_count"]["KICK"]
        punishes = player_profile_data["penalty_count"]["PUNISH"]
        tempbans = player_profile_data["penalty_count"]["TEMPBAN"]

        elapsed_time_seconds = (datetime.now() - datetime.fromisoformat(str(created))).total_seconds()

        penalties_message = ""
        if kicks == 0 and punishes == 0 and tempbans == 0:
            penalties_message += f"{TRANSL['nopunish'][LANG]}"
        else:
            if punishes > 0:
                penalties_message += f"{punishes} punishes"
            if kicks > 0:
                if punishes > 0:
                    penalties_message += ", "
                penalties_message += f"{kicks} kicks"
            if tempbans > 0:
                if punishes > 0 or kicks > 0:
                    penalties_message += ", "
                penalties_message += f"{tempbans} tempbans"

        player_id_query = "SELECT s.id FROM steam_id_64 AS s WHERE s.steam_id_64 = :player_id"

        queries = {
            "tot_games": "SELECT COUNT(*) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "avg_combat": "SELECT AVG(combat) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "avg_offense": "SELECT AVG(offense) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "avg_defense": "SELECT AVG(defense) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "avg_support": "SELECT AVG(support) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "tot_kills": "SELECT SUM(kills) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "tot_teamkills": "SELECT SUM(teamkills) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "tot_deaths": "SELECT SUM(deaths) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "tot_deaths_by_tk": "SELECT SUM(deaths_by_tk) FROM public.player_stats WHERE playersteamid_id = :db_player_id",
            "most_used_weapons": """
                SELECT weapon, SUM(usage_count) AS total_usage 
                FROM (
                    SELECT playersteamid_id, weapon_data.key AS weapon, 
                    (weapon_data.value::text)::int AS usage_count 
                    FROM public.player_stats, 
                    jsonb_each(weapons::jsonb) AS weapon_data 
                    WHERE playersteamid_id = :db_player_id
                ) AS weapon_usage 
                GROUP BY weapon 
                ORDER BY total_usage DESC 
                LIMIT 3
            """,
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
            """
        }

        with enter_session() as sess:
            db_player_result = sess.execute(text(player_id_query), {"player_id": player_id}).fetchone()
            if not db_player_result:
                logger.error(f"No db_player_id for {player_id}")
                return

            db_player_id = db_player_result[0]
            params = {"db_player_id": db_player_id}

            results = {}
            for key, query in queries.items():
                result = sess.execute(text(query), params).fetchall()
                results[key] = result

            tot_games = int(results["tot_games"][0][0])
            avg_combat = round(float(results["avg_combat"][0][0]), 2)
            avg_offense = round(float(results["avg_offense"][0][0]), 2)
            avg_defense = round(float(results["avg_defense"][0][0]), 2)
            avg_support = round(float(results["avg_support"][0][0]), 2)
            tot_kills = int(results["tot_kills"][0][0])
            tot_teamkills = int(results["tot_teamkills"][0][0])
            tot_deaths = int(results["tot_deaths"][0][0])
            tot_deaths_by_tk = int(results["tot_deaths_by_tk"][0][0])

            most_used_weapons = "\n".join(
                f"{row[0]} ({row[1]} kills)"
                for row in results["most_used_weapons"][:3]
            )

            most_killed = "\n".join(
                f"{row[0]} : {row[1]} ({row[2]} games)"
                for row in results["most_killed"][:3]
            )

            most_death_by = "\n".join(
                f"{row[0]} : {row[1]} ({row[2]} games)"
                for row in results["most_death_by"][:3]
            )

        if tot_deaths - tot_deaths_by_tk == 0:
            ratio_kd = (tot_kills - tot_teamkills)
        else :
            ratio_kd = round(((tot_kills - tot_teamkills) / (tot_deaths - tot_deaths_by_tk)), 2)

        message = (
            f"{player_name}\n"
            "\n"
            f"{TRANSL['firsttimehere'][LANG]}\n"
            f"{readable_duration(elapsed_time_seconds)}\n"
            f"{TRANSL['gamesessions'][LANG]} : {sessions_count}\n"
            f"{TRANSL['playedgames'][LANG]} : {tot_games}\n"
            "\n"
            f"{TRANSL['cumulatedplaytime'][LANG]}\n"
            f"{readable_duration(total_playtime_seconds)}\n"
            f"({TRANSL['averagesession'][LANG]} : {readable_duration(total_playtime_seconds/sessions_count)})\n"
            "\n"
            f"▒ {TRANSL['punishments'][LANG]} ▒\n"
            f"{penalties_message}\n"
            "\n"
            f"▒ {TRANSL['averages'][LANG]} ▒\n"
            f"{TRANSL['combat'][LANG]} : {avg_combat} ; {TRANSL['support'][LANG]} : {avg_support}\n"
            f"{TRANSL['offense'][LANG]} : {avg_offense} ; {TRANSL['defense'][LANG]} : {avg_defense}\n"
            "\n"
            f"▒ {TRANSL['totals'][LANG]} ▒\n"
            f"{TRANSL['kills'][LANG]} : {tot_kills} ({tot_teamkills} TKs)\n"
            f"{TRANSL['deaths'][LANG]} : {tot_deaths} ({tot_deaths_by_tk} TKs)\n"
            f"{TRANSL['ratio'][LANG]} {TRANSL['kills'][LANG]}/{TRANSL['deaths'][LANG]} : {ratio_kd}\n"
            "\n"
            f"▒ {TRANSL['favoriteweapons'][LANG]} ▒\n"
            f"{most_used_weapons}\n"
            "\n"
            f"▒ {TRANSL['victims'][LANG]} ▒\n"
            f"{most_killed}\n"
            "\n"
            f"▒ {TRANSL['nemesis'][LANG]} ▒\n"
            f"{most_death_by}"
        )

        rcon.message_player(
            player_name=player_name,
            player_id=player_id,
            message=message,
            by="all_time_stats",
            save_message=False
        )

    except Exception as error:
        logger.error(error)


# logger = logging.getLogger(__name__)
logger = logging.getLogger('rcon')
