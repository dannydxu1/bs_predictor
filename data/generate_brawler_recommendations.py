import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Load the data
input_csv = 'match_data.csv'
output_csv = 'brawler_recommendations.csv'
match_data = pd.read_csv(input_csv)

# Preprocessing
# One-hot encode 'battle_mode' and 'map_name'
match_data = pd.get_dummies(match_data, columns=['battle_mode', 'map_name'])

# Create binary features for each brawler's presence in the teammates and opponents columns
brawlers = match_data['brawler_id'].unique()
for brawler in brawlers:
    match_data[f'teammate_{brawler}'] = match_data.apply(lambda row: int(brawler in [row['teammate1'], row['teammate2']]), axis=1)
    match_data[f'opponent_{brawler}'] = match_data.apply(lambda row: int(brawler in [row['opponent1'], row['opponent2'], row['opponent3']]), axis=1)

# Drop original teammate and opponent columns
match_data = match_data.drop(columns=['teammate1', 'teammate2', 'opponent1', 'opponent2', 'opponent3'])

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

# Function to predict best brawlers for synergies and counters
def predict_best_brawlers(model, X_columns, brawler, teammates, enemies, top_n=3):
    # Create a feature vector with the same structure as the training data
    feature_vector = pd.DataFrame(columns=X_columns)
    feature_vector.loc[0] = 0  # Initialize all features to 0

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

# Create the output DataFrame
output_data = []

for brawler in brawlers:
    print(brawler)
    # Predict best synergies (teammates)
    best_teammates = predict_best_brawlers(model, X.columns, brawler, [brawler], [], top_n=3)
    
    # Predict best counters (opponents)
    best_counters = predict_best_brawlers(model, X.columns, brawler, [], [brawler], top_n=3)
    
    output_data.append({
        'brawler_id': brawler,
        'best_teammate_1': best_teammates[0],
        'best_teammate_2': best_teammates[1],
        'best_teammate_3': best_teammates[2],
        'best_counter_1': best_counters[0],
        'best_counter_2': best_counters[1],
        'best_counter_3': best_counters[2]
    })

output_df = pd.DataFrame(output_data)

# Save the output to a new CSV file
output_df.to_csv(output_csv, index=False)
print(f'Recommendations saved to {output_csv}')
