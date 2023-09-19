import argparse
import csv
from argparse import ArgumentParser
from datetime import datetime, timedelta
from logging import basicConfig, DEBUG, INFO
from operator import itemgetter
from os import getcwd
from os.path import join
from time import strptime

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

    plan = return_plan191(server, args.material)
    dict2csv(plan, 'plan191.csv')

    with open('plan191.csv') as f:
        plan = [{k: v for k, v in row.items()}
                for row in csv.DictReader(f, skipinitialspace=True)]

    specifications = return_specifications(config)
    entities = get_entities(config)

    wip = return_wip(server)

    new_plan = []
    new_wip = []
    for row in plan:
        entity = row['CODE']
        how_many = float(row['AMOUNT'])
        if entity not in specifications:
            continue
        for child in specifications[entity]:
            how_many = min(wip[child] / specifications[entity][child], how_many)
        if how_many > 0:
            order_name = f"[{date_to_week(row['ORDER'])}]{entities[row['CODE']]}_OK"
            if how_many < float(row['AMOUNT']):
                order_name += '_D'
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
                # 'DATE_FROM': datetime.now().strftime('%Y-%m-%d 07:00'),
                'DATE_TO': row['DATE_TO'],
                'PRIORITY': f"{(datetime.strptime(row['DATE_TO'], '%Y-%m-%d %H:%M') - timedelta(days=21)).strftime('%Y-%m-%d 07:00')}_{row['DATE_TO']}"
            })
            for child in specifications[entity]:
                new_wip.append({
                    'ORDER': order_name,
                    'BATCH_ID': f"{order_name}_{child}",
                    'CODE': child,
                    'AMOUNT': how_many * specifications[entity][child],
                    'OPERATION_ID': '',
                    'OPERATION_PROGRESS': 100
                })
                wip[child] -= how_many * specifications[entity][child]
        if float(row['AMOUNT']) - how_many > 0:
            order_name = f"[{date_to_week(row['ORDER'])}]{entities[row['CODE']]}_NOK"
            # order_name = f"[{row['ORDER']}]{row['CODE']}_NOK"
            if how_many > 0:
                order_name += '_D'
            new_plan.append({
                'ORDER': order_name,
                'CODE': row['CODE'],
                'AMOUNT': float(row['AMOUNT']) - how_many,
                # 'DATE_FROM': (
                #         datetime.strptime(row['DATE_TO'], '%Y-%m-%d %H:%M') -
                #         timedelta(days=21)
                # ).strftime('%Y-%m-%d 07:00'),
                'DATE_FROM': (
                    max(
                        datetime.now() + timedelta(days=config['rules']['days-shift']),
                        datetime.strptime(
                            row['DATE_TO'], '%Y-%m-%d %H:%M'
                        ) - timedelta(days=21),
                    )
                ).strftime('%Y-%m-%d 07:00'),
                'DATE_TO': row['DATE_TO'],
                'PRIORITY': f"{(datetime.strptime(row['DATE_TO'], '%Y-%m-%d %H:%M') + timedelta(days=config['rules']['days-shift'])).strftime('%Y-%m-%d 07:00')}_{row['DATE_TO']}"
                # 'PRIORITY': f"{(datetime.now() + timedelta(days=config['rules']['days-shift'])).strftime('%Y-%m-%d 07:00')}_{row['DATE_TO']}"
                # 'NAME': entities[row['CODE']]
            })
            for child in specifications[entity]:
                new_wip.append({
                    'ORDER': order_name,
                    'BATCH_ID': f"{order_name}_{child}",
                    'CODE': child,
                    'AMOUNT': (float(row['AMOUNT']) - how_many) * specifications[entity][child],
                    'OPERATION_ID': '',
                    'OPERATION_PROGRESS': 100
                })

    # Пока убрали все партии из НЗП, которые не пригодятся
    # for code, amount in wip.items():
    #     if amount > 0:
    #         new_wip.append({
    #             'ORDER': '',
    #             'BATCH_ID': code,
    #             'CODE': code,
    #             'AMOUNT': amount,
    #             'OPERATION_ID': '',
    #             'OPERATION_PROGRESS': 100
    #         })

    new_plan = sorted(new_plan, key=itemgetter('PRIORITY'))
    dict2csv(new_wip, 'wip105.csv')
    dict2csv(new_plan, 'plan105.csv')


if __name__ == '__main__':
    main()
