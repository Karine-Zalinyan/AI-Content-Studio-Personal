"""Default food-YouTube niche profile for AI Content Studio."""

FOOD_NICHE = {
    "name": "Food Entertainment / AI Culinary",
    "audience": "international English-speaking YouTube viewers",
    "primary_formats": [
        "cheap-to-luxury food transformation",
        "one ingredient to multiple recipes",
        "food storytelling",
        "satisfying cooking transformations",
    ],
    "default_duration_seconds": 30,
    "aspect_ratio": "9:16",
    "fps": 30,
    "language": "English",
    "hook_seconds": 2,
    "style": "cinematic food, appetizing macro details, fast visual progression",
    "avoid": [
        "generic recipe tutorial without a hook",
        "repetitive AI slideshow",
        "unrelated topics",
        "unsafe or misleading food claims",
    ],
}


def food_profile_text() -> str:
    """Return a compact profile suitable for an LLM system prompt."""
    return (
        "Niche: AI-first food entertainment for international English-speaking YouTube. "
        "Prioritize cheap-to-luxury transformations, one-ingredient challenges, "
        "food stories, and satisfying cooking transformations. "
        "Default to 30-second vertical 9:16 Shorts. "
        "The first 2 seconds must create a clear visual curiosity gap. "
        "Prefer visual storytelling over talking-head exposition. "
        "Avoid generic recipe tutorials and repetitive AI slideshows."
    )
