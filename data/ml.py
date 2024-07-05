import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
import numpy as np

# Load data
brawler_data = pd.read_csv('brawler_data.csv')
match_data = pd.read_csv('data/match_data.csv')

# Preprocessing and feature engineering

# One-hot encode 'battle_mode' and 'map_name'
match_data = pd.get_dummies(match_data, columns=['battle_mode', 'map_name'])

# Create binary features for each brawler's presence in the teammates and opponents columns
brawlers = brawler_data['brawler_id'].unique()
for brawler in brawlers:
    match_data[f'teammate_{brawler}'] = match_data.apply(lambda row: int(brawler in [row['teammate1'], row['teammate2']]), axis=1)
    match_data[f'opponent_{brawler}'] = match_data.apply(lambda row: int(brawler in [row['opponent1'], row['opponent2'], row['opponent3']]), axis=1)

# Drop original teammate and opponent columns
match_data = match_data.drop(columns=['teammate1', 'teammate2', 'opponent1', 'opponent2', 'opponent3'])

# Add brawler class information
brawler_classes = brawler_data[['brawler_id', 'class']]
brawler_classes = pd.get_dummies(brawler_classes, columns=['class'])
match_data = match_data.merge(brawler_classes, left_on='brawler_id', right_on='brawler_id', how='left')

# Define the target variable
match_data['target'] = match_data['win']

# Split the data
X = match_data.drop(columns=['brawler_id', 'win', 'target'])
y = match_data['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train the model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Evaluate the model
print(f'Model Accuracy: {model.score(X_test, y_test)}')

# Model inference function
def predict_best_brawlers(model, battle_mode, map_name, teammates, enemies, top_n=3):
    # Create a feature vector with the same structure as the training data
    feature_vector = pd.DataFrame(columns=X.columns)
    feature_vector.loc[0] = 0  # Initialize all features to 0

    # Set battle mode and map name
    feature_vector[f'battle_mode_{battle_mode}'] = 1
    feature_vector[f'map_name_{map_name}'] = 1

    # Set teammate and opponent brawler presence
    for teammate in teammates:
        feature_vector[f'teammate_{teammate}'] = 1
    for enemy in enemies:
        feature_vector[f'opponent_{enemy}'] = 1

    # Predict the probabilities of each brawler being the best pick
    predictions = model.predict_proba(feature_vector)[0]

    # Get the top N brawlers based on the predicted probabilities
    top_brawlers = np.argsort(predictions)[-top_n:][::-1]
    best_brawlers = [model.classes_[brawler] for brawler in top_brawlers]

    return best_brawlers

# Example usage
best_brawlers = predict_best_brawlers(model, 'hotZone', 'Local Businesses', ['MEG', 'SANDY'], ['ANGELO', 'DYNAMIKE', 'SHELLY'], top_n=3)
print(f'Best brawlers to pick: {best_brawlers}')
