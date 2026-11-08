"""SmartEstate AI chatbot: intent routing + answers built from real listing data."""
import os
import re
import json
import time
import statistics
from uuid import UUID
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from groq import Groq
from sqlalchemy import func, or_, cast, String
from sqlalchemy.orm import Session

from app.rag.vector_store import search_properties
from app.models.property import Property, PropertyStatusEnum

load_dotenv()

_groq_client = None
_embedding_model = None
_session_ctx: Dict[str, Dict[str, Any]] = {}  # per-chat memory (resets on server restart)

FAST_MODEL = "openai/gpt-oss-20b"
MAIN_MODEL = "openai/gpt-oss-120b"

DEFAULT_RATE = 8.75      # % per year, assumption only
DEFAULT_TENURE = 20      # years, assumption only
EMI_INCOME_LIMIT = 0.40  # rule of thumb: total EMIs <= 40% of monthly income

DISCLAIMER_VERIFY = (
    "AI verification is a preliminary risk assessment, not a guarantee of legal ownership or safety. "
    "Please have a qualified property lawyer verify the title, encumbrances, approvals and other "
    "legal requirements before paying any money."
)
DISCLAIMER_LOAN = (
    "These are estimates only. Actual eligibility, interest rate and charges depend on the lender's assessment."
)

SYSTEM_PROMPT = """You are Luna, a real-estate assistant for the SmartEstate AI property buying and selling platform.
Rules:
- Use ONLY the property data provided in the prompt. Never invent prices, locations, documents or properties.
- Clearly separate listing facts (from the platform) from estimates.
- Never say a property is legally safe or guaranteed genuine. Recommend a property lawyer for legal checks.
- If there is no exact match, mention the closest alternatives from the data and say they are not exact matches.
- Keep answers concise and helpful. Use the conversation history to resolve words like "this" or "it"."""

CLASSIFY_PROMPT = """You are the query-understanding step of a real-estate assistant.
Return ONLY one JSON object, no other text:
{
  "intent": "search" | "count" | "property_info" | "verification" | "affordability" | "sell" | "location" | "general",
  "is_followup": true | false,
  "filters": {
    "bedrooms": integer or null,
    "property_type": "apartment" | "villa" | "plot" | "independent_house" | null,
    "listing_type": "buy" | "rent" | null,
    "city": string or null,
    "locality": string or null,
    "min_price": number or null,
    "max_price": number or null,
    "min_area_sqft": number or null,
    "max_area_sqft": number or null
  },
  "affordability": {
    "monthly_income": number or null,
    "existing_emi": number or null,
    "down_payment": number or null,
    "tenure_years": number or null,
    "interest_rate": number or null
  }
}
Intent guide:
- search: wants to see/find properties ("show me 2BHK under 70 lakhs")
- count: "how many ..."
- property_info: asks about a specific property's price/worth/details ("is this worth buying?")
- verification: genuine, fraud, fake, safe, legal, documents, verified
- affordability: EMI, loan, salary, can I afford, down payment
- sell: wants to sell/list their own property
- location: nearby facilities, neighbourhood, schools, metro
- general: anything else
Rules:
- Convert lakhs/crores to rupees (1 lakh = 100000, 1 crore = 10000000). "under/below" -> max_price, "above/over" -> min_price.
- flat/apartment -> property_type "apartment". BHK -> bedrooms.
- is_followup is true when the message refers to earlier results or tweaks the previous search ("what about 3BHK", "cheaper ones").
- Use null for anything not stated. The "Context" line is only to help you judge follow-ups."""


# ----------------------------------------------------------------------------
# Groq helpers
# ----------------------------------------------------------------------------
def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def try_groq_completion(client, messages, temperature=0.3, max_tokens=500, models=None):
    """Try models in order; return (text, model_name) or (None, None)."""
    if not client:
        return None, None
    for model_name in (models or [MAIN_MODEL, FAST_MODEL]):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if completion and completion.choices and completion.choices[0].message and completion.choices[0].message.content:
                return completion.choices[0].message.content, model_name
            print(f"Groq completion returned empty content for model {model_name}")
        except Exception as e:
            print(f"Groq completion failed for model {model_name}: {type(e).__name__}: {e}")
    return None, None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _safe_json(text: Optional[str]) -> Optional[dict]:
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Small utilities
# ----------------------------------------------------------------------------
def _val(x):
    return x.value if hasattr(x, "value") else x


def fmt_price(n) -> str:
    n = float(n or 0)
    if n >= 1e7:
        return f"₹{n / 1e7:.2f} Cr"
    if n >= 1e5:
        return f"₹{n / 1e5:.1f} L"
    return f"₹{n:,.0f}"


def _get_ctx(session_id: Optional[str]) -> Dict[str, Any]:
    if not session_id:
        return {}
    ctx = _session_ctx.get(session_id)
    if ctx is None:
        if len(_session_ctx) > 500:
            _session_ctx.pop(next(iter(_session_ctx)))
        ctx = {}
        _session_ctx[session_id] = ctx
    return ctx


CITY_ALIASES = {
    "bengaluru": ["bengaluru", "bangalore"],
    "bangalore": ["bengaluru", "bangalore"],
    "mumbai": ["mumbai", "bombay"],
    "gurgaon": ["gurgaon", "gurugram"],
    "gurugram": ["gurgaon", "gurugram"],
}
PROPERTY_TYPE_ALIASES = {
    "apartment": ["apartment", "flat"],
    "villa": ["villa"],
    "plot": ["plot", "land"],
    "independent_house": ["independent house", "independent_house", "house"],
}
LISTING_ALIASES = {
    "buy": ["buy", "sale", "sell", "for sale"],
    "rent": ["rent", "rental", "lease"],
}
KNOWN_CITIES = [
    "bengaluru", "bangalore", "mumbai", "delhi", "chennai", "hyderabad",
    "pune", "kolkata", "ahmedabad", "gurgaon", "gurugram", "noida",
]
FILTER_KEYS = [
    "bedrooms", "property_type", "listing_type", "city", "locality",
    "min_price", "max_price", "min_area_sqft", "max_area_sqft",
]


def _clean_filters(raw: Optional[dict]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    raw = raw or {}
    for k in FILTER_KEYS:
        v = raw.get(k)
        if v in (None, "", "null", "None"):
            continue
        try:
            if k == "bedrooms":
                v = int(v)
            elif k in ("min_price", "max_price", "min_area_sqft", "max_area_sqft"):
                v = float(v)
            else:
                v = str(v).strip().lower()
        except Exception:
            continue
        out[k] = v
    return out


# ----------------------------------------------------------------------------
# Rule-based parsing (fallback + safety net on top of the LLM)
# ----------------------------------------------------------------------------
_UNIT = r"(?:crores?|cr|lakhs?|lacs?|l)"


def _rupees(num, unit) -> float:
    return float(num) * (1e7 if unit.lower().startswith("cr") else 1e5)


def _money(num, unit) -> float:
    num = float(num)
    unit = (unit or "").lower()
    if unit == "k":
        return num * 1e3
    if unit.startswith("cr"):
        return num * 1e7
    if unit.startswith("l"):
        return num * 1e5
    return num


def _normalize_text(query: str) -> str:
    return query.lower().replace("₹", " ").replace(",", "").replace("rs.", " ").replace("rs ", " ")


def parse_price_filters(query: str) -> Dict[str, float]:
    q = _normalize_text(query)
    out: Dict[str, float] = {}
    m = re.search(rf"between\s+([\d.]+)\s*({_UNIT})?\s*(?:and|to|-)\s*([\d.]+)\s*({_UNIT})\b", q)
    if m:
        u2 = m.group(4)
        u1 = m.group(2) or u2
        out["min_price"] = _rupees(m.group(1), u1)
        out["max_price"] = _rupees(m.group(3), u2)
        return out
    m = re.search(rf"(?:under|below|less than|upto|up to|within|max|maximum|budget(?: of)?)\s*([\d.]+)\s*({_UNIT})\b", q)
    if not m:
        m = re.search(rf"([\d.]+)\s*({_UNIT})\s*(?:budget|or less|or below|max)\b", q)
    if m:
        out["max_price"] = _rupees(m.group(1), m.group(2))
    m = re.search(rf"(?:above|over|more than|at least|min|minimum)\s*([\d.]+)\s*({_UNIT})\b", q)
    if m:
        out["min_price"] = _rupees(m.group(1), m.group(2))
    return out


def parse_affordability(query: str) -> Dict[str, Any]:
    q = _normalize_text(query)
    out: Dict[str, Any] = {}
    m = (re.search(r"(?:salary|income|earn\w*)\D{0,20}?([\d.]+)\s*(k|lakhs?|lacs?)?\b", q)
         or re.search(r"([\d.]+)\s*(k|lakhs?|lacs?)?\s*(?:per month|monthly|a month|pm)?\s*(?:salary|income)", q))
    if m:
        out["monthly_income"] = _money(m.group(1), m.group(2))
    m = re.search(r"(?:existing|other|current)\s*emis?\D{0,15}?([\d.]+)\s*(k|lakhs?|lacs?)?\b", q)
    if m:
        out["existing_emi"] = _money(m.group(1), m.group(2))
    m = re.search(r"down\s*payment\D{0,15}?([\d.]+)\s*(k|crores?|cr|lakhs?|lacs?|l)?\b", q)
    if m:
        out["down_payment"] = _money(m.group(1), m.group(2))
    m = re.search(r"(\d+)\s*(?:years|yrs|year)\b", q)
    if m:
        out["tenure_years"] = float(m.group(1))
    m = re.search(r"([\d.]+)\s*%", q)
    if m:
        out["interest_rate"] = float(m.group(1))
    return out


def rule_based_classify(query: str) -> Dict[str, Any]:
    q = query.lower()
    f: Dict[str, Any] = {}

    bhk = re.search(r"(\d+)\s*-?\s*(?:bhk|bedroom|bed)\b", q)
    if bhk:
        f["bedrooms"] = int(bhk.group(1))
    for pt, words in PROPERTY_TYPE_ALIASES.items():
        if any(re.search(rf"\b{re.escape(w)}s?\b", q) for w in words):
            f["property_type"] = pt
            break
    if re.search(r"\b(rent|rental|lease)\b", q):
        f["listing_type"] = "rent"
    elif re.search(r"\b(buy|purchase|sale)\b", q):
        f["listing_type"] = "buy"
    elif f.get("min_price") is not None or f.get("max_price") is not None:
        f["listing_type"] = "buy"
    for city in KNOWN_CITIES:
        if city in q:
            f["city"] = city
            break
    f.update(parse_price_filters(query))

    if re.search(r"\b(sell my|list my|how (?:do|can) i sell|post my|sell a|selling my|sell flat|sell property)\b", q):
        intent = "sell"
    elif re.search(r"\b(genuine|fraud|fake|scam|safe to buy|legal|verified|verification|authentic|duplicate)\b", q):
        intent = "verification"
    elif re.search(r"\b(afford|emi|loan|salary|income|down payment|eligib\w*)\b", q):
        intent = "affordability"
    elif re.search(r"\b(worth|good deal|overpriced|fair price|should i buy|tell me about|details)\b", q):
        intent = "property_info"
    elif re.search(r"\b(nearby|neighbou?rhood|school|hospital|metro|connectivity|location)\b", q):
        intent = "location"
    elif re.search(r"\b(how many|count|number of)\b", q):
        intent = "count"
    elif re.search(r"\b(show|find|list|search|looking for|want to buy|flats?|apartments?|villas?|plots?)\b", q) or bhk:
        intent = "search"
    else:
        intent = "general"

    return {
        "intent": intent,
        "is_followup": bool(re.search(r"\b(what about|instead|also|cheaper|bigger|smaller|more)\b", q)),
        "filters": f,
        "affordability": parse_affordability(query),
    }


def classify(query: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    valid = {"search", "count", "property_info", "verification", "affordability", "sell", "location", "general"}
    rb = rule_based_classify(query)
    parsed = None

    client = get_groq_client()
    if client:
        note = json.dumps({"current_property": ctx.get("current_title"), "last_filters": ctx.get("last_filters")})
        content, _ = try_groq_completion(
            client,
            [
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": f"Context: {note}\nUser message: {query}"},
            ],
            temperature=0,
            max_tokens=350,
            models=[FAST_MODEL, MAIN_MODEL],
        )
        parsed = _safe_json(content)

    if not parsed:
        parsed = rb

    intent = parsed.get("intent") if parsed.get("intent") in valid else rb["intent"]
    if intent == "general" and rb["intent"] != "general":
        intent = rb["intent"]

    filters = _clean_filters(parsed.get("filters"))
    for k, v in _clean_filters(rb["filters"]).items():  # regex fills anything the LLM missed
        filters.setdefault(k, v)

    aff = {k: v for k, v in (parsed.get("affordability") or {}).items() if v is not None}
    for k, v in rb["affordability"].items():
        aff.setdefault(k, v)

    return {
        "intent": intent,
        "is_followup": bool(parsed.get("is_followup", rb["is_followup"])),
        "filters": filters,
        "affordability": aff,
    }


# ----------------------------------------------------------------------------
# Database queries
# ----------------------------------------------------------------------------
def build_sql_query(filters: Dict[str, Any], db: Session):
    query = db.query(Property).filter(Property.status == PropertyStatusEnum.approved)

    if filters.get("bedrooms"):
        query = query.filter(Property.bhk == filters["bedrooms"])
    if filters.get("_bhk_in"):
        query = query.filter(Property.bhk.in_(filters["_bhk_in"]))

    if filters.get("property_type"):
        aliases = PROPERTY_TYPE_ALIASES.get(filters["property_type"], [filters["property_type"]])
        query = query.filter(func.lower(cast(Property.property_type, String)).in_(aliases))

    if filters.get("listing_type"):
        aliases = LISTING_ALIASES.get(filters["listing_type"], [filters["listing_type"]])
        query = query.filter(func.lower(cast(Property.listing_type, String)).in_(aliases))

    if filters.get("city"):
        variants = CITY_ALIASES.get(filters["city"], [filters["city"]])
        query = query.filter(or_(*[Property.city.ilike(f"%{c}%") for c in variants]))

    if filters.get("locality"):
        query = query.filter(
            or_(
                Property.address.ilike(f"%{filters['locality']}%"),
                Property.city.ilike(f"%{filters['locality']}%"),
            )
        )

    if filters.get("min_price"):
        query = query.filter(Property.price >= filters["min_price"])
    if filters.get("max_price"):
        query = query.filter(Property.price <= filters["max_price"])
    if filters.get("min_area_sqft"):
        query = query.filter(Property.area_sqft >= filters["min_area_sqft"])
    if filters.get("max_area_sqft"):
        query = query.filter(Property.area_sqft <= filters["max_area_sqft"])

    return query


def _load_property(db: Session, pid) -> Optional[Property]:
    if not pid:
        return None
    try:
        return db.query(Property).filter(Property.id == UUID(str(pid))).first()
    except Exception:
        return None


def _load_by_ids(db: Session, ids: List[str]) -> List[Property]:
    uuids = []
    for i in ids:
        try:
            uuids.append(UUID(str(i)))
        except Exception:
            pass
    if not uuids:
        return []
    rows = db.query(Property).filter(
        Property.id.in_(uuids), Property.status == PropertyStatusEnum.approved
    ).all()
    order = {str(u): n for n, u in enumerate(uuids)}
    return sorted(rows, key=lambda r: order.get(str(r.id), 99))


def prop_card(p: Property) -> Dict[str, Any]:
    return {
        "id": str(p.id),
        "title": p.title,
        "price": float(p.price) if p.price else 0,
        "area_sqft": float(p.area_sqft) if p.area_sqft else 0,
        "bhk": p.bhk,
        "bathrooms": p.bathrooms,
        "address": p.address,
        "city": p.city,
        "property_type": _val(p.property_type),
        "listing_type": _val(p.listing_type),
        "status": _val(p.status),
        "trust_score": getattr(p, "trust_score", None),
    }


def resolve_property(query: str, db: Session, ctx: Dict[str, Any], property_id=None) -> Optional[Property]:
    results = ctx.get("last_results", [])
    pid = str(property_id) if property_id else None
    if not pid:
        ordinals = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2,
                    "fourth": 3, "4th": 3, "fifth": 4, "5th": 4}
        m = re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\b", query.lower())
        if m and ordinals[m.group(1)] < len(results):
            pid = results[ordinals[m.group(1)]]["id"]
    if not pid:
        ql = query.lower()
        for r in results:
            if r.get("title") and r["title"].lower() in ql:
                pid = r["id"]
                break
    if not pid:
        pid = ctx.get("current_property_id")
    if not pid and len(results) == 1:
        pid = results[0]["id"]
    return _load_property(db, pid)


def comparables(p: Property, db: Session) -> Dict[str, Any]:
    base = db.query(Property).filter(
        Property.status == PropertyStatusEnum.approved,
        Property.id != p.id,
        Property.area_sqft > 0,
        Property.price > 0,
    )
    if p.city:
        base = base.filter(func.lower(Property.city) == p.city.lower())
    same = base.filter(Property.bhk == p.bhk).all() if p.bhk else []
    if len(same) >= 3:
        rows, scope = same, f"{p.bhk} BHK listings in {p.city}"
    else:
        rows, scope = base.all(), f"all listings in {p.city}"
    ppsf = [float(r.price) / float(r.area_sqft) for r in rows]
    if len(ppsf) < 3:
        return {"n": len(ppsf), "scope": scope}
    return {"n": len(ppsf), "scope": scope, "median": statistics.median(ppsf),
            "min": min(ppsf), "max": max(ppsf)}


# ----------------------------------------------------------------------------
# Handlers (each returns {"text", "ids", "props"})
# ----------------------------------------------------------------------------
def _describe_filters(f: Dict[str, Any]) -> str:
    parts = []
    if f.get("bedrooms"):
        parts.append(f"{f['bedrooms']} BHK")
    if f.get("property_type"):
        parts.append(f["property_type"].replace("_", " "))
    desc = " ".join(parts) if parts else "properties"
    if f.get("listing_type") == "rent":
        desc += " for rent"
    if f.get("locality"):
        desc += f" in {f['locality'].title()}"
    if f.get("city"):
        desc += f" in {f['city'].title()}"
    if f.get("min_price") and f.get("max_price"):
        desc += f" between {fmt_price(f['min_price'])} and {fmt_price(f['max_price'])}"
    elif f.get("max_price"):
        desc += f" under {fmt_price(f['max_price'])}"
    elif f.get("min_price"):
        desc += f" above {fmt_price(f['min_price'])}"
    return desc


def _relaxed_variants(f: Dict[str, Any]):
    variants = []
    if f.get("max_price"):
        v = dict(f)
        v["max_price"] = f["max_price"] * 1.2
        variants.append((v, f"slightly above your budget (up to {fmt_price(v['max_price'])})"))
    if f.get("bedrooms"):
        v = dict(f)
        b = v.pop("bedrooms")
        v["_bhk_in"] = [x for x in (b - 1, b + 1) if x > 0]
        variants.append((v, f"with a different BHK count ({' or '.join(str(x) for x in v['_bhk_in'])} BHK)"))
    if f.get("locality"):
        v = dict(f)
        v.pop("locality")
        variants.append((v, "in other areas of the city"))
    return variants


def handle_search(filters: Dict[str, Any], db: Session, ctx: Dict[str, Any], intent: str) -> Dict[str, Any]:
    q = build_sql_query(filters, db)
    total = q.count()
    note = ""
    if total == 0:
        for variant, why in _relaxed_variants(filters):
            q2 = build_sql_query(variant, db)
            t2 = q2.count()
            if t2 > 0:
                q, total, note = q2, t2, why
                break

    desc = _describe_filters(filters)

    if intent == "count":
        if total == 0:
            text = f"I couldn't find any approved listings for {desc}."
        elif note:
            text = f"No exact matches for {desc}, but I found {total} listing(s) {note}. Want me to show them?"
        else:
            text = f"There are {total} approved listings for {desc}. Want me to show them?"
        return {"text": text, "ids": [], "props": []}

    if total == 0:
        return {"text": f"I couldn't find any listings for {desc}. Try widening the budget, area or BHK count.",
                "ids": [], "props": []}

    rows = q.order_by(Property.created_at.desc()).limit(5).all()
    listing_phrase = "for rent" if (filters.get("listing_type") or "").lower() == "rent" else "for sale"

    if note:
        header = f"No exact match for {desc}. Closest alternatives ({note})."
    else:
        header = f"I found {total} approved properties {listing_phrase} for {desc}. Here are the {len(rows)} matching listings:"

    lines = [header]
    if total > len(rows):
        lines.append(f"...and {total - len(rows)} more. Ask me to narrow the search.")
    lines.append('Ask about any of them, e.g. "is the first one worth buying?" or "is this genuine?"')

    cards = [prop_card(p) for p in rows]
    ctx["last_filters"] = filters
    ctx["last_results"] = [{"id": c["id"], "title": c["title"]} for c in cards]
    if len(cards) == 1:
        ctx["current_property_id"] = cards[0]["id"]
        ctx["current_title"] = cards[0]["title"]
    return {"text": "\n".join(lines), "ids": [c["id"] for c in cards], "props": cards}


def _quality_flags(p: Property) -> List[str]:
    flags = []
    if not p.area_sqft:
        flags.append("Area is missing from the listing.")
    if not p.description:
        flags.append("No description provided.")
    if not p.address:
        flags.append("Address is missing.")
    if _val(p.status) != "approved":
        flags.append(f"Listing status is '{_val(p.status)}', not approved.")
    return flags


def handle_property_info(p: Property, db: Session) -> Dict[str, Any]:
    comp = comparables(p, db)
    lines = [f"**{p.title}** — {', '.join(x for x in [p.address, p.city] if x)}", "",
             "**Listing details (from the platform)**",
             f"- Price: {fmt_price(p.price)}"]
    if p.bhk:
        lines.append(f"- Configuration: {p.bhk} BHK" + (f", {p.bathrooms} bathrooms" if p.bathrooms else ""))
    ppsf = None
    if p.area_sqft and p.price:
        ppsf = float(p.price) / float(p.area_sqft)
        lines.append(f"- Area: {float(p.area_sqft):,.0f} sqft → ₹{ppsf:,.0f}/sqft")
    trust = getattr(p, "trust_score", None)
    if trust is not None:
        lines.append(f"- Platform trust score: {trust}")

    lines += ["", "**Price comparison (estimate based on other SmartEstate listings)**"]
    if ppsf and comp.get("median"):
        diff = (ppsf - comp["median"]) / comp["median"] * 100
        lines.append(f"- Compared with {comp['n']} {comp['scope']}: typical ₹{comp['median']:,.0f}/sqft "
                     f"(range ₹{comp['min']:,.0f}–₹{comp['max']:,.0f}).")
        if diff > 15:
            lines.append(f"- This listing is about {diff:.0f}% above the typical price per sqft. Ask the seller to justify it.")
        elif diff < -30:
            lines.append(f"- This listing is about {abs(diff):.0f}% below typical. Unusually low prices need extra checking.")
        elif diff < -15:
            lines.append(f"- This listing is about {abs(diff):.0f}% below typical, which may be a good deal. Check why.")
        else:
            lines.append("- The price per sqft is in line with similar listings.")
        lines.append("- This only uses listings on this platform, not full market data.")
    else:
        lines.append("- Not enough comparable listings on the platform to judge the price.")

    flags = _quality_flags(p)
    lines += ["", "**Potential concerns**"]
    lines += [f"- {f}" for f in flags] if flags else ["- No obvious gaps in the listing data."]
    lines.append("- Location, builder reputation, approvals and legal title are not covered here and need on-site checks.")
    lines += ["", "Want me to check verification status or estimate the EMI for this property?"]
    return {"text": "\n".join(lines), "ids": [str(p.id)], "props": [prop_card(p)]}


def handle_verification(p: Property, db: Session) -> Dict[str, Any]:
    lines = [f"**Verification summary — {p.title}**", "",
             f"- Platform listing status: {_val(p.status)}"]
    trust = getattr(p, "trust_score", None)
    lines.append(f"- Trust score: {trust}" if trust is not None else "- Trust score: not available for this listing")

    signals = getattr(p, "trust_signals", None)
    if isinstance(signals, dict) and signals:
        lines.append("- Document checks:")
        lines += [f"  - {str(k).replace('_', ' ').title()}: {v}" for k, v in signals.items()]
    elif signals:
        lines.append(f"- Document checks: {signals}")
    else:
        lines.append("- Document checks: no verification results are available for this listing yet.")

    risks = _quality_flags(p)
    if p.address and p.city:
        dupes = db.query(Property).filter(
            Property.id != p.id,
            func.lower(Property.address) == p.address.lower(),
            func.lower(Property.city) == p.city.lower(),
            Property.bhk == p.bhk,
        ).count()
        if dupes:
            risks.append(f"{dupes} other listing(s) share the same address and BHK count (possible duplicate).")
    comp = comparables(p, db)
    if p.area_sqft and p.price and comp.get("median"):
        diff = (float(p.price) / float(p.area_sqft) - comp["median"]) / comp["median"] * 100
        if diff < -30:
            risks.append(f"Price per sqft is about {abs(diff):.0f}% below similar listings (a common fraud signal).")
        elif diff > 40:
            risks.append(f"Price per sqft is about {diff:.0f}% above similar listings.")

    lines += ["", "**Potential risks**"]
    lines += [f"- {r}" for r in risks] if risks else ["- No inconsistencies found in the available data."]
    lines += ["", DISCLAIMER_VERIFY]
    return {"text": "\n".join(lines), "ids": [str(p.id)], "props": [prop_card(p)]}


def _emi(principal: float, annual_rate: float, years: float) -> float:
    n = int(years * 12)
    r = annual_rate / 12 / 100
    if n <= 0:
        return 0.0
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _max_loan(emi_cap: float, annual_rate: float, years: float) -> float:
    n = int(years * 12)
    r = annual_rate / 12 / 100
    if emi_cap <= 0 or n <= 0:
        return 0.0
    if r == 0:
        return emi_cap * n
    return emi_cap * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def handle_affordability(p: Optional[Property], aff: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    a = {**ctx.get("affordability", {}), **{k: v for k, v in aff.items() if v is not None}}
    ctx["affordability"] = a

    income = a.get("monthly_income")
    if not income:
        return {"text": ("I can estimate your home-loan affordability. Please tell me:\n"
                         "- Your monthly take-home income\n"
                         "- Existing monthly EMIs (if any)\n"
                         "- Down payment you can pay\n"
                         "- Preferred loan tenure in years\n\n" + DISCLAIMER_LOAN),
                "ids": [], "props": []}

    existing = float(a.get("existing_emi") or 0)
    rate = float(a.get("interest_rate") or DEFAULT_RATE)
    years = float(a.get("tenure_years") or DEFAULT_TENURE)
    assumed = []
    if not a.get("interest_rate"):
        assumed.append(f"interest rate {DEFAULT_RATE}% per year")
    if not a.get("tenure_years"):
        assumed.append(f"{DEFAULT_TENURE}-year tenure")
    if not a.get("existing_emi"):
        assumed.append("no existing EMIs")

    cap = max(float(income) * EMI_INCOME_LIMIT - existing, 0)
    max_loan = _max_loan(cap, rate, years)
    lines = []

    if p is None:
        lines.append(f"With an income of ₹{float(income):,.0f}/month, a comfortable EMI is about ₹{cap:,.0f} "
                     f"({int(EMI_INCOME_LIMIT * 100)}% of income minus existing EMIs).")
        lines.append(f"- Estimated maximum loan: {fmt_price(max_loan)} at {rate}% for {years:.0f} years")
        if a.get("down_payment"):
            lines.append(f"- With your down payment of {fmt_price(a['down_payment'])}, you could look at properties up to "
                         f"about {fmt_price(max_loan + float(a['down_payment']))}")
        else:
            lines.append(f"- With a 20% down payment, that is roughly a {fmt_price(max_loan / 0.8)} property")
        lines.append("\nWant me to show properties within that budget?")
        ids, props = [], []
    else:
        price = float(p.price or 0)
        down = a.get("down_payment")
        if down is None:
            down = price * 0.2
            assumed.append("20% down payment")
        down = float(down)
        loan = max(price - down, 0)
        emi = _emi(loan, rate, years)
        share = emi / float(income) * 100
        lo, hi = price * 0.06, price * 0.08
        lines.append(f"**Affordability for {p.title}** ({fmt_price(price)})")
        lines.append(f"- Loan amount: {fmt_price(loan)} (down payment {fmt_price(down)})")
        lines.append(f"- Estimated EMI: ₹{emi:,.0f}/month at {rate}% for {years:.0f} years")
        lines.append(f"- EMI as share of your income: {share:.0f}% (comfortable limit used here: {int(EMI_INCOME_LIMIT * 100)}% including existing EMIs)")
        lines.append(f"- Upfront cost: down payment + roughly {fmt_price(lo)}–{fmt_price(hi)} for stamp duty, registration and other charges (varies by state)")
        if emi <= cap:
            lines.append("- Result: this looks manageable on the numbers above.")
        else:
            needed_down = max(price - max_loan, 0)
            lines.append(f"- Result: the EMI is above your comfortable limit (about ₹{cap:,.0f}). "
                         f"You would need a down payment of about {fmt_price(needed_down)}, a longer tenure, or a cheaper property.")
        ids, props = [str(p.id)], [prop_card(p)]

    if assumed:
        lines.append("\nAssumptions: " + ", ".join(assumed) + ". Tell me the real values and I'll recalculate.")
    lines.append(DISCLAIMER_LOAN)
    return {"text": "\n".join(lines), "ids": ids, "props": props}


def handle_sell(filters: Dict[str, Any], db: Session) -> Dict[str, Any]:
    lines = ["Here is how to sell your property on SmartEstate AI:", "",
             "1. **Add property details**: title, address, city, BHK, bathrooms, area (sqft) and a clear description.",
             "2. **Upload photos**: clear photos of every room, the building exterior and the entrance.",
             "3. **Upload documents**: ownership/title papers and other property documents, so the listing can be verified.",
             "4. **Set a reasonable asking price**: compare with similar listings (I can estimate one below).",
             "5. **Submit for verification**: the listing goes live after it is reviewed and approved.",
             "", "Complete listings with documents get more trust from buyers."]

    city, area = filters.get("city"), filters.get("min_area_sqft") or filters.get("max_area_sqft")
    if city and area:
        base = db.query(Property).filter(
            Property.status == PropertyStatusEnum.approved,
            Property.area_sqft > 0, Property.price > 0,
            or_(*[Property.city.ilike(f"%{c}%") for c in CITY_ALIASES.get(city, [city])]),
        )
        if filters.get("bedrooms"):
            base = base.filter(Property.bhk == filters["bedrooms"])
        ppsf = [float(r.price) / float(r.area_sqft) for r in base.all()]
        if len(ppsf) >= 3:
            mid = statistics.median(ppsf) * float(area)
            lines += ["", f"**Price estimate (based on {len(ppsf)} similar listings on this platform):** "
                          f"{fmt_price(mid * 0.92)} – {fmt_price(mid * 1.08)}. "
                          "This is only a rough guide, not a valuation."]
    else:
        lines += ["", "Tell me the city, BHK and area (sqft) of your property and I'll estimate a reasonable asking price."]
    return {"text": "\n".join(lines), "ids": [], "props": []}


def _prop_facts(p: Property) -> str:
    desc = (p.description or "")[:300]
    return (f"- ID {p.id}: {p.title}, {p.bhk} BHK, {fmt_price(p.price)}, "
            f"{float(p.area_sqft or 0):,.0f} sqft, {p.address}, {p.city}, "
            f"type {_val(p.property_type)}, trust score {getattr(p, 'trust_score', None)}. {desc}")


def handle_general(query: str, db: Session, ctx: Dict[str, Any], history: Optional[List[Dict[str, str]]],
                   current: Optional[Property]) -> Dict[str, Any]:
    client = get_groq_client()
    if not client:
        return {"text": "The AI assistant is unavailable right now because GROQ_API_KEY is not configured.",
                "ids": [], "props": []}

    props: List[Property] = []
    if current:
        props.append(current)
    try:
        matches = search_properties(query, top_k=5)
        for p in _load_by_ids(db, matches["ids"][0]):
            if not any(x.id == p.id for x in props):
                props.append(p)
    except Exception as e:
        print(f"Vector search failed: {e}")

    if not props:
        return {"text": "I don't have any listings relevant to that right now. Try asking me to search by city, BHK and budget.",
                "ids": [], "props": []}

    context = "\n".join(_prop_facts(p) for p in props)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in (history or [])[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"][:800]})
    messages.append({"role": "user", "content": (
        f"Question: {query}\n\nProperty data (the ONLY data you may use):\n{context}")})

    text, _ = try_groq_completion(client, messages, temperature=0.3, max_tokens=500)
    if not text:
        text = "I couldn't generate an answer right now. Please try again in a moment."
        return {"text": text, "ids": [], "props": [], "fallback": True}
    return {"text": text, "ids": [str(p.id) for p in props], "props": [prop_card(p) for p in props], "fallback": False}


def _is_greeting(query: str) -> bool:
    text = (query or "").strip().lower()
    text = re.sub(r"[^\\w\\s]", "", text)
    return text in {
        "hi", "hello", "hey", "hi there", "hello there", "hey there",
        "good morning", "good afternoon", "good evening",
    }


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def answer_query(query: str, db: Session, session_id=None, history: Optional[List[Dict[str, str]]] = None,
                 property_id=None) -> Dict[str, Any]:
    t0 = time.time()
    sid = str(session_id) if session_id else None
    ctx = _get_ctx(sid)
    if property_id:
        ctx["current_property_id"] = str(property_id)

    if _is_greeting(query):
        return {
            "response_text": ("Hi! 👋 I'm Luna, your AI assistant. I can help you find properties, compare options, "
                              "and explore buying or selling. "
                              'Try asking something like "show 2BHK flats in Bengaluru under 80 lakhs".',),
            "referenced_property_ids": [],
            "properties": [],
            "intent": "general",
            "filters_used": {},
            "timing": {"total_ms": int((time.time() - t0) * 1000), "classify_ms": 0},
            "fallback": False,
        }

    t1 = time.time()
    parsed = classify(query, ctx)
    classify_ms = int((time.time() - t1) * 1000)
    intent = parsed["intent"]
    filters = parsed["filters"]

    try:
        if intent in ("search", "count"):
            if parsed["is_followup"] and ctx.get("last_filters"):
                filters = {**ctx["last_filters"], **filters}
            result = handle_search(filters, db, ctx, intent)

        elif intent in ("property_info", "verification", "location"):
            prop = resolve_property(query, db, ctx, property_id)
            if prop is None:
                result = {"text": ("Which property do you mean? Search for one first (for example "
                                   "\"show 2BHK flats in Bengaluru under 70 lakhs\"), or open a property page and ask from there."),
                          "ids": [], "props": []}
            else:
                ctx["current_property_id"] = str(prop.id)
                ctx["current_title"] = prop.title
                if intent == "property_info":
                    result = handle_property_info(prop, db)
                elif intent == "verification":
                    result = handle_verification(prop, db)
                else:
                    result = handle_general(query, db, ctx, history, prop)

        elif intent == "affordability":
            refers = property_id or re.search(
                r"\b(this|that|it|first|second|third|these|those|the property|the flat)\b", query.lower())
            prop = resolve_property(query, db, ctx, property_id) if refers else None
            result = handle_affordability(prop, parsed["affordability"], ctx)

        elif intent == "sell":
            result = handle_sell(filters, db)

        else:
            result = handle_general(query, db, ctx, history, None)

    except Exception as e:
        print(f"answer_query failed: {e}")
        db.rollback()
        result = {"text": "Sorry, something went wrong while processing that. Please try again.",
                  "ids": [], "props": [], "fallback": True}

    return {
        "response_text": result["text"],
        "referenced_property_ids": result["ids"],
        "properties": result["props"],
        "intent": intent,
        "filters_used": filters,
        "timing": {"total_ms": int((time.time() - t0) * 1000), "classify_ms": classify_ms},
        "fallback": bool(result.get("fallback", False)),
    }


def sync_chromadb_with_db(db: Session):
    properties = db.query(Property).filter(Property.status == PropertyStatusEnum.approved).all()
    from app.rag.vector_store import upsert_property, reset_collection

    reset_collection()
    for p in properties:
        ptype = _val(p.property_type)
        text = (f"{p.title}. {p.description or ''}. {ptype}. {p.bhk} BHK. {p.area_sqft} sqft. "
                f"{p.address}. {p.city}. ₹{p.price:,.0f}.")
        metadata = {
            "title": p.title,
            "price": float(p.price) if p.price else 0,
            "bhk": p.bhk,
            "area_sqft": float(p.area_sqft) if p.area_sqft else 0,
            "city": p.city,
            "property_type": ptype,
        }
        upsert_property(str(p.id), text, metadata)
    return len(properties)


if __name__ == "__main__":
    from app.database import get_db

    db = next(get_db())
    for msg in ["Show me 2BHK flats in Bangalore under ₹70 lakhs", "is the first one worth buying?", "is this genuine?"]:
        print(json.dumps(answer_query(msg, db, session_id="test"), indent=2, default=str))