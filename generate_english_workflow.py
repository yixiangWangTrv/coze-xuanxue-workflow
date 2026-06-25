#!/usr/bin/env python3
"""
生成英文版本的抖音玄学视频蒸馏工作流
使用 Coze YAML Builder 格式
"""

import sys
import os

# 添加脚本路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from coze_yaml_builder import *

# 创建输出目录
os.makedirs('/tmp/coze-workflow', exist_ok=True)

# 定义节点
nodes = ""

# Phase 1: Style Distillation
# Start node (100001)
nodes += start_node("100001", {"video_url": "string"})
nodes += "\n"

# Code node (100002) - Video Analysis
code_100002 = """
import json
import subprocess
import tempfile
import os
from pathlib import Path

def main(video_url: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")
        frames_dir = os.path.join(tmpdir, "frames")
        os.makedirs(frames_dir)
        
        # Download video
        subprocess.run(["yt-dlp", "-o", video_path, "--no-warning", video_url], check=True)
        
        # Extract audio
        subprocess.run([
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", audio_path, "-y"
        ], check=True, capture_output=True)
        
        # Extract frames
        subprocess.run([
            "ffmpeg", "-i", video_path, "-vf", "fps=1",
            f"{frames_dir}/frame_%03d.jpg", "-y"
        ], check=True, capture_output=True)
        
        # Analyze visual features
        visual_params = analyze_visual(frames_dir)
        
        # Analyze audio features
        audio_params = analyze_audio(audio_path)
        
        # Analyze scenes
        scene_params = analyze_scenes(frames_dir)
    
    return {
        "visual": visual_params,
        "audio": audio_params,
        "scenes": scene_params
    }

def analyze_visual(frames_dir: str) -> dict:
    from PIL import Image
    import numpy as np
    
    frames = sorted(Path(frames_dir).glob("*.jpg"))
    r_list, g_list, b_list = [], [], []
    dark_ratios = []
    warm_ratios = []
    
    for frame_path in frames:
        img = Image.open(frame_path)
        arr = np.array(img.resize((50, 50)))
        r_list.append(arr[:,:,0].mean())
        g_list.append(arr[:,:,1].mean())
        b_list.append(arr[:,:,2].mean())
        
        flat = arr.reshape(-1, 3)
        dark_count = (flat.max(axis=1) < 60).sum()
        dark_ratios.append(dark_count / len(flat))
        
        warm_count = (flat[:,0] > flat[:,2] + 30).sum()
        warm_ratios.append(warm_count / len(flat))
    
    avg_r = sum(r_list) / len(r_list)
    avg_g = sum(g_list) / len(g_list)
    avg_b = sum(b_list) / len(b_list)
    brightness = (avg_r + avg_g + avg_b) / 3
    
    tone = classify_color_tone(avg_r, avg_g, avg_b)
    
    return {
        "tone": tone,
        "avg_rgb": {"R": int(avg_r), "G": int(avg_g), "B": int(avg_b)},
        "brightness": f"{brightness:.0f} (brightness_level_{int(brightness//20)})",
        "dark_pixel_ratio": f"{sum(dark_ratios)/len(dark_ratios)*100:.0f}%",
        "warm_pixel_ratio": f"{sum(warm_ratios)/len(warm_ratios)*100:.0f}%"
    }

def classify_color_tone(r: float, g: float, b: float) -> str:
    warmth = r - b
    if warmth > 40:
        if r > 60:
            return "Warm (R>G>B)"
        return "Warm"
    elif warmth > 15:
        return "Slightly Warm"
    elif warmth > -15:
        return "Neutral"
    else:
        return "Cool"

def analyze_audio(audio_path: str) -> dict:
    import wave, struct, math
    import numpy as np
    
    with wave.open(audio_path, 'r') as wf:
        sr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
        samples = struct.unpack(f'{nframes}h', raw)
    
    samples_np = np.array(samples, dtype=float)
    
    fft = np.fft.rfft(samples_np)
    freqs = np.fft.rfftfreq(len(samples_np), 1/sr)
    magnitudes = np.abs(fft)
    
    centroid = np.sum(freqs * magnitudes) / np.sum(magnitudes)
    
    mask = (freqs > 80) & (freqs < 300)
    speech_fft = np.where(mask, magnitudes, 0)
    fundamental = freqs[np.argmax(speech_fft)]
    
    chunk_size = sr
    zcr_values = []
    for i in range(nframes // chunk_size):
        chunk = samples[i*chunk_size:(i+1)*chunk_size]
        zcr = sum(1 for j in range(1, len(chunk)) if (chunk[j-1]>0) != (chunk[j]>0)) / len(chunk)
        zcr_values.append(zcr)
    
    avg_zcr = sum(zcr_values) / len(zcr_values)
    
    pitch_category = "Deep Male" if 200 < fundamental < 280 else ("Moderate Male" if fundamental < 200 else "Light/Female")
    
    return {
        "pitch": f"~{fundamental:.0f}Hz ({pitch_category})",
        "spectral_centroid": f"{centroid:.0f}Hz",
        "avg_zero_crossing_rate": f"{avg_zcr:.3f}",
        "pace": "Slow" if avg_zcr < 0.12 else "Fast"
    }

def analyze_scenes(frames_dir: str) -> dict:
    from PIL import Image
    
    frames = sorted(Path(frames_dir).glob("*.jpg"))
    brightnesses = []
    for f in frames:
        img = Image.open(f)
        arr = list(img.resize((50,50)).getdata())
        b = sum(max(c[:3]) for c in arr) / len(arr)
        brightnesses.append(b)
    
    transitions = []
    for i in range(1, len(brightnesses)):
        diff = brightnesses[i] - brightnesses[i-1]
        if abs(diff) > 25:
            transitions.append({"frame": i, "type": "Fade to Black" if min(brightnesses[i], brightnesses[i-1]) < 15 else "Soft Fade"})
    
    black_frames = [i for i, b in enumerate(brightnesses) if b < 15]
    scene_count = len(black_frames) + 1 if black_frames else 1
    
    return {
        "scene_count": scene_count,
        "transitions": transitions,
        "transition_style": "Fade to Black" if black_frames else "Soft Fade"
    }
"""

nodes += code_node(
    "100002",
    "Video Analysis",
    code_100002,
    3,  # Python
    {"video_url": "string"},
    {"output": "dict"},
    "100001",
    "video_url",
    300, 0
)
nodes += "\n"

# LLM node (100003) - Style Translation
sys_prompt_100003 = "You are a video style translation expert, skilled at converting technical analysis parameters into artistic style descriptions."
prompt_100003 = """## Task
Convert the following video style parameters into:
1. Style description (Chinese, emotional expression)
2. Text-to-video prompt prefix (English, for models like Jimeng)
3. TTS voice suggestion

## Input: Style Parameters JSON
{{100002.output}}

## Output Format (JSON)

```json
{
  "style_description": "A Chinese style description for human reading",
  "prompt_prefix": "English prompt prefix, added to each video segment",
  "negative_prompt": "Elements not desired, in English",
  "tts_suggestion": {
    "voice_type": "Voice type suggestion",
    "speed": 0.8,
    "pitch_adjustment": "+1",
    "notes": "Voice selection notes"
  }
}
```

## Translation Principles
- **Color Tone Mapping**: R>G>B warm → amber/golden, R≈B cool → cool/silver, high saturation → vivid, low saturation → muted
- **Brightness Mapping**: <40 → low-key/dark/candlelight, 40-80 → medium, >80 → high-key/bright
- **Transition Mapping**: Black transition → fade to black, fade in/out → soft fade
- **Atmosphere Mapping**: Calm + low frequency → zen/contemplative, fast pace + high frequency → dynamic/energetic
- **Pitch Mapping**: Male voice <180Hz → deep male, 180-250Hz → moderate male, >250Hz → light/female"""

nodes += llm_node(
    "100003",
    "Style Translation",
    sys_prompt_100003,
    prompt_100003,
    "100002",
    "output",
    600, 0
)
nodes += "\n"

# End node (900001) - Phase 1 End
nodes += end_node("900001", "100003", "output", 900)
nodes += "\n"

# Phase 2: Video Generation
# Start node (200001)
nodes += start_node("200001", {"subtitle_text": "string", "style_id": "string"})
nodes += "\n"

# Knowledge node (200002) - Load Style Profile
nodes += knowledge_node("200002", "Load Style Profile", "200001", "style_id", 300, 300)
nodes += "\n"

# LLM node (200003) - Subtitle Splitting
sys_prompt_200003 = "You are a metaphysics short video storyboard director, responsible for splitting narration subtitles into shots and generating scene descriptions."
prompt_200003 = """## Input
- **Subtitle Text**: {{200001.subtitle_text}}
- **Style Profile**: {{200002.output}}

## Task
1. Split subtitles into **3-5 segments** based on semantics/rhythm
2. Generate English **video scene prompts** for each segment (combining style profile's prompt_prefix)
3. Control each narration segment to **6-10 seconds** reading time (about 15-40 characters)

## Output Format (JSON Array)

```json
[
  {
    "segment_index": 1,
    "subtitle_text": "First segment subtitle text",
    "video_prompt": "dark amber tones... an elderly Taoist master meditating...",
    "estimated_duration": 8
  }
]
```"""

nodes += llm_node(
    "200003",
    "Subtitle Splitting",
    sys_prompt_200003,
    prompt_200003,
    "200002",
    "output",
    600, 300
)
nodes += "\n"

# Loop node (200004) - Parallel Generation
# 内部节点需要单独定义
inner_nodes = ""
inner_nodes += inner_llm_node(
    "301001",
    "Generate Video",
    "You are a video generation assistant.",
    "Generate video based on: {{200003.output}}",
    "200004",
    "input",
    180, 0
)
inner_nodes += "\n"

nodes += loop_node(
    "200004",
    "Parallel Generation",
    "200003",
    "output",
    inner_nodes,
    [("301001", "301001")],
    "301001",
    900, 300
)
nodes += "\n"

# Code node (200005) - Video Composition
code_200005 = """
import subprocess
import tempfile
import os
import urllib.request

def main(segments: list, style_profile: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = f"{tmpdir}/output.mp4"
        part_files = []
        
        for i, seg in enumerate(segments):
            video_path = download_file(seg["video_url"], f"{tmpdir}/vid_{i}.mp4")
            audio_path = download_file(seg["audio_url"], f"{tmpdir}/aud_{i}.wav")
            
            trimmed = trim_video(video_path, seg["audio_duration"], f"{tmpdir}/trim_{i}.mp4")
            with_audio = merge_audio(trimmed, audio_path, f"{tmpdir}/waud_{i}.mp4")
            with_sub = burn_subtitle(
                with_audio,
                seg["subtitle_text"],
                style_profile.get("visual", {}).get("subtitle_style", {}),
                seg["audio_duration"],
                f"{tmpdir}/wsub_{i}.mp4"
            )
            part_files.append(with_sub)
            
            if i < len(segments) - 1:
                transition_dur = style_profile.get("visual", {}).get("transition_duration", 0.5)
                black = create_black_frame(f"{tmpdir}/black_{i}.mp4", transition_dur)
                part_files.append(black)
        
        concat_file = f"{tmpdir}/concat.txt"
        with open(concat_file, 'w') as f:
            for part in part_files:
                f.write(f"file '{part}'\\n")
        
        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", output_path, "-y"
        ], check=True, capture_output=True)
        
        return {"output_video_url": output_path}

def download_file(url: str, dest: str) -> str:
    urllib.request.urlretrieve(url, dest)
    return dest

def trim_video(video_path: str, duration: float, output: str) -> str:
    subprocess.run([
        "ffmpeg", "-i", video_path, "-t", str(duration),
        "-c:v", "libx264", "-c:a", "aac", output, "-y"
    ], check=True, capture_output=True)
    return output

def merge_audio(video_path: str, audio_path: str, output: str) -> str:
    subprocess.run([
        "ffmpeg", "-i", video_path, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", output, "-y"
    ], check=True, capture_output=True)
    return output

def burn_subtitle(video_path: str, text: str, style: dict, duration: float, output: str) -> str:
    font_size = style.get("font_size", "large")
    color = style.get("color", "white")
    y_offset = style.get("y_offset", "75%")
    
    fontsize_map = {"small": 20, "medium": 28, "large": 36}
    fs = fontsize_map.get(font_size, 28)
    
    safe_text = text.replace("'", "'\\\\''").replace(":", "\\\\:")
    
    drawtext = (
        f"drawtext=text='{safe_text}'"
        f":fontsize={fs}:fontcolor={color}"
        f":x=(w-text_w)/2:y=h*{y_offset.rstrip('%')}/100"
    )
    
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-vf", drawtext,
        "-c:a", "copy", output, "-y"
    ], check=True, capture_output=True)
    return output

def create_black_frame(output: str, duration: float) -> str:
    subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i",
        f"color=c=black:s=720x1280:d={duration}:r=30",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration), output, "-y"
    ], check=True, capture_output=True)
    return output
"""

nodes += code_node(
    "200005",
    "Video Composition",
    code_200005,
    3,  # Python
    {"segments": "list", "style_profile": "dict"},
    {"output_video_url": "string"},
    "200004",
    "output",
    1200, 300
)
nodes += "\n"

# End node (900002) - Phase 2 End
nodes += end_node("900002", "200005", "output_video_url", 1500)

# 定义边
edges = ""
edges += edge("100001", "100002")
edges += "\n"
edges += edge("100002", "100003")
edges += "\n"
edges += edge("100003", "900001")
edges += "\n"
edges += edge("200001", "200002")
edges += "\n"
edges += edge("200002", "200003")
edges += "\n"
edges += edge("200003", "200004")
edges += "\n"
edges += edge("200004", "200005", "loop-output")
edges += "\n"
edges += edge("200005", "900002")

# 构建工作流
build_workflow(
    "douyin_metaphysics_video_distillation",
    "7585079438426600001",
    "Douyin metaphysics video style distillation and generation workflow",
    nodes,
    edges,
    "./dist/Workflow-douyin_metaphysics_video_distillation-draft-0001.zip"
)

print("Done!")