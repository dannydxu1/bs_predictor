import requests
import json
import os
from dotenv import load_dotenv
import time
import hashlib
from shared.utils import get_player_name, print_progress_bar

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

class BattleLogTracker:
    def __init__(self):
        self.duplicate_battles = 0
        self.unique_battles = 0
        self.processed_battles = set()

    def update_unique_battles(self, battles):
        self.unique_battles += battles
    
    def update_duplicate_battles(self, dupes):
        self.duplicate_battles += dupes

    def get_counters(self):
        return self.duplicate_battles, self.unique_battles

    def add_processed_battle(self, battle_hash):
        self.processed_battles.add(battle_hash)

    def is_battle_processed(self, battle_hash):
        return battle_hash in self.processed_battles

class BrawlerStats:
    def __init__(self):
        self.brawler_winrates = {}
        self.brawler_pickrates = {}

    def update_brawler_stats(self, brawler_name, win_status):
        result = "victory" if win_status else "defeat"
        if brawler_name not in self.brawler_winrates:
            self.brawler_pickrates[brawler_name] = 1
            self.brawler_winrates[brawler_name] = {"win": 0, "loss": 0}
        else:
            self.brawler_pickrates[brawler_name] += 1
        if result == "victory":
            self.brawler_winrates[brawler_name]["win"] += 1
        elif result == "defeat":
            self.brawler_winrates[brawler_name]["loss"] += 1

    def calculate_win_rates(self):
        for brawler, stats in self.brawler_winrates.items():
            total_games = stats['win'] + stats['loss']
            stats['winrate'] = stats['win'] / total_games if total_games > 0 else 0

    def get_stats(self):
        return self.brawler_winrates, self.brawler_pickrates

def get_player_team_index(player_tag, teams):
    for index, team in enumerate(teams):
        for player in team:
            if player['tag'] == player_tag:
                return index
    return None

def create_battle_hash(battle_time, teams):
    hash_input = battle_time
    players = []
    for team in teams:
        for player in team:
            players.append(player['name'])
    players.sort()
    hash_input += "".join(players)
    return hashlib.sha256(hash_input.encode()).hexdigest()

def process_teams(brawler_stats, to_traverse, teams, primary_team_victory, primary_team_index):
    secondary_team_index = 1 - primary_team_index
    for player in teams[primary_team_index]:
        brawler_stats.update_brawler_stats(player['brawler']['name'], primary_team_victory)
        to_traverse.add(player['tag']) # Each newly encountered player is added to the traversal set
    for player in teams[secondary_team_index]:
        brawler_stats.update_brawler_stats(player['brawler']['name'], not primary_team_victory)
        to_traverse.add(player['tag'])

def print_and_save_stats(brawler_stats, popular_brawlers):
    formatted_popular_brawler_alphabetical_stats = json.dumps({k: popular_brawlers[k] for k in sorted(popular_brawlers)}, indent=4)
    formatted_popular_brawler_stats = json.dumps(dict(sorted(popular_brawlers.items(), key=lambda item: item[1], reverse=True)), indent=4)
    formatted_brawler_winrate_stats = json.dumps(dict(sorted(brawler_stats.items(), key=lambda item: item[1]['winrate'], reverse=True)), indent=4)
    print(formatted_popular_brawler_stats)
    print(formatted_brawler_winrate_stats)
    
    with open('brawler_winrates.json', 'w') as file:
        file.write(formatted_brawler_winrate_stats)
        print("Updated 'brawler_winrates.json'")
    with open('brawler_popularity_alphabetical.json', 'w') as file:
        file.write(formatted_popular_brawler_alphabetical_stats)
        print("Updated 'brawler_popularity_alphabetical.json'")
    with open('brawler_popularity.json', 'w') as file:
        file.write(formatted_popular_brawler_stats)
        print("Updated 'brawler_popularity.json'")

def fetch_battle_log(player_tag, brawler_stats, seen_players, to_traverse, battle_tracker):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    
    if response.status_code == 200:
        battle_log = response.json()
        current_player_tag = get_player_name(player_tag)
        if current_player_tag not in seen_players: # Avoid seen players
            # print(f'Now getting stats for player [{current_player_tag}] ')
            for item in battle_log.get('items', []):
                battle = item.get('battle')
                if not battle or (battle.get('mode') in ['soloShowdown', 'duoShowdown']):
                    continue
                
                if not item.get('event').get('mode') or "5V5" in item.get('event').get('mode'): # sometimes ID == 0 and mode == None
                    continue

                # Avoid duplicate battles
                battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
                if battle_tracker.is_battle_processed(battle_hash):
                    battle_tracker.update_duplicate_battles(1)
                    continue
                battle_tracker.add_processed_battle(battle_hash)
                battle_tracker.update_unique_battles(1)

                # Process stats on a per player per team basis
                teams = battle.get('teams', [])
                primary_team_index = get_player_team_index(player_tag, teams)
                if len(teams) == 2:
                    primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                    process_teams(brawler_stats, to_traverse, teams, primary_team_victory, primary_team_index)
        seen_players.add(current_player_tag)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text} using request URL: {BASE_URL}")

def main(initial_player_tag, battle_quantity):
    battle_tracker = BattleLogTracker()
    brawler_stats = BrawlerStats()
    seen_players, to_traverse = set(), set()
    to_traverse.add(initial_player_tag) 
    # while there are players to traverse and we haven't reached the desired number of battles
    while to_traverse and battle_tracker.unique_battles < battle_quantity:
        # Copy the current traversal set to avoid modifying it while iterating
        traverse_copy = to_traverse.copy()
        to_traverse.clear()
        for player_tag in traverse_copy: # Process every player in the traversal copy, resulting in newly encountered players being processed
            print_progress_bar(battle_tracker.unique_battles, battle_quantity, prefix='Progress:', suffix='Complete', length=100)
            if battle_tracker.unique_battles > battle_quantity:
                break
            fetch_battle_log(player_tag, brawler_stats, seen_players, to_traverse, battle_tracker) # Processing results in to_traverse and battle_tracker objects changing during loop execution

            
    # Calculate win rates
    brawler_stats.calculate_win_rates()
    stats, popular_brawlers = brawler_stats.get_stats()
    print_and_save_stats(stats, popular_brawlers)

    dupes, battles = battle_tracker.get_counters()
    print(f'Evaluated {battles} unique battles.')
    print(f'Ignored {dupes} duplicate battles.')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Script executed in {elapsed_time:.2f} seconds")

main("#PLYYP2RRQ", 2000)
