"""Create an explicitly synthetic preview DB without replacing an existing file."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def create_demo(path):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects an existing demo or a mistakenly supplied real DB.
    with path.open("xb"):
        pass
    with closing(sqlite3.connect(path)) as db:
        db.executescript("""
            CREATE TABLE scenes (
                scene_id TEXT PRIMARY KEY, name TEXT NOT NULL, units TEXT DEFAULT 'mm', revision INTEGER);
            CREATE TABLE components (
                component_id TEXT PRIMARY KEY, scene_id TEXT REFERENCES scenes(scene_id), name TEXT,
                category TEXT, layer TEXT, material TEXT, width_mm REAL, height_mm REAL,
                volume_m3 REAL, status TEXT, metadata_json TEXT);
            CREATE TABLE generation_plans (
                plan_id TEXT PRIMARY KEY, scene_id TEXT REFERENCES scenes(scene_id), title TEXT, status TEXT);
            CREATE TABLE generation_plan_steps (
                step_id TEXT PRIMARY KEY, plan_id TEXT REFERENCES generation_plans(plan_id),
                sequence INTEGER, title TEXT, status TEXT, progress REAL);
            CREATE TABLE material_notes (material TEXT PRIMARY KEY, note TEXT, color TEXT);
            CREATE VIEW component_summary AS
                SELECT category, count(*) AS component_count, round(sum(volume_m3),2) AS total_volume_m3
                FROM components GROUP BY category;
        """)
        db.executemany("INSERT INTO scenes VALUES (?,?,?,?)", [
            ("SC-01", "예시 · 커뮤니티센터", "mm", 3), ("SC-02", "예시 · 방문자센터", "mm", 2),
            ("SC-03", "예시 · 야외 쉼터", "mm", 1)])
        categories = ["기둥", "보", "벽", "슬래브", "문", "창"]
        materials = ["콘크리트", "강재", "벽돌", "콘크리트", "목재", "유리"]
        for i in range(1, 97):
            category = (i - 1) % 6
            metadata = json.dumps({"example": True, "floor": (i - 1) % 3 + 1,
                                   "tags": ["미리보기", categories[category]], "dimensions": {"unit": "mm"}}, ensure_ascii=False)
            db.execute("INSERT INTO components VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                f"CMP-{i:03}", f"SC-{(i - 1) % 3 + 1:02}", f"{categories[category]} {i:02}", categories[category],
                f"L{(i - 1) % 3 + 1}::{categories[category]}", materials[category], 300 + (i % 7) * 100,
                2400 + (i % 5) * 150, round(0.2 + (i % 13) * 0.17, 2), ["계획", "진행", "완료"][i % 3], metadata))
        db.executemany("INSERT INTO generation_plans VALUES (?,?,?,?)", [
            ("PL-01", "SC-01", "예시 · 공간 구성", "진행"), ("PL-02", "SC-02", "예시 · 자료 정리", "계획")])
        db.executemany("INSERT INTO generation_plan_steps VALUES (?,?,?,?,?,?)", [
            ("ST-01", "PL-01", 1, "자료 확인", "완료", 100), ("ST-02", "PL-01", 2, "층별 배치", "진행", 60),
            ("ST-03", "PL-01", 3, "출력 준비", "계획", 0), ("ST-04", "PL-02", 1, "목록 정리", "계획", 0)])
        db.executemany("INSERT INTO material_notes VALUES (?,?,?)", [
            ("콘크리트", "화면 확인용 예시 데이터", "#b9b9b0"), ("목재", "실제 모델 자료가 아닙니다", "#b99772")])
        db.commit()
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    print(create_demo(args.path))
