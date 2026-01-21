"""Exceptions for topic operations."""


class TopicCreationError(Exception):
    """Base exception for topic creation failures."""

    pass


class BusinessDomainNotFoundError(TopicCreationError):
    """Raised when the specified business domain does not exist."""

    def __init__(self, business_domain_id: int):
        self.business_domain_id = business_domain_id
        super().__init__(f"Business domain {business_domain_id} not found")


class CountryNotFoundError(TopicCreationError):
    """Raised when the specified country does not exist."""

    def __init__(self, country_id: int):
        self.country_id = country_id
        super().__init__(f"Country {country_id} not found")
