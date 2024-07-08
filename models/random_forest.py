import pandas as pd
import time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib


# Load the data
data = pd.read_csv('raw_data/battle_logs_1M_07-06-2024_01:34_pm.csv')

# Sample the data
sample_size = 700000  # Adjusted sample size to 100,000 rows
sample_data = data.sample(n=sample_size, random_state=42)

# Preprocess the data
categorical_features = ['battle_mode', 'map_name', 'teammate1', 'teammate2', 'teammate3', 'opponent1', 'opponent2', 'opponent3']
target = 'brawler_id'

preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ]
)

# Separate features and target
X = sample_data[categorical_features]
y = sample_data[target]

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create a pipeline with preprocessing and a classifier model
pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(random_state=42, n_estimators=50, max_depth=10))
])

# Measure training time
start_time = time.time()
pipeline.fit(X_train, y_train)
end_time = time.time()

training_time = end_time - start_time
print(f'Training time for {sample_size} rows: {training_time:.2f} seconds')

# Predict on the test set
y_pred = pipeline.predict(X_test)

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred)
print(f'Accuracy: {accuracy}')
print(f'Classification Report:\n{report}')

# Save the pipeline (including the preprocessor and the classifier)
joblib.dump(pipeline, 'models/random_forest.pkl')
print("Model saved successfully!")
