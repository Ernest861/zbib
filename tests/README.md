# tests/ — 单元测试

使用 pytest 进行自动化测试。

## 测试文件

```
tests/
├── __init__.py
├── test_applicant.py    # 申请人分析测试 (35 个)
└── test_plotting.py     # 绑图模块测试 (23 个)
```

## 运行测试

```bash
# 运行全部测试
pytest tests/

# 运行特定文件
pytest tests/test_applicant.py

# 详细输出
pytest tests/ -v

# 显示覆盖率
pytest tests/ --cov=scripts
```

## 测试内容

### test_applicant.py (35 个测试)

| 类别 | 测试数 | 内容 |
|------|--------|------|
| 评分计算 | 8 | 适配度/胜任力/象限判定 |
| 作者匹配 | 6 | 姓名模式、第一/通讯作者 |
| 基准排名 | 5 | 百分位计算、快速排名 |
| 数据质量 | 4 | 边界条件、空数据处理 |
| 报告生成 | 5 | Markdown 章节、格式验证 |
| 评估功能 | 4 | 叙事评估、薄弱维度 |
| 权重验证 | 2 | 权重归一化、自定义权重 |
| 超图网络 | 3 | 合作超边、团队稳定性 |

### test_plotting.py (23 个测试)

| 类别 | 测试数 | 内容 |
|------|--------|------|
| 色板常量 | 6 | COLORS 键、色值格式 |
| 包结构 | 3 | __all__ 导出、延迟加载 |
| Mixin 测试 | 14 | 导入、组合、功能验证 |

## 跳过条件

部分测试需要 matplotlib，会在无图形环境时跳过:

```python
requires_matplotlib = pytest.mark.skipif(
    not MATPLOTLIB_AVAILABLE,
    reason="matplotlib not available"
)

@requires_matplotlib
def test_plot_timeline():
    ...
```

## 添加新测试

```python
# tests/test_new_feature.py
import pytest
from scripts.my_module import MyClass

class TestMyClass:
    def test_basic_functionality(self):
        obj = MyClass()
        assert obj.do_something() == expected

    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
    ])
    def test_with_params(self, input, expected):
        assert MyClass.process(input) == expected
```

## CI 集成

测试在 GitHub Actions 中自动运行:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest tests/ --cov=scripts
```
