#!/bin/bash
find . -type f -name "messages.json" | while read -r jsonfile; do
    echo "Processing $jsonfile"
    python3 simple_slack_pdf_maker.py "$jsonfile" --page-size A5 --margin-top 0.65 --margin-left 0.5 --margin-right 0.5 --margin-bottom 0.35 --normal-font "/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontMono-Regular.ttf" --bold-font "/Users/julian/OMATA Dropbox/Julian Bleecker/PRODUCTION ASSETS/FONTS/3270/3270NerdFontPropo-Condensed.ttf"
done