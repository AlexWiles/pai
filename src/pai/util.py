import toml


def get_version_from_pyproject():
    data = toml.load("pyproject.toml")
    return data["tool"]["poetry"]["version"]
