"""Seed (or clear) safe demo/starter data for launch testing.

Usage:
    python manage.py seed_demo            # create demo data (idempotent)
    python manage.py seed_demo --clear    # remove all demo data

All demo content is tagged so it can be removed cleanly:
  - demo users use the @kommunitea.dev domain
  - demo communities/events are created_by a demo user
  - demo jobs use posted_by == DEMO_TAG
  - demo sponsor companies are matched by name (DEMO_SPONSORS)

It never touches real user data.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from community.models import Community, CommunityEvent
from posts.models import Post
from jobs.models import Job, SponsorCompany
from scheduler.models import JobApplication

DEMO_DOMAIN = "@kommunitea.dev"
DEMO_TAG = "Kommunitea Demo"
DEMO_PASSWORD = "demo12345"

DEMO_USERS = [
    {
        "email": "simon.demo@kommunitea.dev", "full_name": "Simon Demo", "user_type": "student",
        "city": "Newcastle", "university": "Northumbria University", "course": "MSc Computer Science",
        "bio": "MSc student exploring grad roles in the North East.",
        "skills": ["Python", "React", "SQL"], "interests": ["Tech", "Career"],
        "looking_for": ["jobs", "networking"],
    },
    {
        "email": "priya.demo@kommunitea.dev", "full_name": "Priya Demo", "user_type": "job_seeker",
        "city": "London", "target_role": "Data Analyst", "experience_level": "Entry level",
        "bio": "Recent grad looking for visa-sponsored data roles.",
        "skills": ["Python", "Power BI", "Excel"], "interests": ["Data", "Finance"],
        "looking_for": ["jobs", "referrals"],
    },
    {
        "email": "recruiter.demo@kommunitea.dev", "full_name": "Riya Recruiter", "user_type": "recruiter",
        "city": "Manchester", "company": "Demo Talent Partners", "job_title": "Talent Partner",
        "industry": "Recruitment", "hiring_for": "Graduate tech roles",
        "bio": "Connecting UK graduates with sponsor-friendly employers.",
        "open_to_referrals": True,
    },
]

DEMO_COMMUNITIES = [
    ("Northumbria University", "university", "Students & alumni of Northumbria University."),
    ("UK Tech Careers", "technology", "Jobs, referrals and advice for tech roles in the UK."),
    ("Newcomers to the UK", "other", "Settling-in help: housing, banking, visas and friends."),
    ("Visa & Sponsorship Help", "jobs", "Sharing sponsor-friendly employers and visa tips."),
]

DEMO_JOBS = [
    ("Graduate Data Analyst", "Northbridge Analytics", "London", "graduate", True, "£30,000–£35,000", "entry",
     "SQL, Python, Power BI", "Join our graduate analytics scheme. Visa sponsorship available."),
    ("Junior Software Engineer", "Tyne Software", "Newcastle", "full_time", True, "£32,000", "junior",
     "JavaScript, React, Node", "Build products with a friendly team. Sponsorship considered."),
    ("Marketing Intern", "BrightReach", "Manchester", "internship", False, "£24,000 pro-rata", "entry",
     "Content, Social media", "6-month marketing internship."),
]

DEMO_SPONSORS = [
    ("Northbridge Analytics", "Technology", "https://example.com/careers", "confirmed"),
    ("Tyne Software", "Technology", "https://example.com/jobs", "likely"),
    ("Global Health NHS Trust", "Healthcare", "https://example.com/nhs", "confirmed"),
]


class Command(BaseCommand):
    help = "Seed or clear demo/starter data (demo emails only)."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove all demo data instead of creating it.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            return self._clear()
        self._seed()

    # ------------------------------------------------------------------ #
    def _seed(self):
        users = {}
        for spec in DEMO_USERS:
            email = spec["email"]
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(email=email, password=DEMO_PASSWORD, full_name=spec["full_name"])
            for field, value in spec.items():
                if field in ("email", "full_name"):
                    continue
                setattr(user, field, value)
            user.is_onboarded = True
            user.save()
            users[email] = user
        self.stdout.write(self.style.SUCCESS(f"✓ {len(users)} demo users"))

        simon = users["simon.demo@kommunitea.dev"]
        priya = users["priya.demo@kommunitea.dev"]

        communities = {}
        for name, category, desc in DEMO_COMMUNITIES:
            c, _ = Community.objects.get_or_create(
                name=name, defaults={"category": category, "description": desc, "created_by": simon})
            c.members.add(simon, priya)
            communities[name] = c
        self.stdout.write(self.style.SUCCESS(f"✓ {len(communities)} demo communities"))

        # Sample discussions (community posts)
        post_count = 0
        discussions = [
            (simon, "UK Tech Careers", "Anyone interviewed at a sponsor-friendly startup recently? Tips welcome!", "tech"),
            (priya, "Visa & Sponsorship Help", "Sharing my list of confirmed sponsors for data roles. DM me!", "visa_psw"),
            (simon, "Northumbria University", "Study group forming for the data module — who's in?", "university_life"),
        ]
        for author, comm_name, body, category in discussions:
            _, created = Post.objects.get_or_create(
                author=author, community=communities[comm_name], body=body,
                defaults={"category": category})
            post_count += 1 if created else 0
        self.stdout.write(self.style.SUCCESS(f"✓ {post_count} sample discussions"))

        # Standalone feed posts
        for author, body, category in [
            (simon, "Just joined Kommunitea — excited to meet other UK students!", "university_life"),
            (priya, "Applied to 3 graduate roles today. Momentum!", "success_stories"),
        ]:
            Post.objects.get_or_create(author=author, body=body, community=None, defaults={"category": category})

        # Jobs
        job_objs = {}
        for title, company, location, jtype, visa, salary, exp, skills, desc in DEMO_JOBS:
            j, _ = Job.objects.get_or_create(
                title=title, company=company,
                defaults={"location": location, "job_type": jtype, "visa_sponsorship": visa,
                          "salary_range": salary, "experience_level": exp, "skills": skills,
                          "description": desc, "apply_url": "https://example.com/apply",
                          "posted_by": DEMO_TAG, "is_active": True})
            job_objs[title] = j
        self.stdout.write(self.style.SUCCESS(f"✓ {len(job_objs)} demo jobs"))

        # Sponsor companies
        sponsor_count = 0
        for name, industry, url, confidence in DEMO_SPONSORS:
            _, created = SponsorCompany.objects.get_or_create(
                name=name, defaults={"industry": industry, "careers_url": url, "sponsorship_confidence": confidence})
            sponsor_count += 1 if created else 0
        self.stdout.write(self.style.SUCCESS(f"✓ {sponsor_count} demo sponsor companies"))

        # Community event
        CommunityEvent.objects.get_or_create(
            community=communities["UK Tech Careers"], title="Sponsor-friendly employers Q&A",
            defaults={"location": "Online", "starts_at": timezone.now() + timedelta(days=7),
                      "created_by": simon, "description": "Live Q&A with recruiters who sponsor visas."})

        # Sample application tasks for Priya (saved / applied / interview)
        for title, status in [("Graduate Data Analyst", "saved"),
                              ("Junior Software Engineer", "applied"),
                              ("Marketing Intern", "interview")]:
            job = job_objs[title]
            JobApplication.objects.get_or_create(
                user=priya, company=job.company, role_title=job.title,
                defaults={"job": job, "status": status, "source": "Job board",
                          "job_link": "https://example.com/apply"})
        self.stdout.write(self.style.SUCCESS("✓ sample application tracker entries"))

        self.stdout.write(self.style.SUCCESS("\nDemo data ready. Log in with any *.demo@kommunitea.dev / "
                                             f"password '{DEMO_PASSWORD}'."))

    # ------------------------------------------------------------------ #
    def _clear(self):
        events = CommunityEvent.objects.filter(created_by__email__endswith=DEMO_DOMAIN)
        ne = events.count(); events.delete()
        comms = Community.objects.filter(created_by__email__endswith=DEMO_DOMAIN)
        nc = comms.count(); comms.delete()
        jobs = Job.objects.filter(posted_by=DEMO_TAG)
        nj = jobs.count(); jobs.delete()
        sponsors = SponsorCompany.objects.filter(name__in=[s[0] for s in DEMO_SPONSORS])
        nsp = sponsors.count(); sponsors.delete()
        # Deleting demo users cascades their posts, applications and reshares.
        usrs = User.objects.filter(email__endswith=DEMO_DOMAIN)
        nu = usrs.count(); usrs.delete()
        self.stdout.write(self.style.WARNING(
            f"Cleared demo data: {nu} users, {nc} communities, {nj} jobs, {nsp} sponsors, {ne} events "
            "(posts & applications cascaded)."))
