from src.yolo.loader import YoloModelLoader
from src.yolo.models import DEFAULT_MODEL_KEY, YOLO_MODELS, get_all_label_names
from src.yolo.model_registry import build_name_to_model_map, build_yolo_model_settings, list_target_names
from src.yolo.openvino_detector import OpenVinoYolo8Detect
