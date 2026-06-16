from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from analytics.data_pipeline import CLEANED_DATA_PATH, OUTPUTS_DIR, RAG_DOCUMENTS_DIR
from analytics.kpi_engine import BUSINESS_REPORT_PATH, KPI_SUMMARY_PATH
from analytics.models import BusinessKPI, BusinessReport


class Command(BaseCommand):
    help = "Run local smoke checks for generated outputs and core database records."

    def handle(self, *args, **options):
        failures = []

        def check(label, condition, detail=""):
            if condition:
                self.stdout.write(self.style.SUCCESS(f"PASS: {label}"))
            else:
                message = f"FAIL: {label}"
                if detail:
                    message = f"{message} - {detail}"
                failures.append(message)
                self.stdout.write(self.style.ERROR(message))

        check("cleaned CSV exists", CLEANED_DATA_PATH.exists(), str(CLEANED_DATA_PATH))
        check("KPI summary JSON exists", KPI_SUMMARY_PATH.exists(), str(KPI_SUMMARY_PATH))
        check("business report exists", BUSINESS_REPORT_PATH.exists(), str(BUSINESS_REPORT_PATH))
        check("RAG directory exists", RAG_DOCUMENTS_DIR.exists(), str(RAG_DOCUMENTS_DIR))

        expected_rag_files = [
            "kpi_summary.txt",
            "dataset_dictionary.txt",
            "operational_insights.txt",
            "experiment_notes.txt",
        ]
        for file_name in expected_rag_files:
            path = RAG_DOCUMENTS_DIR / file_name
            check(f"RAG document {file_name} exists", path.exists(), str(path))

        check("KPIs saved in database", BusinessKPI.objects.exists())
        check("business report saved in database", BusinessReport.objects.exists())
        check("demo user exists", get_user_model().objects.filter(username="admin").exists())

        if failures:
            raise CommandError("Smoke test failed. Fix the failed checks above and rerun.")

        self.stdout.write(self.style.SUCCESS("All local smoke tests passed."))
