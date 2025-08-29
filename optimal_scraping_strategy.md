# Optimal Scraping Strategy for Each Platform

## Executive Summary

Each platform requires a different approach to maximize data capture:

1. **CaFE/CallForEntry.org**: Use API only - it has EVERYTHING
2. **ArtCall.org**: Focus on subdomain calls, ignore "Featured" aggregated calls
3. **ShowSubmit.com**: Must fetch individual pages for complete data

---

## CaFE / CallForEntry.org

### Current Approach: ❌ Using only 5 of 100+ available fields

### Optimal Approach: ✅ Use API with ALL fields

The API returns **100+ fields** including:
- Basic: title, organization, URL, email
- Dates: deadline, event_start, event_end, jury dates
- Location: city, state (as code)
- Requirements: eligibility, image specs, statement requirements
- Financial: entry fees (implied in requirements text)
- Rich text: full descriptions, eligibility details, requirements
- Status: active/inactive, days until deadline
- Categories: accept_images, accept_video, accept_audio
- Jury info: jury type, jury dates, jury process

**Recommendation**: 
- **KEEP using the API** (no need for individual pages)
- **Extract ALL available fields** from the JSON response
- The `fair_url` links to organization sites, not more data

### Data We're Missing:
```python
# Currently capturing:
id, title, organization, url, scraped_at

# SHOULD be capturing:
deadline, event_start, event_end, location (city + state),
email, eligibility_desc, requirements, agreement,
jury_start, jury_end, image_number, allow_range_of_images,
artist_statement_required, fair_type, and 90+ more fields!
```

---

## ArtCall.org

### Current Approach: ✅ Correct - scraping listing page

### Optimal Approach: ✅ Keep current + optionally fetch subdomain pages

The listing page has most critical data:
- Title, deadline, eligibility, entry fee, location (state)
- Organization (from subdomain)
- Type (Featured vs ArtCall)

**Important distinction**:
- **"Featured" calls** = Aggregated from other platforms (less valuable)
- **ArtCall subdomain calls** = Native to platform (more valuable)

The subdomain pages (e.g., `peekingthrough.artcall.org`) have:
- Application forms and payment processing
- Some additional requirements text
- But core data is already in the listing

**Recommendation**:
- **KEEP scraping the listing page** (current approach is good)
- **Filter out or deprioritize "Featured" calls** (they're duplicates)
- **Optionally fetch subdomain pages** for high-interest calls only

---

## ShowSubmit.com

### Current Approach: ❌ Missing critical data from individual pages

### Optimal Approach: ✅ Must fetch individual pages

The listing page has only:
- Title, organization, partial deadline (no year!), basic eligibility

Individual pages have MUCH more:
- **Complete deadline with year**
- **Full address** (street, city, state, zip)
- **Tiered pricing** (Early bird: $20, Regular: $30, Late: $40)
- **Detailed eligibility requirements**
- **Exhibition dates**
- **Juror information**
- **Categories and specifications**
- **Awards/prizes**

**Recommendation**:
- **MUST fetch individual pages** for complete data
- Listing gives ~40 calls, pages are ~70KB each = ~2.8MB total
- This is a small, finite dataset - fetch them all

### Scraping Strategy for ShowSubmit:
```python
1. Get listing page (current approach)
2. For each call, fetch the individual page
3. Extract rich data from individual pages
4. Cache pages to avoid re-fetching
```

---

## ArtworkArchive.com

### Current Approach: ✅ Scraping listings, but missing source tracking

### Optimal Approach: ✅ Fetch individual pages + track original sources

ArtworkArchive is a **major aggregator** pulling from:
- CaFE, ShowSubmit, ArtCall (our main sources)
- Plus dozens of other platforms (lightspacetime.art, zealous.co, Google Forms, etc.)

Individual pages have:
- Complete deadline, fees, eligibility, description, categories
- **Most importantly**: Apply button with **original source URL**

**Recommendation**:
- **Fetch all individual pages** to capture complete data
- **Extract and store the original source URL** from Apply button
- **Track which opportunities are duplicates** from our main sources
- **Discover new opportunities** not available on our main platforms

### Value of ArtworkArchive:
1. **Discovery of new sources** - finds opportunities we'd miss otherwise
2. **Unified format** - normalizes data from diverse sources
3. **Additional metadata** - sometimes adds context not in original

---

## Aggregator Handling Strategy

We have two types of aggregators:

### 1. Platform-Specific Aggregation
- **ArtCall "Featured" section**: Aggregates from other platforms
- Should be scraped and marked as aggregated content
- Store original source URL when available

### 2. Dedicated Aggregators  
- **ArtworkArchive**: Pure aggregator from 20+ sources
- Valuable for discovering opportunities not on main platforms
- Must track original source to handle deduplication

### Deduplication Strategy:
```python
# In our unified schema (models.py), we already have:
- alternate_urls: List[str]  # All URLs for this opportunity
- merged_from_platforms: List[str]  # Which platforms had this

# Process:
1. Scrape all sources (including aggregators)
2. Extract original source URLs from aggregators
3. Match opportunities by:
   - Exact URL match
   - Original source URL match
   - Fuzzy title + organization match
4. Merge data, keeping the most complete version
```

---

## Change Detection for Database

Since we're moving to a database with change detection:

### Initial Load:
1. Scrape everything from all sources (including individual pages)
2. Store in database with:
   - Full current data
   - Hash of key fields for change detection
   - Timestamp of last check

### Incremental Updates:
1. **Daily quick scan**: Check listings only
   - New opportunities → fetch individual pages
   - Changed deadlines/titles → mark for deep refresh
2. **Weekly deep refresh**: Re-fetch individual pages for:
   - Opportunities with upcoming deadlines
   - Recently changed opportunities
3. **Monthly full refresh**: Re-scrape everything

### Database Schema Addition:
```python
# Track scraping metadata
last_listing_check: datetime
last_detail_fetch: datetime
listing_hash: str  # Hash of listing data for change detection
detail_hash: str   # Hash of detail page data
fetch_priority: int  # Higher for new, upcoming, or changed
```

---

## Implementation Priority

### Phase 1: Quick Wins (1 hour)
1. **Switch to cafe_spider_enhanced.py** and capture ALL API fields
2. **Update ArtCall spider** to mark Featured vs ArtCall calls

### Phase 2: ShowSubmit Enhancement (2-3 hours)
1. **Add individual page fetching** for ShowSubmit
2. **Parse full data** from ShowSubmit pages
3. **Add year inference** for deadline dates

### Phase 3: Optimization (Optional)
1. **Add caching layer** to avoid re-fetching unchanged pages
2. **Smart fetch strategy** - only fetch new/updated calls
3. **Cross-platform deduplication** using the unified schema

---

## Data Volume Analysis

### Current State
- CaFE: ~300 calls × 5 fields = minimal data
- ArtCall: ~200 calls (159 native + ~40 featured) × 8 fields = good data
- ShowSubmit: ~40 calls × 5 fields = minimal data
- ArtworkArchive: ~200-300 calls × 7 fields = partial data

### With Optimal Scraping
- CaFE: ~300 calls × 100+ fields = COMPLETE data from API
- ArtCall: ~200 calls × 8 fields = good data (already optimal)
- ShowSubmit: ~40 calls × 15+ fields = COMPLETE data with individual pages
- ArtworkArchive: ~200-300 calls × 10+ fields + original source URLs

### Total Data Size
- CaFE API: ~500KB JSON (complete dataset)
- ArtCall: Current scraping is sufficient
- ShowSubmit pages: ~3MB (40 × 75KB)
- ArtworkArchive pages: ~5-8MB (200-300 × 25KB)
- **Total: < 12MB for complete dataset**

### Unique Opportunities After Deduplication
- Direct sources: ~400-500 unique opportunities
- Via aggregators: +50-100 additional from other platforms
- **Total: ~500-600 unique opportunities**

This is absolutely a finite dataset - we should capture everything available!