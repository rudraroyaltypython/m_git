from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect
from .models import NumberEntry, ExcelUpload
import pandas as pd
from dateutil.parser import parse as dt_parse
import math
from datetime import timedelta

DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
DAY_TO_OFFSET = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5}


def import_excel_file(file_path):
    """Reusable importer (used on save + re-import)"""
    df = pd.read_excel(file_path)
    df.columns = [str(c).strip() for c in df.columns]

    day_starts = {}
    cols = list(df.columns)
    for d in DAY_ORDER:
        if d in cols:
            idx = cols.index(d)
            if idx + 2 < len(cols):
                day_starts[d] = idx

    rows_to_create = []
    seen = set()

    for _, row in df.iterrows():
        raw_date = row.get('Date', None)
        monday = None
        if isinstance(raw_date, str):
            try:
                monday = dt_parse(raw_date, dayfirst=False, fuzzy=True)
            except Exception:
                continue
        else:
            try:
                monday = pd.to_datetime(raw_date)
            except Exception:
                continue
        if monday is None or pd.isna(raw_date):
            continue

        monday = monday.date()

        for day, start_idx in day_starts.items():
            date_for_day = monday + timedelta(days=DAY_TO_OFFSET[day])

            vals = row.iloc[start_idx:start_idx+3].tolist()

            def norm(v):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    return None
                try:
                    return int(v)
                except Exception:
                    return None

            nums = [norm(v) for v in vals]

            key = (date_for_day.isoformat(), day)
            if key in seen:
                continue
            seen.add(key)

            rows_to_create.append(NumberEntry(
                date=date_for_day,
                day_label=day,
                num1=nums[0], num2=nums[1], num3=nums[2]
            ))

    NumberEntry.objects.bulk_create(rows_to_create, ignore_conflicts=True)
    return len(rows_to_create)


@admin.register(NumberEntry)
class NumberEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'day_label', 'num1', 'num2', 'num3')
    list_filter = ('day_label', 'date')
    search_fields = ('date',)


@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at', 'file')

    def save_model(self, request, obj, form, change):
        """When saving a new Excel, auto-import"""
        super().save_model(request, obj, form, change)
        count = import_excel_file(obj.file.path)
        messages.success(request, f"Imported {count} rows from {obj.file.name}")

    # Add custom re-import button in admin
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/reimport/',
                self.admin_site.admin_view(self.reimport_view),
                name='excelupload-reimport',
            ),
        ]
        return custom_urls + urls

    def reimport_view(self, request, pk):
        obj = ExcelUpload.objects.get(pk=pk)
        count = import_excel_file(obj.file.path)
        self.message_user(request, f"Re-imported {count} rows from {obj.file.name}", messages.SUCCESS)
        return redirect(f'../../{pk}/change/')

    # Show a button in admin detail view
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['reimport_url'] = f'./reimport/'
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
