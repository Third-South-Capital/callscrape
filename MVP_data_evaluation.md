# MVP Data Evaluation

## Current Data Quality

From **759 total opportunities** scraped:

### ✅ What's Working (MVP Fields)

| Field | CaFE | ArtCall | ShowSubmit | ArtworkArchive |
|-------|------|---------|------------|----------------|
| **Title** | 100% | 100% | 100% | 100% |
| **URL** | 100% | 100% | 100% | 100% |
| **Deadline** | 100% | 100% | 100%* | 100% |
| **Organization** | 100% | 100% | 100% | **0%** |

*ShowSubmit deadlines lack year ("August 29th" not "August 29th, 2025")

### 🔧 Issues to Fix for MVP

1. **ShowSubmit Deadlines** - Missing year
   - Current: "August 29th"
   - Solution: Fetch individual pages for complete dates

2. **ArtworkArchive Organizations** - Completely missing
   - Current: 0/249 have organization
   - Solution: Extract from individual pages

3. **Deduplication** - 32 opportunities on multiple platforms
   - Example: "REFINED: The Foreseeable Future" on CaFE + ArtworkArchive
   - Solution: Match by title similarity + merge data

## Revised MVP Schema

```python
# Core MVP fields (required)
{
    "id": "unique_hash",
    "title": "Call name",
    "organization": "Who's running it", 
    "deadline": "2025-08-29",  # Parsed date for sorting
    "apply_url": "Where to apply",
    "source_platforms": ["cafe", "artwork_archive"],  # Track all sources
    
    # Extras bucket for everything else
    "extras": {
        "deadline_raw": "August 29th, 2025",  # Original text
        "location": "New York, NY",
        "entry_fee": "$35",
        "eligibility": "International",
        "description": "...",
        "event_dates": {...},
        # ... any other fields from enhanced CaFE API
    }
}
```

## Action Items for MVP

### Must Fix:
1. **Update ShowSubmit** - Fetch individual pages for complete deadlines
2. **Update ArtworkArchive** - Fetch individual pages for organizations
3. **Implement deduplication** - Match and merge the 32 cross-platform duplicates

### Can Ship As-Is:
- CaFE data is perfect for MVP (could add 100+ fields to extras later)
- ArtCall data is perfect for MVP
- Current schema handles deduplication with `alternate_urls` and `merged_from_platforms`

## Data Volume Reality

- **759 raw opportunities** → ~**700-720 unique** after deduplication
- Total data size: < 5MB even with all individual pages
- This is completely manageable

## Recommendation

1. Fix the two data issues (ShowSubmit dates, ArtworkArchive orgs)
2. Run deduplication using title matching
3. Ship MVP with core fields
4. Put everything else in `extras` for future use

The data confirms your MVP vision is correct - we have what we need!