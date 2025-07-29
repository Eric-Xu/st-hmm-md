import os


def append_file_path(path: str) -> None:
    append_path(get_dir_name(path))


def append_path(path: str) -> None:
    if not path_exists(path):
        os.makedirs(path)


def get_dir_name(dir_path: str) -> str:
    if "/" in dir_path:
        dir_name = dir_path.rsplit("/", 1)[0]
    else:
        dir_name = os.getcwd()

    return dir_name


def path_exists(path: str) -> bool:
    exists = False
    if path is not None:
        if os.path.isfile(path):
            exists = True
        elif os.path.isdir(path):
            exists = True

    return exists
