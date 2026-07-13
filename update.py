"""Fetch fresh Keshet tokens and build israel.m3u with all Israeli channels."""
import requests, json, subprocess

TOKEN_URL = "https://mass.mako.co.il/ClicksStatistics/entitlementsServicesV2.jsp"
CDN = "https://mako-streaming.akamaized.net"

# user request 2026-07-12: no logo anywhere upstream -- pulled from each channel's own
# site/app-store listing, downloaded and self-hosted here so they can't break elsewhere
_LOGOS = "https://cdn.jsdelivr.net/gh/Samhouston010/israel-tv@main/logos"

# YouTube live channels -- HLS manifest URL expires after a few hours, so it's
# re-resolved via yt-dlp on every run (same 10-min cron as the Keshet tokens).
# ponytail: TBN Israel removed by user request 2026-07-12 -- stopped working (the
# hardcoded video_id was one specific broadcast; once it ends there's no fallback
# to auto-discover a new live video id for the channel).
YOUTUBE_CHANNELS = []

KESHET_CHANNELS = {
    "Keshet 12": "/direct/hls/live/2033791/k12/index.m3u8?as=1",
    "Keshet 12 DVR": "/direct/hls/live/2033791/k12dvr/index.m3u8?b-in-range=800-2700",
    "N12 News": "/n12/hls/live/2103938/k12/index.m3u8?b-in-range=0-1100",
    "Keshet 12 CC": "/direct/hls/live/2035325/k12cc/index.m3u8?as=1",
    "Channel 24": "/direct/hls/live/2035340/ch24live/index.m3u8?as=1",
    "Eretz Nehederet": "/free/hls/live/2111419/erets/index.m3u8?b-in-range=0-1800",
}

DIRECT_CHANNELS = [
    ("Kan 11", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/kan11.default.svg",
     "https://kancdn.medonecdn.net/livehls/oil/kancdn-live/live/kan11/live.livx/playlist.m3u8"),
    ("Kan 11 HD", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/kan11.default.svg",
     "https://r.il.cdn-redge.media/livehls/oil/kancdn-live/live/kan11/live.livx/playlist.m3u8?dvr=21600000"),
    ("Kan Educational 23", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/kan11.default.svg",
     "https://r.il.cdn-redge.media/livehls/oil/kancdn-live/live/kan_edu/live.livx/playlist.m3u8?dvr=21600000"),
    ("Kan Kids", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/kan11.default.svg",
     "https://kankids.media.kan.org.il/hls/live/2024820/2024820/playlist.m3u8"),
    ("Makan 33", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/kan11.default.svg",
     "https://r.il.cdn-redge.media/livehls/oil/kancdn-live/live/makan/live.livx/playlist.m3u8?dvr=21600000"),
    ("Reshet 13", f"{_LOGOS}/reshet13.png",
     "https://d2xg1g9o5vns8m.cloudfront.net/out/v1/0855d703f7d5436fae6a9c7ce8ca5075/index.m3u8"),
    ("13 Comedy", f"{_LOGOS}/reshet13.png",
     "https://d15ds134q59udk.cloudfront.net/out/v1/fbba879221d045598540ee783b140fe2/index.m3u8"),
    ("13 Reality", f"{_LOGOS}/reshet13.png",
     "https://d2dffl3588mvfk.cloudfront.net/out/v1/d8e15050ca4148aab0ee387a5e2eb46b/index.m3u8"),
    ("13 Vacation", f"{_LOGOS}/reshet13.png",
     "https://d1yd8hohnldm33.cloudfront.net/out/v1/19dee23c2cc24f689bd4e1288661ee0c/index.m3u8"),
    ("Now 14", f"{_LOGOS}/channel14.png",
     "https://r.il.cdn-redge.media/livehls/oil/ch14/live/ch14/live.livx/playlist.m3u8?dvr=21600000"),
    ("Channel 10 Economy", f"{_LOGOS}/channel10economy.png",
     "https://r.il.cdn-redge.media/livehls/oil/calcala-live/live/channel10/live.livx/playlist.m3u8?dvr=21600000"),
    ("Channel 9 Russian", f"{_LOGOS}/channel9.png",
     "https://contact.gostreaming.tv/Con-11/index.m3u8"),
    ("Knesset 99", f"{_LOGOS}/knesset99.svg",
     "https://kneset.gostreaming.tv/p2-kneset/_definst_/myStream/index.m3u8"),
    ("i24 News Hebrew", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/i24news.default.svg",
     "https://i24newshebrew-cdn.encoders.immergo.tv/master.m3u8"),
    ("i24 News English", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/i24news.default.svg",
     "https://i24newsenglish-cdn.encoders.immergo.tv/master.m3u8"),
    ("i24 News Arabic", "https://raw.githubusercontent.com/picons/picons/master/build-source/logos/i24news.default.svg",
     "https://i24newsarabic-cdn.encoders.immergo.tv/master.m3u8"),
    ("Sport 5", f"{_LOGOS}/sport5.png",
     "https://rgelive.akamaized.net/hls/live/2043095/live3/playlist.m3u8"),
    ("Ynet Live", f"{_LOGOS}/ynet.svg",
     "https://ynet-live-01.ynet-pic1.yit.co.il/ynet/live.m3u8"),
    ("100FM TV", f"{_LOGOS}/100fm.png", "https://cdn.cybercdn.live/Radios_100FM/Video/playlist.m3u8"),
    ("Hidabroot 97", f"{_LOGOS}/hidabroot97.png", "https://cdn.cybercdn.live/HidabrootIL/Live97/playlist.m3u8"),
]

def get_ticket(path):
    try:
        r = requests.post(TOKEN_URL, params={"et": "ngt", "lp": path, "rv": "AKAMAI"}, timeout=15)
        return r.json()["tickets"][0]["ticket"]
    except:
        return None

def get_youtube_live_url(video_id):
    try:
        r = subprocess.run(["yt-dlp", "-g", f"https://www.youtube.com/watch?v={video_id}"],
                            capture_output=True, text=True, timeout=30)
        return r.stdout.strip().splitlines()[0] if r.stdout.strip() else None
    except Exception:
        return None

def build():
    lines = ['#EXTM3U']

    # Keshet channels (need token)
    for name, path in KESHET_CHANNELS.items():
        ticket = get_ticket(path)
        if not ticket:
            print(f"SKIP {name} — no token")
            continue
        stream_path = path.split("?")[0]
        url = CDN + stream_path + "?" + ticket
        logo = f"{_LOGOS}/keshet12.png"
        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="Israel",{name}')
        lines.append(url)
        print(f"OK {name}")
        if name == "Keshet 12":
            for yt_name, yt_logo, video_id in YOUTUBE_CHANNELS:
                yt_url = get_youtube_live_url(video_id)
                if not yt_url:
                    print(f"SKIP {yt_name} — no stream url")
                    continue
                lines.append(f'#EXTINF:-1 tvg-name="{yt_name}" tvg-logo="{yt_logo}" group-title="Israel",{yt_name}')
                lines.append(yt_url)
                print(f"OK {yt_name}")

    # Direct channels
    for name, logo, url in DIRECT_CHANNELS:
        lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="Israel",{name}')
        lines.append(url)
        print(f"OK {name}")

    with open("israel.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nDone! {len([l for l in lines if l.startswith('#EXTINF')])} channels")

if __name__ == "__main__":
    build()
