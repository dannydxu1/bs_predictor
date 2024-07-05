import requests
import csv
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch API key from environment variables
API_KEY = os.getenv('BRAWL_STARS_API_KEY')

if not API_KEY:
    raise ValueError("Please set the BRAWL_STARS_API_KEY environment variable in the .env file.")

# Headers for the API request
HEADERS = {
    'Authorization': f'Bearer {API_KEY}'
}

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
    
def extract_trophies(player_tag, brawler_name):
    player_info = get_player_info(player_tag)
    if not player_info:
        return -1, -1

    overall_trophies = player_info.get('trophies', -1)
    brawler_trophies = -1
    brawlers = {b['name'].lower(): b for b in player_info.get('brawlers', [])}
    if brawler_name.lower() in brawlers:
        brawler_trophies = brawlers[brawler_name.lower()].get('trophies', -1)
    return overall_trophies, brawler_trophies

def update_trophies(input_csv, output_csv):
    with open(input_csv, 'r') as infile, open(output_csv, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Read the header
        header = next(reader)
        writer.writerow(header)

        # Process each row
        for row in reader:
            player_tag = row[2]  # Adjust index based on your CSV format
            brawler_name = row[3]  # Adjust index based on your CSV format

            player_trophies, brawler_trophies = extract_trophies(player_tag, brawler_name)
            row[7] = player_trophies  # Adjust index based on your CSV format
            row[8] = brawler_trophies  # Adjust index based on your CSV format
            writer.writerow(row)

if __name__ == '__main__':
    input_csv = 'battle_data.csv'  # Input CSV file
    output_csv = 'battle_data_with_trophies.csv'  # Output CSV file
    update_trophies(input_csv, output_csv)
