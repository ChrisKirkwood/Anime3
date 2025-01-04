import os
import subprocess
import logging
from glob import glob
from extract import extract_subtitles_from_video, setup_vision_client, save_subtitles_to_file
from cleaner import clean_subtitles_file
from speech import setup_tts_client, synthesize_subtitles
from pydub import AudioSegment
from speech import synthesize_speech_to_audio_segment
import re

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

def split_video(input_video, chunk_dir, chunk_duration=150):
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
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg command failed with error: {result.stderr}")
            return []
        chunk_files = sorted(glob(os.path.join(chunk_dir, "chunk_*.mp4")))
        
        if not chunk_files:
            raise FileNotFoundError("No chunks were created during the splitting process.")
        
        logger.info(f"Video successfully split into {len(chunk_files)} chunks.")
        logger.debug(f"Chunks created: {chunk_files}")
        return chunk_files
    except Exception as e:
        logger.error(f"Error splitting video: {e}")
        return []

def get_last_audio_index(output_dir):
    """
    Gets the highest numbered `final_synthesized_audio_*.mp3` file in the output directory.

    Args:
        output_dir (str): Directory to check for audio files.

    Returns:
        int: The highest audio file index found, or 0 if no files are found.
    """
    audio_files = glob(os.path.join(output_dir, "final_synthesized_audio_*.mp3"))
    if not audio_files:
        logger.info(f"No audio files found in {output_dir}. Starting index will be 1.")
        return 0

    max_index = 0
    for file in audio_files:
        match = re.search(r"final_synthesized_audio_(\d+)\.mp3", file)
        if match:
            index = int(match.group(1))
            max_index = max(max_index, index)

    logger.info(f"Highest audio index found: {max_index}")
    return max_index


def process_chunks(chunk_files, output_dir, current_time_in_ms=0):
    """
    Processes each video chunk through the pipeline.

    Args:
        chunk_files (list): List of video chunk paths.
        output_dir (str): Directory to save processed files.
        current_time_in_ms (int): Current cumulative time in milliseconds.

    Returns:
        tuple: Paths to all cleaned subtitle files, synthesized audio files, and updated current_time_in_ms.
    """
    cleaned_subtitle_files = []
    final_audio_files = []

    # Initialize Google Cloud Vision and TTS clients
    vision_client = setup_vision_client()
    tts_client = setup_tts_client()

    # Get the last audio index to ensure continuity
    start_index = get_last_audio_index(output_dir) + 1

    for idx, chunk in enumerate(chunk_files):
        try:
            logger.info(f"Processing chunk {idx + 1}/{len(chunk_files)}: {chunk}")
            logger.info(f"Chunk {idx + 1}: Starting with current_time_in_ms = {current_time_in_ms}")

            # Paths for intermediate outputs
            subtitle_file = os.path.join(output_dir, f"chunk_{idx + 1}_subtitles.txt")
            cleaned_file = os.path.join(output_dir, f"chunk_{idx + 1}_cleaned.txt")

            # Extract subtitles
            logger.info("Extracting subtitles...")
            subtitles = extract_subtitles_from_video(chunk, vision_client)
            if not subtitles:
                logger.error(f"No subtitles extracted from chunk {chunk}. Skipping...")
                continue
            save_subtitles_to_file(subtitles, subtitle_file)

            # Clean subtitles
            logger.info("Cleaning subtitles...")
            clean_subtitles_file(subtitle_file, cleaned_file)
            if not os.path.exists(cleaned_file):
                logger.error(f"Cleaned subtitle file not found for chunk {chunk}.")
                continue
            cleaned_subtitle_files.append(cleaned_file)

            # Synthesize audio
            logger.info("Synthesizing audio...")
            new_start_index, updated_time_in_ms = synthesize_subtitles(
                input_file=cleaned_file,
                output_dir=output_dir,
                tts_client=tts_client,
                start_index=start_index,
                current_time_in_ms=current_time_in_ms
            )

            # Log the duration of audio generated for the chunk
            audio_duration = updated_time_in_ms - current_time_in_ms
            logger.info(f"Chunk {idx + 1}: Audio duration generated = {audio_duration} ms")

            # Update `current_time_in_ms` and `start_index`
            current_time_in_ms = updated_time_in_ms
            logger.info(f"Chunk {idx + 1}: Updated current_time_in_ms = {current_time_in_ms}")

            audio_files = [
                os.path.join(output_dir, f"final_synthesized_audio_{i}.mp3")
                for i in range(start_index, new_start_index)
            ]
            final_audio_files.extend(audio_files)
            start_index = new_start_index

        except Exception as e:
            logger.error(f"Error processing chunk {idx + 1}: {e}")
            continue

    if not cleaned_subtitle_files or not final_audio_files:
        logger.error("No cleaned subtitles or synthesized audio files generated.")
    else:
        logger.info(f"Processed {len(cleaned_subtitle_files)} subtitle files and {len(final_audio_files)} audio files.")

    return cleaned_subtitle_files, final_audio_files, current_time_in_ms










def merge_results(cleaned_subtitle_files, output_dir, final_output, chunk_files):
    """
    Merges video chunks, concatenates synthesized audio, adjusts subtitle timestamps,
    and replaces the audio in the final merged video.

    Args:
        cleaned_subtitle_files (list): Paths to cleaned subtitle files.
        output_dir (str): Directory to save intermediate and final outputs.
        final_output (str): Path to the final video output.
        chunk_files (list): List of chunked video files.

    Returns:
        None
    """
    try:
        logger.info("Merging results...")

        # Step 1: Locate all synthesized audio files
        logger.info("Locating all synthesized audio files...")
        audio_files = sorted(glob(os.path.join(output_dir, "final_synthesized_audio_*.mp3")))
        if not audio_files:
            raise FileNotFoundError("No synthesized audio files found to concatenate.")

        # Step 2: Create a text file listing all audio files for FFmpeg concatenation
        audio_list_file = os.path.join(output_dir, "audio_list.txt")
        with open(audio_list_file, 'w') as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")
        logger.info(f"Audio list file created at: {audio_list_file}")

        # Step 3: Concatenate all audio files into a single audio file
        combined_audio_path = os.path.join(output_dir, "final_combined_audio.mp3")
        ffmpeg_concat_audio_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", audio_list_file,
            "-c", "copy", combined_audio_path
        ]
        logger.info("Concatenating all synthesized audio files into one final audio file...")
        subprocess.run(ffmpeg_concat_audio_cmd, check=True)
        logger.info(f"Combined audio file saved at: {combined_audio_path}")

        # Step 4: Recombine all video chunks into a single video file
        logger.info("Recombining video chunks into a single video...")
        video_list_file = os.path.join(output_dir, "video_chunks_list.txt")
        recombined_video_path = os.path.join(output_dir, "recombined_video.mp4")

        with open(video_list_file, 'w') as f:
            for chunk in chunk_files:
                f.write(f"file '{chunk}'\n")
        logger.info(f"Video list file created at: {video_list_file}")

        ffmpeg_concat_video_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", video_list_file,
            "-c", "copy", recombined_video_path
        ]
        subprocess.run(ffmpeg_concat_video_cmd, check=True)
        logger.info(f"Recombined video file saved at: {recombined_video_path}")

        # Step 5: Replace the audio in the final recombined video
        logger.info("Replacing audio in the final video...")
        ffmpeg_replace_audio_cmd = [
            "ffmpeg", "-i", recombined_video_path, "-i", combined_audio_path,
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-y", final_output
        ]
        subprocess.run(ffmpeg_replace_audio_cmd, check=True)
        logger.info(f"Final video with combined audio saved at: {final_output}")

        # Step 6: Log completion
        logger.info("Merging results completed successfully!")

    except Exception as e:
        logger.error(f"Error merging results: {e}")
        raise

def main(video_file, output_dir):
    chunk_dir = os.path.join(output_dir, "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    final_output = os.path.join(output_dir, "final_output.mp4")

    # Step 1: Split the video
    chunk_files = split_video(video_file, chunk_dir)
    if not chunk_files:
        logger.error("No chunks generated. Exiting.")
        return

    # Step 2: Process each chunk
    cleaned_subtitle_files, final_audio_files = process_chunks(chunk_files, output_dir)

    # Step 3: Merge results
    if cleaned_subtitle_files and final_audio_files:
        merge_results(
            cleaned_subtitle_files=cleaned_subtitle_files,
            output_dir=output_dir,
            final_output=final_output,
            chunk_files=chunk_files
        )
    else:
        logger.error("Failed to process all chunks. Exiting.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python chunked.py <video_file> <output_dir>")
        sys.exit(1)

    video_file = sys.argv[1]
    output_dir = sys.argv[2]
    main(video_file, output_dir)
