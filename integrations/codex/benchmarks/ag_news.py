"""Pinned public AG News test data. Download explicitly; never commit its news text."""
import argparse
import csv
import hashlib
import io
from pathlib import Path
import random
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PATH = ROOT / "dist/benchmark-data/ag-news-test.csv"
REVISION = "555590db4219b1243abb1918effd6a7425a2d75f"
URL = f"https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/{REVISION}/data/ag_news_csv/test.csv"
SHA256 = "521465c2428ed7f02f8d6db6ffdd4b5447c1c701962353eb2c40d548c3c85699"
LABELS = ["world", "sports", "business", "science_technology"]
QUESTIONS = {"topic": {"type": "choice", "instructions": "Classify the news article's main topic.",
                       "criteria": {"world": "world news, politics, international affairs",
                                    "sports": "sporting events, teams, athletes",
                                    "business": "business, finance, markets, economy",
                                    "science_technology": "science, computing, technology"}}}


def load(path, per_class=50, seed=1729):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("AG News SHA-256 mismatch; refuse an unpinned dataset")
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    if len(rows) != 7600 or not 1 <= per_class <= 1900:
        raise ValueError("Expected 7600 test rows and 1–1900 samples per class")
    rng = random.Random(seed)
    selected = []
    for number, label in enumerate(LABELS, 1):
        indices = [i for i, row in enumerate(rows) if int(row[0]) == number]
        for index in rng.sample(indices, per_class):
            selected.append({"id": f"ag-news-test-{index}", "row_index": index,
                             "state": " ".join(rows[index][1:]), "expected": label})
    rng.shuffle(selected)
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    data = urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Downloaded AG News failed its pinned checksum")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"Prepared 7600 public test records: {args.output}; sha256={SHA256}")


if __name__ == "__main__":
    main()
