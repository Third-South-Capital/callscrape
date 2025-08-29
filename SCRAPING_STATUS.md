# Scraping Status

## Current Progress (Started 9:03 AM)

### Completed Scrapers ✅
- **CaFE**: 312 opportunities (311 with real platform IDs)
- **ArtCall**: 164 opportunities  
- **ShowSubmit**: 42 opportunities
- **ArtworkArchive**: 243 opportunities

### In Progress ⏳
- **Zapplication**: Processing 892 events
  - Started: 9:04 AM
  - Current: 80/892 events (as of 9:08 AM)
  - Rate: ~1 event per 3 seconds
  - Estimated completion: ~9:48 AM

### Expected Total
- **Approximately 1,650+ opportunities** when complete

## Key Improvements in This Run

1. **CaFE Real IDs**: Getting actual platform IDs (e.g., 16019) not fake ones (1,2,3)
2. **Full Zapplication**: All 892 events instead of just 20
3. **Complete Data**: ShowSubmit fetching detail pages for deadlines
4. **Fixed URLs**: ArtworkArchive and ShowSubmit using correct endpoints

## What Happens After Scraping

1. Data saved to `data/opportunities_YYYYMMDD_HHMMSS.json`
2. Duplicates removed (cross-platform deduplication)
3. Ready for Supabase sync (additive, won't delete existing)
4. GitHub Pages GUI will show updated data after sync

## Monitoring Command
```bash
# Check current progress
ps aux | grep python3
ls -la data/opportunities_*.json
```