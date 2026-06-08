"""Curated indicative city signals for the UK City Guide.

Values are 1–5 indicative judgments (curated), shown to users as bands with a
"verify on official source" note — never as exact statistics. Monthly cost is a
band, never a precise figure. Top universities are derived factually from the
real catalog at seed time.
"""

# city: (region, cost, rent, part_time, grad, student_life, community, accommodation_difficulty,
#        best_for[list], industries[list])
CITY_DATA = {
    "London": ("London", 5, 5, 5, 5, 5, 5, 5, ["Finance", "Tech", "Business", "Law"], ["Finance", "Tech", "Media"]),
    "Manchester": ("North West", 4, 3, 4, 4, 5, 5, 3, ["Business", "Tech", "Data", "Media"], ["Tech", "Media", "Finance"]),
    "Birmingham": ("West Midlands", 3, 3, 4, 4, 4, 5, 3, ["Business", "Engineering", "Healthcare"], ["Manufacturing", "Business", "Healthcare"]),
    "Newcastle": ("North East", 2, 2, 3, 3, 4, 4, 2, ["Engineering", "Computing", "Healthcare"], ["Healthcare", "Tech", "Education"]),
    "Leeds": ("Yorkshire and the Humber", 3, 3, 4, 4, 4, 4, 3, ["Business", "Finance", "Data"], ["Finance", "Legal", "Digital"]),
    "Sheffield": ("Yorkshire and the Humber", 2, 2, 3, 3, 4, 4, 2, ["Engineering", "Computing", "Manufacturing"], ["Manufacturing", "Engineering", "Health"]),
    "Glasgow": ("Scotland", 3, 3, 4, 4, 4, 4, 3, ["Engineering", "Computing", "Finance"], ["Finance", "Engineering", "Creative"]),
    "Edinburgh": ("Scotland", 4, 4, 4, 4, 4, 4, 4, ["Finance", "Data", "Informatics"], ["Finance", "Tech", "Tourism"]),
    "Cardiff": ("Wales", 3, 3, 3, 3, 4, 3, 3, ["Media", "Healthcare", "Business"], ["Media", "Public Sector", "Finance"]),
    "Coventry": ("West Midlands", 2, 2, 3, 3, 3, 5, 2, ["Engineering", "Automotive", "Business"], ["Automotive", "Engineering", "Logistics"]),
    "Leicester": ("East Midlands", 2, 2, 3, 3, 3, 5, 2, ["Business", "Engineering", "Healthcare"], ["Logistics", "Manufacturing", "Retail"]),
    "Nottingham": ("East Midlands", 3, 3, 3, 4, 4, 4, 3, ["Business", "Computing", "Pharmacy"], ["Finance", "Pharma", "Retail"]),
    "Bristol": ("South West", 4, 4, 4, 4, 4, 3, 4, ["Engineering", "Aerospace", "Tech"], ["Aerospace", "Tech", "Creative"]),
    "Liverpool": ("North West", 2, 2, 3, 3, 4, 4, 2, ["Healthcare", "Business", "Maritime"], ["Maritime", "Health", "Creative"]),
    "Southampton": ("South East", 3, 3, 3, 3, 3, 3, 3, ["Engineering", "Maritime", "Healthcare"], ["Maritime", "Marine", "Health"]),
    "Portsmouth": ("South East", 2, 3, 3, 3, 3, 3, 3, ["Engineering", "Computing", "Business"], ["Defence", "Maritime", "Tech"]),
    "Aberdeen": ("Scotland", 3, 3, 3, 3, 3, 3, 3, ["Engineering", "Energy", "Geoscience"], ["Energy", "Oil & Gas", "Engineering"]),
    "Dundee": ("Scotland", 2, 2, 2, 3, 3, 3, 2, ["Life Sciences", "Computing", "Design"], ["Life Sciences", "Games", "Health"]),
    "York": ("Yorkshire and the Humber", 3, 3, 2, 3, 4, 3, 3, ["History", "Computing", "Business"], ["Tourism", "Education", "Rail"]),
    "Durham": ("North East", 3, 3, 2, 3, 3, 3, 3, ["Sciences", "Business", "Law"], ["Education", "Public Sector"]),
    "Oxford": ("South East", 5, 5, 3, 4, 4, 4, 5, ["Sciences", "Research", "Business"], ["Research", "Publishing", "Tech"]),
    "Cambridge": ("East of England", 5, 5, 3, 4, 4, 4, 5, ["Sciences", "Tech", "Research"], ["Tech", "Biotech", "Research"]),
    "Belfast": ("Northern Ireland", 2, 2, 3, 3, 4, 3, 2, ["Computing", "Cyber Security", "Business"], ["Tech", "Cyber", "Finance"]),
    "Swansea": ("Wales", 2, 2, 2, 2, 3, 3, 2, ["Engineering", "Sciences", "Sport"], ["Energy", "Health", "Public Sector"]),
    "Brighton": ("South East", 4, 4, 3, 3, 5, 3, 4, ["Media", "Design", "Tech"], ["Digital", "Creative", "Tourism"]),
}

COST_LABEL = {1: "Low", 2: "Low-medium", 3: "Medium", 4: "Medium-high", 5: "Very high"}
COST_BAND = {1: "£700–£1,000/month", 2: "£800–£1,150/month", 3: "£900–£1,300/month",
             4: "£1,100–£1,600/month", 5: "£1,300–£1,900/month"}
RENT_LABEL = {1: "Low", 2: "Low", 3: "Medium", 4: "High", 5: "High"}
SIGNAL_4 = {1: "Limited", 2: "Limited", 3: "Moderate", 4: "Strong", 5: "Very strong"}
ACCOM_LABEL = {1: "Easy", 2: "Easy", 3: "Moderate", 4: "Hard", 5: "Hard"}

SOURCE_NAME = "Kommunitea curated indicative city signals"
SOURCE_URL = "https://www.gov.uk/student-visa"  # official cost/visa guidance reference


def city_match_score(cost, rent, part_time, grad, student_life, community, accommodation):
    """General indicative city score /100 with the 6 specified components."""
    budget = (5 - cost) / 4 * 25
    pt = part_time / 5 * 20
    career = grad / 5 * 20
    life = student_life / 5 * 15
    accom = (5 - accommodation) / 4 * 10
    comm = community / 5 * 10
    breakdown = {
        "budget": round(budget), "partTime": round(pt), "career": round(career),
        "studentLife": round(life), "accommodation": round(accom), "community": round(comm),
    }
    return min(100, sum(breakdown.values())), breakdown
