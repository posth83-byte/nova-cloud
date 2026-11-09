"""Unit tests for source-linked Wikipedia explainer research."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_research


def main():
    search = json.dumps({"query": {"search": [{"title": "Solenergi"}]}})
    extract = "Solenergi är energi från solen. Den kan omvandlas till elektricitet med solceller. Solvärme kan också användas för att värma vatten. Solinstrålningen varierar med väder och årstid. Energilagring kan jämna ut skillnader mellan produktion och användning. Tekniken används i många delar av världen."
    article = json.dumps({"query": {"pages": {"123": {"extract": extract}}}})
    with patch.object(video_research, "_api", side_effect=[search, article]):
        result = video_research.research_wikipedia("solenergi")
    assert result and result["title"] == "Solenergi", result
    assert result["language"] == "sv"
    assert result["source_url"].startswith("https://sv.wikipedia.org/wiki/")
    beats = video_research.build_explainer_beats(result)
    assert len(beats) == 5, beats
    assert all(beat[1] for beat in beats)
    assert "solceller" in " ".join(beat[1] for beat in beats)
    with patch.object(video_research, "_api", side_effect=RuntimeError("offline")):
        assert video_research.research_wikipedia("okänt ämne") is None
    assert video_research.build_explainer_beats(None) == []
    print("PASS Wikipedia source retrieval, five-scene factual beat creation and offline failure handling.")


if __name__ == "__main__":
    main()
