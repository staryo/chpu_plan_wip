import argparse
import csv
import math
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timedelta
from logging import basicConfig, DEBUG, INFO
from operator import itemgetter
from os import getcwd
from os.path import join

import yaml

from get_spec import return_specifications, get_entities
from plan191 import return_plan191
from utils.Raport_to_priority import get_priority
from utils.date_to_week import date_to_week
from utils.listofdicts_to_csv import dict2csv
from wip import return_wip

from datetime import date, datetime, timedelta


def main():
    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'config.yml'))

    parser.add_argument('-m', '--material', required=False, default=None)

    parser.add_argument('-d', '--debug', required=False, action='store_true',
                        default=False)

    args = parser.parse_args()

    if args.material == '':
        args.material = None

    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=args.debug and DEBUG or INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    b = datetime.now() + timedelta(days=8)
    print(b)

    if config['priority']:
        priority = get_priority(config['input'])
    else:
        priority = ['ф']

    with open(config['wipca'], 'r', encoding='utf-8') as input_file:
        wipca = list(csv.DictReader(
            input_file
        ))
    wipca.sort(
        key=lambda x: (x['#NOP'], float(x['OPERATION_PROGRESS'])),
        reverse=True
    )
    wip_ca_dict = defaultdict(lambda: defaultdict(float))

    for row in wipca:
        if 0 < float(row['OPERATION_PROGRESS']) < 100:
            done = round(
                float(row['AMOUNT']) * float(row['OPERATION_PROGRESS']) / 100
            )
            wip_ca_dict[row['#ROUTE_PHASE']][
                f"{row['OPERATION_ID']}|100.0"] += done
            wip_ca_dict[row['#ROUTE_PHASE']][
                f"{row['OPERATION_ID']}|0.0"] += float(row['AMOUNT']) - done
        else:
            wip_ca_dict[
                row['#ROUTE_PHASE']
            ][
                f"{row['OPERATION_ID']}|{row['OPERATION_PROGRESS']}"
            ] += float(row['AMOUNT'])

    plan = return_plan191(server, args.material)
    dict2csv(plan, 'plan191.csv')

    with open('plan191.csv') as f:
        plan = [{k: v for k, v in row.items()}
                for row in csv.DictReader(f, skipinitialspace=True)]

    specifications = return_specifications(config)
    entities = get_entities(config)

    wip = return_wip(server)
    dict2csv(
        [{'CODE': key, 'AMOUNT': value} for key, value in wip.items()],
        'wip_sap.csv'
    )
    with open('wip_sap.csv') as f:
        wip_list = [{k: v for k, v in row.items()}
                    for row in csv.DictReader(f, skipinitialspace=True)]
    wip = defaultdict(float)
    for row in wip_list:
        wip[row['CODE']] = float(row['AMOUNT'])

    new_plan = []
    new_wip = []
    for row in plan:
        entity = row['CODE']
        how_many = float(row['AMOUNT'])
        if entity not in specifications:
            continue
        for child in specifications[entity]:
            how_many = min(
                math.floor(wip[child] / specifications[entity][child]),
                how_many
            )

        if datetime.strptime(
                row['DATE_TO'],
                '%Y-%m-%d %H:%M'
        ) >= datetime.now() + timedelta(days=8):
            entity_priority = 3
        elif row['CODE'] in priority:
            entity_priority = 1
        else:
            entity_priority = 2

        if how_many > 0:
            ok_priority = 1
            order_name = (f"[{date_to_week(row['ORDER'])}]"
                          f"{entities[row['CODE']]}_OK")
            if how_many < float(row['AMOUNT']):
                ok_priority = 2
                order_name += '_D'
            date_to_with_shift = (
                    datetime.strptime(
                        row['DATE_TO'],
                        '%Y-%m-%d %H:%M'
                    ) - timedelta(days=21)
            ).strftime('%Y-%m-%d 07:00')

            new_plan.append({
                'ORDER': order_name,
                'CODE': row['CODE'],
                'AMOUNT': how_many,
                'DATE_FROM': (
                    max(
                        datetime.strptime(
                            row['DATE_TO'], '%Y-%m-%d %H:%M'
                        ) - timedelta(days=21),
                        datetime.now()
                    )
                ).strftime('%Y-%m-%d 07:00'),
                'DATE_TO': row['DATE_TO'],
                'PRIORITY': f"{entity_priority}_{date_to_with_shift}_"
                            f"{row['DATE_TO']}_{ok_priority}"
            })

            route_phase = None
            if '-' in entity:
                route_phase = f"{entity}_Z{entity[13]}01"
            else:
                for child in specifications[entity]:
                    if '-' in child:
                        route_phase = f"{entity}_Z{child[13]}01"
                        break

            if route_phase is None:
                print('Не найден маршрут для', entity)

            need_amount = how_many
            if route_phase in wip_ca_dict:
                print("Нашли", route_phase, ". Всего надо", how_many)
                for operation, amount in wip_ca_dict[route_phase].items():
                    amount_to_take = min(need_amount, amount)
                    if amount_to_take < 0:
                        print("Остаток меньше нуля",
                              operation,
                              amount,
                              need_amount)
                    operation_progress = float(operation.split('|')[1])
                    if amount_to_take > 0:
                        need_amount -= amount_to_take
                        print("Взяли", operation, amount_to_take)
                        print("Было на складе",
                              wip_ca_dict[route_phase][operation])
                        wip_ca_dict[route_phase][
                            operation] = amount - amount_to_take
                        print("Осталось",
                              operation,
                              wip_ca_dict[route_phase][operation])
                        new_wip.append({
                            'ORDER': order_name,
                            'BATCH_ID': f"{order_name}_{operation}",
                            'CODE': entity,
                            'AMOUNT': amount_to_take,
                            'OPERATION_ID': operation.split('|')[0],
                            'OPERATION_PROGRESS': operation_progress,
                            '#PARENT_CODE': row['CODE']
                        })

                print("Не хватило", need_amount)
                print()

            for child in specifications[entity]:
                wip[child] -= how_many * specifications[entity][child]
                if need_amount > 0:
                    new_wip.append({
                        'ORDER': order_name,
                        'BATCH_ID': f"{order_name}_{child}",
                        'CODE': child,
                        'AMOUNT': round(
                            need_amount * specifications[entity][child],
                            4
                        ),
                        'OPERATION_ID': '',
                        'OPERATION_PROGRESS': 100,
                        '#PARENT_CODE': row['CODE']
                    })

        if float(row['AMOUNT']) - how_many > 0:
            order_name = (f"[{date_to_week(row['ORDER'])}]"
                          f"{entities[row['CODE']]}_NOK")
            ok_priority = 3
            if how_many > 0:
                order_name += '_D'
                ok_priority = 4

            date_to_with_shift = (
                    datetime.strptime(
                        row['DATE_TO'],
                        '%Y-%m-%d %H:%M'
                    ) + timedelta(days=config['rules']['days-shift'])
            ).strftime('%Y-%m-%d 07:00')

            new_plan.append({
                'ORDER': order_name,
                'CODE': row['CODE'],
                'AMOUNT': float(row['AMOUNT']) - how_many,
                'DATE_FROM': date_to_with_shift,
                'DATE_TO': row['DATE_TO'],
                'PRIORITY': f"{entity_priority}_{date_to_with_shift}_"
                            f"{row['DATE_TO']}_{ok_priority}"
            })
            for child in specifications[entity]:
                new_wip.append({
                    'ORDER': order_name,
                    'BATCH_ID': f"{order_name}_{child}",
                    'CODE': child,
                    'AMOUNT': round(
                        (float(row['AMOUNT']) - how_many)
                        * specifications[entity][child], 4
                    ),
                    'OPERATION_ID': '',
                    'OPERATION_PROGRESS': 100,
                    '#PARENT_CODE': row['CODE']
                })

    new_plan = sorted(new_plan, key=itemgetter('PRIORITY'))
    dict2csv(new_wip, 'wip105.csv')
    dict2csv(new_plan, 'plan105.csv')


if __name__ == '__main__':
    main()
