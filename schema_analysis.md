# Art Opportunity Schema Analysis

## Current Field Capture by Platform

### CaFE (cafe_spider.py - Basic)
- `id`: Generated hash
- `title`: fair_name
- `organization`: organization_name
- `url`: fair_url
- `scraped_at`: timestamp

### CaFE (cafe_spider_enhanced.py - Not in production)
- `id`: Generated hash
- `title`: fair_name
- `organization`: organization_name
- `url`: fair_url
- `deadline`: fair_deadline (YYYY-MM-DD format!)
- `event_start`: event_start date
- `event_end`: event_end date
- `location`: "city, state_code"
- `email`: fair_email
- `scraped_at`: timestamp

### ArtCall (artcall_spider.py)
- `id`: Generated hash
- `title`: Call title
- `organization`: From subdomain
- `url`: Call URL
- `deadline`: Entry deadline text
- `eligibility`: Eligibility requirements
- `entry_fee`: Fee text
- `location`: State badge
- `type`: "Featured" or "ArtCall"
- `scraped_at`: timestamp

### ShowSubmit (showsubmit_spider.py)
- `id`: Generated hash
- `title`: Show title
- `organization`: Organization name
- `url`: Details page URL
- `deadline`: Deadline text (partial)
- `eligibility`: Eligibility badge
- `scraped_at`: timestamp

## Available Fields Not Currently Captured

### From Listings (without individual pages)

**CaFE** - Already available in API response:
- ✅ deadline (in enhanced version)
- ✅ event_start/event_end (in enhanced version)
- ✅ location details (in enhanced version)
- ✅ email (in enhanced version)

**ArtCall** - Available in listing:
- ✅ All fields being captured

**ShowSubmit** - Available in listing:
- ❌ Entry fees (visible in some cards)
- ❌ Full deadline with year
- ❌ Location details

### From Individual Pages (requires additional requests)

**ShowSubmit individual pages have:**
- Full address with street, city, state, zip
- Tiered fee structures (Early bird, Regular, Late)
- Detailed eligibility requirements
- Event/exhibition dates
- Jury information
- Awards/prizes
- Contact information

**ArtCall individual pages have:**
- Detailed description
- Application requirements (image specs, etc.)
- Categories accepted
- Sales commission rates

## Proposed Unified Schema

### Core Fields (Lowest Common Denominator)
Every platform has or can easily get these:

```python
# Required fields - available from all platforms
id: str                    # Generated hash for deduplication
title: str                 # Opportunity title
organization: str          # Hosting organization
url: str                   # Link to opportunity/application
source_platform: str       # "cafe", "artcall", "showsubmit"
scraped_at: datetime       # When we scraped it
```

### Standard Optional Fields
Most platforms have these, use None if not available:

```python
# Common fields - available from most platforms without extra requests
deadline: Optional[str]           # Deadline date/text
deadline_parsed: Optional[date]   # Parsed deadline for sorting
location_text: Optional[str]      # Location as provided (varied formats)
location_city: Optional[str]      # Parsed city
location_state: Optional[str]     # Parsed state/province
location_country: Optional[str]   # Default to "USA" if not specified
entry_fee: Optional[str]          # Fee information (text)
eligibility: Optional[str]        # Who can apply
```

### Enhanced Optional Fields
Available from some platforms or require parsing:

```python
# Enhanced fields - some platforms or needs individual page fetch
email: Optional[str]              # Contact email
event_start_date: Optional[date]  # When exhibition/event starts
event_end_date: Optional[date]    # When exhibition/event ends
application_type: Optional[str]   # "exhibition", "public_art", "grant", etc.
is_featured: bool = False         # Promoted/featured opportunity
```

### Platform-Specific Fields
Store raw platform data for future use:

```python
# Platform-specific data preserved for future use
raw_data: dict                    # Original platform response/data
platform_id: Optional[str]        # Platform's internal ID if available
last_updated: datetime            # For change tracking
```

## Data Quality Notes

1. **Deadlines**: Mix of formats
   - CaFE: Clean "YYYY-MM-DD"
   - ArtCall: "December 31, 2024" with unicode spaces
   - ShowSubmit: "December 31st" (no year in listing)

2. **Locations**: Highly varied
   - CaFE: Separate city and state code fields
   - ArtCall: State abbreviation badges
   - ShowSubmit: Mixed or missing

3. **Fees**: Inconsistent formats
   - Some have "$X", others "Free", some "Varies"
   - ShowSubmit has tiered fees on individual pages

4. **Organizations**: 
   - CaFE and ShowSubmit have clear org names
   - ArtCall derives from subdomain (less reliable)

## Recommendations

1. **Start with core + standard optional fields** - This covers 90% of use cases
2. **Add deadline parsing logic** to convert various formats to dates for sorting
3. **Implement location parsing** to extract city/state from various formats
4. **Keep raw_data field** to preserve original data for future enhancements
5. **Add data quality scores** to indicate completeness/confidence