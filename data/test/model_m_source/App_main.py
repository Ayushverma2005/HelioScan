from collections import OrderedDict

import gradio as gr
import os
os.system('nvidia-smi')
os.system('ls /usr/local')
os.system('pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu113')
import torch
from torchvision import transforms
from torchvision.transforms import InterpolationMode
from STTNet import STTNet

def construct_sample(img, mean, std):
    img = transforms.ToTensor()(img)
    img = transforms.Resize(512, InterpolationMode.BICUBIC)(img)
    img = transforms.Normalize(mean=mean, std=std)(img)
    
    return img

def build_model(checkpoint):
    model_infos = {
        # vgg16_bn, resnet50, resnet18
        'backbone': 'resnet50',
        'pretrained': False,
        'out_keys': ['block4'],
        'in_channel': 3,
        'n_classes': 2,
        'top_k_s': 64,
        'top_k_c': 16,
        'encoder_pos': True,
        'decoder_pos': True,
        'model_pattern': ['X', 'A', 'S', 'C'],
    }
    model = STTNet(**model_infos)
    state_dict = torch.load(checkpoint, map_location='cpu')
    model_dict = state_dict['model_state_dict']
    try:
        model_dict = OrderedDict({k.replace('module.', ''): v for k, v in model_dict.items()})
        model.load_state_dict(model_dict)
    except Exception as e:
        model.load_state_dict(model_dict)
    return model


# Function for building extraction
def seg_buildings(Image, Checkpoint):
    if Checkpoint == 'WHU':
        mean = [0.4352682576428411, 0.44523221318154493, 0.41307610541534784]
        std = [0.026973196780331585, 0.026424642808887323, 0.02791246590291434]
        checkpoint = 'Pretrain/WHU_ckpt_latest.pt'
    elif Checkpoint == 'INRIA':
        mean = [0.40672500537632994, 0.42829032416229895, 0.39331840468605667]
        std = [0.029498464618176873, 0.027740088491668233, 0.028246722411879095]
        checkpoint = 'Pretrain/INRIA_ckpt_latest.pt'
    else:
        raise NotImplementedError
    sample = construct_sample(Image, mean, std)
    model = build_model(checkpoint)
    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    print('Use: ', device)

    model = model.to(device)
    model.eval()
    sample = sample.to(device)
    sample = sample.unsqueeze(0)

    with torch.no_grad():
        logits, att_branch_output = model(sample)
    pred_label = torch.argmax(logits, 1, keepdim=True)
    pred_label *= 255
    pred_label = pred_label[0].detach().cpu()
    # pred_label = transforms.Resize(32, InterpolationMode.NEAREST)(pred_label)
    pred = pred_label.numpy()[0]

    return pred

title = "BuildingExtraction"
description = "Gradio Demo for Building Extraction. Upload image from INRIA or WHU Dataset or click any one of the examples, " \
              "Then click \"Submit\" and wait for the segmentation result. " \
              "Paper: Building Extraction from Remote Sensing Images with Sparse Token Transformers"
article = "<p style='text-align: center'><a href='https://github.com/KyanChen/BuildingExtraction' target='_blank'>STT Github " \
          "Repo</a></p> "

examples = [
    ['Examples/2_970.png', 'WHU'],
    ['Examples/2_1139.png', 'WHU'],
    ['Examples/502.png', 'WHU'],
    ['Examples/austin24_460_3680.png', 'INRIA'],
    ['Examples/austin36_1380_1840.png', 'INRIA'],
    ['Examples/tyrol-w19_920_3220.png', 'INRIA'],
]

with gr.Row():
    image_input = gr.Image(type='pil', label='Input Img')
    image_output = gr.Image(image_mode='L', label='Segmentation Result', tool='select')
with gr.Column():
    checkpoint = gr.inputs.Radio(['WHU', 'INRIA'], label='Checkpoint')

io = gr.Interface(fn=seg_buildings,
                  inputs=[image_input,
                          checkpoint],
                  outputs=image_output,
                  title=title,
                  description=description,
                  article=article,
                  allow_flagging='auto',
                  examples=examples,
                  cache_examples=True
                  )
io.launch()
