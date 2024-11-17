from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import os
import logging

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

# Function to merge audio files into one
def merge_audio_files(audio_files, output_file):
    try:
        merged_audio = AudioSegment.empty()
        
        # Loop through all audio files and concatenate them
        for file in audio_files:
            logger.info(f"Processing audio file: {file}")
            audio = AudioSegment.from_mp3(file)
            merged_audio += audio
        
        # Export the merged audio to an output file
        merged_audio.export(output_file, format="mp3")
        logger.info(f"Merged audio saved to {output_file}")
    except Exception as e:
        logger.error(f"Error merging audio files: {e}")

# Function to replace audio in an MP4 video file with the merged audio
def replace_audio_in_video(video_file, audio_file, output_file):
    try:
        # Load the video file
        logger.info(f"Loading video file: {video_file}")
        video = VideoFileClip(video_file)
        
        # Load the new audio file
        logger.info(f"Loading audio file: {audio_file}")
        new_audio = AudioFileClip(audio_file)
        
        # Set the new audio to the video
        video_with_new_audio = video.set_audio(new_audio)
        
        # Write the result to the output file
        video_with_new_audio.write_videofile(output_file, codec="libx264", audio_codec="aac")
        logger.info(f"Video with new audio saved to {output_file}")
    except Exception as e:
        logger.error(f"Error replacing audio in video: {e}")

# Main function to handle merging and overlaying
def main():
    try:
        # List of MP3 subtitle files to merge
        audio_files = ["subtitle_1.mp3", "subtitle_2.mp3", "subtitle_3.mp3", "subtitle_4.mp3"]
        
        # File paths
        merged_audio_file = "merged_subtitles.mp3"
        original_video_file = "path_to_your_original_video.mp4"  # Replace with the original MP4 file
        output_video_file = "output_video_with_new_audio.mp4"
        
        # Merge audio files into one
        logger.info("Starting audio merging process...")
        merge_audio_files(audio_files, merged_audio_file)
        
        # Replace the original audio in the video with the merged audio
        logger.info("Starting audio replacement in video...")
        replace_audio_in_video(original_video_file, merged_audio_file, output_video_file)
        logger.info("Process completed successfully.")
    except Exception as e:
        logger.error(f"Error in the main process: {e}")

if __name__ == "__main__":
    main()
