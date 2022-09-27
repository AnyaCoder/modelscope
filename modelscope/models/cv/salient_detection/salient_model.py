import os.path as osp

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms

from modelscope.metainfo import Models
from modelscope.models.base.base_torch_model import TorchModel
from modelscope.models.builder import MODELS
from modelscope.utils.constant import ModelFile, Tasks
from .models import U2NET


@MODELS.register_module(
    Tasks.semantic_segmentation, module_name=Models.detection)
class SalientDetection(TorchModel):

    def __init__(self, model_dir: str, *args, **kwargs):
        """str -- model file root."""
        super().__init__(model_dir, *args, **kwargs)
        model_path = osp.join(model_dir, ModelFile.TORCH_MODEL_FILE)
        self.model = U2NET(3, 1)
        checkpoint = torch.load(model_path, map_location='cpu')
        self.transform_input = transforms.Compose([
            transforms.Resize((320, 320)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.model.load_state_dict(checkpoint)
        self.model.eval()

    def inference(self, data):
        """data is tensor 3 * H * W ---> return tensor H * W ."""
        data = data.unsqueeze(0)
        if next(self.model.parameters()).is_cuda:
            data = data.to(
                torch.device([next(self.model.parameters()).device][0]))

        with torch.no_grad():
            results = self.model(data)

        if next(self.model.parameters()).is_cuda:
            return results[0][0, 0, :, :].cpu()
        return results[0][0, 0, :, :]

    def preprocess(self, image):
        """image is numpy."""
        data = self.transform_input(Image.fromarray(image))
        return data.float()

    def postprocess(self, inputs):
        """resize ."""
        data = inputs['data']
        w = inputs['img_w']
        h = inputs['img_h']
        data_norm = (data - torch.min(data)) / (
            torch.max(data) - torch.min(data))
        data_norm_np = (data_norm.numpy() * 255).astype('uint8')
        data_norm_rst = cv2.resize(data_norm_np, (w, h))

        return data_norm_rst
