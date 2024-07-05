import pandas as pd

def remove_first_three_columns(input_file, output_file):
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Drop the first three columns
   
    # Split the teammates and opponents columns into individual columns
    df[['teammate1', 'teammate2']] = df['teammates'].str.split(',', expand=True)
    df[['opponent1', 'opponent2', 'opponent3']] = df['opponents'].str.split(',', expand=True)

    # Drop the original teammates and opponents columns
    df = df.drop(['teammates', 'opponents'], axis=1)

    # Reorder columns to match the desired format
    df = df[['brawler_id', 'win', 'battle_mode', 'map_name', 'teammate1', 'teammate2', 'opponent1', 'opponent2', 'opponent3']]

    # Save the modified DataFrame to a new CSV file
    df.to_csv(output_file, index=False)
    
input_file = 'data/1M_battle_data.csv'
output_file = 'output.csv'
remove_first_three_columns(input_file, output_file)
