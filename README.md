# CallScrape - Art Opportunity Aggregator

A comprehensive web scraping system that aggregates art opportunities from multiple platforms into a unified database.

## Features

- **Multi-Platform Support**: Scrapes opportunities from CaFE, ArtCall, ShowSubmit, ArtworkArchive, and Zapplication
- **Smart Deduplication**: Prevents duplicate entries across platforms using deterministic UUIDs
- **Data Normalization**: Standardizes locations, fees, and dates across different formats
- **Supabase Integration**: Syncs opportunities to cloud database with UPSERT logic
- **Real Platform IDs**: Uses Selenium to get actual CaFE platform IDs for working application links
- **GitHub Pages GUI**: Live web interface at https://third-south-capital.github.io/callscrape/

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all scrapers
python3 main.py

# Run specific platform
python3 main.py --platforms cafe artcall

# Sync to database (requires .env with Supabase credentials)
python3 main.py --db-only --sync-db

# Full scrape with all Zapplication events (takes ~45 minutes)
./run_full_scrape.sh
```

## Architecture

```
scrapers/
  ├── base.py           # Base scraper class with shared functionality
  ├── cafe.py           # CaFE scraper with Selenium for real IDs
  ├── artcall.py        # ArtCall scraper
  ├── showsubmit.py     # ShowSubmit scraper with detail fetching
  ├── artwork_archive.py # ArtworkArchive scraper
  └── zapplication.py   # Zapplication scraper with Selenium

utils/
  ├── state_mapper.py      # Maps numeric state codes to names
  ├── location_normalizer.py # Normalizes locations across platforms
  └── fee_normalizer.py    # Standardizes fee formats

database.py  # Supabase integration with deduplication
main.py      # Main orchestrator
```

## Data Quality Features

- **Location Normalization**: Converts "Tucson, 3" → "Tucson, AZ"
- **Fee Standardization**: Converts "15.00" → "$15", "Free to Enter" → "Free"
- **Deadline Parsing**: Ensures consistent YYYY-MM-DD format
- **Cross-Platform Deduplication**: Identifies same opportunity across multiple platforms

## Environment Setup

Create a `.env` file with your Supabase credentials:

```env
SUPABASE_URL=your_project_url
SUPABASE_SERVICE_KEY=your_service_key
```

## Performance

- **CaFE**: ~2 minutes (312 opportunities with real platform IDs)
- **ArtCall**: ~30 seconds (164 opportunities)
- **ShowSubmit**: ~20 seconds (42 opportunities with detail pages)
- **ArtworkArchive**: ~1 minute (243 opportunities)
- **Zapplication**: ~45 minutes for full scrape (892 events)

Total: ~1,600+ opportunities per full scrape

## Database

The system uses Supabase with UPSERT logic:
- Updates existing opportunities (increments `times_seen`)
- Inserts new opportunities
- Preserves historical data
- No data loss on sync

## License

Private repository - Third South Capital