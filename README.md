# Mobile XL

Mobile XL is a Kivy mobile app for opening, editing, and saving `.csv` and `.xlsx` files.

## Local Run

```bash
pip install -r requirements.txt
python main.py
```

## Android APK

The repository includes `buildozer.spec` and a GitHub Actions workflow at `.github/workflows/build-apk.yml`.

Push to `main`, open a pull request, or run the workflow manually. The debug APK is uploaded as a workflow artifact named `mobile-xl-debug-apk`.

## Current Scope

- Open `.csv` and `.xlsx`
- Scroll spreadsheet data horizontally and vertically
- Drag expandable fast-scroll thumbs to jump across large row and column ranges
- Keep large spreadsheets responsive with a virtualized cell canvas
- Import files in the background into a disk-backed working database
- Edit selected cells through the bottom edit bar
- Add rows and cells below the current selection
- Delete selected rows and cells
- Freeze the top row per sheet, with persistence in `.xlsx` files
- Save as `.csv` or `.xlsx`
- Switch sheets for Excel workbooks

Large files are streamed into SQLite in the app data directory. The editor only
queries and draws cells near the visible viewport instead of creating a Kivy
widget for every cell. Saving is streamed through a temporary file and replaces
the destination only after the export completes.
