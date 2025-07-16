# Add Anki Cards (Japanese & English)

This web application provides a simple interface to add flashcards to your Anki collection for both Japanese and English vocabulary. It automates the process of translation, sentence generation, audio creation, and card formatting.

## Features

-   **Dual Language Support:** Add cards for either Japanese or English.
-   **Automatic Translation:** Provide a word in English to get a Japanese card, or vice-versa.
-   **AI-Powered Content:** Uses the Google Gemini API to generate example sentences and definitions, providing rich context for vocabulary.
-   **Audio Generation:** Automatically generates and attaches audio for words and example sentences using Google Text-to-Speech (gTTS).
-   **Rich Formatting (Japanese):** Automatically generates Furigana (Hiragana) for Japanese words and Kana for example sentences.
-   **Direct Anki Integration:** Connects directly to your running Anki desktop application using the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on.
-   **Containerized:** Runs in a Docker container for easy setup and deployment.
-   **Optional Container Management:** Can be configured to start/stop a specified Anki Docker container via a Portainer API, ensuring Anki is running when you need it.

## How it Works

The application exposes a simple API endpoint (`/api/addnote`) that takes a word and a desired deck.

### For Japanese Cards:

1.  **Input:** A word (either Japanese or English).
2.  **Translation:** If the word is in English, it's translated to Japanese.
3.  **Content Generation:** Google Gemini generates a simple Japanese example sentence using the word.
4.  **Furigana/Kana:** The application generates Hiragana for the main word and Kana for the example sentence.
5.  **Audio:** gTTS creates audio files for both the Japanese word and the example sentence.
6.  **Anki Card Creation:** A new "Basic" note is created with:
    -   **Front:** Japanese word (large font), audio, and Hiragana.
    -   **Back:** English translation, the full Japanese example sentence, the Kana version of the sentence, the English translation of the sentence, and the sentence audio.

### For English Cards:

1.  **Input:** A word (either Japanese or English).
2.  **Translation:** If the word is in Japanese, it's translated to English.
3.  **Content Generation:** Google Gemini generates a short definition and a simple example sentence for the English word.
4.  **Audio:** gTTS creates audio files for both the English word and the example sentence.
5.  **Anki Card Creation:** A new "Basic" note is created with:
    -   **Front:** English word (large font) and audio.
    -   **Back:** The definition, the example sentence, and the sentence audio.

## Requirements

-   **Docker:** To run the application container.
-   **Anki Desktop:** The Anki application must be running on your machine or on a server.
-   **AnkiConnect Add-on:** You must have the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed in Anki and configured to allow requests from the application's address.
-   **Google API Key:** You need a valid API key for the Google Gemini API.

## Usage

The recommended way to run this application is with `docker-compose`.

### 1. Using `docker-compose`

A `docker-compose.yml` file is provided for convenience.

1.  **Create a `.env` file:** Create a file named `.env` in the project root and add the following environment variables, replacing the placeholder values with your own.

    ```
    FLASK_APP=run.py
    FLASK_ENV=production
    SECRET_KEY='your-secret-key'
    GOOGLE_API_KEY='your-google-api-key'
    ANKICONNECT_URL='http://localhost:8765'

    # --- Optional: For Portainer Integration ---
    HANDLE_CONTAINER=true
    PORTAINER_URL='http://localhost:9000'
    PORTAINER_USERNAME='your-portainer-user'
    PORTAINER_PASSWORD='your-portainer-password'
    PORTAINER_ENDPOINT_ID=1
    PORTAINER_CONTAINER_ID='your-anki-container-id-or-name'
    ```

2.  **Run the container:**
    ```bash
    docker-compose up -d
    ```

The application will be available at `http://localhost:5000`.

### 2. Using `docker run`

You can also run the application using the `docker run` command.

```bash
docker run -d -p 5000:5000 \
  -e FLASK_APP=run.py \
  -e FLASK_ENV=production \
  -e SECRET_KEY='your-secret-key' \
  -e GOOGLE_API_KEY='your-google-api-key' \
  -e ANKICONNECT_URL='http://localhost:8765' \
  # Optional
  -e HANDLE_CONTAINER=true \
  -e PORTAINER_URL='http://localhost:9000' \
  -e PORTAINER_USERNAME='your-portainer-user' \
  -e PORTAINER_PASSWORD='your-portainer-password' \
  -e PORTAINER_ENDPOINT_ID=1 \
  -e PORTAINER_CONTAINER_ID='your-anki-container-id-or-name' \
  lhuckaz/add-japanese-anki-web
```

### Environment Variables

-   `SECRET_KEY`: A secret key for Flask sessions.
-   `GOOGLE_API_KEY`: Your API key for Google Gemini.
-   `ANKICONNECT_URL`: The full URL to your AnkiConnect instance (e.g., `http://localhost:8765`).

Optional:
-   `HANDLE_CONTAINER`: Set to `true` to enable the Portainer integration for managing the Anki container.
-   `PORTAINER_URL`: URL for your Portainer instance.
-   `PORTAINER_USERNAME`: Your Portainer username.
-   `PORTAINER_PASSWORD`: Your Portainer password or an access token.
-   `PORTAINER_ENDPOINT_ID`: The ID of the Portainer endpoint where the Anki container is running.
-   `PORTAINER_CONTAINER_ID`: The ID or name of the Anki container to be managed.