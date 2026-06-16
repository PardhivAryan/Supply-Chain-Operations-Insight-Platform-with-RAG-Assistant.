from django.core.management.base import BaseCommand, CommandError

from analytics.data_pipeline import extract_dataset
from analytics.models import DatasetImport


class Command(BaseCommand):
    help = "Extract the largest ZIP file from Dataset/ and detect supply-chain CSV files."

    def handle(self, *args, **options):
        result = extract_dataset()
        for message in result["messages"]:
            self.stdout.write(message)

        if result.get("candidates"):
            self.stdout.write("")
            self.stdout.write("CSV detection scores:")
            for candidate in result["candidates"]:
                if "error" in candidate:
                    self.stdout.write(f"- {candidate['path']}: ERROR {candidate['error']}")
                    continue
                self.stdout.write(
                    "- {name}: main={main_score}, description={description_score}, access_log={access_log_score}".format(
                        **candidate
                    )
                )

        zip_name = result["zip_file"] or "No ZIP file"
        DatasetImport.objects.create(
            file_name=zip_name,
            status="EXTRACTED" if result["status"] == "ok" else "FAILED",
            notes="\n".join(result["messages"]),
        )

        if result["status"] != "ok":
            raise CommandError("No usable main supply-chain CSV was detected.")

        self.stdout.write(self.style.SUCCESS("Dataset extraction and CSV detection completed."))
