"""Video generation back-ends (text prompt -> .mp4)."""

from .base import VideoGenerator, GenerationError


def get_generator(generator_id: str) -> VideoGenerator:
    """Return a generator instance by its id (from Settings.generator)."""
    if generator_id == "google_flow":
        from .google_flow import GoogleFlowGenerator
        return GoogleFlowGenerator()
    raise GenerationError(f"Unknown generator: {generator_id!r}")
