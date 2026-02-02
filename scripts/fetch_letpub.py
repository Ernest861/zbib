"""LetPub 国自然项目数据下载 (Playwright 浏览器自动化)"""

import glob
import os
import re
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright


GRANT_URL = "https://www.letpub.com.cn/index.php?page=grant"
LOGIN_URL = "https://www.letpub.com.cn/index.php?page=login"

_CLOSED_HINTS = (
    "Target page, context or browser has been closed",
    "TargetClosedError",
)


class LetPubClient:
    """LetPub 逐年下载国自然项目 Excel 数据。

    用法:
        client = LetPubClient(keyword="精神分裂", output_dir=Path("../nsfc_data"))
        client.download(start=1997, end=2023, email="x@y.com", password="***")
        client.merge()  # 合并为 nsfcfund_精神分裂_all.xlsx
    """

    def __init__(self, keyword: str, output_dir: Path):
        self.keyword = keyword
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def download(self, start: int = 1997, end: int = 2023,
                 email: str = None, password: str = None) -> list[Path]:
        """逐年下载 LetPub 国自然项目 xlsx，返回已下载文件列表。"""
        return self._download_by_year(start, end, email, password)

    def merge(self) -> pd.DataFrame | None:
        """合并所有年份的 xls 为一个 xlsx 文件。"""
        return self._merge_yearly_files()

    # ─────────────────────────────────────────────
    # 浏览器会话管理
    # ─────────────────────────────────────────────

    def _storage_state_path(self) -> Path:
        return self.output_dir / "letpub_storage_state.json"

    def _new_session(self, pw, with_state: bool):
        browser = pw.chromium.launch(headless=False)
        ssp = self._storage_state_path()
        if with_state and ssp.exists():
            context = browser.new_context(accept_downloads=True, storage_state=str(ssp))
        else:
            context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})
        return browser, context, page

    # ─────────────────────────────────────────────
    # 登录
    # ─────────────────────────────────────────────

    def _check_logged_in(self, page) -> bool:
        """检查当前页面是否已登录。"""
        content = page.content()
        return ("退出" in content or "logout" in content.lower() or "个人中心" in content)

    def _login(self, page, email: str = None, password: str = None):
        """处理登录逻辑: 自动登录 → 手动 fallback。"""
        ssp = self._storage_state_path()

        # 检查已有登录态
        need_login = True
        if ssp.exists():
            print("[1] 检测到已保存的登录态，尝试使用...")
            try:
                page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2)
                if self._check_logged_in(page):
                    print("    ✓ 登录态有效，无需重新登录")
                    need_login = False
                else:
                    print("    [!] 登录态已过期，需要重新登录")
            except Exception:
                print("    [!] 无法验证登录态，需要重新登录")

        if not need_login:
            return

        # 自动登录
        if email and password:
            print(f"[2] 自动登录 LetPub: {email}")
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2)

                print("    填写登录表单...")
                email_input = page.locator('input[name="email"]').first
                password_input = page.locator('input[name="password"]').first
                email_input.wait_for(state="visible", timeout=10000)
                password_input.wait_for(state="visible", timeout=10000)
                email_input.fill(email)
                password_input.fill(password)
                time.sleep(0.5)

                print("    执行登录...")
                page.evaluate("login()")

                try:
                    page.wait_for_url("**/index.php**", timeout=15000)
                except Exception:
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass

                time.sleep(3)

                if self._check_logged_in(page):
                    print("    ✓ 登录成功")
                else:
                    print("    [!] 警告：未检测到明显的登录成功标志")
                    page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=60000)
                    time.sleep(2)
                    if self._check_logged_in(page):
                        print("    ✓ 登录成功（通过基金页面验证）")
                    else:
                        print("    [!] 登录状态不确定，继续尝试...")
                        page.screenshot(path=str(self.output_dir / "login_debug.png"))

            except Exception as e:
                print(f"    ✗ 自动登录失败: {e}")
                import traceback
                traceback.print_exc()
                print("    将尝试手动登录...")
                page.screenshot(path=str(self.output_dir / "login_error.png"))
                page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=60000)
                input("    >>> 请手动登录，完成后按回车继续 <<<")
        else:
            print("[2] 打开LetPub基金页面，请手动登录...")
            page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=60000)
            input("    >>> 登录完成后按回车继续 <<<")

    # ─────────────────────────────────────────────
    # 快速登录验证 (不下载任何数据)
    # ─────────────────────────────────────────────

    @classmethod
    def verify_login(cls, email: str, password: str) -> bool:
        """尝试登录 LetPub，成功返回 True，失败返回 False。不下载数据。"""
        from playwright.sync_api import sync_playwright
        ok = False
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                time.sleep(1)
                page.locator('input[name="email"]').first.fill(email)
                page.locator('input[name="password"]').first.fill(password)
                time.sleep(0.3)
                page.evaluate("login()")
                try:
                    page.wait_for_url("**/index.php**", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)
                content = page.content()
                ok = ("退出" in content or "logout" in content.lower() or "个人中心" in content)
            except Exception:
                ok = False
            finally:
                browser.close()
        return ok

    # ─────────────────────────────────────────────
    # 搜索 + 下载单个年份
    # ─────────────────────────────────────────────

    def _fill_and_search(self, page, year: int):
        """填写搜索表单并点击查询。"""
        page.wait_for_selector('input[name="name"]', timeout=10000)
        form = page.locator("form").filter(has=page.locator('input[name="name"]')).first
        if not form.is_visible(timeout=3000):
            raise Exception("未找到包含关键词输入框的查询表单")

        # 确保在基础搜索标签页
        try:
            basic_tab = page.locator('.layui-tab-title li:has-text("基础搜索"), .layui-tab-title li:first-child').first
            if basic_tab.is_visible(timeout=2000):
                basic_tab.click()
                time.sleep(1)
        except Exception:
            pass

        # 填写关键词
        name_input = form.locator('input[name="name"]').first
        name_input.clear()
        name_input.fill(self.keyword)
        time.sleep(0.3)

        # 选择年份
        year_str = str(year)
        print(f"    设置年份: {year_str}")

        for select_name in ("startTime", "endTime"):
            sel = form.locator(f'select[name="{select_name}"]').first
            if sel.is_visible(timeout=3000):
                try:
                    sel.select_option(year_str)
                    print(f"    ✓ {select_name} 已设置: {year_str}")
                except Exception:
                    page.evaluate(f"""
                        (function() {{
                            const form = document.querySelector('form');
                            const sels = form ? form.querySelectorAll('select[name="{select_name}"]') : document.querySelectorAll('select[name="{select_name}"]');
                            sels.forEach(s => {{
                                if (s.querySelector('option[value="{year_str}"]')) {{
                                    s.value = '{year_str}';
                                    s.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }}
                            }});
                        }})();
                    """)

        time.sleep(1)

        # 验证表单值
        kw_val = name_input.input_value()
        start_sel = form.locator('select[name="startTime"]').first
        end_sel = form.locator('select[name="endTime"]').first
        start_val = start_sel.input_value() if start_sel.count() else ""
        end_val = end_sel.input_value() if end_sel.count() else ""
        print(f"    表单值确认: 关键词={kw_val}, 开始={start_val}, 结束={end_val}")

        # 点击查询按钮
        self._click_search_button(page, form)

        # 等待结果
        print("    等待搜索结果...")
        time.sleep(4)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

        return form

    def _click_search_button(self, page, form):
        """查找并点击查询按钮。"""
        button_selectors = [
            'input[type="image"][value="advSearch"]',
            'input[type="image"][name="submit"][value="advSearch"]',
            'input[type="image"]#submit',
            'input[type="image"][onclick*="checksubmit"]',
            'input[type="submit"][value*="查询"]',
            'input[type="button"][value*="查询"]',
            'input[value*="查"][value*="询"]',
            'button:has-text("查询")',
            'button:has-text("查 询")',
            'input[value*="查询"]',
            'input[type="submit"][value*="搜索"]',
            'input[type="button"][value*="搜索"]',
            'button:has-text("搜索")',
            'input[value*="搜索"]',
            'input[type="submit"]',
            'input[type="button"]',
            'button[type="submit"]',
            'button',
        ]

        for selector in button_selectors:
            try:
                btn = form.locator(selector).first
                if btn.is_visible(timeout=2000):
                    btn.scroll_into_view_if_needed()
                    time.sleep(0.3)
                    btn.click()
                    print(f"    ✓ 已点击查询按钮 ({selector})")
                    return
            except Exception:
                continue

        # fallback: role-based
        try:
            btn = page.get_by_role("button", name=re.compile(r"查\s*询"))
            if btn.is_visible(timeout=2000):
                btn.scroll_into_view_if_needed()
                time.sleep(0.2)
                btn.click()
                print('    ✓ 已通过 role=button 点击"查 询"')
                return
        except Exception:
            pass

        # fallback: JS
        js_result = page.evaluate("""
            (function() {
                const form = document.querySelector('form');
                const root = form || document;
                const candidates = root.querySelectorAll('input, button');
                function label(el){
                    const v = (el.value || '').trim();
                    const t = (el.textContent || '').trim();
                    return (v || t);
                }
                for (let el of candidates) {
                    const tag = el.tagName.toLowerCase();
                    const type = (el.getAttribute('type') || '').toLowerCase();
                    if (tag === 'input' && !['submit','button','image'].includes(type)) continue;
                    if (tag === 'button' && type && type !== 'submit') continue;
                    const rect = el.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    const lab = label(el);
                    if (lab.includes('查询') || lab.includes('搜索') || lab === 'advSearch' || (el.getAttribute('onclick') || '').includes('checksubmit')) {
                        el.click();
                        return { success: true, label: lab };
                    }
                }
                for (let el of candidates) {
                    const tag = el.tagName.toLowerCase();
                    const type = (el.getAttribute('type') || '').toLowerCase();
                    if (tag === 'input' && !['submit','button','image'].includes(type)) continue;
                    if (tag === 'button' && type && type !== 'submit') continue;
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        el.click();
                        return { success: true, label: label(el), fallback: true };
                    }
                }
                return { success: false };
            })();
        """)
        if js_result.get('success'):
            print(f"    ✓ JS点击成功: {js_result.get('label')}")
            return

        raise Exception("无法找到查询按钮")

    def _check_result_count(self, page) -> int:
        """从页面提取搜索结果数量。"""
        body_text = page.inner_text("body")
        patterns = [
            r'(\d+)\s*条相关记录',
            r'共\s*(\d+)\s*条',
            r'找到\s*(\d+)\s*条',
            r'(\d+)\s*条记录',
            r'共找到\s*(\d+)\s*条',
            r'(\d+)\s*条',
        ]
        for pattern in patterns:
            m = re.search(pattern, body_text)
            if m:
                count = int(m.group(1))
                print(f"    通过模式 '{pattern}' 匹配到: {count} 条")
                return count

        # fallback: 从表格行数判断
        try:
            rows = page.locator('table tr').count()
            if rows > 3:
                print(f"    [!] 未找到记录数文本，但检测到 {rows} 行数据")
                return rows - 1
        except Exception:
            pass
        return 0

    def _has_downloadable_data(self, page, count: int) -> bool:
        """即使 count==0，检查页面是否有数据/下载按钮。"""
        if count > 0:
            return True
        try:
            rows = page.locator('table tr').count()
            if rows > 3:
                print(f"    [!] 虽然记录数为0，但检测到表格数据（{rows}行），继续尝试下载")
                return True
        except Exception:
            pass
        try:
            if page.locator('#download_excel_button, a:has-text("下载"), button:has-text("下载")').count() > 0:
                print(f"    [!] 虽然记录数为0，但检测到下载按钮，继续尝试下载")
                return True
        except Exception:
            pass
        return False

    def _click_download(self, page) -> 'Download | None':
        """查找并点击下载按钮，返回 Download 对象。"""
        # 先滚动到分页器区域
        for pag_sel in [':has-text("首页")', ':has-text("上一页")', ':has-text("条相关记录")']:
            try:
                pagination = page.locator(pag_sel).first
                if pagination.is_visible(timeout=2000):
                    pagination.scroll_into_view_if_needed()
                    time.sleep(1)
                    break
            except Exception:
                continue

        time.sleep(2)

        download_selectors = [
            '#download_excel_button',
            'a#download_excel_button',
            'button#download_excel_button',
            ':has-text("首页") ~ a:has-text("下载")',
            ':has-text("尾页") ~ a:has-text("下载")',
            'a:has-text("下载")',
            'button:has-text("下载")',
            'a:has-text("Excel")',
            'a:has-text("xlsx")',
            'a:has-text("导出")',
            'a[href*="download"]',
            'a[href*="excel"]',
            'a[href*="xlsx"]',
            'button[onclick*="download"]',
            'button[onclick*="excel"]',
            '.download-btn',
            '.excel-btn',
        ]

        for attempt in range(3):
            if attempt > 0:
                print(f"    第 {attempt + 1} 次尝试查找下载按钮...")
                time.sleep(2)

            for selector in download_selectors:
                try:
                    for loc in page.locator(selector).all():
                        try:
                            loc.wait_for(state="visible", timeout=3000)
                            loc.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            if loc.is_visible():
                                print(f"    找到下载按钮: {selector}")
                                loc.wait_for(state="visible", timeout=3000)
                                with page.expect_download(timeout=60000) as download_info:
                                    loc.click()
                                return download_info.value
                        except Exception:
                            continue
                except Exception:
                    continue

        return None

    @staticmethod
    def _validate_excel(path: Path) -> bool:
        """验证下载的文件是否为 Excel 格式。"""
        try:
            with open(path, 'rb') as f:
                header = f.read(4)
            if header.startswith(b'PK') or header.startswith(b'\xd0\xcf\x11\xe0'):
                return True
            file_content = path.read_text(encoding='utf-8', errors='ignore')[:500]
            if '<html' in file_content.lower() or '<!doctype' in file_content.lower():
                print(f"    ✗ 下载的文件是 HTML 页面，不是 Excel 文件")
                path.unlink()
                return False
            return True  # 格式不明但保留
        except Exception:
            return True

    # ─────────────────────────────────────────────
    # 主下载循环
    # ─────────────────────────────────────────────

    def _download_by_year(self, start: int, end: int,
                          email: str = None, password: str = None) -> list[Path]:
        downloaded_files = []

        with sync_playwright() as pw:
            browser, context, page = self._new_session(pw, with_state=True)

            self._login(page, email, password)

            # 保存登录态
            try:
                context.storage_state(path=str(self._storage_state_path()))
                print(f"[✓] 已保存登录态: {self._storage_state_path()}")
            except Exception as e:
                print(f"[!] 保存登录态失败: {e}")

            page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)

            for year in range(start, end + 1):
                out_path = self.output_dir / f"nsfcfund_{self.keyword}_{year}.xls"
                if out_path.exists():
                    print(f"[跳过] {year} 已存在: {out_path.name}")
                    downloaded_files.append(out_path)
                    continue

                print(f"\n[{year}] 查询: {self.keyword}, 批准年份: {year}")

                try:
                    # 恢复关闭的浏览器
                    if page.is_closed():
                        print("    [!] 检测到页面已关闭，正在恢复...")
                        try:
                            browser.close()
                        except Exception:
                            pass
                        browser, context, page = self._new_session(pw, with_state=True)

                    # 每次回到搜索页面
                    try:
                        page.goto(GRANT_URL, wait_until="domcontentloaded", timeout=90000)
                        time.sleep(2)
                        page.wait_for_selector('input[name="name"]', timeout=10000)
                        time.sleep(1)
                    except Exception as e:
                        print(f"    [!] 页面加载超时: {e}")
                        time.sleep(3)

                    self._fill_and_search(page, year)

                    # 检查 404
                    if '404' in page.title() or 'Not Found' in page.title():
                        raise Exception(f"页面返回404错误: {page.url}")

                    try:
                        page.wait_for_selector('table, :has-text("条"), #download_excel_button', timeout=10000)
                    except Exception:
                        pass
                    time.sleep(2)

                    count = self._check_result_count(page)
                    print(f"    最终判断: {count} 条记录")

                    if not self._has_downloadable_data(page, count):
                        print(f"    {year} 无数据，跳过")
                        continue

                    download = self._click_download(page)
                    if download:
                        download.save_as(str(out_path))
                        if self._validate_excel(out_path):
                            print(f"    ✓ 已下载: {out_path.name}")
                            downloaded_files.append(out_path)
                    else:
                        print(f"    ✗ 未找到下载按钮")
                        page.screenshot(path=str(self.output_dir / f"debug_{year}.png"))

                except Exception as e:
                    print(f"    ✗ 失败: {e}")
                    import traceback
                    traceback.print_exc()

                    if any(h in str(e) for h in _CLOSED_HINTS):
                        print("    [!] 浏览器已关闭，自动重建会话...")
                        try:
                            browser.close()
                        except Exception:
                            pass
                        browser, context, page = self._new_session(pw, with_state=True)

                    try:
                        page.screenshot(path=str(self.output_dir / f"error_{year}.png"))
                        html_path = self.output_dir / f"error_{year}.html"
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(page.content())
                    except Exception:
                        pass

                time.sleep(2)

            browser.close()

        print(f"\n{'='*50}")
        print(f"下载完成: {len(downloaded_files)} 个文件")
        for f in downloaded_files:
            print(f"  {f.name}")
        print(f"{'='*50}")
        return downloaded_files

    # ─────────────────────────────────────────────
    # 合并
    # ─────────────────────────────────────────────

    def _merge_yearly_files(self) -> pd.DataFrame | None:
        pattern = self.output_dir / f"nsfcfund_{self.keyword}_*.xls"
        files = sorted(glob.glob(str(pattern)))

        if not files:
            print(f"[!] 未找到匹配文件: {pattern}")
            return None

        print(f"\n[合并] 找到 {len(files)} 个文件")
        dfs = []
        for f in files:
            try:
                import xlrd
                wb = xlrd.open_workbook(f, ignore_workbook_corruption=True)
                sh = wb.sheet_by_index(0)
                headers = [sh.cell_value(1, c) for c in range(sh.ncols)]
                data = [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(2, sh.nrows)]
                df = pd.DataFrame(data, columns=headers)
                print(f"  {Path(f).name}: {len(df)} 条")
                dfs.append(df)
            except Exception as e:
                print(f"  {Path(f).name}: 读取失败 - {e}")

        if not dfs:
            return None

        merged = pd.concat(dfs, ignore_index=True)
        if "项目编号" in merged.columns:
            before = len(merged)
            merged = merged.drop_duplicates(subset=["项目编号"], keep="first")
            print(f"  去重: {before} → {len(merged)}")

        out_path = self.output_dir / f"nsfcfund_{self.keyword}_all.xlsx"
        merged.to_excel(out_path, index=False, engine="openpyxl")
        print(f"[✓] 合并完成: {out_path} ({len(merged)} 条)")
        return merged
