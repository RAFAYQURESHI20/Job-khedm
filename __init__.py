name: Daily Scrape Pipeline

on:
  schedule:
    - cron: "0 2 * * *"   # 02:00 UTC every day
  workflow_dispatch:
    inputs:
      sources:
        description: "Sources to scrape (comma-separated or 'all')"
        required: false
        default: "all"
      dry_run:
        description: "Dry run (skip DB writes)"
        type: boolean
        required: false
        default: false

jobs:
  scrape:
    name: Run Scrape Pipeline
    runs-on: ubuntu-latest
    timeout-minutes: 60

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: jobpulse
          POSTGRES_USER: jobpulse_user
          POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Download ML model
        run: |
          mkdir -p ml/models
          curl -L "${{ secrets.MODEL_DOWNLOAD_URL }}" -o ml/models/classifier_v3.pt
        continue-on-error: true

      - name: Run Alembic migrations
        env:
          DATABASE_URL: postgresql+asyncpg://jobpulse_user:${{ secrets.DB_PASSWORD }}@localhost:5432/jobpulse
        run: alembic upgrade head

      - name: Run daily pipeline
        env:
          DATABASE_URL: postgresql+asyncpg://jobpulse_user:${{ secrets.DB_PASSWORD }}@localhost:5432/jobpulse
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          PROXY_URL: ${{ secrets.PROXY_URL }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          LOG_LEVEL: INFO
        run: |
          python run_daily_pipeline.py \
            --sources "${{ github.event.inputs.sources || 'all' }}" \
            ${{ github.event.inputs.dry_run == 'true' && '--dry-run' || '' }}

      - name: Upload pipeline log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pipeline-log-${{ github.run_id }}
          path: "pipeline_log_*.txt"
          retention-days: 14
