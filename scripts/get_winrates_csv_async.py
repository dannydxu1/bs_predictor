
import os
import time
import hashlib
import csv
import asyncio
import aiohttp
from dotenv import load_dotenv
from utils import print_progress_bar

# Load environment variables from .env file
start_time = time.time()
load_dotenv()

# Fetch API key from environment variables
API_KEY = os.getenv('BRAWL_STARS_API_KEY')

if not API_KEY:
    raise ValueError("Please set the BRAWL_STARS_API_KEY in the .env file.")

# Headers for the API request
HEADERS = {
    'Authorization': f'Bearer {API_KEY}'
}

class BattleLogTracker:
    def __init__(self):
        self.duplicate_battles = 0
        self.unique_battles = 0
        self.processed_battles = set()
        self.lock = asyncio.Lock()

    def update_unique_battles(self):
        self.unique_battles += 1
    
    def update_duplicate_battles(self):
        self.duplicate_battles += 1

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

def create_battle_hash(battle_time, player_tags):
    unique_string = battle_time + ''.join(player_tags)
    return unique_string

async def fetch_battle_log(session, current_player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer, semaphore, num_battles):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{current_player_tag.replace("#", "%23")}/battlelog'
    async with semaphore:  # Acquire semaphore before making the request
        if battle_tracker.unique_battles > num_battles:
            return
        response = await session.get(BASE_URL, headers=HEADERS)
        if response.status == 200:
            battle_log = await response.json()
            if current_player_tag not in seen_players:  # Avoid seen players
                for item in battle_log.get('items', []): # In a Battle
                    battle = item.get('battle')
                    if not battle or (battle.get('mode') not in ['gemGrab', 'knockout', 'heist', 'hotZone', 'bounty', 'brawlBall']):
                        continue
                    
                    if not item.get('event').get('mode') or "5V5" in item.get('event').get('mode'):  # sometimes ID == 0 and mode == None
                        continue
                    
                    teams = battle.get('teams', [])
                    player_tags = []
                    for team in teams:
                        for player in team:
                            player_tags.append(player['tag'])
                    player_tags.sort()

                    # Avoid duplicate battles
                    battle_hash = create_battle_hash(item.get('battleTime'), player_tags)
                    if battle_tracker.is_battle_processed(battle_hash):
                        battle_tracker.update_duplicate_battles()
                        continue
                    battle_tracker.add_processed_battle(battle_hash)
                    battle_tracker.update_unique_battles()

                    if len(teams) == 2:
                        primary_team_index = get_player_team_index(current_player_tag, teams)
                        primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                        primary_team = sorted(p['brawler']['name'] for p in teams[primary_team_index])
                        opposing_team = sorted(p['brawler']['name'] for p in teams[1 - primary_team_index])
                        winnners, losers = [], []
                        if primary_team_victory:
                            winners = primary_team
                            losers = opposing_team
                        else:
                            winners = opposing_team
                            losers = primary_team

                        while len(primary_team) < 3:
                            primary_team.append('N/A')
                        while len(opposing_team) < 3:
                            opposing_team.append('N/A')
                        global count  # Declare that we are using the global variable
                        count += 1
                        print(count)
                        csv_writer.writerow([
                            item.get('event').get('mode'), 
                            item.get('event').get('map'),
                            winners[0], winners[1], winners[2], 
                            losers[0], losers[1], losers[2]  
                        ])
                        for player in player_tags:
                            to_traverse.add(player)

            seen_players.add(current_player_tag)
        else:
            print(f"Failed to fetch battle log: RESPONSE {response.status}")
            global failures
            failures +=1

count = 0
failures = 0

async def main(initial_player_tag, battle_quantity):
    battle_tracker = BattleLogTracker()
    brawler_stats = BrawlerStats()
    seen_players, to_traverse = set(), set()
    to_traverse.add(initial_player_tag)

    # Initialize a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(5)  # Limit to 10 concurrent requests

    # Open CSV file for writing
    with open('data/new_battle_data_rev2.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write CSV header
        csv_writer.writerow(['battle_mode', 'map_name', 'winner_1', 'winner_2', 'winner_3', 'loser_1', 'loser_2', 'loser_3'])

        async with aiohttp.ClientSession() as session:
            while to_traverse and count < battle_quantity:
                # Copy the current traversal set to avoid modifying it while iterating
                traverse_copy = to_traverse.copy()
                to_traverse.clear()
                tasks = []
                for player_tag in traverse_copy:  # Process every player in the traversal copy, resulting in newly encountered players being processed
                    if count >= battle_quantity:
                        break
                    tasks.append(fetch_battle_log(session, player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer, semaphore,battle_quantity))

                await asyncio.gather(*tasks)
                
                # Flush the file every 10,000 battles
                if battle_tracker.unique_battles % 10000 == 0:
                    print(f'Backing up data at {battle_tracker.unique_battles} battles')
                    csvfile.flush()

    dupes, battles = battle_tracker.get_counters()
    print(f'Evaluated {battles} unique battles.')
    print(f'Ignored {dupes} duplicate battles.')
    print(f'Encountered {failures} request failures.')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Script executed in {elapsed_time:.2f} seconds")

# Run the main function
asyncio.run(main("#PLYYP2RRQ", 1000000))
