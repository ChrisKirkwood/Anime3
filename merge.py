from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip
import os

# Function to merge audio files into one
def merge_audio_files(audio_files, output_file):
    merged_audio = AudioSegment.empty()
    
    # Loop through all audio files and concatenate them
    for file in audio_files:
        audio = AudioSegment.from_mp3(file)
        merged_audio += audio
    
    # Export the merged audio to an output file
    merged_audio.export(output_file, format="mp3")
    print(f"Merged audio saved to {output_file}")

# Function to replace audio in an MP4 video file with the merged audio
def replace_audio_in_video(video_file, audio_file, output_file):
    # Load the video file
    video = VideoFileClip(video_file)
    
    # Load the new audio file
    new_audio = AudioFileClip(audio_file)
    
    # Set the new audio to the video
    video_with_new_audio = video.set_audio(new_audio)
    
    # Write the result to the output file
    video_with_new_audio.write_videofile(output_file, codec="libx264", audio_codec="aac")
    print(f"Video with new audio saved to {output_file}")

# Main function to handle merging and overlaying
def main():
    # List of MP3 subtitle files to merge
    audio_files = ["subtitle_1.mp3", "subtitle_2.mp3", "subtitle_3.mp3", "subtitle_4.mp3"]
    
    # File paths
    merged_audio_file = "merged_subtitles.mp3"
    original_video_file = "path_to_your_original_video.mp4"  # Replace with the original MP4 file
    output_video_file = "output_video_with_new_audio.mp4"
    
    # Merge audio files into one
    merge_audio_files(audio_files, merged_audio_file)
    
    # Replace the original audio in the video with the merged audio
    replace_audio_in_video(original_video_file, merged_audio_file, output_video_file)

if __name__ == "__main__":
    main()
