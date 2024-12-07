import re
import openai
import logging
import nltk
from nltk.corpus import words
import os
from difflib import SequenceMatcher

# Ensure NLTK's words corpus is downloaded
nltk.download('words')

# Set up logging
log_file_path = r"D:\Anime3\log\backend.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Ensure the log directory exists

logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),  # Append to the log file
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

# Load the English dictionary for validation
english_vocab = set(words.words())

# Define a whitelist for specific phrases that are always allowed
whitelist = {"At Onigashima", "Raftel", "Kaido", "Onigashima"}

# Normalize and clean text
def normalize_text(text):
    """
    Cleans up detected text by removing extraneous characters and normalizing spacing.
    """
    try:
        logger.debug(f"Normalizing text: {text}")
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        text = re.sub(r'[^\w .,!?\'"-]', '', text)  # Remove special characters
        normalized = text.strip()
        logger.debug(f"Normalized text: {normalized}")
        return normalized
    except Exception as e:
        logger.error(f"Error normalizing text: {e}")
        return text

# Check if text is valid English
def is_valid_english(text):
    """
    Determines if text is valid English using a combination of word and character checks.
    """
    try:
        logger.debug(f"Validating English text: {text}")
        tokens = text.split()
        if not tokens:
            logger.debug("Text contains no valid tokens.")
            return False

        valid_words = [word for word in tokens if word.lower() in english_vocab or word in whitelist]
        word_score = len(valid_words) / len(tokens)
        logger.debug(f"Word score: {word_score:.2f}")

        english_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-")
        char_score = sum(1 for char in text if char in english_chars) / len(text)
        logger.debug(f"Character score: {char_score:.2f}")

        valid = word_score > 0.5 or char_score > 0.7
        logger.debug(f"Text is {'valid' if valid else 'invalid'} based on scores.")
        return valid
    except Exception as e:
        logger.error(f"Error validating English text: {e}")
        return False

# Simplify subtitle validation
def is_valid_subtitle(subtitle):
    """
    Validates a subtitle's structure and content for cleaning.
    """
    try:
        logger.debug(f"Validating subtitle: {subtitle}")
        subtitle = subtitle.strip()
        if len(subtitle) < 2:
            logger.debug("Subtitle is too short.")
            return False
        if subtitle.isnumeric():
            logger.debug("Subtitle is purely numeric.")
            return False
        if not any(char.isalpha() for char in subtitle):
            logger.debug("Subtitle contains no alphabetic characters.")
            return False
        valid = is_valid_english(subtitle)
        logger.debug(f"Subtitle is {'valid' if valid else 'invalid'}.")
        return valid
    except Exception as e:
        logger.error(f"Error validating subtitle: {e}")
        return False

# Check similarity between subtitles
def is_similar(text1, text2, threshold=0.85):
    """
    Checks similarity between two text strings using Levenshtein ratio.
    """
    try:
        similarity = SequenceMatcher(None, text1, text2).ratio()
        logger.debug(f"Similarity between '{text1}' and '{text2}' is {similarity:.2f}.")
        return similarity > threshold
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return False

# Use OpenAI API to clean a batch of subtitles
def clean_subtitles_with_openai_batch(subtitles_with_timestamps):
    """
    Sends a batch of subtitles with timestamps to OpenAI for cleaning,
    retaining valid subtitles with proper timestamps and removing artifacts.
    """
    try:
        logger.debug(f"Sending batch of {len(subtitles_with_timestamps)} subtitles with timestamps to OpenAI.")

        # Construct a prompt with explicit cleaning and timestamp retention instructions
        prompt = (
    "You are a subtitle cleaning assistant. For each subtitle below:\n"
    "1. Clean grammar and ensure clarity while preserving meaning.\n"
    "2. Retain the timestamps and match cleaned subtitles to their timestamps.\n"
    "3. Remove entries that are gibberish, nonsensical, noise artifacts, or invalid (e.g., random characters, 'OOO', 'INN', 'www' 'Oppo').\n"
    "4. Exclude subtitles with fewer than 3 words or excessive repetition.\n"
    "5. Exclude subtitles only if they are entirely gibberish, nonsensical, or invalid after cleaning attempts. Do not exclude valid subtitles, even if minimal cleaning is needed to make them clear and meaningful.\n"
    "6. Return results in the format 'timestamp: cleaned subtitle'.\n"
    "7. If noise artifacts appear with valid subtitles, attempt to remove them while keeping the main content intact.\n"
)
        for timestamp, subtitle in subtitles_with_timestamps:
            prompt += f"{timestamp}: {subtitle}\n"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1500  # Adjust based on subtitle length and batch size
        )

        cleaned_text = response['choices'][0]['message']['content'].strip()
        logger.debug(f"OpenAI batch response: {cleaned_text}")

        # Parse the cleaned batch response
        cleaned_subtitles = []
        for line in cleaned_text.split("\n"):
            if ":" not in line:
                logger.warning(f"Malformed line skipped: {line}")
                continue
            parts = line.split(":", 1)  # Split into at most 2 parts
            if len(parts) != 2:
                logger.warning(f"Malformed line skipped: {line}")
                continue
            timestamp, subtitle = parts
            cleaned_subtitles.append(f"{timestamp.strip()}: {subtitle.strip()}")
        
        logger.debug(f"Parsed cleaned subtitles: {cleaned_subtitles}")
        return cleaned_subtitles

    except Exception as e:
        logger.error(f"Error cleaning subtitles batch with OpenAI: {e}")
        return []

def extract_subtitles_with_timestamps(raw_subtitles):
    """
    Parses raw subtitles into a list of (timestamp, subtitle) tuples, handling multiline subtitles.

    Args:
        raw_subtitles (list of str): List of raw subtitle lines from the input file.

    Returns:
        list of tuples: List of (timestamp, subtitle) pairs.
    """
    subtitles_with_timestamps = []
    current_timestamp = None
    current_subtitle = []

    for idx, line in enumerate(raw_subtitles, 1):
        line = line.strip()  # Remove whitespace
        if ":" in line:  # Likely a timestamp line
            if current_timestamp is not None:  # Save the previous subtitle
                subtitles_with_timestamps.append(
                    (current_timestamp, " ".join(current_subtitle))
                )
                logger.debug(f"[Line {idx}] Parsed: Timestamp='{current_timestamp}', Subtitle='{' '.join(current_subtitle)}'")

            # Start a new subtitle block
            try:
                current_timestamp, subtitle = line.split(":", 1)
                current_timestamp = current_timestamp.strip()
                current_subtitle = [subtitle.strip()]
            except ValueError:
                logger.warning(f"[Line {idx}] Failed to parse line: {line}")
                continue
        else:  # Continuation of the previous subtitle
            if current_timestamp is not None:
                current_subtitle.append(line)
            else:
                logger.warning(f"[Line {idx}] Unhandled line without timestamp: {line}")

    # Save the last subtitle
    if current_timestamp is not None:
        subtitles_with_timestamps.append(
            (current_timestamp, " ".join(current_subtitle))
        )
        logger.debug(f"Finalized: Timestamp='{current_timestamp}', Subtitle='{' '.join(current_subtitle)}'")

    return subtitles_with_timestamps



# Clean subtitles from an input file and save results
def clean_subtitles_file(input_file, output_file):
    """
    Processes subtitles from the input file, sends them in a batch to OpenAI for cleaning,
    retains timestamps, and saves the cleaned results.
    """
    try:
        logger.info(f"Reading subtitles from file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_subtitles = f.readlines()

        logger.debug(f"Raw content of input file:\n{''.join(raw_subtitles)}")

        # Extract subtitles with timestamps using the updated function
        subtitles_with_timestamps = extract_subtitles_with_timestamps(raw_subtitles)

        logger.info(f"Extracted {len(subtitles_with_timestamps)} valid subtitles.")

        seen_cleaned_subtitles = set()

        # Batch process with OpenAI
        cleaned_subtitles = []
        if subtitles_with_timestamps:
            logger.info("Sending subtitles with timestamps to OpenAI for batch cleaning.")
            cleaned_batch = clean_subtitles_with_openai_batch(subtitles_with_timestamps)

            if cleaned_batch:
                for cleaned in cleaned_batch:
                    try:
                        timestamp, subtitle = cleaned.split(":", 1)
                        cleaned_text = subtitle.strip()
                        if cleaned_text and cleaned_text not in seen_cleaned_subtitles:
                            cleaned_subtitles.append(cleaned)
                            seen_cleaned_subtitles.add(cleaned_text)
                            logger.debug(f"Added cleaned subtitle: {cleaned_text}")
                        else:
                            logger.info(f"Skipped duplicate or invalid cleaned subtitle: {cleaned_text}")
                    except ValueError as ve:
                        logger.warning(f"Malformed cleaned line: {cleaned}. Error: {ve}")
                        continue

        logger.info(f"Writing cleaned subtitles to file: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(cleaned_subtitles))

        logger.info(f"Cleaned subtitles successfully saved to {output_file}")
    except Exception as e:
        logger.error(f"Error cleaning subtitles file: {e}")



# Entry point
if __name__ == "__main__":
    input_file = r"D:\Anime3\output\subtitles.txt"  # Replace with your input file path
    output_file = r"D:\Anime3\output\cleaned_subtitles.txt"  # Replace with your output file path

    logger.info("Starting subtitle cleaning script.")
    clean_subtitles_file(input_file, output_file)
    logger.info("Subtitle cleaning script completed.")