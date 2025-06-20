# traffic_ai.py
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from joblib import dump, load
import os
import random

MODEL_PATH = "traffic_model_v2.joblib"
DATA_PATH = "traffic_data_v2.csv"
FEATURE_NAMES = [
    'waiting_NS', 'waiting_EW', 'bus_request_NS', 'bus_request_EW'
]

def train_model():

    if not os.path.exists(DATA_PATH):
        print(f"[INFO] Creating dummy data '{DATA_PATH}'...")
        data = []
        for _ in range(500):
            waiting_ns = random.randint(0, 50)
            waiting_ew = random.randint(0, 50)
            bus_ns = random.choice([0, 1])
            bus_ew = random.choice([0, 1])

            # La décision est fortement influencée par le bus
            score_ns = waiting_ns + bus_ns * 30
            score_ew = waiting_ew + bus_ew * 30
            label = 'NS' if score_ns > score_ew else 'EW'
            data.append([waiting_ns, waiting_ew, bus_ns, bus_ew, label])

        df = pd.DataFrame(data, columns=FEATURE_NAMES + ['label'])
        df.to_csv(DATA_PATH, index=False)

    df = pd.read_csv(DATA_PATH)
    if df.empty or len(df) < 10:
        print("[INFO] Not enough data to train.")
        return None

    df['label'] = df['label'].map({'NS': 0, 'EW': 1})
    X = df[FEATURE_NAMES]
    y = df['label']

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    dump(model, MODEL_PATH)
    print("[INFO] Model trained and saved.")
    return model


# --- Logique d'IA ---

class TrafficAI:

    def __init__(self):
        self.model = self._load_or_train_model()
        self.emergency_direction = None
        self.bus_requests = set()

    def _load_or_train_model(self):
        if os.path.exists(MODEL_PATH):
            print(f"[INFO] Loading model from {MODEL_PATH}")
            return load(MODEL_PATH)
        else:
            print("[INFO] Model not found. Training a new one.")
            return train_model()

    def report_emergency(self, direction):
        print(f"[AI STATE] Emergency reported for direction: {direction}")
        self.emergency_direction = direction

    def report_bus_request(self, direction):
        print(f"[AI STATE] Bus priority request for direction: {direction}")
        self.bus_requests.add(direction)

    def clear_states(self):
        self.emergency_direction = None
        self.bus_requests.clear()

    def decide(self, waiting_NS, waiting_EW):
        if self.emergency_direction in ['NS', 'EW']:
            direction = self.emergency_direction
            # L'urgence est prioritaire, on prépare une décision spéciale
            decision = {'direction': direction, 'duration': 20, 'reason': 'EMERGENCY VEHICLE PRIORITY'}
            self.clear_states()
            return decision

        if self.model is None:
            score_ns = waiting_NS + (50 if 'NS' in self.bus_requests else 0)
            score_ew = waiting_EW + (50 if 'EW' in self.bus_requests else 0)
            direction = "NS" if score_ns >= score_ew else "EW"
            return {'direction': direction, 'duration': 15, 'reason': 'Fallback logic (no model)'}

        bus_ns = 1 if 'NS' in self.bus_requests else 0
        bus_ew = 1 if 'EW' in self.bus_requests else 0

        data_to_predict = pd.DataFrame([[
            waiting_NS, waiting_EW, bus_ns, bus_ew
        ]], columns=FEATURE_NAMES)

        prediction = self.model.predict(data_to_predict)[0]
        direction = "NS" if prediction == 0 else "EW"

        # Calcul simple de durée pour la démo
        base_duration = 10
        waiting_count = waiting_NS if direction == 'NS' else waiting_EW
        duration = min(45, base_duration + waiting_count // 2)

        decision = {'direction': direction, 'duration': round(duration), 'reason': 'AI Model Decision'}

        self.clear_states()
        return decision


_ai_instance = TrafficAI()

def report_emergency_to_ai(direction):
    _ai_instance.report_emergency(direction)


def report_bus_to_ai(direction):
    _ai_instance.report_bus_request(direction)