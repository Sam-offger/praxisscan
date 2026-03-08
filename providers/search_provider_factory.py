import config
from .search_provider_base import BaseSearchProvider

def get_search_provider() -> BaseSearchProvider:
    provider = config.SEARCH_PROVIDER.lower()
    if provider == "duckduckgo":
        from .search_provider_duckduckgo import DuckDuckGoProvider
        return DuckDuckGoProvider()
    elif provider == "serper":
        from .search_provider_serper import SerperProvider
        return SerperProvider()
    elif provider == "jameda":
        from .search_provider_jameda import JamedaProvider
        return JamedaProvider()
    elif provider == "googlemaps":
        from .search_provider_googlemaps import GoogleMapsProvider
        return GoogleMapsProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}")

def get_all_providers() -> list:
    """Gibt alle konfigurierten Provider zurück für Multi-Source Discovery."""
    providers = []
    # Serper immer wenn Key vorhanden
    if config.SERPER_API_KEY:
        from .search_provider_serper import SerperProvider
        providers.append(("serper", SerperProvider()))
    # Jameda immer aktiv (kostenlos)
    from .search_provider_jameda import JamedaProvider
    providers.append(("jameda", JamedaProvider()))
    # Google Maps wenn Key vorhanden
    if config.SERPAPI_API_KEY:
        from .search_provider_googlemaps import GoogleMapsProvider
        providers.append(("googlemaps", GoogleMapsProvider()))
    return providers
