import os
import gzip
import urllib.request
import xml.etree.ElementTree as ET

TARGET_SOURCES = [
    {
        "name": "beIN Sports & Entertainment",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_BEIN1.xml.gz",
        "keywords": ["bein", "alkass"]
    },
    {
        "name": "Arab & Gulf Channels (AE1)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_AE1.xml.gz",
        "keywords": ["jazeera", "sky", "arabiya", "cnbc", "trt", "mbc", "rotana", "dubai", "ad sports", "sharjah", "osn"]
    },
    {
        "name": "Saudi & Asharq (SA2)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_SA2.xml.gz",
        "keywords": ["asharq", "mbc", "aflam", "action"]
    },
    {
        "name": "HBO & Cinemax (US2)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
        "keywords": ["hbo", "cinemax"]
    },
    {
        "name": "Sky UK (UK1)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
        "keywords": ["sky.news", "sky.main", "sky.premier", "sky.cinema", "sky.greats"]
    },
    {
        "name": "Sky Italia (IT1)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz",
        "keywords": ["sky.uno", "sky.sport", "sky.cinema", "sky.atlantic"]
    },
    {
        "name": "Sky Deutschland (DE1)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
        "keywords": ["sky.sport", "sky.cinema", "bundesliga"]
    },
    {
        "name": "France & Canal+ (FR1)",
        "url": "https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
        "keywords": ["france.24", "canal", "rmc"]
    }
]

out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "epg")
os.makedirs(out_dir, exist_ok=True)
gz_file = os.path.join(out_dir, "streambox-epg.xml.gz")

def run():
    with gzip.open(gz_file, "wb") as out_gz:
        out_gz.write(b"<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<tv generator-info-name=\"StreamBox EPG Engine\">\n")
        
        target_channel_ids = set()
        channels_added = 0
        programmes_added = 0

        for src in TARGET_SOURCES:
            print(f"--> Processing {src['name']}...")
            try:
                req = urllib.request.Request(src["url"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    with gzip.GzipFile(fileobj=resp) as in_gz:
                        context = ET.iterparse(in_gz, events=("end",))
                        for event, elem in context:
                            if elem.tag == "channel":
                                cid = elem.attrib.get("id", "")
                                dname = elem.find("display-name")
                                txt = dname.text if dname is not None and dname.text else cid
                                comb = (cid + " " + txt).lower()
                                if any(kw in comb for kw in src["keywords"]):
                                    target_channel_ids.add(cid)
                                    out_gz.write(b"  " + ET.tostring(elem, encoding="utf-8") + b"\n")
                                    channels_added += 1
                                elem.clear()
                            elif elem.tag == "programme":
                                cid = elem.attrib.get("channel", "")
                                if cid in target_channel_ids:
                                    out_gz.write(b"  " + ET.tostring(elem, encoding="utf-8") + b"\n")
                                    programmes_added += 1
                                elem.clear()
                print(f"    Channels: {channels_added}, Programmes: {programmes_added}")
            except Exception as e:
                print(f"    Error {src['name']}: {e}")

        out_gz.write(b"</tv>\n")

    print(f"\nSUCCESS! File size: {os.path.getsize(gz_file)/1024:.1f} KB")
    print(f"Total Channels: {channels_added}, Total Programmes: {programmes_added}")

if __name__ == "__main__":
    run()
