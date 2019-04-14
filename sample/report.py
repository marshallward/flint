from flint.project import Project

proj = Project()
proj.parse('mom6')

for src in proj.files:
    ws_lines = src.report.errors['C0102']
    if ws_lines:
        print(
            '{fname}: {lineno}'.format(
                fname=src.path,
                lineno=', '.join(str(n) for n in ws_lines),
            )
        )
