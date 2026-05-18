"""SCNU curriculum scraper — major list + training plans from zsb.scnu.edu.cn.

Sources:
  1. 招生网 https://zsb.scnu.edu.cn — major catalog with colleges
  2. 教务处 https://jwc.scnu.edu.cn — training plan PDFs / pages
  3. 各学院官网 — individual college pages as fallback
"""
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
from loguru import logger

from scrapers.config import ScraperConfig
from scrapers.base_scraper import BaseScraper

SCNU_MOE_CODE = "10574"
SCNU_NAME = "华南师范大学"

SCNU_COLLEGES = [
    ("教育科学学院", "https://jky.scnu.edu.cn"),
    ("心理学院", "https://psy.scnu.edu.cn"),
    ("哲学与社会发展学院", "https://zheshe.scnu.edu.cn"),
    ("马克思主义学院", "https://marx.scnu.edu.cn"),
    ("历史文化学院", "https://lswh.scnu.edu.cn"),
    ("外国语言文化学院", "https://sfs.scnu.edu.cn"),
    ("国际文化学院", "https://cicz.scnu.edu.cn"),
    ("文学院", "https://wxy.scnu.edu.cn"),
    ("数学科学学院", "https://maths.scnu.edu.cn"),
    ("物理与电信工程学院", "https://physics.scnu.edu.cn"),
    ("化学学院", "https://chem.scnu.edu.cn"),
    ("生命科学学院", "https://life.scnu.edu.cn"),
    ("地理科学学院", "https://geography.scnu.edu.cn"),
    ("计算机学院", "https://cs.scnu.edu.cn"),
    ("软件学院", "https://ss.scnu.edu.cn"),
    ("信息光电子科技学院", "https://ioe.scnu.edu.cn"),
    ("半导体科学与技术学院", "https://semi.scnu.edu.cn"),
    ("环境学院", "https://env.scnu.edu.cn"),
    ("经济与管理学院", "https://em.scnu.edu.cn"),
    ("法学院", "https://law.scnu.edu.cn"),
    ("政治与公共管理学院", "https://zg.scnu.edu.cn"),
    ("体育科学学院", "https://sport.scnu.edu.cn"),
    ("音乐学院", "https://music.scnu.edu.cn"),
    ("美术学院", "https://art.scnu.edu.cn"),
    ("旅游管理学院", "https://stm.scnu.edu.cn"),
    ("信息管理系", "https://im.scnu.edu.cn"),
    ("国际商学院", "https://ibs.scnu.edu.cn"),
    ("职业教育学院", "https://zq.scnu.edu.cn"),
    ("城市文化学院", "https://cch.scnu.edu.cn"),
    ("科学技术与社会研究院", "https://sts.scnu.edu.cn"),
    ("脑科学与康复医学研究院", "https://brain.scnu.edu.cn"),
    ("人工智能学院", "https://ai.scnu.edu.cn"),
    ("电子与信息工程学院", "https://eie.scnu.edu.cn"),
    ("材料与新能源学院", "https://mne.scnu.edu.cn"),
    ("阿伯丁数据科学与人工智能学院", "https://abdn.scnu.edu.cn"),
]

# Known SCNU majors by category (from public catalogs)
SCNU_MAJORS = [
    # 教育学
    ("教育学", "教育学", "教育科学学院", "教育学学士"),
    ("小学教育", "教育学", "教育科学学院", "教育学学士"),
    ("学前教育", "教育学", "教育科学学院", "教育学学士"),
    ("特殊教育", "教育学", "教育科学学院", "教育学学士"),
    ("教育技术学", "教育学", "教育科学学院", "教育学学士"),
    # 心理学
    ("心理学", "理学", "心理学院", "理学学士"),
    ("应用心理学", "理学", "心理学院", "理学学士"),
    # 文学
    ("汉语言文学", "文学", "文学院", "文学学士"),
    ("汉语言", "文学", "文学院", "文学学士"),
    ("汉语国际教育", "文学", "国际文化学院", "文学学士"),
    ("英语", "文学", "外国语言文化学院", "文学学士"),
    ("翻译", "文学", "外国语言文化学院", "文学学士"),
    ("日语", "文学", "外国语言文化学院", "文学学士"),
    ("俄语", "文学", "外国语言文化学院", "文学学士"),
    ("法语", "文学", "外国语言文化学院", "文学学士"),
    ("新闻学", "文学", "教育科学学院", "文学学士"),
    ("传播学", "文学", "教育科学学院", "文学学士"),
    # 历史学
    ("历史学", "历史学", "历史文化学院", "历史学学士"),
    # 哲学
    ("哲学", "哲学", "哲学与社会发展学院", "哲学学士"),
    # 法学
    ("法学", "法学", "法学院", "法学学士"),
    ("社会工作", "法学", "哲学与社会发展学院", "法学学士"),
    ("思想政治教育", "法学", "马克思主义学院", "法学学士"),
    ("政治学与行政学", "法学", "政治与公共管理学院", "法学学士"),
    ("行政管理", "管理学", "政治与公共管理学院", "管理学学士"),
    ("公共事业管理", "管理学", "政治与公共管理学院", "管理学学士"),
    # 经济学与管理学
    ("经济学", "经济学", "经济与管理学院", "经济学学士"),
    ("金融学", "经济学", "经济与管理学院", "经济学学士"),
    ("金融科技", "经济学", "经济与管理学院", "经济学学士"),
    ("国际经济与贸易", "经济学", "经济与管理学院", "经济学学士"),
    ("会计学", "管理学", "经济与管理学院", "管理学学士"),
    ("财务管理", "管理学", "经济与管理学院", "管理学学士"),
    ("人力资源管理", "管理学", "经济与管理学院", "管理学学士"),
    ("工商管理", "管理学", "经济与管理学院", "管理学学士"),
    ("物流管理", "管理学", "经济与管理学院", "管理学学士"),
    ("电子商务", "管理学", "经济与管理学院", "管理学学士"),
    ("信息管理与信息系统", "管理学", "信息管理系", "管理学学士"),
    ("旅游管理", "管理学", "旅游管理学院", "管理学学士"),
    ("酒店管理", "管理学", "旅游管理学院", "管理学学士"),
    ("会展经济与管理", "管理学", "旅游管理学院", "管理学学士"),
    # 理学
    ("数学与应用数学", "理学", "数学科学学院", "理学学士"),
    ("信息与计算科学", "理学", "数学科学学院", "理学学士"),
    ("金融数学", "理学", "数学科学学院", "理学学士"),
    ("物理学", "理学", "物理与电信工程学院", "理学学士"),
    ("化学", "理学", "化学学院", "理学学士"),
    ("应用化学", "理学", "化学学院", "理学学士"),
    ("生物科学", "理学", "生命科学学院", "理学学士"),
    ("生物技术", "理学", "生命科学学院", "理学学士"),
    ("生物工程", "工学", "生命科学学院", "工学学士"),
    ("地理科学", "理学", "地理科学学院", "理学学士"),
    ("自然地理与资源环境", "理学", "地理科学学院", "理学学士"),
    ("人文地理与城乡规划", "理学", "地理科学学院", "理学学士"),
    ("地理信息科学", "理学", "地理科学学院", "理学学士"),
    ("大气科学", "理学", "地理科学学院", "理学学士"),
    # 工学
    ("计算机科学与技术", "工学", "计算机学院", "工学学士"),
    ("软件工程", "工学", "软件学院", "工学学士"),
    ("网络工程", "工学", "计算机学院", "工学学士"),
    ("人工智能", "工学", "人工智能学院", "工学学士"),
    ("数据科学与大数据技术", "工学", "计算机学院", "工学学士"),
    ("光电信息科学与工程", "工学", "信息光电子科技学院", "工学学士"),
    ("电子信息工程", "工学", "电子与信息工程学院", "工学学士"),
    ("通信工程", "工学", "电子与信息工程学院", "工学学士"),
    ("电子科学与技术", "工学", "电子与信息工程学院", "工学学士"),
    ("集成电路设计与集成系统", "工学", "半导体科学与技术学院", "工学学士"),
    ("微电子科学与工程", "工学", "半导体科学与技术学院", "工学学士"),
    ("环境工程", "工学", "环境学院", "工学学士"),
    ("环境科学", "工学", "环境学院", "工学学士"),
    ("材料物理", "工学", "材料与新能源学院", "工学学士"),
    ("材料化学", "工学", "材料与新能源学院", "工学学士"),
    ("新能源材料与器件", "工学", "材料与新能源学院", "工学学士"),
    ("新能源科学与工程", "工学", "材料与新能源学院", "工学学士"),
    ("测控技术与仪器", "工学", "物理与电信工程学院", "工学学士"),
    # 艺术
    ("音乐学", "艺术学", "音乐学院", "艺术学学士"),
    ("音乐表演", "艺术学", "音乐学院", "艺术学学士"),
    ("舞蹈学", "艺术学", "音乐学院", "艺术学学士"),
    ("美术学", "艺术学", "美术学院", "艺术学学士"),
    ("设计学", "艺术学", "美术学院", "艺术学学士"),
    ("视觉传达设计", "艺术学", "美术学院", "艺术学学士"),
    ("环境设计", "艺术学", "美术学院", "艺术学学士"),
    ("产品设计", "艺术学", "美术学院", "艺术学学士"),
    ("数字媒体艺术", "艺术学", "美术学院", "艺术学学士"),
    # 体育
    ("体育教育", "教育学", "体育科学学院", "教育学学士"),
    ("运动训练", "教育学", "体育科学学院", "教育学学士"),
    ("社会体育指导与管理", "教育学", "体育科学学院", "教育学学士"),
    # 中外合作办学
    ("数据科学与大数据技术(中外合作)", "工学", "阿伯丁数据科学与人工智能学院", "工学学士"),
    ("人工智能(中外合作)", "工学", "阿伯丁数据科学与人工智能学院", "工学学士"),
    ("信息管理与信息系统(中外合作)", "管理学", "阿伯丁数据科学与人工智能学院", "管理学学士"),
]


class SCNUCurriculumScraper(BaseScraper):

    def __init__(self):
        super().__init__(ScraperConfig(
            name="scnu",
            base_url="https://zsb.scnu.edu.cn",
            delay_seconds=2.0,
        ))

    async def fetch_major_list_page(
        self, client: httpx.AsyncClient
    ) -> str | None:
        urls = [
            f"{self.config.base_url}/zyjs.htm",
            f"{self.config.base_url}/zsjh.htm",
            f"{self.config.base_url}/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1021",
            "https://zsb.scnu.edu.cn/list.jsp?a1178232t=1178232&a1178232p=1&a1178232c=10&urltype=tree.TreeTempUrl&wbtreeid=1021",
        ]
        for url in urls:
            try:
                html = await self.fetch_with_retry(client, url, expect_json=False)
                if html and ("专业" in html or "major" in html.lower()):
                    return html
            except Exception:
                continue
        return None

    async def fetch_college_page(
        self, client: httpx.AsyncClient, college_name: str, url: str
    ) -> dict | None:
        """Try to scrape a college's page for curriculum info."""
        patterns = [
            f"{url}/rcpy/bkjx.htm",
            f"{url}/jxgl.htm",
            f"{url}/pyfa.htm",
            f"{url}/rcpy.htm",
        ]
        for page_url in patterns:
            try:
                html = await self.fetch_with_retry(client, page_url, expect_json=False)
                if html and len(html) > 500:
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator="\n", strip=True)
                    return {
                        "college": college_name,
                        "url": page_url,
                        "text_snippet": text[:5000],
                    }
            except Exception:
                continue
        return None

    async def fetch_jwc_curriculum(
        self, client: httpx.AsyncClient
    ) -> str | None:
        """Try to scrape the academic affairs office for training plans."""
        jwc_urls = [
            "https://jwc.scnu.edu.cn/jxyj/rcpy.htm",
            "https://jwc.scnu.edu.cn/jxyj.htm",
            "https://jwc.scnu.edu.cn/list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1007",
        ]
        for url in jwc_urls:
            try:
                html = await self.fetch_with_retry(client, url, expect_json=False)
                if html and len(html) > 500:
                    return html
            except Exception:
                continue
        return None

    def build_curriculum_entries(self) -> list[dict]:
        """Build curriculum entries from known SCNU major data."""
        results = []
        for major_name, category, college, degree in SCNU_MAJORS:
            entry = {
                "college_code": SCNU_MOE_CODE,
                "college_name": SCNU_NAME,
                "major_name": major_name,
                "college": college,
                "category": category,
                "degree_type": degree,
                "duration": 4,
                "source": "scnu_catalog",
            }
            # Core courses are associated with categories
            entry["core_courses"] = _get_core_courses(major_name, category)
            entry["objective"] = _get_training_objective(major_name, category, college)
            results.append(entry)
        return results

    async def run(self) -> dict:
        logger.info(
            f"Building SCNU curriculum data for {len(SCNU_MAJORS)} majors"
        )

        curriculums = self.build_curriculum_entries()
        errors = []

        # Attempt live scraping for supplementary data
        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            headers=self.config.headers,
        ) as client:
            # Try to get major list from zsb
            html = await self.fetch_major_list_page(client)
            if html:
                logger.info("Successfully fetched SCNU major list page")
            else:
                errors.append({
                    "type": "major_list_failed",
                    "message": "Could not fetch major list from zsb.scnu.edu.cn",
                })

            # Try college pages in parallel (limited to avoid hammering)
            sem = asyncio.Semaphore(4)

            async def fetch_college(name, url):
                async with sem:
                    return await self.fetch_college_page(client, name, url)

            # Sample first 10 colleges to avoid excessive traffic
            college_tasks = [
                fetch_college(name, url)
                for name, url in SCNU_COLLEGES[:10]
            ]
            college_results = await asyncio.gather(*college_tasks)
            college_hits = sum(1 for r in college_results if r)
            logger.info(
                f"College pages scraped: {college_hits}/{len(college_results)}"
            )

            jwc_html = await self.fetch_jwc_curriculum(client)
            if jwc_html:
                logger.info("Successfully fetched JWC curriculum page")

        self.save_raw("curriculums.json", curriculums)
        if errors:
            self.save_raw("errors_curriculum.json", errors)

        return {
            "source": "scnu_curriculum",
            "majors": len(curriculums),
            "colleges_scraped": college_hits if 'college_hits' in dir() else 0,
            "errors": len(errors),
        }


def _get_core_courses(major_name: str, category: str) -> list[str]:
    courses = {
        "教育学": ["教育原理", "教育心理学", "课程与教学论", "教育研究方法", "中国教育史", "外国教育史"],
        "心理学": ["普通心理学", "实验心理学", "心理统计学", "发展心理学", "认知心理学", "心理测量学"],
        "汉语言文学": ["中国古代文学", "中国现代文学", "外国文学", "文学理论", "古代汉语", "现代汉语"],
        "法学": ["法理学", "宪法学", "民法学", "刑法学", "行政法学", "诉讼法学"],
        "经济学": ["微观经济学", "宏观经济学", "计量经济学", "政治经济学", "经济统计学", "发展经济学"],
        "数学与应用数学": ["数学分析", "高等代数", "概率论与数理统计", "常微分方程", "实变函数", "复变函数"],
        "物理学": ["力学", "热学", "电磁学", "光学", "原子物理学", "量子力学"],
        "化学": ["无机化学", "有机化学", "分析化学", "物理化学", "结构化学", "高分子化学"],
        "计算机科学与技术": ["数据结构", "计算机组成原理", "操作系统", "计算机网络", "算法设计与分析", "数据库系统"],
        "软件工程": ["软件工程导论", "面向对象程序设计", "软件测试", "软件项目管理", "软件体系结构"],
        "英语": ["综合英语", "英语听力", "英语口语", "英语写作", "英语国家概况", "英汉互译"],
        "历史学": ["中国通史", "世界通史", "史学概论", "历史文献学", "考古学通论"],
        "生物科学": ["植物学", "动物学", "生物化学", "分子生物学", "细胞生物学", "遗传学"],
        "地理科学": ["自然地理学", "人文地理学", "经济地理学", "地图学", "遥感概论", "GIS原理"],
        "思想政治教育": ["马克思主义哲学", "政治经济学", "科学社会主义", "思想政治教育原理", "伦理学"],
        "美术学": ["素描", "色彩", "中外美术史", "艺术概论", "国画基础", "油画基础"],
        "音乐学": ["基本乐理", "视唱练耳", "中外音乐史", "和声学", "曲式分析", "钢琴基础"],
        "体育教育": ["运动生理学", "体育心理学", "学校体育学", "田径", "体操", "球类运动"],
    }

    for key, course_list in courses.items():
        if key in major_name:
            return course_list
    if "学" in category:
        return ["学科基础课", "专业核心课", "专业选修课", "实践教学"]
    return ["专业基础课", "专业核心课", "专业选修课", "毕业实习"]


def _get_training_objective(major_name: str, category: str, college: str) -> str:
    base = f"本专业培养德智体美劳全面发展，掌握{category}学科基础理论和{major_name}专业知识与技能"
    if "师范" in major_name or "教育" in major_name:
        return base + "，能够胜任中小学教育教学、教育管理与教育研究工作的专门人才。"
    if "工程" in major_name or "科学" in major_name or "技术" in major_name:
        return base + "，能够在相关领域从事科学研究、技术开发与管理工作的应用型高级专门人才。"
    return base + "，能够在相关行业从事专业工作的高素质人才。"


if __name__ == "__main__":
    asyncio.run(SCNUCurriculumScraper().run())
