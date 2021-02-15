from flint.project import Project


def report_whitespace(project_dirs):
    proj = Project()
    proj.parse(*project_dirs)

    for src in proj.files:
        ws_lines = src.report.errors['C0102']
        if ws_lines:
            print(
                '{fname}: {lineno}'.format(
                    fname=src.path,
                    lineno=', '.join(str(n) for n in ws_lines),
                )
            )
