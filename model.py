import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load trained objects from beside this file, not from whichever folder launched Python.
with open(BASE_DIR / "vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)

with open(BASE_DIR / "intent_model.pkl", "rb") as f:
    model = pickle.load(f)

MIN_CONFIDENCE = 0.12

def predict_intent(text):
    vec = vectorizer.transform([text])
    probabilities = model.predict_proba(vec)[0]
    best_index = probabilities.argmax()

    if probabilities[best_index] < MIN_CONFIDENCE:
        return "unknown"

    return model.classes_[best_index]
