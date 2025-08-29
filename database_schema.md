# Database Schema for Art Opportunities

## Core Design Principles

1. **Keep all historical data** - Past deadlines are valuable for industry tracking
2. **Track changes over time** - Know when opportunities are added/updated
3. **Support deduplication** - Link same opportunity across platforms
4. **Optimize for common queries** - Active calls, upcoming deadlines, by organization

## Schema Design

### 1. `opportunities` (Main Table)
The canonical record for each unique opportunity.

```sql
CREATE TABLE opportunities (
    -- Identity
    id TEXT PRIMARY KEY,  -- Generated hash
    title TEXT NOT NULL,
    organization TEXT,  -- Best available org name
    
    -- Key dates  
    deadline DATE,  -- Parsed deadline for sorting
    deadline_raw TEXT,  -- Original deadline text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,  -- False when deadline passed
    status TEXT DEFAULT 'open',  -- open, closed, cancelled
    
    -- MVP fields
    primary_url TEXT NOT NULL,  -- Best URL to apply
    
    -- Additional data (JSON for flexibility)
    extras JSON,  -- All other fields: location, fees, eligibility, etc.
    
    -- Tracking
    first_seen DATE,
    last_checked DATE,
    times_seen INTEGER DEFAULT 1,
    
    -- Data quality
    has_complete_data BOOLEAN DEFAULT FALSE,
    missing_fields TEXT[]  -- Track what needs fetching
);

-- Indexes for common queries
CREATE INDEX idx_deadline ON opportunities(deadline) WHERE is_active = TRUE;
CREATE INDEX idx_organization ON opportunities(organization);
CREATE INDEX idx_status ON opportunities(status);
CREATE INDEX idx_created ON opportunities(created_at);
```

### 2. `opportunity_sources` (Platform Tracking)
Track where each opportunity appears.

```sql
CREATE TABLE opportunity_sources (
    opportunity_id TEXT REFERENCES opportunities(id),
    platform TEXT NOT NULL,  -- cafe, artcall, showsubmit, artwork_archive
    platform_url TEXT NOT NULL,
    platform_id TEXT,  -- Platform's internal ID if available
    
    -- Platform-specific data
    raw_data JSON,  -- Complete original response
    
    -- Tracking
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (opportunity_id, platform)
);
```

### 3. `scrape_runs` (Audit Trail)
Track each scraping session.

```sql
CREATE TABLE scrape_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    platform TEXT,
    
    -- Results
    total_found INTEGER,
    new_opportunities INTEGER,
    updated_opportunities INTEGER,
    errors JSON,
    
    -- Performance
    duration_seconds FLOAT,
    pages_fetched INTEGER
);
```

### 4. `opportunity_history` (Change Tracking)
Track changes to opportunities over time.

```sql
CREATE TABLE opportunity_history (
    opportunity_id TEXT REFERENCES opportunities(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    change_source TEXT  -- Which platform reported the change
);
```

## Query Examples

### Active Opportunities (for website display)
```sql
SELECT * FROM opportunities 
WHERE is_active = TRUE 
  AND deadline >= CURRENT_DATE
ORDER BY deadline ASC;
```

### Find Duplicates
```sql
SELECT o1.title, o1.organization, 
       GROUP_CONCAT(os.platform) as platforms
FROM opportunities o1
JOIN opportunity_sources os ON o1.id = os.opportunity_id
GROUP BY o1.id
HAVING COUNT(DISTINCT os.platform) > 1;
```

### Industry Tracking (Historical Analysis)
```sql
-- Organizations with most opportunities
SELECT organization, COUNT(*) as total_opportunities,
       COUNT(CASE WHEN deadline >= CURRENT_DATE THEN 1 END) as active
FROM opportunities
WHERE organization IS NOT NULL
GROUP BY organization
ORDER BY total_opportunities DESC;

-- Seasonal trends
SELECT EXTRACT(MONTH FROM deadline) as month,
       COUNT(*) as opportunities
FROM opportunities
WHERE deadline IS NOT NULL
GROUP BY month
ORDER BY month;
```

### Data Quality Report
```sql
SELECT 
    platform,
    COUNT(*) as total,
    COUNT(CASE WHEN o.organization IS NOT NULL THEN 1 END) as has_org,
    COUNT(CASE WHEN o.deadline IS NOT NULL THEN 1 END) as has_deadline,
    COUNT(CASE WHEN o.has_complete_data THEN 1 END) as complete
FROM opportunity_sources os
JOIN opportunities o ON os.opportunity_id = o.id
GROUP BY platform;
```

## Migration Path

1. **Initial Load**: 
   - Scrape all platforms
   - Create canonical opportunities
   - Link sources
   
2. **Daily Updates**:
   - Check for new/changed opportunities
   - Update `is_active` based on deadline
   - Record changes in history
   
3. **Weekly Enrichment**:
   - Fetch individual pages for incomplete data
   - Update organization names from subpages
   - Re-check past deadlines that might recur

## Benefits of This Design

1. **Historical Tracking** - Keep past deadlines for analysis
2. **Deduplication** - One canonical record, multiple sources
3. **Flexibility** - JSON `extras` field for platform-specific data
4. **Performance** - Indexed for common queries
5. **Audit Trail** - Track all changes and scrape runs
6. **Data Quality** - Track completeness, missing fields

## Implementation Notes

- Use SQLite for simplicity or PostgreSQL for JSON support
- Consider adding full-text search on title/organization
- Implement soft deletes (mark as inactive vs. delete)
- Add recurring opportunity detection (annual events)