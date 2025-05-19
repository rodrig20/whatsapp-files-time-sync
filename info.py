import json
import os
import re
import subprocess
from datetime import datetime

import ffmpeg
import piexif
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm


class Info:
    local_output_dir = "/tmp/whatsapp_temp_adb"

    @staticmethod
    def clear():
        # Clear local_output_dir
        try:
            os.rmdir(Info.local_output_dir)
        except OSError:
            pass

    def __init__(self, type) -> None:
        # Check if the type is valid
        if type == "image":
            self.type = "image/jpeg"
            self.__search_paths = [
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/",
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/Sent/",
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/Private/",
            ]
        elif type == "video":
            self.type = "video/mp4"
            self.__search_paths = [
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video/",
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video/Sent/",
                "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video/Private/",
            ]
        else:
            raise ValueError(f"Invalid type: {type}. Must be 'image' or 'video'.")

        self.__chat_info = {}
        self.__load_content_from_all_chats()

    # Add media of self.type from the given chat json to self.chat_info
    def __get_media_from_json_chat(self, file_path):
        # Load the json file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Get messages from the chat
        first_tag = next(iter(data))
        messages = data[first_tag]["messages"]

        # Get the messages that are media and of the specified type with the timestamp
        # and store them in the dictionary
        for msg_id in messages:
            msg = messages[msg_id]
            if msg["media"] is True and msg["mime"] == self.type:
                self.__chat_info[os.path.basename(msg["data"])] = msg["timestamp"]

    # Load all json files from the result folder and get the media from each chat
    def __load_content_from_all_chats(self):
        path = "./result"

        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            # Check if the file is a JSON file
            if os.path.isfile(file_path) and filename.endswith(".json"):
                self.__get_media_from_json_chat(file_path)

    # Check if the file is on the device
    def __find_file_on_device(self, name):
        for path in self.__search_paths:
            full_path = f"{path}{name}"
            result = subprocess.run(
                ["adb", "shell", "ls", full_path.replace(" ", "\\ ")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # Check status code
            if result.returncode == 0:
                return full_path
        return None

    # Change the EXIF data of the file
    def __change_exif(self, path, ts):
        if self.type == "video/mp4":
            # Get the new timestamp of the video
            dt_iso = datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")
            # Create move the file to a temporary file
            dir_name, base_name = os.path.split(path)
            name, ext = os.path.splitext(base_name)
            temp_name = f"{name}_tmp{ext}"
            temp_path = os.path.join(dir_name, temp_name)

            # Change the timestamp of the file
            try:
                (
                    ffmpeg.input(path)
                    .output(temp_path, metadata=f"creation_time={dt_iso}", c="copy")
                    .overwrite_output()
                    .run(quiet=True)
                )
                # Remove original video
                os.remove(path)
                # Rename the temporary file to the original name
                os.rename(temp_path, path)
            except Exception as e:
                # Remove the temporary file if it exists
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e

        elif self.type == "image/jpeg":
            # Get the new timestamp of the image
            dt_str = datetime.fromtimestamp(ts).strftime("%Y:%m:%d %H:%M:%S")

            # Try to load the EXIF data
            try:
                exif_dict = piexif.load(path)
            except Exception:
                exif_dict = {
                    "0th": {},
                    "Exif": {},
                    "GPS": {},
                    "1st": {},
                    "thumbnail": None,
                }

            # Check if the EXIF data is empty
            if "0th" not in exif_dict:
                exif_dict["0th"] = {}
            if "Exif" not in exif_dict:
                exif_dict["Exif"] = {}

            # Set the EXIF data
            exif_dict["0th"][piexif.ImageIFD.DateTime] = dt_str.encode("utf-8")
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_str.encode("utf-8")
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_str.encode("utf-8")
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, path)
        else:
            raise ValueError(
                f"Invalid type: {self.type}. Must be 'image/jpeg' or 'video/mp4'"
            )

    # Update the files found in chat
    def update_from_chat(self):
        os.makedirs(Info.local_output_dir, exist_ok=True)
        with logging_redirect_tqdm():
            for file_name, timestamp in tqdm(
                self.__chat_info.items(),
                desc=f"Processing {self.type.split('/')[0]}s",
                unit=f"{self.type.split('/')[0][:3]}",
                dynamic_ncols=True,
            ):
                # Check if the file name is on the device
                remote_path = self.__find_file_on_device(file_name)
                if not remote_path:
                    print(
                        f"\33[2K\r{self.type.split("/")[0].title()} '{file_name}' not found on device"
                    )
                    continue

                local_path = os.path.join(Info.local_output_dir, file_name)

                # Pull file
                subprocess.run(
                    ["adb", "pull", remote_path, local_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Change timestamp
                os.utime(local_path, (timestamp, timestamp))

                # Change EXIF
                try:
                    self.__change_exif(local_path, timestamp)
                except Exception as e:
                    print(f"\33[2K\rError changing EXIF: {e}")

                # Push new file back to the device
                try:
                    subprocess.run(
                        ["adb", "shell", "rm", remote_path.replace(" ", "\\ ")],
                        check=True,
                    )
                    subprocess.run(
                        ["adb", "push", local_path, remote_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except KeyboardInterrupt:
                    subprocess.run(
                        ["adb", "push", local_path, remote_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                subprocess.run(
                    [
                        "adb",
                        "shell",
                        "am",
                        "broadcast",
                        "-a",
                        "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                        f'-d file://{remote_path.replace(" ", "\\ ")}',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    # Get all files from WhatsApp storage that are not in the json
    def __get_files_from_wa_storage(self):
        all_filenames = []
        # Search for files in the WhatsApp storage
        for dir_path in self.__search_paths:
            result = subprocess.run(
                ["adb", "shell", f"ls '{dir_path}'"], capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"\33[2K\rError listing {dir_path}")
                continue
            filenames = result.stdout.strip().splitlines()
            # Save if the file is not in the json
            for fname in filenames:
                if fname not in self.__chat_info:
                    all_filenames.append((dir_path, fname))

        return all_filenames

    # Get the EXIF timestamp from the file
    def __get_exif_timestamp(self, path):
        try:
            exif_dict = piexif.load(path)
            raw = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
            if raw:
                dt_str = raw.decode()
                return int(datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").timestamp())
        except:
            pass
        return None

    # Update the files found in WhatsApp storage that are not in any chat
    def update_from_name(self):
        os.makedirs(Info.local_output_dir, exist_ok=True)
        all_filenames = self.__get_files_from_wa_storage()
        if self.type == "image/jpeg":
            regex = re.compile(r"IMG-(\d{8})-WA\d+\.jpg")
        elif self.type == "video/mp4":
            regex = re.compile(r"VID-(\d{8})-WA\d+\.mp4")

        with logging_redirect_tqdm():
            for dir_path, fname in tqdm(
                all_filenames,
                desc=f"Checking {self.type.split("/")[0]}s with no chat",
                dynamic_ncols=True,
            ):
                # Check if has the correct regex
                match = regex.match(fname)
                if not match:
                    continue

                # Get the date from the filename (YYYYMMDD)
                date_str = match.group(1)
                try:
                    dt = datetime.strptime(date_str, "%Y%m%d")
                    dt = dt.replace(hour=12, minute=0, second=0)
                    ts = int(dt.timestamp())
                except ValueError:
                    continue

                remote_path = f"{dir_path}{fname}"
                local_path = os.path.join(Info.local_output_dir, fname)
                # Pull file
                subprocess.run(
                    ["adb", "pull", remote_path, local_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Check if the file has the correct timestamp
                exif_ts = self.__get_exif_timestamp(local_path)
                if exif_ts and abs(exif_ts - ts) < 60:
                    continue

                # Change timestamp
                os.utime(local_path, (ts, ts))
                try:
                    self.__change_exif(local_path, ts)
                except Exception as e:
                    print(f"\33[2K\rError changing EXIF: {e}")

                # Push new file back to the device
                try:
                    subprocess.run(
                        ["adb", "shell", "rm", remote_path.replace(" ", "\\ ")],
                        check=True,
                    )
                    subprocess.run(
                        ["adb", "push", local_path, remote_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except KeyboardInterrupt:
                    subprocess.run(
                        ["adb", "push", local_path, remote_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                subprocess.run(
                    [
                        "adb",
                        "shell",
                        "am",
                        "broadcast",
                        "-a",
                        "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                        f'-d file://{remote_path.replace(" ", "\\ ")}',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    # Update all files
    def update_all(self):
        self.update_from_chat()
        self.update_from_name()

        print(f"\nAll {self.type.split("/")[0]} processed")
        # Clear
        Info.clear()
