#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject structured resume data into the single-file editor template.

The script NEVER asks a model to rewrite the 50KB editor HTML. It only replaces
the contents of <main id="resume">, preserving every class and data-module hook
so all editor features keep working.

Usage:
    python build_editor.py --data resume.json
    python build_editor.py --data resume.json --template ../../index.html --out my.html --photo me.jpg
"""
import argparse
import base64
import hashlib
import html
import io
import json
import mimetypes
import os
import re
import sys

MAIN_RE = r'<main class="page" id="resume"[^>]*>[\s\S]*?</main>'


def esc(value):
    if value is None:
        return ''
    return html.escape(str(value), quote=False)


def br_lines(values):
    return '<br>'.join(esc(v) for v in (values or []) if str(v).strip())


def render_chips(block):
    chips = block.get('chips') or []
    if not chips:
        return ''
    inner = ''.join(
        '<span class="chip" data-module="chip" data-label="优势标签">%s</span>' % esc(c)
        for c in chips
    )
    return '<div class="chips">%s</div>' % inner


def render_side_blocks(blocks):
    parts = []
    for block in (blocks or []):
        title = esc(block.get('title') or '')
        if block.get('chips'):
            body = render_chips(block)
        else:
            body = '<p>%s</p>' % br_lines(block.get('lines'))
        parts.append(
            '<section class="side-block" data-module="sideblock" data-label="侧栏分区">'
            '<h2>%s</h2>%s\n</section>' % (title, body)
        )
    return ''.join(parts)


def render_numbers(numbers):
    cards = []
    for n in (numbers or [])[:4]:
        cards.append(
            '<div class="number" data-module="number" data-label="数据指标卡片">'
            '<b>%s<span>%s</span></b><strong>%s</strong><span>%s</span></div>'
            % (esc(n.get('value')), esc(n.get('unit')),
               esc(n.get('label')), esc(n.get('note')))
        )
    if not cards:
        return ''
    return '<div class="numbers">%s</div>\n' % ''.join(cards)


def render_bullets(bullets):
    items = []
    for b in (bullets or []):
        if isinstance(b, dict):
            label = b.get('label')
            text = b.get('text') or ''
            prefix = '<b>%s：</b>' % esc(label) if label else ''
            items.append('<li>%s%s</li>' % (prefix, esc(text)))
        else:
            items.append('<li>%s</li>' % esc(b))
    return '<ul>%s</ul>' % ''.join(items) if items else ''


def render_items(items, kind):
    out = []
    for item in (items or []):
        when = '<br>'.join(esc(w) for w in (item.get('when') or []) if str(w).strip())
        if kind == 'timeline':
            org = ('<div class="org">%s</div>' % esc(item['org'])) if item.get('org') else ''
            out.append(
                '<div class="timeline" data-module="timeline" '
                'data-label="时间线 / 工作·实习条目">'
                '<div class="when">%s</div><div class="entry"><h3>%s</h3>%s%s</div></div>\n'
                % (when, esc(item.get('title')), org, render_bullets(item.get('bullets')))
            )
        elif kind == 'project':
            out.append(
                '<div class="project" data-module="project" data-label="项目条目">'
                '<h3>%s</h3><p>%s</p></div>\n'
                % (esc(item.get('title')), esc(item.get('text')))
            )
        elif kind == 'edu':
            org = ('<div class="org">%s</div>' % esc(item['org'])) if item.get('org') else ''
            small = ('<div class="small">%s</div>' % esc(item['small'])) if item.get('small') else ''
            out.append(
                '<div class="edu-highlight" data-module="edu" data-label="教育条目">'
                '<div class="edu-when">%s</div><div><h3>%s</h3>%s%s</div></div>'
                % (when, esc(item.get('title')), org, small)
            )
    return ''.join(out)


ALLOWED_KINDS = {'timeline': 'timeline', 'project': 'project', 'edu': 'edu',
                 'education': 'edu', 'internship': 'timeline', 'work': 'timeline'}


def render_sections(sections):
    parts = []
    for idx, sec in enumerate(sections or []):
        kind = ALLOWED_KINDS.get(str(sec.get('type') or 'timeline').lower())
        if not kind:
            continue
        items = render_items(sec.get('items'), kind)
        if not items:
            continue
        spacer = '<h2 data-module="section" data-label="章节标题"><br></h2>' if idx == 0 else ''
        parts.append(
            '%s<h2 data-module="section" data-label="章节标题">%s</h2>\n%s'
            % (spacer, esc(sec.get('title')), items)
        )
    return ''.join(parts)


def build_main(data, photo_uri):
    summary = ''.join(
        '<p class="summary">%s</p>' % esc(p)
        for p in (data.get('summary') or []) if str(p).strip()
    )
    return (
        '<main class="page" id="resume" contenteditable="true" spellcheck="false">\n'
        '<aside class="side">\n'
        '<div class="photo-wrap"><img class="photo" src="%s" alt="证件照"></div>'
        '<h1>%s</h1><div class="role">%s</div>\n'
        '<div class="meta">%s</div>\n'
        '%s</aside>\n'
        '<section class="main">\n'
        '<header><div class="kicker">%s</div>%s</header>\n'
        '%s%s'
        '</section>\n'
        '</main>'
    ) % (
        photo_uri,
        esc(data.get('name')),
        br_lines(data.get('role')),
        br_lines(data.get('meta')),
        render_side_blocks(data.get('side_blocks')),
        esc(data.get('kicker')),
        summary,
        render_numbers(data.get('numbers')),
        render_sections(data.get('sections')),
    )


def default_photo(template):
    m = re.search(r'<img class="photo" src="([^"]+)"', template)
    if m:
        return m.group(1)
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='290' height='360'>"
        "<rect width='290' height='360' fill='#edf1f5'/>"
        "<circle cx='145' cy='128' r='54' fill='#c2ccd8'/>"
        "<path d='M40 300 Q40 205 145 205 Q250 205 250 300 Z' fill='#c2ccd8'/>"
        "</svg>"
    )
    from urllib.parse import quote
    return 'data:image/svg+xml,' + quote(svg, safe='')


def photo_data_uri(path):
    raw = io.open(path, 'rb').read()
    mime = mimetypes.guess_type(path)[0] or 'image/jpeg'
    return 'data:%s;base64,%s' % (mime, base64.b64encode(raw).decode('ascii'))


def find_template(explicit):
    here = os.path.dirname(os.path.abspath(__file__))
    skill_dir = os.path.dirname(here)
    candidates = [
        explicit,
        os.path.join(skill_dir, 'assets', 'editor-template.html'),
        os.path.join(skill_dir, '..', '..', 'index.html'),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    raise RuntimeError(
        '找不到编辑器模板 index.html。请通过 --template 指定路径，'
        '或把仓库的 index.html 复制到 assets/editor-template.html。\n已尝试：\n  '
        + '\n  '.join(str(c) for c in candidates if c)
    )


def main():
    ap = argparse.ArgumentParser(description='Generate an editable resume HTML from structured JSON.')
    ap.add_argument('--data', required=True, help='结构化简历 JSON 文件路径')
    ap.add_argument('--template', help='编辑器模板 index.html 路径（默认自动查找）')
    ap.add_argument('--out', help='输出 HTML 路径（默认 <姓名>_简历修改器.html）')
    ap.add_argument('--photo', help='可选：证件照路径，内嵌为 data URI')
    args = ap.parse_args()

    try:
        data = json.load(io.open(os.path.abspath(args.data), encoding='utf-8'))
    except Exception as e:
        print('JSON 读取失败：%s' % e, file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not str(data.get('name') or '').strip():
        print('JSON 缺少 name 字段（姓名），无法生成。', file=sys.stderr)
        return 1

    try:
        template_path = find_template(args.template)
        template = io.open(template_path, encoding='utf-8').read()
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    if not re.search(MAIN_RE, template):
        print('模板中没有找到 <main class="page" id="resume">，请确认传入的是编辑器 index.html '
              '而不是导出的纯净版简历。', file=sys.stderr)
        return 1

    if args.photo:
        if not os.path.isfile(args.photo):
            print('找不到照片：%s' % args.photo, file=sys.stderr)
            return 1
        photo_uri = photo_data_uri(args.photo)
    else:
        photo_uri = default_photo(template)

    main_html = build_main(data, photo_uri)
    out_html, n = re.subn(MAIN_RE, lambda m: main_html, template, count=1)
    if n != 1:
        print('模板替换失败。', file=sys.stderr)
        return 1

    name = str(data.get('name'))
    out_html = re.sub(r'(?s)<title>.*?</title>', '<title>%s｜简历</title>' % esc(name),
                      out_html, count=1)

    safe = re.sub(r'[\\/:*?"<>|\r\n]', '_', name).strip() or '我的简历'
    default_name = safe + '_简历修改器.html'
    out_path = os.path.abspath(args.out) if args.out else os.path.abspath(default_name)
    if os.path.isdir(out_path):
        out_path = os.path.join(out_path, default_name)

    # Give each generated resume its own localStorage namespace.
    key = 'resume-editor-' + hashlib.md5(
        (name + os.path.basename(out_path)).encode('utf-8')).hexdigest()[:10]
    out_html = out_html.replace("var KEY='resume-editor-v1';", "var KEY='%s';" % key)

    io.open(out_path, 'w', encoding='utf-8', newline='\n').write(out_html)
    print('已生成：%s' % out_path)
    print('模板：%s' % template_path)
    print('模块数：%d ｜ 文件大小：%d 字节 ｜ 存储键：%s'
          % (main_html.count('data-module='), len(out_html.encode('utf-8')), key))
    print('提示：生成的文件含真实简历，请勿提交到公开仓库；用 Chrome/Edge 双击打开即可继续编辑。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
