# NewsGPT
Gcloud webpage that summarizes articles accurately to create a new headline


The goal is to remove bias and editor's mal-intent when labeling an article. By using an LLM to parse the body of the article, we can remove bias and misleading titles designed to generate clicks. Instead consistently and reliably lead the reader to content that they want to engage with.

TODO:
 - Add multiple feeds for different categories
 - A "For You" page that leverages a login and a user's personal preference to pull articles that would be of interest based on the content of the article

## Run locally

```sh
pip install -r requirements.txt
prisma generate
python scrapeNProcess.py
```

## Deploy to Google Cloud Run

```sh
gcloud run jobs deploy scrape-n-process \
  --project newsgpt-415319 \
  --region us-west1 \
  --max-retries 0 \
  --task-timeout 1h \
  --parallelism 1 \
  --memory 2Gi \
  --source . \
  --set-env-vars GORT_DB_URL="$GORT_DB_URL" \
  --set-env-vars OPENAI_API_KEY="$OPENAI_API_KEY" \
  --set-env-vars REDDIT_API="$REDDIT_API" \
  --set-env-vars REDDIT_PASS="$REDDIT_PASS"
```

### Schedule the Cloud Run job (above) to run every 12 hours

```sh
gcloud scheduler jobs create http scrape-scheduler \
  --project newsgpt-415319 \
  --location us-west1 \
  --schedule "0 6,18 * * *" \
  --time-zone America/Los_Angeles \
  --uri "https://us-west1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/newsgpt-415319/jobs/scrape-n-process:run" \
  --http-method POST \
  --oauth-service-account-email 164669378659-compute@developer.gserviceaccount.com
```

Note: If this scheduler has already been created and the parameters need to be adjusted, replace `create` with `update`.
