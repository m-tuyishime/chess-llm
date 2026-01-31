import os
import sys

# Add the project root to sys.path to allow imports from 'website' and 'chess_llm_eval'
# This is necessary because this file is inside the 'api/' directory
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import the FastAPI app from the website server
from website.server.main import app
