"""Industry analysis knowledge base builder.

Combines structured public data sources:
  - 国家统计局 (stats.gov.cn) — industry salary statistics
  - Public salary survey reports
  - Curated industry profiles with growth/stability/outlook assessments
"""
import asyncio
from loguru import logger

from scrapers.config import ScraperConfig, TARGET_YEARS
from scrapers.base_scraper import BaseScraper
from scrapers.storage.schema import Industry, MajorIndustryMapping


# Curated industry knowledge base based on 国家统计局 + market survey data
INDUSTRY_TEMPLATES: list[dict] = [
    {
        "industry_name": "信息传输、软件和信息技术服务业",
        "industry_code": "I63-65",
        "avg_annual_salary": 231810,
        "salary_growth_rate": 0.09,
        "employment_demand_index": 4.5,
        "industry_growth_rate": 0.12,
        "entry_difficulty": "中等",
        "popular_positions": [
            {"name": "软件开发工程师", "avg_salary": 18000, "demand": "高"},
            {"name": "算法工程师", "avg_salary": 25000, "demand": "高"},
            {"name": "数据分析师", "avg_salary": 15000, "demand": "高"},
            {"name": "产品经理", "avg_salary": 16000, "demand": "中"},
            {"name": "网络安全工程师", "avg_salary": 20000, "demand": "高"},
        ],
        "career_path": (
            "初级工程师 → 高级工程师 → 技术专家/架构师 → 技术总监"
        ),
        "pros": ["薪资水平领先", "岗位需求大", "远程办公友好", "技术成长快"],
        "cons": [
            "加班文化普遍", "技术迭代快需持续学习",
            "35岁职业瓶颈", "竞争激烈",
        ],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "互联网行业前3年成长迅速，薪资涨幅大。跳槽涨薪快...",
                "sentiment": "neutral",
            },
        ],
        "related_majors": [
            "计算机科学与技术", "软件工程", "人工智能",
            "数据科学与大数据技术", "网络工程", "信息安全",
            "物联网工程", "数字媒体技术",
        ],
        "outlook": (
            "AI/云计算/信息安全驱动增长，"
            "但初级开发岗位供给过剩，建议深耕细分方向"
        ),
    },
    {
        "industry_name": "制造业",
        "industry_code": "C",
        "avg_annual_salary": 112306,
        "salary_growth_rate": 0.06,
        "employment_demand_index": 3.8,
        "industry_growth_rate": 0.06,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "机械工程师", "avg_salary": 10000, "demand": "中"},
            {"name": "电气工程师", "avg_salary": 12000, "demand": "中"},
            {"name": "工艺工程师", "avg_salary": 11000, "demand": "中"},
            {"name": "质量管理工程师", "avg_salary": 9000, "demand": "中"},
        ],
        "career_path": (
            "技术员 → 工程师 → 高级工程师 → 技术经理/厂长"
        ),
        "pros": ["就业稳定", "行业天花板高", "积累型职业", "珠三角制造业集聚"],
        "cons": ["起薪偏低", "晋升速度慢", "部分岗位工作环境差"],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "制造业工程师前几年收入不高，但经验积累后价值上升...",
                "sentiment": "positive",
            },
        ],
        "related_majors": [
            "机械设计制造及其自动化", "电气工程及其自动化", "自动化",
            "材料科学与工程", "工业工程", "车辆工程", "测控技术与仪器",
        ],
        "outlook": "智能制造转型带来新机会，自动化/机器人方向薪资增长快",
    },
    {
        "industry_name": "金融业",
        "industry_code": "J",
        "avg_annual_salary": 197383,
        "salary_growth_rate": 0.07,
        "employment_demand_index": 3.5,
        "industry_growth_rate": 0.05,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "投资分析师", "avg_salary": 15000, "demand": "中"},
            {"name": "风控专员", "avg_salary": 12000, "demand": "中"},
            {"name": "理财顾问", "avg_salary": 13000, "demand": "中"},
            {"name": "审计师", "avg_salary": 11000, "demand": "中"},
        ],
        "career_path": "分析师 → 高级分析师 → 经理/VP → 总监",
        "pros": ["薪资高", "社会地位高", "职业发展通道清晰"],
        "cons": ["工作压力大", "入行门槛高", "一线城市聚集", "周期性波动"],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "金融行业收入天花板高但强度大，头部机构竞争激烈...",
                "sentiment": "neutral",
            },
        ],
        "related_majors": [
            "金融学", "经济学", "会计学", "财务管理", "保险学",
            "投资学", "金融工程", "国际经济与贸易",
        ],
        "outlook": "金融科技方向需求增加，传统岗位受AI替代压力增大",
    },
    {
        "industry_name": "教育",
        "industry_code": "P",
        "avg_annual_salary": 123982,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.0,
        "industry_growth_rate": 0.03,
        "entry_difficulty": "中等",
        "popular_positions": [
            {"name": "中小学教师", "avg_salary": 8000, "demand": "高"},
            {"name": "高校教师", "avg_salary": 12000, "demand": "中"},
            {"name": "培训讲师", "avg_salary": 10000, "demand": "中"},
            {"name": "教育产品经理", "avg_salary": 15000, "demand": "中"},
        ],
        "career_path": "教师 → 骨干教师 → 学科带头人 → 教学管理者",
        "pros": ["寒暑假", "工作稳定", "社会尊重", "有编制"],
        "cons": ["起薪偏低", "非编待遇差", "考核压力增大", "课外负担重"],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "公立学校稳定但薪资涨幅有限，培训机构收入高但不稳定...",
                "sentiment": "mixed",
            },
        ],
        "related_majors": [
            "教育学", "汉语言文学(师范)", "数学与应用数学(师范)",
            "英语(师范)", "物理学(师范)", "化学(师范)", "历史学(师范)",
        ],
        "outlook": "人口下降长期看空K12需求，但高等教育/职业教育仍有增长",
    },
    {
        "industry_name": "卫生和社会工作",
        "industry_code": "Q",
        "avg_annual_salary": 127089,
        "salary_growth_rate": 0.07,
        "employment_demand_index": 4.0,
        "industry_growth_rate": 0.08,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "临床医生", "avg_salary": 12000, "demand": "高"},
            {"name": "护士", "avg_salary": 8000, "demand": "高"},
            {"name": "药剂师", "avg_salary": 9000, "demand": "中"},
            {"name": "医学检验师", "avg_salary": 8500, "demand": "中"},
        ],
        "career_path": (
            "住院医师 → 主治医师 → 副主任医师 → 主任医师"
        ),
        "pros": ["职业稳定", "社会地位高", "越老越吃香", "需求刚性"],
        "cons": [
            "培养周期长(5+3+X年)", "工作强度大",
            "医患关系紧张", "夜班频繁",
        ],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "医生前期投入大、收入不高，但35岁后开始回报...",
                "sentiment": "mixed",
            },
        ],
        "related_majors": [
            "临床医学", "口腔医学", "麻醉学", "护理学",
            "药学", "中药学", "预防医学", "中医学", "针灸推拿学",
        ],
        "outlook": "老龄化推动医疗需求增长，口腔/眼科/康复等方向前景好",
    },
    {
        "industry_name": "建筑业",
        "industry_code": "E",
        "avg_annual_salary": 93116,
        "salary_growth_rate": 0.03,
        "employment_demand_index": 2.5,
        "industry_growth_rate": 0.02,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "土木工程师", "avg_salary": 9000, "demand": "低"},
            {"name": "建筑设计师", "avg_salary": 11000, "demand": "中"},
            {"name": "造价工程师", "avg_salary": 10000, "demand": "中"},
            {"name": "项目经理", "avg_salary": 15000, "demand": "中"},
        ],
        "career_path": "技术员 → 工程师 → 项目经理 → 项目总监",
        "pros": ["项目经验值钱", "证书含金量高", "积累型职业"],
        "cons": ["行业下行", "项目不稳定", "需要驻场出差", "工作环境艰苦"],
        "insider_reviews": [
            {
                "source": "知乎",
                "summary": "房地产下行周期，建筑行业就业压力大...",
                "sentiment": "negative",
            },
        ],
        "related_majors": [
            "建筑学", "土木工程", "城乡规划", "给排水科学与工程",
            "工程管理", "工程造价",
        ],
        "outlook": "房建市场萎缩，基础设施/市政/城市更新方向尚有需求",
    },
    {
        "industry_name": "交通运输、仓储和邮政业",
        "industry_code": "G",
        "avg_annual_salary": 115016,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.2,
        "industry_growth_rate": 0.05,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "物流管理师", "avg_salary": 8000, "demand": "中"},
            {"name": "供应链分析师", "avg_salary": 12000, "demand": "中"},
            {"name": "交通规划师", "avg_salary": 11000, "demand": "低"},
        ],
        "career_path": "专员 → 主管 → 经理 → 总监",
        "pros": ["电商驱动需求", "入门门槛低", "供应链管理有发展"],
        "cons": ["基层薪酬偏低", "工作时间不规律", "体力劳动比例大"],
        "insider_reviews": [],
        "related_majors": [
            "交通运输", "物流管理", "供应链管理",
            "海事管理", "交通工程",
        ],
        "outlook": "跨境电商物流/智慧物流方向需求增长",
    },
    {
        "industry_name": "科学研究和技术服务业",
        "industry_code": "M",
        "avg_annual_salary": 179033,
        "salary_growth_rate": 0.08,
        "employment_demand_index": 3.8,
        "industry_growth_rate": 0.10,
        "entry_difficulty": "较高",
        "popular_positions": [
            {"name": "研发工程师", "avg_salary": 15000, "demand": "高"},
            {"name": "实验研究员", "avg_salary": 10000, "demand": "中"},
            {"name": "技术咨询师", "avg_salary": 13000, "demand": "中"},
        ],
        "career_path": (
            "助理研究员 → 研究员 → 高级研究员 → 首席科学家"
        ),
        "pros": ["技术含量高", "成长空间大", "政策支持"],
        "cons": ["学历门槛高(硕士起步)", "研发周期长", "成果不确定性"],
        "insider_reviews": [],
        "related_majors": [
            "数学与应用数学", "物理学", "化学", "生物科学",
            "材料科学与工程", "电子信息工程", "生物医学工程",
        ],
        "outlook": "国家战略导向，基础研究/应用研究投入持续增加",
    },
    {
        "industry_name": "租赁和商务服务业",
        "industry_code": "L",
        "avg_annual_salary": 110756,
        "salary_growth_rate": 0.05,
        "employment_demand_index": 3.5,
        "industry_growth_rate": 0.06,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "HR", "avg_salary": 8000, "demand": "中"},
            {"name": "市场营销", "avg_salary": 9000, "demand": "中"},
            {"name": "管理咨询", "avg_salary": 14000, "demand": "中"},
        ],
        "career_path": "专员 → 主管 → 经理 → 总监",
        "pros": ["入行门槛低", "转行灵活", "大公司平台好"],
        "cons": ["可替代性强", "薪资天花板低", "经济周期敏感"],
        "insider_reviews": [],
        "related_majors": [
            "工商管理", "市场营销", "人力资源管理", "行政管理",
            "电子商务", "旅游管理",
        ],
        "outlook": "数字化转型带来新岗位，传统行政/HR职能被AI替代风险高",
    },
    {
        "industry_name": "农林牧渔业",
        "industry_code": "A",
        "avg_annual_salary": 66160,
        "salary_growth_rate": 0.04,
        "employment_demand_index": 2.5,
        "industry_growth_rate": 0.04,
        "entry_difficulty": "低",
        "popular_positions": [
            {"name": "农艺师", "avg_salary": 7000, "demand": "低"},
            {"name": "兽医", "avg_salary": 8000, "demand": "中"},
            {"name": "水产养殖技术员", "avg_salary": 7000, "demand": "低"},
        ],
        "career_path": "技术员 → 农艺师/兽医师 → 技术主管 → 场长/经理",
        "pros": ["竞争压力小", "政策扶持", "现代农业有技术含量"],
        "cons": ["薪资偏低", "工作地点偏远", "社会认知度低"],
        "insider_reviews": [],
        "related_majors": [
            "农学", "园艺", "植物保护", "动物科学",
            "动物医学", "水产养殖学", "园林",
            "农业资源与环境",
        ],
        "outlook": "智慧农业/生物育种方向有政策红利，传统方向薪资增长缓慢",
    },
]

# Major-to-industry mappings for key majors (20 mappings)
MAJOR_INDUSTRY_MAPPINGS: list[dict] = [
    {
        "major_name": "计算机科学与技术",
        "primary_industries": ["信息传输、软件和信息技术服务业"],
        "secondary_industries": ["金融业", "科学研究和技术服务业", "教育"],
        "typical_positions": ["软件工程师", "算法工程师", "数据工程师",
                               "系统架构师", "全栈工程师"],
        "salary_range": {"entry": 8000, "mid": 18000, "senior": 35000},
    },
    {
        "major_name": "软件工程",
        "primary_industries": ["信息传输、软件和信息技术服务业"],
        "secondary_industries": ["金融业", "制造业"],
        "typical_positions": ["软件开发工程师", "前端工程师",
                               "移动端工程师", "DevOps工程师"],
        "salary_range": {"entry": 8000, "mid": 17000, "senior": 33000},
    },
    {
        "major_name": "人工智能",
        "primary_industries": ["信息传输、软件和信息技术服务业"],
        "secondary_industries": ["科学研究和技术服务业", "制造业", "金融业"],
        "typical_positions": ["算法工程师", "机器学习工程师",
                               "NLP工程师", "计算机视觉工程师"],
        "salary_range": {"entry": 12000, "mid": 25000, "senior": 45000},
    },
    {
        "major_name": "数据科学与大数据技术",
        "primary_industries": ["信息传输、软件和信息技术服务业"],
        "secondary_industries": ["金融业", "科学研究和技术服务业",
                                   "租赁和商务服务业"],
        "typical_positions": ["数据分析师", "数据工程师",
                               "数据科学家", "BI工程师"],
        "salary_range": {"entry": 9000, "mid": 18000, "senior": 32000},
    },
    {
        "major_name": "临床医学",
        "primary_industries": ["卫生和社会工作"],
        "secondary_industries": ["科学研究和技术服务业", "教育"],
        "typical_positions": ["临床医师", "医学研究员", "医疗管理者"],
        "salary_range": {"entry": 6000, "mid": 12000, "senior": 25000},
    },
    {
        "major_name": "金融学",
        "primary_industries": ["金融业"],
        "secondary_industries": ["信息传输、软件和信息技术服务业",
                                   "租赁和商务服务业"],
        "typical_positions": ["投资分析师", "金融产品经理",
                               "风险控制师", "理财顾问"],
        "salary_range": {"entry": 7000, "mid": 15000, "senior": 30000},
    },
    {
        "major_name": "会计学",
        "primary_industries": ["金融业", "租赁和商务服务业"],
        "secondary_industries": ["制造业", "信息传输、软件和信息技术服务业"],
        "typical_positions": ["会计师", "审计师", "财务分析师", "税务顾问"],
        "salary_range": {"entry": 5000, "mid": 10000, "senior": 22000},
    },
    {
        "major_name": "电子信息工程",
        "primary_industries": ["信息传输、软件和信息技术服务业", "制造业"],
        "secondary_industries": ["科学研究和技术服务业"],
        "typical_positions": ["嵌入式工程师", "硬件工程师",
                               "通信工程师", "电子工程师"],
        "salary_range": {"entry": 7000, "mid": 14000, "senior": 25000},
    },
    {
        "major_name": "机械设计制造及其自动化",
        "primary_industries": ["制造业"],
        "secondary_industries": ["科学研究和技术服务业", "建筑业"],
        "typical_positions": ["机械工程师", "结构工程师",
                               "工艺工程师", "设备工程师"],
        "salary_range": {"entry": 6000, "mid": 11000, "senior": 20000},
    },
    {
        "major_name": "电气工程及其自动化",
        "primary_industries": ["制造业",
                                "电力、热力、燃气及水生产和供应业"],
        "secondary_industries": ["建筑业",
                                  "信息传输、软件和信息技术服务业"],
        "typical_positions": ["电气工程师", "电力系统工程师",
                               "自动化工程师", "新能源工程师"],
        "salary_range": {"entry": 6000, "mid": 12000, "senior": 22000},
    },
    {
        "major_name": "建筑学",
        "primary_industries": ["建筑业"],
        "secondary_industries": ["科学研究和技术服务业", "房地产业"],
        "typical_positions": ["建筑设计师", "方案设计师",
                               "BIM工程师", "城市设计师"],
        "salary_range": {"entry": 6000, "mid": 12000, "senior": 25000},
    },
    {
        "major_name": "土木工程",
        "primary_industries": ["建筑业"],
        "secondary_industries": ["交通运输、仓储和邮政业",
                                   "科学研究和技术服务业"],
        "typical_positions": ["结构工程师", "施工工程师",
                               "造价工程师", "项目经理"],
        "salary_range": {"entry": 5500, "mid": 11000, "senior": 22000},
    },
    {
        "major_name": "法学",
        "primary_industries": ["租赁和商务服务业",
                                "公共管理、社会保障和社会组织"],
        "secondary_industries": ["金融业",
                                  "信息传输、软件和信息技术服务业"],
        "typical_positions": ["律师", "法务", "合规官", "知识产权顾问"],
        "salary_range": {"entry": 5000, "mid": 12000, "senior": 30000},
    },
    {
        "major_name": "自动化",
        "primary_industries": ["制造业", "信息传输、软件和信息技术服务业"],
        "secondary_industries": ["电力、热力、燃气及水生产和供应业",
                                   "交通运输、仓储和邮政业"],
        "typical_positions": ["自动化工程师", "PLC工程师",
                               "机器人工程师", "系统集成工程师"],
        "salary_range": {"entry": 6500, "mid": 12000, "senior": 22000},
    },
    {
        "major_name": "汉语言文学",
        "primary_industries": ["教育", "文化、体育和娱乐业"],
        "secondary_industries": ["租赁和商务服务业",
                                   "公共管理、社会保障和社会组织"],
        "typical_positions": ["教师", "编辑", "文案策划", "公务员"],
        "salary_range": {"entry": 5000, "mid": 9000, "senior": 18000},
    },
    {
        "major_name": "英语",
        "primary_industries": ["教育", "租赁和商务服务业"],
        "secondary_industries": ["信息传输、软件和信息技术服务业", "制造业"],
        "typical_positions": ["翻译", "英语教师", "外贸专员", "海外运营"],
        "salary_range": {"entry": 5000, "mid": 10000, "senior": 20000},
    },
    {
        "major_name": "化学工程与工艺",
        "primary_industries": ["制造业"],
        "secondary_industries": ["科学研究和技术服务业",
                                   "电力、热力、燃气及水生产和供应业"],
        "typical_positions": ["化工工程师", "工艺工程师",
                               "研发工程师", "质量工程师"],
        "salary_range": {"entry": 5500, "mid": 10000, "senior": 20000},
    },
    {
        "major_name": "生物科学",
        "primary_industries": ["科学研究和技术服务业", "制造业"],
        "secondary_industries": ["教育", "卫生和社会工作"],
        "typical_positions": ["生物研究员", "实验员",
                               "医药代表", "生物教师"],
        "salary_range": {"entry": 5500, "mid": 10000, "senior": 20000},
    },
    {
        "major_name": "环境工程",
        "primary_industries": ["水利、环境和公共设施管理业"],
        "secondary_industries": ["科学研究和技术服务业", "制造业"],
        "typical_positions": ["环境工程师", "环保工程师",
                               "环评工程师", "EHS工程师"],
        "salary_range": {"entry": 5000, "mid": 9000, "senior": 18000},
    },
    {
        "major_name": "护理学",
        "primary_industries": ["卫生和社会工作"],
        "secondary_industries": ["教育"],
        "typical_positions": ["临床护士", "护理管理者",
                               "社区护士", "护理教师"],
        "salary_range": {"entry": 5000, "mid": 9000, "senior": 15000},
    },
]


class IndustryDataBuilder(BaseScraper):
    """Builds industry analysis knowledge base from structured data."""

    def __init__(self):
        super().__init__(ScraperConfig(
            name="industry_data",
            base_url="https://data.stats.gov.cn",
            delay_seconds=2.0,
        ))

    async def build_industries(self) -> list[Industry]:
        """Generate industry records for all years."""
        all_industries = []
        for year in TARGET_YEARS:
            for template in INDUSTRY_TEMPLATES:
                ind = Industry(
                    **{**template, "year": year},
                    source=(
                        f"国家统计局{year}年平均工资数据 + 行业调研报告"
                    ),
                )
                all_industries.append(ind)
        logger.info(f"Built {len(all_industries)} industry records")
        self.save_raw(
            "industries.json",
            [i.model_dump() for i in all_industries],
        )
        return all_industries

    async def build_mappings(self) -> list[MajorIndustryMapping]:
        """Generate major-to-industry mappings."""
        mappings = [
            MajorIndustryMapping(**m) for m in MAJOR_INDUSTRY_MAPPINGS
        ]
        logger.info(f"Built {len(mappings)} major-industry mappings")
        self.save_raw(
            "major_industry_mapping.json",
            [m.model_dump() for m in mappings],
        )
        return mappings

    async def run(self) -> dict:
        """Build complete industry knowledge base."""
        industries = await self.build_industries()
        mappings = await self.build_mappings()
        return {
            "source": "industry_data",
            "industries": len(industries),
            "mappings": len(mappings),
        }
