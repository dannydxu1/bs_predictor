import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('BRAWL_STARS_API_KEY')

if not API_KEY:
    raise ValueError("Please set the BRAWL_STARS_API_KEY environment variable in the .env file.")

HEADERS = {
    'Authorization': f'Bearer {API_KEY}'
}

def get_player_name(player_tag):
    """
    Fetches the player's name given their player tag.
    
    Args:
        player_tag (str): The player tag of the player.
    
    Returns:
        str: The name of the player.
    """
    BASE_URL = f'https://api.brawlstars.com/v1/players/{player_tag.replace("#", "%23")}'
    response = requests.get(BASE_URL, headers=HEADERS)
    
    if response.status_code == 200:
        player_data = response.json()
        return player_data.get('name', 'Unknown')
    else:
        print(f"Failed to fetch player data: {response.status_code}, {response.text} using request URL: {BASE_URL}")
        return 'Unknown'

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar

    Args:
    iteration (int): current iteration
    total (int): total iterations
    prefix (str): prefix string
    suffix (str): suffix string
    decimals (int): positive number of decimals in percent complete
    length (int): character length of bar
    fill (str): bar fill character
    print_end (str): end character (e.g. "\r", "\r\n")

    Example:
    for i in range(0, 100):
        time.sleep(0.1)
        print_progress_bar(i + 1, 100, prefix='Progress:', suffix='Complete', length=50)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()
