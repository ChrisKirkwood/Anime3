import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from extract import main as extract_subtitles
from cleaner import clean_subtitles_file
from speech import setup_tts_client, synthesize_subtitles
from merge import replace_audio_in_video  # Import the correct function from merge.py


# Create the main application class
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

        # Text widget to show logs and process updates
        self.log_text = tk.Text(self.frame, width=60, height=10, state=tk.DISABLED)
        self.log_text.grid(row=5, column=0, columnspan=2, pady=10)

        # Variables to hold file paths
        self.video_file = None
        self.output_file = None
        self.cleaned_file = None  # Variable to hold the cleaned subtitles file
        self.synthesized_audio_file = None  # Variable to hold synthesized audio file

    # Function to select a file
    def select_file(self):
        file_path = filedialog.askopenfilename(title="Select Video File", filetypes=[("MP4 Files", "*.mp4")])
        if file_path:
            self.video_file = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
        else:
            self.file_label.config(text="No file selected")

    # Function to log messages in the GUI
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

    # Function to start the extraction in a new thread
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

    # Function to run the extraction process
    def run_extraction(self, video_path, output_file):
        try:
            extract_subtitles(video_path, output_file)
            self.log_message("Subtitle extraction completed successfully!")
            messagebox.showinfo("Success", "Subtitles extracted successfully!")
        except Exception as e:
            self.log_message(f"Error during extraction: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")

    # Function to extract and clean subtitles
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

    # Function to run extraction and cleaning in one step
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

    # Function to select the cleaned subtitles and synthesize them into speech
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

    # Function to run the TTS synthesis process
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

    # Function to merge synthesized audio with the original video
    def merge_audio_video(self):
        if not self.synthesized_audio_file:
            self.synthesized_audio_file = filedialog.askopenfilename(title="Select Synthesized Audio File", filetypes=[("MP3 Files", "*.mp3")])

        if not self.synthesized_audio_file:
            messagebox.showwarning("No Audio File Selected", "Please select a synthesized audio file.")
            return

        output_video_file = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Files", "*.mp4")])
        if not output_video_file:
            messagebox.showwarning("No Output Video File Selected", "Please select an output video file.")
            return

        self.log_message("Starting the merge of audio and video...")

        # Start the merge process in a separate thread to keep the GUI responsive
        threading.Thread(target=self.run_merge_audio_video, args=(self.video_file, self.synthesized_audio_file, output_video_file)).start()

    # Function to run the merge process
    def run_merge_audio_video(self, video_file, audio_file, output_video_file):
        try:
            replace_audio_in_video(video_file, audio_file, output_video_file)  # Corrected function call
            self.log_message(f"Audio merged with video successfully! Video saved to {output_video_file}")
            messagebox.showinfo("Success", f"Audio merged with video successfully! Video saved to {output_video_file}")
        except Exception as e:
            self.log_message(f"Error during merging or video overlay: {e}")
            messagebox.showerror("Error", f"An error occurred: {e}")


# Main function to set up and run the GUI
def main():
    root = tk.Tk()
    app = SubtitleExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
