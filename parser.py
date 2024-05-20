
def obtain_function(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    find = False
    groups = [[]]
    for line in lines:
        if line.startswith('#'):
            continue
        if '@guppy' in line:
            if find:
                groups.append([])
            else:
                find = True
        else:
            if find:
                groups[-1].append(line)

    return groups


def clean_empty_line_and_comment(lines):
    res = []
    for line in lines:
        for char in line:
            if not char.isspace():
                if not line.replace(" ", "").startswith('#'):
                    res.append(line)
                break

    return res


