"""NIH Intramural Annual Report 爬虫 (Playwright 浏览器自动化)

从 intramural.nih.gov 按项目号+年份抓取 annual report，
提取 Goals, Summary, Publications (PMID), Keywords, PI, Collaborators 等。
"""

import re
import time

import pandas as pd
from playwright.sync_api import sync_playwright, Browser, BrowserContext

SEARCH_URL = "https://intramural.nih.gov/search/index.taf"


def _parse_project_num(core_project_num: str) -> tuple[str, str] | None:
    """ZIAMH002652 → ('MH', '002652'), Z01MH002251 → ('MH', '002251')"""
    # ZIA + 2-letter IC + 6 digits, or Z01 + 2-letter IC + 6 digits
    m = re.match(r'(?:ZI[A-Z]|Z\d{2})([A-Z]{2})(\d{6})', core_project_num)
    return (m.group(1), m.group(2)) if m else None


def _parse_report(text: str) -> dict:
    """Parse annual report page text into structured fields."""
    result = {}

    m = re.search(r'(ZI[A-Z]?\s*[A-Z]{2}\d{6}-\d{2})', text)
    result['project_num_full'] = m.group(1).replace(' ', '') if m else ''

    m = re.search(r'Report Title\s*\n+(.+?)(?:\n\d{4}\s+Fiscal)', text, re.S)
    result['title'] = m.group(1).strip() if m else ''

    m = re.search(r'(\d{4})\s+Fiscal Year', text)
    result['fiscal_year'] = m.group(1) if m else ''

    m = re.search(r'Principal Investigator\s*\n+(.+?)(?:\n\s*IRP Faculty|\n\s*Research Org)', text, re.S)
    result['pi'] = m.group(1).strip() if m else ''

    m = re.search(r'Research Organization\s*\n+(.+?)(?:\n\s*Lab Staff|\n\s*Keywords)', text, re.S)
    result['organization'] = m.group(1).strip() if m else ''

    m = re.search(r'Keywords\s*\n+(.+?)(?:\nGoals)', text, re.S)
    result['keywords'] = m.group(1).strip() if m else ''

    m = re.search(r'Goals and Objectives\s*\n+(.+?)(?:\nSummary)', text, re.S)
    result['goals'] = m.group(1).strip() if m else ''

    m = re.search(r'Summary\s*\n+(.+?)(?:\n\s*Return to Intramural|\Z)', text, re.S)
    result['summary'] = m.group(1).strip() if m else ''

    result['pmids'] = '; '.join(re.findall(r'PMID:\s*(\d+)', text))

    return result


class IntramuralClient:
    """NIH Intramural Annual Report 爬虫。

    用法:
        client = IntramuralClient()
        df = client.fetch(['ZIDDA000623'], years=[2023, 2024])
    """

    def __init__(self):
        self._pw = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None
        self._index_page = None

    def _ensure_browser(self):
        if self._browser is None:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled'],
            )
            self._ctx = self._browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/131.0.0.0 Safari/537.36'
                ),
            )
            self._index_page = self._ctx.new_page()
            self._index_page.goto(SEARCH_URL, wait_until='networkidle', timeout=30000)
            self._index_page.wait_for_timeout(2000)

    def close(self):
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._pw:
            self._pw.stop()
            self._pw = None

    def _fetch_one(self, code: str, project: str, year: str) -> dict | None:
        """Submit the onereport form and parse the result."""
        page = self._index_page
        try:
            page.select_option('form#numberlink select[name=code]', code)
            page.fill('form#numberlink input[name=project]', project)
            page.select_option('form#numberlink select[name=year]', year)

            with page.expect_popup(timeout=15000) as popup_info:
                page.click('form#numberlink input[type=submit]')
            popup = popup_info.value
            popup.wait_for_load_state('networkidle', timeout=20000)
            popup.wait_for_timeout(2000)

            text = popup.inner_text('body')
            popup.close()

            if 'Report Title' not in text:
                return None

            return _parse_report(text)
        except Exception as e:
            print(f"    ⚠ {code}{project} year={year}: {e}")
            return None

    def fetch(
        self,
        core_project_nums: list[str],
        years: list[int] | None = None,
    ) -> pd.DataFrame:
        """抓取多个 intramural 项目的 annual report。

        Args:
            core_project_nums: e.g. ['ZIDDA000623', 'ZIAMH002942']
            years: fiscal years to fetch. None = [current year].
        """
        if years is None:
            from datetime import date
            years = [date.today().year]

        self._ensure_browser()
        all_rows = []

        for num in core_project_nums:
            parsed = _parse_project_num(num)
            if not parsed:
                print(f"  跳过非 intramural 项目: {num}")
                continue
            code, project = parsed

            for yr in years:
                print(f"  {num} FY{yr} ...", end=' ')
                row = self._fetch_one(code, project, str(yr))
                if row:
                    row['core_project_num'] = num
                    all_rows.append(row)
                    print(f"OK ({len(row.get('summary',''))} chars)")
                else:
                    print("无数据")
                time.sleep(1)

        self.close()

        df = pd.DataFrame(all_rows)
        if not df.empty:
            cols = ['core_project_num', 'project_num_full', 'fiscal_year',
                    'title', 'pi', 'organization', 'keywords',
                    'goals', 'summary', 'pmids']
            df = df[[c for c in cols if c in df.columns]]
        print(f"共获取 {len(df)} 份 annual report")
        return df

    @staticmethod
    def save(df: pd.DataFrame, path: str):
        path = str(path)
        if not path.endswith('.gz'):
            path = path + '.gz' if path.endswith('.csv') else path + '.csv.gz'
        df.to_csv(path, index=False, compression='gzip')
        print(f"已保存 {len(df)} 份 → {path}")
