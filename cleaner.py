import re
import openai
import logging
import nltk
from nltk.corpus import words
import json
import os

nltk.download('words')

# Set up logging
log_file_path = r"D:\Anime3\log\backend.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Ensure the log directory exists

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),  # Append to the log file
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

# Load the English dictionary for validation
english_vocab = set(words.words())

# Path to the dynamic whitelist file
whitelist_file = "dynamic_whitelist.json"

# Function to load the dynamic whitelist
def load_whitelist():
    if os.path.exists(whitelist_file):
        with open(whitelist_file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

# Function to save the dynamic whitelist
def save_whitelist(whitelist):
    with open(whitelist_file, 'w', encoding='utf-8') as f:
        json.dump(list(whitelist), f, ensure_ascii=False, indent=4)

# Load initial whitelist
whitelist = load_whitelist()

# Function to check if a subtitle is valid English (with a dictionary check)
def is_valid_english(text):
    tokens = text.split()
    valid_words = [word for word in tokens if word.lower() in english_vocab or word in whitelist]
    return len(valid_words) / len(tokens) > 0.5  # Consider valid if more than 50% are English words or whitelisted

# Function to check if a subtitle is valid
def is_valid_subtitle(subtitle, flagged_as_valid):
    subtitle = subtitle.strip()
    # Always allow whitelisted or flagged valid subtitles
    if subtitle in whitelist or flagged_as_valid:
        return True
    # Skip subtitles that are too short, numbers, or single characters (unless whitelisted or flagged)
    if len(subtitle) < 3 or re.match(r'^\d+$', subtitle) or len(subtitle.split()) <= 1:
        return False
    # Perform a dictionary check to filter out gibberish
    return is_valid_english(subtitle)

# Function to dynamically add to the whitelist
def add_to_whitelist(subtitle):
    # Avoid adding single characters, numbers, or generic problematic entries
    if len(subtitle) <= 1 or re.match(r'^\d+$', subtitle) or subtitle.lower() in {"true", "false"}:
        logger.info(f"Rejected invalid subtitle for whitelist: {subtitle}")
        return
    if subtitle not in whitelist:
        whitelist.add(subtitle)
        save_whitelist(whitelist)
        logger.info(f"Added '{subtitle}' to the dynamic whitelist.")

# Batch processing for cleaning subtitles using OpenAI
def clean_subtitles_with_openai_batch(subtitles):
    try:
        # Construct a single prompt with all subtitles
        system_prompt = "You are a subtitle cleaning assistant. Clean each subtitle for grammar and clarity without changing its meaning or adding details. Keep only valid English words or phrases and remove any duplicates."
        user_prompt = "\n".join([f"{i + 1}. {subtitle}" for i, subtitle in enumerate(subtitles)])

        # Log the prompt for debugging
        logger.info(f"Batch prompt:\n{user_prompt}")

        # Use OpenAI's model for batch processing
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            max_tokens=4096 - len(user_prompt.split()),  # Reserve tokens for output
        )

        # Log the response for debugging
        logger.info(f"Batch response:\n{response['choices'][0]['message']['content']}")

        # Split the response into cleaned subtitles
        cleaned_text = response['choices'][0]['message']['content'].strip()
        cleaned_subtitles = cleaned_text.split('\n')

        # Ensure output aligns with input
        if len(cleaned_subtitles) != len(subtitles):
            logger.warning("Mismatch in the number of input and cleaned subtitles.")
            return None
        return cleaned_subtitles
    except Exception as e:
        logger.error(f"Error during batch cleaning: {e}")
        return None



# Function to clean subtitles file and save results
def clean_subtitles_file(input_file, output_file):
    # Read the extracted subtitles from the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        subtitles = f.readlines()

    # Set to track unique cleaned subtitles to avoid duplicates
    seen_cleaned_subtitles = set()

    # Prepare batches of subtitles for cleaning
    batch_size = 50  # Number of subtitles per batch
    all_subtitles = []
    timestamps = []
    flagged_subtitles = []

    for line in subtitles:
        try:
            # Split the line on the first colon (timestamp:subtitle)
            timestamp, subtitle = line.strip().split(":", 1)
            flagged_as_valid = "##flagged##" in subtitle
            subtitle = subtitle.replace("##flagged##", "").strip()

            # Skip invalid or non-English subtitles unless flagged
            if not is_valid_subtitle(subtitle, flagged_as_valid):
                if is_valid_english(subtitle):
                    add_to_whitelist(subtitle)
                    logger.info(f"Added to whitelist: {subtitle}")
                else:
                    logger.info(f"Skipping invalid subtitle: {subtitle}")
                continue

            timestamps.append(timestamp)
            all_subtitles.append(subtitle)
            flagged_subtitles.append(flagged_as_valid)
        except ValueError:
            logger.warning(f"Skipping malformed line: {line}")
            continue

    # Process subtitles in batches
    cleaned_results = []
    for i in range(0, len(all_subtitles), batch_size):
        batch = all_subtitles[i:i + batch_size]
        cleaned_batch = clean_subtitles_with_openai_batch(batch)

        if cleaned_batch:
            for j, cleaned_text in enumerate(cleaned_batch):
                if cleaned_text and cleaned_text not in seen_cleaned_subtitles:
                    cleaned_results.append(f"{timestamps[i + j]}: {cleaned_text}")
                    seen_cleaned_subtitles.add(cleaned_text)
        else:
            logger.warning(f"Batch cleaning failed for subtitles: {batch}")

    # Save the cleaned subtitles to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(cleaned_results))

    logger.info(f"Cleaned subtitles saved to {output_file}")
