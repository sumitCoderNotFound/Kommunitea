"""Centralised privacy helpers — the single source of truth for who can see/share what.
These are enforced at the API level so private content never leaks via direct calls.
"""
from django.db.models import Q


def can_view_profile(viewer, profile_user):
    """Public profiles are visible to all; private only to the owner or approved followers."""
    if not getattr(profile_user, "is_private", False):
        return True
    if not (viewer and viewer.is_authenticated):
        return False
    if viewer == profile_user:
        return True
    return profile_user.followers.filter(pk=viewer.pk).exists()


def can_view_post(viewer, post):
    """Privacy gate for a single post."""
    if post is None:
        return False
    vis = getattr(post, "visibility", "public")
    if vis == "public":
        return True
    if not (viewer and viewer.is_authenticated):
        return False
    if viewer == post.author:
        return True
    if vis == "followers_only":
        return post.author.followers.filter(pk=viewer.pk).exists()
    if vis == "community_only":
        # visible to members of the post's community (or author)
        community = getattr(post, "community", None)
        if community is None:
            return False
        return community.members.filter(pk=viewer.pk).exists()
    # private -> hidden from others
    return False


def visible_posts_filter(viewer):
    """DB-level Q() for filtering a Post queryset to what `viewer` may see."""
    if viewer and viewer.is_authenticated:
        following_ids = viewer.following.values_list("id", flat=True)
        member_community_ids = viewer.communities.values_list("id", flat=True) if hasattr(viewer, "communities") else []
        return (
            Q(visibility="public")
            | Q(author=viewer)
            | (Q(visibility="followers_only") & Q(author_id__in=list(following_ids)))
            | (Q(visibility="community_only") & Q(community_id__in=list(member_community_ids)))
        )
    return Q(visibility="public")


def can_share_post(viewer, post):
    """A post can be shared/sent only if the viewer can see it and it's public."""
    return can_view_post(viewer, post) and getattr(post, "visibility", "public") == "public"


def can_reshare_post(viewer, post):
    """Reshare requires a public post with resharing allowed."""
    return (
        can_view_post(viewer, post)
        and getattr(post, "visibility", "public") == "public"
        and getattr(post, "allow_reshare", True)
    )


def can_add_post_to_story(viewer, post):
    """Adding to story requires a public post with story-sharing allowed."""
    return (
        can_view_post(viewer, post)
        and getattr(post, "visibility", "public") == "public"
        and getattr(post, "allow_share_to_story", True)
    )
