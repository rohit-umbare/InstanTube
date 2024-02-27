import tkinter as tk
from tkinter import ttk, messagebox
from pytube import YouTube
import os
import subprocess
from threading import Thread
from pathlib import Path
from PIL import Image, ImageTk

class YouTubeDownloaderApp:
    def __init__(self, root):
        try:
            # Initialize the YouTubeDownloaderApp class
            self.root = root
            self.root.title("InstanTube")
            self.root.geometry("400x300")
            self.root.resizable(True, True)  # Allowing window resizing
            self.set_theme()
            self.root.wm_attributes("-topmost", True)

            self.fetched_data = None
            self.last_copied_url = None
            self.download_in_progress = False
            self.check_clipboard()

        except Exception as e:
            # Show an error message if an unexpected error occurs during initialization
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def set_theme(self):
        # Set the theme colors for the GUI
        theme_color = "#1e272e"  # Dark background color
        text_color = "#d2dae2"   # Light text color
        button_color = "#3498db"  # Blue color
        button_text_color = "#ecf0f1"  # Light gray color

        self.root.configure(bg=theme_color)
        self.root.option_add('*TButton*highlightBackground', button_color)
        self.root.option_add('*TButton*highlightColor', button_color)
        self.root.option_add('*TButton*background', button_color)
        self.root.option_add('*TButton*foreground', button_text_color)

    def show_options(self):
        try:
            self.clear_screen()

            # Display loading message while fetching data
            loading_label = tk.Label(self.root, text="Fetching data... Please wait.", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12))
            loading_label.pack(pady=20)

            self.root.update()

            clipboard_content = self.root.clipboard_get()
            if clipboard_content.startswith("https://www.youtube.com/"):
                if clipboard_content != self.last_copied_url:
                    try:
                        # Fetch video details and streams
                        yt = YouTube(clipboard_content)
                        video_streams = yt.streams.filter(mime_type="video/webm", adaptive=True)
                        audio_streams = yt.streams.filter(mime_type="audio/webm", adaptive=True).desc().first()

                        if not video_streams or not audio_streams:
                            raise ValueError("No available video or audio streams.")

                        video_streams = sorted(video_streams, key=lambda v: (v.resolution, -v.fps))

                        self.fetched_data = {
                            'yt': yt,
                            'video_streams': video_streams,
                            'audio_streams': audio_streams
                        }

                        self.last_copied_url = clipboard_content

                        # Display video title and resolution buttons with scrollbar
                        title_label = tk.Label(self.root, text=f"Video Title: {yt.title}", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 14, "bold"), wraplength=300)
                        title_label.pack(pady=10)

                        frame = tk.Frame(self.root, bg="#1e272e")
                        frame.pack(pady=5)

                        canvas = tk.Canvas(frame, bg="#1e272e")
                        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)

                        resolution_frame = ttk.Frame(canvas)
                        resolution_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                        
                        canvas.create_window((canvas.winfo_reqwidth()/2, 0), window=resolution_frame, anchor="n")
                        canvas.configure(yscrollcommand=scrollbar.set)

                        for video_stream in video_streams:
                            resolution = f"{video_stream.resolution}-{video_stream.fps}fps"
                            resolution_btn = tk.Button(resolution_frame, text=resolution, command=lambda v=video_stream: self.download_video(v, yt.title), font=("Helvetica", 12))
                            resolution_btn.pack(pady=5, padx=10, fill="x")

                        canvas.pack(side="left", fill="both", expand=True)
                        scrollbar.pack(side="right", fill="y")

                    except Exception as e:
                        # Display error message if an error occurs during fetching video streams
                        self.display_message(f"Error fetching video streams: {e}")
            else:
                if not self.fetched_data:
                    # Display message if the clipboard doesn't contain a YouTube URL
                    self.clear_screen()
                    copy_url_label = tk.Label(self.root, text="Copy URL to fetch download options.", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 14))
                    copy_url_label.pack()

            loading_label.pack_forget()

        except Exception as e:
            # Display error message if an error occurs during showing options
            self.display_message(f"Error showing options: {e}")

    def download_video(self, selected_video, video_title):
        try:
            # Initialize the download process
            self.download_in_progress = True

            self.clear_screen()
            # Display downloading message
            downloading_message = f"Downloading: {video_title} - {selected_video.resolution}-{selected_video.fps}fps"
            downloading_label = tk.Label(self.root, text=downloading_message, bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12), wraplength=300)
            downloading_label.pack(pady=20)

            # Display progress bar
            progress_bar = ttk.Progressbar(self.root, orient="horizontal", length=300, mode="indeterminate")
            progress_bar.pack(pady=10)
            progress_bar.start()

            self.root.update()

            # Start the download thread
            download_thread = Thread(target=self.download_thread, args=(selected_video, video_title, downloading_message, progress_bar))
            download_thread.start()

        except Exception as e:
            # Display error message if an error occurs during starting the download thread
            self.display_message(f"Error starting download thread: {e}")

    def download_thread(self, selected_video, video_title, downloading_message, progress_bar):
        try:
            # Set up the download directories and filenames
            download_directory = Path.home() / 'Downloads' / 'instantube'
            download_directory.mkdir(parents=True, exist_ok=True)

            filename = f"{video_title}_{selected_video.resolution}_{selected_video.fps}fps.mp4"
            audio_file = download_directory / f"{filename}_audio.webm"
            video_file = download_directory / f"{filename}_video.webm"
            output_file = download_directory / filename

            if output_file.exists():
                raise FileExistsError(f"File '{output_file.name}' already exists in {download_directory}")

            # Download video and audio streams separately
            selected_video.download(filename=str(video_file))
            self.fetched_data['audio_streams'].download(filename=str(audio_file))

            # Combine video and audio using ffmpeg
            command = [
                'ffmpeg',
                '-i', str(video_file),
                '-i', str(audio_file),
                '-c', 'copy',
                '-strict', '-2',
                str(output_file)
            ]

            subprocess.run(command, check=True)

            # Remove temporary audio and video files
            audio_file.unlink()
            video_file.unlink()

            # Display success message
            self.clear_screen()
            success_message = f"{output_file.name} Downloaded Successfully in {download_directory}"
            success_label = tk.Label(self.root, text=success_message, bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12), wraplength=300)
            success_label.pack(pady=10)

            copy_url_label = tk.Label(self.root, text="Copy URL to download another video", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12,))
            copy_url_label.pack(pady=5)

        except FileExistsError as e:
            # Display error message if the output file already exists
            self.clear_screen()
            error_label = tk.Label(self.root, text=f"Error: {e}", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12), wraplength=300)
            error_label.pack()

        except Exception as e:
            # Display error message if an error occurs during the download process
            self.clear_screen()
            error_label = tk.Label(self.root, text=f"Error during download: {e}", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12), wraplength=300)
            error_label.pack()

        finally:
            # Stop and destroy the progress bar, update download status
            progress_bar.stop()
            progress_bar.destroy()

            self.download_in_progress = False

            # Check the clipboard for changes
            self.check_clipboard()

    def display_message(self, message):
        try:
            # Display a message on the screen
            message_label = tk.Label(self.root, text=message, bg="#1e272e", fg="#d2dae2", font=("Helvetica", 12), wraplength=300)
            message_label.pack()
        except Exception as e:
            # Display error message if an error occurs during message display
            print(f"Error displaying message: {e}")

    def clear_screen(self):
        try:
            # Clear the screen by removing all widgets
            for widget in self.root.winfo_children():
                widget.pack_forget()
        except Exception as e:
            # Display error message if an error occurs during screen clearing
            print(f"Error clearing screen: {e}")

    def check_clipboard(self):
        try:
            # Check the clipboard for YouTube URLs
            if not self.download_in_progress:
                clipboard_content = self.root.clipboard_get()
                if clipboard_content.startswith("https://www.youtube.com/"):
                    if clipboard_content != self.last_copied_url:
                        self.fetched_data = None
                        self.show_options()
                else:
                    if not self.fetched_data:
                        self.clear_screen()
                        copy_url_label = tk.Label(self.root, text="Copy URL to fetch download options.", bg="#1e272e", fg="#d2dae2", font=("Helvetica", 14))
                        copy_url_label.pack()
            self.root.after(2000, self.check_clipboard)
        except Exception as e:
            # Display error message if an error occurs during clipboard checking
            print(f"Error checking clipboard: {e}")

if __name__ == "__main__":
    try:
        # Create the main Tkinter window and start the application
        root = tk.Tk()
        app = YouTubeDownloaderApp(root)

        root.mainloop()
    except Exception as e:
        # Show an error message if an unexpected error occurs during execution
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
