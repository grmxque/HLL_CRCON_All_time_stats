"""
hooks_custom_chatcommands

A plugin for HLL CRCON (see : https://github.com/MarechJ/hll_rcon_tool)
- Display player's data for this server

Source : https://github.com/ElGuillermo

Feel free to use/modify/distribute, as long as you keep this note in your code
"""

from datetime import datetime
import logging

from sqlalchemy.sql import text  # type: ignore

from rcon.models import enter_session
from rcon.player_history import get_player_profile
from rcon.rcon import Rcon, StructuredLogLineWithMetaData


# Configuration (you must review/change these !)
# -----------------------------------------------------------------------------

# The command the players have to enter in chat to display their stats
CHAT_COMMAND_STATS = ["!me"]

# Strings translations
# Available : 0 for english, 1 for french, 2 for german
LANG = 0


# Translations
# format is : "key": ["english", "french", "german"]
# ----------------------------------------------

TRANSL = {
    # Units
    "years": ["years", "années", "Jahre"],
    "monthes": ["monthes", "mois", "Monate"],
    "weeks": ["weeks", "semaines", "Wochen"],
    "days": ["days", "jours", "Tage"],
    "hours": ["hours", "heures", "Dienststunden"],
    "minutes": ["minutes", "minutes", "Minuten"],
    "seconds": ["seconds", "secondes", "Sekunden"],
    # for this script only
    "nopunish": ["None ! Well done !", "Aucune ! Félicitations !", "Keiner! Gut gemacht!"],
    "firsttimehere": ["first time here", "tu es venu(e) il y a", "zum ersten Mal hier"],
    "gamesessions": ["game sessions", "sessions de jeu", "Spielesitzungen"],
    "playedgames": ["played games", "parties jouées", "gespielte Spiele"],
    "cumulatedplaytime": ["cumulated play time", "temps de jeu cumulé", "kumulierte Spielzeit"],
    "averagesession": ["average session", "session moyenne", "Durchschnittliche Sitzung"],
    "punishments": ["punishments", "punitions", "Strafen"],
    "averages": ["averages", "moyennes", "Durchschnittswerte"],
    "favoriteweapons": ["favorite weapons", "armes favorites", "Lieblingswaffen"],
    "victims": ["victims", "victimes", "Opfer"],
    "nemesis": ["nemesis", "nemesis", "Nemesis"],
    "combat": ["combat", "combat", "kampf"],
    "offense": ["attack", "attaque", "angriff"],
    "defense": ["defense", "défense", "verteidigung"],
    "support": ["support", "soutien", "unterstützung"],
    "totals": ["totals", "totaux", "Gesamtsummen"],
    "kills": ["kills", "kills", "tötet"],
    "deaths": ["deaths", "morts", "todesfälle"],
    "ratio": ["ratio", "ratio", "verhältnis"],
}


# (End of configuration)
# -----------------------------------------------------------------------------


def readable_duration(seconds: int) -> str:
    """
    Returns a human readable string from a number of seconds
    """
    years, lessthanayearseconds =  divmod(seconds, 31536000)
    monthes, lessthanamonthseconds = divmod(lessthanayearseconds, 18446400)
    weeks, lessthanaweekseconds =  divmod(lessthanamonthseconds, 604800)
    days, lessthanadayseconds =  divmod(lessthanaweekseconds, 86400)
    hours, lessthananhourseconds = divmod(lessthanadayseconds, 3600)
    minutes, seconds = divmod(lessthananhourseconds, 60)

    time_string = []
    if years > 0:
        time_string.append(f"{int(years)} {TRANSL['years'][LANG]}")
    if monthes > 0:
        if years > 0:
            time_string.append(", ")
        time_string.append(f"{int(monthes)} {TRANSL['monthes'][LANG]}")
    if weeks > 0:
        if years > 0 or monthes > 0:
            time_string.append(", ")
        time_string.append(f"{int(weeks)} {TRANSL['weeks'][LANG]}")
    if days > 0:
        # if years > 0 or monthes > 0 or weeks > 0:
        #     time_string.append(",\n")
        time_string.append(f"{int(days)} {TRANSL['days'][LANG]}")
    # if years > 0 or monthes > 0 or weeks > 0 or days > 0:
    #     time_string.append(",")
    if hours > 0:
        time_string.append(f"{int(hours)}h")
    else:
        time_string.append("0h")
    if minutes > 0:
        time_string.append(f"{int(minutes)}m")
    else:
        time_string.append("00m")
    if seconds > 0:
        time_string.append(f"{int(seconds)}s")
    else:
        time_string.append("00s")

    return ' '.join(time_string)

def chat_commands(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData
):
    """
    - Fast redeploy
    - Show player stats
    """
    chat_message: str|None = struct_log["sub_content"]
    if chat_message is None:
        return

    player_id: str|None = struct_log["player_id_1"]
    if player_id is None:
        return

    player_name: str|None = struct_log["player_name_1"]
    if player_name is None:
        return

    # Player profile (get_player_profile)
    if struct_log["sub_content"] in CHAT_COMMAND_STATS:
        try:
            # Gather data
            player_profile_data = get_player_profile(
                player_id=player_id,
                nb_sessions=0
            )
            if player_profile_data is not None:
                created = player_profile_data["created"]
                sessions_count = player_profile_data["sessions_count"]
                total_playtime_seconds = player_profile_data["total_playtime_seconds"]
                kicks = player_profile_data["penalty_count"]["KICK"]
                punishes = player_profile_data["penalty_count"]["PUNISH"]
                tempbans = player_profile_data["penalty_count"]["TEMPBAN"]
            else:
                return

            # First time appearance on server
            created_timestamp = datetime.fromisoformat(str(created))
            current_time = datetime.now()
            elapsed_time = current_time - created_timestamp
            elapsed_days, elapsed_seconds = elapsed_time.days, elapsed_time.seconds
            elapsed_hours = elapsed_seconds // 3600
            elapsed_minutes = (elapsed_seconds % 3600) // 60
            elapsed_seconds = elapsed_seconds % 60
            elapsed_message = ""
            if elapsed_days > 0:
                elapsed_message = str(elapsed_days) + f" {TRANSL['days'][LANG]}, "
            if elapsed_hours > 0:
                elapsed_message = elapsed_message + " " + str(elapsed_hours) + "h"
            else:
                elapsed_message = elapsed_message + " 00h"
            if elapsed_minutes > 0:
                elapsed_message = elapsed_message + " " + str(elapsed_minutes) + "m"
            else:
                elapsed_message = elapsed_message + " 00m"
            if elapsed_seconds > 0:
                elapsed_message = elapsed_message + " " + str(elapsed_seconds) + "s"
            else:
                elapsed_message = elapsed_message + " 00s"

            # Penalties
            penalties_message = ""
            if kicks == 0 and punishes == 0 and tempbans == 0:
                penalties_message = f"{TRANSL['nopunish'][LANG]}"
            else :
                if punishes > 0:
                    penalties_message = penalties_message + str(punishes) + " punishes"
                if kicks > 0:
                    if punishes > 0:
                        penalties_message = penalties_message + ", "
                    penalties_message = penalties_message + str(kicks) + " kicks"
                if tempbans > 0:
                    if punishes > 0 or kicks > 0:
                        penalties_message = penalties_message + ", "
                    penalties_message = penalties_message + str(tempbans) + " tempbans"

            # db stats
            tot_games_query = f"SELECT COUNT(*) FROM public.player_stats WHERE name = '{player_name}';"
            avg_combat_query = f"SELECT AVG(combat) FROM public.player_stats WHERE name = '{player_name}';"
            avg_offense_query = f"SELECT AVG(offense) FROM public.player_stats WHERE name = '{player_name}';"
            avg_defense_query = f"SELECT AVG(defense) FROM public.player_stats WHERE name = '{player_name}';"
            avg_support_query = f"SELECT AVG(support) FROM public.player_stats WHERE name = '{player_name}';"
            tot_kills_query = f"SELECT SUM(kills) FROM public.player_stats WHERE name = '{player_name}';"
            tot_teamkills_query = f"SELECT SUM(teamkills) FROM public.player_stats WHERE name = '{player_name}';"
            tot_deaths_query = f"SELECT SUM(deaths) FROM public.player_stats WHERE name = '{player_name}';"
            tot_deaths_by_tk_query = f"SELECT SUM(deaths_by_tk) FROM public.player_stats WHERE name = '{player_name}';"
            most_used_weapons_query = f"SELECT weapon, SUM(usage_count) AS total_usage FROM (SELECT name, weapon_data.key AS weapon, (weapon_data.value::text)::int AS usage_count FROM public.player_stats, jsonb_each(weapons::jsonb) AS weapon_data WHERE name = '{player_name}') AS weapon_usage GROUP BY weapon ORDER BY total_usage DESC LIMIT 3;"
            most_killed_query = f"SELECT key AS player_name, SUM(value::int) AS total_kills, count(*) FROM public.player_stats, jsonb_each_text(most_killed) WHERE name = '{player_name}' GROUP BY key ORDER BY total_kills DESC LIMIT 3;"
            most_death_by_query = f"SELECT key AS player_name, SUM(value::int) AS total_kills, count(*) FROM public.player_stats, jsonb_each_text(death_by) WHERE name = '{player_name}' GROUP BY key ORDER BY total_kills DESC LIMIT 3;"

            with enter_session() as sess:
                tot_games_result = sess.execute(text(tot_games_query)).fetchone()
                tot_games = int(tot_games_result[0])
                avg_combat_result = sess.execute(text(avg_combat_query)).fetchone()
                avg_combat = round(float(avg_combat_result[0]), 2)
                avg_offense_result = sess.execute(text(avg_offense_query)).fetchone()
                avg_offense = round(float(avg_offense_result[0]), 2)
                avg_defense_result = sess.execute(text(avg_defense_query)).fetchone()
                avg_defense = round(float(avg_defense_result[0]), 2)
                avg_support_result = sess.execute(text(avg_support_query)).fetchone()
                avg_support = round(float(avg_support_result[0]), 2)
                tot_kills_result = sess.execute(text(tot_kills_query)).fetchone()
                tot_kills = int(tot_kills_result[0])
                tot_teamkills_result = sess.execute(text(tot_teamkills_query)).fetchone()
                tot_teamkills = int(tot_teamkills_result[0])
                tot_deaths_result = sess.execute(text(tot_deaths_query)).fetchone()
                tot_deaths = int(tot_deaths_result[0])
                tot_deaths_by_tk_result = sess.execute(text(tot_deaths_by_tk_query)).fetchone()
                tot_deaths_by_tk = int(tot_deaths_by_tk_result[0])
                most_used_weapons_result = sess.execute(text(most_used_weapons_query)).fetchall()
                most_used_weapons = str(most_used_weapons_result[0][0]) + " (" + str(most_used_weapons_result[0][1]) + " kills)"
                most_used_weapons = most_used_weapons + "\n" + str(most_used_weapons_result[1][0]) + " (" + str(most_used_weapons_result[1][1]) + " kills)"
                most_used_weapons = most_used_weapons + "\n" + str(most_used_weapons_result[2][0]) + " (" + str(most_used_weapons_result[2][1]) + " kills)"
                most_killed_results = sess.execute(text(most_killed_query)).fetchall()
                most_killed = str(most_killed_results[0][0]) + " : " + str(most_killed_results[0][1]) + " (" + str(most_killed_results[0][2]) + " games)"
                most_killed = most_killed + "\n" + str(most_killed_results[1][0]) + " : " + str(most_killed_results[1][1]) + " (" + str(most_killed_results[1][2]) + " games)"
                most_killed = most_killed + "\n" + str(most_killed_results[2][0]) + " : " + str(most_killed_results[2][1]) + " (" + str(most_killed_results[2][2]) + " games)"
                most_death_by_results = sess.execute(text(most_death_by_query)).fetchall()
                most_death_by = str(most_death_by_results[0][0]) + " : " + str(most_death_by_results[0][1]) + " (" + str(most_death_by_results[0][2]) + " games)"
                most_death_by = most_death_by + "\n" + str(most_death_by_results[1][0]) + " : " + str(most_death_by_results[1][1]) + " (" + str(most_death_by_results[1][2]) + " games)"
                most_death_by = most_death_by + "\n" + str(most_death_by_results[2][0]) + " : " + str(most_death_by_results[2][1]) + " (" + str(most_death_by_results[2][2]) + " games)"

            ratio_kd = round(((tot_kills-tot_teamkills)/(tot_deaths-tot_deaths_by_tk)), 2)

            # Message to send
            message = (
                f"{player_name}\n"
                "\n"
                f"{TRANSL['firsttimehere'][LANG]}\n"
                f"{elapsed_message}\n"
                f"{TRANSL['gamesessions'][LANG]} : {str(sessions_count)}\n"
                f"{TRANSL['playedgames'][LANG]} : {str(tot_games)}\n"
                "\n"
                f"{TRANSL['cumulatedplaytime'][LANG]}\n"
                f"{str(readable_duration(total_playtime_seconds))}\n"
                f"({TRANSL['averagesession'][LANG]} : {str(readable_duration(total_playtime_seconds/sessions_count))})\n"
                "\n"
                f"▒ {TRANSL['punishments'][LANG]} ▒\n"
                f"{penalties_message}\n"
                "\n"
                f"▒ {TRANSL['averages'][LANG]} ▒\n"
                f"{TRANSL['combat'][LANG]} : {str(avg_combat)} ; {TRANSL['support'][LANG]} : {str(avg_support)}\n"
                f"{TRANSL['offense'][LANG]} : {str(avg_offense)} ; {TRANSL['defense'][LANG]} : {str(avg_defense)}\n"
                "\n"
                f"▒ {TRANSL['totals'][LANG]} ▒\n"
                f"{TRANSL['kills'][LANG]} : {str(tot_kills)} ({str(tot_teamkills)} TKs)\n"
                f"{TRANSL['deaths'][LANG]} : {str(tot_deaths)} ({str(tot_deaths_by_tk)} TKs)\n"
                f"{TRANSL['ratio'][LANG]} {TRANSL['kills'][LANG]}/{TRANSL['deaths'][LANG]} : {str(ratio_kd)}\n"
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

            # Send message
            rcon.message_player(
                player_id=player_id,
                message=message,
                by="custom_chatcommands",
                save_message=False
            )

        except Exception as error:
            logger.error(error)

logger = logging.getLogger(__name__)
