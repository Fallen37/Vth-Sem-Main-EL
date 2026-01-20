# Frontend Cache Troubleshooting Guide

If the changes aren't being reflected in the frontend, follow these steps:

## Step 1: Clear Browser Cache

### Chrome/Edge
1. Press `Ctrl+Shift+Delete` (Windows) or `Cmd+Shift+Delete` (Mac)
2. Select "All time" for time range
3. Check "Cookies and other site data" and "Cached images and files"
4. Click "Clear data"
5. Refresh the page (`Ctrl+R` or `Cmd+R`)

### Firefox
1. Press `Ctrl+Shift+Delete` (Windows) or `Cmd+Shift+Delete` (Mac)
2. Select "Everything" for time range
3. Check "Cache" and "Cookies"
4. Click "Clear Now"
5. Refresh the page

### Safari
1. Click "Safari" → "Preferences"
2. Go to "Privacy" tab
3. Click "Manage Website Data"
4. Select all and click "Remove"
5. Refresh the page

## Step 2: Hard Refresh

- **Windows**: `Ctrl+Shift+R`
- **Mac**: `Cmd+Shift+R`

This bypasses the cache and forces a fresh download of all assets.

## Step 3: Clear Vite Cache

```bash
# In the frontend directory
rm -rf node_modules/.vite
npm run build
```

## Step 4: Restart Dev Server

If running a dev server:

```bash
# Stop the current server (Ctrl+C)
# Then restart it
npm run dev
```

## Step 5: Check Network Tab

1. Open Developer Tools (`F12`)
2. Go to "Network" tab
3. Refresh the page
4. Look for the JavaScript bundle file (e.g., `index-*.js`)
5. Check the "Size" column - if it says "from cache", the cache is being used
6. If it says the actual size (e.g., "429 KB"), it's loading fresh

## Step 6: Verify Changes Are in Build

Check that the build includes your changes:

```bash
# Rebuild the frontend
npm run build

# Check the dist folder was updated
ls -la frontend/dist/
```

## Step 7: Full Clean Build

If nothing else works:

```bash
# Remove all build artifacts
rm -rf frontend/dist
rm -rf frontend/node_modules/.vite

# Rebuild
npm run build

# Clear browser cache (see Step 1)
# Then refresh the page
```

## What Changed in Task 4 Addendum

The NotebookBlock component now has:
- ✅ Clickable button-like interface
- ✅ Active/hover state management
- ✅ Floating toolbar with animations
- ✅ Keyboard navigation support
- ✅ Autism-friendly pastel colors
- ✅ Smooth transitions (< 200ms)

You should see:
1. Blocks with soft gradient backgrounds (#f0f4ff to #f5f0ff)
2. Rounded corners (12px border-radius)
3. Subtle shadows that increase on hover
4. When you click a block, a floating toolbar appears above it
5. The toolbar has quick action buttons (✨ 📝 📖 💡)
6. Smooth animations when hovering and clicking

## Verification Checklist

After clearing cache and refreshing:

- [ ] Blocks have soft pastel gradient backgrounds
- [ ] Blocks have rounded corners
- [ ] Hovering over a block shows elevation
- [ ] Clicking a block activates it (darker background)
- [ ] Floating toolbar appears above active block
- [ ] Toolbar has 4 buttons (✨ 📝 📖 💡)
- [ ] Clicking toolbar buttons works
- [ ] Animations are smooth (no jank)
- [ ] Keyboard navigation works (Tab + Enter)

## Still Not Working?

1. Check browser console for errors (`F12` → Console tab)
2. Verify the build completed successfully (no errors)
3. Check that `frontend/dist/` folder exists and was recently updated
4. Try a different browser
5. Try incognito/private mode (bypasses cache)

## Quick Commands

```bash
# Full clean and rebuild
rm -rf frontend/dist && npm run build

# Check if build succeeded
ls -la frontend/dist/assets/

# Check file sizes (should be ~429KB for JS)
du -h frontend/dist/assets/index-*.js
```

