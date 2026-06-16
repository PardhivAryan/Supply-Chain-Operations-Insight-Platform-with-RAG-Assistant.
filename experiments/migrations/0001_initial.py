# Generated for local development. Keep migrations committed so `migrate` works normally.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Experiment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("research_question", models.TextField()),
                ("control_condition", models.TextField()),
                ("treatment_condition", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("ACTIVE", "Active"),
                            ("COMPLETED", "Completed"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="DRAFT",
                        max_length=30,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ExperimentResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("participant_code", models.CharField(max_length=100)),
                (
                    "assigned_condition",
                    models.CharField(
                        choices=[("CONTROL", "Control"), ("TREATMENT", "Treatment")],
                        max_length=30,
                    ),
                ),
                ("decision", models.TextField()),
                ("confidence_score", models.DecimalField(decimal_places=2, max_digits=5)),
                ("response_time_seconds", models.DecimalField(decimal_places=2, max_digits=8)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "experiment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="experiments.experiment",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
