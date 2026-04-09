"""
PDF Parser for Thesis Documents
Uses pdfplumber for text extraction with structure preservation
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

import pdfplumber


@dataclass
class ChapterModule:
    """A single chapter in the thesis"""
    number: int  # Chapter number (1, 2, 3...)
    title: str  # Chapter title
    content: str  # Full text content
    char_count: int
    start_para: int = 0  # Starting paragraph index
    end_para: int = 0    # Ending paragraph index
    sections: Dict[str, str] = field(default_factory=dict)  # subsections


@dataclass
class ThesisModules:
    """Complete modular structure of a thesis"""
    title: str = ""
    modules: Dict[str, Any] = field(default_factory=dict)

    # Front matter
    cover: str = ""  # 封面
    abstract_cn: str = ""  # 中文摘要
    abstract_en: str = ""  # 英文摘要
    originality_statement: str = ""  # 独创性声明
    toc: str = ""  # 目录
    acknowledgments: str = ""  # 致谢
    appendix: str = ""  # 附录

    # Chapters
    chapters: List[ChapterModule] = field(default_factory=list)

    # References
    references: List[str] = field(default_factory=list)

    def get_chapter(self, num: int) -> Optional[ChapterModule]:
        """Get chapter by number"""
        for ch in self.chapters:
            if ch.number == num:
                return ch
        return None

    def get_chapter_by_title(self, title_pattern: str) -> Optional[ChapterModule]:
        """Get chapter by title (partial match)"""
        for ch in self.chapters:
            if title_pattern.lower() in ch.title.lower():
                return ch
        return None

    def chapter_summary(self) -> str:
        """Get chapter structure summary"""
        lines = ["章节结构:"]
        for ch in self.chapters:
            lines.append(f"  第{ch.number}章 {ch.title} ({ch.char_count}字)")
        return "\n".join(lines)


class PDFParser:
    """
    Parse PDF thesis into hierarchical modules.
    Extracts: cover, abstract, chapters, references, etc.
    """

    def __init__(self):
        self.all_text = ""  # Full document text
        self.lines = []     # Lines with position info

    def parse(self, file_path: str) -> ThesisModules:
        """Parse PDF file into hierarchical modules"""
        modules = ThesisModules()

        # Extract all text from PDF
        self._extract_all_text(file_path)

        if not self.all_text:
            return modules

        # Extract title
        modules.title = self._extract_title()

        # Extract front matter
        self._extract_front_matter(modules)

        # Extract chapters
        self._extract_chapters(modules)

        # Extract back matter (references, acknowledgments)
        self._extract_back_matter(modules)

        return modules

    def _extract_all_text(self, file_path: str):
        """Extract all text from PDF with position tracking"""
        self.all_text = ""
        self.lines = []

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""

                # Split into lines but preserve paragraph boundaries
                page_lines = text.split('\n')
                for line_idx, line in enumerate(page_lines):
                    line = line.strip()
                    if line:
                        self.lines.append({
                            'text': line,
                            'page': page_num,
                            'line_idx': line_idx
                        })

                self.all_text += text + "\n"

    def _extract_title(self) -> str:
        """Extract document title from cover page"""
        # On cover page, title is often split across lines
        # Look for pattern: "论文题目：" followed by title lines

        title_candidates = []
        in_title_block = False

        for line_info in self.lines[:30]:
            text = line_info['text'].strip()
            normalized = text.replace(' ', '').replace('　', '')

            # Title block starts after "论文题目："
            if '论文题目' in normalized:
                in_title_block = True
                # Remove prefix
                for prefix in ['论文题目：', '论文题目:', '题目：', '题目:']:
                    if prefix in normalized:
                        text = normalized.replace(prefix, '')
                        break
                if text:
                    title_candidates.append(text)
                continue

            if in_title_block:
                # Stop at chapter, abstract, or学位类型
                if text.startswith('第一章') or '学位类型' in text:
                    break
                # Stop if we hit abstract marker
                if text.replace(' ', '').replace('　', '') == '摘要':
                    break
                # Add all lines that look like title continuation
                # (long lines or lines starting with common continuations)
                if len(text) >= 6:
                    title_candidates.append(text)

        if title_candidates:
            # Return combined title (often 2 lines)
            combined = ''.join(title_candidates)
            if len(combined) >= 15:
                return combined
            # Or return longest candidate
            return max(title_candidates, key=len)

        # Fallback: look for longest meaningful line
        best_line = ""
        for line_info in self.lines[:50]:
            text = line_info['text'].strip()
            if len(text) > len(best_line) and 10 <= len(text) <= 100:
                best_line = text
        return best_line

    def _extract_front_matter(self, modules: ThesisModules):
        """Extract front matter: cover, abstract, originality statement, TOC"""
        in_abstract_cn = False
        in_abstract_en = False
        abstract_lines_cn = []
        abstract_lines_en = []
        seen_page_abstract = set()  # Avoid duplicate abstract pages

        for i, line_info in enumerate(self.lines):
            text = line_info['text'].strip()

            # Chinese abstract marker - handle both 1 and 2 spaces
            if text.replace(' ', '').replace('　', '') == '摘要':
                # Only start if we haven't captured abstract yet
                if not modules.abstract_cn:
                    in_abstract_cn = True
                    in_abstract_en = False
                    abstract_lines_cn = []
                continue

            # English abstract marker
            if text == 'ABSTRACT' or text == 'Abstract':
                if not modules.abstract_en and abstract_lines_cn:
                    # Chinese abstract done, start English
                    modules.abstract_cn = '\n'.join(abstract_lines_cn)
                    in_abstract_cn = False
                    in_abstract_en = True
                    abstract_lines_en = []
                    # The line "ABSTRACT" itself is not content
                    continue
                continue

            # Keywords marker - marks end of Chinese abstract
            if text.startswith('关键词') or '关键词' in text[:10]:
                if in_abstract_cn and abstract_lines_cn:
                    # This line is keywords, add it then stop
                    abstract_lines_cn.append(text)
                    in_abstract_cn = False
                continue

            # KEY WORDS - marks end of English abstract
            if 'KEY WORDS' in text.upper() or text.startswith('Keywords'):
                if in_abstract_en and abstract_lines_en:
                    abstract_lines_en.append(text)
                    in_abstract_en = False
                continue

            # Collect Chinese abstract
            if in_abstract_cn and text:
                # Stop at first chapter
                if self._is_chapter_header(text):
                    in_abstract_cn = False
                    if abstract_lines_cn:
                        modules.abstract_cn = '\n'.join(abstract_lines_cn)
                    continue
                abstract_lines_cn.append(text)

            # Collect English abstract
            if in_abstract_en and text:
                # Stop at first chapter
                if self._is_chapter_header(text):
                    in_abstract_en = False
                    if abstract_lines_en:
                        modules.abstract_en = '\n'.join(abstract_lines_en)
                    continue
                abstract_lines_en.append(text)

            # TOC
            if text == '目  录' or text == '目录' or text == 'CONTENTS':
                modules.toc = '目录已识别'

            # Originality statement
            if '独创性声明' in text:
                modules.originality_statement = '独创性声明已识别'

    def _extract_back_matter(self, modules: ThesisModules):
        """Extract back matter: references, acknowledgments, appendix"""
        # Find references section
        ref_started = False
        current_ref = ""  # Accumulate multi-line references

        for line_info in self.lines:
            text = line_info['text'].strip()

            # References header
            if text == '参考文献' or text == 'References':
                ref_started = True
                continue

            if ref_started:
                # Stop at acknowledgments or appendix
                text_no_space = text.replace(' ', '').replace('　', '')
                if text_no_space == '致谢' or text == '附录':
                    # Save any accumulated reference before breaking
                    if current_ref and self._is_valid_reference(current_ref):
                        modules.references.append(self._clean_reference(current_ref))
                    break
                if '本论文的顺利完成' in text:
                    if current_ref and self._is_valid_reference(current_ref):
                        modules.references.append(self._clean_reference(current_ref))
                    break

                # Check if this is a new reference (starts with reference marker)
                is_new_ref = self._is_new_reference_start(text)

                if is_new_ref:
                    # Save previous accumulated reference
                    if current_ref and self._is_valid_reference(current_ref):
                        modules.references.append(self._clean_reference(current_ref))
                    # Start new reference
                    current_ref = text
                else:
                    # Continuation of previous reference
                    if current_ref:
                        # Add space if needed
                        if text:
                            # Handle PDF line breaks: often a word is split
                            # If continuation looks like a new sentence (starts with uppercase or bracket), add space
                            if text[0].isupper() or text[0] in '（([':
                                current_ref += ' ' + text
                            else:
                                # Otherwise direct concatenation (word was split at line break)
                                current_ref += text
                    else:
                        # No previous reference, treat as new (edge case)
                        current_ref = text

        # Don't forget the last reference
        if current_ref and self._is_valid_reference(current_ref):
            modules.references.append(self._clean_reference(current_ref))

    def _clean_reference(self, text: str) -> str:
        """Clean a reference string by removing trailing page numbers etc."""
        if not text:
            return text
        # Remove trailing page numbers like ".75" or ".123"
        text = re.sub(r'\.\d{1,3}$', '', text)
        # Remove trailing dots and spaces
        text = text.strip().rstrip('.')
        return text

    def _is_new_reference_start(self, text: str) -> bool:
        """Check if text starts a new reference entry"""
        if not text or len(text) < 5:
            return False

        # Pattern 1: [数字] - numbered reference
        if re.match(r'^\[\d+\]', text):
            return True

        # Pattern 2: 数字. - numbered reference (no brackets)
        if re.match(r'^\d+\.\s', text):
            return True

        # Pattern 3: [J], [M], [D] etc - type marker at start
        if re.match(r'^\[[A-Z]\]', text):
            return True

        return False

    def _is_chapter_header(self, text: str) -> bool:
        """Check if text is a chapter header"""
        if not text:
            return False

        # Pattern 1: "第X章" or "第X节"
        if re.match(r'^第[一二三四五六七八九十\d]+[章节]', text):
            return True

        # Pattern 2: "第一章", "第二章" etc
        if re.match(r'^第[一二三四五六七八九十]+章', text):
            return True

        # Pattern 3: Pure number like "1.", "2." at start of line
        if re.match(r'^[12][0-9]*\.\s+', text) and len(text) < 100:
            return True

        # Pattern 4: Chapter numbers like "1 Introduction" or "1.1"
        if re.match(r'^[1-9]\d*(\.\d+)?\s+[A-Z\u4e00-\u9fff]', text) and len(text) < 150:
            return True

        return False

    def _is_valid_reference(self, text: str) -> bool:
        """Check if text is a valid reference entry"""
        if not text or len(text) < 15:
            return False

        text = text.strip()

        # Skip patterns
        skip_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^\d+\.\d+',
            r'^[一二三四五六七八九十]+、',
            r'^Abstract$',
            r'^(Key\s*Words|KEY\s*WORDS)',
            r'^感谢', r'^首先', r'^其次', r'^最后',
            r'^本论文', r'^谨向', r'^致谢',
            r'^附录',
            r'^\d+$',  # Just numbers
            r'^\[\]$',  # Empty brackets
        ]
        for pattern in skip_patterns:
            if re.match(pattern, text):
                return False

        if text == '参考文献':
            return False

        # Clean up trailing page numbers (e.g., "...145.75" -> "...145")
        text = re.sub(r'\.\d{1,3}$', '', text)

        # Must have a reference number marker
        # Pattern 1: [数字] - numbered reference
        if re.match(r'^\[\d+\]', text):
            return True

        # Pattern 2: Starts with number and period followed by author (English style)
        if re.match(r'^\d+\.\s+[A-Z\u4e00-\u9fff]', text):
            return True

        # Pattern 3: Author names at start (for foreign references)
        if re.match(r'^[A-Z][a-z]+,\s*[A-Z]', text) and len(text) > 30:
            return True

        # Reject lines that are just continuation fragments
        # (e.g., "[J].期刊名" without proper reference structure)
        if re.match(r'^\[J\]\.', text):
            return False
        if re.match(r'^\[M\]\.', text):
            return False
        if re.match(r'^\[D\]\.', text):
            return False
        if re.match(r'^\[C\]\.', text):
            return False
        if re.match(r'^\[N\]\.', text):
            return False

        return False

    def _extract_chapters(self, modules: ThesisModules):
        """Extract chapters from main body"""
        chapters = []
        current_chapter = None
        current_content = []
        chapter_start_idx = 0
        last_idx = 0

        # Find TOC end position
        toc_end_idx = self._find_toc_end()

        # Track last chapter number to avoid duplicates
        last_chapter_num = 0

        # Process lines
        for i, line_info in enumerate(self.lines):
            text = line_info['text'].strip()

            # Skip front matter and TOC
            if i < toc_end_idx:
                continue

            # Check for chapter header
            chapter_info = self._is_chapter_start(text)
            if chapter_info:
                # Skip if same chapter number (duplicate header)
                if chapter_info['number'] == last_chapter_num:
                    # Just add content to current chapter
                    if current_chapter is not None:
                        current_content.append(text)
                        last_idx = i
                    continue

                # Save previous chapter
                if current_chapter is not None and current_content:
                    content_text = '\n'.join(current_content)
                    if len(content_text) > 100:
                        chapters.append(ChapterModule(
                            number=current_chapter['number'],
                            title=current_chapter['title'],
                            content=content_text,
                            char_count=len(content_text),
                            start_para=chapter_start_idx,
                            end_para=last_idx
                        ))
                    current_content = []

                # Start new chapter
                current_chapter = chapter_info
                last_chapter_num = chapter_info['number']
                chapter_start_idx = i
                current_content = [text]
            elif current_chapter is not None:
                # Add to current chapter
                current_content.append(text)
                last_idx = i

        # Save last chapter
        if current_chapter is not None and current_content:
            content_text = '\n'.join(current_content)
            if len(content_text) > 100:
                chapters.append(ChapterModule(
                    number=current_chapter['number'],
                    title=current_chapter['title'],
                    content=content_text,
                    char_count=len(content_text),
                    start_para=chapter_start_idx,
                    end_para=last_idx
                ))

        modules.chapters = chapters

    def _find_toc_end(self) -> int:
        """Find where TOC ends and first chapter begins"""
        in_toc = False
        toc_end = 0

        for i, line_info in enumerate(self.lines):
            text = line_info['text'].strip()

            if text == '目  录' or text == '目录' or text == 'CONTENTS':
                in_toc = True
                continue

            if in_toc and self._is_chapter_header(text):
                toc_end = i
                break

        return toc_end

    def _is_chapter_start(self, text: str) -> Optional[Dict]:
        """Check if text marks start of a new chapter"""
        if not text:
            return None

        text_clean = text.strip()

        # Skip TOC-like entries
        if re.match(r'^第.章.+?\d+$', text_clean.replace(' ', '')):
            return None

        # Pattern: "第X章" - primary chapter header
        match = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', text_clean)
        if match:
            chapter_num_str = match.group(1)
            chapter_num = self._chinese_to_number(chapter_num_str)
            title = match.group(2).strip()
            if len(title) >= 2:
                return {'number': chapter_num, 'title': title}

        # Pattern: "1. Introduction" - numbered chapter
        match = re.match(r'^([1-9])\.\s+([A-Z][^\d]+)$', text_clean)
        if match:
            num = int(match.group(1))
            title = match.group(2).strip()
            if len(title) > 2:
                return {'number': num, 'title': title}

        return None

    def _chinese_to_number(self, chinese: str) -> int:
        """Convert Chinese number to integer"""
        chinese_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        try:
            return int(chinese) if chinese.isdigit() else chinese_map.get(chinese, 0)
        except:
            return 0


def parse_pdf(file_path: str) -> ThesisModules:
    """Convenience function to parse PDF thesis hierarchically"""
    parser = PDFParser()
    return parser.parse(file_path)


def extract_references_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extract reference statistics from a PDF thesis.
    Returns a dict with: total, chinese, foreign, journals, journal_ratio, recent_5yr, recent_5yr_ratio
    """
    parser = PDFParser()
    parser._extract_all_text(file_path)

    references = parser.references if hasattr(parser, 'references') else []

    # Re-parse just references with multi-line handling
    ref_started = False
    ref_list = []
    current_ref = ""

    for line in parser.lines:
        text = line['text'].strip()
        if text == '参考文献' or text == 'References':
            ref_started = True
            continue
        if ref_started:
            text_no_space = text.replace(' ', '').replace('　', '')
            if text_no_space == '致谢' or text == '附录':
                if current_ref and parser._is_valid_reference(current_ref):
                    ref_list.append(current_ref)
                break
            if '本论文的顺利完成' in text:
                if current_ref and parser._is_valid_reference(current_ref):
                    ref_list.append(current_ref)
                break

            # Check if this is a new reference
            is_new_ref = parser._is_new_reference_start(text)

            if is_new_ref:
                if current_ref and parser._is_valid_reference(current_ref):
                    ref_list.append(current_ref)
                current_ref = text
            else:
                if current_ref:
                    current_ref += text
                else:
                    current_ref = text

    if current_ref and parser._is_valid_reference(current_ref):
        ref_list.append(current_ref)

    # Analyze
    chinese_count = 0
    foreign_count = 0
    journal_count = 0
    recent_5yr_count = 0
    current_year = datetime.now().year

    for ref in ref_list:
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', ref))
        english_chars = len(re.findall(r'[A-Za-z]', ref))
        if chinese_chars > english_chars:
            chinese_count += 1
        else:
            foreign_count += 1

        if re.search(r'\[J\]', ref):
            journal_count += 1

        year_match = re.search(r'[\\(（]?(20[12]\d)[\\)）]?', ref)
        if year_match:
            year = int(year_match.group(1))
            if current_year - year <= 5:
                recent_5yr_count += 1

    total = len(ref_list)
    return {
        'total': total,
        'chinese': chinese_count,
        'foreign': foreign_count,
        'journals': journal_count,
        'journal_ratio': journal_count / total if total > 0 else 0.0,
        'recent_5yr': recent_5yr_count,
        'recent_5yr_ratio': recent_5yr_count / total if total > 0 else 0.0
    }