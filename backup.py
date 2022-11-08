import json
import os
import shutil
import time

from dotenv import load_dotenv
from isodate import parse_duration
from pyyoutube import Api

for folder in ["output/songs", "output/deleted"]:
    shutil.rmtree(folder, ignore_errors=True)
    os.mkdir(folder)

load_dotenv()
api = Api(api_key=os.getenv("API_KEY"))
data = api.get_playlist_items(
    playlist_id="PLRct1-5In-8Ewg5Kq-0JP8wh3ZweOXH9A",
    parts=["snippet", "contentDetails", "status"],
    count=None,
    return_json=True,
)
summary = {"items": [], "duration": 0, "lastUpdated": time.time()}
for index in range(0, len(data["items"]), 50):
    data2 = api.get_video_by_id(
        video_id=[
            video["snippet"]["resourceId"]["videoId"]
            for video in data["items"][index : index + 50]
        ],
        parts=["contentDetails", "statistics"],
        return_json=True,
    )
    for i, item2 in enumerate(data2["items"]):
        try:
            item = data["items"][i + index]
        except IndexError:
            break
        item["statistics"] = item2["statistics"]
        for key, value in item2["contentDetails"].items():
            item["contentDetails"][key] = value
        if "likeCount" not in item["statistics"]:
            item["statistics"]["likeCount"] = "0"
        del item["snippet"]["position"]
        del item["etag"]
        with open(
            f"output/songs/{item['snippet']['resourceId']['videoId']}.json", "w"
        ) as file:
            json.dump(item, file, indent=4)
        if "videoPublishedAt" not in item["contentDetails"]:
            with open(
                f"output/deleted/{item['snippet']['resourceId']['videoId']}.json", "w"
            ) as file:
                json.dump(item, file, indent=4)
            continue
        duration = parse_duration(item2["contentDetails"]["duration"])
        minutes, seconds = divmod(int(duration.total_seconds()), 60)
        summary["items"].append(
            {
                "id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                "channel": item["snippet"]["videoOwnerChannelTitle"],
                "channelId": item["snippet"]["videoOwnerChannelId"],
                "duration": f"{minutes:02d}:{seconds:02d}",
                "privacyStatus": item["status"]["privacyStatus"],
                "views": f"{int(item['statistics']['viewCount']):,}",
                "likes": f"{int(item['statistics']['likeCount']):,}",
                "publishedDate": item["contentDetails"]["videoPublishedAt"],
                "addedDate": item["snippet"]["publishedAt"],
            }
        )
        summary["duration"] += int(duration.total_seconds())
with open("output/summary.json", "w") as file:
    json.dump(summary, file)
