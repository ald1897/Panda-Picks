import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

def build_prediction_model():
    """
    Build a machine learning model to predict NFL game outcomes
    based on team grades and advantage metrics.
    """
    conn = sqlite3.connect("../../database/nfl_data.db")

    # Join picks_results with grades data
    query = """
    SELECT 
        pr.*,
        h.OVR as home_ovr, h.OFF as home_off, h.DEF as home_def,
        a.OVR as away_ovr, a.OFF as away_off, a.DEF as away_def
    FROM picks_results pr
    JOIN grades h ON pr.Home_Team = h.TEAM
    JOIN grades a ON pr.Away_Team = a.TEAM
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Feature engineering
    df['ovr_diff'] = df['home_ovr'] - df['away_ovr']
    df['off_diff'] = df['home_off'] - df['away_off']
    df['def_diff'] = df['home_def'] - df['away_def']
    df['line_diff'] = df['Home_Line_Close'] - df['Away_Line_Close']

    # Prepare features and target
    features = ['ovr_diff', 'off_diff', 'def_diff', 'line_diff',
                'Overall_Adv', 'Offense_Adv', 'Defense_Adv']

    X = df[features].fillna(0)
    y = df['Correct_Pick']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42)

    # Train model
    print("Training Random Forest model...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"Model accuracy: {accuracy:.2f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Feature importance
    feature_importance = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)

    print("\nFeature Importance:")
    print(feature_importance)

    # Save model for future predictions
    joblib.dump(model, 'nfl_prediction_model.joblib')
    print("\nModel saved to 'nfl_prediction_model.joblib'")

    # Example: Predict a new game
    print("\nExample prediction for a new game:")

    # Example data for a hypothetical game (could be loaded from database)
    new_game = pd.DataFrame({
        'ovr_diff': [5.0],       # Home team OVR is 5 points better
        'off_diff': [7.0],       # Home team OFF is 7 points better
        'def_diff': [3.0],       # Home team DEF is 3 points better
        'line_diff': [-6.0],     # Home team favored by 3 points (-3 vs +3)
        'Overall_Adv': [10.0],   # Overall advantage of 10
        'Offense_Adv': [12.0],   # Offense advantage of 12
        'Defense_Adv': [8.0]     # Defense advantage of 8
    })

    prediction = model.predict(new_game)
    pred_proba = model.predict_proba(new_game)

    print(f"Prediction: {'Correct' if prediction[0] == 1 else 'Incorrect'}")
    print(f"Probability: {pred_proba[0][1]:.2f}")

    return model, feature_importance

if __name__ == "__main__":
    model, importance = build_prediction_model()
