"""
Coze代码节点：视频合成
输入：
  - segments: 数组，每项包含 {video_url, audio_url, subtitle_text, audio_duration}
  - style_profile: 风格档案JSON (用于字幕样式和转场参数)
输出：
  - output_video_url: 最终合成的MP4文件URL
"""
import subprocess
import tempfile
import os
import json
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
                f.write(f"file '{part}'\n")

        subprocess.run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", output_path, "-y"
        ], check=True, capture_output=True)

        result_url = upload_output(output_path)
        return {"output_video_url": result_url}

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
    outline = style.get("outline", "none")

    fontsize_map = {"small": 20, "medium": 28, "large": 36}
    fs = fontsize_map.get(font_size, 28)

    outline_opt = "" if outline == "none" else f":borderw=2:bordercolor=black"

    safe_text = text.replace("'", "'\\''").replace(":", "\\:")

    drawtext = (
        f"drawtext=text='{safe_text}'"
        f":fontsize={fs}:fontcolor={color}"
        f":x=(w-text_w)/2:y=h*{y_offset.rstrip('%')}/100"
        f"{outline_opt}"
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

def upload_output(video_path: str) -> str:
    # Coze环境中需要替换为实际的上传逻辑
    # 目前返回文件路径，实际部署时对接Coze文件存储API
    return video_path
