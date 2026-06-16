from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from analytics.data_pipeline import clean_supply_chain_data, extract_dataset
from analytics.kpi_engine import generate_business_outputs
from analytics.models import BusinessKPI, BusinessReport, DatasetImport


KPI_CATEGORIES = {
    "total_orders": "Volume",
    "total_revenue": "Revenue",
    "total_profit": "Profitability",
    "average_profit_margin": "Profitability",
    "total_quantity": "Volume",
    "average_order_value": "Revenue",
    "late_delivery_rate": "Delivery",
    "average_delivery_delay": "Delivery",
    "best_region_by_revenue": "Region",
    "worst_region_by_late_delivery_rate": "Delivery",
    "top_product_by_revenue": "Product",
    "top_category_by_revenue": "Product",
    "top_shipping_mode_by_volume": "Shipping",
    "number_of_countries": "Coverage",
    "number_of_product_categories": "Coverage",
}


class Command(BaseCommand):
    help = "Extract, clean, analyze, report, and save local supply-chain KPIs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess data even when output files already exist.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting local supply-chain data processing...")
        extraction = extract_dataset()
        for message in extraction["messages"]:
            self.stdout.write(message)

        if extraction["status"] != "ok" or not extraction["main_csv"]:
            DatasetImport.objects.create(
                file_name=extraction["zip_file"] or "No ZIP file",
                status="FAILED",
                notes="\n".join(extraction["messages"]),
            )
            raise CommandError("Processing stopped because no usable main supply-chain CSV was detected.")

        dataset_import = DatasetImport.objects.create(
            file_name=extraction["zip_file"],
            status="EXTRACTED",
            notes="\n".join(extraction["messages"]),
        )

        try:
            cleaned_df, context = clean_supply_chain_data(Path(extraction["main_csv"]))
            summary = generate_business_outputs(
                cleaned_df,
                context,
                Path(extraction["description_csv"]) if extraction.get("description_csv") else None,
            )
        except Exception as exc:
            dataset_import.status = "FAILED"
            dataset_import.notes = f"{dataset_import.notes}\nProcessing error: {exc}"
            dataset_import.save(update_fields=["status", "notes"])
            raise

        with transaction.atomic():
            BusinessKPI.objects.all().delete()
            for name, value in summary["kpis"].items():
                BusinessKPI.objects.create(
                    name=name,
                    value=str(value),
                    category=KPI_CATEGORIES.get(name, "General"),
                )
            BusinessReport.objects.create(
                title="Generated Supply Chain Business Report",
                content=Path(summary["report_path"]).read_text(encoding="utf-8"),
            )
            dataset_import.status = "PROCESSED"
            dataset_import.rows_loaded = int(context["cleaned_row_count"])
            dataset_import.processed_at = timezone.now()
            dataset_import.notes = (
                f"{dataset_import.notes}\n"
                f"Cleaned rows: {context['cleaned_row_count']}\n"
                f"Output summary: {summary['report_path']}"
            )
            dataset_import.save()

        self.stdout.write(self.style.SUCCESS("Processing completed."))
        self.stdout.write(f"Cleaned CSV: {context['cleaned_data_path']}")
        self.stdout.write("KPI summary: outputs/business_kpi_summary.json")
        self.stdout.write("Business report: outputs/generated_business_report.md")
        self.stdout.write("RAG documents: outputs/rag_documents/")
