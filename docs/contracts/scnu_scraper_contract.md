# 测试契约：SCNU 知识库爬虫

> 基于需求规格（PR #6）编写。此文档仅含公开接口签名和行为契约，不含实现细节。

## 公开接口（仅签名）

```python
# 模块级辅助函数
def _extract_pdf_urls(html_text: str) -> list[str]: ...

class SCNUZsbAdmissionsScraper(BaseScraper):
    def __init__(self): ...
    async def run(self) -> dict: ...
    # 内部方法（测试可通过子类覆盖或 mock 验证）：
    # async def _get_year_map(self, client) -> dict
    # async def _find_pdf_url(self, client, article_url) -> str | None
    # def _parse_pdf_table(self, pdf_bytes: bytes, year: int, province_type: str) -> list[dict]
```

## 行为契约

### SCNUZsbAdmissionsScraper.run()
- 输入：无（构造时确定配置）
- 输出：dict，含 {source: str, records: int, errors: int, output: str}
- 契约 1：成功抓取 → 返回 records > 0，output 为 JSON 文件路径
- 契约 2：网络全部失败 → 返回 records=0，errors > 0（不抛异常）
- 契约 3：部分年份失败 → 返回 records > 0 且 errors > 0（部分成功）
- 契约 4：返回的 source 字段 == "scnu_zsb_admissions"
- 契约 5：调用后 save_raw 写入 admissions_scnu.json 文件

### _parse_pdf_table（内部方法，可通过子类测试）
- 输入：pdf_bytes(bytes), year(int), province_type(str: "guangdong"|"waisheng")
- 输出：list[dict]，每条含年份/省份/科类/批次/最低分/最低位次
- 契约 1：合法 PDF 字节 → 返回结构化表格数据
- 契约 2：PDF 无表格 → 返回空列表（不抛异常）
- 契约 3：PDF 字节损坏 → 返回空列表（不抛异常）
- 契约 4：province_type="guangdong" → 记录含物理/历史分组
- 契约 5：province_type="waisheng" → 记录含文理分组
- 契约 6：表格中"合 计"行被跳过（不作为数据记录）

### _extract_pdf_urls（模块级函数）
- 输入：html_text(str)
- 输出：list[str]，PDF URL 列表
- 契约 1：HTML 含 PDF 链接 → 返回 URL 列表
- 契约 2：HTML 无 PDF 链接 → 返回空列表
- 契约 3：空字符串输入 → 返回空列表

## 边界条件
- 网络超时、HTTP 404/500
- PDF 文件损坏、PDF 为图片格式（无可提取文本）
- HTML 页面结构变化（找不到文章链接）
- 年份范围外（2022-2025 之外）

## 依赖
- BaseScraper（save_raw 方法）
- httpx.AsyncClient（HTTP 请求）
- pdfplumber（PDF 解析）
- BeautifulSoup（HTML 解析）
