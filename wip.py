from argparse import ArgumentParser
from collections import defaultdict
from contextlib import closing
from os import getcwd
from os.path import join
from xml.etree.ElementTree import parse

import paramiko
import yaml
from tqdm import tqdm

from utils.xml_tools import get_text_value, get_float_value_with_dot


def return_wip(server):
    sftpURL = server['sftpURL']
    sftpUser = server['sftpUser']
    sftpPass = server['sftpPass']
    sftpPath = '/home/http_request_collector/app/data/input/state/POST'

    client = paramiko.SSHClient()
    # automatically add keys without requiring human intervention
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(sftpURL, username=sftpUser, password=sftpPass)

    with closing(client) as ssh:
        with closing(ssh.open_sftp()) as ftp:
            final_path = sftpPath
            check = True
            while check:
                print(
                    sorted(
                        ftp.listdir(
                            path=final_path
                        ), reverse=True
                    )
                )
                check = False
                for i in sorted(
                        ftp.listdir(
                            path=final_path
                        ), reverse=True
                ):
                    lstatout = str(ftp.lstat(
                        '{}/{}'.format(final_path, i)
                    )).split()[0]
                    if 'd' in lstatout:
                        check = True
                        final_path = '{}/{}'.format(final_path, i)
                        break
            tqdm.write('{}/body'.format(final_path))
            with closing(ftp.open('{}/body'.format(final_path))) as f:
                xml_data = read_from_file(f)
    return xml_data


def read_from_file(xml_file):
    tree = parse(xml_file)
    root = tree.getroot()
    report = defaultdict(float)

    # читаем все фреймы в исходном файле
    rows = root.findall('MAT_DATA')

    for material in tqdm(rows, desc='Считываем XML'):
        # читаем идентификатор ДСЕ
        product = get_text_value(material, "MATNR")
        # читаем все строки НЗП по этой ДСЕ
        wip_rows = material.findall('MT_STOCK')
        for stock in wip_rows:
            if str(get_text_value(stock, 'LGORT'))[:3] != '105' and '-' not in product:
                continue

            # В LABST лежит количество
            amount = get_float_value_with_dot(stock, 'LABST')
            report[product] += amount

    return report


def main():

    parser = ArgumentParser(
        description='Инструмент консольной генерации отчетов '
                    'по результатам моделирования.'
    )

    parser.add_argument('-c', '--config', required=False,
                        default=join(getcwd(), 'kk_plan_parser.yml'))
    parser.add_argument('-s', '--server', required=False,
                        default=join(getcwd(), 'server.yml'))
    args = parser.parse_args()

    with open(args.config, 'r', encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=yaml.SafeLoader)

    with open(args.server, 'r', encoding="utf-8") as stream:
        server = yaml.load(stream, Loader=yaml.SafeLoader)

    xml_data = return_wip(
        server
    )
    print(xml_data)


if __name__ == '__main__':
    main()
