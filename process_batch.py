from checker import check_document
from extractor import extract_text_from_file


def process_files(file_list):
    reports = {}
    for file in file_list:
        content = extract_text_from_file(file)
        result = check_document(content)
        reports[file.name] = result
    return reports
