import asyncio
import base64
import json
import os
from typing import Annotated

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
tidal_token = os.getenv("TIDAL_TOKEN")


async def auth():
    cids = client_id
    csec = client_secret

    url = "https://auth.tidal.com/v1/oauth2/token"

    payload = {
        "grant_type": "client_credentials",
        "client_id": cids,
        "client_secret": csec,
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url=url, data=payload)

        access_token = res.json()["access_token"]
        expires_in = res.json()["expires_in"]
        token_type = res.json()["token_type"]
        out_res = {
            "access_token": access_token,
            "expires_in": expires_in,
            "token_type": token_type,
        }

    return out_res


async def track():
    auths = await auth()
    access_token = auths.get("access_token")
    return access_token


@app.api_route("/", methods=["GET"])
async def index():
    return {"HIFI-API": "v1", "REPO": "https://github.com/sachinsenal0x64/Hifi-Tui"}


@app.api_route("/track/", methods=["GET"])
async def get_track(
    id: int,
    quality: str,
    country: Annotated[str | None, Query(max_length=3)] = None,
):
    token = await track()
    track_url = f"https://api.tidal.com/v1/tracks/{id}/playbackinfopostpaywall/v4?audioquality={quality}&playbackmode=STREAM&assetpresentation=FULL"

    info_url = f"https://api.tidal.com/v1/tracks/{id}/?countryCode=US"

    payload = {
        "authorization": f"Bearer {tidal_token}",
    }

    print(token)
    async with httpx.AsyncClient() as client:
        track_data = await client.get(url=track_url, headers=payload)
        info_data = await client.get(url=info_url, headers=payload)
    try:
        final_data = track_data.json()["manifest"]
        decode_manifest = base64.b64decode(final_data)
        con_json = json.loads(decode_manifest)
        audio_url = con_json.get("urls")[0]
        fetch_info = info_data.json()
        return {
            "Song Info": fetch_info,
            "Track Info": track_data.json(),
            "OriginalTrackUrl": audio_url,
        }
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Quality not found. check API docs = https://github.com/sachinsenal0x64/Hifi-Tui?tab=readme-ov-file#-api-documentation",
        )


@app.api_route("/search/", methods=["GET"])
async def search_track(q: str | None):
    search_url = f"https://api.tidal.com/v1/search/tracks?countryCode=US&query={q}"
    header = {"authorization": f"Bearer {tidal_token}"}
    async with httpx.AsyncClient() as clinet:
        search_data = await clinet.get(url=search_url, headers=header)

        return search_data.json()


@app.api_route("/cover/", methods=["GET"])
async def search_cover(id: int | None = None, q: str | None = None):
    if id:
        search_url = f"https://api.tidal.com/v1/tracks/{id}/?countryCode=US"
        header = {"authorization": f"Bearer {tidal_token}"}
        async with httpx.AsyncClient() as clinet:
            cover_data = await clinet.get(url=search_url, headers=header)
            tracks = cover_data.json()["album"]

            album_ids = []  # list to store album ids

            album_track_id = tracks["id"]
            print(album_track_id)
            album_cover = tracks["cover"].replace("-", "/")
            album_name = tracks["title"]
            album_ids.append(album_cover)
            album_ids.append(album_name)
            album_ids.append(album_track_id)

            json_data = [
                {
                    "id": album_ids[i + 2],
                    "name": album_ids[i + 1],
                    "1280": f"https://resources.tidal.com/images/{album_ids[i]}/1280x1280.jpg",
                    "640": f"https://resources.tidal.com/images/{album_ids[i]}/640x640.jpg",
                    "80": f"https://resources.tidal.com/images/{album_ids[i]}/80x80.jpg",
                }
                for i in range(0, len(album_ids), 3)
            ]

            # Create a list of dictionaries with "cover" and "name" keys
            return json_data

    else:
        search_url = f"https://api.tidal.com/v1/search/tracks?countryCode=US&query={q}"
        header = {"authorization": f"Bearer {tidal_token}"}
        async with httpx.AsyncClient() as clinet:
            cover_data = await clinet.get(url=search_url, headers=header)
            tracks = cover_data.json()["items"][:10]

            album_ids = []  # list to store album ids

            for track in tracks:
                album_track_id = track["id"]
                print(album_track_id)
                album_cover = track["album"]["cover"].replace("-", "/")
                album_name = track["title"]
                album_ids.append(album_cover)
                album_ids.append(album_name)
                album_ids.append(album_track_id)
            json_data = [
                {
                    "id": album_ids[i + 2],
                    "name": album_ids[i + 1],
                    "1280": f"https://resources.tidal.com/images/{album_ids[i]}/1280x1280.jpg",
                    "640": f"https://resources.tidal.com/images/{album_ids[i]}/640x640.jpg",
                    "80": f"https://resources.tidal.com/images/{album_ids[i]}/80x80.jpg",
                }
                for i in range(0, len(album_ids), 3)
            ]

            # Create a list of dictionaries with "cover" and "name" keys
            return json_data


async def main():
    config = uvicorn.Config("main:app", port=5000)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
