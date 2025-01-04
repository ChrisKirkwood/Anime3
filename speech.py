import os
from google.cloud import texttospeech
from pydub import AudioSegment
import logging
import time
import io



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

# Set up Google Cloud Text-to-Speech client
def setup_tts_client():
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        raise EnvironmentError("Google Cloud credentials not found. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable.")
    
    client = texttospeech.TextToSpeechClient()
    logger.info("Google Cloud Text-to-Speech client successfully set up.")
    return client

# Function to synthesize speech and return it as an AudioSegment
def synthesize_speech_to_audio_segment(subtitle, tts_client):
    """
    Synthesizes speech from text and returns it as an AudioSegment.
    Args:
        subtitle (str): The text to synthesize.
        tts_client: Initialized Google Cloud TTS client.
    Returns:
        AudioSegment: The synthesized audio as an AudioSegment object.
    """
    synthesis_input = texttospeech.SynthesisInput(text=subtitle)

    # Configure voice and audio settings
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the synthesis request
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    # Convert the audio content to an AudioSegment
    return AudioSegment.from_file(io.BytesIO(response.audio_content), format="mp3")

# Function to batch subtitles for synthesis
def batch_subtitles(subtitles, max_batch_size=10):
    for i in range(0, len(subtitles), max_batch_size):
        yield subtitles[i:i + max_batch_size]

# Function to synthesize subtitles into speech with correct timing alignment
def synthesize_subtitles(input_file, output_dir, tts_client, start_index=1, batch_delay=5, max_batch_size=10, current_time_in_ms=0):
    """
    Synthesizes speech from cleaned subtitles and saves the audio files in batches.

    Args:
        input_file (str): Path to the cleaned subtitles file.
        output_dir (str): Directory to save the audio files.
        tts_client: Initialized Google Cloud TTS client.
        start_index (int): Starting index for the audio file naming.
        batch_delay (int): Delay between batches to avoid rate limits.
        max_batch_size (int): Maximum number of subtitles to process in each batch.
        current_time_in_ms (int): Current cumulative time in milliseconds.

    Returns:
        tuple: The next starting index for subsequent batches and the updated current_time_in_ms.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r', encoding='utf-8') as f:
        subtitles = f.readlines()

    for batch_idx, batch in enumerate(batch_subtitles(subtitles, max_batch_size=max_batch_size), start=1):
        logger.info(f"Processing batch {batch_idx} with {len(batch)} subtitles.")
        logger.info(f"Starting batch {batch_idx} with current_time_in_ms: {current_time_in_ms}")

        numbered_audio_file = os.path.join(output_dir, f"final_synthesized_audio_{start_index}.mp3")
        while os.path.exists(numbered_audio_file):
            start_index += 1
            numbered_audio_file = os.path.join(output_dir, f"final_synthesized_audio_{start_index}.mp3")

        combined_audio = AudioSegment.silent(duration=0)

        try:
            # Extract the first timestamp and normalize
            first_timestamp = float(batch[0].split(":")[0]) * 1000  # Convert to milliseconds
            initial_silence_padding = max(0, int(first_timestamp - current_time_in_ms))
            combined_audio += AudioSegment.silent(duration=initial_silence_padding)
            current_time_in_ms += initial_silence_padding

            logger.info(f"Batch {batch_idx}: first_timestamp={first_timestamp}, initial_silence_padding={initial_silence_padding}")

        except Exception as e:
            logger.error(f"Error extracting first timestamp in batch {batch_idx}: {e}")
            continue

        for idx, line in enumerate(batch):
            try:
                timestamp, subtitle = line.strip().split(":", 1)
                subtitle = subtitle.strip()
                if not subtitle:
                    continue

                # Calculate silence required before this subtitle
                normalized_timestamp = max(0, int(float(timestamp) * 1000) - first_timestamp)
                silence_duration = max(0, normalized_timestamp - current_time_in_ms)

                logger.info(f"Subtitle {idx}: timestamp={timestamp}, normalized_timestamp={normalized_timestamp}, silence_duration={silence_duration}")

                if silence_duration > 0:
                    combined_audio += AudioSegment.silent(duration=silence_duration)
                    current_time_in_ms += silence_duration

                # Generate audio for the subtitle
                generated_audio = synthesize_speech_to_audio_segment(subtitle, tts_client)
                combined_audio += generated_audio
                current_time_in_ms += len(generated_audio)

                logger.info(f"Subtitle {idx}: generated_audio_duration={len(generated_audio)}, current_time_in_ms={current_time_in_ms}")

                # Handle gaps between subtitles
                if idx < len(batch) - 1:
                    next_timestamp = float(batch[idx + 1].split(":")[0]) * 1000
                    gap_duration = max(0, int(next_timestamp) - current_time_in_ms)
                    if gap_duration > 0:
                        combined_audio += AudioSegment.silent(duration=gap_duration)
                        current_time_in_ms += gap_duration

                        logger.info(f"Subtitle {idx}: gap_duration_to_next_subtitle={gap_duration}, updated_current_time_in_ms={current_time_in_ms}")

            except Exception as e:
                logger.error(f"Error processing subtitle line '{line.strip()}': {e}")

        # Export the combined audio for this batch
        combined_audio.export(numbered_audio_file, format="mp3")
        logger.info(f"Batch {batch_idx} audio saved to {numbered_audio_file}")

        # Increment the start index for the next batch
        start_index += 1
        time.sleep(batch_delay)

    logger.info(f"Final current_time_in_ms after batch {batch_idx}: {current_time_in_ms}")
    return start_index, current_time_in_ms








# Main function to handle the process
def main(input_file, output_dir):
    # Initialize the Google Cloud TTS client
    tts_client = setup_tts_client()

    # Initialize the starting index
    current_index = 1

    # Convert subtitles to speech with timing alignment
    current_index = synthesize_subtitles(input_file, output_dir, tts_client, start_index=current_index)

    # If there are more batches or chunks to process, continue with the updated index
    # Example: current_index = process_chunks(chunks, output_dir, tts_client, start_index=current_index)

if __name__ == "__main__":
    # Replace with your paths
    input_file = "path_to_cleaned_subtitles.txt"  # Path to the cleaned subtitle file
    output_dir = "path_to_output_audio_files"  # Directory to save the audio files
    main(input_file, output_dir)
