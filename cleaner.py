import re
import openai
import logging
import nltk
from nltk.corpus import words
import os
from difflib import SequenceMatcher
import tiktoken
import hashlib
from langdetect import detect

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
    Normalizes the text by removing noise, standardizing cases, and keeping only meaningful characters.
    """
    try:
        logger.debug(f"Normalizing text: {text}")
        text = re.sub(r'\s+', ' ', text.lower())  # Normalize spaces and lowercase
        text = re.sub(r'[^\w\s]', '', text)  # Remove non-alphanumeric characters except spaces
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
    try:
        text1_normalized = normalize_text(text1)
        text2_normalized = normalize_text(text2)
        similarity = SequenceMatcher(None, text1_normalized, text2_normalized).ratio()
        logger.debug(f"Similarity between '{text1}' and '{text2}' is {similarity:.2f}.")
        return similarity >= threshold
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return False

# Function to check if a timestamp is validc
def is_valid_timestamp(timestamp):
    try:
        float(timestamp)
        return True
    except ValueError:
        logger.warning(f"Invalid timestamp: {timestamp}")
        return False


# Function for generating a unique hash
def generate_hash(text, timestamp=None, similarity_check=False, existing_hashes=None, similarity_threshold=0.94):
    """
    Generates a unique hash for the given text with enhancements for:
    - Hash-based deduplication for exact matches.
    - Similarity-based filtering for near-duplicates.
    - Contextual hashing considering text length and timestamp.
    - Language detection for processing only meaningful English subtitles.
    
    Args:
        text (str): The input subtitle text.
        timestamp (float, optional): The timestamp associated with the subtitle.
        similarity_check (bool): Whether to perform similarity checks for near-duplicates.
        existing_hashes (dict, optional): Existing hashes with their respective texts for similarity comparison.
        similarity_threshold (float): Threshold for text similarity (default is 0.94).
    
    Returns:
        str: The generated hash for the input text.
    """
    try:
        # Normalize the text
        normalized = normalize_text(text)
        logger.debug(f"Normalized text: '{normalized}' from original: '{text}'")

        # Perform language detection
        try:
            detected_language = detect(normalized)
            if detected_language != 'en':
                logger.info(f"Non-English text detected and skipped: '{text}' (Language: {detected_language})")
                return hashlib.md5(text.encode('utf-8')).hexdigest()  # Fallback hash
        except Exception as lang_error:
            logger.error(f"Language detection error for text '{text}': {lang_error}")
            return hashlib.md5(text.encode('utf-8')).hexdigest()  # Fallback hash

        # Ensure the normalized text is not empty
        if not normalized:
            logger.warning(f"Skipping subtitle '{text}' due to empty normalized text.")
            return hashlib.md5(text.encode('utf-8')).hexdigest()  # Fallback hash

        # Contextual hashing with timestamp
        hash_input = f"{normalized}-{len(normalized)}-{timestamp or 'no_time'}"
        hash_value = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
        logger.debug(f"Generated hash for text '{text}' with input '{hash_input}': {hash_value}")

        # Similarity-based filtering
        if similarity_check and existing_hashes is not None:
            for existing_hash, existing_text in existing_hashes.items():
                normalized_existing = normalize_text(existing_text)
                similarity = SequenceMatcher(None, normalized, normalized_existing).ratio()
                logger.debug(f"Similarity check: '{text}' vs '{existing_text}' -> {similarity:.2f}")
                if similarity >= similarity_threshold:
                    logger.info(f"Text '{text}' is similar to existing text '{existing_text}' (Similarity: {similarity:.2f})")
                    return existing_hash  # Return the hash of the similar text

        # Log the final decision to add the hash
        logger.info(f"Finalized hash for text '{text}': {hash_value}")
        return hash_value

    except Exception as e:
        logger.error(f"Error generating hash for text '{text}': {e}")
        return hashlib.md5(text.encode('utf-8')).hexdigest()  # Fallback hash


# Function to consolidate subtitles using hash-based deduplication
def hash_based_consolidate(subtitles_with_timestamps):
    """
    Consolidates subtitles using hash-based deduplication with single timestamps.

    Args:
        subtitles_with_timestamps (list): List of (timestamp, subtitle) tuples.

    Returns:
        list: Consolidated list of subtitles with single timestamps.
    """
    consolidated = {}
    for timestamp, subtitle in subtitles_with_timestamps:
        timestamp = float(timestamp)
        subtitle_hash = generate_hash(subtitle)
        logger.debug(f"Generated hash for subtitle '{subtitle}': {subtitle_hash}")

        if subtitle_hash is None:
            logger.warning(f"Skipping subtitle '{subtitle}' due to None hash value.")
            continue

        if subtitle_hash in consolidated:
            # Update the subtitle text, keeping the earliest timestamp
            existing = consolidated[subtitle_hash]
            existing['timestamps'].append(timestamp)
            existing['subtitle'] = f"{existing['subtitle']} {subtitle}"
            logger.debug(f"Updated existing group for hash {subtitle_hash}: {existing}")
        else:
            # Add a new subtitle entry
            consolidated[subtitle_hash] = {
                'timestamps': [timestamp],
                'subtitle': subtitle,
            }
            logger.debug(f"Created new group for hash {subtitle_hash}: {consolidated[subtitle_hash]}")

    # Convert consolidated dict to a list with single timestamps
    result = []
    for entry in consolidated.values():
        # Choose a single timestamp: earliest, latest, or midpoint
        timestamps = entry['timestamps']
        chosen_time = min(timestamps)  # Use the earliest timestamp
        # chosen_time = max(timestamps)  # Use the latest timestamp
        # chosen_time = sum(timestamps) / len(timestamps)  # Use the midpoint

        consolidated_subtitle = entry['subtitle']
        result.append(
            (
                f"{chosen_time:.2f}",
                consolidated_subtitle,
            )
        )
        logger.debug(f"Consolidated entry: Timestamp={chosen_time}, Subtitle='{consolidated_subtitle}'")

    logger.info(f"Consolidation complete. Total consolidated subtitles: {len(result)}")
    return result

# Function to merge a group of similar subtitles
def merge_group(group):
    """
    Merges a group of similar subtitles into one, using a single timestamp.

    Args:
        group (list): List of (timestamp, subtitle) tuples.

    Returns:
        tuple: Merged (timestamp, consolidated_subtitle).
    """
    logger.debug(f"Merging group: {group}")

    timestamps = [float(ts) for ts, _ in group]
    subtitles = {normalize_text(subtitle) for _, subtitle in group}  # Deduplicate within the group

    logger.debug(f"Extracted timestamps: {timestamps}")
    logger.debug(f"Normalized subtitles: {subtitles}")

    # Choose a single timestamp: earliest, latest, or midpoint
    chosen_time = min(timestamps)  # Use the earliest timestamp
    # chosen_time = max(timestamps)  # Use the latest timestamp
    # chosen_time = sum(timestamps) / len(timestamps)  # Use the midpoint

    consolidated_subtitle = " ".join(sorted(subtitles))  # Combine unique subtitles in order
    logger.debug(f"Chosen timestamp: {chosen_time}")
    logger.debug(f"Consolidated subtitle: {consolidated_subtitle}")

    return f"{chosen_time:.2f}", consolidated_subtitle


# Function to consolidate subtitles using time-based and text-based similarity
def remove_final_duplicates(subtitles_with_timestamps, similarity_threshold=0.95):
    """
    Removes exact and near duplicates from the final list of subtitles.

    Args:
        subtitles_with_timestamps (list): List of (timestamp, subtitle) tuples.
        similarity_threshold (float): Similarity threshold for near-duplicates.

    Returns:
        list: Cleaned list of (timestamp, subtitle) tuples.
    """
    seen = []
    cleaned_subtitles = []

    for timestamp, subtitle in subtitles_with_timestamps:
        normalized = normalize_text(subtitle)
        found_similar = False

        for i, (seen_timestamp, seen_normalized) in enumerate(seen):
            if is_similar(normalized, seen_normalized, threshold=similarity_threshold):
                # Merge the subtitles and update the timestamp
                merged_subtitle = f"{cleaned_subtitles[i][1]} {subtitle}"
                cleaned_subtitles[i] = (seen_timestamp, merged_subtitle)
                seen[i] = (seen_timestamp, normalize_text(merged_subtitle))
                found_similar = True
                logger.info(f"Near duplicate merged: {subtitle} with {cleaned_subtitles[i][1]}")
                break

        if not found_similar:
            seen.append((timestamp, normalized))
            cleaned_subtitles.append((timestamp, subtitle))

    return cleaned_subtitles

# Function to extract subtitles with timestamps
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
        line = line.strip()
        logger.debug(f"Processing line {idx}: {line}")
        if re.match(r"^\d+\.\d+:", line):  # Check for timestamp
            if current_timestamp and current_subtitle:  # Save previous block
                subtitles_with_timestamps.append((current_timestamp, " ".join(current_subtitle)))
                logger.debug(f"Added subtitle: {current_timestamp}: {' '.join(current_subtitle)}")
            try:
                current_timestamp, subtitle = line.split(":", 1)
                current_timestamp = current_timestamp.strip()
                current_subtitle = [subtitle.strip()]
                logger.debug(f"New timestamp block: {current_timestamp}")
            except ValueError:
                # Log malformed lines
                logger.warning(f"Malformed line at {idx}: {line}")
                continue
        else:
            if current_timestamp:  # Add to current block
                if current_subtitle and not current_subtitle[-1].endswith(('.', '?')):
                    current_subtitle.append(line)
                    logger.debug(f"Appending to current subtitle: {line}")
                else:
                    # Log lines without timestamps that are not continuations
                    logger.warning(f"Line without timestamp at {idx}: {line}")
            else:
                # Log lines without timestamps and no current timestamp
                logger.warning(f"Line without timestamp at {idx}: {line}")

    if current_timestamp and current_subtitle:  # Final block
        subtitles_with_timestamps.append((current_timestamp, " ".join(current_subtitle)))
        logger.debug(f"Finalized subtitle: {current_timestamp}: {' '.join(current_subtitle)}")

    # Validate timestamps after extracting all subtitles
    logger.info("Filtering subtitles with invalid timestamps...")
    valid_subtitles = [
        (timestamp, subtitle) for timestamp, subtitle in subtitles_with_timestamps
        if is_valid_timestamp(timestamp)
    ]

    # Log invalid timestamps for debugging
    invalid_count = len(subtitles_with_timestamps) - len(valid_subtitles)
    if invalid_count > 0:
        logger.warning(f"Filtered out {invalid_count} subtitles with invalid timestamps.")

    return valid_subtitles


# Use OpenAI API to clean a batch of subtitles
def clean_subtitles_with_openai_batch(subtitles_with_timestamps, max_tokens=1500):
    """
    Sends batches of subtitles with timestamps to OpenAI for cleaning,
    retaining valid subtitles with proper timestamps and removing artifacts.
    
    Args:
        subtitles_with_timestamps (list): List of (timestamp, subtitle) tuples.
        max_tokens (int): Maximum token count per batch.
    
    Returns:
        list: Cleaned subtitles from all batches.
    """
    try:
        # Batch the subtitles
        batches = batch_subtitles(subtitles_with_timestamps, max_tokens=max_tokens)
        logger.info(f"Created {len(batches)} batches for OpenAI processing.")

        cleaned_subtitles = []

        # Process each batch
        for batch_idx, batch in enumerate(batches, start=1):
            logger.info(f"Processing batch {batch_idx}/{len(batches)} with {len(batch)} subtitles.")

            # Construct the prompt for the batch
            prompt = (
                "You are a subtitle cleaning assistant. For each subtitle below:\n"
                "1. Clean grammar and ensure clarity while preserving meaning.\n"
                "2. Retain the timestamps and match cleaned subtitles to their timestamps.\n"
                "3. Remove entries that are gibberish, nonsensical, noise artifacts, or invalid (e.g., random characters, 'OOO', 'INN', 'www' 'Oppo').\n"
                "4. Exclude subtitles with fewer than 3 words or excessive repetition.\n"
                "5. Exclude subtitles only if they are entirely gibberish, nonsensical, or invalid after cleaning attempts. Do not exclude valid subtitles, even if minimal cleaning is needed to make them clear and meaningful.\n"
                "6. Return results in the format 'timestamp: cleaned subtitle'.\n"
                "7. If noise artifacts appear with valid subtitles, attempt to remove them while keeping the main content intact.\n"
                "8. Ensure that short subtitle entries are retained if they are valid and meaningful. For example, keep subtitles like 'I already know' with their original timestamp (e.g., 42.07), as they provide valuable context despite being concise.\n"
                "9. Consolidate duplicates and near duplicates into one coherent subtitle. With one time stamp. Be extra vigilant for near duplicates.\n"
                "10. If a subtitle shares a 60 percent similarity to another subtitle consider it a duplicate remove it.\n"
            )
            for timestamp, subtitle in batch:
                prompt += f"{timestamp}: {subtitle}\n"

            try:
                # Send the batch to OpenAI
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "You are a helpful assistant."},
                              {"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=1500  # Limit for cleaned output tokens
                )

                cleaned_text = response['choices'][0]['message']['content'].strip()
                logger.debug(f"OpenAI batch {batch_idx} response: {cleaned_text}")

                # Parse the cleaned batch response
                for line in cleaned_text.split("\n"):
                    if ":" not in line:
                        logger.warning(f"Malformed line in batch {batch_idx} skipped: {line}")
                        continue
                    parts = line.split(":", 1)  # Split into at most 2 parts
                    if len(parts) != 2:
                        logger.warning(f"Malformed line in batch {batch_idx} skipped: {line}")
                        continue
                    timestamp, subtitle = parts
                    cleaned_subtitles.append(f"{timestamp.strip()}: {subtitle.strip()}")

            except Exception as e:
                logger.error(f"Error cleaning batch {batch_idx}: {e}")
                continue

        logger.info(f"Successfully cleaned {len(cleaned_subtitles)} subtitles across all batches.")
        return cleaned_subtitles

    except Exception as e:
        logger.error(f"Error during batch cleaning: {e}")
        return []

# Clean subtitles from an input file and save results
def clean_subtitles_file(input_file, output_file, batch_size=10, iterations=2):
    """
    Processes subtitles from the input file, iteratively consolidates duplicates using hashing,
    sends them in batches to OpenAI for cleaning, and saves the cleaned results.

    Args:
        input_file (str): Path to the input subtitles file.
        output_file (str): Path to save the cleaned subtitles.
        batch_size (int): Number of subtitles to process in each OpenAI batch.
        iterations (int): Number of cleaning iterations to perform on the subtitles.
    """
    try:
        logger.info(f"Reading subtitles from file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_subtitles = f.readlines()

        logger.debug(f"Raw content of input file:\n{''.join(raw_subtitles)}")

        # Extract subtitles with timestamps
        subtitles_with_timestamps = extract_subtitles_with_timestamps(raw_subtitles)
        logger.info(f"Extracted {len(subtitles_with_timestamps)} valid subtitles.")

        for iteration in range(iterations):
            logger.info(f"Starting cleaning iteration {iteration + 1}/{iterations}")

            # Consolidate duplicates using hashing
            logger.info("Consolidating subtitles with hash-based deduplication.")
            subtitles_with_timestamps = hash_based_consolidate(subtitles_with_timestamps)
            logger.info(f"Iteration {iteration + 1}: Consolidated to {len(subtitles_with_timestamps)} subtitles.")

            # Save intermediate file with raw subtitles for debugging or validation
            intermediate_file = f"{os.path.splitext(output_file)[0]}_iteration_{iteration + 1}_pre_openai.txt"
            logger.info(f"Saving intermediate subtitles to: {intermediate_file}")
            with open(intermediate_file, 'w', encoding='utf-8') as f:
                for timestamp, subtitle in subtitles_with_timestamps:
                    f.write(f"{timestamp}: {subtitle}\n")
            logger.info(f"Intermediate subtitles for iteration {iteration + 1} saved successfully.")

            # Batch process with OpenAI
            logger.info("Starting batch processing for OpenAI subtitle cleaning.")
            cleaned_subtitles = []
            seen_cleaned_subtitles = set()

            for i in range(0, len(subtitles_with_timestamps), batch_size):
                batch = subtitles_with_timestamps[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1} with {len(batch)} subtitles.")

                # Clean the batch using OpenAI
                try:
                    cleaned_batch = clean_subtitles_with_openai_batch(batch)
                    if cleaned_batch:
                        for cleaned in cleaned_batch:
                            try:
                                # New logic to validate OpenAI output lines
                                if ":" not in cleaned:
                                    logger.warning(f"Malformed line in OpenAI output: {cleaned}")
                                    continue

                                parts = cleaned.split(":", 1)
                                if len(parts) != 2 or not is_valid_timestamp(parts[0]):
                                    logger.warning(f"Invalid line in OpenAI output: {cleaned}")
                                    continue

                                timestamp, subtitle = parts
                                timestamp = timestamp.strip()
                                subtitle = subtitle.strip()

                                # Validate the timestamp further
                                if not is_valid_timestamp(timestamp):
                                    raise ValueError(f"Invalid timestamp: {timestamp}")

                                cleaned_text = subtitle.strip()
                                if cleaned_text and cleaned_text not in seen_cleaned_subtitles:
                                    cleaned_subtitles.append((timestamp, cleaned_text))
                                    seen_cleaned_subtitles.add(cleaned_text)
                                    logger.debug(f"Added cleaned subtitle: {cleaned_text}")
                                else:
                                    logger.info(f"Skipped duplicate or invalid cleaned subtitle: {cleaned_text}")
                            except ValueError as ve:
                                logger.warning(f"Malformed cleaned line: {cleaned}. Error: {ve}")
                                continue
                except Exception as e:
                    logger.error(f"Error processing batch {i // batch_size + 1}: {e}")
                    continue

            # Sort cleaned subtitles by timestamp
            cleaned_subtitles.sort(key=lambda x: float(x[0]))
            subtitles_with_timestamps = cleaned_subtitles  # Update for the next iteration

            logger.info(f"Iteration {iteration + 1} completed. Total subtitles: {len(cleaned_subtitles)}")

        # Save final cleaned subtitles to file
        logger.info(f"Writing final cleaned subtitles to file: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for timestamp, subtitle in subtitles_with_timestamps:
                f.write(f"{timestamp}: {subtitle}\n")

        logger.info(f"Final cleaned subtitles successfully saved to {output_file}")

    except Exception as e:
        logger.error(f"Error cleaning subtitles file: {e}")


# Function to batch subtitles based on token limit
def batch_subtitles(subtitles_with_timestamps, max_tokens=1500):
    """
    Batches subtitles with timestamps into manageable groups based on token limits.
    
    Args:
        subtitles_with_timestamps (list): List of tuples (timestamp, subtitle).
        max_tokens (int): Maximum token count per batch.
    
    Returns:
        list of list of tuples: List of subtitle batches.
    """
    tokenizer = tiktoken.get_encoding("cl100k_base")  # Adjust encoding for your model
    batches = []
    current_batch = []
    current_tokens = 0

    for timestamp, subtitle in subtitles_with_timestamps:
        # Estimate token count for the subtitle and timestamp
        subtitle_tokens = len(tokenizer.encode(subtitle))
        timestamp_tokens = len(tokenizer.encode(timestamp))
        total_tokens = subtitle_tokens + timestamp_tokens

        if current_tokens + total_tokens > max_tokens:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append((timestamp, subtitle))
        current_tokens += total_tokens

    # Add the final batch
    if current_batch:
        batches.append(current_batch)

    return batches


# Entry point
if __name__ == "__main__":
    input_file = r"D:\Anime3\output\subtitles.txt"  # Replace with your input file path
    output_file = r"D:\Anime3\output\cleaned_subtitles.txt"  # Replace with your output file path

    logger.info("Starting subtitle cleaning script.")
    clean_subtitles_file(input_file, output_file)
    logger.info("Subtitle cleaning script completed.")