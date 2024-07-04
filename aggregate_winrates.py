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

def update_brawler_stats(brawler_stats, brawler_name, win_status, popular_brawlers):
    result = "victory" if win_status else "defeat"
    if brawler_name not in brawler_stats:
        popular_brawlers[brawler_name] = 1
        brawler_stats[brawler_name] = {"win": 0, "loss": 0}
    else:
        popular_brawlers[brawler_name] += 1
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

def process_teams(pass_iteration, brawler_stats, seen_players, popular_brawlers, teams, primary_team_victory, primary_team_index):
    secondary_team_index = 1 - primary_team_index
    for player in teams[primary_team_index]:
        update_brawler_stats(brawler_stats, player['brawler']['name'], primary_team_victory, popular_brawlers)
        if pass_iteration == 1:
            seen_players.add(player['tag'])
    for player in teams[secondary_team_index]:
        update_brawler_stats(brawler_stats, player['brawler']['name'], not primary_team_victory, popular_brawlers)
        if pass_iteration == 1:
            seen_players.add(player['tag'])

def print_and_save_stats(brawler_stats, popular_brawlers):
    formatted_popular_brawler_alpabetical_stats = json.dumps({k: popular_brawlers[k] for k in sorted(popular_brawlers)}, indent=4)
    formatted_popular_brawler_stats = json.dumps(dict(sorted(popular_brawlers.items(), key=lambda item: item[1], reverse=True)), indent=4)
    formatted_brawler_winrate_stats = json.dumps(dict(sorted(brawler_stats.items(), key=lambda item: item[1]['winrate'], reverse=True)), indent=4)
    print(formatted_popular_brawler_stats)
    print(formatted_brawler_winrate_stats)
    
    with open('brawler_winrates.json', 'w') as file:
        file.write(formatted_brawler_winrate_stats)
        print("Updated'brawler_winrates.json'")
    with open('brawler_popularity_alphabetical.json', 'w') as file:
        file.write(formatted_popular_brawler_alpabetical_stats)
        print("Updated'brawler_popularity_alphabetical.json'")
    with open('brawler_popularity.json', 'w') as file:
        file.write(formatted_popular_brawler_stats)
        print("Updated'brawler_popularity.json'")

def fetch_battle_log(pass_iteration, player_tag, brawler_stats, seen_players, processed_battles, popular_brawlers, dupes=0, battles=0):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    
    if response.status_code == 200:
        battle_log = response.json()
        for item in battle_log.get('items', []):
            battle = item.get('battle')
            if not battle or battle.get('mode') in ['soloShowdown', 'duoShowdown']:
                continue

            battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
            if battle_hash in processed_battles:
                    dupes += 1
                    # print("Duplicate battle detected, #:",dupes)
                    continue
            processed_battles.add(battle_hash)
            battles += 1

            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                process_teams(pass_iteration, brawler_stats, seen_players, popular_brawlers, teams, primary_team_victory, primary_team_index)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text} using request URL: {BASE_URL}")
    return dupes, battles


def main():
    dupes = battles = 0
    seen_players = set()
    brawler_stats = {}
    popular_brawlers = {}
    processed_battles = set()
    iterations = 1
    dupes, battles = fetch_battle_log(iterations, PLAYER_TAG, brawler_stats, seen_players, processed_battles, popular_brawlers, dupes=dupes, battles=battles)
    print(f'Initial player count: {len(seen_players)}')
    count = 1
    # Fetch battle logs for new player tags
    for new_player_tag in seen_players:
        count += 1
        formatted_percentage = "{:.2f}".format(((count / len(seen_players)) * 100))
        if count % 5 == 0:
            print(f"Status: {formatted_percentage}% done")
        if new_player_tag != PLAYER_TAG:
            iterations += 1
            dupes, battles = fetch_battle_log(iterations, new_player_tag, brawler_stats, seen_players, processed_battles, popular_brawlers, dupes=dupes, battles=battles)
    
    # Calculate win rates
    for brawler, stats in brawler_stats.items():
        total_games = stats['win'] + stats['loss']
        stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0

    print_and_save_stats(brawler_stats, popular_brawlers)

    print(f'Sucessfully evaluted {battles} unique battles.')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Script executed in {elapsed_time:.2f} seconds")


main()
