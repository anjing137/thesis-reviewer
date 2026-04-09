"""
Hierarchical Modular Document Parser
Parses thesis into structured modules: cover, abstract, chapters, references, etc.
"""
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import re


NAMESPACES = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


@dataclass
class ChapterModule:
    """A single chapter in the thesis"""
    number: int  # Chapter number (1, 2, 3...)
    title: str  # Chapter title
    content: str  # Full text content
    char_count: int
    start_para: int = 0  # Starting paragraph index in XML
    end_para: int = 0    # Ending paragraph index in XML
    sections: Dict[str, str] = field(default_factory=dict)  # subsections

    def overlaps(self, other_start: int, other_end: int) -> bool:
        """Check if this chapter overlaps with a range"""
        return self.start_para < other_end and self.end_para > other_start


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


class HierarchicalParser:
    """
    Parse thesis into hierarchical modules.
    Modules: cover, abstract, chapters, references, etc.
    """

    def __init__(self):
        self.root = None
        self.body = None

    def parse(self, file_path: str) -> ThesisModules:
        """Parse docx file into hierarchical modules"""
        if file_path.lower().endswith('.doc') and not file_path.lower().endswith('.docx'):
            from .docx_parser import convert_doc_to_docx
            file_path = convert_doc_to_docx(file_path)

        with zipfile.ZipFile(file_path, 'r') as zf:
            xml_content = zf.read('word/document.xml').decode('utf-8')

        self.root = ET.fromstring(xml_content)
        self.body = self.root.find('.//w:body', NAMESPACES)

        modules = ThesisModules()

        # Extract all paragraphs
        paragraphs = self._extract_all_paragraphs()

        # First pass: identify front matter and back matter
        self._extract_front_matter(modules, paragraphs)
        self._extract_back_matter(modules, paragraphs)

        # Extract title
        modules.title = self._extract_title()

        # Extract chapters (main body)
        self._extract_chapters(modules, paragraphs)

        return modules

    def _extract_all_paragraphs(self) -> List[Dict]:
        """Extract all paragraphs with their text and position"""
        paragraphs = []
        for i, para in enumerate(self.body.findall('.//w:p', NAMESPACES)):
            text = self._get_paragraph_text(para)
            paragraphs.append({
                'index': i,
                'text': text,
                'para': para
            })
        return paragraphs

    def _get_paragraph_text(self, para: ET.Element) -> str:
        """Extract text from paragraph"""
        texts = []
        for elem in para.iter():
            if elem.tag.endswith('}t') and elem.text:
                texts.append(elem.text)
        return ''.join(texts)

    def _extract_title(self) -> str:
        """Extract document title from cover page"""
        found_thesis_marker = False

        for para in self.body.findall('.//w:p', NAMESPACES):
            text = self._get_paragraph_text(para).strip()
            normalized = text.replace(' ', '').replace('　', '')

            # Check for thesis marker
            if ('硕' in normalized and '士' in normalized and '学' in normalized and
                '位' in normalized and '论' in normalized and '文' in normalized):
                if len(normalized) < 20:
                    found_thesis_marker = True
                    continue

            if found_thesis_marker and text:
                # Skip template notes
                if '宋体' in normalized or '小初' in normalized:
                    continue

                # Skip template prefixes
                for prefix in ['论  文  题  目：', '论 文 题 目：', '论文题目：', '论文题目:', '题目：', '题目:']:
                    if text.startswith(prefix):
                        text = text[len(prefix):]
                        break

                if len(text) >= 10:
                    return text

        return ""

    def _extract_front_matter(self, modules: ThesisModules, paragraphs: List[Dict]):
        """Extract front matter: cover, abstract, originality statement, TOC"""
        for i, para_info in enumerate(paragraphs):
            text = para_info['text'].strip()

            # Abstract (Chinese)
            if text == '摘  要' or text == '摘要':
                # Collect until Abstract (English) or first chapter
                abstract_lines = []
                for j in range(i + 1, len(paragraphs)):
                    next_text = paragraphs[j]['text'].strip()
                    if 'Abstract' in next_text or 'ABSTRACT' in next_text or 'abstract' in next_text.lower():
                        break
                    if self._is_chapter_header(next_text, paragraphs[j]['index']):
                        break
                    if next_text and len(next_text) > 5:
                        abstract_lines.append(next_text)
                if abstract_lines:
                    modules.abstract_cn = '\n'.join(abstract_lines[:100])  # Limit to first 100 lines

            # Abstract (English)
            if 'Abstract' in text and len(text) < 50:
                abstract_en_lines = []
                for j in range(i + 1, len(paragraphs)):
                    next_text = paragraphs[j]['text'].strip()
                    if self._is_chapter_header(next_text, paragraphs[j]['index']):
                        break
                    if 'KEY WORDS' in next_text or 'Keywords' in next_text:
                        abstract_en_lines.append(next_text)
                        break
                    if next_text and len(next_text) > 5:
                        abstract_en_lines.append(next_text)
                if abstract_en_lines:
                    modules.abstract_en = '\n'.join(abstract_en_lines[:100])

            # Originality statement
            if '独创性声明' in text:
                statement_lines = []
                for j in range(i, min(i + 20, len(paragraphs))):
                    next_text = paragraphs[j]['text'].strip()
                    if '论文作者签名' in next_text or '导师签名' in next_text:
                        statement_lines.append(next_text)
                    if '学位论文使用授权声明' in next_text:
                        break
                modules.originality_statement = '\n'.join(statement_lines[:30])

            # TOC marker
            if text == '目  录' or text == '目录' or text == 'CONTENTS':
                modules.toc = '目录已识别'

    def _extract_back_matter(self, modules: ThesisModules, paragraphs: List[Dict]):
        """Extract back matter: references, acknowledgments, appendix"""
        # For references, acknowledgments, appendix - use the dedicated extractor
        # This is handled by ReferenceExtractor class in pipeline_v3
        # Just mark where they start for now
        pass

    def _is_chapter_header(self, text: str, para_index: int) -> bool:
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

    def _is_references_header(self, text: str) -> bool:
        """Check if text is references header"""
        if not text:
            return False
        cleaned = text.strip()
        if cleaned == '参考文献':
            return True
        if cleaned.startswith('参考文献'):
            suffix = cleaned[len('参考文献'):]
            if suffix and suffix.strip() == suffix and suffix.replace('\t', '').replace(' ', '').isdigit():
                return True
        if cleaned in ('References', 'REFERENCES'):
            return True
        return False

    def _parse_reference(self, text: str) -> Optional[Dict]:
        """Parse a reference string"""
        if not text or len(text) < 10:
            return None

        cleaned = text.strip()

        # Skip non-references
        skip_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^\d+\.\d+',
            r'^[一二三四五六七八九十]+、',
            r'^Abstract$',
            r'^(Key\s*Words|KEY\s*WORDS)',
            r'^感谢', r'^首先', r'^其次', r'^最后',
            r'^本论文', r'^谨向', r'^致谢',
            r'^附录',
        ]
        for pattern in skip_patterns:
            if re.match(pattern, cleaned):
                return None

        return {
            'raw': text,
            'type': self._detect_ref_type(text),
            'language': self._detect_ref_language(text),
            'year': self._extract_year(text),
        }

    def _detect_ref_type(self, text: str) -> str:
        """Detect reference type [J], [M], [D], etc."""
        type_match = re.search(r'\[([A-Z])\]', text)
        return type_match.group(1) if type_match else 'unknown'

    def _detect_ref_language(self, text: str) -> str:
        """Detect reference language"""
        chinese = len(re.findall(r'[\u4e00-\u9fff]', text))
        english = len(re.findall(r'[A-Za-z]', text))
        return 'chinese' if chinese > english else 'english'

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from reference"""
        match = re.search(r'[\(（]?(20[12]\d)[\)）]?[,，年]', text)
        return int(match.group(1)) if match else None

    def _extract_chapters(self, modules: ThesisModules, paragraphs: List[Dict]):
        """Extract chapters from main body"""
        chapters = []
        current_chapter = None
        current_content = []
        current_sections = {}
        chapter_start_para = 0  # Track start paragraph of current chapter
        last_para_index = 0     # Track last processed paragraph index

        # Find TOC position to skip
        toc_end = 0
        in_toc = False
        for i, para_info in enumerate(paragraphs):
            text = para_info['text'].strip()
            if text == '目  录' or text == '目录' or text == 'CONTENTS':
                in_toc = True
                continue
            if in_toc and self._is_chapter_header(text, para_info['index']):
                # TOC ends when we hit first real chapter
                toc_end = i
                in_toc = False
                break

        for i, para_info in enumerate(paragraphs):
            text = para_info['text'].strip()
            para_index = para_info['index']

            # Skip front matter and TOC
            if para_index < toc_end:
                continue
            if self._is_front_matter(para_index, text):
                continue

            # Skip if we've already processed this paragraph in a chapter
            if chapters and chapters[-1].end_para >= para_index:
                continue

            # Check for chapter header
            chapter_info = self._is_chapter_start(text)
            if chapter_info:
                # Save previous chapter if it has content
                if current_chapter is not None and current_content:
                    content_text = '\n'.join(current_content)
                    # Only save if content is substantial (not just TOC entry)
                    if len(content_text) > 100:
                        chapters.append(ChapterModule(
                            number=current_chapter['number'],
                            title=current_chapter['title'],
                            content=content_text,
                            char_count=len(content_text),
                            start_para=chapter_start_para,
                            end_para=last_para_index,
                            sections=current_sections.copy()
                        ))
                    current_content = []
                    current_sections = {}

                # Start new chapter
                current_chapter = chapter_info
                chapter_start_para = para_index
                current_content = [text]
            elif current_chapter is not None:
                # Add to current chapter
                current_content.append(text)
                last_para_index = para_index

                # Check for section headers within chapter
                section_info = self._is_section_header(text)
                if section_info:
                    current_sections[section_info['title']] = text[:200]

        # Save last chapter
        if current_chapter is not None and current_content:
            content_text = '\n'.join(current_content)
            if len(content_text) > 100:
                chapters.append(ChapterModule(
                    number=current_chapter['number'],
                    title=current_chapter['title'],
                    content=content_text,
                    char_count=len(content_text),
                    start_para=chapter_start_para,
                    end_para=last_para_index,
                    sections=current_sections.copy()
                ))

        modules.chapters = chapters

    def _is_front_matter(self, para_index: int, text: str) -> bool:
        """Check if paragraph is front matter"""
        # Front matter typically at the beginning
        if para_index < 50:
            # Check for common front matter markers
            front_markers = [
                '硕士学位论文封面', '单位代码', '分类号', '申请号',
                '独创性声明', '学位论文使用授权',
                '摘要', 'Abstract', '目录', 'CONTENTS',
                '致谢', '参考文献'
            ]
            for marker in front_markers:
                if marker in text:
                    return True

            # Check for early chapter
            if self._is_chapter_header(text, para_index):
                return False

            # Skip empty or very short lines
            if len(text) < 10:
                return True

        return False

    def _is_chapter_start(self, text: str) -> Optional[Dict]:
        """Check if text marks start of a new chapter"""
        if not text:
            return None

        # Clean the text
        text_clean = text.strip()

        # Skip if it looks like a TOC entry (has trailing numbers like "40" or page-like content)
        # TOC entries often have patterns like "第1章 研究背景..........40"
        if re.match(r'^第.章.+?\d+$', text_clean.replace(' ', '')):
            return None

        # Pattern: "第X章" - primary chapter header
        # Must be: starts with 第, has 章, then title
        # Title should not be just numbers or very short
        match = re.match(r'^第([一二三四五六七八九十\d]+)章\s+(.+)$', text_clean)
        if match:
            chapter_num_str = match.group(1)
            chapter_num = self._chinese_to_number(chapter_num_str)
            title = match.group(2).strip()
            # Title should be meaningful (not just numbers or very short)
            if len(title) >= 2:
                return {'number': chapter_num, 'title': title}

        # Pattern: "1. Introduction" - numbered chapter (English style)
        match = re.match(r'^([1-9])\.\s+([A-Z][^\d]+)$', text_clean)
        if match:
            num = int(match.group(1))
            title = match.group(2).strip()
            if len(title) > 2:
                return {'number': num, 'title': title}

        return None

    def _is_section_header(self, text: str) -> Optional[Dict]:
        """Check if text is a section header within a chapter"""
        if not text or len(text) > 100:
            return None

        # Pattern: "1.1.1" or "1.1" at start
        match = re.match(r'^(\d+\.\d+)\s+(.*)$', text)
        if match:
            return {
                'title': text[:50],
                'level': 'subsection'
            }

        # Pattern: "(1)" or "(2)"
        match = re.match(r'^\((\d+)\)\s+(.*)$', text)
        if match:
            return {
                'title': text[:50],
                'level': 'subsection'
            }

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


class ParserError(Exception):
    """文档解析错误基类"""
    pass


class FileNotFoundParserError(ParserError):
    """文件不存在错误"""
    pass


class UnsupportedFormatError(ParserError):
    """不支持的格式错误"""
    pass


class EmptyDocumentError(ParserError):
    """空文档错误"""
    pass


class PDFParseError(ParserError):
    """PDF解析错误"""
    pass


class DOCXParseError(ParserError):
    """DOCX解析错误"""
    pass


def parse_hierarchical(file_path: str) -> ThesisModules:
    """
    Parse thesis hierarchically with error handling.

    Args:
        file_path: Path to thesis file (PDF or DOCX)

    Returns:
        ThesisModules object

    Raises:
        FileNotFoundParserError: File does not exist
        UnsupportedFormatError: Unsupported file format
        EmptyDocumentError: Document is empty
        PDFParseError: PDF parsing failed
        DOCXParseError: DOCX parsing failed
    """
    # Check file exists
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundParserError(f"文件不存在: {file_path}")

    if not path.is_file():
        raise FileNotFoundParserError(f"路径不是文件: {file_path}")

    # Check file extension
    suffix = path.suffix.lower()
    if suffix not in ['.pdf', '.docx', '.doc']:
        raise UnsupportedFormatError(f"不支持的文件格式: {suffix}，仅支持PDF/DOCX/DOC")

    # Check file size (empty file check)
    if path.stat().st_size == 0:
        raise EmptyDocumentError(f"文件为空: {file_path}")

    try:
        # Dispatch to appropriate parser based on file type
        if suffix == '.pdf':
            from .pdf_parser import parse_pdf
            modules = parse_pdf(file_path)
        elif suffix == '.doc':
            # .doc needs conversion first
            from .docx_parser import convert_doc_to_docx
            converted_path = convert_doc_to_docx(file_path)
            parser = HierarchicalParser()
            modules = parser.parse(converted_path)
        else:
            parser = HierarchicalParser()
            modules = parser.parse(file_path)

        # Check if modules has meaningful content
        if not modules.chapters and not modules.references:
            raise EmptyDocumentError(f"文档解析后内容为空，可能文件已损坏: {file_path}")

        return modules

    except FileNotFoundParserError:
        raise
    except UnsupportedFormatError:
        raise
    except EmptyDocumentError:
        raise
    except zipfile.BadZipFile:
        raise DOCXParseError(f"DOCX文件已损坏或不是有效的ZIP格式: {file_path}")
    except Exception as e:
        if suffix == '.pdf':
            raise PDFParseError(f"PDF解析失败: {str(e)}")
        else:
            raise DOCXParseError(f"DOCX解析失败: {str(e)}")


def extract_references(file_path: str) -> Dict[str, Any]:
    """
    Extract reference statistics from a thesis document.

    Args:
        file_path: Path to thesis file

    Returns:
        Dict with: total, chinese, foreign, journals, journal_ratio, recent_5yr, recent_5yr_ratio

    Raises:
        FileNotFoundParserError: File does not exist
        UnsupportedFormatError: Unsupported file format
        EmptyDocumentError: Document has no references
    """
    # Use parse_hierarchical for consistent error handling
    modules = parse_hierarchical(file_path)

    refs = modules.references
    total = len(refs)

    if total == 0:
        raise EmptyDocumentError(f"文档中未找到参考文献: {file_path}")

    import re
    from datetime import datetime

    chinese_count = 0
    foreign_count = 0
    journal_count = 0
    recent_5yr_count = 0
    current_year = datetime.now().year

    for ref in refs:
        # 判断中英文：前50字符中文字符占比
        first_50 = ref[:50]
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', first_50))
        english_chars = len(re.findall(r'[A-Za-z]', first_50))
        if chinese_chars > english_chars:
            chinese_count += 1
        else:
            foreign_count += 1

        # 期刊标记
        if re.search(r'\[J\]', ref):
            journal_count += 1

        # 年份检测
        year_match = re.search(r'[（(]?(20[12]\d)[)）]?', ref)
        if year_match:
            year = int(year_match.group(1))
            if current_year - year <= 5:
                recent_5yr_count += 1

    return {
        'total': total,
        'chinese': chinese_count,
        'foreign': foreign_count,
        'journals': journal_count,
        'journal_ratio': round(journal_count / total, 2) if total > 0 else 0,
        'recent_5yr': recent_5yr_count,
        'recent_5yr_ratio': round(recent_5yr_count / total, 2) if total > 0 else 0
    }


def _is_valid_reference(text: str) -> bool:
    """Check if text is a valid reference entry"""
    if not text or len(text) < 10:
        return False

    # Skip patterns that indicate non-reference content
    skip_patterns = [
        r'^第[一二三四五六七八九十\d]+章',
        r'^\d+\.\d+',
        r'^[一二三四五六七八九十]+、',
        r'^Abstract$',
        r'^(Key\s*Words|KEY\s*WORDS)',
        r'^感谢', r'^首先', r'^其次', r'^最后',
        r'^本论文', r'^谨向', r'^致谢',
        r'^附录',
    ]
    for pattern in skip_patterns:
        if re.match(pattern, text.strip()):
            return False

    # If it looks like a reference header, skip
    if text.strip() == '参考文献':
        return False

    # Accept if it has academic reference markers [J], [M], [D], [C], [N]
    if re.search(r'\[[JMNDC]\]', text):
        return True

    # Accept numbered references like [1], [2], etc.
    if re.match(r'\[\d+\]', text[:6]):
        return True

    # Accept if starts with number followed by period: "1. Author..."
    if re.match(r'^\d+\.\s+[A-Z\u4e00-\u9fff]', text):
        return True

    # Accept if has any year in 20xx format
    has_year = re.search(r'20\d{2}', text)

    # If has year and reasonable length, likely a reference
    if has_year and len(text) > 30:
        return True

    # Accept English names at start with reasonable length
    if re.match(r'^[A-Z][a-z]+\s+[A-Z]\.?\s*', text) and len(text) > 40:
        return True

    # Accept Chinese text that looks like academic citation
    if re.match(r'^[\u4e00-\u9fff]{2,5}', text) and len(text) > 25:
        return True

    return False
