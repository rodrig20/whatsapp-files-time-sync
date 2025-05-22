# WhatsApp Media Date Fixer

A Python script to correct the creation dates of WhatsApp media files (images and videos), extracting real timestamps from chat exports and updating the metadata accordingly.

## Description

This tool helps fix the creation dates of WhatsApp media files that might have incorrect timestamps. It works by:

1. Extracting WhatsApp chat data using wtsexporter
2. Processing both images and videos
3. Updating file timestamps and EXIF data based on the actual message timestamps
4. Handling both files found in chats and standalone media files

## Prerequisites

Before using this tool, make sure you have:
1. Python 3.x (tested on 3.13)
2. Enabled end-to-end backup encryption in WhatsApp
3. Saved your 64-digit encryption key in a safe place (you'll need it to run the tool)
4. ADB (Android Debug Bridge) installed and configured


## Installation

1. Make sure you have ADB installed and configured
2. Install required Python packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Connect your Android device via USB and enable USB debugging
2. Run the script with your WhatsApp key:
```bash
python main.py YOUR_64_DIGIT_KEY
```
*Example:*
```bash
python main.py 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

The script will:
1. Pull the WhatsApp database from your device
2. Export chat data using [wtsexporter](https://github.com/KnugiHK/WhatsApp-Chat-Exporter)
3. Process all images and videos, updating their timestamps
4. Push the updated files back to your device


## Why Use This Tool?

This tool is particularly useful when:
- Syncing WhatsApp media with Google Photos or similar cloud services
- Organizing your media library chronologically
- Ensure your media files have correct creation dates for backup purposes
- Fixing media files that have incorrect timestamps after WhatsApp transfers or backups

## Important Notes

- **IMPORTANT**: You must have end-to-end backup encryption enabled in WhatsApp and have saved your encryption key before using this tool
- Make sure you have enough storage space on your device
- Keep your device connected until the process is complete
- You can disable end-to-end backup encryption after the script completes