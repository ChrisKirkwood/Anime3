from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import logging
import subprocess
from glob import glob
from moviepy.audio.AudioClip import CompositeAudioClip

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
        # Log the audio files being merged
        logger.info(f"Audio files to be merged: {audio_files}")

        # Create a temporary text file with the list of audio files
        with open("audio_files.txt", "w") as f:
            for file in audio_files:
                f.write(f"file '{file}'\n")

        # Use FFmpeg to concatenate the audio files
        command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", "audio_files.txt", "-c", "copy", output_file]
        subprocess.run(command, check=True)
        logger.info(f"Merged audio saved to {output_file}")

        # Log the success of the merged audio file creation
        if os.path.exists(output_file):
            logger.info(f"Merged audio file successfully created: {output_file}")
        else:
            logger.warning(f"Merged audio file was not created at: {output_file}")

        # Clean up the temporary text file
        os.remove("audio_files.txt")
    except Exception as e:
        logger.error(f"Error while merging audio files: {e}")


def overlay_audio_in_video(video_file, audio_file, output_file):
    """
    Overlays new audio onto the existing audio in a video file.

    Args:
        video_file (str): Path to the input video file.
        audio_file (str): Path to the new audio file to overlay.
        output_file (str): Path to the output video file with overlaid audio.
    """
    try:
        # Log the video and audio file paths being used
        logger.info(f"Overlay process started with video file: {video_file} and audio file: {audio_file}")

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"The video file {video_file} does not exist.")

        logger.info(f"Loading video file: {video_file}")
        video = VideoFileClip(video_file)

        logger.info(f"Loading new audio file: {audio_file}")
        new_audio = AudioFileClip(audio_file)

        # Retrieve the original audio from the video
        if video.audio is None:
            raise ValueError(f"The video file {video_file} has no audio track.")

        logger.info("Extracting original audio from video...")
        original_audio = video.audio

        # Combine original audio with new audio
        logger.info("Overlaying new audio onto original audio...")
        combined_audio = CompositeAudioClip([original_audio, new_audio])

        # Set the combined audio to the video
        video_with_combined_audio = video.set_audio(combined_audio)

        # Write the result to the output file
        logger.info(f"Writing video with overlaid audio to: {output_file}")
        video_with_combined_audio.write_videofile(output_file, codec="libx264", audio_codec="aac")

        # Log when the combined video with audio is successfully saved
        if os.path.exists(output_file):
            logger.info(f"Video with overlaid audio successfully saved to {output_file}")
        else:
            logger.warning(f"Output video file was not created at: {output_file}")

    except Exception as e:
        logger.error(f"Error while overlaying audio in video: {e}")


def main(video_file, audio_files, merged_audio_file, output_video_file):
    """
    Main function to merge audio files and overlay the merged audio onto a video.

    Args:
        video_file (str): Path to the input video file.
        audio_files (list): List of paths to the audio files to merge.
        merged_audio_file (str): Path for the merged audio file.
        output_video_file (str): Path for the final output video with overlaid audio.
    """
    try:
        # Merge audio files into one
        logger.info("Starting audio merging process...")
        merge_audio_files(audio_files, merged_audio_file)
        
        # Overlay the merged audio onto the video
        logger.info("Starting audio overlay process...")
        overlay_audio_in_video(video_file, merged_audio_file, output_video_file)
        
        logger.info("Process completed successfully.")
    except Exception as e:
        logger.error(f"Error in main function: {e}")


if __name__ == "__main__":
    main()
