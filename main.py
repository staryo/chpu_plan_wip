import argparse
import csv
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
from utils.date_to_week import date_to_week
from utils.listofdicts_to_csv import dict2csv
from wip import return_wip


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
                float(row['AMOUNT']) * float(row['OPERATION_PROGRESS'])
            )
            wip_ca_dict[row['#ROUTE_PHASE']][
                f"{row['OPERATION_ID']}|100.0"] +=  done
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
            how_many = min(wip[child] / specifications[entity][child],
                           how_many)
        if how_many > 0:
            order_name = f"[{date_to_week(row['ORDER'])}]{entities[row['CODE']]}_OK"
            if how_many < float(row['AMOUNT']):
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
                'PRIORITY': f"{date_to_with_shift}_{row['DATE_TO']}"
            })

            if '-' in entity:
                route_phase = f"{entity}_Z{entity[13]}01"
            else:
                route_phase = f"{entity}_Z{specifications[entity][0][13]}01"

            need_amount = how_many
            if route_phase in wip_ca_dict:
                print("Нашли", route_phase)
                for operation, amount in wip_ca_dict[route_phase].items():
                    amount_to_take = min(need_amount, amount)
                    need_amount -= amount_to_take
                    operation_progress = float(operation.split('|')[1])
                    if amount_to_take > 0:
                        print("Взяли", operation, amount_to_take)
                        wip_ca_dict[route_phase][operation] -= amount_to_take
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
                        'AMOUNT': need_amount,
                        'OPERATION_ID': '',
                        'OPERATION_PROGRESS': 100,
                        '#PARENT_CODE': row['CODE']
                    })

        if float(row['AMOUNT']) - how_many > 0:
            order_name = f"[{date_to_week(row['ORDER'])}]{entities[row['CODE']]}_NOK"
            if how_many > 0:
                order_name += '_D'

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
                'PRIORITY': f"{date_to_with_shift}_{row['DATE_TO']}"
            })
            for child in specifications[entity]:
                new_wip.append({
                    'ORDER': order_name,
                    'BATCH_ID': f"{order_name}_{child}",
                    'CODE': child,
                    'AMOUNT': (
                                      float(row['AMOUNT']) - how_many
                              ) * specifications[entity][child],
                    'OPERATION_ID': '',
                    'OPERATION_PROGRESS': 100,
                    '#PARENT_CODE': row['CODE']
                })

    new_plan = sorted(new_plan, key=itemgetter('PRIORITY'))
    dict2csv(new_wip, 'wip105.csv')
    dict2csv(new_plan, 'plan105.csv')


if __name__ == '__main__':
    main()
