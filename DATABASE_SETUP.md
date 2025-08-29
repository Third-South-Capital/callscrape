# Database Setup Guide

This guide explains how to set up and use the Supabase database integration for CallScrape.

## Overview

The database integration provides:
- **Persistent storage** of all scraped opportunities
- **Deduplication** across platforms (same opportunity on multiple sites)
- **Historical tracking** of changes over time
- **Data integrity** with proper validation and normalization
- **Analytics** on organizations, deadlines, and trends

## Quick Start

### 1. Set Up Supabase Project

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → API to get your credentials:
   - Project URL
   - Anon/Public key
   - Service Role key (for write access)

### 2. Configure Environment

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 3. Create Database Schema

Run the SQL migrations in your Supabase SQL editor:

1. Go to SQL Editor in Supabase dashboard
2. Copy and run the schema from `database_schema.md`
3. Or use the migration files if available

### 4. Install Dependencies

```bash
pip install supabase python-dotenv
```

## Usage

### Basic Scraping (No Database)

```bash
# Scrape all platforms to JSON
python3 main.py

# Scrape specific platform
python3 main.py --platforms cafe
```

### With Database Sync

```bash
# Scrape and sync to database
python3 main.py --sync-db

# Scrape specific platforms and sync
python3 main.py --platforms cafe artcall --sync-db

# Sync existing JSON to database (no scraping)
python3 main.py --db-only
```

### Direct Database Operations

```bash
# Sync specific JSON file to database
python3 database.py data/opportunities_20250829_073609.json
```

## Data Flow

1. **Scraping**: Each platform scraper fetches opportunities
2. **Normalization**: Data is standardized to common format
3. **Deduplication**: Similar opportunities are identified
4. **Database Sync**: Normalized data is upserted to Supabase
5. **Integrity Checks**: 
   - Deterministic IDs prevent duplicates
   - Cross-platform matches are tracked
   - Historical changes are logged

## Database Schema

### Main Tables

- **opportunities**: Core opportunity data
  - Deterministic UUID based on source + URL
  - Normalized fields (title, org, deadline, etc.)
  - JSON extras for platform-specific data
  
- **opportunity_sources**: Tracks platform appearances
  - Links opportunities to their source platforms
  - Stores platform-specific IDs and URLs

- **scrape_runs**: Audit trail of scraping sessions
  - Tracks when each platform was scraped
  - Records new/updated counts and errors

- **opportunity_history**: Change tracking
  - Records all changes to opportunities
  - Enables trend analysis

## Data Integrity Features

### Deduplication Logic

The system identifies duplicates using:
1. **Exact URL matches** - Same opportunity URL
2. **Title similarity** - 85%+ similar titles
3. **Organization + Title** - Same org with similar title

Duplicates are merged, keeping the most complete data.

### ID Generation

Each opportunity gets a deterministic UUID:
- Based on platform + unique identifier
- Same opportunity always gets same ID
- Prevents duplicate insertions

### Data Normalization

- **Deadlines**: Parsed to ISO dates for sorting
- **Locations**: Split into city/state components
- **Fees**: Extracted as numeric values
- **Organizations**: Cleaned and standardized

## Monitoring

### Check Data Quality

```sql
-- In Supabase SQL Editor
SELECT 
    source_platform,
    COUNT(*) as total,
    COUNT(CASE WHEN organization IS NOT NULL THEN 1 END) as has_org,
    COUNT(CASE WHEN deadline_parsed IS NOT NULL THEN 1 END) as has_deadline,
    AVG(CASE WHEN organization IS NOT NULL THEN 1 ELSE 0 END) * 100 as org_percentage
FROM opportunities
GROUP BY source_platform;
```

### Find Duplicates

```sql
-- Find cross-platform opportunities
SELECT 
    title,
    organization,
    COUNT(DISTINCT source_platform) as platform_count,
    ARRAY_AGG(DISTINCT source_platform) as platforms
FROM opportunities
GROUP BY title, organization
HAVING COUNT(DISTINCT source_platform) > 1;
```

### Active Opportunities

```sql
-- Current open calls
SELECT * FROM opportunities
WHERE is_active = true
  AND deadline_parsed >= CURRENT_DATE
ORDER BY deadline_parsed ASC;
```

## Troubleshooting

### No Database Connection

If you see "No database connection" messages:
1. Check your `.env` file has correct credentials
2. Verify Supabase project is active
3. Test connection with: `python3 -c "from database import OpportunityDatabase; db = OpportunityDatabase()"`

### Duplicate Warnings

Duplicates are expected and handled:
- System tracks cross-platform appearances
- Alternate URLs are stored
- Most complete data is preserved

### Performance

For large datasets:
- Initial sync may take a few minutes
- Subsequent updates are incremental
- Database indexes optimize common queries

## Daily Workflow

Recommended daily process:

```bash
# Morning: Scrape all platforms and sync
python3 main.py --sync-db

# Or via cron/GitHub Actions
0 6 * * * cd /path/to/callscrape && python3 main.py --sync-db
```

## Security Notes

- **Never commit `.env` file** - It contains secrets
- **Service Role key** gives full database access - keep secure
- **Use Anon key** for read-only operations
- **Enable RLS** (Row Level Security) for production

## Next Steps

1. Set up automated daily scraping (cron or GitHub Actions)
2. Build a frontend to display opportunities
3. Add email alerts for new opportunities
4. Implement advanced duplicate detection
5. Add organization enrichment from external sources