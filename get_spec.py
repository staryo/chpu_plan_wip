import argparse
from argparse import ArgumentParser
from collections import defaultdict
from logging import basicConfig, INFO, DEBUG
from os import getcwd
from os.path import join

import yaml

from ia_rest.iarest import IARest
from utils.list_to_dict import list_to_dict


def return_specifications(config):

    with IARest.from_config(config['IA']) as ia:
        entities = list_to_dict(ia.get_from_rest_collection(
            'entity'
        ))
        spec_items = ia.get_from_rest_collection(
            'specification_item'
        )
        spec_report = defaultdict(lambda: defaultdict(float))
        for row in spec_items:
            if '(' in entities[row['parent_id']]['identity']:
                continue
            spec_report[
                entities[row['parent_id']]['identity']
            ][entities[row['child_id']]['identity']] = row['amount']

        return spec_report


def get_entities(config):

    with IARest.from_config(config['IA']) as ia:
        entities = ia.get_from_rest_collection(
            'entity'
        )

        entity_report = {}

        for row in entities:
            entity_report[row['identity']] = row['name']

        return entity_report

def get_entities(config):

    with IARest.from_config(config['IA']) as ia:
        entities = ia.get_from_rest_collection(
            'entity'
        )

        entity_report = {}

        for row in entities:
            entity_report[row['identity']] = row['name']

        return entity_report

if __name__ == '__main__':
    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'config.yml'))

    parser.add_argument('-d', '--debug', required=False, action='store_true',
                        default=False)

    args = parser.parse_args()

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=args.debug and DEBUG or INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    return_specifications(config)