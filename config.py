from pathlib import Path

DB_PATH = Path("data/events.db")
WINDOW_HOURS = 48            # look at articles from the last 48 hours
SIMILARITY_DISTANCE = 0.45   # clustering threshold (lower = stricter). A starting guess; you'll tune it
MIN_SOURCES = 2              # an event needs at least 2 different outlets
MAX_EVENTS_PER_RUN = 10      # protects the free LLM quota (use 3 while testing)
KEEP_DAYS = 14               # delete older articles to keep the database small
MODEL_NAME = "openai/gpt-oss-20b"   # pick a text model that your Groq account lists
MIN_TOPIC_SCORE = 0.18   # starting guess. You will tune it with the debug script below