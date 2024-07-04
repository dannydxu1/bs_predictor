import requests
import json
import os
from dotenv import load_dotenv
import time
import hashlib

# Load environment variables from .env file
start_time = time.time()
load_dotenv()

# Fetch API key and player tag from environment variables
API_KEY = os.getenv('BRAWL_STARS_API_KEY')
PLAYER_TAG = os.getenv('BRAWL_STARS_PLAYER_TAG')

if not API_KEY or not PLAYER_TAG:
    raise ValueError("Please set the BRAWL_STARS_API_KEY and BRAWL_STARS_PLAYER_TAG environment variables in the .env file.")

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

def update_brawler_stats(brawler_stats, brawler_name, win_status):
    result = "victory" if win_status else "defeat"
    if brawler_name not in brawler_stats:
        brawler_stats[brawler_name] = {"win": 0, "loss": 0}
    if result == "victory":
        brawler_stats[brawler_name]["win"] += 1
    elif result == "defeat":
        brawler_stats[brawler_name]["loss"] += 1

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

def fetch_battle_log_first_pass(player_tag, brawler_stats, seen_players, processed_battles):
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

            battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
            processed_battles.add(battle_hash)
            global battles
            battles += 1

            # Process Winners and Losers
            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                secondary_team_index = 1 - primary_team_index
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                for player in teams[primary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], primary_team_victory)
                    seen_players.add(player['tag'])
                for player in teams[secondary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], not primary_team_victory)
                    seen_players.add(player['tag'])
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text}")


def fetch_battle_log_sequential_passes(player_tag, brawler_stats, processed_battles):
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
            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                secondary_team_index = 1 - primary_team_index
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                for player in teams[primary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], primary_team_victory)
                for player in teams[secondary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], not primary_team_victory)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text}")

dupes = 0
battles = 0

def main():
    seen_players = set()
    brawler_stats = {}
    processed_battles = set()

    fetch_battle_log_first_pass(PLAYER_TAG, brawler_stats, seen_players, processed_battles)
    print(f'Initial player count: {len(seen_players)}')
    count = 1
    # Fetch battle logs for new player tags
    for new_player_tag in seen_players:
        count += 1
        formatted_percentage = "{:.2f}".format(((count / len(seen_players)) * 100))
        print(f"Status: {formatted_percentage}% done")
        if new_player_tag != PLAYER_TAG:
            fetch_battle_log_sequential_passes(new_player_tag, brawler_stats, processed_battles)

    # Calculate win rates
    for brawler, stats in brawler_stats.items():
        total_games = stats['win'] + stats['loss']
        stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0

    # Sort the brawler_stats dictionary by winrate
    sorted_brawler_stats = dict(sorted(brawler_stats.items(), key=lambda item: item[1]['winrate'], reverse=True))

    # Prettify the JSON response
    pretty_brawler_stats = json.dumps(sorted_brawler_stats, indent=4)
    print(pretty_brawler_stats)
    
    # Export the prettified JSON response to a file
    with open('combined_brawler_winrates.json', 'w') as file:
        file.write(pretty_brawler_stats)
    
    print(f'Sucessfully evaluted {battles} unique battles.')
    print("Combined brawler winrates saved to 'combined_brawler_winrates.json'")
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Script executed in {elapsed_time:.2f} seconds")


main()
