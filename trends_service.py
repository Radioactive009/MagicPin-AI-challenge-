import random

# Mock data for trends
TRENDING_ITEMS = {
    "restaurants": ["Butter Chicken", "Cold Coffee", "Veg Thali", "Peri Peri Pizza", "Momos"],
    "dentists": ["Teeth Whitening", "Root Canal", "Invisalign", "Scaling", "Dental Implants"],
    "salons": ["Keratin Treatment", "Hydra Facial", "Balayage", "Manicure", "Beard Trim"],
    "gyms": ["Zumba Class", "Personal Training", "Yoga session", "HIIT Workshop", "Trial Pass"],
    "pharmacies": ["Vitamin C", "Omega 3", "First Aid Kit", "Whey Protein", "Skin Care Pack"],
}

LOCALITY_MODIFIERS = {
    "Delhi": 1.2,
    "Mumbai": 1.5,
    "Bangalore": 1.3,
    "Hyderabad": 1.1,
}

def get_market_trends(locality: str, category: str):
    """
    Returns mock market intelligence for a specific locality and category.
    """
    items = TRENDING_ITEMS.get(category, ["Standard Service", "Special Package"])
    modifier = LOCALITY_MODIFIERS.get(locality, 1.0)
    
    # Deterministic-ish random based on category + locality
    seed = hash(locality + category)
    rng = random.Random(seed)
    
    trending_now = rng.choice(items)
    search_volume = int(rng.randint(500, 2000) * modifier)
    competitor_count = rng.randint(5, 20)
    
    return {
        "trending_item": trending_now,
        "search_count": search_volume,
        "competitor_activity": "High" if competitor_count > 12 else "Medium",
        "spike_detected": search_volume > 1500
    }

def get_future_forecasts(city: str):
    """
    Returns upcoming events and predicted business impact.
    """
    events = [
        {"name": "IPL Final 2026", "date": "Sunday", "impact": "+45% Food Demand"},
        {"name": "Monsoon Festival", "date": "In 3 Days", "impact": "+30% Home Delivery"},
        {"name": "Local Weekend Spike", "date": "Saturday", "impact": "+20% Footfall"},
        {"name": "Global Yoga Day", "date": "June 21", "impact": "+50% Health/Gyms"}
    ]
    # Filter or customize based on city
    return events
