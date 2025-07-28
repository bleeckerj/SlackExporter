#!/bin/bash
find . -type f -name "messages.json" | while read -r jsonfile; do
    echo "Processing $jsonfile"
    python3 simple_slack_pdf_maker.py "$jsonfile" --page-size a5 --margin-top 0.35 --margin-left 0.5 --margin-right 0.5 --margin-bottom 0.35 --normal-font "/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf" --bold-font "/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Condensed.ttf" --output-pdf-name "${jsonfile%.json}.pdf"
done