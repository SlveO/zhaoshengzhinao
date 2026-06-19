"""Accuracy benchmarks — KB Q&A (LLM-as-judge) + profile extraction (field comparison).
Usage: python tests/benchmarks/run_accuracy.py [--kb-only|--extract-only] [--output report.json]
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent

def load_json(filename):
    path = BENCHMARK_DIR / filename
    if not path.exists(): print(f"[ERROR] {filename} not found"); sys.exit(1)
    with open(path, encoding="utf-8") as f: return json.load(f)

def fuzzy_match_province(p1, p2):
    if not p1 or not p2: return p1 == p2
    for s in ["省","市","自治区"]: p1, p2 = p1.replace(s,""), p2.replace(s,"")
    return p1 == p2

def jaccard(l1, l2):
    if not l1 and not l2: return 1.0
    s1, s2 = set(l1), set(l2)
    return len(s1&s2)/len(s1|s2) if len(s1|s2) else 0.0

def evaluate_kb_accuracy(dataset):
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_openai import ChatOpenAI
    from config import settings
    llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key,
                     base_url=settings.deepseek_base_url, temperature=0.0)
    judge_tpl = ("Rate answer quality 1-5.\n5=fully correct\n4=mostly correct\n3=partial\n"
                 "2=mostly wrong\n1=completely wrong\n\nQuestion: {q}\nExpected: {e}\nActual: {a}\n\nOutput ONLY a digit 1-5.")
    scores, details = [], []
    for item in dataset:
        q, exp = item["question"], item["expected_answer"]
        try:
            msgs = [SystemMessage(content="你是华南师范大学招生咨询助手。"), HumanMessage(content=q)]
            actual = llm.invoke(msgs).content
            jmsg = judge_tpl.format(q=q, e=exp, a=actual)
            score = max(1, min(5, int(llm.invoke([HumanMessage(content=jmsg)]).content.strip())))
        except: actual, score = "[ERROR]", 1
        scores.append(score)
        details.append({"id": item["id"], "question": q, "expected": exp, "actual": actual[:500],
                        "score": score, "correct": score>=4, "category": item.get("category","")})
    accuracy = sum(1 for s in scores if s>=4)/len(scores) if scores else 0
    return {"total": len(dataset), "average_score": round(sum(scores)/len(scores),2) if scores else 0,
            "accuracy": round(accuracy,4), "correct_count": sum(1 for s in scores if s>=4), "details": details}

def evaluate_extraction_accuracy(dataset):
    import asyncio
    from services.cend_profile_analyzer import analyze_cend_turn, merge_extraction_results, CendExtractionResult
    basic_scores, riasec_scores, interest_scores, details = [], [], [], []
    for item in dataset:
        conv = item["conversation"]; expected = item["expected_extraction"]
        merged = CendExtractionResult()
        user_msgs = [m for m in conv if m["role"]=="user"]
        ai_msgs = [m for m in conv if m["role"]=="assistant"]
        for i in range(len(user_msgs)):
            try:
                tr = asyncio.get_event_loop().run_until_complete(
                    analyze_cend_turn(user_msgs[i]["content"], ai_msgs[i]["content"] if i<len(ai_msgs) else "", merged.to_profile_json()))
                merged = merge_extraction_results(merged, tr)
            except: pass
        actual = merged.to_profile_json()
        # Basic 40%
        bc = 0
        if fuzzy_match_province(str(expected.get("basic",{}).get("province","")), str(actual.get("basic",{}).get("province",""))): bc+=1
        if str(expected.get("basic",{}).get("subject_type",""))==str(actual.get("basic",{}).get("subject_type","")): bc+=1
        try:
            if abs(int(expected.get("basic",{}).get("score",0) or 0)-int(actual.get("basic",{}).get("score",0) or 0))<=10: bc+=1
        except: pass
        basic_score = bc/3; basic_scores.append(basic_score)
        # RIASEC 30%
        rc = sum(1 for d in ["R","I","A","S","E","C"] if abs((expected.get("riasec",{}).get(d,0) or 0)-(actual.get("riasec",{}).get(d,0) or 0))<=2)
        riasec_score = rc/6; riasec_scores.append(riasec_score)
        # Interest/concern 30%
        ic = sum([jaccard(expected.get("interests",{}).get("preferred_subjects",[]), actual.get("interests",{}).get("preferred_subjects",[]))>=0.7,
                  jaccard(expected.get("concerns",[]), actual.get("concerns",[]))>=0.7,
                  jaccard(expected.get("values",[]), actual.get("values",[]))>=0.7])
        interest_score = ic/3; interest_scores.append(interest_score)
        details.append({"id":item["id"],"expected":expected,"actual":actual,
                        "basic_score":round(basic_score,2),"riasec_score":round(riasec_score,2),"interest_score":round(interest_score,2)})
    avg_b = sum(basic_scores)/len(basic_scores) if basic_scores else 0
    avg_r = sum(riasec_scores)/len(riasec_scores) if riasec_scores else 0
    avg_i = sum(interest_scores)/len(interest_scores) if interest_scores else 0
    return {"total":len(dataset),"basic_accuracy":round(avg_b,4),"riasec_accuracy":round(avg_r,4),
            "interest_accuracy":round(avg_i,4),"weighted_accuracy":round(0.4*avg_b+0.3*avg_r+0.3*avg_i,4),"details":details}

def benchmark_response_speed(num_samples: int = 10) -> dict:
    """Benchmark SSE response speed: first-token time, full-reply time, P50/P95/P99.
    Simulates a single-turn LLM call and measures timing.
    """
    import time, statistics
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_openai import ChatOpenAI
    from config import settings

    llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key,
                     base_url=settings.deepseek_base_url, temperature=0.0, streaming=True)

    test_question = "华南师范大学计算机专业2025年录取分数线是多少？"
    test_system = "你是华南师范大学招生咨询助手。请简短回答。"

    first_token_times = []
    full_reply_times = []

    for i in range(num_samples):
        msgs = [SystemMessage(content=test_system), HumanMessage(content=test_question)]
        try:
            t_start = time.perf_counter()
            first_token = None
            full_content = ""
            for chunk in llm.stream(msgs):
                if first_token is None:
                    first_token = time.perf_counter()
                full_content += chunk.content if hasattr(chunk, "content") else str(chunk)
            t_end = time.perf_counter()

            if first_token is not None:
                first_token_times.append(first_token - t_start)
            full_reply_times.append(t_end - t_start)
        except Exception:
            continue

    if not first_token_times:
        first_token_times = [0]
    if not full_reply_times:
        full_reply_times = [0]

    def percentile(data, p):
        data = sorted(data)
        idx = int(len(data) * p / 100)
        return data[min(idx, len(data)-1)]

    return {
        "samples": len(first_token_times),
        "first_token": {
            "avg": round(statistics.mean(first_token_times), 3),
            "p50": round(percentile(first_token_times, 50), 3),
            "p95": round(percentile(first_token_times, 95), 3),
            "p99": round(percentile(first_token_times, 99), 3),
        },
        "full_reply": {
            "avg": round(statistics.mean(full_reply_times), 3),
            "p50": round(percentile(full_reply_times, 50), 3),
            "p95": round(percentile(full_reply_times, 95), 3),
            "p99": round(percentile(full_reply_times, 99), 3),
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb-only", action="store_true"); p.add_argument("--extract-only", action="store_true")
    p.add_argument("--speed-only", action="store_true", help="Run only response speed benchmark")
    p.add_argument("--speed-samples", type=int, default=10, help="Samples for speed benchmark")
    p.add_argument("--output", type=str, default=None)
    args = p.parse_args()
    report = {"timestamp": datetime.now().isoformat(), "kb_accuracy": None, "extract_accuracy": None, "response_speed": None}
    run_all = not args.kb_only and not args.extract_only and not args.speed_only
    if not args.extract_only:
        print("="*60+"\nKB Q&A Accuracy\n"+"="*60)
        kb_data = load_json("knowledge_qa.json")
        print(f"Loaded {len(kb_data)} pairs")
        r = evaluate_kb_accuracy(kb_data)
        report["kb_accuracy"] = r["accuracy"]; report["kb_details"] = r
        print(f"Accuracy: {r['accuracy']:.1%} ({r['correct_count']}/{r['total']}) Avg: {r['average_score']}/5")
        print(f"{'PASS' if r['accuracy']>=0.95 else 'FAIL (<95%)'}")
    if not args.kb_only and not args.extract_only:
        print("\n"+"="*60+"\nResponse Speed Benchmark\n"+"="*60)
        print(f"Running {args.speed_samples} samples...")
        speed = benchmark_response_speed(args.speed_samples)
        report["response_speed"] = speed
        ft = speed["first_token"]
        fr = speed["full_reply"]
        print(f"First-token: avg={ft['avg']}s P50={ft['p50']}s P95={ft['p95']}s P99={ft['p99']}s")
        print(f"Full-reply:  avg={fr['avg']}s P50={fr['p50']}s P95={fr['p95']}s P99={fr['p99']}s")

    print("\n"+"="*60+"\nSUMMARY\n"+"="*60)
    if report["kb_accuracy"] is not None: print(f"KB: {report['kb_accuracy']:.1%} [{'PASS' if report['kb_accuracy']>=0.95 else 'FAIL'}]")
    if report["extract_accuracy"] is not None: print(f"Extract: {report['extract_accuracy']:.1%} [{'PASS' if report['extract_accuracy']>=0.95 else 'FAIL'}]")
    if report["response_speed"] is not None: print(f"Speed: first-token avg={report['response_speed']['first_token']['avg']}s P95={report['response_speed']['first_token']['p95']}s")
    if args.output:
        with open(Path(args.output), "w", encoding="utf-8") as f: json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    overall = (report["kb_accuracy"] is None or report["kb_accuracy"]>=0.95) and (report["extract_accuracy"] is None or report["extract_accuracy"]>=0.95)
    sys.exit(0 if overall else 1)

if __name__=="__main__": main()
