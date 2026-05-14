#!/usr/bin/env python3
"""Collect multi-province admission scores for Beijing & Shanghai universities."""
import asyncio, json, sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# All Chinese provinces
PROVINCES = {
    11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江",
    31: "上海", 32: "江苏", 33: "浙江", 34: "安徽", 35: "福建",
    36: "江西", 37: "山东",
    41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西", 46: "海南",
    50: "重庆", 51: "四川", 52: "贵州", 53: "云南", 54: "西藏",
    61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏", 65: "新疆",
}
YEARS = [2021, 2022, 2023, 2024]
CONCURRENCY = 10
API_BASE = "https://static-data.gaokao.cn/www/2.0/schoolspecialscore"


async def collect_schools(school_map: dict, label: str):
    """Collect scores for all schools in map across all provinces and years."""
    import httpx

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "Referer": "https://gkcx.eol.cn/",
    }

    sem = asyncio.Semaphore(CONCURRENCY)
    all_records = []
    total = len(school_map) * len(PROVINCES) * len(YEARS)
    done = [0]

    async def fetch_one(pid, name, year, prov_id, prov_name):
        async with sem:
            url = f"{API_BASE}/{pid}/{year}/{prov_id}.json"
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(url, headers=headers)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    records = []
                    for batch_data in (data.values() if isinstance(data, dict) else []):
                        if not isinstance(batch_data, dict):
                            continue
                        for item in batch_data.get("item", []):
                            records.append({
                                "platform_id": str(pid),
                                "school_name": name,
                                "major_name": item.get("sp_name", ""),
                                "major_group": item.get("sg_name", ""),
                                "year": year,
                                "province": prov_name,
                                "province_id": prov_id,
                                "batch": item.get("local_batch_name", ""),
                                "subject_requirements": item.get("sg_info", ""),
                                "plan_count": item.get("lq_num"),
                                "min_score": item.get("min"),
                                "min_rank": item.get("min_section"),
                                "avg_score": item.get("average"),
                                "max_score": item.get("max"),
                                "source_url": url,
                            })
                    return records
            except Exception:
                pass
            return []

    async def tracked_fetch(pid, name, year, prov_id, prov_name):
        result = await fetch_one(pid, name, year, prov_id, prov_name)
        done[0] += 1
        if done[0] % 500 == 0:
            pct = done[0] / total * 100
            speed = done[0] / (time.time() - t0) if time.time() - t0 > 0 else 0
            eta = (total - done[0]) / speed if speed > 0 else 0
            print(f"  [{label}] {done[0]}/{total} ({pct:.0f}%) {len(all_records)} records eta={eta/60:.0f}m", flush=True)
        return []

    tasks = []
    for pid, (name, code_id) in school_map.items():
        for year in YEARS:
            for prov_id, prov_name in PROVINCES.items():
                tasks.append(tracked_fetch(pid, name, year, prov_id, prov_name))

    print(f"[{label}] {len(school_map)} schools x {len(PROVINCES)} provinces x {len(YEARS)} years = {len(tasks)} requests", flush=True)
    t0 = time.time()
    results = await asyncio.gather(*tasks)
    for batch in results:
        all_records.extend(batch)

    elapsed = time.time() - t0
    print(f"[{label}] Done: {len(all_records)} records in {elapsed/60:.1f}m", flush=True)
    return all_records


async def main():
    from scrapers.config_beijing import BEIJING_SCHOOLS
    from scrapers.config_shanghai import SHANGHAI_SCHOOLS

    # Collect Beijing
    bj_records = await collect_schools(BEIJING_SCHOOLS, "Beijing")

    # Collect Shanghai
    sh_records = await collect_schools(SHANGHAI_SCHOOLS, "Shanghai")

    # Save
    with open("data/raw/beijing_scores.json", "w", encoding="utf-8") as f:
        json.dump(bj_records, f, ensure_ascii=False, indent=2)
    with open("data/raw/shanghai_scores.json", "w", encoding="utf-8") as f:
        json.dump(sh_records, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: Beijing={len(bj_records)}, Shanghai={len(sh_records)}")


if __name__ == "__main__":
    asyncio.run(main())
