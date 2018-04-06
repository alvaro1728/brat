#!/usr/bin/env bash
project="${PWD##*/}"
rm -f "$project `date +%Y-%m-%d`.zip"
zip -r "$project `date +%Y-%m-%d`.zip" . -x "./node_modules/*" "./.idea/*" "*/.DS_Store" "./.DS_Store" "./.git/*" "./*.iml" "./*.log" "./*.zip" "./target/*" "./out/*" "./cache/*" "./data/examples/*" "./data/examples/*" "./example-data/*" "./venv/*" "./static/*" "./external/*" "./res/*" "temp.txt"
open .
