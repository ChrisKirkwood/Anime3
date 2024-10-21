import re
import openai
import logging
import nltk
from nltk.corpus import words

nltk.download('words')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the English dictionary for validation
english_vocab = set(words.words())

# Define the whitelist for specific phrases
whitelist = {"At Onigashima"}

# Function to check if a subtitle is valid English (with a dictionary check)
def is_valid_english(text):
    tokens = text.split()
    valid_words = [word for word in tokens if word.lower() in english_vocab or word in whitelist]
    return len(valid_words) / len(tokens) > 0.5  # Consider valid if more than 50% are English words or whitelisted

# Function to check if a subtitle is valid
def is_valid_subtitle(subtitle):
    subtitle = subtitle.strip()
    # Always allow whitelisted subtitles
    if subtitle in whitelist:
        return True
    # Skip subtitles that are too short, numbers, or single characters (unless whitelisted)
    if len(subtitle) < 3 or re.match(r'^\d+$', subtitle) or len(subtitle.split()) <= 1:
        return False
    # Perform a dictionary check to filter out gibberish
    return is_valid_english(subtitle)

# Function to clean subtitles using OpenAI, while preserving the original meaning
def clean_subtitle_with_openai(subtitle):
    try:
        # Use OpenAI's new chat model to clean the subtitle
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a subtitle cleaning assistant. Your task is to clean subtitles for grammar and clarity without changing their meaning or adding extra details."},
                {"role": "user", "content": f"Please clean the following subtitle but preserve the meaning exactly: '{subtitle.strip()}'."}
            ],
            temperature=0.0,  # Reduce creativity
            max_tokens=50
        )
        cleaned_text = response['choices'][0]['message']['content'].strip()

        # Post-cleaning filter to remove irrelevant completions
        if any(keyword in cleaned_text for keyword in ["I'm ready", "help", "error", "context"]):
            logger.info(f"Skipping irrelevant OpenAI response: {cleaned_text}")
            return None

        return cleaned_text
    except Exception as e:
        logger.error(f"Error cleaning subtitle: {e}")
        return None

# Function to perform post-processing validation (check for significant changes)
def is_similar_to_original(original, cleaned):
    original_tokens = original.split()
    cleaned_tokens = cleaned.split()
    
    # Ensure that the cleaned version isn't drastically different in length
    length_difference = abs(len(original_tokens) - len(cleaned_tokens)) / len(original_tokens)
    if length_difference > 0.2:
        return False  # Too much difference in length
    return True

# Function to clean subtitles file and save results
def clean_subtitles_file(input_file, output_file):
    # Read the extracted subtitles from the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        subtitles = f.readlines()

    # Set to track unique cleaned subtitles to avoid duplicates
    seen_cleaned_subtitles = set()

    # Process each subtitle through OpenAI for cleaning
    cleaned_subtitles = []
    for line in subtitles:
        # Split the line on the first colon (timestamp:subtitle)
        try:
            timestamp, subtitle = line.strip().split(":", 1)
        except ValueError:
            logger.warning(f"Skipping malformed line: {line}")
            continue

        # Skip invalid or non-English subtitles
        if not is_valid_subtitle(subtitle):
            logger.info(f"Skipping invalid subtitle: {subtitle}")
            continue

        try:
            # Clean the subtitle using OpenAI
            cleaned_text = clean_subtitle_with_openai(subtitle.strip())

            # Ensure the cleaned text is valid and similar to the original subtitle
            if cleaned_text and cleaned_text not in seen_cleaned_subtitles and is_similar_to_original(subtitle, cleaned_text):
                cleaned_subtitles.append(f"{timestamp}: {cleaned_text}")
                seen_cleaned_subtitles.add(cleaned_text)  # Track cleaned subtitles
            else:
                logger.info(f"Skipping altered or duplicate subtitle: {cleaned_text}")

        except Exception as e:
            logger.error(f"Error cleaning subtitle: {e}")

    # Save the cleaned subtitles to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(cleaned_subtitles))

    logger.info(f"Cleaned subtitles saved to {output_file}") 
