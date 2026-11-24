import json
import unittest
from unittest.mock import patch
import nova_studio_worker as worker
from nova_studio_worker import make_workflow, scene_prompt, plan_scenes_local


class NovaStudioWorkerTests(unittest.TestCase):
    def test_comfyui_graph_is_connected(self):
        graph = make_workflow("A funny blue character", 12345, 512, 768)
        self.assertEqual(graph["7"]["class_type"], "SaveImage")
        self.assertEqual(graph["7"]["inputs"]["images"], ["6", 0])
        self.assertEqual(graph["5"]["inputs"]["positive"], ["2", 0])
        self.assertEqual(graph["5"]["inputs"]["negative"], ["3", 0])
        self.assertEqual(graph["4"]["inputs"]["width"], 512)
        self.assertEqual(graph["4"]["inputs"]["height"], 768)

    def test_scene_prompt_uses_nova_visual_prompt(self):
        prompt = scene_prompt("Blå och Gul", 0, 4, {
            "visual_prompt": "Two characters discover a glowing door in a quiet house."
        })
        self.assertIn("glowing door", prompt)
        self.assertIn("small rounded blue character", prompt)
        self.assertIn("bright yellow character", prompt)

    def test_scene_prompt_has_fallback(self):
        prompt = scene_prompt("A story about a lost robot", 2, 4)
        self.assertIn("Story subject: A story about a lost robot", prompt)
        self.assertIn("turning point", prompt)

    @patch("nova_studio_worker.http_json")
    def test_local_ollama_planner_parses_four_scenes(self, mock_http):
        scenes = [
            {"visual_prompt": "A detailed cinematic opening shot in a small house.", "voiceover": "Det börjar hemma."},
            {"visual_prompt": "A curious character discovers a mysterious glowing door.", "voiceover": "Något märkligt väntar."},
            {"visual_prompt": "A playful surprise changes the entire situation.", "voiceover": "Allt vänds upp och ner."},
            {"visual_prompt": "A warm funny ending with the characters smiling.", "voiceover": "Det blev ett äventyr."},
        ]
        mock_http.return_value = {"response": json.dumps({"scenes": scenes})}
        previous = worker.OLLAMA_MODEL
        worker.OLLAMA_MODEL = "qwen2.5:3b"
        try:
            result = plan_scenes_local("Blå och Gul hittar en hemlig dörr")
        finally:
            worker.OLLAMA_MODEL = previous
        self.assertEqual(len(result), 4)
        self.assertIn("11434", mock_http.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
