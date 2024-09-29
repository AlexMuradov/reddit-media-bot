# Reddit Bot Documentation

## Overview
This bot monitors specified subreddits for relevant posts, generates automated replies using OpenAI's API, and logs the posts to a MongoDB database. Relevant posts are also sent to a Discord channel via a webhook.

## Prerequisites
- Python 3.11
- PRAW (Python Reddit API Wrapper)
- MongoDB with a database and collection
- OpenAI API Key
- Discord Webhook URL
- Docker
- Kubernetes and Helm (for deployment)

## Environment Variables
Ensure the following environment variables are set:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `OPENAI_API_KEY`
- `MONGO_URI`
- `REDDIT_SUBREDDITS` (comma-separated list of subreddits)
- `DISCORD_WEBHOOK_URL`
- `LOOKUP_WINDOW` (how many recent posts to check)
- `DB_NAME` (default: `mediabot`)
- `COLLECTION_NAME` (default: `filtered_posts`)
- `SLEEP_INTERVAL` (time in seconds between scans, default: `600`)

## Steps to Run Locally

1. Clone the repository.

2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Set required environment variables.

4. Run the application:
    ```sh
    python prep_bot.py
    ```

## Docker Setup

1. Build the Docker image:
    ```sh
    docker build -t reddit-bot .
    ```

2. Run the Docker container:
    ```sh
    docker run -p 5000:5000 --env-file .env reddit-bot
    ```

## Helm Chart for Kubernetes Deployment

1. Edit the `./helm/values.yaml` file to set the required environment variables and image repository.

2. Deploy the Helm chart:
    ```sh
    helm install reddit-bot ./helm
    ```

## REST API Endpoints

### List Entries
- **URL:** `/entries`
- **Method:** GET
- **Description:** Lists all relevant posts with replies.

### Delete Entry
- **URL:** `/delete-entry`
- **Method:** GET
- **Description:** Deletes a specific entry by ID from MongoDB.

## Logging
Logs are written to `reddit_fetcher.log`.

## License
This project is licensed under the MIT License.

---

For detailed setup and configuration, refer to the script and Helm values files.