import pandas as pd
import joblib

# Load the trained model
pipeline = joblib.load('trained_model.pkl')
print("Model loaded successfully!")

# Function to make predictions based on input
def recommend_brawlers(battle_mode, map_name, teammate1, teammate2, opponent1, opponent2, opponent3, top_n=5):
    categorical_features = ['battle_mode', 'map_name', 'teammate1', 'teammate2', 'opponent1', 'opponent2', 'opponent3']
    input_data = pd.DataFrame([[battle_mode, map_name, teammate1, teammate2, opponent1, opponent2, opponent3]],
                              columns=categorical_features)
    
    # Predict probabilities for each brawler
    probabilities = pipeline.predict_proba(input_data)[0]
    
    # Get the top N brawlers with the highest probabilities
    top_indices = probabilities.argsort()[-top_n:][::-1]
    top_brawlers = [(pipeline.classes_[index], probabilities[index]) for index in top_indices]
    
    return top_brawlers

# Example usage of the recommendation function
battle_mode = 'brawlBall'
map_name = "Center Stage"
teammate1 = ''
teammate2 = ''
opponent1 = 'FRANK'
opponent2 = 'FRANK'
opponent3 = 'FRANK'


recommended_brawlers = recommend_brawlers(battle_mode, map_name, teammate1, teammate2, opponent1, opponent2, opponent3, top_n=6)
print(f'Recommended Brawlers: {recommended_brawlers}')

# Function to test custom input
def test_custom_input():
    battle_mode = input("Enter battle mode: ")
    map_name = input("Enter map name: ")
    teammate1 = input("Enter first teammate: ")
    teammate2 = input("Enter second teammate: ")
    opponent1 = input("Enter first opponent: ")
    opponent2 = input("Enter second opponent: ")
    opponent3 = input("Enter third opponent: ")
    top_n = int(input("Enter number of top recommendations: "))

    recommended_brawlers = recommend_brawlers(battle_mode, map_name, teammate1, teammate2, opponent1, opponent2, opponent3, top_n=top_n)
    print(f'Recommended Brawlers: {recommended_brawlers}')

# Uncomment the line below to test with custom input
# test_custom_input()
1