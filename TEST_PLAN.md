# Test Plan for CallScrape Improvements

## Current Status
- **Local scraping**: ~747 opportunities (with Zapplication limited to 20)
- **Supabase database**: 1,287 opportunities (accumulated over time)
- **GUI at GitHub Pages**: Shows all 1,287 from Supabase

## Key Improvements Made

### 1. CaFE Scraper Enhanced ✅
- Now uses Selenium to get REAL platform IDs
- 311 out of 312 opportunities have correct application URLs
- URLs like `https://artist.callforentry.org/festivals_unique_info.php?ID=16019` (real ID)
- Instead of fake sequential IDs (1, 2, 3...)

### 2. Zapplication Scraper Fixed ✅
- Can now scrape ALL 892 events (was limited to 20)
- Added `--zap-limit` parameter for testing
- Full scrape takes ~45 minutes

### 3. Database Sync is Additive ✅
- Uses UPSERT logic (update if exists, insert if new)
- Preserves existing data
- Tracks `times_seen` and `first_seen`
- Won't delete existing records

## Testing Steps

### Step 1: Quick Test (5 minutes)
```bash
# Test with limited data
python3 main.py --platforms cafe artcall --zap-limit 5

# Check results
ls -la data/opportunities_*.json
```

### Step 2: Full Scrape Test (50-60 minutes)
```bash
# Run full scraper (all platforms, all Zapplication events)
./run_full_scrape.sh

# This will get approximately:
# - CaFE: ~312 opportunities (with real IDs)
# - ArtCall: ~164 opportunities  
# - ShowSubmit: ~42 opportunities
# - ArtworkArchive: ~243 opportunities
# - Zapplication: ~892 opportunities
# Total: ~1,650+ opportunities
```

### Step 3: Database Sync Test
```bash
# First, check what would be synced (dry run)
python3 main.py --db-only

# If you have Supabase credentials in .env:
python3 main.py --db-only --sync-db
```

### Step 4: Verify Data Quality
```bash
# Check the data locally
python3 -m http.server 8080
# Open: http://localhost:8080/test_viewer.html

# Verify:
# - CaFE opportunities have real platform IDs
# - All platforms are represented
# - Deadlines are present
# - No major data loss
```

## Important Notes

### Database Safety
- The sync is **ADDITIVE** - it won't delete existing records
- Each opportunity has a deterministic UUID based on source + title
- Duplicates are detected and merged
- Existing data is preserved when new data is empty

### Zapplication Time Warning
- Full Zapplication scrape of 892 events takes ~45 minutes
- Use `--zap-limit 20` for quick tests
- Each event requires a separate page load with Selenium

### CaFE Platform IDs
- We now get the REAL IDs from the live site
- These are required for artists to actually apply
- Without Selenium, the IDs are fake (1, 2, 3...)

## Before Committing to Git

1. ✅ All scrapers working
2. ✅ CaFE has real platform IDs  
3. ✅ Database sync is additive
4. ⏳ Run full scrape to get all ~1,650 opportunities
5. ⏳ Test database sync (need .env credentials)
6. ⏳ Verify GitHub Pages GUI still works

## Commands Summary

```bash
# Quick test (5 min)
python3 main.py --zap-limit 5

# Full scrape (50-60 min)
./run_full_scrape.sh

# Database sync (with .env configured)
python3 main.py --db-only --sync-db

# View locally
python3 -m http.server 8080
open http://localhost:8080/test_viewer.html
```