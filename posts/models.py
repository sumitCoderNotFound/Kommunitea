"""Community posts, comments, likes and saves."""
from django.conf import settings
from django.db import models


class Post(models.Model):
    class Category(models.TextChoices):
        JOBS = "jobs", "Jobs"
        INTERNSHIPS = "internships", "Internships"
        ACCOMMODATION = "accommodation", "Accommodation"
        VISA_PSW = "visa_psw", "Visa & PSW"
        UNIVERSITY_LIFE = "university_life", "University Life"
        EVENTS = "events", "Events"
        TECH = "tech", "Tech Discussions"
        COLLABORATION = "collaboration", "Project Collaboration"
        SUCCESS_STORIES = "success_stories", "Success Stories"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField()
    image = models.ImageField(upload_to="posts/", blank=True, null=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.UNIVERSITY_LIFE)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)
    saved_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="saved_posts", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.full_name}: {self.body[:40]}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.full_name}"


class Story(models.Model):
    """Instagram-style story: an image that expires after 24 hours."""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    image = models.ImageField(upload_to="stories/")
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    viewed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="viewed_stories", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        from datetime import timedelta
        from django.utils import timezone
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Story by {self.author.full_name}"
