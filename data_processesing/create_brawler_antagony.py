import pandas as pd
import json
from collections import defaultdict
import os
import glob

"""
Antagony - {Brawler A: {Brawler B, Brawler C, ...}, ...}
    Pick Brawler A to counter enemy Brawler B
"""

def find_most_recent_file(directory):
    files = glob.glob(os.path.join(directory, '*'))
    if not files:
        return None
    most_recent_file = max(files, key=os.path.getctime)
    return most_recent_file

def process_brawler_data(input_csv_path, output_antagony_json_path):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(input_csv_path)

    # Initialize dictionary to store antagony data
    antagony_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'total': 0}))

    # Process each row in the DataFrame
    for index, row in df.iterrows():
        winners = [row['winner_1'], row['winner_2'], row['winner_3']]
        losers = [row['loser_1'], row['loser_2'], row['loser_3']]
        
        # Skip rows with NaN values for brawlers
        winners = [brawler for brawler in winners if pd.notna(brawler)]
        losers = [brawler for brawler in losers if pd.notna(brawler)]
        
        # Update antagony stats
        for winner in winners:
            for loser in losers:
                antagony_stats[winner][loser]['wins'] += 1
                antagony_stats[winner][loser]['total'] += 1
                antagony_stats[loser][winner]['total'] += 1

    # Calculate antagony percentages
    antagony_percentages = defaultdict(dict)

    for brawler, opponents in antagony_stats.items():
        for opponent, stats in opponents.items():
            if stats['total'] > 0:
                antagony_percentage = (stats['wins'] / stats['total']) * 100
                antagony_percentages[brawler][opponent] = antagony_percentage

    # Prepare JSON data for antagony
    antagony_data = defaultdict(dict)
    for brawler in antagony_percentages:
        antagony = sorted(antagony_percentages[brawler].items(), key=lambda x: x[1], reverse=True)
        antagony_data[brawler] = [{'brawler': opponent, 'percentage': percentage} for opponent, percentage in antagony if opponent != brawler]

    # Save to JSON file
    with open(output_antagony_json_path, 'w') as f:
        json.dump(antagony_data, f, indent=4)

def main():
    most_recent_file = find_most_recent_file('raw_data')
    if most_recent_file:
        output_antagony_json_path = 'brawler_antagony.json'
        process_brawler_data(most_recent_file, output_antagony_json_path)
        print(f"Processed data from {most_recent_file} and saved to {output_antagony_json_path}")
    else:
        print("No files found in the directory.")

if __name__ == "__main__":
    main()
