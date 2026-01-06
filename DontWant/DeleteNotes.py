import os


def find_comments(file_path):
    comments = []

    with open(file_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                comments.append((lineno, line.rstrip()))

    return comments


def clean_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        if line.strip() == "":
            continue
        new_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def collect_py_files():
    files = []

    for file in os.listdir("."):
        if file.endswith(".py") and os.path.isfile(file):
            files.append(os.path.join(".", file))

    component_dir = os.path.join(".", "component")
    if os.path.isdir(component_dir):
        for root, _, filenames in os.walk(component_dir):
            for file in filenames:
                if file.endswith(".py"):
                    files.append(os.path.join(root, file))

    return files


def process():
    files_with_comments = {}

    for file_path in collect_py_files():
        comments = find_comments(file_path)
        if comments:
            files_with_comments[file_path] = comments

    if not files_with_comments:
        print("לא נמצאו קבצים עם הערות")
        return

    print("נמצאו ההערות הבאות\n")

    for file, comments in files_with_comments.items():
        print(file)
        for lineno, text in comments:
            print(f"שורה {lineno}: {text}")
        print()

    answer = input("להמשיך ולמחוק הערות ושורות ריקות y n: ").strip().lower()

    if answer != "y":
        print("בוטל ללא שינוי")
        return

    print("\nמתחיל ניקוי\n")

    for f in files_with_comments:
        clean_file(f)
        print(f"נוקה: {f}")


if __name__ == "__main__":
    process()
