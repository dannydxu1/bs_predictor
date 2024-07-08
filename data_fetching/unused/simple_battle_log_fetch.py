import requests
import json
import os
from dotenv import load_dotenv
from shared.utils import get_player_name
# Load environment variables from .env file
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

def update_brawler_stats(brawler_stats, brawler_name, win_status):
    result = "victory" if win_status else "defeat"
    if brawler_name not in brawler_stats:
        brawler_stats[brawler_name] = {"win": 0, "loss": 0}
    if result == "victory":
        brawler_stats[brawler_name]["win"] += 1
        # print(brawler_name, "win")
    elif result == "defeat":
        brawler_stats[brawler_name]["loss"] += 1
        # print(brawler_name, "loss")
        
def fetch_battle_log(player_tag):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code == 200:
        print(f'Now getting stats for {get_player_name(player_tag)} player')
        # Get the JSON response
        battle_log = response.json()
        
        # Dictionary to store Brawler stats
        brawler_stats = {}

        # Process the battle log to calculate win rates
        for item in battle_log.get('items', []):
            battle = item.get('battle')
            if not battle or (battle.get('mode') in ['soloShowdown', 'duoShowdown']):
                continue

            if not item.get('event').get('mode') or "5V5" in item.get('event').get('mode'):
                continue

            # Identify all brawlers in the battle
            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                secondary_team_index = 1 - primary_team_index
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                for player in teams[primary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], primary_team_victory)
                for player in teams[secondary_team_index]:
                    update_brawler_stats(brawler_stats, player['brawler']['name'], not primary_team_victory)
   
        # Calculate win rates
        for brawler, stats in brawler_stats.items():
            total_games = stats['win'] + stats['loss']
            stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0
        
        pretty_brawler_stats = json.dumps(brawler_stats, indent=4)
        # print(pretty_brawler_stats)
        
        # Export the prettified JSON response to a file
        with open('simple_brawler_winrates.json', 'w') as file:
            file.write(pretty_brawler_stats)
        
        print("Brawler winrates saved to 'simple_brawler_winrates.json'")
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text}")


fetch_battle_log(PLAYER_TAG)
