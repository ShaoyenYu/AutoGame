from yaml import load, CLoader


def load_yaml(file):
    with open(file, encoding="utf-8") as f:
        return load(f, CLoader)
