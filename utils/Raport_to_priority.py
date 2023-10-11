from string import ascii_lowercase

from pyxlsb import open_workbook
from tqdm import tqdm


def get_priority(config):
    input_file = open_workbook(config["INPUT_FILE"])
    input_sheet = input_file.get_sheet(config["INPUT_FILE_SHEET"])

    Flag, counter = False, 1
    priority_list = []

    for i, row in tqdm(enumerate(input_sheet.rows(sparse=True))):
        string_list = [c.v for c in row]
        if string_list[2] == "Артикул":
            Flag = True
            continue
        if Flag and string_list[7] == "Опер.план (ЦПП)":
            if string_list[13] is not None:
                # если есть буквы в Артикуле ДСЕ
                if set(str(string_list[2]).lower()) & set(ascii_lowercase):
                    priority_item = string_list[2]
                    priority_list.append(priority_item)
                    continue
                else:
                    priority_item = (
                        str(
                            string_list[2]
                        ).split(".")[0].rjust(18, "0")
                    )  # приводим Артикул в 18-значный формат
                    priority_list.append(priority_item)
                    continue
    print(priority_list)
    return priority_list
