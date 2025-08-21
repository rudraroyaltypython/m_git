from django.db import models

# -----------------------------
# File Upload for Excel sheets
# -----------------------------
class ExcelUpload(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload {self.id} at {self.uploaded_at:%Y-%m-%d %H:%M}"


# -----------------------------
# Number Entries (main dataset)
# -----------------------------
DAY_CHOICES = [
    ('MON', 'Monday'),
    ('TUE', 'Tuesday'),
    ('WED', 'Wednesday'),
    ('THU', 'Thursday'),
    ('FRI', 'Friday'),
    ('SAT', 'Saturday'),
]

class NumberEntry(models.Model):
    # calendar date of this record (unique per weekday)
    date = models.DateField(db_index=True)
    day_label = models.CharField(max_length=3, choices=DAY_CHOICES, db_index=True)

    # recorded numbers (can be null if missing)
    num1 = models.IntegerField(null=True, blank=True)
    num2 = models.IntegerField(null=True, blank=True)
    num3 = models.IntegerField(null=True, blank=True)

    # optional middle number (like "83" in your Excel file screenshot)
    middle_num = models.IntegerField(null=True, blank=True, help_text="Optional middle number if available")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['day_label']),
        ]
        # prevents duplicates for same date + weekday
        unique_together = (('date', 'day_label'),)

    def numbers(self):
        """
        Returns a clean list of numbers (ignores None).
        Example: [2, 6, 0] or [1, 5, 7]
        """
        return [n for n in [self.num1, self.num2, self.num3] if n is not None]

    def __str__(self):
        nums = ",".join(str(n) for n in self.numbers())
        return f"{self.date} {self.day_label} -> {nums}"
