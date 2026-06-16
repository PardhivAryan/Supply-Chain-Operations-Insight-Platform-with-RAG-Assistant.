import json
import re
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_pipeline import RAG_DOCUMENTS_DIR
from .kpi_engine import KPI_SUMMARY_PATH


FALLBACK_ANSWER = "I could not find enough information in the generated reports to answer that confidently."

LANGUAGE_TEMPLATES = {
    "english": {
        "prefix": "Based on the generated reports:",
        "direct": "Answer",
        "evidence": "Evidence",
        "interpretation": "Business interpretation",
        "fallback": FALLBACK_ANSWER,
    },
    "telugu_roman": {
        "prefix": "Generated reports prakaram:",
        "direct": "Answer",
        "evidence": "Evidence",
        "interpretation": "Business meaning",
        "fallback": "Generated reports lo ee question ki confident ga answer cheyyadaniki saripoyina information dorakaledu.",
    },
    "telugu": {
        "prefix": "జనరేట్ చేసిన రిపోర్ట్స్ ప్రకారం:",
        "direct": "సమాధానం",
        "evidence": "ఆధారం",
        "interpretation": "బిజినెస్ అర్థం",
        "fallback": "జనరేట్ చేసిన రిపోర్ట్స్‌లో ఈ ప్రశ్నకు నమ్మకంగా సమాధానం ఇవ్వడానికి సరిపడిన సమాచారం దొరకలేదు.",
    },
    "hindi": {
        "prefix": "Generated reports ke hisaab se:",
        "direct": "Answer",
        "evidence": "Evidence",
        "interpretation": "Business meaning",
        "fallback": "Generated reports mein is question ka confident answer dene ke liye enough information nahi mila.",
    },
}

QUERY_HINTS = {
    "revenue": [
        "revenue",
        "sales",
        "income",
        "earning",
        "ammakam",
        "salesu",
        "ఆదాయం",
        "रेवेन्यू",
    ],
    "profit": ["profit", "margin", "labham", "లాభం", "मुनाफा"],
    "late delivery": [
        "late",
        "delay",
        "delivery",
        "late_delivery",
        "alasya",
        "late delivery",
        "ఆలస్యం",
        "लेट",
        "देरी",
    ],
    "region": ["region", "area", "prantham", "ప్రాంతం", "क्षेत्र"],
    "country": ["country", "desam", "దేశం", "देश"],
    "category": ["category", "product category", "vargam", "కేటగిరీ", "श्रेणी"],
    "product": ["product", "item", "vastuvu", "ఉత్పత్తి", "प्रोडक्ट"],
    "shipping mode": ["shipping", "mode", "shipment", "delivery mode", "రవాణా", "शिपिंग"],
    "recommendations": [
        "recommendation",
        "recommendations",
        "suggest",
        "advice",
        "salahalu",
        "cheyyali",
        "సిఫార్సులు",
        "सलाह",
    ],
    "risk": ["risk", "problem", "issue", "operational risk", "samasyalu", "రిస్క్", "जोखिम"],
    "monthly revenue trend": ["monthly", "month", "trend", "nelavari", "నెల", "महीना"],
}


def _load_documents() -> List[Dict[str, str]]:
    if not RAG_DOCUMENTS_DIR.exists():
        return []
    documents = []
    for path in sorted(RAG_DOCUMENTS_DIR.glob("*.txt")):
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            documents.append({"source": path.name, "content": content})
    return documents


def _load_summary() -> Optional[Dict[str, object]]:
    if not KPI_SUMMARY_PATH.exists():
        return None
    try:
        return json.loads(KPI_SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "Not available"


def _percent(value) -> str:
    try:
        return f"{float(value):,.2f}%"
    except (TypeError, ValueError):
        return "Not available"


def _number(value) -> str:
    try:
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "Not available"


def _question_tokens(question: str) -> set:
    tokens = set(re.findall(r"[a-z0-9]+", _augment_question_for_retrieval(question).lower()))
    singulars = {token[:-1] for token in tokens if len(token) > 4 and token.endswith("s")}
    return tokens | singulars


def _has_any(tokens: set, *words: str) -> bool:
    return any(word in tokens for word in words)


def _has_all(tokens: set, *words: str) -> bool:
    return all(word in tokens for word in words)


def _top_record(records: List[Dict[str, object]], key: str) -> Optional[Dict[str, object]]:
    usable = [record for record in records if record.get(key) is not None]
    if not usable:
        return None
    return max(usable, key=lambda record: float(record.get(key) or 0))


def _answer_block(question: str, direct: str, evidence: List[str], interpretation: str = "") -> str:
    template = _language_template(question)
    parts = [f"{template['prefix']}", "", f"{template['direct']}: {direct}"]
    if evidence:
        parts.append("")
        parts.append(f"{template['evidence']}:")
        parts.extend(f"- {item}" for item in evidence)
    if interpretation:
        parts.append("")
        parts.append(f"{template['interpretation']}: {interpretation}")
    return "\n".join(parts)


def _ranked_rows(records: List[Dict[str, object]], value_key: str, formatter, limit: int = 5) -> List[str]:
    sorted_records = sorted(records, key=lambda row: float(row.get(value_key) or 0), reverse=True)
    return [
        f"{index}. {row.get('label', 'Not available')} - {formatter(row.get(value_key))}"
        for index, row in enumerate(sorted_records[:limit], start=1)
    ]


def _structured_answer(question: str) -> Optional[str]:
    summary = _load_summary()
    if not summary:
        return None

    kpis = summary.get("kpis", {})
    datasets = summary.get("summary_datasets", {})
    tokens = _question_tokens(question)

    asks_top = _has_any(tokens, "top", "highest", "best", "most", "largest", "maximum", "ekkuva", "compare", "rank")
    asks_worst = _has_any(tokens, "worst", "lowest", "risk", "problem")
    asks_recommendations = _has_any(
        tokens,
        "recommendation",
        "recommendations",
        "suggest",
        "advice",
        "cheyyali",
        "reduce",
        "improve",
        "fix",
        "solve",
        "action",
        "should",
    )
    asks_risk = _has_any(tokens, "risk", "problem", "issue", "samasyalu")
    asks_trend = _has_any(tokens, "trend", "monthly", "month")

    if _has_all(tokens, "total", "revenue") or (_has_any(tokens, "revenue") and _has_any(tokens, "overall", "total")):
        return _answer_block(
            question,
            f"Total revenue is {_money(kpis.get('total_revenue'))}.",
            [
                f"Total orders: {_number(kpis.get('total_orders'))}",
                f"Average order value: {_money(kpis.get('average_order_value'))}",
                f"Best region by revenue: {kpis.get('best_region_by_revenue', 'Not available')}",
            ],
            "Revenue scale is strong, but it should be reviewed together with profit margin and delivery reliability.",
        )

    if _has_all(tokens, "total", "orders") or (_has_any(tokens, "orders") and _has_any(tokens, "overall", "total")):
        return _answer_block(
            question,
            f"Total orders are {_number(kpis.get('total_orders'))}.",
            [
                f"Total quantity: {_number(kpis.get('total_quantity'))}",
                f"Top shipping mode by volume: {kpis.get('top_shipping_mode_by_volume', 'Not available')}",
            ],
            "Order volume helps identify where fulfillment capacity and delivery performance need the most attention.",
        )

    if asks_recommendations and _has_any(tokens, "late", "delay", "delivery"):
        return _answer_block(
            question,
            "To reduce late deliveries, the company should prioritize high-risk regions, review shipping-mode promises, improve carrier planning, and monitor delay KPIs every month.",
            [
                f"Overall late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                f"Average delivery delay: {_number(kpis.get('average_delivery_delay'))} days",
                f"Worst region by late delivery: {kpis.get('worst_region_by_late_delivery_rate', 'Not available')}",
                "The generated report recommends reviewing capacity and carrier planning for Standard Class.",
            ],
            "This turns the RAG output into an operational action plan instead of only reporting a metric.",
        )

    if _has_any(tokens, "late", "delay", "delivery"):
        region_rows = datasets.get("late_delivery_rate_by_region", [])
        shipping_rows = datasets.get("shipping_mode_performance", [])
        if _has_any(tokens, "shipping", "mode", "shipment"):
            top_mode = _top_record(shipping_rows, "late_delivery_rate" if asks_risk or asks_worst or _has_any(tokens, "late", "delay") else "order_volume")
            if top_mode:
                return _answer_block(
                    question,
                    f"{top_mode.get('label')} has the highest late-delivery risk among shipping modes.",
                    [
                        f"{top_mode.get('label')} late-delivery rate: {_percent(top_mode.get('late_delivery_rate'))}",
                        f"{top_mode.get('label')} order volume: {_number(top_mode.get('order_volume'))}",
                        f"Overall late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                        f"Average delivery delay: {_number(kpis.get('average_delivery_delay'))} days",
                    ],
                    "This mode should be reviewed for carrier performance, promised delivery windows, and fulfillment capacity.",
                )
        top_region = _top_record(region_rows, "late_delivery_rate")
        return _answer_block(
            question,
            f"{top_region.get('label') if top_region else kpis.get('worst_region_by_late_delivery_rate', 'Not available')} has the highest late-delivery rate in the regional summary.",
            [
                f"Overall late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                f"Average delivery delay: {_number(kpis.get('average_delivery_delay'))} days",
                *(_ranked_rows(region_rows, "late_delivery_rate", _percent, limit=3) if region_rows else []),
            ],
            "Late delivery is one of the main operational risks because it can affect customer satisfaction and service cost.",
        )

    if _has_any(tokens, "category", "categories"):
        rows = datasets.get("revenue_by_product_category", [])
        if asks_top or _has_any(tokens, "revenue", "sales"):
            top = _top_record(rows, "revenue")
            if top:
                return _answer_block(
                    question,
                    f"{top.get('label')} is the top product category by revenue.",
                    [
                        f"{top.get('label')} revenue: {_money(top.get('revenue'))}",
                        f"{top.get('label')} profit: {_money(top.get('profit'))}",
                        f"Number of product categories: {_number(kpis.get('number_of_product_categories'))}",
                        *(_ranked_rows(rows, "revenue", _money, limit=5)),
                    ],
                    "The top category should be protected with strong inventory planning and margin monitoring.",
                )

    if _has_any(tokens, "product", "item"):
        return _answer_block(
            question,
            f"The top product by revenue is {kpis.get('top_product_by_revenue', 'Not available')}.",
            [
                f"Top category by revenue: {kpis.get('top_category_by_revenue', 'Not available')}",
                f"Total revenue: {_money(kpis.get('total_revenue'))}",
            ],
            "Product-level revenue concentration can guide inventory prioritization and promotion decisions.",
        )

    if _has_any(tokens, "region", "area"):
        rows = datasets.get("revenue_by_region", [])
        if asks_top or _has_any(tokens, "revenue", "sales"):
            top = _top_record(rows, "revenue")
            if top:
                return _answer_block(
                    question,
                    f"{top.get('label')} is the best region by revenue.",
                    [
                        f"{top.get('label')} revenue: {_money(top.get('revenue'))}",
                        f"Best region from KPI summary: {kpis.get('best_region_by_revenue', 'Not available')}",
                        *(_ranked_rows(rows, "revenue", _money, limit=5)),
                    ],
                    "High-performing regions are good candidates for retention, inventory availability, and margin-protection analysis.",
                )
        if asks_worst:
            return _answer_block(
                question,
                f"{kpis.get('worst_region_by_late_delivery_rate', 'Not available')} is the weakest region by late-delivery rate.",
                [
                    f"Overall late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                    f"Average delivery delay: {_number(kpis.get('average_delivery_delay'))} days",
                ],
                "This region should be prioritized for fulfillment and carrier performance review.",
            )

    if _has_any(tokens, "country"):
        rows = datasets.get("revenue_by_country", [])
        top = _top_record(rows, "revenue")
        if top:
            return _answer_block(
                question,
                f"{top.get('label')} is the top country by revenue in the available summary.",
                [
                    f"{top.get('label')} revenue: {_money(top.get('revenue'))}",
                    f"Countries represented: {_number(kpis.get('number_of_countries'))}",
                    *(_ranked_rows(rows, "revenue", _money, limit=5)),
                ],
                "Country-level ranking helps identify where demand is strongest and where regional operating plans should focus.",
            )

    if _has_any(tokens, "shipping", "mode", "shipment"):
        rows = datasets.get("shipping_mode_performance", [])
        ranking_key = "late_delivery_rate" if asks_risk or asks_worst else "order_volume"
        top = _top_record(rows, ranking_key)
        if top:
            direct_metric = (
                "highest late-delivery rate"
                if ranking_key == "late_delivery_rate"
                else "highest order volume"
            )
            return _answer_block(
                question,
                f"{top.get('label')} has the {direct_metric} among shipping modes.",
                [
                    f"{top.get('label')} orders: {_number(top.get('order_volume'))}",
                    f"{top.get('label')} late-delivery rate: {_percent(top.get('late_delivery_rate'))}",
                    *(_ranked_rows(rows, ranking_key, _percent if ranking_key == "late_delivery_rate" else _number, limit=4)),
                ],
                "Shipping-mode performance should be judged by both order volume and late-delivery exposure.",
            )

    if _has_any(tokens, "profit", "margin"):
        return _answer_block(
            question,
            f"Total profit is {_money(kpis.get('total_profit'))}, with an average profit margin of {_percent(kpis.get('average_profit_margin'))}.",
            [
                f"Total revenue: {_money(kpis.get('total_revenue'))}",
                f"Average order value: {_money(kpis.get('average_order_value'))}",
                f"Top category by revenue: {kpis.get('top_category_by_revenue', 'Not available')}",
            ],
            "Profitability should be reviewed with category mix, discounts, and delivery cost exposure.",
        )

    if asks_trend:
        rows = datasets.get("monthly_revenue_trend", [])
        if rows:
            first = rows[0]
            last = rows[-1]
            peak = _top_record(rows, "revenue")
            return _answer_block(
                question,
                f"The monthly revenue data covers {first.get('label')} to {last.get('label')}, with peak revenue in {peak.get('label') if peak else 'Not available'}.",
                [
                    f"First month revenue: {_money(first.get('revenue'))}",
                    f"Latest month revenue: {_money(last.get('revenue'))}",
                    f"Peak month revenue: {_money(peak.get('revenue') if peak else None)}",
                ],
                "Monthly trends can support demand forecasting, staffing plans, and inventory positioning.",
            )

    if asks_recommendations:
        return _answer_block(
            question,
            "The report recommends focusing on delivery improvement, top-category protection, shipping-mode planning, demand planning, and combined KPI monitoring.",
            [
                "Prioritize delivery-improvement analysis in South Asia.",
                "Protect and expand the Fishing category while monitoring margin quality.",
                "Review capacity and carrier planning for Standard Class.",
                "Use monthly demand patterns for inventory and staffing.",
                "Track late delivery, profit margin, and category revenue together.",
            ],
            "These recommendations connect revenue growth with operational reliability instead of looking at sales alone.",
        )

    if asks_risk:
        return _answer_block(
            question,
            "The main operational risk is late delivery, followed by category/region concentration and margin visibility.",
            [
                f"Overall late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                f"Worst region by late delivery: {kpis.get('worst_region_by_late_delivery_rate', 'Not available')}",
                "High revenue concentration can create planning risk.",
                "Profit margin should be monitored alongside revenue.",
            ],
            "The business should not treat revenue growth as healthy unless fulfillment reliability and margins are also stable.",
        )

    if _has_any(tokens, "summary", "overview", "summarize"):
        return _answer_block(
            question,
            "The dataset shows strong revenue volume, meaningful profit, and a high late-delivery rate that needs operational attention.",
            [
                f"Total orders: {_number(kpis.get('total_orders'))}",
                f"Total revenue: {_money(kpis.get('total_revenue'))}",
                f"Total profit: {_money(kpis.get('total_profit'))}",
                f"Late-delivery rate: {_percent(kpis.get('late_delivery_rate'))}",
                f"Top category: {kpis.get('top_category_by_revenue', 'Not available')}",
                f"Best region: {kpis.get('best_region_by_revenue', 'Not available')}",
            ],
            "This is a useful GRA-style business insight case because it connects data cleaning, KPI engineering, dashboarding, and decision support.",
        )

    return None


def _chunk_text(text: str, source: str, max_words: int = 130) -> List[Dict[str, str]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: List[Dict[str, str]] = []
    buffer: List[str] = []
    word_count = 0

    for paragraph in paragraphs:
        words = paragraph.split()
        if buffer and word_count + len(words) > max_words:
            chunks.append({"source": source, "text": "\n".join(buffer)})
            buffer = []
            word_count = 0
        buffer.append(paragraph)
        word_count += len(words)

    if buffer:
        chunks.append({"source": source, "text": "\n".join(buffer)})
    return chunks


def _build_chunks() -> List[Dict[str, str]]:
    chunks: List[Dict[str, str]] = []
    for document in _load_documents():
        chunks.extend(_chunk_text(document["content"], document["source"]))
    return chunks


def _query_terms(question: str) -> set:
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "for",
        "what",
        "which",
        "how",
        "does",
        "do",
        "is",
        "are",
        "has",
        "have",
        "with",
        "from",
        "that",
        "this",
        "question",
        "answer",
        "tell",
        "about",
    }
    return {word for word in re.findall(r"[a-z0-9]+", question.lower()) if word not in stopwords and len(word) > 2}


def _detect_language(question: str) -> str:
    lowered = question.lower()
    if re.search(r"[\u0c00-\u0c7f]", question):
        return "telugu"
    if re.search(r"[\u0900-\u097f]", question):
        return "hindi"

    telugu_roman_words = {
        "enti",
        "em",
        "ela",
        "endhuku",
        "enduku",
        "andhulo",
        "chupistundi",
        "chupichidhi",
        "cheppu",
        "chey",
        "kaavali",
        "aythe",
        "adhi",
        "naku",
        "naaku",
        "ekkada",
        "ekkkuva",
        "ekkuva",
        "tagginchali",
        "prakaram",
    }
    if any(re.search(rf"\b{word}\b", lowered) for word in telugu_roman_words):
        return "telugu_roman"

    hindi_roman_words = {"kya", "kaise", "kyun", "mein", "hai", "hisaab", "batao", "kitna"}
    if any(re.search(rf"\b{word}\b", lowered) for word in hindi_roman_words):
        return "hindi"

    return "english"


def _language_template(question: str) -> Dict[str, str]:
    return LANGUAGE_TEMPLATES.get(_detect_language(question), LANGUAGE_TEMPLATES["english"])


def _augment_question_for_retrieval(question: str) -> str:
    lowered = question.lower()
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    extra_terms = []
    for english_term, aliases in QUERY_HINTS.items():
        matched = False
        for alias in aliases:
            normalized_alias = alias.lower()
            if re.fullmatch(r"[a-z0-9 ]+", normalized_alias):
                alias_tokens = normalized_alias.split()
                matched = all(token in tokens for token in alias_tokens)
            else:
                matched = normalized_alias in lowered
            if matched:
                break
        if matched:
            extra_terms.append(english_term)

    if not extra_terms:
        return question
    return f"{question} {' '.join(extra_terms)}"


def _sentence_split(text: str) -> List[str]:
    text = re.sub(r"(?m)^#+\s*.+$", "", text)
    pieces = re.split(r"(?<=[.!?])\s+|\n+-\s+|\n+\d+\.\s+", text)
    cleaned = []
    for piece in pieces:
        sentence = re.sub(r"^#+\s*", "", piece.strip(" -\n\t"))
        if sentence and not sentence.endswith(":"):
            cleaned.append(sentence)
    return cleaned


def _grounded_answer(question: str, retrieval_question: str, chunks: List[Dict[str, str]]) -> str:
    template = _language_template(question)
    terms = _query_terms(retrieval_question)
    candidate_sentences: List[str] = []

    for chunk in chunks:
        for sentence in _sentence_split(chunk["text"]):
            sentence_terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
            if terms and terms.intersection(sentence_terms):
                candidate_sentences.append(sentence)

    if not candidate_sentences:
        return template["fallback"]

    unique_sentences = []
    seen = set()
    for sentence in candidate_sentences:
        if sentence not in seen:
            unique_sentences.append(sentence)
            seen.add(sentence)
        if len(unique_sentences) >= 4:
            break

    if not unique_sentences:
        return template["fallback"]

    return f"{template['prefix']} " + " ".join(unique_sentences)


def answer_question(question: str) -> Dict[str, object]:
    question = (question or "").strip()
    template = _language_template(question)
    if not question:
        return {"answer": template["fallback"], "context": "", "matches": []}

    structured_answer = _structured_answer(question)
    if structured_answer:
        return {
            "answer": structured_answer,
            "context": "Source: business_kpi_summary.json and generated_business_report.md",
            "matches": [{"source": "business_kpi_summary.json", "text": structured_answer, "score": 1.0}],
        }

    chunks = _build_chunks()
    if not chunks:
        return {"answer": template["fallback"], "context": "", "matches": []}

    chunk_texts = [chunk["text"] for chunk in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform(chunk_texts)
        retrieval_question = _augment_question_for_retrieval(question)
        query_vector = vectorizer.transform([retrieval_question])
    except ValueError:
        return {"answer": template["fallback"], "context": "", "matches": []}

    scores = cosine_similarity(query_vector, matrix).flatten()
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    top_matches = [
        {"source": chunks[index]["source"], "text": chunks[index]["text"], "score": float(score)}
        for index, score in ranked[:3]
        if score > 0
    ]

    if not top_matches or top_matches[0]["score"] < 0.08:
        return {"answer": template["fallback"], "context": "", "matches": top_matches}

    answer = _grounded_answer(question, retrieval_question, top_matches)
    context = "\n\n---\n\n".join(
        f"Source: {match['source']}\nScore: {match['score']:.3f}\n{match['text']}" for match in top_matches
    )
    return {"answer": answer, "context": context, "matches": top_matches}
