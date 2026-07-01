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
- Edit selected cells through the bottom edit bar
- Add rows and columns
- Save as `.csv` or `.xlsx`
- Switch sheets for Excel workbooks
