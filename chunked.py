import os
import subprocess
import logging
from glob import glob
from extract import extract_subtitles_from_video, setup_vision_client, save_subtitles_to_file
from cleaner import clean_subtitles_file
from speech import setup_tts_client, synthesize_subtitles
from merge import replace_audio_in_video

# Set up logging
log_file_path = r"D:\Anime3\log\automation.log"
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Paths
input_video = r"D:\Anime3\input\video_reencoded.mp4"  # Replace with your video path
output_dir = r"D:\Anime3\output"
os.makedirs(output_dir, exist_ok=True)

chunk_dir = os.path.join(output_dir, "chunks")
os.makedirs(chunk_dir, exist_ok=True)

final_output = os.path.join(output_dir, "final_output.mp4")

# Step 1: Split video into chunks
def split_video(input_video, chunk_dir, chunk_duration=300):
    """
    Splits the input video into chunks using FFmpeg.

    Args:
        input_video (str): Path to the input video.
        chunk_dir (str): Directory to save video chunks.
        chunk_duration (int): Duration of each chunk in seconds.

    Returns:
        list: List of chunk file paths.
    """
    try:
        logger.info("Splitting video into chunks...")
        command = [
            "ffmpeg", "-i", input_video,
            "-c", "copy", "-map", "0",
            "-segment_time", str(chunk_duration),
            "-f", "segment",
            os.path.join(chunk_dir, "chunk_%03d.mp4")
        ]
        subprocess.run(command, check=True)
        chunk_files = sorted(glob(os.path.join(chunk_dir, "chunk_*.mp4")))
        logger.info(f"Video successfully split into {len(chunk_files)} chunks.")
        return chunk_files
    except Exception as e:
        logger.error(f"Error splitting video: {e}")
        return []

# Step 2: Process each chunk through your pipeline
def process_chunks(chunk_files):
    """
    Processes each video chunk through the pipeline.

    Args:
        chunk_files (list): List of video chunk paths.

    Returns:
        tuple: Paths to all cleaned subtitle files and synthesized audio files.
    """
    cleaned_subtitle_files = []
    synthesized_audio_files = []

    vision_client = setup_vision_client()
    tts_client = setup_tts_client()

    for idx, chunk in enumerate(chunk_files):
        try:
            logger.info(f"Processing chunk {idx + 1}/{len(chunk_files)}: {chunk}")

            # Update file paths for each chunk
            subtitle_file = os.path.join(output_dir, f"chunk_{idx+1}_subtitles.txt")
            cleaned_file = os.path.join(output_dir, f"chunk_{idx+1}_cleaned.txt")
            audio_file = os.path.join(output_dir, f"chunk_{idx+1}_audio.mp3")

            # Extract subtitles
            logger.info("Extracting subtitles...")
            subtitles = extract_subtitles_from_video(chunk, vision_client)
            save_subtitles_to_file(subtitles, subtitle_file)

            # Clean subtitles
            logger.info("Cleaning subtitles...")
            clean_subtitles_file(subtitle_file, cleaned_file)

            # Synthesize audio
            logger.info("Synthesizing audio...")
            synthesize_subtitles(cleaned_file, output_dir, tts_client)

            # Collect processed files
            cleaned_subtitle_files.append(cleaned_file)
            synthesized_audio_files.append(audio_file)

        except Exception as e:
            logger.error(f"Error processing chunk {idx + 1}: {e}")
            continue

    return cleaned_subtitle_files, synthesized_audio_files

# Step 3: Merge results
def merge_results(cleaned_subtitle_files, synthesized_audio_files, final_output, chunk_files):
    """
    Merges cleaned subtitles and audio files into a final video with adjusted timestamps.

    Args:
        cleaned_subtitle_files (list): Paths to cleaned subtitle files.
        synthesized_audio_files (list): Paths to synthesized audio files.
        final_output (str): Path to the final merged video.
        chunk_files (list): Paths to the original chunk files for duration calculation.
    """
    try:
        logger.info("Merging results...")

        # Calculate chunk durations
        chunk_durations = []
        for chunk in chunk_files:
            command = [
                "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", chunk
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                chunk_durations.append(float(result.stdout.strip()))
            else:
                logger.error(f"Error calculating duration for chunk {chunk}: {result.stderr}")
                return

        # Combine subtitles with adjusted timestamps
        combined_subtitles = os.path.join(output_dir, "combined_subtitles.txt")
        offset = 0
        with open(combined_subtitles, 'w', encoding='utf-8') as f_out:
            for idx, file in enumerate(cleaned_subtitle_files):
                with open(file, 'r', encoding='utf-8') as f_in:
                    for line in f_in:
                        if ":" in line:
                            timestamp, subtitle = line.split(":", 1)
                            adjusted_timestamp = float(timestamp) + offset
                            f_out.write(f"{adjusted_timestamp:.2f}: {subtitle}")
                offset += chunk_durations[idx]
        logger.info(f"Combined subtitles saved to {combined_subtitles}")

        # Synthesize audio for the combined subtitles
        combined_audio = os.path.join(output_dir, "final_synthesized_audio.mp3")
        logger.info("Synthesizing final audio...")
        synthesize_subtitles(combined_subtitles, combined_audio, setup_tts_client())

        # Merge audio with the video
        replace_audio_in_video(input_video, combined_audio, final_output)
        logger.info(f"Final video saved to {final_output}")

    except Exception as e:
        logger.error(f"Error merging results: {e}")





# Main workflow
if __name__ == "__main__":
    # Step 1: Split the video
    chunk_files = split_video(input_video, chunk_dir)

    if not chunk_files:
        logger.error("No chunks generated. Exiting.")
        exit(1)

    # Step 2: Process each chunk
    cleaned_subtitle_files, synthesized_audio_files = process_chunks(chunk_files)

    # Step 3: Merge results
    merge_results(cleaned_subtitle_files, synthesized_audio_files, final_output)