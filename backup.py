import json
import os

from dotenv import load_dotenv
from pyyoutube import Api

load_dotenv()
api = Api(api_key=os.getenv("API_KEY"))
data = api.get_playlist_items(
    playlist_id="PLRct1-5In-8Ewg5Kq-0JP8wh3ZweOXH9A",
    parts=["snippet", "contentDetails", "status"],
    count=None,
    return_json=True
)
for item in data["items"]:
    with open(f"songs/{item['snippet']['resourceId']['videoId']}.json", "w") as file:
        del item["snippet"]["position"]
        del item["etag"]
        json.dump(item, file, indent=4)
