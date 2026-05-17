# from huggingface_hub import snapshot_download

# # Tải model đã convert sẵn về thư mục 'qwen2.5_coder_3b_openvino_int4'
# model_dir = snapshot_download(repo_id="OpenVINO/Qwen2.5-Coder-3B-Instruct-int4-ov", 
#                               local_dir="qwen2.5_coder_3b_openvino_int4")
# print(f"Model downloaded to: {model_dir}")

from huggingface_hub import snapshot_download


model_dir = snapshot_download(repo_id="OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov", 
                              local_dir="qwen2.5_coder_7b_openvino_int4")
print(f"Model downloaded to: {model_dir}")