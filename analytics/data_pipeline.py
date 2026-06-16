import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from django.conf import settings


DATASET_DIR = settings.BASE_DIR / "Dataset"
EXTRACTED_DIR = settings.BASE_DIR / "extracted_data"
OUTPUTS_DIR = settings.BASE_DIR / "outputs"
RAG_DOCUMENTS_DIR = OUTPUTS_DIR / "rag_documents"
CLEANED_DATA_PATH = OUTPUTS_DIR / "cleaned_supply_chain_data.csv"

CSV_ENCODINGS = ("utf-8", "utf-8-sig", "latin1", "ISO-8859-1")

MAIN_COLUMN_PATTERNS = [
    ("order", "id"),
    ("order", "date"),
    ("order", "country"),
    ("order", "region"),
    ("product", "name"),
    ("product", "price"),
    ("customer", "segment"),
    ("customer", "country"),
    ("sales",),
    ("profit",),
    ("delivery",),
    ("shipping", "mode"),
    ("category", "name"),
    ("quantity",),
    ("status",),
]


def ensure_project_directories() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    RAG_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def normalize_column_name(column_name: object) -> str:
    """Normalize messy CSV headers without losing their meaning."""
    text = str(column_name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unnamed_column"


def normalize_dataframe_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    used_names: Dict[str, int] = {}
    normalized_columns: List[str] = []
    mapping: Dict[str, str] = {}

    for original_name in df.columns:
        base_name = normalize_column_name(original_name)
        next_name = base_name
        if next_name in used_names:
            used_names[base_name] += 1
            next_name = f"{base_name}_{used_names[base_name]}"
        else:
            used_names[base_name] = 0
        normalized_columns.append(next_name)
        mapping[str(original_name)] = next_name

    df = df.copy()
    df.columns = normalized_columns
    return df, mapping


def find_zip_files() -> List[Path]:
    ensure_project_directories()
    return sorted(DATASET_DIR.glob("*.zip"), key=lambda path: path.stat().st_size, reverse=True)


def choose_largest_zip() -> Optional[Path]:
    zip_files = find_zip_files()
    return zip_files[0] if zip_files else None


def safe_extract_zip(zip_path: Path, target_dir: Path = EXTRACTED_DIR) -> None:
    """Extract a ZIP archive while preventing files from escaping target_dir."""
    ensure_project_directories()
    target_root = target_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_path = (target_dir / member.filename).resolve()
            if not str(member_path).startswith(str(target_root)):
                raise ValueError(f"Unsafe path found in ZIP archive: {member.filename}")
        archive.extractall(target_dir)


def read_csv_with_fallback(path: Path, **kwargs) -> pd.DataFrame:
    last_error: Optional[Exception] = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return pd.read_csv(path, low_memory=False, **kwargs)


def get_processing_row_limit() -> Optional[int]:
    """Limit cloud processing so small free instances do not run out of memory."""
    raw_value = os.getenv("PROCESSING_ROW_LIMIT", "").strip()
    if raw_value:
        try:
            parsed_value = int(raw_value)
            return parsed_value if parsed_value > 0 else None
        except ValueError:
            return 50000

    # Local development keeps full processing. Render/Neon deployments default to
    # a representative sample because the free web instance has limited memory.
    if os.getenv("DATABASE_URL") and not settings.DEBUG:
        return 50000
    return None


def get_csv_columns(path: Path) -> List[str]:
    sample = read_csv_with_fallback(path, nrows=25)
    return [str(column) for column in sample.columns]


def _pattern_score(columns: Sequence[str], patterns: Sequence[Tuple[str, ...]]) -> int:
    score = 0
    for pattern in patterns:
        if any(all(part in column for part in pattern) for column in columns):
            score += 3 if len(pattern) > 1 else 1
    return score


def detect_dataset_files(csv_paths: Iterable[Path]) -> Dict[str, object]:
    candidates = []
    for path in csv_paths:
        try:
            original_columns = get_csv_columns(path)
        except Exception as exc:
            candidates.append(
                {
                    "path": str(path),
                    "error": str(exc),
                    "main_score": 0,
                    "description_score": 0,
                    "access_log_score": 0,
                }
            )
            continue

        normalized_columns = [normalize_column_name(column) for column in original_columns]
        lower_name = path.name.lower()
        main_score = _pattern_score(normalized_columns, MAIN_COLUMN_PATTERNS)
        if "dataco" in lower_name or "supply" in lower_name:
            main_score += 6
        if "access" in lower_name or "log" in lower_name or "tokenized" in lower_name:
            main_score -= 8

        description_score = 0
        if any(word in lower_name for word in ("description", "dictionary", "metadata", "schema")):
            description_score += 10
        if any("description" in column or "definition" in column for column in normalized_columns):
            description_score += 4

        access_log_score = 0
        if any(word in lower_name for word in ("access", "log", "tokenized")):
            access_log_score += 10
        if any("url" in column or "ip" in column or "session" in column for column in normalized_columns):
            access_log_score += 3

        candidates.append(
            {
                "path": str(path),
                "name": path.name,
                "columns": original_columns,
                "normalized_columns": normalized_columns,
                "main_score": main_score,
                "description_score": description_score,
                "access_log_score": access_log_score,
            }
        )

    usable = [candidate for candidate in candidates if "error" not in candidate]
    main_candidates = [
        candidate
        for candidate in usable
        if candidate["main_score"] >= 8 and candidate["access_log_score"] < 10 and candidate["description_score"] < 10
    ]
    main_csv = max(main_candidates, key=lambda candidate: candidate["main_score"], default=None)

    description_csv = max(usable, key=lambda candidate: candidate["description_score"], default=None)
    if description_csv and description_csv["description_score"] <= 0:
        description_csv = None

    access_log_csv = max(usable, key=lambda candidate: candidate["access_log_score"], default=None)
    if access_log_csv and access_log_csv["access_log_score"] <= 0:
        access_log_csv = None

    return {
        "main_csv": main_csv["path"] if main_csv else None,
        "description_csv": description_csv["path"] if description_csv else None,
        "access_log_csv": access_log_csv["path"] if access_log_csv else None,
        "candidates": candidates,
    }


def extract_dataset() -> Dict[str, object]:
    ensure_project_directories()
    selected_zip = choose_largest_zip()
    messages: List[str] = []

    if not selected_zip:
        return {
            "status": "failed",
            "messages": [f"No ZIP files found in {DATASET_DIR}."],
            "zip_file": None,
            "main_csv": None,
            "description_csv": None,
            "access_log_csv": None,
            "candidates": [],
        }

    messages.append(f"Selected largest ZIP file: {selected_zip.name}")
    safe_extract_zip(selected_zip, EXTRACTED_DIR)
    messages.append(f"Extracted files into: {EXTRACTED_DIR}")

    csv_paths = sorted(EXTRACTED_DIR.rglob("*.csv"))
    if not csv_paths:
        messages.append("No CSV files were found after extraction.")
        return {
            "status": "failed",
            "messages": messages,
            "zip_file": str(selected_zip),
            "main_csv": None,
            "description_csv": None,
            "access_log_csv": None,
            "candidates": [],
        }

    detected = detect_dataset_files(csv_paths)
    messages.append(f"Detected {len(csv_paths)} CSV file(s).")
    if detected["main_csv"]:
        messages.append(f"Main supply-chain CSV: {detected['main_csv']}")
    else:
        messages.append("No usable main supply-chain CSV could be detected.")
    if detected["description_csv"]:
        messages.append(f"Dataset description CSV: {detected['description_csv']}")
    else:
        messages.append("Dataset description CSV: not found")
    if detected["access_log_csv"]:
        messages.append(f"Access log CSV: {detected['access_log_csv']}")
    else:
        messages.append("Access log CSV: not found")

    return {
        "status": "ok" if detected["main_csv"] else "failed",
        "messages": messages,
        "zip_file": str(selected_zip),
        **detected,
    }


def _best_column(
    columns: Sequence[str],
    exact_names: Sequence[str] = (),
    keyword_sets: Sequence[Tuple[str, ...]] = (),
    exclude_keywords: Sequence[str] = (),
) -> Optional[str]:
    column_set = set(columns)
    for name in exact_names:
        if name in column_set:
            return name

    best_name = None
    best_score = 0
    for column in columns:
        if any(excluded in column for excluded in exclude_keywords):
            continue
        score = 0
        for keywords in keyword_sets:
            if all(keyword in column for keyword in keywords):
                score += len(keywords) + 1
        if score > best_score:
            best_name = column
            best_score = score
    return best_name


def detect_business_columns(columns: Sequence[str]) -> Dict[str, Optional[str]]:
    return {
        "order_id": _best_column(columns, ["order_id"], [("order", "id")], ["item"]),
        "order_date": _best_column(columns, ["order_date_dateorders"], [("order", "date")], ["shipping"]),
        "shipping_date": _best_column(columns, ["shipping_date_dateorders"], [("shipping", "date")]),
        "actual_shipping_days": _best_column(
            columns,
            ["days_for_shipping_real"],
            [("days", "shipping", "real"), ("actual", "shipping", "days")],
        ),
        "scheduled_shipping_days": _best_column(
            columns,
            ["days_for_shipment_scheduled"],
            [("days", "shipment", "scheduled"), ("days", "shipping", "scheduled")],
        ),
        "late_delivery_risk": _best_column(columns, ["late_delivery_risk"], [("late", "delivery")]),
        "revenue": _best_column(
            columns,
            ["sales", "order_item_total", "sales_per_customer"],
            [("sales",), ("order", "total"), ("revenue",)],
        ),
        "profit": _best_column(
            columns,
            ["order_profit_per_order", "benefit_per_order"],
            [("profit", "order"), ("benefit", "order"), ("profit",)],
        ),
        "quantity": _best_column(columns, ["order_item_quantity", "quantity"], [("quantity",)]),
        "product_price": _best_column(
            columns,
            ["order_item_product_price", "product_price"],
            [("product", "price"), ("item", "price")],
        ),
        "shipping_mode": _best_column(columns, ["shipping_mode"], [("shipping", "mode")]),
        "product_category": _best_column(columns, ["category_name"], [("category", "name"), ("category",)]),
        "product_name": _best_column(columns, ["product_name"], [("product", "name")]),
        "order_region": _best_column(columns, ["order_region", "market"], [("order", "region"), ("region",), ("market",)]),
        "order_country": _best_column(
            columns,
            ["order_country", "customer_country"],
            [("order", "country"), ("customer", "country"), ("country",)],
        ),
        "customer_segment": _best_column(columns, ["customer_segment"], [("customer", "segment"), ("segment",)]),
        "order_status": _best_column(columns, ["order_status"], [("order", "status"), ("status",)]),
    }


def _numeric_series(df: pd.DataFrame, column: Optional[str]) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series(0.0, index=df.index)
    series = df[column]
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = series.astype(str).str.replace(",", "", regex=False)
    cleaned = cleaned.str.replace(r"[^0-9.\-]", "", regex=True)
    cleaned = cleaned.replace("", np.nan)
    return pd.to_numeric(cleaned, errors="coerce")


def _clean_text_series(df: pd.DataFrame, column: Optional[str], default: str = "Unknown") -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series(default, index=df.index)
    series = df[column].fillna(default).astype(str).str.strip()
    return series.replace({"": default, "nan": default, "None": default})


def _datetime_series(df: pd.DataFrame, column: Optional[str]) -> pd.Series:
    if not column or column not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    return pd.to_datetime(df[column], errors="coerce")


def _late_flag_from_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() > 0:
        return numeric.fillna(0).astype(float) > 0
    lowered = series.fillna("").astype(str).str.lower()
    return lowered.str.contains("late|yes|true|risk|1", regex=True)


def clean_supply_chain_data(main_csv_path: Path) -> Tuple[pd.DataFrame, Dict[str, object]]:
    ensure_project_directories()
    main_csv_path = Path(main_csv_path)
    processing_row_limit = get_processing_row_limit()
    read_kwargs = {"nrows": processing_row_limit} if processing_row_limit else {}
    raw_df = read_csv_with_fallback(main_csv_path, **read_kwargs)
    original_row_count = len(raw_df)

    df, column_mapping = normalize_dataframe_columns(raw_df)
    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    detected_columns = detect_business_columns(list(df.columns))
    limitations: List[str] = []
    if processing_row_limit:
        limitations.append(
            f"Cloud-safe processing analyzed the first {original_row_count:,} rows to stay within free deployment memory limits. "
            "Run locally for full-dataset processing."
        )

    order_id_column = detected_columns["order_id"]
    if order_id_column and order_id_column in df.columns:
        valid_order_id = df[order_id_column].notna() & (df[order_id_column].astype(str).str.strip() != "")
        invalid_count = int((~valid_order_id).sum())
        df = df.loc[valid_order_id].copy()
        df["order_id_clean"] = df[order_id_column].astype(str).str.strip()
    else:
        invalid_count = 0
        df["order_id_clean"] = [f"row_{index}" for index in range(1, len(df) + 1)]
        limitations.append("A reliable order ID column was not detected; row-level IDs were generated for counting.")

    # Fill descriptive fields, but keep numeric handling explicit for calculated metrics.
    for column in df.select_dtypes(include=["object"]).columns:
        df[column] = df[column].fillna("Unknown").replace({"": "Unknown"})

    order_date = _datetime_series(df, detected_columns["order_date"])
    shipping_date = _datetime_series(df, detected_columns["shipping_date"])
    df["order_date_clean"] = order_date
    df["shipping_date_clean"] = shipping_date

    quantity = _numeric_series(df, detected_columns["quantity"]).fillna(0)
    product_price = _numeric_series(df, detected_columns["product_price"]).fillna(0)
    df["quantity"] = quantity

    if detected_columns["revenue"]:
        df["revenue"] = _numeric_series(df, detected_columns["revenue"]).fillna(0)
        revenue_source = detected_columns["revenue"]
    elif detected_columns["quantity"] and detected_columns["product_price"]:
        df["revenue"] = quantity * product_price
        revenue_source = "quantity_x_product_price"
    else:
        df["revenue"] = 0.0
        revenue_source = "not_available"
        limitations.append("Revenue could not be calculated because neither sales/order total nor quantity plus price was available.")

    if detected_columns["profit"]:
        df["profit"] = _numeric_series(df, detected_columns["profit"]).fillna(0)
        profit_source = detected_columns["profit"]
    else:
        df["profit"] = 0.0
        profit_source = "not_available"
        limitations.append("Profit was not detected in the dataset, so profit values were set to 0 for local analysis.")

    df["profit_margin"] = np.where(df["revenue"] > 0, df["profit"] / df["revenue"], 0)

    if detected_columns["actual_shipping_days"]:
        df["actual_shipping_days"] = _numeric_series(df, detected_columns["actual_shipping_days"]).fillna(0)
        actual_shipping_source = detected_columns["actual_shipping_days"]
    elif order_date.notna().any() and shipping_date.notna().any():
        df["actual_shipping_days"] = (shipping_date - order_date).dt.days.fillna(0)
        actual_shipping_source = "shipping_date_minus_order_date"
    else:
        df["actual_shipping_days"] = 0.0
        actual_shipping_source = "not_available"
        limitations.append("Actual shipping days could not be calculated from available columns.")

    if detected_columns["scheduled_shipping_days"]:
        df["scheduled_shipping_days"] = _numeric_series(df, detected_columns["scheduled_shipping_days"]).fillna(0)
        scheduled_shipping_source = detected_columns["scheduled_shipping_days"]
    else:
        df["scheduled_shipping_days"] = 0.0
        scheduled_shipping_source = "not_available"
        limitations.append("Scheduled shipping days were not detected; delivery delay uses 0 as the local fallback.")

    df["delivery_delay"] = df["actual_shipping_days"] - df["scheduled_shipping_days"]

    if detected_columns["late_delivery_risk"]:
        df["late_delivery_flag"] = _late_flag_from_series(df[detected_columns["late_delivery_risk"]])
        late_delivery_source = detected_columns["late_delivery_risk"]
    elif "delivery_delay" in df.columns:
        df["late_delivery_flag"] = df["delivery_delay"] > 0
        late_delivery_source = "delivery_delay_greater_than_zero"
    else:
        df["late_delivery_flag"] = False
        late_delivery_source = "not_available"
        limitations.append("Late delivery could not be detected; late delivery flags were set to False.")

    df["order_month"] = order_date.dt.month.fillna(0).astype(int)
    df["order_year"] = order_date.dt.year.fillna(0).astype(int)
    df["order_year_month"] = order_date.dt.strftime("%Y-%m").fillna("Unknown")
    df["shipping_mode"] = _clean_text_series(df, detected_columns["shipping_mode"])
    df["product_category"] = _clean_text_series(df, detected_columns["product_category"])
    df["product_name"] = _clean_text_series(df, detected_columns["product_name"])
    df["order_region"] = _clean_text_series(df, detected_columns["order_region"])
    df["order_country"] = _clean_text_series(df, detected_columns["order_country"])
    df["customer_segment"] = _clean_text_series(df, detected_columns["customer_segment"])
    df["order_status"] = _clean_text_series(df, detected_columns["order_status"])

    df.to_csv(CLEANED_DATA_PATH, index=False)

    context = {
        "source_file": str(main_csv_path),
        "cleaned_data_path": str(CLEANED_DATA_PATH),
        "original_row_count": original_row_count,
        "cleaned_row_count": len(df),
        "duplicates_removed": duplicate_count,
        "invalid_order_rows_removed": invalid_count,
        "column_mapping": column_mapping,
        "detected_columns": detected_columns,
        "calculation_sources": {
            "revenue": revenue_source,
            "profit": profit_source,
            "actual_shipping_days": actual_shipping_source,
            "scheduled_shipping_days": scheduled_shipping_source,
            "late_delivery_flag": late_delivery_source,
        },
        "limitations": limitations,
        "processed_at": datetime.utcnow().isoformat() + "Z",
        "processing_row_limit": processing_row_limit,
    }

    with (OUTPUTS_DIR / "pipeline_context.json").open("w", encoding="utf-8") as file:
        json.dump(context, file, indent=2)

    return df, context
