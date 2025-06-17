# traffic_ai.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from joblib import dump, load
import os

MODEL_PATH = "traffic_model.joblib"
DATA_PATH = "data.csv"

def train_model():
    if not os.path.exists(DATA_PATH):
        print("[INFO] No data available for training.")
        return None

    df = pd.read_csv(DATA_PATH)
    if df.empty or len(df) < 10:
        print("[INFO] Not enough data to train.")
        return None

    df['label'] = df['label'].map({'NS': 0, 'EW': 1})
    X = df[['waiting_NS', 'waiting_EW']]
    y = df['label']

    model = RandomForestClassifier()
    model.fit(X, y)
    dump(model, MODEL_PATH)
    print("[INFO] Model trained and saved.")
    return model

def load_or_train_model():
    if os.path.exists(MODEL_PATH):
        return load(MODEL_PATH)
    else:
        return train_model()

# def predict_direction(model, waiting_NS, waiting_EW):
#     if model is None:
#         return "NS" if waiting_NS >= waiting_EW else "EW"
#     prediction = model.predict([[waiting_NS, waiting_EW]])[0]
#     return "NS" if prediction == 0 else "EW"

# def predict_direction(model, waiting_ns, waiting_ew):
#     """
#     Prédit la direction à passer au vert.
#     Ici, on fait simple : on choisit le côté avec le plus de voitures en attente.
#     Si égalité, on garde NS.
#     """
#     if waiting_ew > waiting_ns:
#         return "EW"
#     else:
#         return "NS"

def predict_direction(model, waiting_NS, waiting_EW):
    if model is None:
        # Laisser passer la direction la plus encombrée
        if abs(waiting_NS - waiting_EW) <= 2:
            return "NS"  # Moins de changements inutiles
        return "NS" if waiting_NS > waiting_EW else "EW"

    prediction = model.predict([[waiting_NS, waiting_EW]])[0]
    return "NS" if prediction == 0 else "EW"