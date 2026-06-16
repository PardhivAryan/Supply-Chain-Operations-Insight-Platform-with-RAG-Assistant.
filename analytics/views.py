import io
import json
import zipfile
from pathlib import Path

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.management import call_command
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_POST

from .data_pipeline import CLEANED_DATA_PATH, DATASET_DIR, OUTPUTS_DIR, RAG_DOCUMENTS_DIR
from .forms import DatasetUploadForm, ProcessDatasetForm
from .kpi_engine import BUSINESS_REPORT_PATH, KPI_SUMMARY_PATH
from .models import BusinessReport, ChatMessage, DatasetImport
from .rag_engine import answer_question


class LocalLoginView(LoginView):
    template_name = "analytics/login.html"
    redirect_authenticated_user = True


class LocalLogoutView(LogoutView):
    next_page = reverse_lazy("analytics:login")


def home(request):
    if request.user.is_authenticated:
        return redirect("analytics:dashboard")
    return redirect("analytics:login")


def health(request):
    return JsonResponse({"status": "ok"})


def _load_summary():
    if not KPI_SUMMARY_PATH.exists():
        return None
    try:
        return json.loads(KPI_SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _chart_data(chart_key):
    summary = _load_summary()
    if not summary:
        return []
    return summary.get("summary_datasets", {}).get(chart_key, [])


def _display_kpis(summary):
    if not summary:
        return {}
    kpis = summary.get("kpis", {})
    return {
        "total_revenue": f"${float(kpis.get('total_revenue', 0)):,.2f}",
        "total_orders": f"{int(kpis.get('total_orders', 0)):,}",
        "late_delivery_rate": f"{float(kpis.get('late_delivery_rate', 0)):,.2f}%",
        "average_delivery_delay": f"{float(kpis.get('average_delivery_delay', 0)):,.2f} days",
        "top_category": kpis.get("top_category_by_revenue", "Not available"),
        "best_region": kpis.get("best_region_by_revenue", "Not available"),
    }


def _parse_report_markdown(content):
    report = {"title": "Generated Business Report", "sections": []}
    current_section = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            report["title"] = line[2:].strip()
            continue
        if line.startswith("## "):
            current_section = {"heading": line[3:].strip(), "items": []}
            report["sections"].append(current_section)
            continue
        if current_section is None:
            current_section = {"heading": "Overview", "items": []}
            report["sections"].append(current_section)

        item_type = "paragraph"
        text = line
        if line.startswith("- "):
            item_type = "bullet"
            text = line[2:].strip()
        elif len(line) > 3 and line[0].isdigit() and line[1:3] == ". ":
            item_type = "numbered"
            text = line[3:].strip()

        current_section["items"].append({"type": item_type, "text": text})

    return report


@login_required
def dashboard(request):
    summary = _load_summary()
    return render(
        request,
        "analytics/dashboard.html",
        {
            "summary": summary,
            "kpis": _display_kpis(summary),
            "has_outputs": CLEANED_DATA_PATH.exists() and KPI_SUMMARY_PATH.exists(),
        },
    )


@login_required
def upload(request):
    command_output = None
    process_form = ProcessDatasetForm()
    upload_form = DatasetUploadForm()

    if request.method == "POST" and request.POST.get("action") == "upload_zip":
        upload_form = DatasetUploadForm(request.POST, request.FILES)
        if upload_form.is_valid():
            uploaded_file = upload_form.cleaned_data["zip_file"]
            safe_name = get_valid_filename(Path(uploaded_file.name).name)
            target_path = DATASET_DIR / safe_name
            if target_path.exists():
                target_path = DATASET_DIR / f"{target_path.stem}_{DatasetImport.objects.count() + 1}{target_path.suffix}"

            DATASET_DIR.mkdir(parents=True, exist_ok=True)
            with target_path.open("wb") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            try:
                with zipfile.ZipFile(target_path, "r") as archive:
                    corrupt_member = archive.testzip()
                if corrupt_member:
                    target_path.unlink(missing_ok=True)
                    messages.error(request, f"Uploaded ZIP is corrupt near: {corrupt_member}")
                else:
                    messages.success(request, f"Uploaded dataset ZIP: {target_path.name}")
            except zipfile.BadZipFile:
                target_path.unlink(missing_ok=True)
                messages.error(request, "Uploaded file is not a valid ZIP archive.")

    elif request.method == "POST" and request.POST.get("action") == "process_data":
        process_form = ProcessDatasetForm(request.POST)
        if process_form.is_valid():
            output = io.StringIO()
            try:
                call_command("process_supply_chain_data", stdout=output)
                command_output = output.getvalue()
                messages.success(request, "Dataset processed successfully.")
            except Exception as exc:
                command_output = output.getvalue()
                messages.error(request, f"Dataset processing failed: {exc}")

    latest_import = DatasetImport.objects.first()
    dataset_files = [
        {"name": path.name, "size": path.stat().st_size}
        for path in sorted(DATASET_DIR.glob("*.zip"), key=lambda item: item.stat().st_size, reverse=True)
    ]
    return render(
        request,
        "analytics/upload.html",
        {
            "process_form": process_form,
            "upload_form": upload_form,
            "latest_import": latest_import,
            "dataset_files": dataset_files,
            "command_output": command_output,
            "cleaned_exists": CLEANED_DATA_PATH.exists(),
            "outputs_dir": OUTPUTS_DIR,
            "rag_dir": RAG_DOCUMENTS_DIR,
        },
    )


@login_required
def orders(request):
    query = request.GET.get("q", "").strip()
    rows = []
    columns = []
    total_loaded = 0

    if CLEANED_DATA_PATH.exists():
        df = pd.read_csv(CLEANED_DATA_PATH, nrows=5000, low_memory=False)
        total_loaded = len(df)
        display_columns = [
            "order_id_clean",
            "order_date_clean",
            "revenue",
            "profit",
            "profit_margin",
            "product_category",
            "product_name",
            "order_region",
            "order_country",
            "shipping_mode",
            "late_delivery_flag",
            "order_status",
        ]
        display_columns = [column for column in display_columns if column in df.columns]
        if not display_columns:
            display_columns = list(df.columns[:12])
        df = df[display_columns].copy()

        if query:
            searchable = df.astype(str).apply(lambda row: row.str.contains(query, case=False, na=False).any(), axis=1)
            df = df[searchable]

        df = df.head(200).fillna("Not available")
        columns = list(df.columns)
        rows = [[row.get(column, "Not available") for column in columns] for row in df.to_dict(orient="records")]

    return render(
        request,
        "analytics/orders.html",
        {
            "query": query,
            "rows": rows,
            "columns": columns,
            "total_loaded": total_loaded,
            "has_data": CLEANED_DATA_PATH.exists(),
        },
    )


@login_required
def chatbot(request):
    recent_messages = ChatMessage.objects.order_by("-created_at")[:10]
    return render(
        request,
        "analytics/chatbot.html",
        {
            "recent_messages": recent_messages,
            "has_rag_documents": RAG_DOCUMENTS_DIR.exists() and any(RAG_DOCUMENTS_DIR.glob("*.txt")),
        },
    )


@login_required
@require_POST
def clear_chat_history(request):
    ChatMessage.objects.all().delete()
    messages.success(request, "Chat history cleared.")
    return redirect("analytics:chatbot")


@login_required
def reports(request):
    latest_report = BusinessReport.objects.first()
    content = latest_report.content if latest_report else ""
    if not content and BUSINESS_REPORT_PATH.exists():
        content = BUSINESS_REPORT_PATH.read_text(encoding="utf-8")
    summary = _load_summary()
    return render(
        request,
        "analytics/reports.html",
        {
            "report": latest_report,
            "content": content,
            "structured_report": _parse_report_markdown(content) if content else None,
            "kpis": _display_kpis(summary),
            "has_report": bool(content),
        },
    )


@login_required
def api_kpis(request):
    summary = _load_summary()
    return JsonResponse(summary.get("kpis", {}) if summary else {})


@login_required
def api_monthly_revenue(request):
    return JsonResponse({"data": _chart_data("monthly_revenue_trend")})


@login_required
def api_category_revenue(request):
    return JsonResponse({"data": _chart_data("revenue_by_product_category")})


@login_required
def api_region_late_delivery(request):
    return JsonResponse({"data": _chart_data("late_delivery_rate_by_region")})


@login_required
def api_shipping_mode(request):
    return JsonResponse({"data": _chart_data("shipping_mode_performance")})


@login_required
def api_country_revenue(request):
    return JsonResponse({"data": _chart_data("revenue_by_country")})


@login_required
@require_POST
def api_chat(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload.")

    question = payload.get("question", "")
    result = answer_question(question)
    ChatMessage.objects.create(
        question=question,
        answer=result["answer"],
        retrieved_context=result["context"],
    )
    return JsonResponse({"answer": result["answer"], "context": result["context"], "matches": result["matches"]})
