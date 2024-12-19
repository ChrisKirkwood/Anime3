import cv2
import io
import os
import logging
import re
from google.cloud import vision
import numpy as np
from collections import Counter
import math
from difflib import SequenceMatcher
import openai
import concurrent.futures
import time

# Set up logging
log_file_path = r"D:\Anime3\log\backend.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)  # Ensure the log directory exists

logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level for detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),  # Append to the log file
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

# Set up OpenAI API key
try:
    openai.api_key = os.environ["OPENAI_API_KEY"]
    if not openai.api_key:
        raise KeyError("OpenAI API key is empty.")
    logger.info("OpenAI API key successfully loaded from environment.")
except KeyError:
    logger.error("OpenAI API key not found. Set it as the 'OPENAI_API_KEY' environment variable.")
    raise RuntimeError("OpenAI API key is required but not set.")

# Initialize the Google Cloud Vision client
def setup_vision_client():
    """
    Sets up the Google Cloud Vision API client.
    """
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise EnvironmentError("Google credentials not found. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        
        vision_client = vision.ImageAnnotatorClient()
        logger.info("Google Cloud Vision client successfully set up.")
        return vision_client
    except Exception as e:
        logger.error(f"Error setting up Vision client: {e}")
        return None

# Enhanced function to extract English text from a video frame using Google Cloud Vision API
def detect_text_from_frame(frame, vision_client):
    try:
        logger.debug("Starting text detection on the frame.")

        # Define the Region of Interest (ROI)
        height, width, _ = frame.shape
        roi_y_start = int(height * 0.8)  # Bottom 20% of the frame
        roi_y_end = height
        roi_x_start = 0
        roi_x_end = width

        # Crop the frame to the ROI
        cropped_frame = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
        logger.debug(f"Frame cropped to ROI: x={roi_x_start}:{roi_x_end}, y={roi_y_start}:{roi_y_end}")

        # Convert the cropped frame to JPEG bytes
        _, buffer = cv2.imencode('.jpg', cropped_frame)
        image_bytes = io.BytesIO(buffer).getvalue()
        logger.debug("Cropped frame successfully encoded into JPEG bytes.")

        # Create Vision API image object
        image = vision.Image(content=image_bytes)

        # Set the request with language hints for English
        image_context = vision.ImageContext(language_hints=['en'])
        logger.debug("Google Vision API request created with language hints set to 'en'.")

        # Call the Vision API text detection
        response = vision_client.text_detection(image=image, image_context=image_context)
        logger.debug("Google Vision API text detection response received.")

        # Log raw response for debugging
        if response.text_annotations:
            logger.debug(f"Vision API response text annotations: {response.text_annotations}")
        else:
            logger.debug("Vision API response contains no text annotations.")

        # Check for errors in the response
        if response.error.message:
            logger.error(f"Vision API returned an error: {response.error.message}")
            raise Exception(f"Vision API error: {response.error.message}")

        texts = response.text_annotations
        if not texts:
            logger.info("No text detected in the frame.")
            return None

        # Process the detected text
        detected_text = texts[0].description.strip()
        logger.debug(f"Raw detected text: '{detected_text}'")

        # Filter non-English text using heuristic: ASCII filtering
        if not is_likely_english(detected_text):
            logger.info(f"Detected text excluded as non-English or invalid: '{detected_text}'")
            return None

        logger.debug(f"Accepted English text: '{detected_text}'")
        return detected_text

    except Exception as e:
        logger.error(f"Error detecting text from frame: {e}")
        return None

# New function to detect text from a batch of frames
def detect_text_from_frames(frames, vision_client):
    """
    Detects text from a batch of video frames using Google Cloud Vision API.

    Args:
        frames (list): List of video frames.
        vision_client (vision.ImageAnnotatorClient): Initialized Google Cloud Vision API client.

    Returns:
        list: List of detected texts for each frame.
    """
    try:
        requests = []
        last_processed_frame = None  # Track the last processed frame for duplicate detection
        brightness_threshold = 10  # Threshold for skipping dark frames
        variance_threshold = 5  # Threshold for skipping solid frames
        valid_frames = []  # Store validated frames
        valid_indices = []  # Track indices of valid frames

        for idx, frame in enumerate(frames):
            # Check for low brightness (black frames)
            frame_mean = np.mean(frame)
            if frame_mean < brightness_threshold:
                logger.info(f"Skipped frame {idx} due to low brightness (mean: {frame_mean:.2f}).")
                continue

            # Check for low variance (solid or nearly solid frames)
            frame_variance = np.std(frame)
            if frame_variance < variance_threshold:
                logger.info(f"Skipped frame {idx} due to low variance (std: {frame_variance:.2f}).")
                continue

            # Check for duplicate frames
            if last_processed_frame is not None and np.array_equal(frame, last_processed_frame):
                logger.info(f"Skipped frame {idx} as it is identical to the last processed frame.")
                continue

            # Update the last processed frame
            last_processed_frame = frame

            # Define the Region of Interest (ROI)
            height, width, _ = frame.shape
            roi_y_start = int(height * 0.8)  # Bottom 20% of the frame
            roi_y_end = height
            roi_x_start = 0
            roi_x_end = width

            # Crop the frame to the ROI
            cropped_frame = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]
            logger.debug(f"Frame cropped to ROI: x={roi_x_start}:{roi_x_end}, y={roi_y_start}:{roi_y_end}")

            # Convert the cropped frame to JPEG bytes
            _, buffer = cv2.imencode('.jpg', cropped_frame)
            image_bytes = io.BytesIO(buffer).getvalue()
            logger.debug("Cropped frame successfully encoded into JPEG bytes.")

            # Create Vision API image object
            image = vision.Image(content=image_bytes)
            requests.append(vision.AnnotateImageRequest(
                image=image,
                features=[vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION)],
                image_context=vision.ImageContext(language_hints=['en'])
            ))
            valid_frames.append(frame)
            valid_indices.append(idx)

        # Send batch request only if there are valid frames
        if not requests:
            logger.info("No valid frames to process.")
            return [None] * len(frames)

        response = vision_client.batch_annotate_images(requests=requests)
        logger.debug("Google Vision API batch text detection response received.")

        detected_texts = [None] * len(frames)  # Default list with None for all frames
        for valid_idx, res in zip(valid_indices, response.responses):
            if res.error.message:
                logger.error(f"Vision API returned an error: {res.error.message}")
                detected_texts[valid_idx] = None
            elif res.text_annotations:
                detected_text = res.text_annotations[0].description.strip()
                logger.debug(f"Raw detected text: '{detected_text}'")
                if is_likely_english(detected_text):
                    logger.debug(f"Accepted English text: '{detected_text}'")
                    detected_texts[valid_idx] = detected_text
                else:
                    logger.info(f"Detected text excluded as non-English or invalid: '{detected_text}'")
                    detected_texts[valid_idx] = None
            else:
                logger.info("No text detected in the frame.")
                detected_texts[valid_idx] = None

        return detected_texts

    except Exception as e:
        logger.error(f"Error detecting text from frames: {e}")
        return [None] * len(frames)

def process_frame(frame, vision_client):
    """
    Validates a video frame and extracts text using Google Cloud OCR if valid.
    """
    # Validate the frame
    if frame is None:
        logger.info("Frame is None, skipping...")
        return None

    frame_mean = np.mean(frame)
    frame_std = np.std(frame)

    # Check for low brightness (blank frame)
    if frame_mean < 10:
        logger.info("Frame is too dark, skipping...")
        return None

    # Check for low variance (solid or near-solid frame)
    if frame_std < 5:
        logger.info("Frame has low variance, skipping...")
        return None

    # Define the Region of Interest (ROI)
    height, width, _ = frame.shape
    roi_y_start = int(height * 0.8)  # Bottom 20% of the frame
    roi_y_end = height
    roi_x_start = 0
    roi_x_end = width
    cropped_frame = frame[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

    # Convert cropped frame to JPEG bytes
    _, buffer = cv2.imencode('.jpg', cropped_frame)
    image_bytes = io.BytesIO(buffer).getvalue()

    # Perform OCR using Google Cloud Vision
    try:
        image = vision.Image(content=image_bytes)
        response = vision_client.text_detection(image=image)

        if response.error.message:
            logger.error(f"Google Vision error: {response.error.message}")
            return None

        texts = response.text_annotations
        if not texts:
            logger.info("No text detected.")
            return None

        # Return the first detected text
        return texts[0].description.strip()

    except Exception as e:
        logger.error(f"Error during text detection: {e}")
        return None

# Helper function to check if text is likely English
def is_likely_english(text):
    try:
        english_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-\"()[]")
        non_english_chars = [char for char in text if char not in english_chars]
        result = len(non_english_chars) / len(text) <= 0.1  # Adjust tolerance as needed

        logger.debug(f"Text '{text}' English validation: {result}, Non-English characters: {non_english_chars}")
        return result
    except Exception as e:
        logger.error(f"Error in English validation for text '{text}': {e}")
        return False


# Pre-filtering utilities: Entropy, Diversity, and Fuzzy Matching
def calculate_entropy(text):
    try:
        if not text:
            logger.debug("Entropy calculation skipped for empty text.")
            return 0

        counter = Counter(text)
        probabilities = [freq / len(text) for freq in counter.values()]
        entropy = -sum(p * math.log2(p) for p in probabilities)

        logger.debug(f"Entropy for text '{text}': {entropy:.4f}")
        return entropy
    except Exception as e:
        logger.error(f"Error calculating entropy for text '{text}': {e}")
        return 0


def is_high_entropy(text, threshold=2.0):  # Lower threshold for more inclusivity
    """
    Filters text based on entropy.
    """
    return calculate_entropy(text) > threshold

def has_character_diversity(text, threshold=0.4):  # Lower diversity threshold
    """
    Ensures text has sufficient character diversity.
    """
    unique_chars = set(text)
    return len(unique_chars) / len(text) > threshold

def is_similar(text1, text2, threshold=0.85):
    """
    Checks if two texts are similar above a certain threshold.
    """
    return SequenceMatcher(None, text1, text2).ratio() > threshold

# GPT Validation
def is_coherent_with_gpt(text, model="gpt-4", max_tokens=50):
    """
    Determines if a given text is coherent and meaningful using OpenAI's GPT models.
    """
    try:
        prompt = {
            "role": "user",
            "content": f"Is the following text meaningful as a subtitle? Reply 'Yes' or 'No'.\n\nText: \"{text}\""
        }

        response = openai.ChatCompletion.create(
            model=model,
            messages=[prompt],
            max_tokens=max_tokens,
            temperature=0.2
        )

        reply = response['choices'][0]['message']['content'].strip().lower()
        return reply == "yes"
    except Exception as e:
        logger.error(f"Error validating text with GPT: {e}")
        return False

# Filtering subtitles
def filter_subtitles(subtitles):
    filtered_subtitles = []
    last_text = None

    for timestamp, text in subtitles:
        logger.debug(f"Processing subtitle at timestamp {timestamp:.2f}: '{text}'")

        # Check duplication
        if last_text and is_similar(text, last_text):
            logger.info(f"Excluded as duplicate: '{text}'")
            continue

        # Check entropy
        entropy = calculate_entropy(text)
        if not is_high_entropy(text):
            logger.info(f"Excluded due to low entropy ({entropy:.4f}): '{text}'")
            continue

        # Check diversity
        diversity = has_character_diversity(text)
        if not diversity:
            logger.info(f"Excluded due to low diversity: '{text}'")
            continue

        # Add the subtitle to the accepted list
        filtered_subtitles.append((timestamp, text))
        last_text = text

    logger.info(f"Filtering complete. Accepted {len(filtered_subtitles)} out of {len(subtitles)} subtitles.")
    return filtered_subtitles


# Function to save filtered subtitles
def save_subtitles_to_file(subtitles, output_file):
    try:
        logger.info(f"Saving {len(subtitles)} subtitles to file: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            for timestamp, subtitle in subtitles:
                logger.debug(f"Saving subtitle: {timestamp:.2f}: {subtitle}")
                f.write(f"{timestamp:.2f}: {subtitle}\n")
    except Exception as e:
        logger.error(f"Error saving subtitles: {e}")


# Function to extract subtitles from video
def extract_subtitles_from_video(video_path, vision_client, initial_frame_skip=15, min_frame_skip=2, max_frame_skip=30, batch_size=32):
    """
    Extracts subtitles from the video by analyzing frames using Google Cloud Vision API with adaptive frame skipping.
    """
    try:
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video file: {video_path}")

        subtitles = []
        frame_count = 0
        last_detected_text = None
        frame_skip = initial_frame_skip  # Start with the initial frame skip
        fps = cap.get(cv2.CAP_PROP_FPS)
        batch_frames = []
        batch_timestamps = []

        # Use ThreadPoolExecutor for batch processing
        with concurrent.futures.ThreadPoolExecutor() as executor:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of video reached.")
                    break

                # Skip frames based on frame_skip
                if frame_count % frame_skip != 0:
                    frame_count += 1
                    continue

                # Add frame and timestamp to batch
                batch_frames.append(frame)
                batch_timestamps.append(frame_count / fps)

                # Process batch when ready
                if len(batch_frames) >= batch_size:
                    logger.info(f"Processing batch of {len(batch_frames)} frames.")
                    future = executor.submit(
                        lambda frames: [process_frame(f, vision_client) for f in frames],
                        batch_frames,
                    )
                    detected_texts = future.result()
                    for ts, text in zip(batch_timestamps, detected_texts):
                        if text:
                            subtitles.append((ts, text))
                            last_detected_text = text
                            frame_skip = max(min_frame_skip, frame_skip // 2)  # Reduce frame skip aggressively
                        else:
                            frame_skip = min(max_frame_skip, frame_skip * 2)  # Increase frame skip conservatively

                    batch_frames = []
                    batch_timestamps = []

                frame_count += 1

            # Process any remaining frames in the batch
            if batch_frames:
                logger.info(f"Processing remaining {len(batch_frames)} frames in the final batch.")
                detected_texts = [process_frame(f, vision_client) for f in batch_frames]
                for ts, text in zip(batch_timestamps, detected_texts):
                    if text:
                        subtitles.append((ts, text))

        cap.release()
        return subtitles

    except Exception as e:
        logger.error(f"Error extracting subtitles from video: {e}")
        return []




# Main function to run the subtitle extraction
def main(video_path, output_file, batch_size=16):
    """
    Main function to extract and save subtitles from a video file.
    Args:
        video_path (str): Path to the video file.
        output_file (str): Path to save the extracted subtitles.
        batch_size (int): Number of frames to process in each batch.
    """
    try:
        vision_client = setup_vision_client()
        if not vision_client:
            raise RuntimeError("Vision client setup failed. Exiting pipeline.")

        # Pass batch_size to the extract_subtitles_from_video function
        subtitles = extract_subtitles_from_video(video_path, vision_client, batch_size=batch_size)
        save_subtitles_to_file(subtitles, output_file)

    except Exception as e:
        logger.error(f"Fatal error in main pipeline: {e}")


if __name__ == "__main__":
    video_path = "path_to_your_video.mp4"  # Replace with the path to your video
    output_file = "extracted_subtitles.txt"  # Replace with your desired output file
    batch_size = 16  # Adjust as needed

    main(video_path, output_file, batch_size=batch_size)