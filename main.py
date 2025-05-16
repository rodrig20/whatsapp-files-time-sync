import subprocess
from info import Info
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhatsApp Date Fix")
    parser.add_argument("key", type=str, help="Your 64-digit key")

    args = parser.parse_args()
    print("Connect your device...")
    subprocess.run("adb wait-for-device".split(), check=True)
    # Transfer the WhatsApp database to the computer
    subprocess.run("adb pull /storage/emulated/0/Android/media/com.whatsapp/WhatsApp .".split(), check=True)

    subprocess.run(f"wtsexporter -a -k {args.key} -b ./WhatsApp/Databases/msgstore.db.crypt15 --json --per-chat --no-html".split(), check=True)

    print("\n\nStarting...")
    images = Info("image")
    images.update_all()
    del images

    videos = Info("video")
    videos.update_all()
    del videos

    Info.clear()
    print("The ADB process has finished. You may disconnect your device now")
