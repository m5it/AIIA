# GPU Support Notes

## Already GPU-Capable

| Feature | Details |
|---------|---------|
| **GenerateImage** | Uses `torch` + `diffusers` with `cuda` when available (`tool_GenerateImage.py`) |
| **Ollama inference** | All LLM inference runs on GPU via Ollama |
| **Terminal** | `nvidia-smi` is allowed — GPU state is inspectable |

## Possible GPU Features

| Feature | Effort | Description |
|---------|--------|-------------|
| **`GPUStatus` tool** | Low (~1hr) | Structured `nvidia-smi` wrapper — GPU count, model, memory use, temperature, processes |
| **`FreeGPU` tool** | Low (~1hr) | Stop conflicting Ollama models + clear HF pipeline cache to free VRAM |
| **Whisper transcription** | Medium (~3hr) | GPU-accelerated speech-to-text via `faster-whisper`. New tool entirely |
| **GPU worker for Orchestra** | Medium (~4hr) | Worker registers GPU capability; director dispatches GPU-heavy tasks |
| **RAG / embeddings** | Medium-High (~6hr) | `sentence-transformers` on GPU for semantic search across project files |
| **Image tool GPU accel** | Low-Medium (~2hr) | Optional OpenCV CUDA backend for ImageTransform/ReadImage |
| **CUDA-aware dep installer** | Low (~1hr) | Detect CUDA version, ensure correct torch wheel, validate post-install |

## Current GPU References

- `tool_GenerateImage.py` — `torch.cuda.is_available()`, `pipe.to("cuda")`, `torch.float16`
- `src/Commands.py` — frees GPU memory by stopping Ollama models on `!MODEL` switch
- `instruct/MediaAnalyst.py` — declares GPU deps (torch, diffusers, etc.) via `requirements()`
- `examples/` — old training scripts with `torch.device('cuda')`, `cudnn.enabled`
