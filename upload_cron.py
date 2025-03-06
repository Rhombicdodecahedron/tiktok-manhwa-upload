import os
import logging
import subprocess
import time
import re
import random

# from tiktok_uploader.upload import upload_video as upload_video_with_cookies

VIDEO_DIR = "videos"
VIDEO_USER = "manhwa-tiktok"
INTERVAL = 5400  # 1 hour 30 minutes

# General hashtags
GENERAL_TAGS = "#fyp #fy #viral #manhwa #manhwareccomendation #manhwaedit #manhwas #manhwafyp #manhwareccomendations #webtoon #webtoonedit #webtoonfyp #webtoonrecommendation #webtoonrecommendations #webtoons #manga #otaku #weeb #animegirl #animeboy #animeaction #animeshorts #animefandom #animefanatic #koreanwebtoon"

# Specific hashtags for different manhwa
MANHWA_TAGS = {
    "orv": "#orv #orvedit #orvfyp #orvrecommendation #omniscientreadersviewpoint #omniscientreadersviewpointedit #omniscientreadersviewpointfyp #omniscientreadersviewpointmanhwa #omniscientreadersviewpointmanhwaedit",
    "sl": "#sololeveling #sololevelingedit #sololevelingfyp #sololevelingmanhwa #sololevelinganime #sololevelingrecommendation",
    "smn": "#solomaxlevelnewbie #smn #smnfyp #solomaxlevelnewbierecommendation",
    "me": "#mercenaryenrollment #mercenaryenrollmentfyp #mercenaryenrollmentedit #mercenaryenrollmentmanhwa",
    "rmhs": "#returnofthemounthuasect #rmhs #mounthuasect #returnofthemounthuasectedit"
}

MANHWA_NAMES = {
    "orv": "Omniscient Reader's Viewpoint",
    "sl": "Solo Leveling",
    "smn": "Solo Max-Level Newbie",
    "me": "Mercenary Enrollment",
    "rmhs": "Return Of The Mount Hua Sect"
}


def extract_manhwa_info(filename):
    """Extracts manhwa type, chapter, and part number from the filename."""
    match = re.search(r'([a-z]+)-(\d+)_part_(\d+)', filename)
    if match:
        manhwa_key = match.group(1)
        chapter = int(match.group(2))
        part = int(match.group(3))
        return manhwa_key, chapter, part
    return None, None, None


def clean_title(title):
    """Removes non-BMP characters to avoid ChromeDriver errors."""
    return ''.join(c for c in title if ord(c) <= 0xFFFF)


def generate_title(video):
    """Generates a dynamic video title based on the filename."""
    filename = os.path.basename(video)
    manhwa_key, chapter, part = extract_manhwa_info(filename)

    title_templates = [
        "🔥 {manhwa_name} - Chapter {chapter}, Part {part}! 📖✨",
        "📖 {manhwa_name} - A new journey begins! Chapter {chapter}, Part {part}! 🚀",
        "⚔️ {manhwa_name} - Action-packed moments in Chapter {chapter}, Part {part}! 🎥🔥",
        "🔥 {manhwa_name} - Unfolding the story in Chapter {chapter}, Part {part}! ⚡",
        "📖 {manhwa_name} - Don’t miss Chapter {chapter}, Part {part}! 💥"
    ]

    if manhwa_key and chapter and part:
        manhwa_name = MANHWA_NAMES.get(manhwa_key, "Unknown Manhwa")
        title_template = random.choice(title_templates)  # Randomize title templates
        title = title_template.format(manhwa_name=manhwa_name, chapter=chapter, part=part)
        return clean_title(title)  # Remove unsupported characters
    return clean_title("🔥 Check out this amazing manhwa! 📖✨")


def upload_video(video, video_path):
    """Uploads a single video for a user and deletes it after successful upload."""
    logging.info(f"Starting upload for {VIDEO_USER}: {video}")

    title = generate_title(video)
    filename = os.path.basename(video)
    tags = GENERAL_TAGS

    manhwa_key, _, _ = extract_manhwa_info(filename)
    if manhwa_key and manhwa_key in MANHWA_TAGS:
        tags += f" {MANHWA_TAGS[manhwa_key]}"

    full_title = f"{title} | {tags}"

    try:
        subprocess.run([
            "python", "cli.py", "upload", "--user", VIDEO_USER, "-v", video, "-t", full_title,
        ], check=True)

        cookies_list = [
            {
                'name': 'sessionid',
                'value': '6aa7523f1358a36bd8cf1d4d04bbb4bf',
                'domain': '.tiktok.com',
                'path': '/',
                'expiry': '2025-08-26T22:46:03.034Z'
            },
        ]

        # upload_video_with_cookies(
        #    filename=video_path,
        #    description=full_title,
        #    sessionid="6aa7523f1358a36bd8cf1d4d04bbb4bf",
        #    headless=True
        # )

        logging.info(f"Upload successful: {video}")
        os.remove(video_path)  # Delete the video file after upload
        logging.info(f"Deleted video file: {video}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Upload failed: {e}")


def get_videos_by_chapter(directory):
    """Groups videos by manhwa and chapter, then sorts them by part."""
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv')
    videos = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(video_extensions)]

    video_dict = {}
    for video in videos:
        manhwa_key, chapter, part = extract_manhwa_info(os.path.basename(video))
        if manhwa_key and chapter and part:
            video_dict.setdefault((manhwa_key, chapter), []).append((part, video))

    # Sort each chapter's videos by part
    for key in video_dict:
        video_dict[key].sort()

    return video_dict


def schedule_uploads():
    """Schedules video uploads by randomly selecting a manhwa and then uploading its chapters in order."""
    while True:
        logging.info("Checking for available videos...")
        videos_by_chapter = get_videos_by_chapter(VIDEO_DIR)
        if videos_by_chapter:
            sorted_manhwa = list(set(manhwa for manhwa, _ in videos_by_chapter.keys()))
            random.shuffle(sorted_manhwa)  # Randomize the manhwa selection order
            for manhwa_key in sorted_manhwa:
                sorted_chapters = sorted([ch for m, ch in videos_by_chapter.keys() if m == manhwa_key])
                for chapter in sorted_chapters:
                    logging.info(f"Uploading {manhwa_key} - Chapter {chapter}...")
                    videos = [v[1] for v in videos_by_chapter[(manhwa_key, chapter)]]
                    for video_path in videos:
                        upload_video(os.path.basename(video_path), video_path)
        else:
            logging.info("No videos found. Retrying after interval...")
        logging.info(f"Waiting {INTERVAL} seconds (1 hour 30 minutes) before next check...")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    schedule_uploads()
