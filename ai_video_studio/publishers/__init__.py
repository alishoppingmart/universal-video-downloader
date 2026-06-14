"""Publishers upload a finished .mp4 to a social platform."""

from .base import Publisher, PublishError, PublishResult


def get_publisher(platform: str) -> Publisher:
    if platform == "youtube":
        from .youtube import YouTubePublisher
        return YouTubePublisher()
    if platform == "tiktok":
        from .tiktok import TikTokPublisher
        return TikTokPublisher()
    raise PublishError(f"Unknown platform: {platform!r}")
