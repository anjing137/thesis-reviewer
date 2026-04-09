"""
Example usage of Thesis Reviewer
"""
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import review_pipeline


def main():
    """Example: Review a thesis file"""

    # Configuration
    thesis_file = "/path/to/your/thesis.docx"  # Change this
    api_key = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
    output_dir = "./review_output"

    if not os.path.exists(thesis_file):
        print(f"文件不存在: {thesis_file}")
        print("\n请修改 example_usage.py 中的 thesis_file 变量指向你的论文文件")
        return

    print("=" * 60)
    print("硕士论文智能评审系统 v2.3")
    print("=" * 60)
    print(f"\n论文文件: {thesis_file}")
    print(f"输出目录: {output_dir}")
    print()

    # Run review
    result = review_pipeline(thesis_file, api_key, output_dir)

    # Print report
    print("\n" + "=" * 60)
    print("评审报告")
    print("=" * 60 + "\n")
    print(result.report)

    # Print scoring summary
    from scoring.scorer import ThesisScorer
    scorer = ThesisScorer()
    print("\n" + scorer.get_scoring_summary(result.scoring_result))


if __name__ == '__main__':
    main()
