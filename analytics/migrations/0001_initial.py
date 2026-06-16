# Generated for local development. Keep migrations committed so `migrate` works normally.
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BusinessKPI",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("value", models.CharField(max_length=255)),
                ("category", models.CharField(default="General", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="BusinessReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField()),
                ("answer", models.TextField()),
                ("retrieved_context", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="DatasetImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file_name", models.CharField(max_length=255)),
                ("extracted_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("rows_loaded", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("EXTRACTED", "Extracted"),
                            ("PROCESSED", "Processed"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
            ],
            options={"ordering": ["-extracted_at"]},
        ),
    ]
