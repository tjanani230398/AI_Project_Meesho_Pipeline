import sqlite3, csv, os
here = os.path.dirname(os.path.abspath(__file__))
conn = sqlite3.connect(os.path.join(here, "meesho_reseller.db"))
jobs = {
 "q1_monthly_category_revenue": "monthly_category_revenue.csv",
 "q2_region_revenue": "region_revenue.csv",
 "q3_top_resellers": "top_resellers.csv",
 "q4a_zero_order_resellers": "zero_order_resellers.csv",
 "q4b_count_star_vs_count_col": "count_star_vs_count_col.csv",
 "q5_june_delivered_aov": "june_delivered_aov.csv",
}
for q, out in jobs.items():
    sql = open(os.path.join(here, "queries", q + ".sql")).read()
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(os.path.join(here, "output", out), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    print(f"--- {out} ({len(rows)} rows)")
    print(",".join(cols))
    for r in rows[:16]: print(",".join(map(str, r)))
