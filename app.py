import streamlit as st
import subprocess
import sys
import os
import json
import re
import requests
import threading
import queue

st.set_page_config(
    page_title="Bilibili Downloader",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Bilibili Downloader")
st.caption("Tải video đơn lẻ hoặc hàng loạt theo kênh Bilibili")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def get_user_info(uid):
    try:
        r = requests.get(
            f"https://api.bilibili.com/x/space/acc/info?mid={uid}&jsonp=jsonp",
            headers=HEADERS, timeout=10
        )
        d = r.json()
        if d.get("code") == 0:
            return d["data"]
    except:
        pass
    return {}

def fetch_channel_videos(uid, max_videos=0):
    videos, page, ps = [], 1, 50
    while True:
        url = (f"https://api.bilibili.com/x/space/arc/search"
               f"?mid={uid}&pn={page}&ps={ps}&order=pubdate&jsonp=jsonp")
        try:
            data = requests.get(url, headers=HEADERS, timeout=15).json()
        except:
            break
        if data.get("code") != 0:
            break
        vlist = data["data"]["list"]["vlist"]
        if not vlist:
            break
        for v in vlist:
            videos.append({
                "bvid": v["bvid"],
                "title": v["title"],
                "duration": v.get("length", ""),
                "play": v.get("play", 0),
            })
            if max_videos and len(videos) >= max_videos:
                break
        total = data["data"]["page"]["count"]
        if (max_videos and len(videos) >= max_videos) or \
           len(videos) >= total or len(vlist) < ps:
            break
        page += 1
    return videos

def extract_uid(text):
    text = text.strip()
    if text.isdigit():
        return text
    for pat in [r"space\.bilibili\.com/(\d+)", r"bilibili\.com/space/(\d+)"]:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None

def build_cmd(mode, target, quality, max_videos=0, subtitle=False, delay=2):
    q_map = {
        "Tốt nhất (tự động)": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best",
        "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best",
        "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best",
        "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best",
    }
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", q_map.get(quality, "best"),
        "--merge-output-format", "mp4",
        "--output", "/tmp/bilibili/%(title)s [%(id)s].%(ext)s",
        "--no-playlist",
    ]
    if subtitle:
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", "zh-Hans,en"]

    if mode == "video":
        if target.upper().startswith("BV"):
            cmd.append(f"https://www.bilibili.com/video/{target}")
        else:
            cmd.append(target)
    else:
        uid = extract_uid(target)
        if not uid:
            return None, "Không tìm thấy UID từ link kênh"
        base = f"https://space.bilibili.com/{uid}/video"
        cmd += ["--playlist-end", str(max_videos) if max_videos > 0 else "999999"]
        cmd.append(base)

    return cmd, None


# ── UI ──────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["⬇ Tải video đơn", "📦 Tải theo kênh"])

with tab1:
    st.subheader("Tải video đơn lẻ")
    url_input = st.text_input(
        "Link video hoặc BVID",
        placeholder="https://www.bilibili.com/video/BVxxxxxxxx  hoặc  BV1xx411c7mD"
    )
    col1, col2 = st.columns(2)
    with col1:
        quality1 = st.selectbox("Chất lượng", ["Tốt nhất (tự động)", "1080p", "720p", "480p", "360p"], key="q1")
    with col2:
        subtitle1 = st.checkbox("Tải kèm phụ đề", key="s1")

    if st.button("▶ Bắt đầu tải", key="btn1", type="primary"):
        if not url_input.strip():
            st.warning("Vui lòng nhập link hoặc BVID!")
        else:
            cmd, err = build_cmd("video", url_input.strip(), quality1, subtitle=subtitle1)
            if err:
                st.error(err)
            else:
                st.info("⏳ Đang tải... (Streamlit Cloud không lưu file lâu dài — xem hướng dẫn bên dưới)")
                log_box = st.empty()
                log_lines = []
                os.makedirs("/tmp/bilibili", exist_ok=True)
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1
                    )
                    for line in proc.stdout:
                        log_lines.append(line.rstrip())
                        log_box.code("\n".join(log_lines[-30:]))
                    proc.wait()
                    if proc.returncode == 0:
                        st.success("✅ Tải xong!")
                        files = os.listdir("/tmp/bilibili")
                        for f in files:
                            fp = f"/tmp/bilibili/{f}"
                            with open(fp, "rb") as fh:
                                st.download_button(
                                    label=f"⬇ Tải về: {f}",
                                    data=fh,
                                    file_name=f,
                                    mime="video/mp4"
                                )
                    else:
                        st.error("❌ Có lỗi xảy ra. Xem log ở trên.")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

with tab2:
    st.subheader("Tải hàng loạt theo kênh")
    ch_input = st.text_input(
        "UID hoặc URL kênh",
        placeholder="12345678  hoặc  https://space.bilibili.com/12345678"
    )

    uid_preview = extract_uid(ch_input) if ch_input.strip() else None
    if uid_preview:
        with st.spinner("Đang lấy thông tin kênh..."):
            info = get_user_info(uid_preview)
        if info:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tên kênh", info.get("name", "—"))
            c2.metric("Fans", f"{info.get('fans', 0):,}")
            c3.metric("UID", uid_preview)

    col3, col4, col5 = st.columns(3)
    with col3:
        quality2 = st.selectbox("Chất lượng", ["Tốt nhất (tự động)", "720p", "480p", "360p"], key="q2")
    with col4:
        max_vids = st.number_input("Số video tối đa", min_value=0, value=10, step=5,
                                   help="0 = tải tất cả")
    with col5:
        subtitle2 = st.checkbox("Tải kèm phụ đề", key="s2")

    if st.button("🔍 Xem danh sách trước", key="btn_list"):
        if not ch_input.strip():
            st.warning("Nhập UID hoặc URL kênh!")
        else:
            uid = extract_uid(ch_input.strip())
            if not uid:
                st.error("Không tìm thấy UID!")
            else:
                with st.spinner(f"Đang lấy danh sách video..."):
                    videos = fetch_channel_videos(uid, max_vids if max_vids > 0 else 20)
                st.success(f"Tìm thấy {len(videos)} video")
                for i, v in enumerate(videos, 1):
                    st.write(f"`{i}.` [{v['title']}](https://www.bilibili.com/video/{v['bvid']}) — {v['duration']}")

    if st.button("▶ Bắt đầu tải kênh", key="btn2", type="primary"):
        if not ch_input.strip():
            st.warning("Nhập UID hoặc URL kênh!")
        else:
            st.info("⏳ Đang tải hàng loạt...")
            uid = extract_uid(ch_input.strip())
            if not uid:
                st.error("Không tìm thấy UID!")
            else:
                videos = fetch_channel_videos(uid, max_vids if max_vids > 0 else 0)
                prog = st.progress(0)
                status = st.empty()
                os.makedirs("/tmp/bilibili", exist_ok=True)
                done = 0
                for i, v in enumerate(videos):
                    status.write(f"⬇ [{i+1}/{len(videos)}] {v['title'][:60]}")
                    cmd, _ = build_cmd("video", v["bvid"], quality2, subtitle=subtitle2)
                    subprocess.run(cmd, capture_output=True)
                    done += 1
                    prog.progress(done / len(videos))
                st.success(f"✅ Đã tải {done}/{len(videos)} video!")
                files = os.listdir("/tmp/bilibili")
                for f in files:
                    fp = f"/tmp/bilibili/{f}"
                    with open(fp, "rb") as fh:
                        st.download_button(f"⬇ {f}", fh, file_name=f, mime="video/mp4")

st.divider()
st.caption("⚠️ Streamlit Cloud lưu file tạm thời — tải về máy ngay sau khi xong. Để tải không giới hạn hãy chạy app trên máy cá nhân.")