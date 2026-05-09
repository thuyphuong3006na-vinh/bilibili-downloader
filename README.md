# 🎬 Bilibili Downloader

Công cụ tải video Bilibili — hỗ trợ tải **đơn lẻ** theo URL/BVID và tải **hàng loạt** toàn bộ kênh.

## Tính năng

- Tải video đơn theo URL hoặc BVID
- Tải hàng loạt toàn bộ video trên một kênh (UID hoặc URL space)
- Chọn chất lượng video (best / 1080p / 720p / 480p)
- Tải kèm phụ đề (zh-Hans, en)
- Lưu danh sách video dạng JSON
- Delay tùy chỉnh giữa các lượt tải để tránh bị chặn

## Cài đặt

```bash
pip install yt-dlp requests
```

## Cách dùng

### Tải video đơn lẻ

```bash
# Theo URL
python bilibili_downloader.py video https://www.bilibili.com/video/BVxxxxxxxx

# Theo BVID
python bilibili_downloader.py video BV1xx411c7mD

# Kèm phụ đề
python bilibili_downloader.py video BV1xx411c7mD --subtitle
```

### Tải hàng loạt theo kênh

```bash
# Toàn bộ kênh theo UID
python bilibili_downloader.py channel 12345678

# Theo URL space
python bilibili_downloader.py channel https://space.bilibili.com/12345678

# Tải 20 video mới nhất
python bilibili_downloader.py channel 12345678 --max 20

# Tùy chỉnh đầy đủ
python bilibili_downloader.py channel 12345678 \
  --max 50 \
  --quality "bestvideo[height<=1080]+bestaudio/best" \
  --subtitle \
  --delay 3 \
  --output ./videos
```

## Tham số

| Tham số | Mô tả | Mặc định |
|---|---|---|
| `mode` | `video` hoặc `channel` | bắt buộc |
| `target` | URL/BVID hoặc UID/URL kênh | bắt buộc |
| `-o, --output` | Thư mục lưu video | `./bilibili_downloads` |
| `-q, --quality` | Format yt-dlp | best mp4 |
| `--max` | Số video tối đa từ kênh (0 = tất cả) | `0` |
| `--cookies` | File cookies Netscape (để tải 1080p/4K) | — |
| `--subtitle` | Tải kèm phụ đề | off |
| `--delay` | Delay (giây) giữa các video | `2` |

## Tải 1080p / 4K

Bilibili yêu cầu đăng nhập để tải chất lượng cao. Cách lấy cookies:

1. Đăng nhập Bilibili trên Chrome/Edge
2. Cài extension **Get cookies.txt LOCALLY**
3. Xuất cookies → lưu thành `cookies.txt`
4. Thêm `--cookies cookies.txt` vào lệnh

## Yêu cầu

- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [requests](https://pypi.org/project/requests/)

## Lưu ý

Chỉ sử dụng cho mục đích cá nhân, không tái phân phối. Tuân thủ điều khoản sử dụng của Bilibili.