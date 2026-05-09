#!/usr/bin/env python3
"""
Bilibili Video Downloader
- Tải video đơn lẻ theo URL / BVID
- Tải hàng loạt toàn bộ video trên 1 kênh (UID hoặc URL space)
Yêu cầu: pip install requests yt-dlp
"""

import os, sys, re, json, time, argparse, requests

try:
    import yt_dlp
except ImportError:
    print("[LỖI] Cần cài yt-dlp: pip install yt-dlp"); sys.exit(1)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

API_USER_VIDEOS = (
    "https://api.bilibili.com/x/space/arc/search"
    "?mid={uid}&pn={page}&ps={page_size}&order=pubdate&jsonp=jsonp"
)

DEFAULT_OUTPUT_DIR = "./bilibili_downloads"
DEFAULT_QUALITY    = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
DELAY_BETWEEN      = 2


def extract_uid_from_url(url):
    for pat in [r"space\.bilibili\.com/(\d+)", r"bilibili\.com/space/(\d+)"]:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def get_user_info(uid):
    try:
        r = requests.get(
            f"https://api.bilibili.com/x/space/acc/info?mid={uid}&jsonp=jsonp",
            headers=HEADERS, timeout=10
        )
        d = r.json()
        if d.get("code") == 0:
            return d["data"]
    except Exception as e:
        print(f"  [WARN] Không lấy được thông tin kênh: {e}")
    return {}


def fetch_channel_videos(uid, max_videos=0):
    videos, page, ps = [], 1, 50
    print(f"\n📡 Đang lấy danh sách video từ UID {uid}...")

    while True:
        url = API_USER_VIDEOS.format(uid=uid, page=page, page_size=ps)
        try:
            data = requests.get(url, headers=HEADERS, timeout=15).json()
        except Exception as e:
            print(f"  [LỖI] trang {page}: {e}"); break

        if data.get("code") != 0:
            print(f"  [LỖI API] {data.get('message', 'unknown')}"); break

        vlist = data["data"]["list"]["vlist"]
        if not vlist:
            break

        for v in vlist:
            videos.append({
                "bvid":     v["bvid"],
                "title":    v["title"],
                "pubdate":  v["created"],
                "play":     v.get("play", 0),
                "duration": v.get("length", ""),
            })
            if max_videos and len(videos) >= max_videos:
                break

        print(f"  Trang {page}: +{len(vlist)} video (tổng {len(videos)})")

        if (max_videos and len(videos) >= max_videos) or \
           len(videos) >= data["data"]["page"]["count"] or \
           len(vlist) < ps:
            break

        page += 1
        time.sleep(0.5)

    return videos


def build_ydl_opts(output_dir, quality, cookies_file=None, subtitle=False):
    opts = {
        "format":              quality,
        "outtmpl":             os.path.join(output_dir, "%(title)s [%(id)s].%(ext)s"),
        "merge_output_format": "mp4",
        "http_headers":        HEADERS,
        "retries":             5,
        "ignoreerrors":        True,
        "quiet":               False,
        "no_warnings":         False,
    }
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file
    if subtitle:
        opts.update({
            "writesubtitles":    True,
            "writeautomaticsub": True,
            "subtitleslangs":    ["zh-Hans", "en"],
        })
    return opts


def download_single(url_or_bvid, output_dir, quality,
                    cookies_file=None, subtitle=False):
    url = (f"https://www.bilibili.com/video/{url_or_bvid}"
           if url_or_bvid.upper().startswith("BV") else url_or_bvid)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n⬇  Đang tải: {url}")
    with yt_dlp.YoutubeDL(build_ydl_opts(output_dir, quality, cookies_file, subtitle)) as ydl:
        ydl.download([url])


def download_channel(uid_or_url, output_dir, quality,
                     max_videos=0, cookies_file=None,
                     subtitle=False, delay=DELAY_BETWEEN):
    uid = uid_or_url if uid_or_url.isdigit() else extract_uid_from_url(uid_or_url)
    if not uid:
        print(f"[LỖI] Không nhận ra: {uid_or_url}"); sys.exit(1)

    info = get_user_info(uid)
    name = info.get("name", uid) if info else uid
    if info:
        print(f"\n👤 Kênh: {name}  |  UID: {uid}  |  Fans: {info.get('fans', 0):,}")

    channel_dir = os.path.join(output_dir, re.sub(r'[\\/:*?"<>|]', "_", name))
    os.makedirs(channel_dir, exist_ok=True)

    videos = fetch_channel_videos(uid, max_videos)
    if not videos:
        print("[LỖI] Không tìm thấy video."); return

    total = len(videos)
    print(f"\n✅ {total} video → {channel_dir}\n")

    list_path = os.path.join(channel_dir, "_video_list.json")
    with open(list_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f"📋 Danh sách video: {list_path}\n")

    opts, failed = build_ydl_opts(channel_dir, quality, cookies_file, subtitle), []

    for idx, v in enumerate(videos, 1):
        url = f"https://www.bilibili.com/video/{v['bvid']}"
        print(f"[{idx:>4}/{total}] {v['title'][:60]}  ({v['bvid']})")
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                if ydl.download([url]) != 0:
                    failed.append(v["bvid"])
        except Exception as e:
            print(f"         ❌ {e}")
            failed.append(v["bvid"])
        if idx < total:
            time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"✅ Xong: {total - len(failed)}/{total} video")
    if failed:
        print(f"❌ Thất bại: {', '.join(failed)}")
    print(f"📁 {os.path.abspath(channel_dir)}")


def main():
    p = argparse.ArgumentParser(
        description="Bilibili Downloader – tải video đơn hoặc hàng loạt theo kênh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python bilibili_downloader.py video https://www.bilibili.com/video/BVxxxxxxxx
  python bilibili_downloader.py video BV1xx411c7mD --subtitle
  python bilibili_downloader.py channel 12345678
  python bilibili_downloader.py channel https://space.bilibili.com/12345678
  python bilibili_downloader.py channel 12345678 --max 20 --subtitle
  python bilibili_downloader.py video BV1xx411c7mD --cookies cookies.txt
"""
    )
    p.add_argument("mode", choices=["video", "channel"])
    p.add_argument("target")
    p.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("-q", "--quality", default=DEFAULT_QUALITY)
    p.add_argument("--max", type=int, default=0, dest="max_videos")
    p.add_argument("--cookies", default=None)
    p.add_argument("--subtitle", action="store_true")
    p.add_argument("--delay", type=float, default=DELAY_BETWEEN)
    a = p.parse_args()

    print("=" * 60)
    print("  🎬  Bilibili Downloader")
    print("=" * 60)

    if a.mode == "video":
        download_single(a.target, a.output, a.quality, a.cookies, a.subtitle)
    else:
        download_channel(a.target, a.output, a.quality,
                         a.max_videos, a.cookies, a.subtitle, a.delay)


if __name__ == "__main__":
    main()