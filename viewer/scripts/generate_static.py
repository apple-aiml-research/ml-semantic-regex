# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "pyarrow",
#     "tqdm",
#     "brotli",
# ]
# ///

import pathlib
import json
import gzip
import pandas as pd
import tqdm
import brotli


def get_all_json_files(dir_path):
    """Recursively find all .json.brotli files in directory."""
    return sorted(pathlib.Path(dir_path).rglob("*.json.brotli"))


def load_json_brotli(path):
    """Load and decompress a gzipped JSON file."""
    with open(path, "rb") as f:
        return json.loads(brotli.decompress(f.read()))


def parse_result_path(path_str):
    """Extract experiment and result from path."""
    path_parts = path_str.replace("experiments/", "").split("/")
    return {
        "experiment": path_parts[0],
        "result": path_parts[1],
    }


def parse_result_content(fetch_path, file_name, json_key, content):
    # Extract evaluation metrics with only values
    evaluation = {}
    for key in content["evaluation"]:
        evaluation[key] = {"value": content["evaluation"][key]["value"]}

    # Create redacted content structure
    redacted_content = {
        "feature": content["feature"],
        "description": {"description": content["description"]["description"]},
        "evaluation": evaluation,
    }

    return {
        "fetchPath": str(fetch_path),
        "fileName": json_key,
        **parse_result_path(file_name),
        "content": redacted_content,
    }


def parse_result_file(base_dir, abs_path):
    """Parse a result file and extract relevant data."""
    fetch_path = abs_path.relative_to(base_dir)
    group_content = load_json_brotli(abs_path)

    result = []
    for key, content in group_content.items():
        result.append(
            parse_result_content(fetch_path, str(fetch_path) + "/" + key, key, content)
        )
    return result


# Main execution
base_dir = pathlib.Path("../experiments/artifacts").resolve()
all_files = get_all_json_files(base_dir)

result = []

for f in tqdm.tqdm(all_files):
    result += parse_result_file(base_dir, f)

# Convert to DataFrame and save as parquet
df = pd.DataFrame(result)

with open("./src/lib/assets/artifacts_index.json", "w", encoding="utf-8") as f:
    json.dump(result, f)


print(f"{len(result)} results found.")
