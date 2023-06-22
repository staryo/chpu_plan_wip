import argparse
import csv
import datetime
import sys
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import closing
from datetime import timedelta
from operator import itemgetter
from os import getcwd
from os.path import join
from xml.etree.ElementTree import XMLParser, parse, ParseError

import paramiko
import yaml
from tqdm import tqdm

from utils.xml_tools import get_text_value, get_float_value_with_dot


def read_pg_from_ftp(ftp_client, path_to_iter, report=None,
                     priority=None, all_dates=None, material_number=None):
    if report is None:
        report = defaultdict(float)
    if priority is None:
        priority = {}
    if all_dates is None:
        all_dates = set()
    iter1 = tqdm(
        sorted(read_from_ftp(ftp_client, path_to_iter)),
        desc=path_to_iter,
        file=sys.stdout,
        position=0
    )
    for each_path in iter1:
        iter1.desc = f'{path_to_iter} ({len(report)})'
        if read_from_ftp(ftp_client, each_path):
            report, priority, all_dates = read_pg_from_ftp(
                ftp_client, each_path, report, priority, all_dates, material_number
            )
        else:
            report, priority, all_dates = read_pg_file(
                ftp_client, each_path, report, priority, all_dates, material_number
            )
    return report, priority, all_dates


def read_pg_file(ftp_client, path, report, priority, all_dates, material_number):
    with closing(ftp_client.open('{}/body'.format(path))) as f:
        # парсим xml
        try:
            # ставим utf-8 хардкодом, чтоб
            # никаких неожиданностей не было
            xmlp = XMLParser(encoding="utf-8")
            tree = parse(f, parser=xmlp)
            root = tree.getroot()
        except ParseError:
            tqdm.write('Ошибка чтения файла -- не распознан корень')
            return
        material = root.find('MT_DATA')
        matnr = get_text_value(material, 'MATNR')
        if material_number in matnr:
            tqdm.write(path)
        for each in material.findall('MT_PG'):
            if get_float_value_with_dot(each, "QUAN") <= 0:
                continue
            if get_text_value(each, 'VERID') is None:
                continue
            if get_text_value(each, 'TYPE') == 'SP':
                order_date = datetime.datetime.strptime(
                        get_text_value(each, "DATE"), '%Y-%m-%d'
                ).date()
                order_date -= timedelta(days=order_date.weekday())
                order_date = order_date.strftime('%Y-%m-%d 07:00')
                # order_date = f'{get_text_value(each, "DATE")} 07:00'
                if datetime.datetime.strptime(
                        get_text_value(each, "DATE"), '%Y-%m-%d'
                ).date() < datetime.datetime.today().date():
                    continue
                if datetime.datetime.strptime(
                        get_text_value(each, "DATE"), '%Y-%m-%d'
                ).date() > datetime.datetime.today().date() + timedelta(days=60):
                    continue

                order_name = f'{matnr}|' \
                    f'{get_text_value(each, "VERID")}|' \
                    f'{order_date}'
                if order_date in all_dates:
                    if order_name not in priority:
                        priority[order_name] = \
                            f'9{order_date[:4]}{order_date[5:7]}'
                else:
                    priority[order_name] = f'{order_date[:4]}{order_date[5:7]}{order_date[8:10]}'
                    all_dates.add(order_date)
                report[f'{order_name}|{priority[order_name]}'] += \
                    get_float_value_with_dot(each, "QUAN")
        return report, priority, all_dates


def read_from_ftp(ftp_client, path_to_iter):
    report = []
    for i in sorted(
            ftp_client.listdir(
                path=path_to_iter
            )
    ):
        lstatout = str(ftp_client.lstat(
            '{}/{}'.format(path_to_iter, i)
        )).split()[0]
        if 'd' in lstatout:
            report.append('{}/{}'.format(path_to_iter, i))
    return report


def read_from_ftp_last_delivery(ftp_client, paths_to_iter):
    report = []
    first_date = None
    for path_to_iter in paths_to_iter:
        for i in sorted(
            ftp_client.listdir(path=path_to_iter),
            reverse=True
        ):
            curent_date = datetime.datetime.strptime(
                    f'{path_to_iter[-10:]} {i}',
                    '%Y-%m-%d %H-%M'
                )
            if first_date is None:
                first_date = curent_date
            if (first_date - curent_date).total_seconds() / 3600 > 1:
                return report
            lstatout = str(ftp_client.lstat(
                '{}/{}'.format(path_to_iter, i)
            )).split()[0]
            if 'd' in lstatout:
                report.append('{}/{}'.format(path_to_iter, i))
    return report


def return_plan191(server, matnr):
    sftpURL = server['sftpURL']
    sftpUser = server['sftpUser']
    sftpPass = server['sftpPass']
    sftpPath = '/home/http_request_collector/app/data/dop/pg/POST'

    client = paramiko.SSHClient()
    # automatically add keys without requiring human intervention
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(sftpURL, username=sftpUser, password=sftpPass)
    report = defaultdict(float)
    priority = {}
    all_dates = set()
    with closing(client) as ssh:
        with closing(ssh.open_sftp()) as ftp:
            path_list = read_from_ftp(ftp, sftpPath)
            print(path_list)
            path_list2 = read_from_ftp_last_delivery(
                ftp,
                sorted(path_list, reverse=True)
            )
            iter = tqdm(
                sorted(path_list2),
                desc=sorted(path_list2)[-1],
                file=sys.stdout,
                position=0
            )
            for path2 in iter:
                report, priority, all_dates = read_pg_from_ftp(
                    ftp, path2, report, priority, all_dates, matnr
                )
    result = [
        {
            'ORDER': key.split('|')[2][:10],
            'CODE': key.split('|')[0],
            'AMOUNT': round(value * 1000) / 1000,
            'DATE_FROM': key.split('|')[2],
            'DATE_TO': key.split('|')[2],
            'PRIORITY': key.split('|')[3],
        }
        for key, value in report.items()
    ]
    result = sorted(result, key=itemgetter('PRIORITY'))

    return result


def main():
    parser = ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))

    args = parser.parse_args()

    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)

    result = return_plan191(server)

    keys = result[0].keys()
    with open(
            'plan191.csv', 'w', newline='', encoding="utf-8"
    ) as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(result)


if __name__ == '__main__':
    main()
