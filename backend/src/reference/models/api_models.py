"""Pydantic models for reference data API endpoints."""

from pydantic import BaseModel


class BusinessDomainResponse(BaseModel):
    """Business domain response model."""

    id: int
    name: str
    description: str


class BusinessDomainsListResponse(BaseModel):
    """List of business domains response."""

    business_domains: list[BusinessDomainResponse]


class LanguageResponse(BaseModel):
    """Language response model."""

    id: int
    name: str
    code: str


class CountryResponse(BaseModel):
    """Country response model."""

    id: int
    name: str
    iso_code: str
    languages: list[LanguageResponse] = []


class CountriesListResponse(BaseModel):
    """List of countries response."""

    countries: list[CountryResponse]


class TopicResponse(BaseModel):
    """Topic response model with related entity names."""

    id: int
    title: str
    description: str
    business_domain_id: int
    business_domain_name: str
    country_id: int
    country_name: str


class TopicsListResponse(BaseModel):
    """List of topics response."""

    topics: list[TopicResponse]
