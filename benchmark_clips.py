import time
import json
import os
import sqlite3
import shutil
from unittest.mock import patch
from shorts.nodes.clips import run

SCHEMA = """
CREATE TABLE step_results (
    job_id TEXT, step_name TEXT, status TEXT,
    output_path TEXT, output_checksum TEXT, error_msg TEXT,
    PRIMARY KEY (job_id, step_name)
)
"""

def setup_benchmark(tmp_path, num_scenes=10):
    job_id = "bench_job"
    scenes = [{"description": f"scene {i}", "duration_seconds": 5} for i in range(num_scenes)]

    os.makedirs(tmp_path, exist_ok=True)
    scenes_file = os.path.join(tmp_path, f"{job_id}_scenes.json")
    with open(scenes_file, "w") as f:
        json.dump(scenes, f)

    conn = sqlite3.connect(":memory:")
    conn.execute(SCHEMA)
    conn.execute(
        "INSERT INTO step_results (job_id, step_name, status, output_path) VALUES (?, ?, ?, ?)",
        (job_id, "scenes", "done", scenes_file)
    )
    conn.commit()

    return job_id, conn, str(tmp_path)

class MockPexels:
    def search(self, description, per_page=1):
        time.sleep(0.1)  # Simulate API latency
        return [{"url": "http://example.com/video.mp4"}]

def mock_urlretrieve(url, path):
    time.sleep(0.2)  # Simulate download latency

def run_benchmark(num_scenes=10):
    tmp_path = "bench_workspace"
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)

    job_id, conn, workspace = setup_benchmark(tmp_path, num_scenes)

    pexels = MockPexels()
    services = {"pexels": pexels}
    execution_context = {"workspace_dir": workspace}

    start_time = time.time()
    with patch("urllib.request.urlretrieve", side_effect=mock_urlretrieve):
        run(job_id, execution_context, conn, services)
    end_time = time.time()

    duration = end_time - start_time
    print(f"Processed {num_scenes} scenes in {duration:.2f} seconds")

    shutil.rmtree(tmp_path)
    return duration

if __name__ == "__main__":
    run_benchmark(10)
