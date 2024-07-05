import pandas as pd

# Define brawler classes
damage_dealers = ["8-BIT", "CARL", "CHESTER", "CHUCK", "CLANCY", "COLETTE", "COLT", "EVE", 
    "LOLA", "NITA", "PEARL", "R-T", "RICO", "SHELLY", "SPIKE", "SURGE", "TARA"]

controllers = ["AMBER", "BO", "JESSIE", "LOU", "CHARLIE", "MR. P", "EMZ", "OTIS", 
               "GALE", "SANDY", "GENE", "GRIFF", "SQUEAK", "WILLOW", "PENNY"]

snipers = ["ANGELO", "BEA", "BELLE", "BONNIE", "BROCK", "JANET", "MAISIE", "MANDY",
             "NANI", "PIPER"]

throwers = ["BARLEY", "DYNAMIKE", "GROM", "LARRY & LAWRIE", "SPROUT", "TICK"]

assasins = ["BUZZ", "CORDELIUS", "CROW", "EDGAR", "FANG", "LEON", "LILY",
             "MELODIE", "MICO", "MORTIS", "SAM", "STU"]

tanks = ["ASH", "BIBI", "BULL", "BUSTER", "DARRYL", "DRACO", "EL PRIMO", "FRANK",
          "HANK", "JACKY", "MEG", "ROSA"]

supports = ["BERRY", "BYRON", "DOUG", "GRAY", "GUS", "KIT", "MAX", "PAM", "POCO",
             "RUFFS"]

def generate_brawler_stats(input_file, output_file):
    # Read the transformed CSV file
    df = pd.read_csv(input_file)

    # Calculate win rate for each brawler
    brawler_stats = df.groupby('brawler_id').agg(
        win_rate=('win', 'mean')
    ).reset_index()

    # Calculate usage rate
    total_battles = len(df)
    brawler_stats['usage_rate'] = (df.groupby('brawler_id')['win'].count().values / total_battles) * 100

    # Standardize win rate and usage rate
    brawler_stats['standardized_winrate'] = (brawler_stats['win_rate'] - brawler_stats['win_rate'].mean()) / brawler_stats['win_rate'].std()
    brawler_stats['standardized_usage_rate'] = (brawler_stats['usage_rate'] - brawler_stats['usage_rate'].mean()) / brawler_stats['usage_rate'].std()

    # Calculate composite score
    alpha = 1  # weight for winrate
    beta = 0.01  # weight for usage rate
    brawler_stats['composite_score'] = alpha * brawler_stats['standardized_winrate'] + beta * brawler_stats['standardized_usage_rate']

    # Rank brawlers by composite score
    brawler_stats['rank'] = brawler_stats['composite_score'].rank(ascending=False)

    # Sort by win rate
    brawler_stats = brawler_stats.sort_values('win_rate', ascending=False)

    # Add class column and assign class based on brawler lists
    brawler_stats['class'] = brawler_stats['brawler_id'].apply(
        lambda x: 'damage_dealer' if x in damage_dealers else
                  'controller' if x in controllers else
                  'sniper' if x in snipers else
                  'thrower' if x in throwers else
                  'assassin' if x in assasins else
                  'tank' if x in tanks else
                  'support' if x in supports else
                  ''
    )

    # Format columns to have a maximum of three decimal places
    brawler_stats['win_rate'] = brawler_stats['win_rate'].round(3)
    brawler_stats['usage_rate'] = brawler_stats['usage_rate'].round(3)
    brawler_stats['standardized_winrate'] = brawler_stats['standardized_winrate'].round(3)
    brawler_stats['standardized_usage_rate'] = brawler_stats['standardized_usage_rate'].round(3)
    brawler_stats['composite_score'] = brawler_stats['composite_score'].round(3)
    brawler_stats['rank'] = brawler_stats['rank'].round(3)

    # Save the resulting DataFrame to a new CSV file
    brawler_stats.to_csv(output_file, index=False)

# Example usage
input_file = 'transformed_input.csv'
output_file = 'brawler_stats.csv'
generate_brawler_stats(input_file, output_file)
