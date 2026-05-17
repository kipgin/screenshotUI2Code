import os
import subprocess
import sys

def install_dependencies():
    print("--- Đang cài đặt các thư viện cần thiết ---")
    commands = [
        # "pip install --upgrade pip",
        "python -m pip install \"optimum-intel[openvino,nncf]>=1.21.0\"",
        # "pip install \"transformers>=4.45.0\"",
        "python -m pip install qwen-vl-utils"
    ]
    for cmd in commands:
        print(f"Running: {cmd}")
        subprocess.check_call(f"{sys.executable} -m {cmd}", shell=True)

def convert_model():
    from optimum.intel.openvino import OVModelForVisualQuestionAnswering
    from transformers import AutoProcessor
    import torch

    model_id = "Qwen/Qwen3-VL-2B-Instruct"
    save_dir = "Qwen3-VL-2B-Instruct-OV-INT4"

    print(f"--- Bắt đầu chuyển đổi model: {model_id} ---")
    
    # Export model sang OpenVINO với định dạng INT4 để tối ưu cho GPU Intel
    # Chú ý: Cần RAM hệ thống lớn (khoảng 16GB-32GB) để thực hiện export
    model = OVModelForVisualQuestionAnswering.from_pretrained(
        model_id,
        export=True,
        trust_remote_code=True,
        quantization_config={"bits": 4, "ratio": 1.0}, # INT4 Weight Compression
    )

    print(f"--- Đang lưu model vào: {save_dir} ---")
    model.save_pretrained(save_dir)

    print("--- Đang lưu processor ---")
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    processor.save_pretrained(save_dir)

    print("--- Chuyển đổi hoàn tất! ---")

if __name__ == "__main__":
    try:
        # Nếu chưa có optimum-intel thì uncomment dòng dưới để cài đặt
        # install_dependencies()
        convert_model()
    except Exception as e:
        print(f"Lỗi trong quá trình chuyển đổi: {e}")
