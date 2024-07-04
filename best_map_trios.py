import requests
import json
import os
from dotenv import load_dotenv
import time

# Load environment variables from .env file
start_time = time.time()
load_dotenv()

# Fetch API key and player tag from environment variables
API_KEY = os.getenv('BRAWL_STARS_API_KEY')
PLAYER_TAG = os.getenv('BRAWL_STARS_PLAYER_TAG')

if not API_KEY or not PLAYER_TAG:
    raise ValueError("Please set the BRAWL_STARS_API_KEY and BRAWL_STARS_PLAYER_TAG environment variables in the .env file.")

# URL to fetch the player's battle log

# Headers for the API request
HEADERS = {
    'Authorization': f'Bearer {API_KEY}'
}


def get_player_team_index(player_tag, teams):
    for index, team in enumerate(teams):
        for player in team:
            if player['tag'] == player_tag:
                return index
    return None




def update_trio_stats(Maps, map_name, brawler_trio, win_status):
    """ In Maps dictionary update key map's brawler trio with win status

    Args:
        Maps (Dictionary): Dictionary containing a dictionary of maps.
        brawler_trio (string): string of three brawlers example: "BIBI,JANET,MEG"
        map_name (string): name of the map
        win_status (boolean): True if win False if loss
    """
    result = "victory" if win_status else "defeat"
    if map_name not in Maps:
        Maps[map_name] = {}

    if brawler_trio not in Maps[map_name]:
        Maps[map_name][brawler_trio]= {"win": 0, "loss": 0}
    if result == "victory":
        Maps[map_name][brawler_trio]["win"] += 1
        print(brawler_trio, "win")
    elif result == "defeat":
        Maps[map_name][brawler_trio]["loss"] += 1
        print(brawler_trio, "loss")

# Create a hash using SHA-256 based off battle time and all six sorted player names
def create_battle_hash(battle_time, teams):
    hash_input = battle_time
    players = []
    for team in teams:
        for player in team:
            players.append(player['name'])
    players.sort()
    hash_input += "".join(players)
    return hash_input

def fetch_battle_log_first_pass(player_tag, Maps, seen_players, processed_battles):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code == 200:
        # Get the JSON response
        battle_log = response.json()
        

        # Process the battle log to calculate win rates
        for item in battle_log.get('items', []):
            battle = item.get('battle')
            if not battle:
                continue

            # Ignore solo and duo showdown games
            if battle.get('mode') in ['soloShowdown', 'duoShowdown']:
                continue

            battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
            processed_battles.add(battle_hash)
            global battles
            battles += 1

            # Identify the map and the trios
            map_name = item.get("event").get("map")
            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                secondary_team_index = 1 - primary_team_index
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                primary_team = []
                secondary_team = []
                for player in teams[primary_team_index]:
                    primary_team.append(player['brawler']['name'])
                    seen_players.add(player['tag'])
                for player in teams[secondary_team_index]:
                    secondary_team.append(player['brawler']['name'])
                    seen_players.add(player['tag'])
                update_trio_stats(Maps,map_name, ",".join(sorted(primary_team)) , primary_team_victory)
                update_trio_stats(Maps,map_name, ",".join(sorted(secondary_team)) , not primary_team_victory)
   
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text}")

def fetch_battle_log_sequential_passes(player_tag, Maps, processed_battles):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code == 200:
        battle_log = response.json()
        for item in battle_log.get('items', []):
            battle = item.get('battle')
            if not battle:
                continue

            # Ignore solo and duo showdown games
            if battle.get('mode') in ['soloShowdown', 'duoShowdown']:
                continue
            if  item.get('event').get('mode') == None:
                continue
            if "5v5" in item.get('event').get('mode'):
                continue
        
            battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
            if battle_hash in processed_battles:
                global dupes
                dupes += 1
                print("DUPLICATE BATTLE DETECTED, #: ",dupes)
                continue
            processed_battles.add(battle_hash)
            global battles
            battles += 1

            # Process Winners and Losers
            map_name = item.get("event").get("map")
            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                secondary_team_index = 1 - primary_team_index
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                primary_team = []
                secondary_team = []
                for player in teams[primary_team_index]:
                    primary_team.append(player['brawler']['name'])
                for player in teams[secondary_team_index]:
                    secondary_team.append(player['brawler']['name'])
                update_trio_stats(Maps,map_name, ",".join(sorted(primary_team)) , primary_team_victory)
                update_trio_stats(Maps,map_name, ",".join(sorted(secondary_team)) , not primary_team_victory)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text}")

dupes = 0
battles = 0


def main():
    seen_players = set()
    Maps = {}
    processed_battles = set()

    fetch_battle_log_first_pass(PLAYER_TAG, Maps, seen_players, processed_battles)
    print(f'Initial player count: {len(seen_players)}')
    count = 1
    # Fetch battle logs for new player tags
    for new_player_tag in seen_players:
        count += 1
        formatted_percentage = "{:.2f}".format(((count / len(seen_players)) * 100))
        print(f"Status: {formatted_percentage}% done")
        if new_player_tag != PLAYER_TAG:
            fetch_battle_log_sequential_passes(new_player_tag, Maps, processed_battles)

    # Calculate win rates
        for _, map_name in Maps.items():
            for _,stats in map_name.items():
                total_games = stats['win'] + stats['loss']
                stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0
        
    # Sort the brawler_stats dictionary by winrate
    sorted_Maps = {}
    for map_name, trios in Maps.items():
        sorted_Maps[map_name] = dict(sorted(trios.items(), key=lambda item: item[1]['winrate'], reverse=True))


        # Prettify the JSON response
        pretty_brawler_stats = json.dumps(sorted_Maps, indent=4)
        print(pretty_brawler_stats)
        print(pretty_brawler_stats)
        
        # Export the prettified JSON response to a file
        with open('brawler_trio_winrates.json', 'w') as file:
            file.write(pretty_brawler_stats)
        
        print("Brawler winrates saved to 'brawler_trio_winrates.json'")

main()

