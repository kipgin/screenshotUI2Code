import huggingface_hub as hf_hub

model_id = "OpenVINO/Qwen2.5-VL-7B-Instruct-int4-ov"
model_path = "Qwen2.5-VL-7B-Instruct-int4-ov"

hf_hub.snapshot_download(model_id, local_dir=model_path)