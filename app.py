import streamlit as st
import subprocess
import sys
import os
import re
import json
import requests

st.set_page_config(
    page_title="Bilibili Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Bilibili Downloader")
st.caption("Tải video đơn lẻ hoặc hàng loạt theo kênh Bilibili")

def extract_uid(text):
    text = text.strip().split("?")[0].split("#")[0]
    if text.isdigit():
        return text
    for pat in [r"space\.bilibili\.com/(\d+)", r"bilibili\.com/space/(\d+)"]:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None

def fetch_channel_videos_ytdlp(uid, max_videos=10):
    """Dùng yt-dlp để lấy danh sách video — không bị Bilibili chặn."""
    channel_url = f"https://space.bilibili.com/{uid}/video"
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--playlist-end", str(max_videos),
        "--print", "%(id)s|||%(title)s|||%(duration_string)s",
        "--no-warnings",
        channel_url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if "|||" in line:
                parts = line.split("|||")
                if len(parts) >= 2:
                    videos.append({
                        "bvid":     parts[0].strip(),
                        "title":    parts[1].strip(),
                        "duration": parts[2].strip() if len(parts) > 2 else "",
                    })
        return videos
    except Exception as e:
        st.error(f"Lỗi lấy danh sách: {e}")
        return []

QUALITY_MAP = {
    "Tốt nhất (tự động)": "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "720p":  "bestvideo[height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]",
    "480p":  "bestvideo[height<=480][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]",
    "360p":  "bestvideo[height<=360][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]",
}

def run_ytdlp(url, quality, subtitle=False, output_dir="/tmp/bilibili"):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", QUALITY_MAP.get(quality, "best[ext=mp4]/best"),
        "--merge-output-format", "mp4",
        "--output", f"{output_dir}/%(title)s [%(id)s].%(ext)s",
        "--no-playlist",
        "--no-warnings",
        "--add-header", "Referer:https://www.bilibili.com",
    ]
    if subtitle:
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", "zh-Hans,en"]
    cmd.append(url)
    return cmd


# ── TABS ────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["⬇ Tải video đơn", "📦 Tải theo kênh"])

# ── Tab 1 ───────────────────────────────────────────────────────
with tab1:
    st.subheader("Tải video đơn lẻ")
    url_input = st.text_input(
        "Link video hoặc BVID",
        placeholder="https://www.bilibili.com/video/BVxxxxxxxx  hoặc  BV1xx411c7mD"
    )
    col1, col2 = st.columns(2)
    with col1:
        quality1 = st.selectbox("Chất lượng", list(QUALITY_MAP.keys()), key="q1")
    with col2:
        subtitle1 = st.checkbox("Tải kèm phụ đề", key="s1")

    if st.button("▶ Bắt đầu tải", key="btn1", type="primary"):
        raw = url_input.strip()
        if not raw:
            st.warning("Vui lòng nhập link hoặc BVID!")
        else:
            if raw.upper().startswith("BV"):
                video_url = f"https://www.bilibili.com/video/{raw}"
            else:
                video_url = raw.split("?")[0]

            cmd = run_ytdlp(video_url, quality1, subtitle1)
            log_box = st.empty()
            log_lines = []
            with st.spinner("⏳ Đang tải..."):
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True
                    )
                    for line in proc.stdout:
                        log_lines.append(line.rstrip())
                        log_box.code("\n".join(log_lines[-20:]))
                    proc.wait()
                    if proc.returncode == 0:
                        st.success("✅ Tải xong!")
                        files = [f for f in os.listdir("/tmp/bilibili")
                                 if f.endswith((".mp4", ".mkv", ".webm"))]
                        for f in files:
                            fp = f"/tmp/bilibili/{f}"
                            with open(fp, "rb") as fh:
                                st.download_button(
                                    label=f"⬇ Tải về máy: {f}",
                                    data=fh,
                                    file_name=f,
                                    mime="video/mp4",
                                    key=f"dl_{f}"
                                )
                    else:
                        st.error("❌ Tải thất bại. Xem log ở trên.")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

# ── Tab 2 ───────────────────────────────────────────────────────
with tab2:
    st.subheader("Tải hàng loạt theo kênh")
    ch_input = st.text_input(
        "UID hoặc URL kênh",
        placeholder="12345678  hoặc  https://space.bilibili.com/12345678"
    )

    uid_preview = extract_uid(ch_input) if ch_input.strip() else None
    if uid_preview:
        st.caption(f"UID nhận được: `{uid_preview}`")

    col3, col4, col5 = st.columns(3)
    with col3:
        quality2 = st.selectbox("Chất lượng", list(QUALITY_MAP.keys()), key="q2")
    with col4:
        max_vids = st.number_input("Số video tối đa", min_value=1, value=5, step=1)
    with col5:
        subtitle2 = st.checkbox("Tải kèm phụ đề", key="s2")

    if st.button("🔍 Xem danh sách video trước", key="btn_list"):
        uid = extract_uid(ch_input.strip()) if ch_input.strip() else None
        if not uid:
            st.error("Không tìm thấy UID!")
        else:
            with st.spinner("Đang lấy danh sách qua yt-dlp..."):
                videos = fetch_channel_videos_ytdlp(uid, int(max_vids))
            if videos:
                st.success(f"✅ Tìm thấy {len(videos)} video")
                for i, v in enumerate(videos, 1):
                    bvid = v['bvid']
                    url  = f"https://www.bilibili.com/video/{bvid}"
                    st.write(f"`{i}.` [{v['title']}]({url}) — ⏱ {v['duration']}")
            else:
                st.error("Không lấy được danh sách video.")

    if st.button("▶ Bắt đầu tải kênh", key="btn2", type="primary"):
        uid = extract_uid(ch_input.strip()) if ch_input.strip() else None
        if not uid:
            st.error("Không tìm thấy UID!")
        else:
            with st.spinner("Đang lấy danh sách video..."):
                videos = fetch_channel_videos_ytdlp(uid, int(max_vids))
            if not videos:
                st.error("Không lấy được danh sách video!")
            else:
                st.info(f"Bắt đầu tải {len(videos)} video...")
                prog = st.progress(0)
                status = st.empty()
                os.makedirs("/tmp/bilibili", exist_ok=True)
                done = 0
                for i, v in enumerate(videos):
                    bvid = v["bvid"]
                    video_url = f"https://www.bilibili.com/video/{bvid}"
                    status.info(f"⬇ [{i+1}/{len(videos)}] {v['title'][:70]}")
                    cmd = run_ytdlp(video_url, quality2, subtitle2)
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        done += 1
                    prog.progress((i + 1) / len(videos))

                st.success(f"✅ Đã tải xong {done}/{len(videos)} video!")
                files = [f for f in os.listdir("/tmp/bilibili")
                         if f.endswith((".mp4", ".mkv", ".webm"))]
                for f in files:
                    fp = f"/tmp/bilibili/{f}"
                    with open(fp, "rb") as fh:
                        st.download_button(
                            label=f"⬇ {f}",
                            data=fh,
                            file_name=f,
                            mime="video/mp4",
                            key=f"dl2_{f}"
                        )

st.divider()
st.caption("⚠️ Streamlit Cloud lưu file tạm thời — tải về máy ngay sau khi xong.")