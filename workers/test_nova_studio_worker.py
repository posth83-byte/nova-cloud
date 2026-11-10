import unittest

from nova_studio_worker import make_workflow, scene_prompt


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


if __name__ == "__main__":
    unittest.main()
