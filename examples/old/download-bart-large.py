from huggingface_hub import snapshot_download
model_id = "facebook/bart-large"  # Or your desired BART model
snapshot_download(repo_id=model_id, local_dir="bart-hf")
