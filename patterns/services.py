# patterns/services.py
from collections import Counter
from datetime import date
from typing import Dict, Any, List
from .models import NumberEntry

PREDICT_SVC_VERSION = "v2.0 (accepts threshold, returns labels & lists)"


def predict_for_date(date_obj: date, threshold: float = 0.7) -> Dict[str, Any]:
    """
    Frequency-based pattern predictor.
    1. Filter rows by weekday (from NumberEntry.day_label).
    2. Count repeating (num1, num2, num3) triplets.
    3. Return top patterns (with label, probability, count).
    4. Predict: all patterns >= threshold, else top 3.
    """
    weekday = date_obj.strftime("%a").upper()  # e.g. "MON", "TUE"
    qs = NumberEntry.objects.filter(day_label=weekday)

    if not qs.exists():
        return {
            "date": date_obj.strftime("%Y-%m-%d"),
            "weekday": weekday,
            "prediction": [],
            "samples": 0,
            "patterns": [],
            "version": PREDICT_SVC_VERSION
        }

    # Collect triplets
    triplets: List[tuple] = [(e.num1, e.num2, e.num3) for e in qs]
    counter = Counter(triplets)
    total = len(triplets)

    # Top repeating patterns
    top_patterns = []
    for nums, count in counter.most_common(5):
        prob = round(count / total, 2)
        nums_list = [n for n in nums if n is not None]  # drop None values
        label = "-".join(str(n) for n in nums_list)
        top_patterns.append({
            "numbers": nums_list,
            "label": label,
            "count": count,
            "probability": prob
        })

    # Prediction
    prediction = [
        p["numbers"] for p in top_patterns if p["probability"] >= threshold
    ] or [p["numbers"] for p in top_patterns[:3]]

    return {
        "date": date_obj.strftime("%Y-%m-%d"),
        "weekday": weekday,
        "prediction": prediction,
        "samples": total,
        "patterns": top_patterns,
        "version": PREDICT_SVC_VERSION
    }
