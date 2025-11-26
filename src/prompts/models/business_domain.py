"""Business domain enum for company classification."""

from enum import Enum


class BusinessDomain(str, Enum):
    """Supported business domains for prompt generation."""

    E_COMMERCE = "E_COMMERCE"
    NOT_SUPPORTED = "NOT_SUPPORTED"
