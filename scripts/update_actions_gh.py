import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Union

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import (
    DoubleQuotedScalarString,  # 引用符保持用（オプション）
)

# 設定
WORKFLOW_DIR: str = ".github/workflows"


def get_latest_version(owner: str, repo: str) -> Optional[str]:
    """gh CLIで最新リリースを取得"""
    cmd: List[str] = ["gh", "api", f"repos/{owner}/{repo}/releases/latest"]
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        import json  # JSON解析用（遅延インポート）

        data: Dict[str, Any] = json.loads(result.stdout)
        return data["tag_name"]  # type: str
    except subprocess.CalledProcessError:
        print(f"Error fetching latest version for {owner}/{repo}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def parse_uses_line(uses_value: Union[str, Any]) -> Optional[tuple[str, str, str]]:
    """uses値からowner, repo, versionを抽出"""
    match: Optional[re.Match[str]] = re.search(
        r"([\w\-]+)/([\w\-]+)@([\w\.\-]+)", str(uses_value)
    )
    if match:
        return match.groups()  # type: tuple[str, str, str]
    return None


def update_workflow(file_path: str) -> None:
    """YAMLファイルをround-tripモードで更新（フォーマット保持）"""
    yaml: YAML = YAML()
    yaml.preserve_quotes = True  # 引用符を保持
    yaml.width = float("inf")  # 行の折り返しを無効化（元のフォーマット保持）

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content: Union[Dict[str, Any], List[Any], None] = yaml.load(f)

        updated: bool = False
        if content and isinstance(content, dict) and "jobs" in content:
            jobs: Dict[str, Any] = content["jobs"]
            for job_name in jobs:
                job: Any = jobs[
                    job_name
                ]  # strictモード下でAnyを許容（構造が複雑のため）
                if isinstance(job, dict) and "steps" in job:
                    steps: List[Any] = job["steps"]
                    for step in steps:
                        if isinstance(step, dict) and "uses" in step:
                            parsed: Optional[tuple[str, str, str]] = parse_uses_line(
                                step["uses"]
                            )
                            if parsed:
                                owner, repo, version = parsed
                                latest: Optional[str] = get_latest_version(owner, repo)
                                if latest and latest != version:
                                    # 元の文字列形式を保持しつつバージョン更新
                                    old_uses: str = str(step["uses"])
                                    new_uses: str = re.sub(
                                        r"@[\w\.\-]+$", f"@{latest}", old_uses
                                    )
                                    step["uses"] = new_uses  # 文字列として直接更新
                                    print(
                                        f"Updated {owner}/{repo}: {version} -> {latest} in {file_path}"
                                    )
                                    updated = True

        if updated:
            # round-tripで書き戻し（元のインデント・順序・コメント保持）
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(content, f)
            print(f"File updated while preserving format: {file_path}")
        else:
            print(f"No updates needed for: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


# 実行（型指定なし、グローバル実行部のため）
for root, dirs, files in os.walk(WORKFLOW_DIR):
    for file in files:
        if file.endswith(".yml") or file.endswith(".yaml"):
            update_workflow(os.path.join(root, file))
