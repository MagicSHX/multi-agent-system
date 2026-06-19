import yaml
import json
import os
from pathlib import Path
from decimal import Decimal
import pandas as pd
from collections import OrderedDict
from datetime import datetime, timezone


def yaml_parser(filePath: str) -> dict:
    """
    Parses a YAML file and returns its content as a dictionary.
    The function opens the file located at `filePath` and uses the `yaml` library to parse it.

    Args:
        filePath (str): The path to the YAML file to be parsed.

    Returns:
        dict: The parsed YAML data.
    """
    with open(filePath) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config


def json_parser(filePath: str) -> dict:
    """
    Parses a JSON file and returns its content as a dictionary.
    The function opens the file located at `filePath` and uses the `json` library to parse it.

    Args:
        filePath (str): The path to the JSON file to be parsed.

    Returns:
        dict: The parsed JSON data.
    """
    with open(filePath) as f:
        value = json.load(f)
    return value


def json_exporter(d, filePath):
    """
    Exports a dictionary to a JSON file at the specified path with pretty formatting.
    This function writes the dictionary `d` to a file specified by `filePath`, formatting the
    JSON output with an indentation of 4 spaces.

    Args:
        d (dict): The dictionary to export.
        filePath (str): The path where the JSON file will be saved.
    """
    with open(filePath, "w") as fp:
        json.dump(d, fp, indent=4)


def convert_to_float(value):
    if value is None:
        return None
    elif value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def convert_to_int(value):
    if value is None:
        return None
    elif value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return value


def create_folder_if_not_exists(filePath):
    # Extract the directory path from the file path
    directory = os.path.dirname(filePath)

    # Create the directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)


# Custom JSON Encoder
class Kafka_Producer_Message_Encoder(json.JSONEncoder):
    """
    A custom JSON encoder for Kafka producer messages.
    This class extends the `json.JSONEncoder` class to handle encoding of Decimal and pd.Timestamp objects.

    Methods:
    default(obj): Encode the given object
    """

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # Serialize as string
        elif isinstance(obj, pd.Timestamp):
            return int(obj.timestamp())
        return super().default(obj)


class LimitedOrderedDict(OrderedDict):
    def __init__(self, maxSize=60, *args, **kwargs):
        self.maxSize = maxSize
        super().__init__(*args, **kwargs)

        # Initially sort the dictionary if it has items
        if self:
            self._reorder_by_key()

    def _reorder_by_key(self):
        """Reorder the OrderedDict so it's sorted by keys"""
        items = list(self.items())
        items.sort(key=lambda x: x[0])  # Sort by key

        self.clear()
        for k, v in items:
            super().__setitem__(k, v)

    def __setitem__(self, key, value):
        # If this is an existing key, simply update it
        if key in self:
            super().__setitem__(key, value)
            self._reorder_by_key()
            return

        # If we're at capacity and this is a new key
        if len(self) >= self.maxSize:
            # Find the smallest key
            minKey = min(self.keys())

            # If the new key is smaller than the smallest key, don't add it
            if key <= minKey:
                return

            # Remove the smallest key
            self.pop(minKey)

        # Add the new item
        super().__setitem__(key, value)

        # Reorder after adding
        self._reorder_by_key()
