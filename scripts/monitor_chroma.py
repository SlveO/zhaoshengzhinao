#!/usr/bin/env python3
"""Real-time Chroma indexing progress monitor."""
import os, sys, time
import chromadb

CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "chroma_data")
TOTAL = 64083

def get_progress():
    try:
        c = chromadb.PersistentClient(path=CHROMA_PATH)
        col = c.get_collection("colleges_majors")
        count = col.count()
        db_path = os.path.join(CHROMA_PATH, "chroma.sqlite3")
        db_mb = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
        return count, db_mb
    except Exception:
        return 0, 0

def fmt_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.0f}m{seconds % 60:.0f}s"
    return f"{seconds / 3600:.0f}h{(seconds % 3600) / 60:.0f}m"

def draw_bar(count, total, width=40):
    pct = count / total if total > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    return bar

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("\033[?25l", end="")  # hide cursor

    prev_count = 0
    prev_time = time.time()
    start_time = time.time()

    try:
        while True:
            count, db_mb = get_progress()
            now = time.time()
            pct = count / TOTAL * 100 if TOTAL > 0 else 0

            # Speed calculation
            elapsed = now - prev_time
            docs_added = count - prev_count
            speed = docs_added / elapsed if elapsed > 0 else 0

            # ETA
            remaining = TOTAL - count
            eta_seconds = remaining / speed if speed > 0 else 0

            # Build display
            os.system("cls" if os.name == "nt" else "clear")
            print("╔══════════════════════════════════════════════════════════╗")
            print("║         Chroma 向量索引构建 — 实时监控                  ║")
            print("╠══════════════════════════════════════════════════════════╣")
            print(f"║  文档数 : {count:>8,} / {TOTAL:,}                   ║")
            print(f"║  完成度 : {pct:>7.1f}%                                  ║")
            print(f"║  {draw_bar(count, TOTAL, 46)} ║")
            print(f"╠══════════════════════════════════════════════════════════╣")
            print(f"║  速度   : {speed:>6.0f} 条/秒                           ║")
            print(f"║  预计剩余: {fmt_time(eta_seconds):>12}                       ║")
            print(f"║  已用时间: {fmt_time(now - start_time):>12}                       ║")
            print(f"║  数据库  : {db_mb:>7.1f} MB                              ║")
            print(f"╠══════════════════════════════════════════════════════════╣")

            # Recent activity sparkline
            if count >= TOTAL:
                print(f"║  ✅ 索引完成！                                          ║")
                print(f"╚══════════════════════════════════════════════════════════╝")
                break
            else:
                print(f"║  状态   : ● 索引构建中...                               ║")
                print(f"╚══════════════════════════════════════════════════════════╝")
                print(f"\n  按 Ctrl+C 退出监控（索引将继续后台运行）")

            prev_count = count
            prev_time = now
            time.sleep(2)

    except KeyboardInterrupt:
        print(f"\n\n监控已退出。索引进度: {count:,} / {TOTAL:,} ({pct:.1f}%)")
    finally:
        print("\033[?25h", end="")  # show cursor

if __name__ == "__main__":
    main()
