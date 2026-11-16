#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract plain text from a resume file.

Standard library only for TXT / MD / HTML / DOCX.
PDF uses an optional backend (pypdf, PyPDF2, pdfplumber or PyMuPDF) when available.

Usage:
    python extract_resume.py input.pdf
    python extract_resume.py input.docx --out resume.txt
"""
import argparse
import html
import io
import os
import re
import sys
import zipfile

ENCODINGS = ('utf-8-sig', 'utf-8', 'gb18030', 'big5', 'latin-1')


def read_text(path):
    raw = io.open(path, 'rb').read()
    for enc in ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace')


def normalize(lines):
    out = []
    for line in lines:
        line = re.sub(r'[\t\xa0\u3000]+', ' ', line)
        line = re.sub(r' +', ' ', line).strip()
        if line:
            out.append(line)
    # collapse 3+ blank lines
    text = '\n'.join(out)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def from_plain(path):
    return normalize(read_text(path).splitlines())


def from_html(path):
    s = read_text(path)
    s = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s)
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</(p|div|li|tr|h[1-6]|section|article)>', '\n', s)
    s = re.sub(r'(?s)<[^>]+>', '', s)
    s = html.unescape(s)
    return normalize(s.splitlines())


def from_docx(path):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.startswith('word/') and n.endswith('.xml')]
        if 'word/document.xml' not in names:
            raise RuntimeError('DOCX 缺少 word/document.xml，可能不是有效的 Word 文档')
        xml = z.read('word/document.xml').decode('utf-8', 'replace')
    paras = re.findall(r'(?s)<w:p\b[^>]*>(.*?)</w:p>', xml)
    lines = []
    for p in paras:
        chunks = re.findall(r'(?s)<w:t\b[^>]*>(.*?)</w:t>', p)
        if not chunks:
            continue
        line = html.unescape(''.join(chunks)).strip()
        if line:
            lines.append(line)
    if not lines:
        raise RuntimeError('DOCX 未提取到文字（可能是扫描件或纯图片文档）')
    return normalize(lines)


def from_pdf(path):
    errors = []
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        text = '\n'.join((p.extract_text() or '') for p in reader.pages)
        if text.strip():
            return normalize(text.splitlines())
    except ImportError:
        errors.append('pypdf')
    except Exception as e:
        errors.append('pypdf: %s' % e)

    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(path)
        text = '\n'.join((p.extract_text() or '') for p in reader.pages)
        if text.strip():
            return normalize(text.splitlines())
    except ImportError:
        errors.append('PyPDF2')
    except Exception as e:
        errors.append('PyPDF2: %s' % e)

    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
        if text.strip():
            return normalize(text.splitlines())
    except ImportError:
        errors.append('pdfplumber')
    except Exception as e:
        errors.append('pdfplumber: %s' % e)

    try:
        import fitz
        doc = fitz.open(path)
        text = '\n'.join(page.get_text() for page in doc)
        if text.strip():
            return normalize(text.splitlines())
    except ImportError:
        errors.append('PyMuPDF')
    except Exception as e:
        errors.append('PyMuPDF: %s' % e)

    raise RuntimeError(
        'PDF_EXTRACTOR_MISSING: 未找到可用的 PDF 文本提取库，且已有库未能读出文字。\n'
        '可选处理：\n'
        '  1) pip install pypdf 后重试；\n'
        '  2) 用 WorkBuddy 自带的 PDF 能力读取该 PDF 并把文本交给后续步骤；\n'
        '  3) 让用户直接粘贴简历文字，或另存为 TXT / DOCX。\n'
        '后端探测：%s' % ', '.join(errors)
    )


EXTRACTORS = {
    '.txt': from_plain, '.md': from_plain, '.markdown': from_plain,
    '.html': from_html, '.htm': from_html,
    '.docx': from_docx,
    '.pdf': from_pdf,
}


def main():
    ap = argparse.ArgumentParser(description='Extract plain text from a resume file.')
    ap.add_argument('input', help='简历文件路径（TXT/MD/HTML/DOCX/PDF）')
    ap.add_argument('--out', help='写入文本文件；省略则输出到 stdout')
    args = ap.parse_args()

    path = os.path.abspath(args.input)
    if not os.path.isfile(path):
        print('找不到文件：%s' % path, file=sys.stderr)
        return 1
    ext = os.path.splitext(path)[1].lower()
    fn = EXTRACTORS.get(ext)
    if fn is None:
        print('不支持的格式 %s。支持：%s' % (ext, ', '.join(sorted(EXTRACTORS))), file=sys.stderr)
        print('图片/扫描件请先 OCR 成文字，或让用户直接粘贴简历内容。', file=sys.stderr)
        return 1

    try:
        text = fn(path)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print('提取失败：%s' % e, file=sys.stderr)
        return 2

    if not text.strip():
        print('未能从文件中提取到文字；请让用户粘贴简历内容。', file=sys.stderr)
        return 2

    if args.out:
        io.open(os.path.abspath(args.out), 'w', encoding='utf-8', newline='\n').write(text + '\n')
        print('已写入：%s（%d 字）' % (os.path.abspath(args.out), len(text)))
    else:
        sys.stdout.write(text + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
