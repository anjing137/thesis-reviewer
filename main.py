"""
Main entry point for Thesis Reviewer CLI
不需要API Key，Python解析+评分，生成Prompt供AI评价
"""
import argparse
import os
import sys

from .pipeline import review_pipeline
from .scoring.scorer import ThesisScorer


def main():
    parser = argparse.ArgumentParser(
        description='硕士论文智能评审系统 v2.3（无需API Key）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
设计理念：Python解析 → 规则评分 → 生成Prompt → AI评价

示例用法:
  # 评审论文
  python main.py 论文.docx

  # 指定输出目录
  python main.py 论文.docx -o 输出目录/

  # 仅解析，不生成Prompt
  python main.py 论文.docx --parse-only
        """
    )

    parser.add_argument('file', help='论文文件路径(.doc/.docx)')
    parser.add_argument('-o', '--output', help='输出目录路径', default=None)
    parser.add_argument('--parse-only', help='仅解析和评分，不生成Prompt', action='store_true')

    args = parser.parse_args()

    # Check file exists
    if not os.path.exists(args.file):
        print(f"错误: 文件不存在: {args.file}")
        sys.exit(1)

    # Run review
    print("=" * 60)
    print("硕士论文智能评审系统 v2.3")
    print("=" * 60)
    print()

    try:
        result = review_pipeline(args.file, args.output)

        # Print scoring summary
        print("=" * 60)
        print("自动评分结果")
        print("=" * 60)
        scorer = ThesisScorer()
        print(scorer.get_scoring_summary(result.scoring_result))

        if not args.parse_only:
            print("\n" + "=" * 60)
            print("评价Prompt（按7维度组织内容）")
            print("=" * 60)
            print(result.review_prompt[:5000])  # 只显示前5000字，避免过长
            if len(result.review_prompt) > 5000:
                print("\n... [Prompt已截断，完整内容已保存到文件]")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
