import os
from google.cloud import texttospeech
import re
from pydub import AudioSegment
import logging
import time

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

# Function to synthesize speech from text
def synthesize_speech(text, output_file, tts_client):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the voice name
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3  # You can change to other formats like LINEAR16, etc.
    )

    # Perform the text-to-speech request on the text input with the selected voice parameters and audio config
    response = tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    # Save the audio to the output file
    with open(output_file, "wb") as out:
        out.write(response.audio_content)
    logger.info(f"Audio content written to {output_file}")

# Function to batch subtitles for synthesis
def batch_subtitles(subtitles, max_batch_size=10):
    for i in range(0, len(subtitles), max_batch_size):
        yield subtitles[i:i + max_batch_size]

# Function to synthesize subtitles into speech with correct timing alignment
# Function to synthesize subtitles into speech with correct timing alignment
def synthesize_subtitles(input_file, output_dir, tts_client, batch_delay=5, max_batch_size=10):
    """
    Synthesizes speech from cleaned subtitles and saves the audio files.

    Args:
        input_file (str): Path to the cleaned subtitles file.
        output_dir (str): Directory to save the audio files.
        tts_client (texttospeech.TextToSpeechClient): Initialized Google Cloud TTS client.
        batch_delay (int): Delay between batches to avoid rate limits.
        max_batch_size (int): Maximum number of subtitles to process in each batch.
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, 'r', encoding='utf-8') as f:
        subtitles = f.readlines()

    combined_audio = AudioSegment.silent(duration=0)  # Initialize with silence at the start

    # Process subtitles in batches
    for batch_idx, batch in enumerate(batch_subtitles(subtitles, max_batch_size=max_batch_size), start=1):
        logger.info(f"Processing batch {batch_idx} with {len(batch)} subtitles.")
        for idx, line in enumerate(batch):
            # Extract the timestamp and subtitle from each line
            try:
                timestamp, subtitle = line.strip().split(":", 1)
                subtitle = subtitle.strip()
                if not subtitle:
                    continue

                # Convert timestamp (in seconds) to milliseconds
                time_in_ms = int(float(timestamp) * 1000)

                # Generate output filename based on subtitle index
                output_file = os.path.join(output_dir, f"subtitle_{batch_idx}_{idx+1}.mp3")

                # Synthesize the subtitle into speech
                synthesize_speech(subtitle, output_file, tts_client)

                # Load the generated MP3
                generated_audio = AudioSegment.from_mp3(output_file)

                # Calculate the duration of silence needed before this subtitle's speech starts
                silence_duration = max(0, time_in_ms - len(combined_audio))
                silence = AudioSegment.silent(duration=silence_duration)

                # Add silence + generated audio to the combined audio track
                combined_audio += silence + generated_audio

                # If there is more time after this subtitle, add more silence to stretch it out
                if idx < len(batch) - 1:
                    # Calculate the time until the next subtitle
                    next_timestamp = int(float(batch[idx + 1].split(":")[0]) * 1000)
                    gap_duration = next_timestamp - time_in_ms - len(generated_audio)
                    if gap_duration > 0:
                        combined_audio += AudioSegment.silent(duration=gap_duration)

            except Exception as e:
                logger.error(f"Error processing subtitle: {line}. Error: {e}")

        # Apply delay between batches to avoid rate limits
        logger.info(f"Batch {batch_idx} processed. Sleeping for {batch_delay} seconds to avoid rate limits.")
        time.sleep(batch_delay)

    # Save the final combined audio
    final_output_file = os.path.join(output_dir, "final_synthesized_audio.mp3")
    combined_audio.export(final_output_file, format="mp3")
    logger.info(f"Final combined audio saved to {final_output_file}")

# Main function to handle the process
def main(input_file, output_dir):
    # Initialize the Google Cloud TTS client
    tts_client = setup_tts_client()

    # Convert subtitles to speech with timing alignment
    synthesize_subtitles(input_file, output_dir, tts_client)

if __name__ == "__main__":
    # Replace with your paths
    input_file = "path_to_cleaned_subtitles.txt"  # Path to the cleaned subtitle file
    output_dir = "path_to_output_audio_files"  # Directory to save the audio files

    main(input_file, output_dir)
