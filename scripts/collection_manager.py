# collection_manager.py
import json


class CollectionManager:
    def __init__(self, file_name="dewdrop.txt"):
        self.file_name = file_name
        self.collection = self.load_dict_from_file()

    def load_dict_from_file(self):
        try:
            with open(self.file_name, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def save_dict_to_file(self):
        with open(self.file_name, "w") as file:
            json.dump(self.collection, file, indent=4)

    def add_item(self, item):
        if item not in self.collection:
            self.collection[item] = 1
        else:
            self.collection[item] += 1
        self.save_dict_to_file()

    def remove_item(self, item):
        self.collection.pop(item, None)
        self.save_dict_to_file()

    def find_item(self, item):
        return item in self.collection.keys()

    def remove_all(self, item):
        self.collection.pop(item, None)
        self.save_dict_to_file()

    def count_items(self, item=None):
        return len(self.collection) if item is None else self.collection.get(item, 0)
