"""
Information Extractor Module
Uses LLM to extract structured information from thesis
"""
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from anthropic import Anthropic

from .prompts import (
    INFO_EXTRACTION_PROMPT,
    METHODOLOGY_EXTRACTION_PROMPT,
    FORMAT_CHECKING_PROMPT,
    PAPER_TYPE_KEYWORDS
)


@dataclass
class ExtractedInfo:
    """Structured extracted information from thesis"""
    paper_type: str = ""
    research_question: str = ""
    research_gap: str = ""
    method: str = ""
    method_details: Dict = field(default_factory=dict)
    data: Dict = field(default_factory=dict)
    has_robustness: Optional[bool] = None
    robustness_details: str = ""
    has_endogeneity: Optional[bool] = None
    endogeneity_details: str = ""
    main_conclusion: str = ""
    innovation_type: str = ""
    limitations: str = ""

    # Reference info (can be set by pipeline after parsing)
    reference_info: Dict = field(default_factory=dict)
    reference_section: str = ""

    # Evidence citations
    evidence: Dict[str, str] = field(default_factory=dict)

    # Format checking results
    format_check: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        result = {
            'paper_type': self.paper_type,
            'research_question': self.research_question,
            'research_gap': self.research_gap,
            'method': self.method,
            'method_details': self.method_details,
            'data': self.data,
            'has_robustness': self.has_robustness,
            'robustness_details': self.robustness_details,
            'has_endogeneity': self.has_endogeneity,
            'endogeneity_details': self.endogeneity_details,
            'main_conclusion': self.main_conclusion,
            'innovation_type': self.innovation_type,
            'limitations': self.limitations,
            'reference_info': self.reference_info,
            'reference_section': self.reference_section,
            'evidence': self.evidence,
            'format_check': self.format_check
        }

        # Promote method_details fields to top level for scoring rules
        method_details = self.method_details or {}
        if 'over_control_issues' in method_details:
            result['over_control_issues'] = method_details['over_control_issues']
        if 'identification_strategy' in method_details:
            result['identification_strategy'] = method_details['identification_strategy']
        if 'variables' in method_details:
            result['variables'] = method_details['variables']
        if 'causal_chains' in method_details:
            result['causal_chains'] = method_details['causal_chains']

        return result


class InfoExtractor:
    """Extracts structured information from thesis using LLM"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def extract(self, content: str, max_chars: int = 50000) -> ExtractedInfo:
        """
        Extract structured information from thesis content

        Args:
            content: Full thesis text content
            max_chars: Maximum characters to send to LLM (for cost control)

        Returns:
            ExtractedInfo with structured data
        """
        # Truncate if too long
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[内容已截断...]"

        # Extract main information
        info = self._extract_main_info(content)

        # Extract methodology details
        method_info = self._extract_methodology(content)
        info.method_details = method_info

        # Extract format compliance
        format_info = self._extract_format_info(content)
        info.format_check = format_info

        return info

    def _extract_main_info(self, content: str) -> ExtractedInfo:
        """Extract main thesis information"""
        prompt = INFO_EXTRACTION_PROMPT.format(content=content)

        response = self._call_llm(prompt)
        data = self._parse_json_response(response)

        info = ExtractedInfo()

        if data:
            info.paper_type = data.get('paper_type', '')
            info.research_question = data.get('research_question', '')
            info.research_gap = data.get('research_gap', '')
            info.method = data.get('method', '')
            info.method_details = data.get('method_details', {})
            info.data = data.get('data', {})
            info.has_robustness = data.get('has_robustness')
            info.robustness_details = data.get('robustness_details', '')
            info.has_endogeneity = data.get('has_endogeneity')
            info.endogeneity_details = data.get('endogeneity_details', '')
            info.main_conclusion = data.get('main_conclusion', '')
            info.innovation_type = data.get('innovation_type', '')
            info.limitations = data.get('limitations', '')

        return info

    def _extract_methodology(self, content: str) -> Dict:
        """Extract detailed methodology information"""
        # Try to find methodology section
        sections = content.split('\n')
        method_section = []
        in_method = False

        keywords = ['研究方法', '方法论', 'methodology', '研究设计与', '实证分析', '模型设定']

        for line in sections:
            if any(kw in line.lower() for kw in keywords):
                in_method = True
            if in_method:
                method_section.append(line)
                if len(method_section) > 50:  # Limit section length
                    break

        if not method_section:
            return {}

        method_content = '\n'.join(method_section[:30])  # First 30 lines of method section
        prompt = METHODOLOGY_EXTRACTION_PROMPT.format(content=method_content)

        response = self._call_llm(prompt)
        return self._parse_json_response(response) or {}

    def _extract_format_info(self, content: str) -> Dict:
        """Extract format compliance information"""
        # Only check a portion for format
        prompt = FORMAT_CHECKING_PROMPT.format(content=content[:30000])

        response = self._call_llm(prompt)
        return self._parse_json_response(response) or {}

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        # Handle different content block types
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                return block.text
        return ""

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        try:
            # Try to find JSON in response
            json_str = response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0]

            # Clean up common issues
            json_str = json_str.strip()
            if json_str.startswith('json'):
                json_str = json_str[4:].strip()

            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Warning: Failed to parse JSON: {e}")
            return None


def extract_info(content: str, api_key: str, use_mock: bool = False) -> ExtractedInfo:
    """
    Convenience function to extract information

    Args:
        content: Thesis text content
        api_key: Anthropic API key
        use_mock: If True, use rule-based mock extraction (no API call)

    Returns:
        ExtractedInfo with structured data
    """
    if use_mock:
        return _mock_extract(content)
    extractor = InfoExtractor(api_key)
    return extractor.extract(content)


def _mock_extract(content: str) -> ExtractedInfo:
    """
    Mock extraction using rules (for testing without API)
    This provides a STARTING POINT for AI to review and refine.

    Args:
        content: Thesis text content

    Returns:
        ExtractedInfo with rule-based extraction data
    """
    info = ExtractedInfo()

    # Detect paper type by keywords
    info.paper_type = _detect_paper_type_mock(content)

    # Extract method keywords
    method_keywords = _extract_method_keywords(content)

    # Analyze content for research question
    info.research_question = _extract_research_question(content)

    # Analyze content for research gap
    info.research_gap = _extract_research_gap(content)

    # Set methods
    info.method = method_keywords.get('main_method', '其他')

    # Analyze variables
    variables = _extract_variables(content)
    info.method_details = {
        'identification_strategy': method_keywords.get('main_method', '回归分析'),
        'variables': variables,
        'over_control_issues': [],
        'causal_chains': _extract_causal_chains(content, variables)
    }

    # Analyze data
    info.data = _extract_data_info(content)

    # Check for robustness and endogeneity
    info.has_robustness = any(kw in content.lower() for kw in
        ['稳健性', '稳健性检验', '敏感性分析', 'robustness'])
    info.has_endogeneity = any(kw in content.lower() for kw in
        ['内生性', '工具变量', 'IV', 'endogeneity'])

    # Check for hypothesis
    info.has_hypothesis = '假设' in content

    # Innovation type
    if '创新' in content:
        if method_keywords.get('methods'):
            info.innovation_type = '方法创新'
        else:
            info.innovation_type = '选题创新'
    else:
        info.innovation_type = '选题创新'

    # Analyze limitations
    info.limitations = _extract_limitations(content)

    # Main conclusion
    info.main_conclusion = _extract_conclusion(content)

    return info


def _detect_paper_type_mock(content: str) -> str:
    """Detect paper type using keywords"""
    content_lower = content.lower()

    scores = {}

    for ptype, keywords in PAPER_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in content_lower)
        scores[ptype] = score

    if scores:
        return max(scores, key=scores.get)
    return '未知'


def _extract_method_keywords(content: str) -> Dict[str, Any]:
    """Extract method-related keywords"""
    content_lower = content.lower()

    methods = []

    # Quantitative methods
    if any(kw in content_lower for kw in ['ols', '回归', '固定效应', '随机效应']):
        methods.append('回归分析')
    if any(kw in content_lower for kw in ['logistic', 'logit', '二元logistic']):
        methods.append('Logistic回归')
    if any(kw in content_lower for kw in ['did', '双重差分']):
        methods.append('DID')
    if any(kw in content_lower for kw in ['psm', '倾向得分']):
        methods.append('PSM')

    # Survey methods
    if any(kw in content_lower for kw in ['问卷', '量表', '李克特']):
        methods.append('问卷调查')
    if any(kw in content_lower for kw in ['信度', '效度', 'cronbach', '克隆巴赫']):
        methods.append('信效度检验')
    if any(kw in content_lower for kw in ['因子分析', '探索性因子', '验证性因子']):
        methods.append('因子分析')

    # Case study
    if any(kw in content_lower for kw in ['案例', '访谈', '扎根']):
        methods.append('案例研究')

    return {
        'main_method': '+'.join(methods) if methods else '其他',
        'methods': methods
    }


def _extract_research_question(content: str) -> str:
    """Extract research question from content"""
    # Look for patterns like "研究..." or "本文研究..."
    import re
    patterns = [
        r'研究(?:了|的是)?(.+?)[，,。]',
        r'本文(?:旨在|致力于|试图)?(.+?)[，,。]',
        r'探讨(.+?)[，,。]',
        r'分析(.+?)[，,。]',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)[:100]
    return '研究问题需根据原文确定'


def _extract_research_gap(content: str) -> str:
    """Extract research gap from content"""
    import re
    patterns = [
        r'(?:然而|但是|尽管)(.+?)[，,。]',
        r'现有研究(.+?)[，,。]',
        r'不足之处(.+?)[，,。]',
        r'有待进一步(.+?)[，,。]',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)[:100]
    return ''


def _extract_variables(content: str) -> Dict[str, List[str]]:
    """Extract variables from content"""
    variables = {
        'dependent': [],
        'independent': [],
        'control': [],
        'mediator': [],
        'moderator': []
    }

    import re

    # Look for 因变量/自变量 patterns
    dep_pattern = r'(?:因变量|被解释变量|被解释变量|被解释变量|Y)(?:是|:|为)?(.+?)[，,。]'
    indep_pattern = r'(?:自变量|解释变量|核心解释变量|X)(?:是|:|为)?(.+?)[，,。]'
    ctrl_pattern = r'(?:控制变量|控制因素)(?:是|:|为)?(.+?)[，,。]'

    for pattern, key in [(dep_pattern, 'dependent'), (indep_pattern, 'independent'), (ctrl_pattern, 'control')]:
        match = re.search(pattern, content)
        if match:
            vars_text = match.group(1)
            # Split by common separators
            vars_list = re.split(r'[,，、和与及]', vars_text)
            variables[key] = [v.strip() for v in vars_list if v.strip()]

    # If no variables found, try to extract common terms
    if not any(variables.values()):
        # Look for common variable patterns
        if '保险' in content:
            variables['dependent'] = ['农业保险需求']
        if any(kw in content.lower() for kw in ['收入', '年龄', '教育']):
            variables['independent'] = ['农户特征']
        if '风险感知' in content:
            variables['control'] = ['风险感知']

    return variables


def _extract_causal_chains(content: str, variables: Dict) -> List[Dict]:
    """Extract causal chain statements"""
    chains = []

    # Look for hypothesis patterns
    import re
    hyp_pattern = r'假设\d*[:：]?\s*(.+?)[。.]'
    matches = re.findall(hyp_pattern, content)

    for m in matches[:5]:  # Limit to 5 hypotheses
        chains.append({
            'statement': m[:100],
            'cause': '待确定',
            'effect': '待确定',
            'mediator': ''
        })

    return chains


def _extract_data_info(content: str) -> Dict:
    """Extract data source and sample info"""
    import re

    data_info = {
        'source': '待确定',
        'sample_size': 0,
        'time_range': '',
        'region': ''
    }

    # Look for sample size
    sample_patterns = [
        r'样本[量个]*(?:为|：|:)?(\d+)',
        r'(\d+)\s*份?[问问]卷',
        r'(\d+)\s*户(?:农户|家庭)',
        r'(\d+)个?(?:样本|观测值|观测)'
    ]
    for pattern in sample_patterns:
        match = re.search(pattern, content)
        if match:
            data_info['sample_size'] = int(match.group(1))
            break

    # Look for region
    region_patterns = [
        r'河南省(\w+)',
        r'(\w+)省(\w+)',
        r'(?:研究|调查|数据来源)[于在](\w+)',
    ]
    for pattern in region_patterns:
        match = re.search(pattern, content)
        if match:
            region = match.group(0).replace('研究于', '').replace('调查于', '').replace('数据来源于', '')
            data_info['region'] = region
            break

    # Look for time range
    year_pattern = r'20\d{2}(?:年|-)20\d{2}'
    year_match = re.search(year_pattern, content)
    if year_match:
        data_info['time_range'] = year_match.group(0)

    # Determine source
    if '问卷' in content:
        data_info['source'] = '问卷调查'
    elif '统计年鉴' in content:
        data_info['source'] = '统计年鉴'
    elif '数据库' in content or 'CFPS' in content or 'CHNS' in content:
        data_info['source'] = '公开数据库'

    return data_info


def _extract_limitations(content: str) -> str:
    """Extract limitations discussion"""
    import re
    patterns = [
        r'(?:研究局限|不足|缺陷)(.+?)[。.]',
        r'本文存在(.+?)不足',
        r'有待进一步(.+?)研究',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)[:150]
    return ''


def _extract_conclusion(content: str) -> str:
    """Extract main conclusion"""
    import re
    patterns = [
        r'(?:研究结论|主要结论|本文结论)(.+?)[。.]',
        r'研究表明(.+?)[。]',
        r'实证结果表明(.+?)[。]',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(0)[:150]
    return ''
