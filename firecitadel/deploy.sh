gcloud beta functions deploy firecitadel-service \
    --gen2 \
    --runtime python39 \
    --trigger-http \
    --entry-point dream_story \
    --source . \
    --region us-central1 \
    --timeout=300 \
    --allow-unauthenticated
