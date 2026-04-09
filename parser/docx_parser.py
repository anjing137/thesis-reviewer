"""
Document Parser Module
Extracts structured text from .docx files
"""
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import re

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def convert_doc_to_docx(file_path: str) -> str:
    """
    Convert old .doc format to .docx using LibreOffice

    Args:
        file_path: Path to the .doc file

    Returns:
        Path to the converted .docx file
    """
    # Check if file is .doc format
    if not file_path.lower().endswith('.doc') or file_path.lower().endswith('.docx'):
        return file_path

    # Check if LibreOffice is installed
    libreoffice_paths = [
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',
        '/Applications/LibreOffice.app/Contents/MacOS/soffice.bin',
        'soffice'  # Fallback to PATH
    ]

    libreoffice = None
    for path in libreoffice_paths:
        if path == 'soffice':
            try:
                subprocess.run([path, '--version'], capture_output=True, check=True)
                libreoffice = path
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        elif os.path.exists(path):
            libreoffice = path
            break

    if not libreoffice:
        raise FileNotFoundError(
            "LibreOffice not found. Please install LibreOffice from https://www.libreoffice.org"
        )

    # Create temp directory for output
    temp_dir = tempfile.mkdtemp()
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = temp_dir

    # Run LibreOffice conversion
    cmd = [
        libreoffice,
        '--headless',
        '--convert-to', 'docx',
        '--outdir', output_dir,
        file_path
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    # Find the converted file
    converted_path = os.path.join(output_dir, base_name + '.docx')

    # LibreOffice might add a number suffix if file exists
    if not os.path.exists(converted_path):
        # Check for numbered versions
        for i in range(1, 100):
            numbered_path = os.path.join(output_dir, f"{base_name}_{i}.docx")
            if os.path.exists(numbered_path):
                converted_path = numbered_path
                break

    if not os.path.exists(converted_path):
        raise FileNotFoundError(f"Conversion output not found: {converted_path}")

    return converted_path


@dataclass
class Section:
    """Represents a section of the thesis"""
    title: str
    level: int  # 1 = chapter, 2 = section, 3 = subsection
    content: str
    start_line: int
    end_line: int
    subsections: List['Section'] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Complete parsed document structure"""
    title: str = ""
    abstract_cn: str = ""
    abstract_en: str = ""
    sections: List[Section] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    acknowledgments: str = ""
    raw_text: str = ""
    metadata: Dict = field(default_factory=dict)

    def get_full_text(self) -> str:
        """Get all text concatenated"""
        parts = [self.title, self.abstract_cn, self.abstract_en]
        for section in self.sections:
            parts.append(section.content)
        return "\n\n".join(filter(None, parts))


class DocxParser:
    """Parser for .docx thesis files"""

    # Keywords to identify sections
    SECTION_KEYWORDS = {
        # Chinese
        '摘要': 'abstract_cn',
        '目录': 'toc',
        '引言': 'introduction',
        '绪论': 'introduction',
        '文献综述': 'literature_review',
        '相关概念': 'related_concepts',
        '理论基础': 'theory',
        '研究方法': 'methodology',
        '研究设计与': 'methodology',
        '模型': 'methodology',
        '数据': 'data',
        '样本': 'data',
        '实证分析': 'empirical',
        '实证研究': 'empirical',
        '结果': 'results',
        '发现': 'results',
        '讨论': 'discussion',
        '结论': 'conclusion',
        '参考文献': 'references',
        '致谢': 'acknowledgments',
        '附录': 'appendix',
        # English
        'abstract': 'abstract_en',
        'introduction': 'introduction',
        'literature review': 'literature_review',
        'methodology': 'methodology',
        'data': 'data',
        'results': 'results',
        'discussion': 'discussion',
        'conclusion': 'conclusion',
        'references': 'references',
        'acknowledgments': 'acknowledgments',
    }

    def __init__(self):
        self.current_section = None
        self.sections_stack = []

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a .docx file and return structured content

        Args:
            file_path: Path to the .docx or .doc file

        Returns:
            ParsedDocument with structured content
        """
        # Convert .doc to .docx if necessary
        if file_path.lower().endswith('.doc') and not file_path.lower().endswith('.docx'):
            print(f"  Converting .doc to .docx using LibreOffice...")
            file_path = convert_doc_to_docx(file_path)

        doc = Document(file_path)
        parsed = ParsedDocument()

        # Extract title (first heading or first line)
        parsed.title = self._extract_title(doc)

        # Extract all paragraphs with their formatting info
        paragraphs = self._extract_paragraphs(doc)

        # Build section structure
        current_chapter = None
        current_section = None
        current_subsection = None
        section_content = []

        for para in paragraphs:
            text = para['text'].strip()
            if not text:
                continue

            level = para.get('heading_level')

            # Detect section start by keywords (for documents without proper heading styles)
            section_type = self._identify_section_type(text)
            is_chapter_heading = (
                re.match(r'^第[一二三四五六七八九十百\d]+章', text) or
                re.match(r'^第[一二三四五六七八九十百\d]+节', text) or
                re.match(r'^[一二三四五六七八九十\d]+[、.．]', text[:10]) or
                (section_type in ['introduction', 'literature_review', 'methodology',
                                  'empirical', 'results', 'discussion', 'conclusion',
                                  'references', 'toc'] and len(text) < 50)
            )

            # Check if it's a heading
            if level and level > 0 or is_chapter_heading:
                # Save previous section content
                if current_subsection:
                    current_subsection['content'] = '\n'.join(section_content)
                    current_section.subsections.append(Section(**current_subsection))
                    section_content = []
                elif current_section:
                    current_section['content'] = '\n'.join(section_content)
                    if current_chapter:
                        current_chapter.subsections.append(Section(**current_section))
                    else:
                        parsed.sections.append(Section(**current_section))
                    section_content = []
                elif current_chapter:
                    current_chapter['content'] = '\n'.join(section_content)
                    parsed.sections.append(Section(**current_chapter))
                    section_content = []

                # Start new section
                section_data = {
                    'title': text,
                    'level': level if level > 0 else 1,  # Use detected level or default to chapter
                    'content': '',
                    'start_line': para.get('line_num', 0),
                    'end_line': 0
                }

                if level > 0:
                    actual_level = level
                elif re.match(r'^第[一二三四五六七八九十百\d]+章', text):
                    actual_level = 1  # Chapter
                else:
                    actual_level = 1  # Default to chapter level for keyword-detected

                if actual_level == 1:
                    current_chapter = section_data
                    current_section = None
                    current_subsection = None
                elif actual_level == 2:
                    current_section = section_data
                    current_subsection = None
                elif actual_level >= 3:
                    current_subsection = section_data

            else:
                # Regular paragraph - add to current section
                section_content.append(text)

                # Try to identify special sections by keywords
                section_type = self._identify_section_type(text)
                if section_type == 'abstract_cn' and not parsed.abstract_cn:
                    # First paragraph after "摘要" is the abstract
                    parsed.abstract_cn = text
                elif section_type == 'abstract_en' and not parsed.abstract_en:
                    parsed.abstract_en = text

        # Save last section
        if current_subsection:
            current_subsection['content'] = '\n'.join(section_content)
            current_subsection['end_line'] = para.get('line_num', 0)
            current_section.subsections.append(Section(**current_subsection))
        elif current_section:
            current_section['content'] = '\n'.join(section_content)
            current_section['end_line'] = para.get('line_num', 0)
            if current_chapter:
                current_chapter.subsections.append(Section(**current_section))
            else:
                parsed.sections.append(Section(**current_section))
        elif current_chapter:
            current_chapter['content'] = '\n'.join(section_content)
            current_chapter['end_line'] = para.get('line_num', 0)
            parsed.sections.append(Section(**current_chapter))

        # Build raw text - use all paragraphs if no sections detected
        if parsed.sections:
            parsed.raw_text = '\n\n'.join([
                parsed.title,
                parsed.abstract_cn,
                parsed.abstract_en,
                '\n\n'.join([s.content for s in parsed.sections])
            ])
        else:
            # Fallback: concatenate all non-empty paragraphs
            all_text = [p['text'] for p in paragraphs if p['text'].strip()]
            parsed.raw_text = '\n\n'.join(all_text)

        # Extract references (simplified - looks for numbered references)
        parsed.references = self._extract_references(doc)

        return parsed

    def _extract_title(self, doc: Document) -> str:
        """Extract document title from cover page

        Cover page structure:
        1. [Header info] 单位代码、分类号 etc. - skip
        2. [Logo image] - ignored by docx
        3. "硕 士 学 位 论 文" - marker
        4. ["（以上一行用宋体小初号字）"] - template note, skip
        5. [论文题目] - THE ACTUAL TITLE (long text line)
        6. [Left column] - student name, year, supervisor - ignore
        """
        def normalize(text):
            return text.replace(' ', '').replace('　', '')

        # Known template prefixes to strip from title
        TEMPLATE_PREFIXES = [
            '论文题目：', '论文题目:', '论 文 题 目：', '论 文 题 目:',
            '论  文  题  目：', '论  文  题  目:', '题目：', '题目:'
        ]

        # Look for the thesis title section
        found_thesis_marker = False
        skip_template_note = False
        title_line = None

        for para in doc.paragraphs:
            text = para.text.strip()
            normalized = normalize(text)

            if not text:
                continue

            # Check if we passed the thesis marker
            if '硕' in normalized and '士' in normalized and '学' in normalized and '位' in normalized and '论' in normalized and '文' in normalized:
                if len(normalized) < 20:  # Short line with the marker words
                    found_thesis_marker = True
                    continue

            if found_thesis_marker:
                # Skip template note like "（以上一行用宋体小初号字）"
                if '宋体' in normalized or '小初' in normalized or ('以上' in normalized and '号字' in normalized):
                    skip_template_note = True
                    continue

                # Skip very short lines
                if len(text) < 10:
                    continue

                # Skip lines that are mostly numbers
                alpha_count = sum(c.isalpha() for c in normalized)
                if alpha_count < len(normalized) * 0.3:
                    continue

                # Skip body text patterns (this is still in cover area)
                body_indicators = ['假设', '本文', '因此', '利用', '使用', '研究表明',
                                   '研究认为', '通过', '进行', '分析', '发现', '得出',
                                   '得出', '认为', '表明']
                if any(pattern in normalized for pattern in body_indicators):
                    continue

                # This is likely the title!
                # Title is usually 15-80 characters for Chinese thesis
                if 10 <= len(text) <= 100:
                    title_line = text
                    break
                # Also accept longer titles (some are very long)
                elif len(text) > 100 and len(text) < 200:
                    # Check if it looks like a title (not full of special chars)
                    if alpha_count > len(normalized) * 0.5:
                        title_line = text
                        break

        if title_line:
            # Strip known template prefixes
            for prefix in TEMPLATE_PREFIXES:
                if title_line.startswith(prefix):
                    title_line = title_line[len(prefix):]
                    break
            # Also check with spaces preserved
            if title_line.startswith('论  文  题  目：'):
                title_line = title_line[9:]  # Remove "论  文  题  目："
            return title_line[:200].strip()

        # Fallback: try first long paragraph
        for para in doc.paragraphs:
            text = para.text.strip()
            if len(text) >= 15 and len(text) < 150:
                alpha_count = sum(c.isalpha() for c in normalize(text))
                if alpha_count > len(text) * 0.5:
                    return text[:200]

        return "Untitled"

    def _extract_paragraphs(self, doc: Document) -> List[Dict]:
        """Extract paragraphs with their formatting info"""
        paragraphs = []
        line_num = 0

        for para in doc.paragraphs:
            line_num += 1
            text = para.text.strip()

            heading_level = 0
            if para.style and 'Heading' in para.style.name:
                # Extract heading level from style name (e.g., "Heading 1")
                match = re.search(r'(\d+)', para.style.name)
                if match:
                    heading_level = int(match.group(1))

            paragraphs.append({
                'text': text,
                'heading_level': heading_level,
                'line_num': line_num,
                'style': para.style.name if para.style else None
            })

        # Also extract table content
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        line_num += 1
                        if para.text.strip():
                            paragraphs.append({
                                'text': para.text.strip(),
                                'heading_level': 0,
                                'line_num': line_num,
                                'style': 'Table'
                            })

        return paragraphs

    def _identify_section_type(self, text: str) -> Optional[str]:
        """Identify section type by keywords"""
        text_lower = text.lower()
        for keyword, section_type in self.SECTION_KEYWORDS.items():
            if keyword in text_lower:
                return section_type
        return None

    def _extract_references(self, doc: Document) -> List[str]:
        """Extract references section"""
        references = []
        in_references = False

        for para in doc.paragraphs:
            text = para.text.strip()
            # Check if this is the references header
            # Must be standalone "参考文献" or "参考文献" + space/newline
            # NOT "xxx参考文献xxx" or "1.格式规范问题...参考文献..."
            if (text == '参考文献' or
                text.startswith('参考文献') and len(text) < 20 or
                'references' in text.lower()):
                in_references = True
                continue
            if in_references and text:
                # Stop at acknowledgments or appendix
                if '致谢' in text or '独创性声明' in text:
                    break
                # Skip appendix markers
                if text.startswith('附') and len(text) < 30:
                    continue
                # Accept only proper reference formats:
                # [1] - numbered bracket format
                # 1. author, year, title... - numbered format
                # Author Name. Title[J/M/N/D]... - Chinese academic format
                # Author, A.B. (year). Title... - English academic format
                is_reference = False
                # Check for [N], [J], [M], [D], [C] journal/monograph markers
                if re.search(r'\[[JMNDC]\]', text):
                    is_reference = True
                # Check for numbered format [1] or 1.
                elif text.startswith('[') and re.match(r'\[\d+\]', text[:10]):
                    is_reference = True
                elif re.match(r'^\d+\.\s+\w', text):
                    is_reference = True
                # Check for author-year pattern at start: "Author, A. (year)" or "Author (year)"
                elif re.match(r'^[A-Z][a-z]+,?\s+[A-Z]\.\s*\(\d{4}\)', text) or \
                     re.match(r'^[A-Z][a-zA-Z\s]+\(\d{4}\)', text):
                    is_reference = True
                # Check for Chinese author pattern: "作者. 标题" (must have period after author, then space or Chinese chars)
                elif re.match(r'^[\u4e00-\u9fff]{2,4}\.\s', text) and len(text) < 200:
                    is_reference = True
                # Check for English author at start with capital and period in title
                elif re.match(r'^[A-Z][a-z]+\s+[A-Z]\.\s+', text) and ('.' in text[:50] or '(' in text[:50]):
                    is_reference = True

                if is_reference:
                    references.append(text)

        return references


def parse_docx(file_path: str) -> ParsedDocument:
    """
    Convenience function to parse a .docx file

    Args:
        file_path: Path to the .docx file

    Returns:
        ParsedDocument with structured content
    """
    parser = DocxParser()
    return parser.parse(file_path)
