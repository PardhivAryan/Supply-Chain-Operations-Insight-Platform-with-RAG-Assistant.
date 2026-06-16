from django.db import models


class Experiment(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("ARCHIVED", "Archived"),
    ]

    title = models.CharField(max_length=255)
    research_question = models.TextField()
    control_condition = models.TextField()
    treatment_condition = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ExperimentResponse(models.Model):
    CONDITION_CHOICES = [
        ("CONTROL", "Control"),
        ("TREATMENT", "Treatment"),
    ]

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    participant_code = models.CharField(max_length=100)
    assigned_condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    decision = models.TextField()
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    response_time_seconds = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.participant_code} - {self.assigned_condition}"
