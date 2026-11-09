"""Unit tests for free, license-filtered Commons visual sourcing."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_assets


def main():
    payload = {"query": {"pages": {
        "1": {"title": "File:Solar panels.jpg", "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/solar.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Solar_panels.jpg",
            "extmetadata": {
                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
                "Artist": {"value": "Example Photographer"},
                "Credit": {"value": "Example credit"},
            },
        }]},
        "2": {"title": "File:Unknown rights.jpg", "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/unknown.jpg",
            "extmetadata": {"LicenseShortName": {"value": "All rights reserved"}},
        }]},
        "3": {"title": "File:Old windmill.jpg", "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/windmill.jpg",
            "extmetadata": {"LicenseShortName": {"value": "Public domain"}},
        }]},
        "4": {"title": "File:Noncommercial.jpg", "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/noncommercial.jpg",
            "extmetadata": {"LicenseShortName": {"value": "CC BY-NC 4.0"}},
        }]},
        "5": {"title": "File:No derivatives.jpg", "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/no-derivatives.jpg",
            "extmetadata": {"LicenseShortName": {"value": "CC BY-ND 4.0"}},
        }]},
    }}}
    with patch.object(video_assets, "_request_json", return_value=payload):
        assets = video_assets.search_commons_images("solenergi", limit=5)
    assert len(assets) == 2, assets
    assert assets[0]["license"] == "CC BY-SA 4.0"
    assert assets[0]["artist"] == "Example Photographer"
    assert assets[1]["license"] == "Public domain"
    with patch.object(video_assets, "_request_json", side_effect=RuntimeError("offline")):
        assert video_assets.search_commons_images("solenergi") == []
    print("PASS Commons license filtering, attribution extraction and offline fallback.")


if __name__ == "__main__":
    main()
