from typing import List, Dict

def query_ai_real_estate_advisor(user_prompt: str, context_properties: List[Dict]) -> str:
    """
    Intelligent Assistant service for real estate search & query recommendation.
    """
    prompt_lower = user_prompt.lower()
    matching = []

    for p in context_properties:
        price = p.get("price", 0) or 0
        bhk = p.get("bhk", 0) or 0

        if "under" in prompt_lower or "budget" in prompt_lower:
            if price <= 600000:
                matching.append(p)
        elif "2 bhk" in prompt_lower or "2 bedroom" in prompt_lower:
            if bhk == 2:
                matching.append(p)
        elif "3 bhk" in prompt_lower or "3 bedroom" in prompt_lower:
            if bhk == 3:
                matching.append(p)
        else:
            matching.append(p)

    count = len(matching)
    if count == 0:
        return "I couldn't find exact matches for your query. Try expanding your location or price filters!"

    top_matches = matching[:3]
    titles = ", ".join([f"'{p.get('title')}' (${p.get('price'):,})" for p in top_matches])
    
    return f"I found {count} matching properties for you! Top options include: {titles}. Would you like to schedule a tour or calculate monthly loan payments for any of these?"
