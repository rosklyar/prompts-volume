"""ISO country code to location name mapping with language support."""

from typing import List, Optional
from pydantic import BaseModel, Field


class Language(BaseModel):
    """Language model with ISO 639-1 code."""

    id: int = Field(..., description="Unique language identifier")
    name: str = Field(..., description="Language name in English")
    code: str = Field(..., description="ISO 639-1 language code")


class Country(BaseModel):
    """Country model with ISO code and preferred languages."""

    id: int = Field(..., description="Unique country identifier")
    name: str = Field(..., description="Country name in English")
    code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    preferred_languages: List[Language] = Field(
        default_factory=list, description="List of preferred languages for this country"
    )


# Static list of all 46 supported languages
ALL_LANGUAGES = [
    Language(id=1, name="Albanian", code="sq"),
    Language(id=2, name="Ukrainian", code="uk"),
    Language(id=3, name="Arabic", code="ar"),
    Language(id=4, name="Armenian", code="hy"),
    Language(id=5, name="Azeri", code="az"),
    Language(id=6, name="Bengali", code="bn"),
    Language(id=7, name="Bosnian", code="bs"),
    Language(id=8, name="Bulgarian", code="bg"),
    Language(id=9, name="Chinese (Simplified)", code="zh-CN"),
    Language(id=10, name="Chinese (Traditional)", code="zh-TW"),
    Language(id=11, name="Croatian", code="hr"),
    Language(id=12, name="Czech", code="cs"),
    Language(id=13, name="Danish", code="da"),
    Language(id=14, name="Dutch", code="nl"),
    Language(id=15, name="English", code="en"),
    Language(id=16, name="Estonian", code="et"),
    Language(id=17, name="Finnish", code="fi"),
    Language(id=18, name="French", code="fr"),
    Language(id=19, name="German", code="de"),
    Language(id=20, name="Greek", code="el"),
    Language(id=21, name="Hebrew", code="he"),
    Language(id=22, name="Hindi", code="hi"),
    Language(id=23, name="Hungarian", code="hu"),
    Language(id=24, name="Indonesian", code="id"),
    Language(id=25, name="Italian", code="it"),
    Language(id=26, name="Japanese", code="ja"),
    Language(id=27, name="Korean", code="ko"),
    Language(id=28, name="Latvian", code="lv"),
    Language(id=29, name="Lithuanian", code="lt"),
    Language(id=30, name="Macedonian", code="mk"),
    Language(id=31, name="Malay", code="ms"),
    Language(id=32, name="Norwegian (Bokmål)", code="nb"),
    Language(id=33, name="Polish", code="pl"),
    Language(id=34, name="Portuguese", code="pt"),
    Language(id=35, name="Romanian", code="ro"),
    Language(id=36, name="Russian", code="ru"),
    Language(id=37, name="Serbian", code="sr"),
    Language(id=38, name="Slovak", code="sk"),
    Language(id=39, name="Slovenian", code="sl"),
    Language(id=40, name="Spanish", code="es"),
    Language(id=41, name="Swedish", code="sv"),
    Language(id=42, name="Tagalog", code="tl"),
    Language(id=43, name="Thai", code="th"),
    Language(id=44, name="Turkish", code="tr"),
    Language(id=45, name="Urdu", code="ur"),
    Language(id=46, name="Vietnamese", code="vi"),
]

# Create language lookup dictionary for efficient access
_LANGUAGE_BY_ID = {lang.id: lang for lang in ALL_LANGUAGES}


def _get_langs_by_ids(ids: List[int]) -> List[Language]:
    """Helper function to get language objects by IDs."""
    return [_LANGUAGE_BY_ID[lang_id] for lang_id in ids if lang_id in _LANGUAGE_BY_ID]


# Static list of all 94 countries with Ukraine at id=1
ALL_COUNTRIES = [
    Country(id=1, name="Ukraine", code="UA", preferred_languages=_get_langs_by_ids([2, 36])),
    Country(id=2, name="Albania", code="AL", preferred_languages=_get_langs_by_ids([1])),
    Country(id=3, name="Algeria", code="DZ", preferred_languages=_get_langs_by_ids([18, 3])),
    Country(id=4, name="Angola", code="AO", preferred_languages=_get_langs_by_ids([34])),
    Country(id=5, name="Azerbaijan", code="AZ", preferred_languages=_get_langs_by_ids([5])),
    Country(id=6, name="Argentina", code="AR", preferred_languages=_get_langs_by_ids([40])),
    Country(id=7, name="Australia", code="AU", preferred_languages=_get_langs_by_ids([15])),
    Country(id=8, name="Austria", code="AT", preferred_languages=_get_langs_by_ids([19])),
    Country(id=9, name="Bahrain", code="BH", preferred_languages=_get_langs_by_ids([3])),
    Country(id=10, name="Bangladesh", code="BD", preferred_languages=_get_langs_by_ids([6])),
    Country(id=11, name="Armenia", code="AM", preferred_languages=_get_langs_by_ids([4])),
    Country(id=12, name="Belgium", code="BE", preferred_languages=_get_langs_by_ids([18, 14, 19])),
    Country(id=13, name="Bolivia", code="BO", preferred_languages=_get_langs_by_ids([40])),
    Country(id=14, name="Bosnia and Herzegovina", code="BA", preferred_languages=_get_langs_by_ids([7])),
    Country(id=15, name="Brazil", code="BR", preferred_languages=_get_langs_by_ids([34])),
    Country(id=16, name="Bulgaria", code="BG", preferred_languages=_get_langs_by_ids([8])),
    Country(id=17, name="Myanmar (Burma)", code="MM", preferred_languages=_get_langs_by_ids([15])),
    Country(id=18, name="Cambodia", code="KH", preferred_languages=_get_langs_by_ids([15])),
    Country(id=19, name="Cameroon", code="CM", preferred_languages=_get_langs_by_ids([18])),
    Country(id=20, name="Canada", code="CA", preferred_languages=_get_langs_by_ids([15, 18])),
    Country(id=21, name="Sri Lanka", code="LK", preferred_languages=_get_langs_by_ids([15])),
    Country(id=22, name="Chile", code="CL", preferred_languages=_get_langs_by_ids([40])),
    Country(id=23, name="Taiwan", code="TW", preferred_languages=_get_langs_by_ids([10])),
    Country(id=24, name="Colombia", code="CO", preferred_languages=_get_langs_by_ids([40])),
    Country(id=25, name="Costa Rica", code="CR", preferred_languages=_get_langs_by_ids([40])),
    Country(id=26, name="Croatia", code="HR", preferred_languages=_get_langs_by_ids([11])),
    Country(id=27, name="Cyprus", code="CY", preferred_languages=_get_langs_by_ids([20, 15])),
    Country(id=28, name="Czechia", code="CZ", preferred_languages=_get_langs_by_ids([12])),
    Country(id=29, name="Denmark", code="DK", preferred_languages=_get_langs_by_ids([13])),
    Country(id=30, name="Ecuador", code="EC", preferred_languages=_get_langs_by_ids([40])),
    Country(id=31, name="El Salvador", code="SV", preferred_languages=_get_langs_by_ids([40])),
    Country(id=32, name="Estonia", code="EE", preferred_languages=_get_langs_by_ids([16])),
    Country(id=33, name="Finland", code="FI", preferred_languages=_get_langs_by_ids([17])),
    Country(id=34, name="France", code="FR", preferred_languages=_get_langs_by_ids([18])),
    Country(id=35, name="Germany", code="DE", preferred_languages=_get_langs_by_ids([19])),
    Country(id=36, name="Ghana", code="GH", preferred_languages=_get_langs_by_ids([15])),
    Country(id=37, name="Greece", code="GR", preferred_languages=_get_langs_by_ids([20, 15])),
    Country(id=38, name="Guatemala", code="GT", preferred_languages=_get_langs_by_ids([40])),
    Country(id=39, name="Hong Kong", code="HK", preferred_languages=_get_langs_by_ids([15, 10])),
    Country(id=40, name="Hungary", code="HU", preferred_languages=_get_langs_by_ids([23])),
    Country(id=41, name="India", code="IN", preferred_languages=_get_langs_by_ids([15, 22])),
    Country(id=42, name="Indonesia", code="ID", preferred_languages=_get_langs_by_ids([15, 24])),
    Country(id=43, name="Ireland", code="IE", preferred_languages=_get_langs_by_ids([15])),
    Country(id=44, name="Israel", code="IL", preferred_languages=_get_langs_by_ids([21, 3])),
    Country(id=45, name="Italy", code="IT", preferred_languages=_get_langs_by_ids([25])),
    Country(id=46, name="Cote d'Ivoire", code="CI", preferred_languages=_get_langs_by_ids([18])),
    Country(id=47, name="Japan", code="JP", preferred_languages=_get_langs_by_ids([26])),
    Country(id=48, name="Kazakhstan", code="KZ", preferred_languages=_get_langs_by_ids([36])),
    Country(id=49, name="Jordan", code="JO", preferred_languages=_get_langs_by_ids([3])),
    Country(id=50, name="Kenya", code="KE", preferred_languages=_get_langs_by_ids([15])),
    Country(id=51, name="South Korea", code="KR", preferred_languages=_get_langs_by_ids([27])),
    Country(id=52, name="Latvia", code="LV", preferred_languages=_get_langs_by_ids([28])),
    Country(id=53, name="Lithuania", code="LT", preferred_languages=_get_langs_by_ids([29])),
    Country(id=54, name="Malaysia", code="MY", preferred_languages=_get_langs_by_ids([15, 31])),
    Country(id=55, name="Malta", code="MT", preferred_languages=_get_langs_by_ids([15])),
    Country(id=56, name="Mexico", code="MX", preferred_languages=_get_langs_by_ids([40])),
    Country(id=57, name="Monaco", code="MC", preferred_languages=_get_langs_by_ids([18])),
    Country(id=58, name="Moldova", code="MD", preferred_languages=_get_langs_by_ids([35])),
    Country(id=59, name="Morocco", code="MA", preferred_languages=_get_langs_by_ids([3, 18])),
    Country(id=60, name="Netherlands", code="NL", preferred_languages=_get_langs_by_ids([14])),
    Country(id=61, name="New Zealand", code="NZ", preferred_languages=_get_langs_by_ids([15])),
    Country(id=62, name="Nicaragua", code="NI", preferred_languages=_get_langs_by_ids([40])),
    Country(id=63, name="Nigeria", code="NG", preferred_languages=_get_langs_by_ids([15])),
    Country(id=64, name="Norway", code="NO", preferred_languages=_get_langs_by_ids([32])),
    Country(id=65, name="Pakistan", code="PK", preferred_languages=_get_langs_by_ids([15, 45])),
    Country(id=66, name="Panama", code="PA", preferred_languages=_get_langs_by_ids([40])),
    Country(id=67, name="Paraguay", code="PY", preferred_languages=_get_langs_by_ids([40])),
    Country(id=68, name="Peru", code="PE", preferred_languages=_get_langs_by_ids([40])),
    Country(id=69, name="Philippines", code="PH", preferred_languages=_get_langs_by_ids([15, 42])),
    Country(id=70, name="Poland", code="PL", preferred_languages=_get_langs_by_ids([33])),
    Country(id=71, name="Portugal", code="PT", preferred_languages=_get_langs_by_ids([34])),
    Country(id=72, name="Romania", code="RO", preferred_languages=_get_langs_by_ids([35])),
    Country(id=73, name="Saudi Arabia", code="SA", preferred_languages=_get_langs_by_ids([3])),
    Country(id=74, name="Senegal", code="SN", preferred_languages=_get_langs_by_ids([18])),
    Country(id=75, name="Serbia", code="RS", preferred_languages=_get_langs_by_ids([37])),
    Country(id=76, name="Singapore", code="SG", preferred_languages=_get_langs_by_ids([15, 9])),
    Country(id=77, name="Slovakia", code="SK", preferred_languages=_get_langs_by_ids([38])),
    Country(id=78, name="Vietnam", code="VN", preferred_languages=_get_langs_by_ids([15, 46])),
    Country(id=79, name="Slovenia", code="SI", preferred_languages=_get_langs_by_ids([39])),
    Country(id=80, name="South Africa", code="ZA", preferred_languages=_get_langs_by_ids([15])),
    Country(id=81, name="Spain", code="ES", preferred_languages=_get_langs_by_ids([40])),
    Country(id=82, name="Sweden", code="SE", preferred_languages=_get_langs_by_ids([41])),
    Country(id=83, name="Switzerland", code="CH", preferred_languages=_get_langs_by_ids([19, 18, 25])),
    Country(id=84, name="Thailand", code="TH", preferred_languages=_get_langs_by_ids([43])),
    Country(id=85, name="United Arab Emirates", code="AE", preferred_languages=_get_langs_by_ids([3, 15])),
    Country(id=86, name="Tunisia", code="TN", preferred_languages=_get_langs_by_ids([3])),
    Country(id=87, name="Turkiye", code="TR", preferred_languages=_get_langs_by_ids([44])),
    Country(id=88, name="North Macedonia", code="MK", preferred_languages=_get_langs_by_ids([30])),
    Country(id=89, name="Egypt", code="EG", preferred_languages=_get_langs_by_ids([3, 15])),
    Country(id=90, name="United Kingdom", code="GB", preferred_languages=_get_langs_by_ids([15])),
    Country(id=91, name="United States", code="US", preferred_languages=_get_langs_by_ids([15, 40])),
    Country(id=92, name="Burkina Faso", code="BF", preferred_languages=_get_langs_by_ids([18])),
    Country(id=93, name="Uruguay", code="UY", preferred_languages=_get_langs_by_ids([40])),
    Country(id=94, name="Venezuela", code="VE", preferred_languages=_get_langs_by_ids([40])),
]

# Create country lookup dictionary for efficient access by ISO code
_COUNTRY_BY_CODE = {country.code: country for country in ALL_COUNTRIES}


def get_country_by_code(iso_code: str) -> Optional[Country]:
    """
    Get country object from ISO country code.

    Args:
        iso_code: ISO country code (e.g., 'US', 'GB', 'UA')

    Returns:
        Country object if found, None otherwise
    """
    return _COUNTRY_BY_CODE.get(iso_code.upper())


def get_location_name(iso_code: str) -> Optional[str]:
    """
    Get location name from ISO country code.

    This function provides backward compatibility for existing code.

    Args:
        iso_code: ISO country code (e.g., 'US', 'GB', 'UA')

    Returns:
        Location name if found, None otherwise
    """
    country = get_country_by_code(iso_code)
    return country.name if country else None
