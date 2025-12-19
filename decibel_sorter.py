import streamlit as st
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.AudioClip import AudioArrayClip
import os
import time
from proglog import ProgressBarLogger

max_duration = 300
cache_dir = "temp_videos"

st.set_page_config(page_title="Video Enhancer", layout="centered")

if "first_run" not in st.session_state:
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    else:
        for f in os.listdir(cache_dir):
            try:
                os.remove(os.path.join(cache_dir, f))
            except:
                pass
    st.session_state.first_run = True
    
# This is to display the moviepy stdout progress bar within streamlit
class StreamlitLogger(ProgressBarLogger):
    def __init__(self, progress_bar, status_text):
        super().__init__()
        self.progress_bar = progress_bar
        self.status_text = status_text
        
    def bars_callback(self, bar, attr, value, old_value=None):
        total = self.state['bars'][bar]['total']
        current = value
                    
        if total > 0:
            prog_val = int((current / total) * 100)
            prog_val = max(0, min(prog_val, 100))
            self.progress_bar.progress(prog_val)
            
        self.status_text.text("Rendering frames...")
        
st.title("Video Enhancer")
st.markdown("""
    This tool improves videos by sorting them into a gradual crescendo of intensity. It sorts videos by the volume of each frame and returns the result.
            """)
        

def process_video(input_path, output_path):
    
    status = st.empty()
    progress = st.progress(0)
    
    try:
        clip = VideoFileClip(input_path)
    except Exception as e:
        st.error(f"Could not load video: {e}")
        return
    
    if clip.duration > max_duration:
        st.warning(f"Video is too long ({clip.duration}s). Trimming to {max_duration}s.")
        clip = clip.subclip(0, max_duration)
        
    duration = clip.duration
    fps = clip.fps if clip.fps else 30
    
    status.text("Ripping audio DNA...")
    
    audio_bitrate = 44100
    audio_array = clip.audio.to_soundarray(fps=audio_bitrate).astype('float32')
    
    total_samples = len(audio_array)
    samples_per_frame = audio_bitrate / fps
    num_frames = int(duration * fps)
    
    status.text("Calculating volume by frame...")
    
    frame_data = []
    for i in range(num_frames):
        start = int(i * samples_per_frame)
        end = int((i + 1) * samples_per_frame)
        
        # Stupid boundary handling
        if end > total_samples: end = total_samples
        
        chunk = audio_array[start:end]
        
        # Stupid boundary handling again
        if chunk.size > 0:
            # Always use RMS for everything
            loudness = np.sqrt(np.mean(chunk**2))
        else:
            loudness = 0.0
            
        frame_data.append((i, loudness))
            
    status.text("Sorting...")
    
    frame_data.sort(key=lambda x: x[1])

    sorted_indices = [x[0] for x in frame_data]
    
    status.text("Reassembling frames...")
    
    new_audio_segments = []
    for idx in sorted_indices:
        start = int(idx * samples_per_frame)
        end = int((idx + 1) * samples_per_frame)
        if end <= total_samples:
            new_audio_segments.append(audio_array[start:end])
            
    if new_audio_segments:
        new_audio_array = np.concatenate(new_audio_segments).astype('float32')
        new_audio = AudioArrayClip(new_audio_array, fps=audio_bitrate)
        del new_audio_segments
        del audio_array
    else:
        # I have no solution if something breaks so the ol' rollback strat
        new_audio = clip.audio
            
    def make_frame_sorted(t):
        
        frame_idx_new = int(t * fps)
        
        if frame_idx_new >= len(sorted_indices):
            frame_idx_new = len(sorted_indices) - 1
            
        original_idx = sorted_indices[frame_idx_new]
        
        t_original = original_idx / fps
        
        return clip.get_frame(t_original)
    
    final_clip = clip.transform(lambda gf, t: make_frame_sorted(t))
    final_clip = final_clip.with_audio(new_audio)
    
    logger = StreamlitLogger(progress, status)
    
    final_clip.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        audio_codec='aac',
        preset='ultrafast',
        threads=4,
        logger=logger
    )
    
    clip.close()
    final_clip.close()
    progress.progress(100)
    status.success("Sorted successfully")
    

# --- UI ---

input_container = st.container()
col_orig, col_sort = st.columns(2)

if 'input_path' not in st.session_state:
    st.session_state.input_path = None
    
with input_container:
    file = st.file_uploader("Upload video", type=['mp4', 'mov', 'avi', 'mkv'])
    if file:
        path = os.path.join(cache_dir, f"in_{int(time.time())}.mp4")
        with open(path, 'wb') as f:
            f.write(file.getbuffer())
        st.session_state.input_path = path

if st.session_state.input_path:
    with col_orig:
        st.subheader("Original Video")
        st.video(st.session_state.input_path)
    
    if st.button("Sort Video"):
        output_path = os.path.join(cache_dir, f"out_{int(time.time())}.mp4")
        process_video(st.session_state.input_path, output_path)
        
        if os.path.exists(output_path):
            with col_sort:
                st.subheader("Sorted Video")
                st.video(output_path)
                with open(output_path, 'rb') as f:
                    st.download_button("Download", f, file_name=f"sorted_{time.time()}.mp4")