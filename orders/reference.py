from dataclasses import dataclass


@dataclass(frozen=True)
class CountryInfo:
    name: str
    currency: str


COUNTRIES = {
    "US": CountryInfo("United States", "USD"),
    "GB": CountryInfo("United Kingdom", "GBP"),
    "DE": CountryInfo("Germany", "EUR"),
}


def lookup_country(code):
    if code is None:
        return None
    return COUNTRIES.get(code.strip().upper())
