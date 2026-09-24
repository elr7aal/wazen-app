import re
from typing import Any


VENDORS = [
    (("كي اف سي","كي إف سي","kfc"), "KFC UAE"),
    (("ماكدونالدز","ماكدونالد","mcdonald's","mcdonalds","mcdonald"), "McDonald's UAE"),
    (("هارديز","hardee's","hardees","hardee"), "Hardee's UAE"),
]

CATEGORIES = [
    (("برغر","برجر","burger","burgers","زنجر","زينجر","zinger"), "BURGERS"),
    (("بيتزا","pizza"), "PIZZA"),
    (("حلويات","حلا","حلى","dessert","sweet","sweets"), "DESSERT"),
    (("سلطة","سلطه","salad"), "SALADS"),
    (("دجاج","chicken"), "CHICKEN"),
    (("سمك","fish","تونة","تونه","tuna"), "FISH"),
    (("رز","أرز","ارز","rice","مجبوس","machboos"), "RICE"),
]

MEALS = [
    (("فطور","الفطور","breakfast"), "BREAKFAST"),
    (("غداء","الغداء","lunch"), "LUNCH"),
    (("عشاء","العشاء","dinner"), "DINNER"),
    (("سناك","snack"), "SNACK"),
]


def _first_alias(text: str, table):
    for aliases,value in table:
        if any(alias in text for alias in aliases):
            return value
    return None


def _number(patterns: list[str], text: str):
    for pattern in patterns:
        match=re.search(pattern,text,re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (TypeError,ValueError):
                pass
    return None


def parse_craving_text(text: str) -> dict[str,Any]:
    raw=' '.join((text or '').strip().split())
    t=raw.lower()

    restaurant=_first_alias(t,VENDORS)
    category=_first_alias(t,CATEGORIES)
    meal_type=_first_alias(t,MEALS)

    max_calories=_number([
        r'(?:تحت|اقل من|أقل من|حد أقصى|ما يتعدى|under|below|max(?:imum)?)\s*(\d{2,4})\s*(?:سعرة|سعره|kcal|calories?)',
        r'(\d{2,4})\s*(?:سعرة|سعره|kcal|calories?)\s*(?:او اقل|أو أقل|or less|max)?',
    ],t)

    budget_max=_number([
        r'(?:ميزانيتي|الميزانية|الميزانيه|budget)\s*(?:حدها|حده|is|of)?\s*(?:aed|درهم|دراهم)?\s*(\d{1,4}(?:\.\d+)?)',
        r'(?:تحت|اقل من|أقل من|under|below)\s*(?:aed|درهم|دراهم)\s*(\d{1,4}(?:\.\d+)?)',
        r'(?:تحت|اقل من|أقل من|under|below)\s*(\d{1,4}(?:\.\d+)?)\s*(?:aed|درهم|دراهم)',
        r'(?:aed|درهم|دراهم)\s*(\d{1,4}(?:\.\d+)?)',
        r'(\d{1,4}(?:\.\d+)?)\s*(?:aed|درهم|دراهم)',
    ],t)

    min_protein_g=_number([
        r'(?:على الأقل|اقل شي|أقل شي|min(?:imum)?|at least)\s*(\d{1,3}(?:\.\d+)?)\s*(?:g|جرام|غرام)?\s*(?:بروتين|protein)',
        r'(\d{1,3}(?:\.\d+)?)\s*(?:g|جرام|غرام)\s*(?:بروتين|protein)',
        r'(?:بروتين|protein)\s*(?:على الأقل|at least|min)?\s*(\d{1,3}(?:\.\d+)?)',
    ],t)

    explicit={
        'restaurant':restaurant is not None,
        'food_category':category is not None,
        'max_calories':max_calories is not None,
        'budget_max':budget_max is not None,
        'min_protein_g':min_protein_g is not None,
        'meal_type':meal_type is not None,
    }
    matched=sum(1 for value in explicit.values() if value)
    confidence=min(0.99,0.45+matched*0.10)

    return {
        'intent':'EAT_NOW',
        'raw_text':raw,
        'restaurant':restaurant,
        'food_category':category,
        'max_calories':max_calories,
        'budget_max':budget_max,
        'min_protein_g':min_protein_g,
        'meal_type':meal_type,
        'explicit':explicit,
        'preserve_restaurant':restaurant is not None,
        'confidence':round(confidence,2),
    }
