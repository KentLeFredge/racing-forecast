name: Weekly Racing Forecast

on:
  schedule:
    - cron: '0 8 * * 1'
  workflow_dispatch:

jobs:
  screenshot-and-post:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Puppeteer
        run: npm install puppeteer

      - name: Take screenshot of bulletin
        run: node screenshot.js

      - name: Post to Discord
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          WEEK=$(date '+%B %d, %Y')
          curl -X POST "$DISCORD_WEBHOOK" \
            -F "file=@bulletin_screenshot.png" \
            -F "payload_json={\"content\":\"📅 **Racing Forecast** — Week of $WEEK\"}"
