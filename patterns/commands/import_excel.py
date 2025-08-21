import math
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from dateutil.parser import parse as dt_parse
import pandas as pd

from patterns.models import NumberEntry

DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
DAY_TO_OFFSET = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5}

class Command(BaseCommand):
    help = "Import weekly sheet (m.xlsx) where each row starts at Monday date and has 3 numbers for each day MON..SAT"

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to Excel file (e.g. m.xlsx)')
        parser.add_argument('--sheet', type=str, default=None, help='Sheet name (default: first)')
        parser.add_argument('--replace', action='store_true', help='Delete all NumberEntry before import')

    def handle(self, *args, **opts):
        path = opts['path']
        sheet = opts['sheet']

        try:
            df = pd.read_excel(path, sheet_name=sheet)
        except Exception as e:
            raise CommandError(f"Failed to read Excel: {e}")

        # Normalize headers -> strings
        df.columns = [str(c).strip() for c in df.columns]

        # Find the starting index of each day block (3 columns each)
        cols = list(df.columns)
        day_starts = {}
        for d in DAY_ORDER:
            if d in cols:
                idx = cols.index(d)
                # Ensure there are at least 3 columns for this day
                if idx + 2 < len(cols):
                    day_starts[d] = idx
                else:
                    self.stdout.write(self.style.WARNING(f"Day {d} header found at end without 3 columns"))
            else:
                self.stdout.write(self.style.WARNING(f"Day header {d} not found; skipping"))

        if 'Date' not in df.columns:
            raise CommandError("Expected a 'Date' column indicating the Monday of the week.")

        if opts['replace']:
            self.stdout.write(self.style.WARNING("Deleting all existing NumberEntry records..."))
            NumberEntry.objects.all().delete()

        rows_to_create = []
        seen = set()  # (date, day_label) to avoid dupes in same file

        for _, row in df.iterrows():
            raw_date = row.get('Date', None)

            # skip rows like 'to'
            monday = None
            if isinstance(raw_date, str):
                try:
                    monday = dt_parse(raw_date, dayfirst=False, fuzzy=True)
                except Exception:
                    monday = None
            else:
                # could be a timestamp or excel serial
                try:
                    monday = pd.to_datetime(raw_date)
                except Exception:
                    monday = None

            if pd.isna(raw_date) or monday is None:
                continue

            monday = monday.date()  # just date

            for day, start_idx in day_starts.items():
                date_for_day = monday + timedelta(days=DAY_TO_OFFSET[day])

                # Read the 3 numbers for this day from adjacent columns
                try:
                    v1 = row.iloc[start_idx]
                    v2 = row.iloc[start_idx + 1]
                    v3 = row.iloc[start_idx + 2]
                except Exception:
                    v1 = v2 = v3 = None

                def norm(v):
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        return None
                    try:
                        return int(v)
                    except Exception:
                        # sometimes there could be stray text; ignore it
                        return None

                n1, n2, n3 = norm(v1), norm(v2), norm(v3)

                key = (date_for_day.isoformat(), day)
                if key in seen:
                    continue
                seen.add(key)

                rows_to_create.append(NumberEntry(
                    date=date_for_day,
                    day_label=day,
                    num1=n1, num2=n2, num3=n3
                ))

        # Bulk insert; ignore conflicts if unique_together clashes
        with transaction.atomic():
            NumberEntry.objects.bulk_create(rows_to_create, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(rows_to_create)} day-rows into NumberEntry."
        ))
