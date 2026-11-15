# Optional offline Swedish voice

The default worker voice uses Microsoft Edge TTS over the internet. To remove that external speech dependency, install the open-source Piper runtime locally and use a Swedish ONNX voice.

1. In the worker virtual environment run: pip install piper-tts
2. Download the Swedish Alma medium voice model and its matching JSON config:
   - https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/alma/medium/sv_SE-alma-medium.onnx
   - https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/alma/medium/sv_SE-alma-medium.onnx.json
3. Set PIPER_MODEL to the full path of the .onnx file.
4. Restart the worker. When PIPER_MODEL is set, the worker uses Piper locally and does not call Edge TTS.

Voice model licence: CC BY 4.0. Attribute the model to Alma / yeagersthlm and include the model card when redistributing voice outputs or model files as required by that licence:
https://huggingface.co/rhasspy/piper-voices/blob/main/sv/sv_SE/alma/medium/MODEL_CARD

The Piper engine itself is GPL-3.0. It is an optional local runtime, not bundled into this repository. Review the applicable licence before redistributing a packaged worker.
