# Art Opportunities Explorer

A live dashboard for browsing art opportunities from multiple platforms, powered by Supabase.

## 🚀 Quick Deploy to GitHub Pages

### Step 1: Create a new GitHub repository
1. Go to [github.com/new](https://github.com/new)
2. Name it something like `art-opportunities` or `art-dashboard`
3. Make it public
4. Don't initialize with README (we have one)

### Step 2: Upload the files
```bash
# Clone your new repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# Copy the index.html file to your repo
cp /path/to/callscrape/gui/index.html .

# Add, commit, and push
git add index.html
git commit -m "Add art opportunities dashboard"
git push origin main
```

### Step 3: Enable GitHub Pages
1. Go to your repo's Settings
2. Scroll down to "Pages" section
3. Under "Source", select "Deploy from a branch"
4. Choose "main" branch and "/ (root)" folder
5. Click Save

### Step 4: Access your site
Your dashboard will be available at:
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
```

It usually takes 2-5 minutes to deploy the first time.

## 🔐 Supabase Configuration

When you first visit the site, you'll need to enter your Supabase credentials:

- **Supabase URL**: `https://hqevaaiketyqhzajqfwj.supabase.co`
- **Anon Key**: The public anon key (safe for client-side use)

These are saved in your browser's local storage for convenience.

## 🎨 Features

- **Live Data**: Real-time connection to Supabase database
- **Multiple Views**: List and Calendar views
- **Smart Filtering**: Search and filter by source platform
- **Auto-cleanup**: Expired deadlines (>24 hours old) are automatically hidden
- **Color Coding**: Each source has its own color for easy identification
- **Responsive Design**: Works on desktop and mobile

## 📊 Data Sources

- **ZapApplication**: 892 art fairs & festivals
- **Artwork Archive**: 251 opportunities
- **CaFÉ**: 249 calls
- **ArtCall**: 79 listings
- **ShowSubmit**: 42 calls

Total: 1,513+ opportunities

## 🛠️ Technical Details

- Single HTML file (no build process needed)
- External dependencies via CDN (FullCalendar, Supabase)
- No server required - runs entirely in the browser
- Secure read-only access via Supabase RLS

## 📝 Notes

- The dashboard requires Row Level Security (RLS) to be configured for public read access
- Location data is partially available (working on improving the scrapers)
- Data is updated daily via automated scrapers

---

Built with ❤️ for artists seeking opportunities
