import os
import logging
import subprocess
import time
import re
import random
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

VIDEO_DIR = "VideosDirPath"
VIDEO_USER = "manhwa-tiktok"
INTERVAL = 5400  # 1 hour 30 minutes
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
DRIVE_FOLDER_ID = "1SMGAeNak58ZAF9rgEoP4QOgiFM-FH2YI"

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


def authenticate_drive():
    """Authenticates with Google Drive API."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("drive", "v3", credentials=creds)


def get_videos_from_drive(service):
    """Gets a list of video files from Google Drive."""
    query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType contains 'video'"
    response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    return response.get('files', [])


def download_video(service, file_id, file_name):
    """Downloads a video file from Google Drive."""
    local_path = os.path.join(VIDEO_DIR, file_name)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logging.info(f"Downloading {file_name}... {int(status.progress() * 100)}% done")
    logging.info(f"Download complete: {local_path}")
    return local_path


def delete_drive_video(service, file_id):
    """Deletes a video file from Google Drive after processing."""
    service.files().delete(fileId=file_id).execute()
    logging.info(f"Deleted video from Drive: {file_id}")


def download_videos(service):
    """Downloads all video files from Google Drive."""
    videos = get_videos_from_drive(service)
    downloaded_videos = {}
    for video in videos:
        downloaded_videos[video['name']] = (video['id'], download_video(service, video['id'], video['name']))
    return downloaded_videos


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
        return f"{title} {GENERAL_TAGS} {MANHWA_TAGS.get(manhwa_key, '')}"
    return "🔥 Check out this amazing manhwa! 📖✨"


def upload_video(video, video_path):
    """Uploads a single video for a user and deletes it after successful upload."""
    logging.info(f"Starting upload for {VIDEO_USER}: {video}")

    subprocess.run([
        "python", "cli.py", "upload", "--user", VIDEO_USER, "-v", video, "-t", generate_title(video)
    ], check=True)
    logging.info(f"Upload successful: {video}")
    os.remove(video_path)  # Delete the local file after upload
    logging.info(f"Deleted local video file: {video}")


def extract_manhwa_info(filename):
    """Extracts manhwa type, chapter, and part number from the filename."""
    match = re.search(r'([a-z]+)-(\d+)_part_(\d+)', filename)
    if match:
        manhwa_key = match.group(1)
        chapter = int(match.group(2))
        part = int(match.group(3))
        return manhwa_key, chapter, part
    return None, None, None


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
    """Schedules video uploads by randomly selecting a manhwa and then uploading a single chapter per batch."""
    while True:
        logging.info("Checking Google Drive for new videos...")
        service = authenticate_drive()
        downloaded_videos = download_videos(service)

        logging.info("Checking for available videos...")
        videos_by_chapter = get_videos_by_chapter(VIDEO_DIR)
        if videos_by_chapter:
            sorted_manhwa = list(set(manhwa for manhwa, _ in videos_by_chapter.keys()))
            random.shuffle(sorted_manhwa)  # Randomize the manhwa selection order

            manhwa_key = random.choice(sorted_manhwa)  # Select one random manhwa
            sorted_chapters = sorted([ch for m, ch in videos_by_chapter.keys() if m == manhwa_key])

            if sorted_chapters:
                chapter = sorted_chapters[0]  # Upload only one chapter per batch
                logging.info(f"Uploading {manhwa_key} - Chapter {chapter}...")
                videos = [v[1] for v in videos_by_chapter[(manhwa_key, chapter)]]

                for video_path in videos:
                    try:
                        upload_video(os.path.basename(video_path), video_path)
                        delete_drive_video(service, downloaded_videos[os.path.basename(video_path)][0])
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Upload failed: {e}")

        else:
            logging.info("No new videos found.")
        logging.info(f"Waiting {INTERVAL} seconds before next check...")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    schedule_uploads()
