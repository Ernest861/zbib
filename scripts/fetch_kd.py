"""kd.nsfc.cn 项目详情爬取 (Playwright 浏览器自动化)"""

import csv
import os
import re
import time
import random
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


class NSFCKDClient:
    """按批准号批量爬取 kd.nsfc.cn 项目详情（摘要、参与人等）。

    用法:
        client = NSFCKDClient()
        client.scrape(input_file="nsfcfund_精神分裂_all.xlsx",
                      output_file="nsfc_kd_enriched.csv")
    """

    SEARCH_URL = "https://kd.nsfc.cn/finalProjectInit?advanced=true"

    HEADERS = [
        '项目批准号', '项目名称', '项目负责人', '依托单位', '研究期限', '资助经费',
        '申请代码', '项目类别', '关键词',
        '项目参与人', '中文摘要', '英文摘要', '结题摘要', '原文链接',
    ]

    def scrape(self, input_file: str, output_file: str, id_column: str = "项目编号"):
        """从 input_file 读取批准号列表，逐个爬取详情，写入 output_file。"""
        print(f"Loading input file: {input_file}")
        try:
            df = pd.read_excel(input_file)
        except Exception as e:
            print(f"Error loading Excel: {e}")
            return

        if id_column not in df.columns:
            print(f"Error: Column '{id_column}' not found. Available: {df.columns.tolist()}")
            return

        project_ids = df[id_column].dropna().unique()
        print(f"Found {len(project_ids)} unique project IDs.")

        processed_ids = self._load_progress(output_file)
        self._ensure_output_header(output_file)

        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(self.SEARCH_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            success_count = 0
            fail_count = 0

            for idx, pid in enumerate(project_ids):
                pid = str(pid).strip()
                if pid in processed_ids:
                    continue

                print(f"[{idx+1}/{len(project_ids)}] Processing: {pid}")
                data = {h: '' for h in self.HEADERS}
                data['项目批准号'] = pid

                try:
                    # Navigate to search
                    page.goto(self.SEARCH_URL, timeout=30000)
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)

                    # Fill approval number
                    inputs = page.query_selector_all("input.el-input__inner")
                    if len(inputs) < 3:
                        print(f"  [!] Cannot find search inputs, skipping")
                        fail_count += 1
                        continue

                    approval_input = inputs[2]
                    approval_input.click()
                    time.sleep(0.2)
                    approval_input.fill("")
                    time.sleep(0.1)
                    approval_input.type(pid, delay=50)
                    time.sleep(0.5)

                    # Click search
                    search_btn = page.query_selector("button.SolidBtn")
                    if not search_btn:
                        print(f"  [!] Cannot find search button, skipping")
                        fail_count += 1
                        continue

                    search_btn.click()
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)

                    # Check results
                    body_text = page.inner_text("body")
                    match = re.search(r'检索到\s*(\d+)\s*项', body_text)
                    if not match or int(match.group(1)) == 0:
                        print(f"  [!] No results for {pid}")
                        data['项目名称'] = 'Not Found'
                        fail_count += 1
                        self._append_row(output_file, data)
                        processed_ids.add(pid)
                        continue

                    # Extract list info
                    data = self._extract_list_info(data, body_text)

                    # Open detail page
                    data, detail_opened = self._extract_detail(data, page, context)

                    # Clean data
                    self._clean_data(data)

                    print(f"  ✓ {data['项目名称'][:50]}")
                    success_count += 1
                    self._append_row(output_file, data)
                    processed_ids.add(pid)

                except Exception as e:
                    print(f"  [!] Error crawling {pid}: {e}")
                    fail_count += 1
                    for p_page in context.pages[1:]:
                        try:
                            p_page.close()
                        except Exception:
                            pass

                time.sleep(random.uniform(2, 4))

            browser.close()
            print(f"\nCrawling completed! Success: {success_count}, Failed: {fail_count}")

    # ─────────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────────

    def _load_progress(self, output_file: str) -> set:
        processed = set()
        if os.path.exists(output_file):
            try:
                if os.path.getsize(output_file) > 0:
                    existing = pd.read_csv(output_file)
                    if '项目批准号' in existing.columns:
                        processed = set(existing['项目批准号'].astype(str))
                        print(f"Resuming... Already processed {len(processed)} projects.")
            except Exception as e:
                print(f"Warning reading existing output: {e}")
        return processed

    def _ensure_output_header(self, output_file: str):
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerow(self.HEADERS)

    def _append_row(self, output_file: str, data: dict):
        with open(output_file, 'a', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerow([data[col] for col in self.HEADERS])

    @staticmethod
    def _extract_list_info(data: dict, body_text: str) -> dict:
        marker_idx = body_text.find("历史记录")
        block = body_text[marker_idx:] if marker_idx >= 0 else body_text

        title_match = re.search(r'\d+\.(.+?)(?:\n|$)', block)
        if title_match:
            data['项目名称'] = title_match.group(1).strip()

        for field, pattern in [
            ('申请代码', r'申请代码[：:]\s*(\S+)'),
            ('项目类别', r'项目类别[：:]\s*(.+?)(?:\n|$)'),
            ('项目负责人', r'项目负责人[：:]\s*(.+?)(?:\n|$)'),
            ('资助经费', r'资助经费[：:]\s*([\d.]+(?:（万元）)?)'),
            ('依托单位', r'依托单位[：:]\s*(.+?)(?:\n|$)'),
            ('关键词', r'关键词[：:]\s*(.+?)(?:\n|$)'),
        ]:
            m = re.search(pattern, block)
            if m:
                data[field] = m.group(1).strip()

        return data

    @staticmethod
    def _extract_detail(data: dict, page, context) -> tuple[dict, bool]:
        """尝试打开详情页提取摘要等信息。"""
        title_link = None
        for link in page.query_selector_all("a"):
            text = link.inner_text().strip()
            if text and re.match(r'\d+\.', text) and len(text) > 5:
                title_link = link
                break

        if not title_link:
            print(f"  [!] Cannot find title link, saving list info only")
            return data, False

        try:
            with context.expect_page(timeout=15000) as new_page_info:
                title_link.click()

            detail_page = new_page_info.value
            detail_page.wait_for_load_state("networkidle")
            time.sleep(2)

            data['原文链接'] = detail_page.url
            detail_text = detail_page.inner_text("body")

            # 研究期限
            m = re.search(r'研究期限[：:]\n(.+?)(?:\n|$)', detail_text)
            if m:
                data['研究期限'] = m.group(1).strip()

            # 展开参与人
            try:
                expand = detail_page.query_selector('text="查看全部"')
                if expand and expand.is_visible():
                    expand.click()
                    time.sleep(0.5)
                    detail_text = detail_page.inner_text("body")
            except Exception:
                pass

            # 项目参与人
            m = re.search(r'查看全部\s*>?\n(.+?)\n项目摘要', detail_text, re.DOTALL)
            if m:
                data['项目参与人'] = re.sub(r'\n+', '; ', m.group(1).strip())

            # 摘要
            m = re.search(r'中文摘要[：:]\n(.+?)\n英文摘要', detail_text, re.DOTALL)
            if m:
                data['中文摘要'] = m.group(1).strip()

            m = re.search(r'英文摘要[：:]\n(.+?)\n结题摘要', detail_text, re.DOTALL)
            if m:
                data['英文摘要'] = m.group(1).strip()

            m = re.search(r'结题摘要\n(.+?)\n结题报告', detail_text, re.DOTALL)
            if m:
                data['结题摘要'] = m.group(1).strip()

            detail_page.close()
            return data, True

        except Exception as e:
            print(f"  [!] Detail page error: {e}")
            for p_page in context.pages[1:]:
                try:
                    p_page.close()
                except Exception:
                    pass
            return data, False

    @staticmethod
    def _clean_data(data: dict):
        for k, v in data.items():
            if isinstance(v, str):
                v = re.sub(r'\s+', ' ', v).strip()
                if v in ('暂无', '结题报告', '结题报告 结题报告全文 在线阅读', '.'):
                    v = ''
                data[k] = v
