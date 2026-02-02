#!/usr/bin/env python3
"""zbib v2 — YAML驱动的 NIBS 文献空白分析

用法:
    python run_all.py -c configs/scz_ofc_rtms.yaml --skip-fetch
    python run_all.py -c configs/scz_ofc_rtms.yaml --step 6
    python run_all.py -c configs/scz_ofc_rtms.yaml --letpub-email x@y.com --letpub-password ***
"""

import argparse
import os

from scripts.pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description='NIBS文献空白分析')
    parser.add_argument('-c', '--config', required=True, help='YAML配置文件路径')
    parser.add_argument('--step', type=int, help='只运行指定步骤 (6=分析+出图)')
    parser.add_argument('--skip-fetch', action='store_true', help='跳过爬虫步骤')
    parser.add_argument('--letpub-email', default=os.environ.get('LETPUB_EMAIL', ''))
    parser.add_argument('--letpub-password', default=os.environ.get('LETPUB_PASSWORD', ''))
    args = parser.parse_args()

    pipe = Pipeline.from_yaml(args.config)
    pipe.run(
        step=args.step,
        skip_fetch=args.skip_fetch,
        email=args.letpub_email,
        password=args.letpub_password,
    )


if __name__ == '__main__':
    main()
