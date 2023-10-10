from pyxlsb import open_workbook
from datetime import date, time, datetime, timedelta
# from config_raport_to_plan import *
# from raport_listofdicts_to_plan import *
from string import ascii_lowercase

from tqdm import tqdm


def get_priority (config):

    input_file = open_workbook(config["INPUT_FILE"])
    input_sheet = input_file.get_sheet(config["INPUT_FILE_SHEET"])

    plan_list = []
    string_list = []
    Flag, counter = False, 1
    week_number = datetime.today().isocalendar()[1]  # получаем текущий номер недели
    current_day = date.today()  # получаем текущий день
    shift_time_start = time(7, 00, 00)  # время начала смены
    date_from_current_week = datetime.combine(
        current_day, shift_time_start
    )  # время date_from в новой таблице
    date_to_dict = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}
    date_to_current_week = date_from_current_week + timedelta(
        days=date_to_dict[date_from_current_week.weekday()]
    )  # зная какой сегодня день недели добавляем значение нужного количества дней из словаря
    priority_list = []

    # print(date_to_current_week)
    # print(date_to_dict)
    # print(date_from_current_week)
    # print(current_day)
    # print(week_number)

    # fact_string_list
    # fact_list = [[c.v for c in row] for row in tqdm(input_sheet.rows())]
    # print(*fact_list[29:50], sep = '\n')

    for i, row in tqdm(enumerate(input_sheet.rows(sparse=True))):
        # print(i)
        string_list = [c.v for c in row]
        if string_list[2] == "Артикул":
            current_week_plan_column = string_list.index(f"{week_number} План/Факт неделя")
            Flag = True
            continue
        if Flag and string_list[7] == "Опер.план (ЦПП)":
            # plan_dict_current_week = {}
            # fact_current_week = int(fact_list[i + 2][current_week_plan_column])
            # plan_dict_current_week["ORDER"] = str(counter) + " / " + string_list[3]
            # plan_dict_current_week["NAME"] = string_list[3]
            # plan_dict_current_week["#WEEK"] = week_number
            if string_list[13] is not None:
                if set(str(string_list[2]).lower()) & set(ascii_lowercase):  # если есть буквы в Артикуле ДСЕ
                    priority_item = string_list[2]
                    priority_list.append(priority_item)
                    continue
                else:
                    priority_item = (
                    str(string_list[2]).split(".")[0].rjust(18, "0")
                    )  # приводим Артикул в 18-значный формат
                    # print(plan_dict['CODE'])
                    priority_list.append(priority_item)
                    continue
            # plan_dict_current_week["#FACT"] = fact_current_week
            # plan_current_week = int(string_list[current_week_plan_column])
            # if plan_current_week - fact_current_week > 0:
            #     plan_dict_current_week["#PLAN"] = plan_current_week
            #     plan_dict_current_week["AMOUNT"] = plan_current_week - fact_current_week
            # plan_dict_current_week["DATE_FROM"] = str(date_from_current_week)
            # plan_dict_current_week["DATE_TO"] = str(date_to_current_week)
            # if string_list[13] is not None:
            #     plan_dict_current_week["#BLOCKING"] = "Y"
            #     plan_dict_current_week["ORDER"] = str(counter) + " / блок / " + string_list[3]
            # else:
            #     plan_dict_current_week["#BLOCKING"] = "N"
            # if i == 193:
            #     print(len(plan_dict_current_week))
            #     print(plan_dict_current_week)
            # if len(plan_dict_current_week) == 10:
            #     plan_list.append(plan_dict_current_week)
            #     print(f'{counter}')
            #     counter += 1
            # next_week_plan_column = 9
            # next_week_number = week_number + 1
            # delta_days = 0
            #
            # while (
            #     current_week_plan_column + next_week_plan_column <= len(string_list)
            #     and string_list[current_week_plan_column + next_week_plan_column] != None
            # ):  # проверяем если ли ещё столбец правее текущей недели откуда можно прочитать значение в план
            #     plan_dict_next_week = {}
            #     plan_dict_next_week["ORDER"] = str(counter) + " / " + string_list[3]
            #     plan_dict_next_week["#WEEK"] = next_week_number
            #     plan_dict_next_week["NAME"] = string_list[3]
            #     if set(str(string_list[2]).lower()) & set(
            #         ascii_lowercase
            #     ):  # если есть буквы в Артикуле ДСЕ
            #         plan_dict_next_week["CODE"] = string_list[2]
            #     else:
            #         plan_dict_next_week["CODE"] = (
            #             str(string_list[2]).split(".")[0].rjust(18, "0")
            #         )  # приводим Артикул в 18-значный формат
            #     if int(string_list[current_week_plan_column + next_week_plan_column]) > 0:
            #         plan_dict_next_week["#PLAN"] = int(
            #             string_list[current_week_plan_column + next_week_plan_column]
            #         )
            #         plan_dict_next_week["AMOUNT"] = int(
            #             string_list[current_week_plan_column + next_week_plan_column]
            #         )
            #         print(f'{counter}')
            #         counter += 1
            #     else:
            #         next_week_number += 1
            #         next_week_plan_column += 9
            #         continue
            #     plan_dict_next_week["#FACT"] = "N"
            #     plan_dict_next_week["DATE_FROM"] = str(
            #         date_to_current_week + timedelta(days=delta_days)
            #     )
            #     delta_days += 7
            #     plan_dict_next_week["DATE_TO"] = str(
            #         date_to_current_week + timedelta(days=delta_days)
            #     )
            #     if string_list[13] is not None:
            #         plan_dict_next_week["#BLOCKING"] = "Y"
            #         plan_dict_current_week["ORDER"] = str(counter) + " / блок / " + string_list[3]
            #     else:
            #         plan_dict_next_week["#BLOCKING"] = "N"
            #     if len(plan_dict_next_week) == 10:
            #         plan_list.append(plan_dict_next_week)
            #     next_week_number += 1
            #     next_week_plan_column += 9

    # print(len(priority_list))
    print(priority_list)
    return priority_list
    # plan_list.sort(key=lambda plan_list: plan_list["#BLOCKING"], reverse=True)
    #
    # output_file_plan = config["OUTPUT_FILE"]
    # print("Чтение исходной таблицы завершено, формирование плана заказов")
    # dict2xlsx(plan_list, output_file_plan)
    # print(f"Количество строчек в плане заказов - {counter-1}")