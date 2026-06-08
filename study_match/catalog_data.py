"""Factual seed data for the UK university catalog.

Only verifiable facts: official name, city, region, country, website and Russell
Group membership (a public, stable list). No fees, rankings or sponsor claims are
invented here — those are filled by sync jobs / admin verification.
"""

# The 24 Russell Group universities (public membership list).
RUSSELL_GROUP = [
    ("University of Birmingham", "Birmingham", "West Midlands", "https://www.birmingham.ac.uk"),
    ("University of Bristol", "Bristol", "South West", "https://www.bristol.ac.uk"),
    ("University of Cambridge", "Cambridge", "East of England", "https://www.cam.ac.uk"),
    ("Cardiff University", "Cardiff", "Wales", "https://www.cardiff.ac.uk"),
    ("Durham University", "Durham", "North East", "https://www.durham.ac.uk"),
    ("University of Edinburgh", "Edinburgh", "Scotland", "https://www.ed.ac.uk"),
    ("University of Exeter", "Exeter", "South West", "https://www.exeter.ac.uk"),
    ("University of Glasgow", "Glasgow", "Scotland", "https://www.gla.ac.uk"),
    ("Imperial College London", "London", "London", "https://www.imperial.ac.uk"),
    ("King's College London", "London", "London", "https://www.kcl.ac.uk"),
    ("University of Leeds", "Leeds", "Yorkshire and the Humber", "https://www.leeds.ac.uk"),
    ("University of Liverpool", "Liverpool", "North West", "https://www.liverpool.ac.uk"),
    ("London School of Economics and Political Science", "London", "London", "https://www.lse.ac.uk"),
    ("University of Manchester", "Manchester", "North West", "https://www.manchester.ac.uk"),
    ("Newcastle University", "Newcastle upon Tyne", "North East", "https://www.ncl.ac.uk"),
    ("University of Nottingham", "Nottingham", "East Midlands", "https://www.nottingham.ac.uk"),
    ("University of Oxford", "Oxford", "South East", "https://www.ox.ac.uk"),
    ("Queen Mary University of London", "London", "London", "https://www.qmul.ac.uk"),
    ("Queen's University Belfast", "Belfast", "Northern Ireland", "https://www.qub.ac.uk"),
    ("University of Sheffield", "Sheffield", "Yorkshire and the Humber", "https://www.sheffield.ac.uk"),
    ("University of Southampton", "Southampton", "South East", "https://www.southampton.ac.uk"),
    ("University College London", "London", "London", "https://www.ucl.ac.uk"),
    ("University of Warwick", "Coventry", "West Midlands", "https://www.warwick.ac.uk"),
    ("University of York", "York", "Yorkshire and the Humber", "https://www.york.ac.uk"),
]

# Other large, internationally popular UK universities (facts only; not Russell Group).
OTHER_UNIVERSITIES = [
    ("Coventry University", "Coventry", "West Midlands", "https://www.coventry.ac.uk"),
    ("Northumbria University", "Newcastle upon Tyne", "North East", "https://www.northumbria.ac.uk"),
    ("University of Hertfordshire", "Hatfield", "East of England", "https://www.herts.ac.uk"),
    ("University of Greenwich", "London", "London", "https://www.gre.ac.uk"),
    ("University of East London", "London", "London", "https://www.uel.ac.uk"),
    ("De Montfort University", "Leicester", "East Midlands", "https://www.dmu.ac.uk"),
    ("Sheffield Hallam University", "Sheffield", "Yorkshire and the Humber", "https://www.shu.ac.uk"),
    ("Manchester Metropolitan University", "Manchester", "North West", "https://www.mmu.ac.uk"),
    ("Birmingham City University", "Birmingham", "West Midlands", "https://www.bcu.ac.uk"),
    ("University of Portsmouth", "Portsmouth", "South East", "https://www.port.ac.uk"),
    ("Aston University", "Birmingham", "West Midlands", "https://www.aston.ac.uk"),
    ("Nottingham Trent University", "Nottingham", "East Midlands", "https://www.ntu.ac.uk"),
    ("University of Strathclyde", "Glasgow", "Scotland", "https://www.strath.ac.uk"),
    ("Heriot-Watt University", "Edinburgh", "Scotland", "https://www.hw.ac.uk"),
    ("University of Leicester", "Leicester", "East Midlands", "https://www.le.ac.uk"),
    ("Ulster University", "Belfast", "Northern Ireland", "https://www.ulster.ac.uk"),
]

OFFICIAL_DATA_SOURCES = [
    {"source_name": "GOV.UK Register of student sponsors", "source_type": "ukvi_sponsors", "update_frequency": "weekly",
     "source_url": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-students"},
    {"source_name": "Russell Group", "source_type": "russell_group", "update_frequency": "rarely",
     "source_url": "https://russellgroup.ac.uk/about/our-universities/"},
    {"source_name": "UK Register of Learning Providers (UKRLP)", "source_type": "providers", "update_frequency": "monthly",
     "source_url": "https://www.ukrlp.co.uk/"},
    {"source_name": "Discover Uni", "source_type": "course_data", "update_frequency": "annually",
     "source_url": "https://discoveruni.gov.uk/"},
    {"source_name": "UCAS", "source_type": "applications", "update_frequency": "annually",
     "source_url": "https://www.ucas.com/"},
    {"source_name": "British Council Study UK", "source_type": "guidance", "update_frequency": "annually",
     "source_url": "https://study-uk.britishcouncil.org/"},
]
