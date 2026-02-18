"""
Loads pickled ML models and exposes prediction functions.
Models are loaded lazily on first call and cached in memory.
"""
import os
import pickle
import numpy as np
from django.conf import settings

ML_DIR = os.path.join(settings.BASE_DIR, 'ml_models')

# Cached models (loaded once per process)
_at_risk_model = None
_anomaly_model = None
_text_classifier = None


def _load_pickle(filename):
    path = os.path.join(ML_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return pickle.load(f)


# ===========================
# 3A: At-Risk Prediction
# ===========================
def predict_at_risk(attendance_pct, avg_marks_pct, failures=0, studytime=2,
                    absences=None, age=19, medu=2, fedu=2, traveltime=1,
                    freetime=3, goout=3, health=3):
    """
    Predict if a student is at risk of failing.
    Returns: {'is_at_risk': bool, 'risk_probability': float, 'risk_level': str}
    """
    global _at_risk_model
    if _at_risk_model is None:
        _at_risk_model = _load_pickle('at_risk_model.pkl')

    if _at_risk_model is None:
        return {'is_at_risk': False, 'risk_probability': 0.0, 'risk_level': 'Unknown'}

    model = _at_risk_model['model']
    scaler = _at_risk_model['scaler']

    # Map our app's data to UCI features
    # G1, G2 are semester grades (0-20 scale), convert from percentage
    g1 = int(avg_marks_pct * 20 / 100) if avg_marks_pct else 10
    g2 = g1  # Use same as approximation
    if absences is None:
        absences = int((100 - attendance_pct) * 0.5)  # rough approximation

    features = np.array([[absences, failures, studytime, g1, g2,
                          age, medu, fedu, traveltime, freetime, goout, health]])

    features_scaled = scaler.transform(features)
    prediction = model.predict(features_scaled)[0]
    probability = model.predict_proba(features_scaled)[0]

    risk_prob = probability[1] if len(probability) > 1 else probability[0]

    if risk_prob >= 0.7:
        risk_level = 'High'
    elif risk_prob >= 0.4:
        risk_level = 'Medium'
    else:
        risk_level = 'Low'

    return {
        'is_at_risk': bool(prediction == 1),
        'risk_probability': round(float(risk_prob) * 100, 1),
        'risk_level': risk_level,
    }


# ===========================
# 3B: Attendance Anomaly
# ===========================
def detect_anomaly(attendance_pct, max_absent_streak=0, total_classes_missed=0,
                   late_arrivals=0, subjects_below_75=0):
    """
    Detect if a student's attendance pattern is anomalous.
    Returns: {'is_anomaly': bool, 'anomaly_score': float}
    """
    global _anomaly_model
    if _anomaly_model is None:
        _anomaly_model = _load_pickle('anomaly_model.pkl')

    if _anomaly_model is None:
        return {'is_anomaly': False, 'anomaly_score': 0.0}

    model = _anomaly_model['model']
    scaler = _anomaly_model['scaler']

    features = np.array([[attendance_pct, max_absent_streak, total_classes_missed,
                          late_arrivals, subjects_below_75]])

    features_scaled = scaler.transform(features)
    prediction = model.predict(features_scaled)[0]
    score = model.decision_function(features_scaled)[0]

    return {
        'is_anomaly': bool(prediction == -1),
        'anomaly_score': round(float(abs(score)), 3),
    }


# ===========================
# 3C: Text Classification
# ===========================
def classify_text(title, body=''):
    """
    Classify a discussion thread text into a tag.
    Returns: {'tag': str, 'confidence': float}
    """
    global _text_classifier
    if _text_classifier is None:
        _text_classifier = _load_pickle('text_classifier.pkl')

    if _text_classifier is None:
        return {'tag': 'Question', 'confidence': 0.0}

    text = f"{title} {body}".strip()
    prediction = _text_classifier.predict([text])[0]
    probabilities = _text_classifier.predict_proba([text])[0]
    confidence = round(float(max(probabilities)) * 100, 1)

    return {
        'tag': prediction,
        'confidence': confidence,
    }
