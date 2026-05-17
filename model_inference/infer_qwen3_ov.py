import torch
from optimum.intel.openvino import OVModelForVisualQuestionAnswering
from transformers import AutoProcessor
from qwen_vl_utils import process_vision_info
import time

def run_inference():
    model_dir = "Qwen3-VL-2B-Instruct-OV-INT4"
    device = "GPU" # Có thể đổi thành "CPU" nếu muốn test

    print(f"--- Đang tải model từ {model_dir} lên {device} ---")
    # Tải model OpenVINO đã convert
    model = OVModelForVisualQuestionAnswering.from_pretrained(
        model_dir, 
        device=device,
        trust_remote_code=True
    )
    
    processor = AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)

    # Chuẩn bị input (Ví dụ: Hỏi về một bức ảnh)
    # Bạn có thể thay đổi URL hoặc đường dẫn ảnh cục bộ
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/ai2d-demo.png"},
                {"type": "text", "text": "What is described in this image?"},
            ],
        }
    ]

    # Preprocess
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )

    print("--- Đang thực hiện inference ---")
    start_time = time.time()
    
    # Generate
    generated_ids = model.generate(**inputs, max_new_tokens=128)
    
    end_time = time.time()

    # Decode kết quả
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )

    print("\n--- Kết quả từ Qwen3-VL (OpenVINO) ---")
    print(output_text[0])
    print(f"\nThời gian inference: {end_time - start_time:.2f} giây")

if __name__ == "__main__":
    try:
        run_inference()
    except Exception as e:
        print(f"Lỗi khi chạy inference: {e}")
        print("Mẹo: Hãy đảm bảo bạn đã chạy script convert_qwen3_ov.py trước.")
