# -*- coding: utf-8 -*-
"""predict.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1IM1wajevHxZA19JBzvKWsouy3arwt1uk
"""

import torch
import torch.nn as nn
from torchvision import models
from collections import OrderedDict
from PIL import Image
import numpy as np
import json
import sys
# Function to load a trained model
def load_model(checkpoint_path):
    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
    arch = checkpoint['arch']
    num_classes = 102

    # Load the pre-trained model architecture
    if arch == 'vgg13':
        model = models.vgg13(pretrained=True)
        num_input_features = model.classifier[0].in_features
    elif arch == 'resnet18':
        model = models.resnet18(pretrained=True)
        num_input_features = model.fc.in_features
    elif arch == 'densenet121':
        model = models.densenet121(pretrained=True)
        num_input_features = model.classifier.in_features

    # Define the classifier
    num_hidden = checkpoint['num_hidden']
    classifier = nn.Sequential(OrderedDict([
        ('fc1', nn.Linear(num_input_features, num_hidden)),
        ('relu', nn.ReLU()),
        ('dropout1', nn.Dropout(p=0.2)),
        ('fc2', nn.Linear(num_hidden, num_classes)),
        ('output', nn.LogSoftmax(dim=1))
    ]))

    # Attach classifier to model
    if arch == 'vgg13':
        model.classifier = classifier
    elif arch == 'resnet18':
        model.fc = classifier
    elif arch == 'densenet121':
        model.classifier = classifier

    # Load model state
    model.load_state_dict(checkpoint['model_state_dict'])
    model.class_to_idx = checkpoint['class_to_idx']

    return model

# Function to process an image
def process_image(image_path):
    image = Image.open(image_path)

    # Resize and crop image
    width, height = image.size
    if width < height:
        image = image.resize((256, int(256 * height / width)))
    else:
        image = image.resize((int(256 * width / height), 256))

    # Center crop to 224x224
    left = (image.width - 224) / 2
    top = (image.height - 224) / 2
    right = left + 224
    bottom = top + 224
    image = image.crop((left, top, right, bottom))

    # ConvertIing image to numpy array and normalize
    np_image = np.array(image) / 255.0
    mean = [0.485, 0.456, 0.406]
    std = [0.229, 0.224, 0.225]
    np_image = (np_image - mean) / std

    # Transpose dimensions (H, W, C) → (C, H, W)
    np_image = np_image.transpose((2, 0, 1))

    return torch.tensor(np_image).unsqueeze(0).float()

# Function to make a prediction
def predict(image_path, model, category_names=None, top_k=1, gpu=True):
    device = torch.device("cuda" if torch.cuda.is_available() and gpu else "cpu")
    model = model.to(device)
    model.eval()

    # Process image and move it to device
    image_tensor = process_image(image_path).to(device)

    with torch.no_grad():
        output = model.forward(image_tensor)

    # Get top probabilities and class indices
    probs, indices = torch.topk(torch.exp(output), top_k)
    probs = probs.cpu().numpy().flatten()
    indices = indices.cpu().numpy().flatten()

    # Convert indices to class labels
    idx_to_class = {v: k for k, v in model.class_to_idx.items()}
    classes = [idx_to_class[idx] for idx in indices]

    # Convert class labels to real names
    if category_names:
        with open(category_names, 'r') as f:
            cat_to_name = json.load(f)
        class_names = [cat_to_name[cls] for cls in classes]
    else:
        class_names = classes

    return probs, class_names

# Load the trained model

checkpoint_path = sys.argv[2]  # Read checkpoint path from command line argument
model = load_model(checkpoint_path)


# Run prediction

image_path = sys.argv[1]  # Read image path from command line argument

category_names = "cat_to_name.json"
probs, classes = predict(image_path, model, category_names, top_k=3, gpu=True)

# Print results
for i in range(len(classes)):
    print(f"{classes[i]}: {probs[i]:.4f}")

print(f"Most likely class: {classes[0]} with probability {probs[0]:.4f}")