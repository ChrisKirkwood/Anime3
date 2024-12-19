import os
from chunked import split_video, process_chunks
from speech import synthesize_subtitles
from merge import merge_audio_files, replace_audio_in_video
from cleaner import clean_subtitles_file
from extract import extract_subtitles_from_video

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

    # Step 1: Chunk the video into smaller parts
    print("Splitting video into chunks...")
    chunk_files = split_video(input_video, output_dir)
    if not chunk_files:
        raise ValueError("Video splitting failed. No chunks were created.")

    # Step 2: Process each chunk to extract subtitles and synthesize audio
    print("Processing video chunks...")
    cleaned_subtitle_files, final_audio_files = process_chunks(chunk_files, output_dir)
    if not cleaned_subtitle_files or not final_audio_files:
        raise ValueError("Processing chunks failed. No cleaned subtitles or audio files were generated.")

    # Step 3: Merge the synthesized audio files
    print("Merging audio files...")
    merged_audio_file = os.path.join(output_dir, "final_combined_audio.mp3")
    merge_audio_files(final_audio_files, merged_audio_file)
    if not os.path.exists(merged_audio_file):
        raise ValueError("Audio merging failed. Combined audio file was not created.")

    # Step 4: Replace the audio in the video with the synthesized audio
    print("Replacing audio in the video...")
    replace_audio_in_video(input_video, merged_audio_file, final_video_output)
    if not os.path.exists(final_video_output):
        raise ValueError("Audio replacement failed. Final video was not created.")

    print("Pipeline completed successfully.")

# Example usage
if __name__ == "__main__":
    input_video = "path_to_input_video.mp4"
    output_dir = "path_to_output_directory"
    final_video_output = "path_to_final_output_video.mp4"
    try:
        main_pipeline(input_video, output_dir, final_video_output)
    except Exception as e:
        print(f"Pipeline failed: {e}")
