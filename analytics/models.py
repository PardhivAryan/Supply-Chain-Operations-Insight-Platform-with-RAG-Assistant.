from django.db import models


class DatasetImport(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("EXTRACTED", "Extracted"),
        ("PROCESSED", "Processed"),
        ("FAILED", "Failed"),
    ]

    file_name = models.CharField(max_length=255)
    extracted_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    rows_loaded = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-extracted_at"]

    def __str__(self):
        return f"{self.file_name} ({self.status})"


class BusinessKPI(models.Model):
    name = models.CharField(max_length=150)
    value = models.CharField(max_length=255)
    category = models.CharField(max_length=100, default="General")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name}: {self.value}"


class BusinessReport(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    question = models.TextField()
    answer = models.TextField()
    retrieved_context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.question[:80]
