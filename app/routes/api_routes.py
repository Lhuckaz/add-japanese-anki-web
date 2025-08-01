from flask import Blueprint, jsonify, request
import os
import logging
from app.utils.utils import addnote as add_anki_note
from app.utils.utils import addnote_english as add_anki_note_english
from app.utils.container import handle_container

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')

@api.route("/addnote", methods=["POST"])
def addnote():
  HANDLE_CONTAINER = os.environ.get('HANDLE_CONTAINER', 'False').lower() == 'true'
  ankiConnect = os.environ.get("ANKICONNECT_URL")
  if not ankiConnect:
    return jsonify({"error": "ANKICONNECT_URL environment variable not set"}), 500

  data = request.get_json()
  if not data:
        return jsonify({"error": "Missing JSON data"}), 400
  word = data.get("word").strip()
  dropdown_value = data.get("dropdownValue")

  if not word:
    return jsonify({"message": "Missing 'word'"}), 400

  try:
    if HANDLE_CONTAINER:
      handle_container()
    deck = dropdown_value.capitalize()
    if dropdown_value == "japanese":
      add_anki_note(ankiConnect, deck, word)
      return jsonify({
            "message": "Note added successfully",
            "word": word,
            "value": dropdown_value
      }), 200
    else:
      add_anki_note_english(ankiConnect, deck, word)
      return jsonify({
            "message": "Note added successfully",
            "word": word,
            "value": dropdown_value
      }), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500
