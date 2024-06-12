import base64
from PIL import Image
from io import BytesIO
import numpy as np
import torch


def img_from_base64(base64_img: str) -> torch.Tensor:
    try:
        imgdata = base64.b64decode(base64_img)
        img = Image.open(BytesIO(imgdata))
        img = img.convert("RGB")
        img = np.array(img).astype(np.float32) / 255.0

        # if "A" in img.getbands():
        #     mask = np.array(img.getchannel("A")).astype(np.float32) / 255.0
        #     mask = 1.0 - torch.from_numpy(mask)
        # else:
        #     mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")

        return torch.from_numpy(img)[None,]
    except Exception as e:
        raise ValueError(f"Could not read base64 image-data.\n{str(e)}")