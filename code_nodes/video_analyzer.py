"""
Coze代码节点：视频风格分析
输入：video_url (抖音视频分享链接或直链)
输出：style_params (风格参数JSON)
"""
import json
import subprocess
import tempfile
import os
import glob
from pathlib import Path


def main(video_url: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")
        frames_dir = os.path.join(tmpdir, "frames")
        os.makedirs(frames_dir)

        try:
            subprocess.run(
                ["yt-dlp", "-o", os.path.join(tmpdir, "video.%(ext)s"), "--no-warning", video_url],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            return {"error": f"yt-dlp 下载失败: {e.stderr.strip() or '未知错误'}"}
        except FileNotFoundError:
            return {"error": "yt-dlp 未安装，请先安装: pip install yt-dlp"}

        downloaded = glob.glob(os.path.join(tmpdir, "video.*"))
        if not downloaded:
            return {"error": "yt-dlp 下载完成但未找到文件"}
        video_path = downloaded[0]

        try:
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                 "-ar", "16000", "-ac", "1", audio_path, "-y"],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            return {"error": f"ffmpeg 音频提取失败: {e.stderr.strip() or '视频可能无音频流'}"}
        except FileNotFoundError:
            return {"error": "ffmpeg 未安装，请先安装 ffmpeg"}

        try:
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-vf", "fps=1",
                 f"{frames_dir}/frame_%03d.jpg", "-y"],
                check=True, capture_output=True, text=True
            )
        except subprocess.CalledProcessError as e:
            return {"error": f"ffmpeg 帧提取失败: {e.stderr.strip() or '未知错误'}"}
        except FileNotFoundError:
            return {"error": "ffmpeg 未安装，请先安装 ffmpeg"}

        visual_params = analyze_visual(frames_dir)
        audio_params = analyze_audio(audio_path)
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
    if not frames:
        return {"error": "未提取到任何帧"}

    r_list, g_list, b_list = [], [], []
    dark_ratios = []
    warm_ratios = []

    for frame_path in frames:
        img = Image.open(frame_path).convert("RGB")
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
        "brightness": {"value": round(brightness), "level": int(brightness // 20)},
        "dark_pixel_ratio": f"{sum(dark_ratios)/len(dark_ratios)*100:.0f}%",
        "warm_pixel_ratio": f"{sum(warm_ratios)/len(warm_ratios)*100:.0f}%"
    }


def classify_color_tone(r: float, g: float, b: float) -> str:
    warmth = r - b
    if warmth > 40:
        if r > 60:
            return "暗琥珀色调，暖色系 R>G>B"
        return "暖褐色调"
    elif warmth > 15:
        return "中性偏暖色调"
    elif warmth > -15:
        return "中性色调"
    else:
        return "冷色调"


def analyze_audio(audio_path: str) -> dict:
    import wave, struct
    import numpy as np

    try:
        with wave.open(audio_path, 'r') as wf:
            sr = wf.getframerate()
            nframes = wf.getnframes()
            raw = wf.readframes(nframes)
    except Exception as e:
        return {"error": f"音频文件读取失败: {e}"}

    if nframes == 0:
        return {"error": "音频文件无帧数据（视频可能无音频流）"}

    expected_bytes = nframes * 2
    if len(raw) < expected_bytes:
        nframes = len(raw) // 2
        raw = raw[:nframes * 2]

    try:
        samples = struct.unpack(f'{nframes}h', raw)
    except struct.error as e:
        return {"error": f"音频数据解包失败: {e}"}

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
        chunk = samples_np[i*chunk_size:(i+1)*chunk_size]
        zcr = np.sum(np.diff(np.sign(chunk)) != 0) / len(chunk)
        zcr_values.append(zcr)

    avg_zcr = sum(zcr_values) / len(zcr_values) if zcr_values else 0.0

    pitch_category = "偏高男声" if 200 < fundamental < 280 else ("男声" if fundamental < 200 else "女声")

    return {
        "pitch": f"~{fundamental:.0f}Hz ({pitch_category})",
        "spectral_centroid": f"{centroid:.0f}Hz",
        "avg_zero_crossing_rate": f"{avg_zcr:.3f}",
        "pace": "舒缓平稳" if avg_zcr < 0.12 else "节奏中等"
    }


def analyze_scenes(frames_dir: str) -> dict:
    from PIL import Image

    frames = sorted(Path(frames_dir).glob("*.jpg"))
    if not frames:
        return {"scene_count": 0, "transitions": [], "transition_style": "无帧数据"}

    brightnesses = []
    for f in frames:
        img = Image.open(f).convert("RGB")
        arr = list(img.resize((50, 50)).getdata())
        b = sum(max(c) for c in arr) / len(arr)
        brightnesses.append(b)

    transitions = []
    for i in range(1, len(brightnesses)):
        diff = brightnesses[i] - brightnesses[i-1]
        if abs(diff) > 25:
            transitions.append({"frame": i, "type": "黑场过渡" if min(brightnesses[i], brightnesses[i-1]) < 15 else "明暗过渡"})

    black_frames = [i for i, b in enumerate(brightnesses) if b < 15]
    scene_count = len(black_frames) + 1 if black_frames else 1

    return {
        "scene_count": scene_count,
        "transitions": transitions,
        "transition_style": "黑场淡入淡出" if black_frames else "直接切换"
    }
