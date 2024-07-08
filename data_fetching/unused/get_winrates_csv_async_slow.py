import os
import time
import hashlib
import csv
import asyncio
import aiohttp
from aiohttp import ClientResponseError, ClientConnectionError, ClientPayloadError
from dotenv import load_dotenv
from shared.utils import print_progress_bar
from shared.class_definitions import BattleLogTracker, BrawlerStats

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

def get_player_team_index(player_tag, teams):
    for index, team in enumerate(teams):
        for player in team:
            if player['tag'] == player_tag:
                return index
    return None

def create_battle_hash(battle_time, teams):
    player_tags = []
    for team in teams:
        for player in team:
            player_tags.append(player['tag'])
    player_tags.sort()
    unique_string = battle_time + ''.join(player_tags)
    return hashlib.sha256(unique_string.encode()).hexdigest()

async def fetch_battle_log(session, current_player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer):
    BASE_URL = f'https://api.brawlstars.com/v1/players/{current_player_tag.replace("#", "%23")}/battlelog'
    try:
        async with session.get(BASE_URL, headers=HEADERS) as response:
            if response.status == 200:
                battle_log = await response.json()
                if current_player_tag not in seen_players:  # Avoid seen players
                    for item in battle_log.get('items', []):
                        battle = item.get('battle')
                        if not battle or (battle.get('mode') not in ['gemGrab', 'knockout', 'heist', 'hotZone', 'bounty', 'brawlBall']):
                            continue

                        if not item.get('event').get('mode') or "5V5" in item.get('event').get('mode'):  # sometimes ID == 0 and mode == None
                            continue

                        # Avoid duplicate battles
                        battle_hash = create_battle_hash(item.get('battleTime'), battle.get('teams', []))
                        if battle_tracker.is_battle_processed(battle_hash):
                            battle_tracker.update_duplicate_battles()
                            continue
                        battle_tracker.add_processed_battle(battle_hash)
                        battle_tracker.update_unique_battles()

                        # Process stats on a per player per team basis
                        teams = battle.get('teams', [])
                        primary_team_index = get_player_team_index(current_player_tag, teams)
                        if len(teams) == 2:
                            primary_team_victory = True if (battle.get('result') and battle.get('result') == 'victory') else False
                            for team_index, team in enumerate(teams):
                                for player in team:
                                    teammates = sorted(p['brawler']['name'] for p in team if p['tag'] != player['tag'])
                                    opponents = sorted(p['brawler']['name'] for p in teams[1 - team_index])
                                    win_status = 1 if (primary_team_index == team_index and primary_team_victory) or (primary_team_index != team_index and not primary_team_victory) else 0

                                    while len(teammates) < 2:
                                        teammates.append('N/A')
                                    while len(opponents) < 3:
                                        opponents.append('N/A')

                                    csv_writer.writerow([
                                        player['brawler']['name'],
                                        win_status,
                                        item.get('event').get('mode'), 
                                        item.get('event').get('map'),
                                        '', '',
                                        teammates[0], teammates[1],  # Explicitly adding teammates
                                        opponents[0], opponents[1], opponents[2]  # Explicitly adding opponents
                                    ])
                                    to_traverse.add(player['tag'])

                seen_players.add(current_player_tag)
            else:
                print(f"Failed to fetch battle log: {response.status}, {response.text} using request URL: {BASE_URL}")
                return False
    except (ClientResponseError, ClientConnectionError, ClientPayloadError) as e:
        print(f"Error fetching data: {str(e)}")
        return False

    return True

async def main(initial_player_tag, battle_quantity):
    battle_tracker = BattleLogTracker()
    brawler_stats = BrawlerStats()
    seen_players, to_traverse = set(), set()
    to_traverse.add(initial_player_tag)

    # Open CSV file for writing
    with open('new_battle_data_rev2.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write CSV header
        csv_writer.writerow(['brawler_name', 'win', 'battle_mode', 'map_name', 'player_trophy_count', 'brawler_trophy_count', 'teammate_1', 'teammate_2', 'opponent_1', 'opponent_2', 'opponent_3'])

        async with aiohttp.ClientSession() as session:
            while to_traverse and battle_tracker.unique_battles < battle_quantity:
                # Copy the current traversal set to avoid modifying it while iterating
                traverse_copy = to_traverse.copy()
                to_traverse.clear()
                tasks = []
                for player_tag in traverse_copy:  # Process every player in the traversal copy, resulting in newly encountered players being processed
                    print_progress_bar(battle_tracker.unique_battles, battle_quantity, prefix='Progress:', suffix='Complete', length=100)
                    if battle_tracker.unique_battles >= battle_quantity:
                        break
                    tasks.append(fetch_battle_log(session, player_tag, brawler_stats, seen_players, to_traverse, battle_tracker, csv_writer))

                results = await asyncio.gather(*tasks)

                # Introduce a delay to avoid rate limiting and exponential backoff for failed requests
                if not all(results):
                    await asyncio.sleep(10)
                else:
                    await asyncio.sleep(1)
                
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

# Run the main function
asyncio.run(main("#PLYYP2RRQ", 1000))
