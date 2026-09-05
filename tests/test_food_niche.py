"""Tests for the default food YouTube niche profile."""

from config.food_niche import FOOD_NICHE, food_profile_text


def test_food_profile_defaults_to_short_form_video():
    assert FOOD_NICHE["default_duration_seconds"] == 30
    assert FOOD_NICHE["aspect_ratio"] == "9:16"
    assert FOOD_NICHE["language"] == "English"


def test_food_profile_has_repeatable_formats():
    assert "cheap-to-luxury food transformation" in FOOD_NICHE["primary_formats"]
    assert "one ingredient to multiple recipes" in FOOD_NICHE["primary_formats"]
    assert "food storytelling" in FOOD_NICHE["primary_formats"]
    assert "AI-first food" in food_profile_text()
