# -*- coding: utf-8 -*-
"""train.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/18jo6pIMC5Qj0Fc3CsswZgHusnwDRRfvy
"""

import torch
import argparse
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import torchvision.models as models
from torch import nn, optim
import numpy as np
from collections import OrderedDict
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Train a new network on a dataset.")
    parser.add_argument('data_dir', type=str, help='Directory of training data')
    parser.add_argument('--save_dir', type=str, default='./', help='Directory to save checkpoints')
    parser.add_argument('--arch', type=str, default='vgg16', help='Model architecture (e.g., vgg13, vgg16, resnet18, densenet121)')
    parser.add_argument('--learning_rate', type=float, default=0.001, help='Learning rate for training')
    parser.add_argument('--hidden_units', type=int, default=512, help='Number of hidden units in the classifier')
    parser.add_argument('--epochs', type=int, default=2, help='Number of epochs for training')
    parser.add_argument('--gpu', action='store_true', help='Use GPU for training if available')
    return parser.parse_args()

def main():
    args = parse_args()
    data_dir = args.data_dir
    train_dir = os.path.join(data_dir, 'train')
    valid_dir = os.path.join(data_dir, 'valid')

    # Data Transformations
    train_transform = transforms.Compose([
        transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Load datasets
    train_dataset = datasets.ImageFolder(root=train_dir, transform=train_transform)
    valid_dataset = datasets.ImageFolder(root=valid_dir, transform=val_transform)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    valid_loader = DataLoader(valid_dataset, batch_size=32, shuffle=False)

    # Load Model
    if args.arch == 'vgg13':
        model = models.vgg13(pretrained=True)
        num_input_features = model.classifier[0].in_features
    elif args.arch == 'resnet18':
        model = models.resnet18(pretrained=True)
        num_input_features = model.fc.in_features
    elif args.arch == 'densenet121':
        model = models.densenet121(pretrained=True)
        num_input_features = model.classifier.in_features
    else:
        raise ValueError(f"Unsupported architecture {args.arch}")

    # Freeze pretrained layers
    for param in model.parameters():
        param.requires_grad = False

    # Define new classifier
    num_classes = 102
    num_hidden = args.hidden_units
    classifier = nn.Sequential(OrderedDict([
        ('fc1', nn.Linear(num_input_features, num_hidden)),
        ('relu', nn.ReLU()),
        ('dropout', nn.Dropout(p=0.2)),
        ('fc2', nn.Linear(num_hidden, num_classes)),
        ('output', nn.LogSoftmax(dim=1))
    ]))

    # Replace classifier
    if args.arch in ['vgg13', 'densenet121']:
        model.classifier = classifier
        optimizer = optim.Adam(model.classifier.parameters(), lr=args.learning_rate)
    elif args.arch == 'resnet18':
        model.fc = classifier
        optimizer = optim.Adam(model.fc.parameters(), lr=args.learning_rate)

    # Device configuration
    device = torch.device("cuda" if args.gpu and torch.cuda.is_available() else "cpu")
    model.to(device)

    # Loss function
    criterion = nn.NLLLoss()

    epochs = args.epochs
    steps = 0
    print_every = 5

    for epoch in range(epochs):
        running_loss = 0
        model.train()

        for inputs, labels in train_loader:
            steps += 1
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            logps = model(inputs)
            loss = criterion(logps, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            if steps % print_every == 0:
                model.eval()
                test_loss = 0
                accuracy = 0

                with torch.no_grad():
                    for inputs, labels in valid_loader:
                        inputs, labels = inputs.to(device), labels.to(device)
                        logps = model(inputs)
                        test_loss += criterion(logps, labels).item()

                        ps = torch.exp(logps)
                        top_p, top_class = ps.topk(1, dim=1)
                        equals = top_class == labels.view(*top_class.shape)
                        accuracy += torch.mean(equals.type(torch.FloatTensor)).item()

                print(f"Epoch {epoch+1}/{epochs}.. "
                      f"Train loss: {running_loss/print_every:.3f}.. "
                      f"Test loss: {test_loss/len(valid_loader):.3f}.. "
                      f"Test accuracy: {accuracy/len(valid_loader):.3f}")

                running_loss = 0
                model.train()

        # Save checkpoint after each epoch
        if not os.path.exists(args.save_dir):
            os.makedirs(args.save_dir)

        checkpoint = {
            'epoch': epoch + 1,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'loss': loss.item(),
            'class_to_idx': train_dataset.class_to_idx,
            'arch': args.arch,
            'num_hidden': args.hidden_units,
        }

        checkpoint_path = os.path.join(args.save_dir, f"checkpoint_epoch_{epoch+1}.pth")
        torch.save(checkpoint, checkpoint_path)
        print(f"Checkpoint saved at {checkpoint_path}")

if __name__ == "__main__":
    main()