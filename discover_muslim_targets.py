"""
Gezielte Discovery für muslimische Premium-Dental Targets.
60% DE, 25% EU, 15% Global
"""
from dotenv import load_dotenv
load_dotenv(override=True)

import time
import logging
from config_muslim_targets import QUERIES_GERMANY, QUERIES_EUROPE, QUERIES_GLOBAL
from providers.search_provider_serper import SerperProvider
from pipeline import run_discover

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_muslim_targets():
    print("\n🎯 Muslim Target Discovery")
    print("=" * 50)

    stats = {"de": 0, "eu": 0, "global": 0}

    # Deutschland (60%)
    print(f"\n🇩🇪 Deutschland ({len(QUERIES_GERMANY)} Queries)...")
    for query in QUERIES_GERMANY:
        count = run_discover(queries=[query], max_per_query=10)
        stats["de"] += count
        print(f"  ✓ '{query[:50]}' → {count} neue Leads")
        time.sleep(2)

    # Europa (25%)
    print(f"\n🌍 Europa ({len(QUERIES_EUROPE)} Queries)...")
    for query in QUERIES_EUROPE:
        count = run_discover(queries=[query], max_per_query=8)
        stats["eu"] += count
        print(f"  ✓ '{query[:50]}' → {count} neue Leads")
        time.sleep(2)

    # Global (15%)
    print(f"\n🌐 Global ({len(QUERIES_GLOBAL)} Queries)...")
    for query in QUERIES_GLOBAL:
        count = run_discover(queries=[query], max_per_query=5)
        stats["global"] += count
        print(f"  ✓ '{query[:50]}' → {count} neue Leads")
        time.sleep(2)

    total = sum(stats.values())
    print(f"\n✅ Discovery abgeschlossen:")
    print(f"   🇩🇪 Deutschland: {stats['de']} neue Leads")
    print(f"   🌍 Europa:       {stats['eu']} neue Leads")
    print(f"   🌐 Global:       {stats['global']} neue Leads")
    print(f"   📊 Total:        {total} neue Leads")

if __name__ == "__main__":
    run_muslim_targets()
