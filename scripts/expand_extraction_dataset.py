import json, pathlib

entries = []
next_id = 1

def add(basic, msgs, interests, strong, riasec, values, region):
    global next_id
    conv = []
    for u, a in msgs:
        conv.append({"role":"user","content":u})
        conv.append({"role":"assistant","content":a})
    r = region if region else {"province":"","city":""}
    entries.append({
        "id": f"pe_{next_id:03d}",
        "conversation": conv,
        "expected_extraction": {
            "basic": {"province":basic.get("province",""),"subject_type":basic.get("subject_type",""),"score":basic.get("score",0)},
            "interests": {"preferred_subjects":interests,"strong_subjects":strong,"hobbies":[]},
            "concerns": [],
            "riasec": {"R":riasec.get("R",0),"I":riasec.get("I",0),"A":riasec.get("A",0),"S":riasec.get("S",0),"E":riasec.get("E",0),"C":riasec.get("C",0)},
            "values": values,
            "region_pref": r,
            "extra": {}
        }
    })
    next_id += 1

# Basic info (15)
add({"province":"广东","subject_type":"物理类","score":620}, [("广东物理类620分","不错"), ("对计算机和软件感兴趣","好方向")], ["计算机","软件工程"], [], {}, [], {})
add({"province":"湖南","subject_type":"历史类","score":565}, [("湖南历史类565","了解"), ("想去师范","很适合")], ["师范"], [], {}, [], {})
add({"province":"浙江","subject_type":"物理类","score":645}, [("浙江物理化学地理645分","优秀"), ("想学医","医学有前景")], ["临床医学"], ["物理","化学","地理"], {}, [], {})
add({"province":"四川","subject_type":"物理类","score":530}, [("四川理科530","了解"), ("喜欢动手做东西","动手型")], [], [], {"R":6}, [], {})
add({"province":"河南","subject_type":"物理类","score":580}, [("河南理科580","了解"), ("对电子信息有兴趣","好方向")], ["电子信息工程"], [], {}, [], {})
add({"province":"江苏","subject_type":"物理类","score":610}, [("江苏物理类610","不错"), ("比较迷茫不知学什么","慢慢聊")], [], [], {}, ["专业选择迷茫"], {})
add({"province":"湖北","subject_type":"历史类","score":575}, [("湖北历史类575","了解"), ("想学法学","法学不错")], ["法学"], [], {}, [], {})
add({"province":"山东","subject_type":"物理类","score":635}, [("山东理科635","优秀"), ("喜欢数学和物理","基础好")], ["数学"], ["数学","物理"], {"I":7}, [], {})
add({"province":"北京","subject_type":"物理类","score":555}, [("北京理科555","北京考生"), ("想学机械","机械工程")], ["机械工程"], [], {"R":6}, [], {})
add({"province":"上海","subject_type":"历史类","score":588}, [("上海历史类588","了解"), ("对新闻传播感兴趣","热门")], ["新闻传播"], [], {}, [], {"province":"上海"})
add({"province":"福建","subject_type":"物理类","score":598}, [("福建理科598","了解"), ("想报土木","土木工程")], ["土木工程"], [], {}, [], {})
add({"province":"安徽","subject_type":"历史类","score":582}, [("安徽历史类582","了解"), ("想学英语","需要积累")], ["英语"], [], {}, [], {})
add({"province":"江西","subject_type":"物理类","score":572}, [("江西理科572","了解"), ("想学材料科学","基础学科")], ["材料"], [], {}, [], {})
add({"province":"重庆","subject_type":"物理类","score":605}, [("重庆理科605","不错"), ("人工智能方向","热门")], ["人工智能"], [], {}, [], {})
add({"province":"广西","subject_type":"历史类","score":562}, [("广西历史类562","了解"), ("想学会计","实用")], ["会计学"], [], {}, ["工作稳定"], {})

# RIASEC (15)
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","兴趣？"), ("喜欢写代码做项目，参加过竞赛","编程强")], ["计算机"], [], {"I":8,"C":6}, [], {})
add({"province":"广东","subject_type":"历史类","score":570}, [("广东历史类570","方向？"), ("喜欢帮别人做志愿者想当老师","有意义")], ["师范"], [], {"S":8}, ["社会贡献"], {})
add({"province":"浙江","subject_type":"物理类","score":610}, [("浙江物理类610","兴趣？"), ("喜欢修理电器研究数学难题","动手强")], [], [], {"R":7,"I":7}, [], {})
add({"province":"湖南","subject_type":"历史类","score":585}, [("湖南历史类585","方向？"), ("喜欢画画设计父母希望学会计","纠结中")], [], [], {"A":7,"C":4}, ["个人成长"], {})
add({"province":"四川","subject_type":"物理类","score":560}, [("四川物理类560","兴趣？"), ("学生会部长喜欢组织活动","领导型")], [], [], {"E":8,"S":5}, ["社会贡献"], {})
add({"province":"河南","subject_type":"物理类","score":590}, [("河南物理类590","兴趣？"), ("做事有条理喜欢整理","条理型")], [], ["数学"], {"C":8,"I":5}, [], {})
add({"province":"湖北","subject_type":"历史类","score":595}, [("湖北历史类595","方向？"), ("喜欢写作阅读文学社成员","文艺")], [], [], {"A":7}, ["个人成长"], {})
add({"province":"江苏","subject_type":"物理类","score":625}, [("江苏物理类625","很强"), ("机器人竞赛拿奖也喜欢分析数据","全面")], [], ["物理","数学"], {"R":7,"I":8,"C":5}, [], {})
add({"province":"福建","subject_type":"物理类","score":575}, [("福建物理类575","兴趣？"), ("喜欢和人打交道也喜欢研究","均衡")], [], [], {"S":6,"I":6}, [], {})
add({"province":"山东","subject_type":"历史类","score":580}, [("山东历史类580","方向？"), ("想学新闻做记者沟通重要","明确")], ["新闻"], [], {"A":5,"E":5,"S":5}, ["社会贡献"], {})
add({"province":"安徽","subject_type":"物理类","score":555}, [("安徽物理类555","兴趣？"), ("喜欢打篮球和生物实验","广泛")], [], ["生物学"], {"R":5,"I":5}, [], {})
add({"province":"江西","subject_type":"历史类","score":568}, [("江西历史类568","方向？"), ("想做管理有领导力","管理型")], [], [], {"E":7,"S":6}, [], {})
add({"province":"重庆","subject_type":"物理类","score":605}, [("重庆物理类605","兴趣？"), ("对新能源环保感兴趣","有远见")], ["环境科学"], [], {"I":6,"R":4}, ["社会贡献"], {})
add({"province":"广东","subject_type":"物理类","score":588}, [("广东物理类588","兴趣？"), ("喜欢做实验对化学感兴趣","研究型")], ["化学"], [], {"I":7,"R":6}, ["学术氛围"], {})
add({"province":"浙江","subject_type":"历史类","score":592}, [("浙江历史类592","方向？"), ("想学法律做律师喜欢辩论","清晰")], ["法学"], [], {"E":6,"C":5,"I":5}, ["薪资水平"], {})

# Values (10)
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("工作稳定很重要","务实")], [], [], {}, ["工作稳定"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("希望工资高给家里减负","担当")], [], [], {}, ["薪资水平"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("想做对社会有贡献的事","理想")], [], [], {}, ["社会贡献"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("希望有挑战能不断成长","上进")], [], [], {}, ["个人成长"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("专业要对口不能浪费","务实")], [], [], {}, ["专业对口"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("想工作生活能平衡","规划")], [], [], {}, ["工作生活平衡"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("想去创新型企业","追求")], [], [], {}, ["创新机会"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("学术氛围很重要","环境")], [], [], {}, ["学术氛围"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("想留在家乡发展","念家")], [], [], {}, ["地域偏好"], {})
add({"province":"广东","subject_type":"物理类","score":600}, [("广东物理类600","看重什么？"), ("能做喜欢的事也帮到别人","情怀")], [], [], {}, ["个人成长","社会贡献"], {})

# Region (5)
add({"province":"广东","subject_type":"历史类","score":580}, [("广东历史类580","想去哪里？"), ("想留在广东最好在广州","本地")], [], [], {}, [], {"province":"广东","city":"广州"})
add({"province":"广东","subject_type":"历史类","score":580}, [("广东历史类580","想去哪里？"), ("想去北京或者上海","大城市")], [], [], {}, [], {"province":"北京","city":"上海"})
add({"province":"广东","subject_type":"历史类","score":580}, [("广东历史类580","想去哪里？"), ("不想离家太远就在省内","就近")], [], [], {}, [], {"province":"广东","city":""})
add({"province":"广东","subject_type":"历史类","score":580}, [("广东历史类580","想去哪里？"), ("想去江浙沪那边","长三角")], [], [], {}, [], {"province":"江苏","city":"上海"})
add({"province":"广东","subject_type":"历史类","score":580}, [("广东历史类580","想去哪里？"), ("无所谓去哪里学校好就行","开放")], [], [], {}, [], {"province":"","city":""})

with open("backend/tests/benchmarks/profile_extraction.json", "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)
print(f"Written {len(entries)} profile extraction pairs")
