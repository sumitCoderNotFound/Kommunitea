"""Curated Study Match reference data.

Phase 1 is UK-focused; Phase 3 country data is included for comparison.
NOTE: figures here are *bands/relative signals*, never authoritative quotes.
Always defer to the official links + disclaimers. Real fees/rankings/visa rules
arrive via the Phase 2 data providers.
"""

# Levels for bands: 1=low, 2=below avg, 3=avg, 4=high, 5=very high
COUNTRIES = {
    "UK": {
        "name": "United Kingdom",
        "tuition_band": 4, "living_band": 4, "part_time": "Up to 20 hrs/week in term",
        "post_study": "Graduate Route — 2 years (3 for PhD)", "post_study_strength": 4,
        "job_market": 4, "visa_difficulty": 2, "settlement": "Possible via Skilled Worker → ILR (5 yrs)",
        "language_barrier": 1, "community": 5,
        "best_for": ["Computer Science", "Data Science", "Business Analytics", "Public Health", "Finance"],
        "official": "https://www.gov.uk/student-visa",
        "summary": "Strong graduate route and large Indian/international community; lower cost outside London.",
    },
    "Canada": {
        "name": "Canada", "tuition_band": 3, "living_band": 3, "part_time": "Up to 24 hrs/week (rules change)",
        "post_study": "Post-Graduation Work Permit — up to 3 years", "post_study_strength": 5,
        "job_market": 4, "visa_difficulty": 2, "settlement": "Strong PR pathway (Express Entry)",
        "language_barrier": 1, "community": 5,
        "best_for": ["Computer Science", "Data Science", "Engineering", "Healthcare Management"],
        "official": "https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "summary": "Clear PR pathway and strong post-study work; living costs vary by province.",
    },
    "Germany": {
        "name": "Germany", "tuition_band": 1, "living_band": 3, "part_time": "120 full / 240 half days per year",
        "post_study": "18-month job-seeker residence permit", "post_study_strength": 4,
        "job_market": 4, "visa_difficulty": 2, "settlement": "EU Blue Card → PR",
        "language_barrier": 3, "community": 3,
        "best_for": ["Engineering", "Computer Science", "Data Science", "Supply Chain"],
        "official": "https://www.make-it-in-germany.com/en/",
        "summary": "Very low/no tuition at public universities; German helps for jobs and daily life.",
    },
    "Australia": {
        "name": "Australia", "tuition_band": 4, "living_band": 5, "part_time": "Up to 48 hrs/fortnight",
        "post_study": "Temporary Graduate visa (485) — 2-4 years", "post_study_strength": 4,
        "job_market": 4, "visa_difficulty": 3, "settlement": "Points-based PR pathway",
        "language_barrier": 1, "community": 4,
        "best_for": ["Nursing / Healthcare", "Engineering", "Business Analytics", "Hospitality"],
        "official": "https://immi.homeaffairs.gov.au/",
        "summary": "Strong student support and PR options; high living costs, especially in big cities.",
    },
    "Ireland": {
        "name": "Ireland", "tuition_band": 3, "living_band": 4, "part_time": "Up to 20 hrs/week in term",
        "post_study": "Third Level Graduate Programme — up to 2 years", "post_study_strength": 3,
        "job_market": 4, "visa_difficulty": 2, "settlement": "Critical Skills route → residency",
        "language_barrier": 1, "community": 3,
        "best_for": ["Computer Science", "Data Science", "Finance", "Pharma/Public Health"],
        "official": "https://www.irishimmigration.ie/",
        "summary": "Major tech/pharma hub (Dublin); accommodation is tight and pricey.",
    },
    "USA": {
        "name": "United States", "tuition_band": 5, "living_band": 5, "part_time": "On-campus only (limited)",
        "post_study": "OPT 12 months (+24 STEM extension)", "post_study_strength": 4,
        "job_market": 5, "visa_difficulty": 4, "settlement": "Employer-sponsored (H-1B lottery) — uncertain",
        "language_barrier": 1, "community": 5,
        "best_for": ["Computer Science", "Artificial Intelligence", "Data Science", "Finance"],
        "official": "https://travel.state.gov/content/travel/en/us-visas/study.html",
        "summary": "Top research and salaries, especially STEM/AI; highest cost and visa uncertainty.",
    },
    "New Zealand": {
        "name": "New Zealand", "tuition_band": 3, "living_band": 4, "part_time": "Up to 20 hrs/week in term",
        "post_study": "Post-study work visa — up to 3 years", "post_study_strength": 3,
        "job_market": 3, "visa_difficulty": 2, "settlement": "Skilled Migrant residence pathway",
        "language_barrier": 1, "community": 2,
        "best_for": ["Agriculture/Environment", "Hospitality", "Engineering", "Healthcare Management"],
        "official": "https://www.immigration.govt.nz/",
        "summary": "Relaxed lifestyle and decent post-study work; smaller job market and community.",
    },
}

# UK cities — relative bands + signals (Phase 1)
UK_CITIES = {
    "London": {"cost": 5, "student_life": 5, "part_time": 5, "grad_market": 5, "accommodation_difficulty": 5,
               "community": 5, "best_for": "Finance, tech, global networking", "universities": ["UCL", "King's College London", "Imperial College London", "Queen Mary"]},
    "Manchester": {"cost": 3, "student_life": 5, "part_time": 4, "grad_market": 4, "accommodation_difficulty": 3,
                   "community": 5, "best_for": "Tech, media, big student city", "universities": ["University of Manchester", "Manchester Metropolitan"]},
    "Birmingham": {"cost": 3, "student_life": 4, "part_time": 4, "grad_market": 4, "accommodation_difficulty": 3,
                   "community": 5, "best_for": "Business, engineering, central UK", "universities": ["University of Birmingham", "Aston University", "Birmingham City"]},
    "Newcastle": {"cost": 2, "student_life": 4, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                  "community": 4, "best_for": "Affordable, friendly student city", "universities": ["Newcastle University", "Northumbria University"]},
    "Leeds": {"cost": 3, "student_life": 5, "part_time": 4, "grad_market": 4, "accommodation_difficulty": 3,
              "community": 4, "best_for": "Finance, big nightlife, student hub", "universities": ["University of Leeds", "Leeds Beckett"]},
    "Sheffield": {"cost": 2, "student_life": 4, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                  "community": 4, "best_for": "Affordable, engineering, green city", "universities": ["University of Sheffield", "Sheffield Hallam"]},
    "Glasgow": {"cost": 2, "student_life": 5, "part_time": 3, "grad_market": 4, "accommodation_difficulty": 3,
                "community": 4, "best_for": "Affordable Scotland, strong unis", "universities": ["University of Glasgow", "Strathclyde", "Glasgow Caledonian"]},
    "Edinburgh": {"cost": 4, "student_life": 5, "part_time": 4, "grad_market": 4, "accommodation_difficulty": 4,
                  "community": 4, "best_for": "Finance, tech, beautiful capital", "universities": ["University of Edinburgh", "Heriot-Watt", "Edinburgh Napier"]},
    "Cardiff": {"cost": 2, "student_life": 4, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                "community": 3, "best_for": "Affordable Wales capital", "universities": ["Cardiff University", "Cardiff Metropolitan"]},
    "Coventry": {"cost": 2, "student_life": 4, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                 "community": 5, "best_for": "Very affordable, huge intl community", "universities": ["University of Warwick", "Coventry University"]},
    "Leicester": {"cost": 2, "student_life": 3, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                  "community": 5, "best_for": "Affordable, diverse, central", "universities": ["University of Leicester", "De Montfort University"]},
    "Nottingham": {"cost": 2, "student_life": 4, "part_time": 3, "grad_market": 3, "accommodation_difficulty": 2,
                   "community": 4, "best_for": "Affordable, two strong unis", "universities": ["University of Nottingham", "Nottingham Trent"]},
}

# Subjects / courses (Phase 1)
COURSES = {
    "Computer Science": {
        "category": "tech", "background": ["computer science", "it", "engineering", "maths"],
        "skills": ["Programming", "Data structures", "Cloud", "System design"],
        "roles": ["Software Engineer", "Backend Developer", "DevOps Engineer"],
        "job_signal": 5, "sponsor_likely": 4,
        "cities": ["London", "Manchester", "Edinburgh", "Bristol"],
        "communities": ["Software Engineers UK", "UK Starter Guide"],
    },
    "Data Science": {
        "category": "tech", "background": ["computer science", "statistics", "maths", "engineering", "economics"],
        "skills": ["Python", "ML", "SQL", "Statistics", "Visualisation"],
        "roles": ["Data Scientist", "ML Engineer", "Data Analyst"],
        "job_signal": 5, "sponsor_likely": 4, "cities": ["London", "Manchester", "Edinburgh"],
        "communities": ["Software Engineers UK"],
    },
    "Artificial Intelligence": {
        "category": "tech", "background": ["computer science", "maths", "engineering"],
        "skills": ["Deep learning", "Python", "Maths", "Research"],
        "roles": ["ML Engineer", "AI Researcher", "Data Scientist"],
        "job_signal": 5, "sponsor_likely": 4, "cities": ["London", "Edinburgh", "Cambridge"],
        "communities": ["Software Engineers UK"],
    },
    "Business Analytics": {
        "category": "business", "background": ["business", "commerce", "economics", "engineering", "maths"],
        "skills": ["SQL", "Excel", "Power BI", "Statistics", "Communication"],
        "roles": ["Business Analyst", "Data Analyst", "Product Analyst"],
        "job_signal": 4, "sponsor_likely": 3, "cities": ["London", "Manchester", "Birmingham"],
        "communities": ["UK Starter Guide"],
    },
    "Cyber Security": {
        "category": "tech", "background": ["computer science", "it", "engineering"],
        "skills": ["Networking", "Security", "Linux", "Risk"],
        "roles": ["Security Analyst", "SOC Analyst", "Security Engineer"],
        "job_signal": 4, "sponsor_likely": 3, "cities": ["London", "Manchester", "Bristol"],
        "communities": ["Software Engineers UK"],
    },
    "Project Management": {
        "category": "business", "background": ["business", "engineering", "any"],
        "skills": ["Agile", "Stakeholder management", "Planning"],
        "roles": ["Project Coordinator", "Project Manager", "Delivery Lead"],
        "job_signal": 3, "sponsor_likely": 2, "cities": ["London", "Birmingham", "Leeds"],
        "communities": ["UK Starter Guide"],
    },
    "Public Health": {
        "category": "health", "background": ["medicine", "life sciences", "nursing", "biology"],
        "skills": ["Epidemiology", "Data", "Policy", "Research"],
        "roles": ["Public Health Officer", "Research Associate", "Health Analyst"],
        "job_signal": 3, "sponsor_likely": 3, "cities": ["London", "Sheffield", "Glasgow"],
        "communities": ["UK Starter Guide"],
    },
    "Healthcare Management": {
        "category": "health", "background": ["health", "business", "nursing", "life sciences"],
        "skills": ["Operations", "Health systems", "Finance"],
        "roles": ["Healthcare Administrator", "Operations Manager"],
        "job_signal": 3, "sponsor_likely": 2, "cities": ["London", "Birmingham", "Leeds"],
        "communities": ["UK Starter Guide"],
    },
    "Engineering": {
        "category": "engineering", "background": ["engineering", "physics", "maths"],
        "skills": ["CAD", "Analysis", "Project work", "Maths"],
        "roles": ["Graduate Engineer", "Design Engineer", "Project Engineer"],
        "job_signal": 4, "sponsor_likely": 3, "cities": ["Sheffield", "Manchester", "Birmingham"],
        "communities": ["UK Starter Guide"],
    },
    "Finance": {
        "category": "business", "background": ["finance", "economics", "commerce", "maths", "business"],
        "skills": ["Financial modelling", "Excel", "Accounting", "Analysis"],
        "roles": ["Financial Analyst", "Risk Analyst", "Investment Analyst"],
        "job_signal": 4, "sponsor_likely": 3, "cities": ["London", "Edinburgh", "Leeds"],
        "communities": ["UK Starter Guide"],
    },
    "Marketing": {
        "category": "business", "background": ["marketing", "business", "communications", "any"],
        "skills": ["Digital marketing", "Analytics", "Content", "SEO"],
        "roles": ["Marketing Executive", "Digital Marketer", "Brand Analyst"],
        "job_signal": 3, "sponsor_likely": 2, "cities": ["London", "Manchester", "Leeds"],
        "communities": ["UK Starter Guide"],
    },
    "Supply Chain": {
        "category": "business", "background": ["business", "engineering", "operations"],
        "skills": ["Logistics", "Analytics", "Operations", "ERP"],
        "roles": ["Supply Chain Analyst", "Logistics Coordinator"],
        "job_signal": 3, "sponsor_likely": 3, "cities": ["Birmingham", "Manchester", "Coventry"],
        "communities": ["UK Starter Guide"],
    },
    "Hospitality": {
        "category": "service", "background": ["hospitality", "business", "any"],
        "skills": ["Operations", "Customer service", "Management"],
        "roles": ["Hospitality Manager", "Operations Supervisor"],
        "job_signal": 2, "sponsor_likely": 2, "cities": ["London", "Edinburgh", "Manchester"],
        "communities": ["UK Starter Guide"],
    },
    "Nursing / Healthcare": {
        "category": "health", "background": ["nursing", "health", "life sciences"],
        "skills": ["Clinical skills", "Patient care", "NMC registration"],
        "roles": ["Registered Nurse", "Healthcare Assistant"],
        "job_signal": 5, "sponsor_likely": 5, "cities": ["London", "Birmingham", "Leeds"],
        "communities": ["UK Starter Guide"],
    },
}

DISCLAIMERS = {
    "study": "Study Match provides guidance to help you research options. It does not guarantee admission, visa approval, scholarships or jobs.",
    "visa": "Visa information is general guidance only. Always check GOV.UK or speak to a qualified immigration adviser.",
    "job": "Job market information is based on available data and does not guarantee employment or sponsorship.",
    "university": "Always confirm course details, fees, entry requirements and deadlines from the official university website.",
}

OFFICIAL_SOURCES = [
    {"name": "GOV.UK Student visa", "url": "https://www.gov.uk/student-visa", "type": "visa"},
    {"name": "GOV.UK Graduate visa", "url": "https://www.gov.uk/graduate-visa", "type": "visa"},
    {"name": "UCAS", "url": "https://www.ucas.com/", "type": "applications"},
    {"name": "Discover Uni", "url": "https://discoveruni.gov.uk/", "type": "course_data"},
    {"name": "UKCISA", "url": "https://www.ukcisa.org.uk/", "type": "guidance"},
    {"name": "British Council Study UK", "url": "https://study-uk.britishcouncil.org/", "type": "guidance"},
    {"name": "GOV.UK Register of licensed sponsors", "url": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers", "type": "sponsor"},
]
