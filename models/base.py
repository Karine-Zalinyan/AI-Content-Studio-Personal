"""
Shared Pydantic base model with common configuration.
"""

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """All project models inherit from this."""

    model_config = ConfigDict(
        frozen=False,
        populate_by_name=True,
        str_strip_whitespace=True,
    )
