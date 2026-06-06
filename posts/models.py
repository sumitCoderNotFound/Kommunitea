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
    community = models.ForeignKey("community.Community", on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS_ONLY = "followers_only", "Followers only"
        COMMUNITY_ONLY = "community_only", "Community only"
        PRIVATE = "private", "Private"

    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PUBLIC)
    allow_reshare = models.BooleanField(default=True)
    allow_share_to_story = models.BooleanField(default=True)
    tags = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="tagged_posts", blank=True)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_posts", blank=True)
    saved_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="saved_posts", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author.full_name}: {self.body[:40]}"

    def visible_to(self, user):
        """Privacy gate for a post."""
        if self.visibility == self.Visibility.PUBLIC:
            return True
        if user and user.is_authenticated:
            if user == self.author:
                return True
            if self.visibility == self.Visibility.FOLLOWERS_ONLY:
                return self.author.followers.filter(pk=user.pk).exists()
        return False


class PostReshare(models.Model):
    """A repost of an existing post, optionally with a comment."""
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reshares")
    reshared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reshares")
    comment_text = models.TextField(blank=True)
    visibility = models.CharField(max_length=16, default="public")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("original_post", "reshared_by")

    def __str__(self):
        return f"{self.reshared_by.full_name} reshared {self.original_post_id}"


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
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers only"
        COMMUNITY = "community", "Community only"
        PRIVATE = "private", "Private"

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    image = models.ImageField(upload_to="stories/", blank=True, null=True)
    story_type = models.CharField(max_length=16, default="image")  # image | video | text | shared_post
    original_post = models.ForeignKey("Post", on_delete=models.SET_NULL, null=True, blank=True, related_name="story_shares")
    caption = models.CharField(max_length=200, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    viewed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="viewed_stories", blank=True)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_stories", blank=True)

    class Meta:
        ordering = ["-created_at"]

    def visible_to(self, user):
        """Whether `user` may see this story under its visibility setting."""
        if user and user.is_authenticated and user.pk == self.author_id:
            return True
        if self.visibility == self.Visibility.PUBLIC:
            return True
        if self.visibility == self.Visibility.PRIVATE:
            return False
        if not (user and user.is_authenticated):
            return False
        # followers-only and community-only: visible to approved followers of the author
        return self.author.followers.filter(pk=user.pk).exists()

    def save(self, *args, **kwargs):
        from datetime import timedelta
        from django.utils import timezone
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Story by {self.author.full_name}"
