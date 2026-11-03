# Original game media

- Cover, Salih portrait and succession illustration: original AI-generated artwork created for this project with OpenAI image generation, November 2026. No assets or voice recordings from Total War are used.
- Text and music bed: authored for this project. Succession film is an illustrated dramatic montage, not archival footage or a literal reconstruction of a particular in-game death.
- Russian narration: rendered locally with Piper and `ru_RU-denis-medium`. The model card identifies its source dataset as CC0. Model and engine are not shipped with the game; static generated audio is shipped. Piper's authoring engine is GPL-3.0.
- Voice model card: https://huggingface.co/rhasspy/piper-voices/blob/main/ru/ru_RU/denis/medium/MODEL_CARD
- Piper: https://github.com/OHF-Voice/piper1-gpl
- The adviser Salih is a fictional gameplay guide. He is not a historical officeholder or a member of the simulated court.

Rebuild voice/video with `scripts/build_media.py` and the separately downloaded voice model. No third-party generative service is contacted during play.
