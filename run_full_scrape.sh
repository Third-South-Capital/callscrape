#!/bin/bash
# Full scraper run - gets ALL data including all Zapplication events
# This will take a long time (~45 minutes for Zapplication alone)

echo "=========================================="
echo "FULL SCRAPER RUN - ALL OPPORTUNITIES"
echo "=========================================="
echo ""
echo "This will scrape:"
echo "  - CaFE (with Selenium for real IDs)"
echo "  - ArtCall"
echo "  - ShowSubmit (with detail pages)"
echo "  - ArtworkArchive"
echo "  - Zapplication (ALL 892 events - will take ~45 minutes)"
echo ""
echo "Total estimated time: 50-60 minutes"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Run the full scrape without limits
python3 main.py

echo ""
echo "=========================================="
echo "Scraping complete!"
echo "=========================================="
echo ""
echo "To sync to Supabase, run:"
echo "  python3 main.py --db-only --sync-db"
echo ""
echo "To view results locally:"
echo "  python3 -m http.server 8080"
echo "  Then open: http://localhost:8080/test_viewer.html"