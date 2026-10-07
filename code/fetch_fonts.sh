#!/bin/zsh
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
for fam in "Google+Sans+Flex:opsz,wght@14..144,400..700" "Roboto+Flex:opsz,wght@14..144,400..600"; do
  css=$(curl -s -A "$UA" "https://fonts.googleapis.com/css2?family=${fam}&display=swap")
  url=$(echo "$css" | awk '/\/\* latin \*\//{f=1} f && /url\(/{match($0, /https:[^)]*\.woff2/); print substr($0, RSTART, RLENGTH); exit}')
  echo "$fam -> $url"
  if [[ "$fam" == *Google* ]]; then out=space_jog/assets/google-sans-flex-var.woff2; else out=space_jog/assets/roboto-flex.woff2; fi
  curl -s -A "$UA" -o "$out" "$url"
done
