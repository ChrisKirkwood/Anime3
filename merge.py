from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import logging
import subprocess
from glob import glob

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

def merge_audio_files(audio_files, output_file):
    """
    Merges multiple MP3 audio files into a single MP3 file using FFmpeg.

    Args:
        audio_files (list): List of MP3 file paths to merge.
        output_file (str): Output file path for the merged audio.
    """
    try:
        # Create a temporary text file with the list of audio files
        with open("audio_files.txt", "w") as f:
            for file in audio_files:
                f.write(f"file '{file}'\n")

        # Use FFmpeg to concatenate the audio files
        command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", "audio_files.txt", "-c", "copy", output_file]
        subprocess.run(command, check=True)
        logger.info(f"Merged audio saved to {output_file}")

        # Clean up the temporary text file
        os.remove("audio_files.txt")
    except Exception as e:
        logger.error(f"Error while merging audio files: {e}")

def replace_audio_in_video(video_file, audio_file, output_file):
    """
    Replaces the audio in a video file with a new audio track.

    Args:
        video_file (str): Path to the input video file.
        audio_file (str): Path to the new audio file.
        output_file (str): Path to the output video file with replaced audio.
    """
    try:
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"The video file {video_file} does not exist.")
        
        logger.info(f"Loading video file: {video_file}")
        video = VideoFileClip(video_file)
        
        logger.info(f"Loading new audio file: {audio_file}")
        new_audio = AudioFileClip(audio_file)
        
        # Set the new audio to the video
        video_with_new_audio = video.set_audio(new_audio)
        
        # Write the result to the output file
        logger.info(f"Writing video with new audio to: {output_file}")
        video_with_new_audio.write_videofile(output_file, codec="libx264", audio_codec="aac")
        logger.info(f"Video with new audio saved to {output_file}")
    except Exception as e:
        logger.error(f"Error while replacing audio in video: {e}")

def main(video_file, audio_files, merged_audio_file, output_video_file):
    """
    Main function to merge audio files and overlay the merged audio onto a video.
    """
    try:
        # Merge audio files into one
        logger.info("Starting audio merging process...")
        merge_audio_files(audio_files, merged_audio_file)
        
        # Replace the original audio in the video with the merged audio
        logger.info("Starting audio replacement in video...")
        replace_audio_in_video(video_file, merged_audio_file, output_video_file)
        
        logger.info("Process completed successfully.")
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == "__main__":
    main()