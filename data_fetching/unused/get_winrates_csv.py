import requests
import json
import os
from dotenv import load_dotenv
import time
import hashlib
import csv
from shared.utils import get_player_name, print_progress_bar

# Load environment variables from .env file
start_time = time.time()
load_dotenv()

# Fetch API key and player tag from environment variables
API_KEY = os.getenv('BRAWL_STARS_API_KEY')
PLAYER_TAG = os.getenv('BRAWL_STARS_PLAYER_TAG')

if not API_KEY or not PLAYER_TAG:
    raise ValueError("Please set the BRAWL_STARS_API_KEY and PLAYER_TAG environment variables in the .env file.")

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

# Cache for player info
player_info_cache = {}

def get_player_info(player_tag):
    if player_tag in player_info_cache:
        return player_info_cache[player_tag]

    base_url = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}'
    response = requests.get(base_url, headers=HEADERS)
    if response.status_code == 200:
        player_info = response.json()
        player_info_cache[player_tag] = player_info  # Cache the response
        return player_info
    else:
        print(f"Failed to fetch player info: {response.status_code}, {response.text}")
        return None
    

def create_battle_hash(battle_time, teams):
    player_tags = []
    for team in teams:
        for player in team:
            player_tags.append(player['tag'])
    player_tags.sort()
    unique_string = battle_time + ''.join(player_tags)
    return hashlib.sha256(unique_string.encode()).hexdigest()

def fetch_battle_log(player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer):
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
                    for team_index, team in enumerate(teams):
                        for player in team:
                            teammates = sorted([p['brawler']['name'] for p in team if p['tag'] != player['tag']])
                            opponents = sorted([p['brawler']['name'] for p in teams[1 - team_index]])
                            win_status = 1 if (primary_team_index == team_index and primary_team_victory) or (primary_team_index != team_index and not primary_team_victory) else 0
                            csv_writer.writerow([
                                battle_hash,
                                item.get('battleTime'), player['tag'], player['brawler']['name'],
                                win_status,
                                item.get('event').get('mode'), item.get('event').get('map'),
                                '', '',
                                ','.join(teammates), ','.join(opponents)
                            ])
                            to_traverse.add(player['tag'])
        seen_players.add(current_player_tag)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text} using request URL: {BASE_URL}")

def main(initial_player_tag, battle_quantity):
    battle_tracker = BattleLogTracker()
    brawler_stats = BrawlerStats()
    seen_players, to_traverse = set(), set()
    to_traverse.add(initial_player_tag) 

    # Open CSV file for writing
    with open('data/new_battle_data.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write CSV header
        csv_writer.writerow(['match_id', 'battle_time', 'player_id', 'brawler_id', 'win', 'battle_mode', 'map_name', 'player_trophies', 'brawler_trophies', 'teammates', 'opponents'])

        # while there are players to traverse and we haven't reached the desired number of battles
        while to_traverse and battle_tracker.unique_battles < battle_quantity:
            # Copy the current traversal set to avoid modifying it while iterating
            traverse_copy = to_traverse.copy()
            to_traverse.clear()
            for player_tag in traverse_copy: # Process every player in the traversal copy, resulting in newly encountered players being processed
                print_progress_bar(battle_tracker.unique_battles, battle_quantity, prefix='Progress:', suffix='Complete', length=100)
                if battle_tracker.unique_battles >= battle_quantity:
                    break
                fetch_battle_log(player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer)
                
                # Flush the file every 10,000 battles
                if battle_tracker.unique_battles % 10000 == 0: 
                    print(f'Backing up data at {battle_tracker.unique_battles} battles')
                    csvfile.flush()


    dupes, battles = battle_tracker.get_counters()
    print(f'Evaluated {battles} unique battles.')
    print(f'Ignored {dupes} duplicate battles.')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Script executed in {elapsed_time:.2f} seconds")

main("#PLYYP2RRQ", 1000)
