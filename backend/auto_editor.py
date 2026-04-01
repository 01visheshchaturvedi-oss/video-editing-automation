import sys, os

# ── Force UTF-8 stdout/stderr so Unicode paths never crash print() ───────────
# Windows defaults to cp1252 which can't encode many Unicode chars.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

print("TRACE: Script Started", flush=True)
print("TRACE: Imported OS", flush=True)
print("TRACE: Imported SYS", flush=True)
import random
import traceback
import argparse
import unicodedata

def sanitize_path(p: str) -> str:
    """Strip invisible Unicode control characters (e.g. U+202A LEFT-TO-RIGHT
    EMBEDDING) that Windows File Explorer silently inserts into copied paths.
    Also strips surrounding quotes and whitespace."""
    if not isinstance(p, str):
        return p
    # Remove characters in Unicode categories Cf (format), Cc (control)
    cleaned = "".join(c for c in p if unicodedata.category(c) not in ("Cf", "Cc"))
    return cleaned.strip().strip('"').strip("'")

# ── cv2 ─────────────────────────────────────────────────────────────────────
try:
    import cv2
    print("TRACE: Imported cv2", flush=True)
except ImportError:
    print("FATAL ERROR: OpenCV not installed. Run: pip install opencv-python", flush=True)
    sys.exit(1)

# ── numpy ────────────────────────────────────────────────────────────────────
try:
    import numpy as np
    print("TRACE: Imported numpy", flush=True)
except ImportError:
    print("FATAL ERROR: numpy not installed. Run: pip install numpy", flush=True)
    sys.exit(1)

# ── librosa ──────────────────────────────────────────────────────────────────
try:
    import librosa
    import warnings
    print("TRACE: Imported librosa", flush=True)
except ImportError:
    print("FATAL ERROR: librosa not installed. Run: pip install librosa", flush=True)
    sys.exit(1)


# ── moviepy (supports both v1.x and v2.x) ────────────────────────────────────
MOVIEPY_V2 = False
try:
    # Try moviepy 2.x first
    from moviepy import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        concatenate_videoclips,
    )
    MOVIEPY_V2 = True
    print("TRACE: Imported moviepy v2.x", flush=True)
except ImportError:
    try:
        # Fall back to moviepy 1.x
        import moviepy.editor as _mpy_editor
        VideoFileClip = _mpy_editor.VideoFileClip
        ImageClip     = _mpy_editor.ImageClip
        AudioFileClip = _mpy_editor.AudioFileClip
        concatenate_videoclips = _mpy_editor.concatenate_videoclips
        print("TRACE: Imported moviepy v1.x", flush=True)
    except ImportError:
        print("FATAL ERROR: moviepy not installed. Run: pip install moviepy", flush=True)
        sys.exit(1)

# ── helpers for resize / crop (v1 vs v2) ─────────────────────────────────────
def _resize_clip(clip, newsize):
    """Resize a clip — works for both moviepy v1 and v2."""
    if MOVIEPY_V2:
        return clip.resized(newsize)
    else:
        try:
            from moviepy.video.fx.all import resize as _resize
            return clip.fx(_resize, newsize=newsize)
        except Exception:
            return clip.resize(newsize)

def _crop_clip(clip, x_center, y_center, width, height):
    """Crop a clip — works for both moviepy v1 and v2."""
    if MOVIEPY_V2:
        x1 = x_center - width / 2
        y1 = y_center - height / 2
        return clip.cropped(x1=x1, y1=y1, width=width, height=height)
    else:
        try:
            from moviepy.video.fx.all import crop as _crop
            return clip.fx(_crop, x_center=x_center, y_center=y_center,
                           width=width, height=height)
        except Exception:
            return clip.crop(x_center=x_center, y_center=y_center,
                             width=width, height=height)


def pad_or_crop(clip, target_size=None):
    """Fit clip into target_size (width x height) by cropping to fill.
    If target_size is None the clip is returned as-is (native resolution kept).
    """
    if target_size is None:
        return clip
    try:
        w, h = clip.size
        target_w, target_h = target_size
        if w <= 0 or h <= 0:
            return clip

        clip_ratio   = w / h
        target_ratio = target_w / target_h

        if abs(clip_ratio - target_ratio) < 0.01:
            return _resize_clip(clip, (target_w, target_h))
        elif clip_ratio > target_ratio:
            # Clip is wider — match height then crop width
            c = _resize_clip(clip, (int(target_h * clip_ratio), target_h))
            x_center = c.size[0] / 2
            y_center = c.size[1] / 2
            return _crop_clip(c, x_center, y_center, target_w, target_h)
        else:
            # Clip is taller — match width then crop height
            c = _resize_clip(clip, (target_w, int(target_w / clip_ratio)))
            x_center = c.size[0] / 2
            y_center = c.size[1] / 2
            return _crop_clip(c, x_center, y_center, target_w, target_h)
    except Exception as e:
        print(f"  [WARN] pad_or_crop failed ({e}), returning original clip.", flush=True)
        return clip


def detect_target_size(videos, photos):
    """Return (width, height) from the first readable video, or first photo,
    capped to 1920×1080 (landscape) or 1080×1920 (portrait).
    Falls back to 1920×1080 if nothing is readable.
    """
    # Try first video
    for v in videos:
        cap = cv2.VideoCapture(v)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0:
                # Preserve orientation but cap resolution to 1080p
                if w >= h:                         # landscape
                    scale = min(1.0, 1920 / w, 1080 / h)
                else:                              # portrait
                    scale = min(1.0, 1080 / w, 1920 / h)
                return (int(w * scale) & ~1, int(h * scale) & ~1)  # even dims for h264

    # Try first photo
    for p in photos:
        img = cv2.imread(p)
        if img is not None:
            h, w = img.shape[:2]
            if w >= h:
                scale = min(1.0, 1920 / w, 1080 / h)
            else:
                scale = min(1.0, 1080 / w, 1920 / h)
            return (int(w * scale) & ~1, int(h * scale) & ~1)

    return (1920, 1080)  # safe default


def analyze_video(filepath):
    """Returns (is_usable, duration, motion_score)."""
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        return False, 0, 0

    fps         = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps <= 0 or frame_count <= 0:
        cap.release()
        return False, 0, 0

    duration     = frame_count / fps
    blur_scores  = []
    motion_scores = []
    prev_frame   = None

    for _ in range(10):
        ret, frame = cap.read()
        if not ret:
            break
        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small_gray = cv2.resize(gray, (128, 128))
        blur_scores.append(cv2.Laplacian(small_gray, cv2.CV_64F).var())
        if prev_frame is not None:
            motion_scores.append(float(np.mean(cv2.absdiff(small_gray, prev_frame))))
        prev_frame = small_gray

    cap.release()

    if not blur_scores:
        return False, duration, 0

    avg_blur   = float(np.mean(blur_scores))
    avg_motion = float(np.mean(motion_scores)) if motion_scores else 0.0

    if avg_blur < 10:
        return False, duration, avg_motion
    return True, duration, avg_motion


def process_photo(filepath, duration):
    clip = ImageClip(filepath).with_duration(duration) if MOVIEPY_V2 \
           else ImageClip(filepath).set_duration(duration)
    return pad_or_crop(clip)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--media_dir",   required=True)
    parser.add_argument("--audio_file",  required=True)
    parser.add_argument("--output_file", required=True)
    args = parser.parse_args()

    MEDIA_DIR   = args.media_dir
    AUDIO_FILE  = args.audio_file
    OUTPUT_FILE = args.output_file

    try:
        # ── PHASE 1: Audio Analysis ──────────────────────────────────────────
        print("PHASE 1: Asset Preparation & Analysis (Loading audio...)", flush=True)

        # Suppress mpg123 ID3-tag warnings (harmless C-library stderr chatter
        # about malformed comment frames in the MP3 — audio still loads fine).
        import io, contextlib
        _devnull = open(os.devnull, "w")
        with contextlib.redirect_stderr(_devnull):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                y, sr = librosa.load(AUDIO_FILE, duration=125.0)
        _devnull.close()
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times   = librosa.frames_to_time(beats, sr=sr)

        tempo_val = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
        print(f"Detected tempo: {tempo_val:.2f} BPM, total beats: {len(beat_times)}", flush=True)

        if len(beat_times) < 2:
            print("FATAL ERROR: Not enough beats detected in audio file.", flush=True)
            return

        # ── PHASE 2: Asset Selection ─────────────────────────────────────────
        print("PHASE 2: Intelligent Asset Selection", flush=True)
        if not os.path.isdir(MEDIA_DIR):
            print(f"FATAL ERROR: Media directory not found: {MEDIA_DIR}", flush=True)
            return

        files  = [os.path.join(MEDIA_DIR, f) for f in os.listdir(MEDIA_DIR)
                  if not f.startswith(".")]
        videos = [f for f in files if f.lower().endswith(('.mov', '.mp4'))]
        photos = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        print(f"Found {len(videos)} videos and {len(photos)} photos. Checking videos...", flush=True)

        usable_videos = []
        for idx, v in enumerate(videos):
            usable, dur, motion = analyze_video(v)
            if usable and dur >= 1.0:
                usable_videos.append({"path": v, "duration": dur, "motion": motion})
            print(f"  [{idx+1}/{len(videos)}] {os.path.basename(v)} — "
                  f"Usable: {usable}, Duration: {dur:.1f}s, Motion: {motion:.1f}", flush=True)

        print(f"Accepted {len(usable_videos)} videos.", flush=True)

        if len(usable_videos) == 0 and len(photos) == 0:
            print("FATAL ERROR: No usable media files found in the directory.", flush=True)
            return

        # Auto-detect target resolution from the first real media file
        _vpaths = [v["path"] for v in usable_videos]
        TARGET_SIZE = detect_target_size(_vpaths, photos)
        orientation = "landscape" if TARGET_SIZE[0] >= TARGET_SIZE[1] else "portrait"
        print(f"Auto-detected target resolution: {TARGET_SIZE[0]}x{TARGET_SIZE[1]} ({orientation})", flush=True)

        random.seed(42)
        random.shuffle(usable_videos)
        random.shuffle(photos)


        # ── PHASE 3: On-the-Beat Cutting ─────────────────────────────────────
        print("PHASE 3: Automated 'On-the-Beat' Cutting", flush=True)
        final_clips = []
        beat_idx    = 0
        media_pool  = {"videos": usable_videos.copy(), "photos": photos.copy()}

        while beat_idx < len(beat_times) - 1:
            beats_to_skip = random.choice([2, 4, 8])
            next_beat_idx = min(beat_idx + beats_to_skip, len(beat_times) - 1)

            start_time = beat_times[beat_idx]
            end_time   = beat_times[next_beat_idx]
            duration   = end_time - start_time

            if duration <= 0:
                beat_idx = next_beat_idx + 1
                continue

            pick_video = (random.random() < 0.7) and len(media_pool["videos"]) > 0
            clip       = None
            clip_dur   = duration

            if pick_video:
                vid_info = media_pool["videos"].pop(0)
                try:
                    video_clip = VideoFileClip(vid_info["path"])
                    cur_dur    = min(video_clip.duration, duration)
                    max_start  = max(0, video_clip.duration - cur_dur)
                    start_cut  = random.uniform(0, max_start)

                    if MOVIEPY_V2:
                        clip = video_clip.subclipped(start_cut, start_cut + cur_dur)
                    else:
                        clip = video_clip.subclip(start_cut, start_cut + cur_dur)

                    clip_dur = cur_dur
                except Exception as e:
                    print(f"  [WARN] Error loading video {os.path.basename(vid_info['path'])}: {e}", flush=True)
                    clip = None

                media_pool["videos"].append(vid_info)

            if clip is None and len(media_pool["photos"]) > 0:
                photo_path = media_pool["photos"].pop(0)
                try:
                    clip = ImageClip(photo_path).with_duration(duration) if MOVIEPY_V2 \
                           else ImageClip(photo_path).set_duration(duration)
                    clip_dur = duration
                except Exception as e:
                    print(f"  [WARN] Error loading photo {os.path.basename(photo_path)}: {e}", flush=True)
                    clip = None
                media_pool["photos"].append(photo_path)

            if clip is not None:
                try:
                    clip = pad_or_crop(clip, TARGET_SIZE)   # use auto-detected size
                    final_clips.append(clip)
                except Exception as e:
                    print(f"  [WARN] pad_or_crop error: {e}", flush=True)

            # Advance beat_idx forward by however many beats the clip covered
            consumed_time = start_time + clip_dur
            new_idx = beat_idx + 1
            for i in range(beat_idx + 1, len(beat_times)):
                if beat_times[i] >= consumed_time - 0.05:
                    new_idx = i
                    break
            beat_idx = max(beat_idx + 1, new_idx)

            if start_time >= 120.0:
                break   # target 2 minutes

        if not final_clips:
            print("FATAL ERROR: Failed to generate any valid clips from the media.", flush=True)
            return

        print(f"PHASE 4: Composing {len(final_clips)} clips...", flush=True)


        final_video = concatenate_videoclips(final_clips, method="compose")

        final_dur = min(120.0, final_video.duration)
        if MOVIEPY_V2:
            final_video = final_video.subclipped(0, final_dur)
        else:
            final_video = final_video.subclip(0, final_dur)

        print("Adding audio track...", flush=True)
        audio_clip = AudioFileClip(AUDIO_FILE)
        audio_dur  = min(final_dur, audio_clip.duration)
        if MOVIEPY_V2:
            audio_clip  = audio_clip.subclipped(0, audio_dur)
            final_video = final_video.with_audio(audio_clip)
        else:
            audio_clip  = audio_clip.subclip(0, audio_dur)
            final_video = final_video.set_audio(audio_clip)

        print(f"Exporting to {OUTPUT_FILE} (this may take several minutes)...", flush=True)

        write_kwargs = dict(
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            threads=max(1, (os.cpu_count() or 2) - 1),
            preset="fast",
        )
        # logger=None suppresses moviepy's own progress bar (v1.x only)
        if not MOVIEPY_V2:
            write_kwargs["logger"] = None

        final_video.write_videofile(OUTPUT_FILE, **write_kwargs)
        print("Process completed successfully.", flush=True)

    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
