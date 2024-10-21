import cv2
import io
import os
import logging
from google.cloud import vision
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
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

# Function to extract frames from the video and process them
def extract_subtitles_from_video(video_path, vision_client, frame_skip=30, similarity_threshold=0.85):
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
                    subtitles.append((frame_count / cap.get(cv2.CAP_PROP_FPS), detected_text))  # Store timestamp and text
                    last_detected_text = detected_text

            frame_count += 1

        cap.release()
        logger.info(f"Finished extracting subtitles from {video_path}")
        return subtitles

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None

# Function to save extracted subtitles to a file
def save_subtitles_to_file(subtitles, output_file):
    try:
        # Open the file with UTF-8 encoding
        with open(output_file, 'w', encoding='utf-8') as f:
            for timestamp, subtitle in subtitles:
                f.write(f"{timestamp:.2f}: {subtitle}\n")
        logger.info(f"Subtitles saved to {output_file}")
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
        # Save subtitles to a file
        save_subtitles_to_file(subtitles, output_file)

if __name__ == "__main__":
    video_path = "path_to_your_video.mp4"  # Replace with the path to your video
    output_file = "extracted_subtitles.txt"  # Replace with your desired output file

    main(video_path, output_file)
