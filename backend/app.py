# --- AI Prediction Server ---
import flask
from flask import Flask, request, jsonify
import xgboost as xgb
import pickle
import pandas as pd
import numpy as np
import os

# --- 2. Define Feature Engineering Functions ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = np.radians(lat2 - lat1); dLon = np.radians(lon2 - lon1)
    a = np.sin(dLat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dLon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def calculate_path_features(df):
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['tourist_id', 'timestamp_dt'])
    df['time_delta'] = df.groupby('tourist_id')['timestamp_dt'].diff().dt.total_seconds().fillna(0)
    df['lat_prev'] = df.groupby('tourist_id')['lat'].shift(1)
    df['lon_prev'] = df.groupby('tourist_id')['lon'].shift(1)
    df['distance'] = haversine(df['lat_prev'], df['lon_prev'], df['lat'], df['lon']).fillna(0)
    df['speed'] = (df['distance'] / (df['time_delta'] / 3600)).fillna(0)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df['speed'].fillna(0, inplace=True)
    agg_features = df.groupby('tourist_id').agg(
        mean_speed=('speed', 'mean'),
        std_speed=('speed', 'std'),
        max_speed=('speed', 'max'),
        total_distance=('distance', 'sum'),
        total_duration_seconds=('time_delta', 'sum'),
        num_points=('lat', 'count')
    ).reset_index()
    return agg_features

# --- 3. Load the Saved Model and Scaler with Absolute Paths ---
# Get the directory where app.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))

print("Loading model and scaler...")
try:
    model = xgb.XGBClassifier()
    # Fixed: Use absolute paths to find files in the backend folder
    model_path = os.path.join(base_dir, "final_tuned_xgboost_model.json")
    scaler_path = os.path.join(base_dir, "final_scaler.pkl")

    model.load_model(model_path)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)

    print("✅ Model and scaler loaded successfully.")
except Exception as e:
    print(f"❌ Error loading model or scaler: {e}")
    model = None
    scaler = None

app = Flask(__name__)

@app.route("/predict", methods=['POST'])
def predict():
    if not model or not scaler:
        return jsonify({"error": "Model not loaded. Check server logs."}), 500
    data = request.get_json()
    if not data or 'path' not in data:
        return jsonify({"error": "Invalid input: 'path' key is missing."}), 400
    path_df = pd.DataFrame(data['path'])
    features_df = calculate_path_features(path_df)
    features_to_predict = features_df.drop(['tourist_id'], axis=1, errors='ignore')
    features_to_predict.fillna(0, inplace=True)
    scaled_features = scaler.transform(features_to_predict)
    prediction = model.predict(scaled_features)[0]
    probability = model.predict_proba(scaled_features)[0]
    is_anomaly = bool(prediction == 1)
    return jsonify({
        'tourist_id': path_df['tourist_id'].iloc[0],
        'is_anomaly': is_anomaly,
        'confidence_normal': f"{probability[0]:.2f}",
        'confidence_anomaly': f"{probability[1]:.2f}"
    })

@app.route("/")
def home():
    return "<h1>Smart Tourist Safety - AI Server is Running!</h1>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)