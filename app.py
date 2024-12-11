import os
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from rasa.core.agent import Agent
from rasa.shared.utils.io import json_to_string
from config import Config
from model import db, Assistant, Prompt, ChatbotConversion
import asyncio


# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize CORS and database
CORS(app)
db.init_app(app)

# Path to the Rasa model file
MODEL_PATH = "./models/20241212-013603-shrewd-sample.tar.gz"

# Load Rasa agent
try:
    agent = Agent.load(MODEL_PATH)
    print("Rasa model loaded successfully.")
except Exception as e:
    print(f"Failed to load Rasa model: {e}")
    agent = None

@app.route('/')
def index():
    return "Welcome to the Sensia Project API!"

# API for chatbot conversation
@app.route("/api/chat", methods=["POST"])
def chatbot_conversation():
    try:
        # Get the user message from the request
        data = request.json
        user_message = data.get("message")
        assistant_id = data.get("assistant_id", "default")  # Default sender if none is provided

        # Validate the message input
        if not user_message:
            return jsonify({"error": "User message is required"}), 400

        if not agent:
            return jsonify({"error": "Rasa model is not loaded."}), 500

        # Process the message using the Rasa agent using asyncio
        async def get_bot_response():
            response = await agent.handle_text(user_message, sender_id=assistant_id)
            return response[0].get("text", "") if response else "No response"

        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot_response = loop.run_until_complete(get_bot_response())

        # Save the conversation to the database
        session_id = str(uuid.uuid4())
        new_conversion = ChatbotConversion(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
        )
        db.session.add(new_conversion)
        db.session.commit()

        # Return the bot's response
        return jsonify({
            "session_id": session_id,
            "bot_message": bot_response
        })

    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
