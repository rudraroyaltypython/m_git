from datetime import date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from dateutil.parser import parse as dt_parse
from django.shortcuts import render
from .models import NumberEntry
from django.db.models import Q

from .services import predict_for_date, PREDICT_SVC_VERSION


def index(request):
    # Collect all numbers (num1, num2, num3)
    raw_numbers = (
        list(NumberEntry.objects.values_list("num1", flat=True)) +
        list(NumberEntry.objects.values_list("num2", flat=True)) +
        list(NumberEntry.objects.values_list("num3", flat=True))
    )

    # Remove None values and duplicates
    numbers = sorted({n for n in raw_numbers if n is not None})

    # Get selected number from query params
    selected_number = request.GET.get("number")
    probability = None

    if selected_number:
        try:
            selected_number = int(selected_number)  # ✅ always int for comparison
            total_entries = NumberEntry.objects.count()
            if total_entries > 0:
                occurrence_count = NumberEntry.objects.filter(
                    Q(num1=selected_number) | Q(num2=selected_number) | Q(num3=selected_number)
                ).count()
                probability = round((occurrence_count / total_entries) * 100, 2)
        except ValueError:
            selected_number = None
    else:
        selected_number = None

    context = {
        "numbers": numbers,
        "selected_number": selected_number,   # keep as int
        "probability": probability,
    }
    return render(request, "patterns/index.html", context)


@api_view(['GET'])
@permission_classes([AllowAny])
def predict_api(request):
    ds = request.GET.get('date')
    if ds:
        try:
            d = dt_parse(ds).date()
        except Exception:
            return Response({"error": "Invalid date format."}, status=400)
    else:
        d = date.today()

    try:
        threshold = float(request.GET.get("threshold", "0.70"))
    except ValueError:
        threshold = 0.70

    result = predict_for_date(d, threshold=threshold)

    if request.GET.get("debug") == "1":
        result["debug"] = {
            "threshold_used": threshold,
            "service_version": PREDICT_SVC_VERSION,
        }

    return Response(result)


def number_probability_view(request):
    selected_number = request.GET.get("number")
    prob_triplet = prob_middle = None

    if selected_number is not None:
        try:
            selected_number = int(selected_number)
            all_triplets = [(e.num1, e.num2, e.num3) for e in NumberEntry.objects.all()]
            all_middles = [e.middle for e in NumberEntry.objects.exclude(middle=None)]

            total_triplets = len(all_triplets)
            total_middles = len(all_middles)

            triplet_count = sum(1 for t in all_triplets if selected_number in t)
            middle_count = all_middles.count(selected_number)

            prob_triplet = round((triplet_count / total_triplets) * 100, 2) if total_triplets else 0
            prob_middle = round((middle_count / total_middles) * 100, 2) if total_middles else 0
        except ValueError:
            selected_number = None

    return render(request, "number_probability.html", {
        "selected_number": selected_number,
        "prob_triplet": prob_triplet,
        "prob_middle": prob_middle,
    })
