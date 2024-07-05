import requests
import json
import os
from dotenv import load_dotenv
import time
import hashlib
from scripts.utils import get_player_name, print_progress_bar

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

def process_teams(pass_iteration, brawler_stats, seen_players, teams, primary_team_victory, primary_team_index):
    secondary_team_index = 1 - primary_team_index
    for player in teams[primary_team_index]:
        brawler_stats.update_brawler_stats(player['brawler']['name'], primary_team_victory)
        if pass_iteration == 1:
            seen_players.add(player['tag'])
    for player in teams[secondary_team_index]:
        brawler_stats.update_brawler_stats(player['brawler']['name'], not primary_team_victory)
        if pass_iteration == 1:
            seen_players.add(player['tag'])

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

def fetch_battle_log(pass_iteration, player_tag, brawler_stats, seen_players, battle_tracker):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}/battlelog'
    response = requests.get(BASE_URL, headers=HEADERS)
    
    if response.status_code == 200:
        battle_log = response.json()
        print(f'Now getting stats for player [{get_player_name(player_tag)}] ')
        for item in battle_log.get('items', []):
            battle = item.get('battle')
            # print(item.get('event'), battle.get('mode'))
            if not battle or (battle.get('mode') in ['soloShowdown', 'duoShowdown']):
                continue
            
            if not item.get('event').get('mode') or "5V5" in item.get('event').get('mode'): # sometimes ID == 0 and mode == None
                continue

            battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
            if battle_tracker.is_battle_processed(battle_hash):
                battle_tracker.update_duplicate_battles(1)
                continue
            battle_tracker.add_processed_battle(battle_hash)
            battle_tracker.update_unique_battles(1)

            teams = battle.get('teams', [])
            primary_team_index = get_player_team_index(player_tag, teams)
            if len(teams) == 2:
                primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                process_teams(pass_iteration, brawler_stats, seen_players, teams, primary_team_victory, primary_team_index)
    else:
        print(f"Failed to fetch battle log: {response.status_code}, {response.text} using request URL: {BASE_URL}")

def main():
    battle_tracker = BattleLogTracker()
    seen_players = set()
    traversed_players = set()
    brawler_stats = BrawlerStats()
    iterations = count = 1
    initial_player_tag = "#PLYYP2RRQ" 
    fetch_battle_log(iterations, initial_player_tag, brawler_stats, seen_players, battle_tracker) # update seen_players to all players in first players battle log
    traversed_players.add(initial_player_tag) # add first player to traversed players set
    print(f'Initial player count: {len(seen_players)}')
    for new_player_tag in seen_players: # iterate over each of the first players seen playres
        count += 1
        if new_player_tag not in traversed_players: # check that the player has not been traversed yet
            traversed_players.add(new_player_tag) # add the new player to the traversed set
            iterations += 1
            print_progress_bar(count, len(seen_players), prefix='Progress:', suffix='Complete', length=50)
            fetch_battle_log(iterations, new_player_tag, brawler_stats, seen_players, battle_tracker)
    
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

main()
