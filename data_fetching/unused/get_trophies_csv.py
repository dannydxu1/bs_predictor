import json
import pandas as pd

def display_composite_ranking_from_json(filepath):
    """
    Display the composite ranking of brawlers from a JSON file.
    
    Args:
        filepath (str): The path to the JSON file containing brawler winrates.
    """
    # Load JSON data from a file
    with open(filepath, 'r') as file:
        data = json.load(file)

    # Convert JSON to DataFrame
    df = pd.DataFrame.from_dict(data, orient='index')

    # Usage Rat = # wins + # losses
    df['UsageRate'] = df['win'] + df['loss']

    # Standardize the columns using the following formulas
        # standardized_winrate = (winrate - mean_winrate)/(stdev_winrate)
        # standardized_userate = (userate - mean_userate)/(stdev_userate)
    df['Standardized Winrate'] = (df['winrate'] - df['winrate'].mean()) / df['winrate'].std()
    df['Standardized Usage Rate'] = (df['UsageRate'] - df['UsageRate'].mean()) / df['UsageRate'].std()

    # Calculate Composite Score
    alpha = 1 # weight for winrate
    beta = 0.01 # weight for usage rate
    df['Composite Score'] = alpha * df['Standardized Winrate'] + beta * df['Standardized Usage Rate']

   
    df['Rank'] = df['Composite Score'].rank(ascending=False)  # Rank Brawlers by Composite Score
    df = df.sort_values('Rank') # Sort by Rank
    # Print the entire DataFrame
    pd.set_option('display.max_rows', None)  # Display all rows
    pd.set_option('display.max_columns', None)  # Display all columns
    pd.set_option('display.width', None)  # Display full width of the DataFrame
    pd.set_option('display.max_colwidth', None)  # Display full column width
    print(df) # Display the DataFrame

display_composite_ranking_from_json('brawler_winrates.json')