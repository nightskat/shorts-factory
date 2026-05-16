import sys

def remove_dead_line():
    with open('tests/test_web.py', 'r') as f:
        lines = f.readlines()

    with open('tests/test_web.py', 'w') as f:
        for i, line in enumerate(lines):
            if i == 121 and 'tmp_path / "test.db"' in line:
                continue
            f.write(line)

remove_dead_line()
