import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .data_pipeline import OUTPUTS_DIR, RAG_DOCUMENTS_DIR


KPI_SUMMARY_PATH = OUTPUTS_DIR / "business_kpi_summary.json"
BUSINESS_REPORT_PATH = OUTPUTS_DIR / "generated_business_report.md"


def _finite_float(value, default=0.0) -> float:
    try:
        number = float(value)
        if np.isfinite(number):
            return number
    except (TypeError, ValueError):
        pass
    return default


def _round(value, decimals=2) -> float:
    return round(_finite_float(value), decimals)


def _format_money(value) -> str:
    return f"${_finite_float(value):,.2f}"


def _format_percent(value) -> str:
    return f"{_finite_float(value):,.2f}%"


def _label_or_not_available(value) -> str:
    if value is None:
        return "Not available"
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "unknown"} else "Not available"


def _group_order_count(grouped, order_id_column: str = "order_id_clean") -> pd.Series:
    if order_id_column in grouped.obj.columns:
        return grouped[order_id_column].nunique()
    return grouped.size()


def _top_label_by_sum(df: pd.DataFrame, group_col: str, value_col: str) -> str:
    if group_col not in df.columns or value_col not in df.columns or df.empty:
        return "Not available"
    grouped = df.groupby(group_col, dropna=False)[value_col].sum().sort_values(ascending=False)
    return _label_or_not_available(grouped.index[0]) if not grouped.empty else "Not available"


def _top_label_by_count(df: pd.DataFrame, group_col: str) -> str:
    if group_col not in df.columns or df.empty:
        return "Not available"
    grouped = df[group_col].value_counts(dropna=False)
    return _label_or_not_available(grouped.index[0]) if not grouped.empty else "Not available"


def _worst_region_by_late_rate(df: pd.DataFrame) -> str:
    if "order_region" not in df.columns or "late_delivery_flag" not in df.columns or df.empty:
        return "Not available"
    grouped = (
        df.groupby("order_region", dropna=False)
        .agg(late_delivery_rate=("late_delivery_flag", "mean"), order_count=("order_id_clean", "nunique"))
        .reset_index()
    )
    if grouped.empty:
        return "Not available"
    grouped = grouped[grouped["order_count"] >= max(1, int(grouped["order_count"].median() * 0.25))]
    if grouped.empty:
        return "Not available"
    row = grouped.sort_values("late_delivery_rate", ascending=False).iloc[0]
    return _label_or_not_available(row["order_region"])


def _records_from_grouped(
    df: pd.DataFrame,
    group_col: str,
    aggregations: Dict[str, tuple],
    label_name: str = "label",
    top: Optional[int] = None,
    sort_by: Optional[str] = None,
    ascending: bool = False,
) -> List[Dict[str, object]]:
    if group_col not in df.columns or df.empty:
        return []
    grouped = df.groupby(group_col, dropna=False).agg(**aggregations).reset_index()
    grouped = grouped.rename(columns={group_col: label_name})
    if sort_by and sort_by in grouped.columns:
        grouped = grouped.sort_values(sort_by, ascending=ascending)
    if top:
        grouped = grouped.head(top)
    return json.loads(grouped.replace({np.nan: None}).to_json(orient="records"))


def build_chart_datasets(df: pd.DataFrame) -> Dict[str, List[Dict[str, object]]]:
    monthly_df = df[df["order_year_month"] != "Unknown"].copy() if "order_year_month" in df.columns else pd.DataFrame()
    if not monthly_df.empty:
        monthly = (
            monthly_df.groupby("order_year_month", dropna=False)
            .agg(revenue=("revenue", "sum"), order_volume=("order_id_clean", "nunique"))
            .reset_index()
            .rename(columns={"order_year_month": "label"})
            .sort_values("label")
        )
        monthly_revenue = json.loads(monthly.to_json(orient="records"))
    else:
        monthly_revenue = []

    category_revenue = _records_from_grouped(
        df,
        "product_category",
        {
            "revenue": ("revenue", "sum"),
            "profit": ("profit", "sum"),
            "order_volume": ("order_id_clean", "nunique"),
        },
        top=12,
        sort_by="revenue",
    )

    category_profit = _records_from_grouped(
        df,
        "product_category",
        {"profit": ("profit", "sum"), "revenue": ("revenue", "sum")},
        top=12,
        sort_by="profit",
    )

    region_late_delivery = _records_from_grouped(
        df,
        "order_region",
        {
            "late_delivery_rate": ("late_delivery_flag", lambda values: float(values.mean() * 100)),
            "order_volume": ("order_id_clean", "nunique"),
            "average_delay": ("delivery_delay", "mean"),
        },
        top=12,
        sort_by="late_delivery_rate",
    )

    revenue_by_region = _records_from_grouped(
        df,
        "order_region",
        {"revenue": ("revenue", "sum"), "order_volume": ("order_id_clean", "nunique")},
        top=12,
        sort_by="revenue",
    )

    revenue_by_country = _records_from_grouped(
        df,
        "order_country",
        {"revenue": ("revenue", "sum"), "order_volume": ("order_id_clean", "nunique")},
        top=10,
        sort_by="revenue",
    )

    shipping_mode_performance = _records_from_grouped(
        df,
        "shipping_mode",
        {
            "order_volume": ("order_id_clean", "nunique"),
            "revenue": ("revenue", "sum"),
            "late_delivery_rate": ("late_delivery_flag", lambda values: float(values.mean() * 100)),
            "average_delay": ("delivery_delay", "mean"),
        },
        sort_by="order_volume",
    )

    order_status_distribution = _records_from_grouped(
        df,
        "order_status",
        {"order_volume": ("order_id_clean", "nunique"), "revenue": ("revenue", "sum")},
        sort_by="order_volume",
    )

    customer_segment_performance = _records_from_grouped(
        df,
        "customer_segment",
        {
            "order_volume": ("order_id_clean", "nunique"),
            "revenue": ("revenue", "sum"),
            "profit": ("profit", "sum"),
            "late_delivery_rate": ("late_delivery_flag", lambda values: float(values.mean() * 100)),
        },
        sort_by="revenue",
    )

    return {
        "monthly_revenue_trend": monthly_revenue,
        "monthly_order_volume": monthly_revenue,
        "revenue_by_product_category": category_revenue,
        "profit_by_product_category": category_profit,
        "late_delivery_rate_by_region": region_late_delivery,
        "revenue_by_region": revenue_by_region,
        "revenue_by_country": revenue_by_country,
        "shipping_mode_performance": shipping_mode_performance,
        "order_status_distribution": order_status_distribution,
        "customer_segment_performance": customer_segment_performance,
    }


def calculate_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total_orders = int(df["order_id_clean"].nunique()) if "order_id_clean" in df.columns else int(len(df))
    total_revenue = _finite_float(df["revenue"].sum()) if "revenue" in df.columns else 0
    total_profit = _finite_float(df["profit"].sum()) if "profit" in df.columns else 0
    total_quantity = _finite_float(df["quantity"].sum()) if "quantity" in df.columns else 0
    average_profit_margin = _finite_float(df.loc[df["revenue"] > 0, "profit_margin"].mean() * 100) if "profit_margin" in df.columns else 0
    average_order_value = total_revenue / total_orders if total_orders else 0
    late_delivery_rate = _finite_float(df["late_delivery_flag"].mean() * 100) if "late_delivery_flag" in df.columns else 0
    average_delivery_delay = _finite_float(df["delivery_delay"].mean()) if "delivery_delay" in df.columns else 0

    return {
        "total_orders": total_orders,
        "total_revenue": _round(total_revenue),
        "total_profit": _round(total_profit),
        "average_profit_margin": _round(average_profit_margin),
        "total_quantity": _round(total_quantity),
        "average_order_value": _round(average_order_value),
        "late_delivery_rate": _round(late_delivery_rate),
        "average_delivery_delay": _round(average_delivery_delay),
        "best_region_by_revenue": _top_label_by_sum(df, "order_region", "revenue"),
        "worst_region_by_late_delivery_rate": _worst_region_by_late_rate(df),
        "top_product_by_revenue": _top_label_by_sum(df, "product_name", "revenue"),
        "top_category_by_revenue": _top_label_by_sum(df, "product_category", "revenue"),
        "top_shipping_mode_by_volume": _top_label_by_count(df, "shipping_mode"),
        "number_of_countries": int(df["order_country"].nunique()) if "order_country" in df.columns else 0,
        "number_of_product_categories": int(df["product_category"].nunique()) if "product_category" in df.columns else 0,
    }


def build_business_report(summary: Dict[str, object], context: Dict[str, object]) -> str:
    kpis = summary["kpis"]
    charts = summary["summary_datasets"]
    limitations = context.get("limitations") or ["No major calculation limitations were recorded."]

    top_categories = charts.get("revenue_by_product_category", [])[:5]
    top_regions = charts.get("revenue_by_region", [])[:5]
    shipping_modes = charts.get("shipping_mode_performance", [])[:5]
    monthly = charts.get("monthly_revenue_trend", [])
    latest_month = monthly[-1]["label"] if monthly else "Not available"
    earliest_month = monthly[0]["label"] if monthly else "Not available"

    recommendations = [
        f"Prioritize delivery-improvement analysis in {kpis['worst_region_by_late_delivery_rate']}, where late-delivery exposure is highest.",
        f"Protect and expand the strongest revenue category, {kpis['top_category_by_revenue']}, while monitoring margin quality.",
        f"Review capacity and carrier planning for {kpis['top_shipping_mode_by_volume']}, the highest-volume shipping mode.",
        "Use monthly demand patterns to plan inventory and fulfillment staffing before peak periods.",
        "Track late delivery, profit margin, and category revenue together so growth decisions do not hide operational risk.",
    ]

    report = [
        "# Supply Chain Operations Business Report",
        "",
        "## Executive summary",
        (
            f"The cleaned dataset contains {kpis['total_orders']:,} orders with total revenue of "
            f"{_format_money(kpis['total_revenue'])}. The best revenue region is "
            f"{kpis['best_region_by_revenue']}, and the top revenue category is "
            f"{kpis['top_category_by_revenue']}. The overall late delivery rate is "
            f"{_format_percent(kpis['late_delivery_rate'])}, which makes fulfillment reliability a key operational focus."
        ),
        "",
        "## Data overview",
        f"- Source file: {context.get('source_file', 'Not available')}",
        f"- Original rows: {context.get('original_row_count', 0):,}",
        f"- Cleaned rows: {context.get('cleaned_row_count', 0):,}",
        f"- Duplicate rows removed: {context.get('duplicates_removed', 0):,}",
        f"- Invalid order rows removed: {context.get('invalid_order_rows_removed', 0):,}",
        f"- Monthly coverage: {earliest_month} to {latest_month}",
        "",
        "## KPI summary",
        f"- Total orders: {kpis['total_orders']:,}",
        f"- Total revenue: {_format_money(kpis['total_revenue'])}",
        f"- Total profit: {_format_money(kpis['total_profit'])}",
        f"- Average profit margin: {_format_percent(kpis['average_profit_margin'])}",
        f"- Average order value: {_format_money(kpis['average_order_value'])}",
        f"- Late delivery rate: {_format_percent(kpis['late_delivery_rate'])}",
        f"- Average delivery delay: {_round(kpis['average_delivery_delay'])} days",
        f"- Countries represented: {kpis['number_of_countries']}",
        f"- Product categories represented: {kpis['number_of_product_categories']}",
        "",
        "## Revenue insights",
        f"The strongest revenue region is {kpis['best_region_by_revenue']}. "
        f"The top product by revenue is {kpis['top_product_by_revenue']}. "
        "Monthly revenue trends are available in the dashboard for seasonality and demand planning.",
        "",
        "## Delivery performance insights",
        f"The late delivery rate is {_format_percent(kpis['late_delivery_rate'])}, and the average delivery delay is "
        f"{_round(kpis['average_delivery_delay'])} days. The region with the highest late delivery rate is "
        f"{kpis['worst_region_by_late_delivery_rate']}.",
        "",
        "## Region insights",
    ]

    if top_regions:
        for row in top_regions:
            report.append(f"- {row['label']}: {_format_money(row.get('revenue', 0))} revenue")
    else:
        report.append("- Region revenue was not available.")

    report.extend(["", "## Product/category insights"])
    if top_categories:
        for row in top_categories:
            report.append(
                f"- {row['label']}: {_format_money(row.get('revenue', 0))} revenue and "
                f"{_format_money(row.get('profit', 0))} profit"
            )
    else:
        report.append("- Product category revenue was not available.")

    report.extend(["", "## Shipping mode insights"])
    if shipping_modes:
        for row in shipping_modes:
            report.append(
                f"- {row['label']}: {int(row.get('order_volume') or 0):,} orders, "
                f"{_format_percent(row.get('late_delivery_rate', 0))} late delivery rate"
            )
    else:
        report.append("- Shipping mode performance was not available.")

    report.extend(
        [
            "",
            "## Operational risks",
            "- Late deliveries can reduce customer satisfaction and increase service recovery costs.",
            "- High revenue concentration in a small number of categories or regions can increase planning risk.",
            "- Profit margin should be monitored alongside revenue because sales volume alone can hide weak economics.",
            "- Missing or inconsistent source columns may limit metric precision until data governance improves.",
            "",
            "## Business recommendations",
        ]
    )
    report.extend(f"{index}. {recommendation}" for index, recommendation in enumerate(recommendations, start=1))

    report.extend(["", "## Data limitations"])
    report.extend(f"- {limitation}" for limitation in limitations)

    return "\n".join(report) + "\n"


def _read_description_file(description_csv_path: Optional[Path]) -> str:
    if not description_csv_path:
        return "No dataset description file was detected."
    path = Path(description_csv_path)
    if not path.exists():
        return "The detected dataset description file was not found on disk."
    try:
        df = pd.read_csv(path, nrows=200, encoding="latin1", low_memory=False)
        return df.to_string(index=False)
    except Exception as exc:
        return f"Could not read dataset description file: {exc}"


def write_rag_documents(
    summary: Dict[str, object],
    report_text: str,
    context: Dict[str, object],
    description_csv_path: Optional[Path],
) -> Dict[str, str]:
    RAG_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    kpis = summary["kpis"]

    kpi_lines = ["Supply Chain KPI Summary", ""]
    for key, value in kpis.items():
        kpi_lines.append(f"{key.replace('_', ' ').title()}: {value}")
    kpi_lines.extend(["", "Calculation sources:"])
    for key, value in context.get("calculation_sources", {}).items():
        kpi_lines.append(f"- {key}: {value}")

    dictionary_lines = [
        "Dataset Dictionary and Column Mapping",
        "",
        "Detected source columns:",
    ]
    for original, normalized in context.get("column_mapping", {}).items():
        dictionary_lines.append(f"- {original} -> {normalized}")
    dictionary_lines.extend(["", "Dataset description file content:", _read_description_file(description_csv_path)])

    experiment_notes = "\n".join(
        [
            "Experiment Tracking Notes",
            "",
            "This local module lets a researcher define a control condition and a treatment condition,",
            "record participant decisions, confidence scores, response times, and notes, then export",
            "responses as CSV for later analysis. It is intended for lightweight supply-chain decision",
            "support studies, such as testing whether KPI dashboards change operational decisions.",
        ]
    )

    documents = {
        "kpi_summary.txt": "\n".join(kpi_lines) + "\n",
        "dataset_dictionary.txt": "\n".join(dictionary_lines) + "\n",
        "operational_insights.txt": report_text,
        "experiment_notes.txt": experiment_notes + "\n",
    }

    written_paths = {}
    for file_name, content in documents.items():
        path = RAG_DOCUMENTS_DIR / file_name
        path.write_text(content, encoding="utf-8")
        written_paths[file_name] = str(path)

    return written_paths


def generate_business_outputs(
    df: pd.DataFrame,
    context: Dict[str, object],
    description_csv_path: Optional[Path] = None,
) -> Dict[str, object]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RAG_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    kpis = calculate_kpis(df)
    chart_datasets = build_chart_datasets(df)
    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "kpis": kpis,
        "summary_datasets": chart_datasets,
        "data_context": context,
    }

    KPI_SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_text = build_business_report(summary, context)
    BUSINESS_REPORT_PATH.write_text(report_text, encoding="utf-8")
    rag_paths = write_rag_documents(summary, report_text, context, description_csv_path)

    summary["report_path"] = str(BUSINESS_REPORT_PATH)
    summary["rag_documents"] = rag_paths
    return summary
