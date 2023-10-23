import json
import os
import shutil
import time
import urllib.request

from colorthief import ColorThief
from dotenv import load_dotenv
from isodate import parse_duration
from pyyoutube import Api

from core.utils import escape_markdown

for folder in ["output/songs", "output/deleted", "output/regionblocked"]:
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
    print(len(data2["items"]))
    offset = 0
    for i, item2 in enumerate(data2["items"]):
        try:
            while True:
                item = data["items"][i + index + offset]
                del item["snippet"]["position"]
                del item["etag"]
                if item["snippet"]["resourceId"]["videoId"] == item2["id"]:
                    break
                offset += 1
                with open(
                    f"output/deleted/{item['snippet']['resourceId']['videoId']}.json",
                    "w",
                ) as file:
                    json.dump(item, file, indent=4)
        except IndexError:
            break
        item["statistics"] = item2["statistics"]
        for key, value in item2["contentDetails"].items():
            item["contentDetails"][key] = value
        if "likeCount" not in item["statistics"]:
            item["statistics"]["likeCount"] = "0"

        # if region blocked in Canada
        if "CA" in item["contentDetails"].get("regionRestriction", {}).get(
            "blocked", []
        ) or "CA" not in item["contentDetails"].get("regionRestriction", {}).get(
            "allowed", ["CA"]
        ):
            with open(
                f"output/regionblocked/{item['snippet']['resourceId']['videoId']}.json",
                "w",
            ) as file:
                json.dump(item, file, indent=4)
            continue

        with open(
            f"output/songs/{item['snippet']['resourceId']['videoId']}.json", "w"
        ) as file:
            json.dump(item, file, indent=4)
        duration = parse_duration(item2["contentDetails"]["duration"])
        minutes, seconds = divmod(int(duration.total_seconds()), 60)
        summary["items"].append(
            {
                "id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                "channel": item["snippet"]["videoOwnerChannelTitle"],
                "channelId": item["snippet"]["videoOwnerChannelId"],
                "duration": f"{minutes}:{seconds:02d}",
                "privacyStatus": item["status"]["privacyStatus"],
                "views": int(item["statistics"]["viewCount"]),
                "likes": int(item["statistics"]["likeCount"]),
                "publishedDate": item["contentDetails"]["videoPublishedAt"],
                "addedDate": item["snippet"]["publishedAt"],
            }
        )
        summary["duration"] += int(duration.total_seconds())
webhook_url = os.environ.get("WEBHOOK_URL")
if webhook_url:
    with open("output/summary.json", "r") as file:
        previous = json.load(file)
        previous_ids = []
        for song in previous["items"]:
            previous_ids.append(song["id"])
with open("output/summary.json", "w") as file:
    json.dump(summary, file)
if webhook_url:
    from discord_webhook import DiscordWebhook, DiscordEmbed

    def create_embed(song: dict):
        image_url = f"https://i.ytimg.com/vi/{song['id']}/maxresdefault.jpg"
        try:
            with urllib.request.urlopen(image_url) as url:
                thief = ColorThief(url)
                color_tuple = thief.get_color(quality=1)
                color = (color_tuple[0] << 16) + (color_tuple[1] << 8) + color_tuple[2]
        except:
            color = 7990062
        embed = DiscordEmbed(color=color)
        embed.set_description(
            f"[{escape_markdown(song['title'])}](https://youtube.com/watch?v={song['id']}&list=PLRct1-5In-8Ewg5Kq-0JP8wh3ZweOXH9A) "
            f"by [{escape_markdown(song['channel'])}](https://youtube.com/channel/{song['channelId']})"
        )
        embed.add_embed_field("Duration", song["duration"], True)
        embed.add_embed_field("Views", f"{song['views']:,}", True)
        embed.add_embed_field("Likes", f"{song['likes']:,}", True)
        embed.set_image(image_url)
        return embed

    for song in reversed(summary["items"]):
        if song["id"] in previous_ids:
            continue

        webhook = DiscordWebhook(webhook_url, rate_limit_retry=True)
        webhook.add_embed(create_embed(song))
        webhook.execute()
