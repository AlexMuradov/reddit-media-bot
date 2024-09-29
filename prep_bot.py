import os
import time
import praw
import prawcore
from pymongo import MongoClient, errors
from bson import ObjectId
import requests
import logging
from openai import OpenAI
from flask import Flask, jsonify, request, redirect, url_for



# Setup logging
logging.basicConfig(filename='reddit_fetcher.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize Flask
app = Flask(__name__)

# Function to check post relevance using OpenAI
def is_post_relevant(title, body):
    messages = [
        {
        "role": "system",
        "content": [
            {
            "type": "text",
            "text": "" # Example Decide whether we could reply and either directly or indirectly promote our Tech Preparation website. Deciding factor to reply or not is - If the post is about career advice, interview preparation, question about how to learn specific technology, jobs interview questions, best please to learn something. Respond only and only with 'yes' or 'no' (witout bracket), 'yes' meaning we can reply 'no' meaning we can not.
            }
        ]
        },
        {

            "role": "user",
            "content": [
                {
                "type": "text",
                "text": f"Title: {title}\n" f"Body: {body}\n"
                }
            ]
        }
    ]
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="gpt-4o",
            max_tokens=1500
        )
        return response.choices[0].message.content.strip().lower() == "yes"
    except Exception as e:
        logging.error(f"OpenAI API Error: {e}")
        return False

# Function to generate reply for a relevant post
def generate_reply(title, body):
    messages = [
        {
        "role": "system",
        "content": [
            {
            "type": "text",
            "text": "" # Autoreply .. write here how to respond on discovered articles
            }
        ]
        },
        {
            "role": "user",
            "content": (
                f"Title: {title} Body: {body}\n"
            )
        }
    ]
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="gpt-4o",
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI API Error: {e}")
        return "Check out our platform for more information!"

def send_to_discord(message, webhook_url):
    data = {
        "content": message,
        "avatar_url": 'https://pbs.twimg.com/profile_images/1311008414156423170/Kxu_7mQS_400x400.jpg',
        "username": 'sniffingCat_Bot',
    }
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        print("Message successfully sent to Discord")
    else:
        print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

def fetch_filtered_posts(subreddit_name, reddit, collection, discord_webhook_url, lookup_window):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = subreddit.new(limit=lookup_window)
        for post in posts:
            if collection.find_one({"link": post.url}):
                continue
            
            print(f"Analyzing:\nr/{subreddit_name}\nTitle: {post.title}\n")
            
            if is_post_relevant(post.title, post.selftext):
                print("Processing...\n")
                reply = generate_reply(post.title, post.selftext)
                message = f"**Title:** {post.title}\n**Link:** {post.url}\n**Subreddit:** r/{subreddit_name}"
                send_to_discord(message, discord_webhook_url)
                print(message)
                collection.insert_one({"link": post.url, "title": post.title, "subreddit": subreddit_name, "selftext": post.selftext, "reply": reply})
            else:
                print("Skipping...\n")
                collection.insert_one({"link": post.url})
    except prawcore.exceptions.RequestException as e:
        logging.error(f"Request Exception: Could not reach Reddit API: {e}")
        print("Network error: Could not reach Reddit API. Please check your internet connection.")
    except prawcore.exceptions.ResponseException as e:
        logging.error(f"Response Exception: {e}. Check your Reddit API credentials.")
        print(f"Response Exception: {e}. Check your Reddit API credentials.")
    except prawcore.exceptions.BadRequest:
        logging.error("Bad Request: Verify the subreddit name and your PRAW setup.")
        print("Bad Request: Verify the subreddit name and your PRAW setup.")
    except prawcore.exceptions.NotFound:
        logging.error(f"Subreddit {subreddit_name} not found.")
        print(f"Subreddit {subreddit_name} not found.")

@app.route("/entries")
def list_entries():
    try:
        entries = collection.find({"reply": {"$exists": True}})
        response_html = ""
        for entry in entries:
            response_html += f'<a href="{entry["link"]}" target="_blank">{entry["title"]}</a><br>{entry["reply"]}<br><a href="/delete-entry?id={entry["_id"]}">Delete Entry</a><hr>'
        return response_html
    except Exception as e:
        logging.error(f"Error fetching entries from MongoDB: {e}")
        return "An error occurred while fetching entries."

@app.route("/delete-entry")
def delete_entry():
    entry_id = request.args.get("id")
    try:
        if entry_id:
            collection.update_one({"_id": ObjectId(entry_id)}, {"$unset": {"reply": ""}})
            return redirect(url_for('list_entries'))
        else:
            return "Invalid entry ID", 400
    except Exception as e:
        logging.error(f"Error deleting entry from MongoDB: {e}")
        return "An error occurred while deleting the entry.", 500

def main():
    # Validate environment variables
    required_env_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USER_AGENT', 'OPENAI_API_KEY', 'MONGO_URI', 'REDDIT_SUBREDDITS', 'DISCORD_WEBHOOK_URL', 'LOOKUP_WINDOW']
    for var in required_env_vars:
        if not os.getenv(var):
            logging.error(f"Environment variable {var} is not set.")
            print(f"Environment variable {var} is not set. Exiting.")
            return

    # Validate and convert LOOKUP_WINDOW to integer
    try:
        lookup_window = int(os.getenv('LOOKUP_WINDOW'))
    except ValueError:
        logging.error("Invalid value for LOOKUP_WINDOW. It should be an integer.")
        print("Invalid value for LOOKUP_WINDOW. It should be an integer. Exiting.")
        return


    # Initialize the Reddit client with your credentials
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT')
    )

    # Initialize MongoDB client
    mongo_uri = os.getenv('MONGO_URI')
    try:
        mongo_client = MongoClient(mongo_uri)
        global collection
        db = mongo_client[os.getenv('DB_NAME', 'mediabot')]
        collection = db[os.getenv('COLLECTION_NAME', 'filtered_posts')]
    except errors.ConnectionError as e:
        logging.error(f"MongoDB Connection Error: {e}")
        print("Unable to connect to MongoDB. Check your MongoDB URI and connection.")
        return

    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    subreddits = os.getenv('REDDIT_SUBREDDITS').split(',')
    interval = int(os.getenv('SLEEP_INTERVAL', '600'))

    def scan_subreddits():
        while True:
            print(f"Checking subreddits: {subreddits} every {interval / 60} minutes")
            for subreddit in subreddits:
                fetch_filtered_posts(subreddit.strip(), reddit, collection, discord_webhook_url, lookup_window)
            print(f"Waiting for {interval / 60} minutes before the next run\n")
            time.sleep(interval)

    # Run the Reddit scanning in a separate thread
    import threading
    scanning_thread = threading.Thread(target=scan_subreddits)
    scanning_thread.start()

    # Run the Flask web server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

if __name__ == "__main__":
    main()