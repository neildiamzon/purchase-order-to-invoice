customers = ["service%foods", "bidfood", "kaan", "davis"]
BRANDS = [
    "alderson", "badia", "bianco", "dinapoli", "big red", "bonta",
    "frank", "french", "louisiana",
    "morepork", "stubbs", "tapatio",
    "mt olive", "mtolive", "kleins", "mrs kleins"
] # Added brands to add filter out false positives (e.g. Vlasic DILL Kosher != DILL Kosher 3.78 (MTOLIVE))

BLOCKED_ITEMS = [
    "frank's redhot honey soy garlic 3.8l",
    "frank's redhot xtra hot buffalo wing's sauce 3.78l",
    "sauer sweet hickory smoked bbq sauce 3.8l"
] # Because Xero get items api does not filter out archived items

inv_items = []
inv_customers = []