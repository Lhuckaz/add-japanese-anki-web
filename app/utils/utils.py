import asyncio
import base64
import logging
import os
import random
import re
import shutil
import time

import pykakasi
import requests
from google import genai
from google.genai import types
from googletrans import Translator
from gtts import gTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"


def _positive_int_env(name, default):
    try:
        value = int(os.getenv(name, default))
        if value >= 0:
            return value
    except (TypeError, ValueError):
        pass
    logger.warning("Invalid %s value; using %s.", name, default)
    return default


def _positive_float_env(name, default):
    try:
        value = float(os.getenv(name, default))
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    logger.warning("Invalid %s value; using %s.", name, default)
    return default


# GEMINI_MAX_RETRIES is the number of retries after the initial request.
GEMINI_MAX_RETRIES = _positive_int_env("GEMINI_MAX_RETRIES", 3)
# The delay doubles after each retry: base, base * 2, base * 4, ...
GEMINI_RETRY_BASE_DELAY_SECONDS = _positive_float_env(
    "GEMINI_RETRY_BASE_DELAY_SECONDS", 1.0
)
RETRYABLE_GEMINI_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiServiceUnavailableError(Exception):
    """Raised when Gemini remains unavailable after all configured retries."""


def _gemini_status_code(error):
    """Return a HTTP status code from Google SDK exceptions when available."""
    for attribute in ("code", "status_code", "status"):
        value = getattr(error, attribute, None)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            match = re.search(r"\b(429|500|502|503|504)\b", str(value))
            if match:
                return int(match.group(1))

    match = re.search(r"\b(429|500|502|503|504)\b", str(error))
    return int(match.group(1)) if match else None


def generate_gemini_content(prompt):
    """Generate content, retrying only temporary Gemini/API availability failures."""
    client = genai.Client()
    total_attempts = GEMINI_MAX_RETRIES + 1

    for attempt in range(1, total_attempts + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                ),
            )
            return response.text.strip()
        except Exception as error:
            status_code = _gemini_status_code(error)
            retryable = status_code in RETRYABLE_GEMINI_STATUS_CODES

            logger.warning(
                "Gemini request attempt %d/%d failed with status %s: %s",
                attempt,
                total_attempts,
                status_code if status_code is not None else "unknown",
                error,
            )

            if not retryable:
                raise

            if attempt == total_attempts:
                raise GeminiServiceUnavailableError(
                    "Gemini is temporarily unavailable after "
                    f"{total_attempts} attempts (last status: {status_code})."
                ) from error

            delay = GEMINI_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            # A small jitter prevents concurrent requests from retrying together.
            delay += random.uniform(0, min(0.5, delay * 0.2))
            logger.info(
                "Retrying Gemini after %.2f seconds (next attempt %d/%d).",
                delay,
                attempt + 1,
                total_attempts,
            )
            time.sleep(delay)


def invoke_ankiconnect(ankiconnect_url, action, **params):
    payload = {"action": action, "version": 6, "params": params}
    try:
        response = requests.post(ankiconnect_url, json=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("error"):
            raise Exception(f"AnkiConnect error: {result['error']}")
        return result.get("result")
    except requests.exceptions.ConnectionError as ce:
        logger.error(f"Error: Could not connect to AnkiConnect at {ankiconnect_url}.")
        logger.error(
            "Please ensure Anki is running and AnkiConnect is installed and enabled."
        )
        raise ce
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise e


def sync_ankiconnect(ankiconnect_url):
    payload = {"action": "sync", "version": 6}
    try:
        response = requests.post(ankiconnect_url, json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Sync successful!")
        if result.get("error"):
            raise Exception(f"AnkiConnect error: {result['error']}")
    except requests.exceptions.ConnectionError as ce:
        logger.error(f"Error: Could not connect to AnkiConnect at {ankiconnect_url}.")
        logger.error(
            "Please ensure Anki is running and AnkiConnect is installed and enabled."
        )
        raise ce
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise e


def upload_audio(file_path: str, ankiconnect_url: str):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            audio_data = f.read()
        base64_audio = base64.b64encode(audio_data).decode("utf-8")
        if base64_audio:
            logger.info(f"Uploading audio: {os.path.basename(file_path)}")
            invoke_ankiconnect(
                ankiconnect_url,
                "storeMediaFile",
                filename=os.path.basename(file_path),
                data=base64_audio,
            )
        else:
            logger.warning(
                f"Warning: base64_audio is empty for {os.path.basename(file_path)}"
            )
    else:
        logger.warning(f"Warning: Audio file not found: {file_path}")


def get_sentence_with_word(word):
    """
    Generates a sentence with the given word using the Gemini API.

    Args:
      word: The word to be used in the sentence.

    Returns:
      A tuple containing the Japanese sentence, Romaji, and English translation.
    """
    text = generate_gemini_content(
        f"Write EXACTLY ONE simple sentence in Japanese using the word '{word}'. "
        "Format: [Japanese sentence] ([Romaji]) - [English translation] but without []"
    )

    # Use regex to parse the sentence.
    match = re.match(r"^(.*?)\s*\((.*?)\)\s*-\s*(.*)$", text)
    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip(),
            match.group(3).strip(),
        )

    logger.info(text)
    raise ValueError("Gemini returned a sentence in an unexpected format")


def get_sentence_with_word_english(word):
    """
    Generates a sentence with the given word using the Gemini API.

    Args:
      word: The word to be used in the sentence.

    Returns:
      A setence with the word.
    """
    return generate_gemini_content(
        f"Write a simple sentence using the word '{word}'. Format: [English setence]"
    ).strip("[]")


def get_definition(word):
    """
    Gets the definition of a word.

    Args:
      word: The word.

    Returns:
      A definition of the word.
    """
    return generate_gemini_content(
        f"Give a short definition of the word '{word}'. Format: [English definition]"
    ).strip("[]")


async def translate_to_japanese(word):
    """
    Translates a word from English to Japanese.

    Args:
      word: The English word to be translated.

    Returns:
      The translated word in Japanese.
    """
    try:
        translator = Translator()
        translation = await translator.translate(word, src="en", dest="ja")
        return translation.text
    except Exception as e:
        return f"Error in translation: {e}"


async def translate_to_english(word):
    """
    Translates a word from Japanese to English.

    Args:
      word: The Japanese word to be translated.

    Returns:
      The translated word in English.
    """
    try:
        translator = Translator()
        translation = await translator.translate(word, src="ja", dest="en")
        return translation.text
    except Exception as e:
        return f"Error in translation: {e}"


def identify_language(word):
    """
    Identifies whether a word is in Japanese or English.

    Args:
      word: The word to be analyzed.

    Returns:
      A string indicating whether the language is "Japanese", "English" or "Language not identified".
    """
    try:
        # Checks for the presence of Japanese characters (Hiragana, Katakana, Kanji)
        for char in word:
            # Unicode ranges for Japanese characters
            if (
                "\u3040" <= char <= "\u309f"
                or "\u30a0" <= char <= "\u30ff"  # Hiragana
                or "\u4e00" <= char <= "\u9fff"  # Katakana
            ):  # Kanji
                return "Japanese"
        return "English"

    except:
        logger.error("Language not identified")
        return "Language not identified"


def download_audio(text, lang, filename):
    """
    Generates and saves an audio file using gTTS.
    """
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save(filename)
        logger.info(f"Audio saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error downloading audio {filename}: {e}")
        return False


def japanese_to_hiragana(text: str) -> str:
    kakasi = pykakasi.kakasi()
    result = kakasi.convert(text)
    return "".join([item["hira"] for item in result])


def romaji_to_kana(romaji: str) -> str:
    try:
        response = requests.get(
            "https://api.romaji2kana.com/v1/to/hiragana", params={"q": romaji}
        )
        response.raise_for_status()
        kana_with_spaces = response.json()["a"]
        kana_no_spaces = kana_with_spaces.replace(" ", "")
        return kana_no_spaces
    except Exception as e:
        logger.error(f"Error: {e}")
        return ""


def empty_folder(folder_path):
    """
    Empty a folder, ignoring the .gitkeep file.
    """
    for item in os.listdir(folder_path):
        if item == ".gitkeep":
            continue
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            logger.error(f"Failed to delete {item_path}. Reason: {e}")


def addnote(ankiconnect_url, deck_name, word):
    # Ensure audios directory exists
    audio_dir = "audios"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    empty_folder(audio_dir)

    word = word.lower()
    language = identify_language(word)
    translation = ""
    english_word = ""
    if language == "English":
        english_word = word
        translation = asyncio.run(translate_to_japanese(word))
        japanese_sentence, romaji_sentence, english_sentence = get_sentence_with_word(
            translation
        )
    else:
        english_word = asyncio.run(translate_to_english(word)).lower()
        translation = word  # If the word is already Japanese, use it as the translation
        japanese_sentence, romaji_sentence, english_sentence = get_sentence_with_word(
            word
        )

    if not japanese_sentence or not romaji_sentence or not english_sentence:
        logger.warning(f"Skipping note for '{word}' due to sentence generation error.")
        raise Exception("Sentences not found")

    kana_word = japanese_to_hiragana(translation)
    kana_sentence = romaji_to_kana(romaji_sentence)

    logger.info(f"Processing '{word}':")
    logger.info(f"  Japanese Translation: {translation}")
    logger.info(f"  Kana: {kana_word}")
    logger.info(f"  English: {english_word}")
    logger.info(f"  Japanese Sentence: {japanese_sentence}")
    logger.info(f"  Kana Sentence: {kana_sentence}")
    logger.info(f"  English Sentence: {english_sentence}")

    # Speak the hiragana reading instead of the kanji. Japanese TTS can choose
    # an unintended reading for ambiguous compounds (for example, 黒板 may be
    # read as "kuroita" rather than "kokuban" when sent as kanji).
    word_audio_filename = os.path.join(audio_dir, f"{translation}.mp3")
    word_audio_success = download_audio(kana_word, "ja", word_audio_filename)

    # Download audio for the sentence
    sentence_audio_filename = os.path.join(audio_dir, f"{translation}_sentence.mp3")
    sentence_audio_success = download_audio(
        japanese_sentence, "ja", sentence_audio_filename
    )

    if not word_audio_success or not sentence_audio_success:
        logger.warning(f"Skipping note for '{word}' due to audio download error.")
        raise Exception("Audios not found")

    try:
        # Sync before adding so duplicate checks and writes use the latest deck state.
        logger.info("Syncing Anki before adding note...")
        sync_ankiconnect(ankiconnect_url)

        # Add to Anki
        logger.info("Adding note to Anki...")
        # Add note
        note = {
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": f'<span style="font-size: 60px;">{translation}</span><br>[sound:{os.path.basename(word_audio_filename)}]<br>{kana_word}',
                "Back": f'<span style="font-size: 40px;">{english_word}</span><br><span style="font-size: 30px;">{japanese_sentence}</span><br>{kana_sentence}<br>{english_sentence}<br>[sound:{os.path.basename(sentence_audio_filename)}]',
            },
            "options": {"allowDuplicate": False},
            "tags": ["japanese_anki_generator"],
        }
        invoke_ankiconnect(ankiconnect_url, "addNote", note=note)

        logger.info(f"Added note for: {translation}")

        logger.info("Uploading files...")

        # Upload word audio
        upload_audio(word_audio_filename, ankiconnect_url)

        # Upload sentence audio
        upload_audio(sentence_audio_filename, ankiconnect_url)

        # Sync after adding the note and its media files.
        logger.info("Syncing Anki after adding note...")
        sync_ankiconnect(ankiconnect_url)

    except Exception as e:
        logger.error(f"Skipping note for '{word}' due to error: {e}")
        raise e
    finally:
        logger.info("Emptying audio folder...")
        empty_folder(audio_dir)


def addnote_english(ankiconnect_url, deck_name, word):
    # Ensure audios directory exists
    audio_dir = "audios"
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)
    empty_folder(audio_dir)

    word = word.lower()
    language = identify_language(word)
    english_word = ""
    if language == "Japanese":
        english_word = asyncio.run(translate_to_english(word)).lower()
    else:
        english_word = word

    english_definition = get_definition(word)
    english_sentence = get_sentence_with_word_english(word)
    if not english_sentence or not english_definition:
        logger.warning(f"Skipping note for '{word}' due to generation error.")
        raise Exception("Sentence or definition not found")

    logger.info(f"Processing '{english_word}':")
    logger.info(f"  Definition: {english_definition}")
    logger.info(f"  English Sentence: {english_sentence}")

    # Download audio for the word
    word_audio_filename = os.path.join(audio_dir, f"{english_word}.mp3")
    word_audio_success = download_audio(english_word, "en", word_audio_filename)

    # Download audio for the sentence
    sentence_audio_filename = os.path.join(audio_dir, f"{english_word}_sentence.mp3")
    sentence_audio_success = download_audio(
        english_sentence, "en", sentence_audio_filename
    )

    if not word_audio_success or not sentence_audio_success:
        logger.warning(f"Skipping note for '{word}' due to audio download error.")
        raise Exception("Audios not found")

    try:
        # Sync before adding so duplicate checks and writes use the latest deck state.
        logger.info("Syncing Anki before adding note...")
        sync_ankiconnect(ankiconnect_url)

        # Add to Anki
        logger.info("Adding note to Anki...")
        # Add note
        note = {
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": f'<span style="font-size: 60px;">{english_word}</span><br>[sound:{os.path.basename(word_audio_filename)}]',
                "Back": f'<span style="font-size: 20px;">{english_definition}</span><br><br>{english_sentence}<br>[sound:{os.path.basename(sentence_audio_filename)}]',
            },
            "options": {"allowDuplicate": False},
            "tags": ["english_anki_generator"],
        }
        invoke_ankiconnect(ankiconnect_url, "addNote", note=note)

        logger.info(f"Added note for: {english_word}")

        logger.info("Uploading files...")

        # Upload word audio
        upload_audio(word_audio_filename, ankiconnect_url)

        # Upload sentence audio
        upload_audio(sentence_audio_filename, ankiconnect_url)

        # Sync after adding the note and its media files.
        logger.info("Syncing Anki after adding note...")
        sync_ankiconnect(ankiconnect_url)

    except Exception as e:
        logger.error(f"Skipping note for '{word}' due to error: {e}")
        raise e
    finally:
        logger.info("Emptying the audio folder...")
        empty_folder(audio_dir)
