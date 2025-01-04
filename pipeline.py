import os
from chunked import split_video, process_chunks
from speech import synthesize_subtitles
from merge import merge_audio_files, overlay_audio_in_video  # Updated function name
from cleaner import clean_subtitles_file
from extract import extract_subtitles_from_video
import logging


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


def main_pipeline(input_video, output_dir, final_video_output):
    """
    Orchestrates the entire pipeline to process a video, extract subtitles,
    synthesize speech, and merge the results.

    Args:
        input_video (str): Path to the input video file.
        output_dir (str): Directory to save intermediate and output files.
        final_video_output (str): Path to save the final video with synthesized audio.

    Returns:
        None
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize global time variable
    current_time_in_ms = 0  # This will track time continuity across chunks
    logger.info(f"Initialized global current_time_in_ms: {current_time_in_ms}")

    try:
        # Step 1: Chunk the video into smaller parts
        logger.info("Starting Step 1: Splitting video into chunks...")
        chunk_files = split_video(input_video, output_dir)
        if not chunk_files:
            raise ValueError("Video splitting failed. No chunks were created.")
        logger.info(f"Step 1 completed: {len(chunk_files)} chunks created. Files: {chunk_files}")

        # Step 2: Process each chunk to extract subtitles and synthesize audio
        logger.info("Starting Step 2: Processing video chunks...")
        for idx, chunk in enumerate(chunk_files, start=1):
            logger.info(f"Processing chunk {idx}/{len(chunk_files)}: {chunk}")
            cleaned_subtitle_files, final_audio_files, updated_time_in_ms = process_chunks(
                chunk_files=[chunk],  # Process one chunk at a time
                output_dir=output_dir,
                current_time_in_ms=current_time_in_ms
            )
            current_time_in_ms = updated_time_in_ms  # Update global time
            logger.info(f"Chunk {idx} processed. Updated current_time_in_ms: {current_time_in_ms}")
            logger.info(f"Cleaned subtitle files: {cleaned_subtitle_files}")
            logger.info(f"Final audio files: {final_audio_files}")

        # Step 3: Merge the synthesized audio files
        logger.info("Starting Step 3: Merging synthesized audio files...")
        merged_audio_file = os.path.join(output_dir, "final_combined_audio.mp3")
        merge_audio_files(final_audio_files, merged_audio_file)
        if not os.path.exists(merged_audio_file):
            raise ValueError("Audio merging failed. Combined audio file was not created.")
        logger.info(f"Step 3 completed: Merged audio file created at {merged_audio_file}")

        # Step 4: Overlay the audio in the video with the synthesized audio
        logger.info("Starting Step 4: Overlaying audio onto the video...")
        overlay_audio_in_video(input_video, merged_audio_file, final_video_output)
        if not os.path.exists(final_video_output):
            raise ValueError("Audio overlay failed. Final video was not created.")
        logger.info(f"Step 4 completed: Final video created at {final_video_output}")

        logger.info("Pipeline completed successfully.")

    except Exception as e:
        logger.error(f"Error in main_pipeline: {e}")
        raise


# Example usage
if __name__ == "__main__":
    input_video = "path_to_input_video.mp4"
    output_dir = "path_to_output_directory"
    final_video_output = "path_to_final_output_video.mp4"
    try:
        main_pipeline(input_video, output_dir, final_video_output)
    except Exception as e:
        print(f"Pipeline failed: {e}")
