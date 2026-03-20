import logging

from app import create_app
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run()
