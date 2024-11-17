import cv2
import io
import os
import logging
import json
from google.cloud import vision
import numpy as np

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

# Initialize the Google Cloud Vision client
def setup_vision_client():
    try:
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
            raise EnvironmentError("Google credentials not found. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        
        vision_client = vision.ImageAnnotatorClient()
        logger.info("Google Cloud Vision client successfully set up.")
        return vision_client
    except Exception as e:
        logger.error(f"Error setting up Vision client: {e}")
        return None

# Function to extract text from a video frame using Google Vision API
def detect_text_from_frame(frame, vision_client):
    try:
        logger.info("Starting text detection on the frame")
        
        # Convert frame to bytes
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = io.BytesIO(buffer).getvalue()

        # Create a Vision API image object
        image = vision.Image(content=image_bytes)

        # Use Vision API to detect text in the image
        response = vision_client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            detected_text = texts[0].description.strip()
            logger.info(f"Detected text: {detected_text}")
            return detected_text
        else:
            logger.info("No text detected in the frame.")
            return None
    except Exception as e:
        logger.error(f"Error detecting text from frame: {e}")
        return None

# Function to validate subtitles
def validate_subtitle(subtitle):
    # Define your validation logic here
    if len(subtitle) < 3:  # Too short
        return False
    if subtitle.isdigit():  # Only numbers
        return False
    if len(subtitle.split()) <= 1:  # Single-word subtitles
        return False
    return True  # Passes validation

# Function to extract frames from the video and process them
def extract_subtitles_from_video(video_path, vision_client, frame_skip=30):
    try:
        # Open video file
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Error: Could not open video {video_path}")

        frame_count = 0
        subtitles = []
        last_detected_text = None

        # Loop through video frames
        while True:
            ret, frame = cap.read()

            if not ret:
                break  # End of video

            # Process every nth frame, where n is defined by frame_skip
            if frame_count % frame_skip == 0:
                logger.info(f"Processing frame {frame_count}")
                detected_text = detect_text_from_frame(frame, vision_client)

                # Skip if the subtitle is too similar to the previous one
                if detected_text and (last_detected_text is None or detected_text != last_detected_text):
                    is_valid = validate_subtitle(detected_text)
                    subtitles.append({
                        "timestamp": frame_count / cap.get(cv2.CAP_PROP_FPS),
                        "text": detected_text,
                        "valid": is_valid
                    })
                    last_detected_text = detected_text

            frame_count += 1

        cap.release()
        logger.info(f"Finished extracting subtitles from {video_path}")
        return subtitles

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None

# Function to save extracted subtitles to a JSON file
def save_subtitles_to_json(subtitles, output_file):
    try:
        # Save subtitles with flags to a JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=4)
        logger.info(f"Subtitles with flags saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving subtitles to file: {e}")

# Main function to run the subtitle extraction
def main(video_path, output_file):
    # Setup Google Cloud Vision client
    vision_client = setup_vision_client()

    if vision_client is None:
        logger.error("Google Vision client setup failed.")
        return

    # Extract subtitles from video
    subtitles = extract_subtitles_from_video(video_path, vision_client)

    if subtitles:
        # Save subtitles to a JSON file
        save_subtitles_to_json(subtitles, output_file)

if __name__ == "__main__":
    video_path = "path_to_your_video.mp4"  # Replace with the path to your video
    output_file = "extracted_subtitles.json"  # Replace with your desired output file

    main(video_path, output_file)
