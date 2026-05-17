import json
import pickle

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
except ModuleNotFoundError as error:
    if error.name == "sklearn":
        raise SystemExit(
            "scikit-learn is not installed for this Python interpreter.\n"
            "Run training with the project virtual environment instead:\n"
            "  venv/bin/python train.py"
        ) from error
    raise

with open("intents.json", "r") as f:
    intents = json.load(f)

X = []
y = []

for intent, phrases in intents.items():
    for phrase in phrases:
        X.append(phrase)
        y.append(intent)

vectorizer = TfidfVectorizer()
X_vec = vectorizer.fit_transform(X)

model = LogisticRegression(max_iter=1000)
model.fit(X_vec, y)

with open("vectorizer.pkl", "wb") as f:
    pickle.dump(vectorizer, f)

with open("intent_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained successfully")