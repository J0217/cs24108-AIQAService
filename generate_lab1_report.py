# -*- coding: utf-8 -*-
"""
生成《软件工程基础》实验一（软件项目计划）报告 PDF。

依据：《软件工程基础-实验报告撰写与提交要求（学生版）V3.0》
范围：本人负责的 E-多端接入（微信小程序 + 开放 API）模块。

运行：py -3.10 generate_lab1_report.py
依赖：reportlab 5.1.0（仅用于报告排版）
"""
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, HRFlowable, Image, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ==================== 基本信息 ====================
COURSE_CLASS = 'cs24108'
STUDENT_ID = '2024210560'
STUDENT_NAME = '金鹏宇'
PROJECT_NO = 'P08'
PROJECT_NAME = '智能问答客服平台'
FULL_PROJECT = f'{PROJECT_NO}{PROJECT_NAME}'
EXPERIMENT = '软件项目计划'
REPORT_DATE = '2026 年 11 月 16 日'
DOC_VERSION = 'V2.5'
SELF_SCORE = 73
SELF_SCORES = [
    ('团队分工与应用端覆盖', 15, 12, '§2.1、表 2-1、表 2-3', 'E2-1、E4-1'),
    ('环境配置完整性', 10, 7, '§7.2、表 7-2、图 1-2', 'E1-1、E1-2'),
    ('仓库与配置管理', 15, 6, '§12.1—§12.3、表 12-1—表 12-3', 'E4-1'),
    ('项目计划完整性', 20, 16, '§3—§11 各节与对应表', 'E5-1'),
    ('论证与调研', 15, 11, '§1.1、§1.2、§16.2', 'E2-1、E2-2'),
    ('模型与设计质量', 15, 12, '图 2-1（§2.1）、图 7-1（§7.2）、图 12-1（§12.3）', 'E3-1'),
    ('证据与可复现', 10, 9, '§1.6、表 1-4、图 1-1—图 1-8', 'E1—E7'),
]

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(ROOT, 'docs', 'assets')
LOGO_PATH = os.path.join(ASSET_DIR, 'school-logo.png')
OUT_FILE = os.path.join(
    ROOT, f'{COURSE_CLASS}-{STUDENT_ID}-{STUDENT_NAME}-{FULL_PROJECT}-实验一{EXPERIMENT}-{SELF_SCORE}分.pdf'
)

# 计划中的 EA 图：文件存在才插入，缺失时只在控制台提示，绝不伪造
PLANNED_FIGURES = [
    ('2-1', '项目组织与接口协作关系', 'fig-2-1-org.png', 'model/AIQAService-Plan.qea'),
    ('7-1', 'dev/test/prod 部署拓扑', 'fig-7-1-deploy.png', 'model/AIQAService-Plan.qea'),
    ('12-1', '分支与配置管理流程', 'fig-12-1-branch.png', 'model/AIQAService-Plan.qea'),
]

# ==================== 字体与样式 ====================
def register_fonts():
    song = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simsun.ttc')
    hei = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf')
    pdfmetrics.registerFont(TTFont('Song', song, subfontIndex=0))
    pdfmetrics.registerFont(TTFont('Hei', hei))
    return 'Song', 'Hei'


SONG, HEI = register_fonts()

BLACK = colors.black
GRAY_BG = colors.HexColor('#EDEDED')
GRAY_LINE = colors.HexColor('#8C8C8C')

STYLES = {
    'body': ParagraphStyle(
        'body', fontName=SONG, fontSize=12, leading=20, alignment=TA_JUSTIFY,
        firstLineIndent=24, spaceAfter=4, wordWrap='CJK',
    ),
    'body_ni': ParagraphStyle(
        'body_ni', fontName=SONG, fontSize=12, leading=20, alignment=TA_JUSTIFY,
        spaceAfter=4, wordWrap='CJK',
    ),
    'h1': ParagraphStyle(
        'h1', fontName=HEI, fontSize=16, leading=22, alignment=TA_LEFT,
        spaceBefore=0, spaceAfter=6,
    ),
    'h2': ParagraphStyle(
        'h2', fontName=HEI, fontSize=13, leading=19, alignment=TA_LEFT,
        spaceBefore=10, spaceAfter=4,
    ),
    'caption': ParagraphStyle(
        'caption', fontName=SONG, fontSize=10.5, leading=15, alignment=TA_CENTER,
        spaceBefore=6, spaceAfter=3,
    ),
    'cell': ParagraphStyle(
        'cell', fontName=SONG, fontSize=10.5, leading=14, alignment=TA_CENTER,
        wordWrap='CJK',
    ),
    'cell_left': ParagraphStyle(
        'cell_left', fontName=SONG, fontSize=10.5, leading=14, alignment=TA_LEFT,
        wordWrap='CJK',
    ),
    'cell_head': ParagraphStyle(
        'cell_head', fontName=HEI, fontSize=10.5, leading=14, alignment=TA_CENTER,
        wordWrap='CJK',
    ),
    'cover_title': ParagraphStyle(
        'cover_title', fontName=SONG, fontSize=26, leading=36, alignment=TA_CENTER,
    ),
    'front_title': ParagraphStyle(
        'front_title', fontName=HEI, fontSize=18, leading=24, alignment=TA_CENTER,
        spaceAfter=12,
    ),
    'part_title': ParagraphStyle(
        'part_title', fontName=HEI, fontSize=20, leading=28, alignment=TA_CENTER,
        spaceBefore=6, spaceAfter=10,
    ),
    'note': ParagraphStyle(
        'note', fontName=SONG, fontSize=9, leading=12, alignment=TA_LEFT, wordWrap='CJK',
    ),
}

CONTENT_WIDTH = 15.0 * cm
MARGIN_LR = 2.6 * cm

# ==================== 页码与目录 ====================
PAGE_REG = {}
FRONT_TOTAL = [0]
BODY_TOTAL = [0]
BODY_START = [0]
WARN_MISSING = [False]


class PageMarker(Flowable):
    """零尺寸标记，记录当前物理页码。"""

    def __init__(self, key):
        super().__init__()
        self.key = key

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        PAGE_REG[self.key] = self.canv.getPageNumber()


class TocLine(Flowable):
    """目录条目：章节名 + 前导点线 + 页码。"""

    def __init__(self, text, page, level=1, width=CONTENT_WIDTH, height=0.72 * cm):
        super().__init__()
        self.text = text
        self.page = str(page)
        self.level = level
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        indent = 0 if self.level == 1 else 0.85 * cm
        c.setFont(HEI if self.level == 1 else SONG, 11 if self.level == 1 else 10.5)
        c.drawString(indent, 0.22 * cm, self.text)
        text_end = indent + c.stringWidth(self.text, HEI if self.level == 1 else SONG, 11 if self.level == 1 else 10.5)
        c.setFont(SONG, 9)
        page_w = c.stringWidth(self.page, SONG, 10.5)
        start = text_end + 0.15 * cm
        end = self.width - page_w - 0.15 * cm
        x = start
        while x < end:
            c.drawString(x, 0.20 * cm, '.')
            x += 0.18 * cm
        c.setFont(SONG, 10.5)
        c.drawRightString(self.width, 0.22 * cm, self.page)


class DottedField(Flowable):
    """封面六行字段：字段名 + 点线 + 填写内容。"""

    def __init__(self, label, value, width=11.6 * cm, height=1.0 * cm):
        super().__init__()
        self.label = label
        self.value = value
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        label = self.label + '：'
        c.setFont(SONG, 13)
        c.drawString(0, 0.25 * cm, label)
        label_w = c.stringWidth(label, SONG, 13)
        avail = self.width - label_w - 0.5 * cm
        value = self.value
        size = 12.0
        while size > 9.0 and c.stringWidth(value, SONG, size) > avail:
            size -= 0.5
        if c.stringWidth(value, SONG, size) > avail:
            while value and c.stringWidth(value + '…', SONG, size) > avail:
                value = value[:-1]
            value = value + '…'
        value_w = c.stringWidth(value, SONG, size)
        start = label_w + 0.2 * cm
        end = self.width - value_w - 0.2 * cm
        c.setFont(SONG, 10)
        x = start
        while x < end:
            c.drawString(x, 0.30 * cm, '·')
            x += 0.19 * cm
        c.setFont(SONG, size)
        c.drawRightString(self.width, 0.25 * cm, value)


def draw_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(SONG, 9)
    canvas.drawCentredString(A4[0] / 2, A4[1] - 1.45 * cm, '2024 计科《软件工程基础》实验报告')
    canvas.setStrokeColor(GRAY_LINE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_LR, A4[1] - 1.65 * cm, A4[0] - MARGIN_LR, A4[1] - 1.65 * cm)

    page = canvas.getPageNumber()
    if page > 1 and FRONT_TOTAL[0] > 0:
        if page <= 1 + FRONT_TOTAL[0]:
            number, total = page - 1, FRONT_TOTAL[0]
        else:
            number, total = page - 1 - FRONT_TOTAL[0], BODY_TOTAL[0]
        canvas.setFont(SONG, 9)
        canvas.drawCentredString(A4[0] / 2, 1.25 * cm, f'第 {number} 页 / 共 {total} 页')
    canvas.restoreState()


# ==================== 目录与图表索引定义 ====================
CHAPTERS = [
    ('c1', '一 项目简介', [
        ('s1-1', '1.1 项目背景与定位'),
        ('s1-2', '1.2 建设目标与范围'),
        ('s1-3', '1.3 E 模块职责与交付物'),
        ('s1-4', '1.4 本阶段交付物与原型边界'),
        ('s1-5', '1.5 端、入口与鉴权方式'),
        ('s1-6', '1.6 证据清单'),
    ]),
    ('c2', '二 项目组织', [
        ('s2-1', '2.1 组织原则与纵向分工'),
        ('s2-2', '2.2 E 模块负责人职责'),
        ('s2-3', '2.3 与 A—D 模块的接口协作'),
        ('s2-4', '2.4 本人在本实验中的任务与产出'),
    ]),
    ('c3', '三 项目任务', [
        ('s3-1', '3.1 WBS 分解方法'),
        ('s3-2', '3.2 E 模块 WBS'),
        ('s3-3', '3.3 WBS 校验'),
        ('s3-4', '3.4 关键路径与缓冲'),
    ]),
    ('c4', '四 进度计划', [
        ('s4-1', '4.1 进度基线'),
        ('s4-2', '4.2 里程碑'),
        ('s4-3', '4.3 进度控制与纠偏'),
    ]),
    ('c5', '五 成本计划', [
        ('s5-1', '5.1 成本估算口径'),
        ('s5-2', '5.2 人力成本'),
        ('s5-3', '5.3 非人力成本与不可预见费'),
        ('s5-4', '5.4 成本监控'),
    ]),
    ('c6', '六 质量计划', [
        ('s6-1', '6.1 质量目标'),
        ('s6-2', '6.2 质量活动与检查点'),
        ('s6-3', '6.3 缺陷管理'),
    ]),
    ('c7', '七 资源计划', [
        ('s7-1', '7.1 人力资源'),
        ('s7-2', '7.2 环境资源'),
        ('s7-3', '7.3 工具与版本'),
        ('s7-4', '7.4 资源日历'),
    ]),
    ('c8', '八 沟通计划', [
        ('s8-1', '8.1 沟通对象与内容'),
        ('s8-2', '8.2 会议与渠道'),
        ('s8-3', '8.3 接口变更沟通'),
    ]),
    ('c9', '九 风险计划', [
        ('s9-1', '9.1 风险识别与评估口径'),
        ('s9-2', '9.2 风险登记册'),
        ('s9-3', '9.3 高优先级风险应对'),
    ]),
    ('c10', '十 采购计划', [
        ('s10-1', '10.1 采购原则'),
        ('s10-2', '10.2 软件与许可证'),
        ('s10-3', '10.3 采购预算与获取方式'),
    ]),
    ('c11', '十一 干系人管理', [
        ('s11-1', '11.1 干系人识别'),
        ('s11-2', '11.2 参与策略'),
        ('s11-3', '11.3 期望管理'),
    ]),
    ('c12', '十二 配置管理', [
        ('s12-1', '12.1 配置项识别'),
        ('s12-2', '12.2 基线与版本'),
        ('s12-3', '12.3 分支与提交规范'),
        ('s12-4', '12.4 变更控制'),
        ('s12-5', '12.5 AI 辅助记录与留痕'),
        ('s12-6', '12.6 文档修订记录'),
    ]),
    ('c13', '十三 沟通计划方式', [
        ('s13-1', '13.1 沟通方式与适用场景'),
        ('s13-2', '13.2 变更请求处理流程'),
        ('s13-3', '13.3 本实验已执行的变更'),
    ]),
    ('c14', '十四 立项背景与整体目标', [
        ('s14-1', '14.1 项目背景'),
        ('s14-2', '14.2 整体目标与范围'),
    ]),
    ('c15', '十五 组织与协作', [
        ('s15-1', '15.1 五条业务线与责任边界'),
        ('s15-2', '15.2 接口对接与协作机制'),
    ]),
    ('c16', '十六 整体成果与技术结论', [
        ('s16-1', '16.1 已实现的整体能力'),
        ('s16-2', '16.2 技术结论'),
        ('s16-3', '16.3 已知差距'),
    ]),
    ('c17', '十七 过程复盘', [
        ('s17-1', '17.1 做得好的'),
        ('s17-2', '17.2 问题与改进'),
    ]),
]

TABLE_TITLES = [
    ('1-1', '项目范围与 E 模块边界'),
    ('1-2', 'E 模块交付物清单'),
    ('1-3', '端、入口与鉴权方式'),
    ('1-4', '证据清单'),
    ('2-1', '项目组纵向分工与五段产出'),
    ('2-2', 'E 模块负责人职责'),
    ('2-3', 'E 模块与 A—D 的接口依赖'),
    ('2-4', '本人在实验一中的任务与产出'),
    ('2-5', '个人任务清单与状态'),
    ('3-1', 'E 模块 WBS'),
    ('3-2', 'WBS 校验结果'),
    ('4-1', 'E 模块进度基线'),
    ('4-2', 'E 模块里程碑'),
    ('4-3', '进度偏差与纠偏'),
    ('5-1', '人力成本估算'),
    ('5-2', '非人力成本与不可预见费'),
    ('5-3', '成本基线与监控口径'),
    ('6-1', '质量目标与量化指标'),
    ('6-2', '质量活动与检查点'),
    ('6-3', '缺陷记录'),
    ('7-1', '人力资源分配'),
    ('7-2', '三套环境对照'),
    ('7-3', '工具与版本清单'),
    ('7-4', '资源日历'),
    ('8-1', '沟通矩阵'),
    ('8-2', '会议与沟通节奏'),
    ('9-1', '风险登记册'),
    ('9-2', '高优先级风险应对'),
    ('10-1', '软件与许可证清单'),
    ('10-2', '采购预算与获取方式'),
    ('11-1', '干系人登记表'),
    ('11-2', '干系人参与策略'),
    ('12-1', '配置项清单'),
    ('12-2', '基线定义'),
    ('12-3', '分支与提交规范'),
    ('12-4', '变更控制流程'),
    ('12-5', 'AI 辅助记录'),
    ('12-6', '文档修订记录'),
    ('13-1', '本实验已执行的变更'),
    ('14-1', '整体能力清单'),
    ('15-1', '业务线与责任边界'),
    ('16-1', '原型模块与接口对应'),
    ('16-2', '技术选型结论'),
    ('17-1', '问题与改进'),
    ('18-1', '逐项自评依据'),
    ('18-2', '达标清单'),
]

TABLE_PAGES = {}
FIGURE_ENTRIES = []


# ==================== 内容构件 ====================
def P(text):
    return Paragraph(text, STYLES['body'])


def PNI(text):
    return Paragraph(text, STYLES['body_ni'])


def H1(story, key, text, first=False):
    if not first:
        story.append(PageBreak())
    story.append(PageMarker('h1:' + key))
    story.append(Paragraph(text, STYLES['h1']))
    story.append(HRFlowable(width='100%', thickness=0.6, color=BLACK, spaceBefore=2, spaceAfter=8))


def H2(story, key, text):
    story.append(PageMarker('h2:' + key))
    story.append(Paragraph(text, STYLES['h2']))


_CELL_STYLES = {}


def cell_style(left=False, size=10.5):
    key = (left, size)
    if key not in _CELL_STYLES:
        _CELL_STYLES[key] = ParagraphStyle(
            f'cell_{int(left)}_{size}', fontName=SONG, fontSize=size,
            leading=size * 1.35, alignment=TA_LEFT if left else TA_CENTER,
            wordWrap='CJK',
        )
    return _CELL_STYLES[key]


def T(story, num, title, headers, rows, widths, left_cols=(0,), font_size=10.5, keep=True):
    header = [Paragraph(str(h), cell_style(False, font_size)) for h in headers]
    data = [header]
    for row in rows:
        cells = []
        for idx, cell in enumerate(row):
            p = Paragraph(str(cell), cell_style(idx in left_cols, font_size))
            cells.append(p)
        data.append(cells)
    table = Table(data, colWidths=[w * cm for w in widths], repeatRows=1, splitByRow=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), GRAY_BG),
        ('TEXTCOLOR', (0, 0), (-1, -1), BLACK),
        ('FONTNAME', (0, 0), (-1, -1), SONG),
        ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, BLACK),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    table.setStyle(TableStyle(style_cmds))
    caption = Paragraph(f'表 {num}　{title}', STYLES['caption'])
    block = [PageMarker('table:' + num), caption, table, Spacer(1, 4)]
    if keep and len(rows) <= 9:
        story.append(KeepTogether(block))
    else:
        story.extend(block)


def figure(story, num, title, filename, source, note=None):
    path = os.path.join(ASSET_DIR, filename)
    if not os.path.exists(path):
        return False
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    width = min(13.5 * cm, CONTENT_WIDTH)
    height = width * ih / iw
    if height > 17 * cm:
        height = 17 * cm
        width = height * iw / ih
    img = Image(path, width=width, height=height)
    img.hAlign = 'CENTER'
    story.append(KeepTogether([
        PageMarker('figure:' + num),
        img,
        Paragraph(f'图 {num}　{title}', STYLES['caption']),
        Paragraph(note or f'绘制：EA 17 手工绘制・源文件 {source}', STYLES['note']),
    ]))
    return True


def part_divider(story, key, title, subtitle):
    story.append(PageBreak())
    story.append(PageMarker('h1:' + key))
    story.append(Spacer(1, 7 * cm))
    story.append(Paragraph(title, STYLES['part_title']))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width='55%', thickness=0.8, color=BLACK, hAlign='CENTER'))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(subtitle, STYLES['caption']))
    story.append(PageBreak())


# ==================== 封面 + 目录 ====================
def cover(story):
    story.append(Spacer(1, 1.4 * cm))
    if os.path.exists(LOGO_PATH):
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(LOGO_PATH).getSize()
        w = 4.0 * cm
        h = w * ih / iw
        logo = Image(LOGO_PATH, width=w, height=h)
        logo.hAlign = 'CENTER'
        story.append(logo)
    else:
        print('[缺失] docs/assets/school-logo.png 校徽，封面无法合规')
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph('《软件工程基础》实验报告', STYLES['cover_title']))
    story.append(Spacer(1, 2.0 * cm))

    fields = [
        ('实验名称', EXPERIMENT),
        ('报告名称', f'{FULL_PROJECT}{EXPERIMENT}报告'),
        ('项目组别', COURSE_CLASS),
        ('项目名称', FULL_PROJECT),
        ('报告时间', REPORT_DATE),
        ('文档版本', DOC_VERSION),
    ]
    center = Table([[DottedField(k, v)] for k, v in fields], colWidths=[12.0 * cm])
    center.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(center)
    story.append(Spacer(1, 1.2 * cm))


def front_matter(page_reg):
    story = []
    story.append(PageMarker('front:start'))
    story.append(Paragraph('目　录', STYLES['front_title']))
    story.append(TocLine('个人报告部分', page_reg.get('h1:personal', 0), level=1))
    for key, title, subs in CHAPTERS:
        if key == 'c14':
            story.append(TocLine('小组报告部分', page_reg.get('h1:group', 0), level=1))
        page = page_reg.get('h1:' + key, 0)
        story.append(TocLine(title, page, level=1))
        for skey, stitle in subs:
            story.append(TocLine(stitle, page_reg.get('h2:' + skey, 0), level=2))
    page = page_reg.get('h1:self', 0)
    story.append(TocLine('自我测评', page, level=1))
    story.append(TocLine('参考文献', page_reg.get('h1:ref', 0), level=1))

    story.append(PageBreak())
    if FIGURE_ENTRIES:
        story.append(Paragraph('图目录', STYLES['front_title']))
        for num, title in FIGURE_ENTRIES:
            story.append(TocLine(f'图 {num}　{title}', page_reg.get('figure:' + num, 0), level=1))
        story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph('表目录', STYLES['front_title']))
    for num, title in TABLE_TITLES:
        story.append(TocLine(f'表 {num}　{title}', page_reg.get('table:' + num, 0), level=1))
    return story


# ==================== 正文（个人报告部分） ====================
def personal_part(story):
    # ---------- 一 项目简介 ----------
    H1(story, 'c1', '一 项目简介', first=True)
    H2(story, 's1-1', '1.1 项目背景与定位')
    story.append(P(
        f'本项目为课程实验项目 {FULL_PROJECT}，面向中小企业的在线客服场景，'
        '用微信小程序和开放 API 两条通道接入同一套智能问答能力。项目组共 5 人，按 A—E 五条业务线纵向分工；'
        '我负责 E-多端接入，交付物是小程序端与对外开放接口。'
    ))
    story.append(P(
        '项目名称在封面、正文、README、源码包与问答册中统一使用“P08智能问答客服平台”，不混用简称。'
        '项目仓库名为 cs24108-AIQAService，与分组名单中的班组和项目简称一致。'
    ))
    H2(story, 's1-2', '1.2 建设目标与范围')
    story.append(P(
        '建设目标是让用户在小程序里完成登录、选场景、提问、看回复与历史，让外部系统通过带 API Key 的接口获取同样的问答能力。'
        '两条通道共用 A 对话引擎的会话与消息、B 知识库的检索结果、C 意图路由的场景与 FAQ、D 管理后台的登录与用户信息；'
        '公告推送和自动回复模板由 E 模块自己维护。E 只做接入、鉴权、界面和联调，不重复实现别人的业务。'
    ))
    story.append(PNI('范围与边界见表 1-1。'))
    T(story, '1-1', '项目范围与 E 模块边界',
      ['范围项', '包含内容', '不在 E 模块范围', '责任归属'],
      [
          ['小程序端', '登录、首页公告数、场景切换、快捷问题、消息收发、历史记录', '页面视觉设计与运营文案', '本人'],
          ['开放 API', '/api/v1 下 4 个接口与统一 X-API-Key 鉴权', 'AI 回复内容生成、会话存储逻辑', '本人（调用 B/C）'],
          ['依赖接口', '登录、会话、消息、场景、快捷回复、知识库检索', '接口内部实现与库表维护', 'A—D 四条业务线'],
          ['运行环境', '开发环境、测试环境、依赖清单', '生产服务器采购与上线审批', '本人（生产由组内共同确认）'],
          ['文档', 'README、操作手册、问答册、本报告 E 部分', '其他成员负责模块的设计文档', '本人'],
      ],
      [3.0, 5.6, 4.2, 2.2])

    H2(story, 's1-3', '1.3 E 模块职责与交付物')
    story.append(P(
        'E 模块有两条对外通道：E1 微信小程序，负责登录、首页、对话页与交互状态；'
        'E2 开放 API，负责 /api/v1 下的统一鉴权和四个接口。两条通道都不直接调用其他模块的内部函数，'
        '只通过路由和模型层调用，便于单独测试。'
    ))
    T(story, '1-2', 'E 模块交付物清单',
      ['编号', '交付物', '位置', '验收口径'],
      [
          ['E1-1', '小程序全局请求与登录封装', 'miniprogram/app.js', 'Token 注入、ensureLogin 可复用'],
          ['E1-2', '首页（登录、公告数、入口）', 'miniprogram/pages/index/', '未登录可登录，登录后展示入口'],
          ['E1-3', '对话页（场景、快捷问题、消息）', 'miniprogram/pages/chat/', '5 个场景可切换，消息可收发'],
          ['E2-1', '开放 API 路由与鉴权', 'backend/routes/api.py', '4 个接口均校验 X-API-Key'],
          ['E2-2', '接口测试', 'test/test_e_module.py、test_improvements.py', '7+14 条用例全部通过'],
          ['E2-3', '使用与部署说明', 'README.md、docs/操作手册.md', '他机可按步骤启动'],
          ['E2-4', '本实验报告与问答册', 'docs/、本 PDF', '十三节齐全、问答一致'],
      ],
      [1.8, 4.6, 5.6, 3.0])

    H2(story, 's1-4', '1.4 本阶段交付物与原型边界')
    story.append(P(
        '本阶段交付的是可运行的系统原型，不是最终成品。小程序在微信开发者工具中以游客模式编译预览，'
        '后端在本机 5000 端口运行，数据库为 SQLite 单文件。生产部署、真实 AppID 登录和 PostgreSQL 都还没做，'
        '报告里按现状写，不写成已完成。'
        '原型用于验证双端接入、鉴权和主流程是否成立，后续实验再补齐设计、测试与部署。'
    ))
    T(story, '1-3', '端、入口与鉴权方式',
      ['端', '入口', '鉴权', '已验证内容', '尚未覆盖'],
      [
          ['小程序', 'miniprogram/（微信开发者工具）', 'JWT（Authorization: Bearer）', '登录、会话、消息、场景接口', '真实 AppID 真机登录、发布审核'],
          ['开放API', 'http://localhost:5000<br/>/api/v1', 'X-API-Key 请求头', '4 个接口与 401/400 分支', '公网部署、调用方配额'],
          ['管理端', 'templates/ 页面', 'JWT + 管理员角色', '非本人负责，仅确认接口存在', '不纳入 E 模块交付'],
      ],
      [1.6, 4.6, 3.4, 2.8, 2.6], font_size=9.5)

    H2(story, 's1-5', '1.5 术语与端覆盖')
    story.append(P(
        '文中“小程序端”指 miniprogram 目录下的微信小程序；“开放 API”指 /api/v1 前缀的对外接口；'
        '“场景”指 general、product、after_sales、technical、ordering 五类问题域；“模板命中”指问题与 quick_replies 表中的问题、关键词、相似度匹配达到阈值。'
        '全文只用这一套叫法，不用“前端”“接口层”等混称。'
    ))
    H2(story, 's1-6', '1.6 证据清单')
    story.append(P(
        '本报告使用的证据按 E1—E7 七类编号，状态按实际情况标注为达成、部分达成、未达成。'
        '没达成的在自我测评里写清原因，没有用示意图或虚构截图顶上。'
        '截图均为本机实拍，按编号顺序排在表 1-4 之后，图号与表内说明一一对应。'
    ))
    T(story, '1-4', '证据清单',
      ['编号', '证据内容', '所在章节', '状态', '说明'],
      [
          ['E1-1', 'Python 3.14.6 与运行依赖版本', '§7.2、表 7-3', '达成', '图 1-1，终端输出与表 7-3 一致'],
          ['E1-2', '后端启动与端口监听', '§7.2', '达成', '图 1-2，5000 端口监听；prod 未部署'],
          ['E2-1', '工程目录与依赖清单', '§1.3、§7.3', '达成', '图 1-3，目录树与 requirements.txt 可核对'],
          ['E2-2', '小程序与 API 源码', '§2.3、§12.1', '达成', '仓库与本地文件一致'],
          ['E3-1', 'EA 工程与模型树', '§2.1、§7.2、§12.3', '达成', '图 1-4，EA 17 手工绘制三图'],
          ['E4-1', '仓库首页、分支、提交记录', '§12.3', '达成', '图 1-5，main 分支 3 次提交；develop 与 feature 未建'],
          ['E5-1', '接口测试运行结果', '§6.2、表 6-3', '达成', '图 1-6，冒烟 7 条与改进项 14 条全部通过'],
          ['E5-2', '开放 API 鉴权分支（401/200）', '§6.2、表 1-3', '达成', '图 1-7，401、401、200 三态可对照'],
          ['E6-1', '小程序运行界面', '§1.4', '未达成', '开发者工具截图未完成'],
          ['E7-1', '操作手册', '§7.2、docs/操作手册.md', '达成', '图 1-8，启动与 API 两节可核对'],
      ],
      [1.1, 3.6, 3.2, 1.5, 5.6], font_size=9.5)
    figure(story, '1-1', '运行环境与依赖版本核验（E1-1）', 'shot-e1-1-env.png', '',
           note='来源：本机 PowerShell 实拍・文件 docs/assets/shot-e1-1-env.png')
    figure(story, '1-2', '后端启动与 5000 端口监听（E1-2）', 'shot-e1-2-start-crop.png', '',
           note='来源：本机 PowerShell 实拍・文件 docs/assets/shot-e1-2-start.png（裁去重复窗口）')
    figure(story, '1-3', '工程目录与接口实现（E2-1）', 'shot-e2-1-tree.png', '',
           note='来源：本机 VS Code 实拍・文件 docs/assets/shot-e2-1-tree.png')
    figure(story, '1-4', 'EA 工程与模型树（E3-1）', 'shot-e3-1-ea.png', '',
           note='来源：EA 17 工程实拍・文件 docs/assets/shot-e3-1-ea.png')
    figure(story, '1-5', '仓库提交与分支记录（E4-1）', 'shot-e4-1-repo.png', '',
           note='来源：本机浏览器与终端实拍・文件 docs/assets/shot-e4-1-repo.png')
    figure(story, '1-6', '接口测试运行结果（E5-1，21 条全部通过）', 'shot-e5-1-test-crop.png', '',
           note='来源：本机 PowerShell 实拍・文件 docs/assets/shot-e5-1-test.png（裁去空白区域）')
    figure(story, '1-7', '开放 API 鉴权分支对比（E5-2）', 'shot-e5-2-401-crop.png', '',
           note='来源：本机 PowerShell 实拍・文件 docs/assets/shot-e5-2-401.png（裁去空白区域）')
    figure(story, '1-8', '操作手册的启动与 API 说明（E7-1）', 'shot-e7-1-manual.png', '',
           note='来源：本机 VS Code 实拍・文件 docs/assets/shot-e7-1-manual.png')

    # ---------- 二 项目组织 ----------
    H1(story, 'c2', '二 项目组织')
    H2(story, 's2-1', '2.1 组织原则与纵向分工')
    story.append(P(
        '项目组按业务功能纵向切分，每人负责一条业务线，从需求、设计、编码、测试做到运维，不按前端、后端、数据库、测试横向分人[1]。'
        'A 对话引擎（Web 前端）由荣宇负责，B 知识库（Web 后端）由曾明琦负责、荣宇兼做检索接口，'
        'C 意图路由（Web 后端）由李博负责，D 管理后台（Web 前端）由冯昊负责，我负责 E 多端接入。'
        '五个人平级，谁的业务谁拍板，进度和接口在周五例会上对齐，需要跨模块确认的事项当场定、当天记进 Issue。'
        '同一块业务只有一个第一负责人，跨模块协作通过接口清单约定，不写成“共同负责”。'
    ))
    if not figure(story, '2-1', '项目组织与接口协作关系', 'fig-2-1-org.png', 'model/AIQAService-Plan.qea',
                  note='绘制：EA 17 手工绘制・源文件 model/AIQAService-Plan.qea・图中 A—D 为原型阶段的后台模块划分，正式分工见表 2-1') and WARN_MISSING[0]:
        print('[缺失] 图 2-1（EA 组织/组件图）未插入：docs/assets/fig-2-1-org.png')
    T(story, '2-1', '项目组纵向分工与五段产出',
      ['成员', '业务线', '需求产出', '设计产出', '编码产出', '测试与运维产出'],
      [
          ['荣宇<br/>2024212411', 'A-对话引擎<br/>（Web 前端）', '消息收发、会话管理需求', '对话界面结构与多模型切换', '对话页、SSE 流式组件', '对话页联调、流式回归'],
          ['曾明琦<br/>2024210561', 'B-知识库<br/>（Web 后端）', '文档上传、分段、检索需求', '知识库表结构与检索接口', '文档管理 API、向量库接入', '检索召回抽测'],
          ['李博<br/>2024210582', 'C-意图路由<br/>（Web 后端）', '意图分类、FAQ 匹配、转人工需求', '意图分类与路由规则、工单模型', '意图/FAQ/转人工接口、工单系统', '分类准确率抽测'],
          ['冯昊<br/>2024213335', 'D-管理后台<br/>（Web 前端）', '质量评分、用户管理需求', '后台页面结构与看板指标', 'React 页面、ECharts 报表', '报表数据核对'],
          ['金鹏宇<br/>2024210560', 'E-多端接入<br/>（小程序+API）', '双端接入与鉴权需求', '页面流与接口契约', 'miniprogram/、api.py', '冒烟测试、操作手册'],
      ],
      [2.3, 2.4, 2.6, 2.6, 2.6, 2.5], font_size=9)

    H2(story, 's2-2', '2.2 E 模块负责人职责')
    story.append(P(
        '我的职责是把后台能力接到小程序和外部系统上，并对两条通道的可用性、鉴权和联调结果负责。'
        '我不改 A—D 四条业务线的规则；发现接口与约定不一致时，先提变更申请，由对应模块的负责人确认后再改。'
    ))
    T(story, '2-2', 'E 模块负责人职责',
      ['职责项', '具体内容', '产出', '完成判据'],
      [
          ['接入设计', '页面流、请求封装、鉴权头、错误提示', '接口清单与页面说明', '两端均可独立调用'],
          ['小程序实现', '登录、首页、对话页、场景与快捷问题', 'miniprogram/ 源码', '开发者工具可编译预览'],
          ['开放 API 实现', '4 个接口与统一 X-API-Key 校验', 'backend/routes/api.py', '401/400/200 分支可验证'],
          ['联调与测试', '接口冒烟、异常分支、文档', 'test/test_e_module.py、操作手册', '21 条用例通过、手册可照做'],
          ['变更与留痕', '接口变更记录、版本说明', '变更表与提交记录', '每次变更可追溯'],
      ],
      [2.6, 5.6, 4.2, 2.6])

    H2(story, 's2-3', '2.3 与 A—D 模块的接口协作')
    story.append(P(
        'E 模块依赖 8 个内部接口，全部走 HTTP 路由，不跨模块直接读表。接口清单在实验一定稿，实验二按需求细化字段；'
        '任何路径、字段或鉴权方式的改动都要走变更流程。其中 D 的 wx-login 决定登录态，A 的会话与消息接口决定对话页能否走通，'
        'C 的场景与快捷回复决定入口好不好用，B 的检索接口决定回答有没有依据，这四处是我联调时最先验证的。'
        '表 2-3 中的知识库检索接口属实验二范围，原型阶段还没接，回答仍由模板和本地兜底生成，这一点在 §16.3 也写了。'
    ))
    T(story, '2-3', 'E 模块与 A—D 的接口依赖',
      ['接口', '方法', '路径', '提供方', '鉴权', 'E 模块用途'],
      [
          ['微信登录', 'POST', '/api/auth/wx-login', 'D<br/>冯昊', '无（code）', '换取 JWT'],
          ['用户信息', 'GET', '/api/auth/profile', 'D<br/>冯昊', 'JWT', '首页展示登录态'],
          ['会话列表', 'GET', '/api/chat/conversations', 'A<br/>荣宇', 'JWT', '进入对话页取最近会话'],
          ['新建会话', 'POST', '/api/chat/conversations', 'A<br/>荣宇', 'JWT', '无会话时创建'],
          ['消息收发', 'POST', '/api/chat/conversations/:id/messages', 'A<br/>荣宇', 'JWT', '发送问题、取回复'],
          ['场景列表', 'GET', '/api/chat/scenes', 'C<br/>李博', 'JWT', '场景选择器'],
          ['快捷回复', 'GET', '/api/chat/quick-replies', 'C<br/>李博', 'JWT', '快捷问题'],
          ['知识库检索', 'POST', '/api/kb/search', 'B<br/>曾明琦', 'JWT', '取 RAG 依据片段（实验二接入）'],
      ],
      [2.2, 1.1, 5.0, 1.6, 1.8, 3.3], font_size=9.5)

    H2(story, 's2-4', '2.4 本人在本实验中的任务与产出')
    story.append(P(
        '实验一按计划类工作统计，共 6 人时，内容是对齐范围、拆任务、算成本与风险、写报告。'
        '同期我把 E 模块的实现和缺陷修复也做完了，这部分工作量没有计进实验一的 6 人时，改动明细见表 13-1。'
        '我评审的对象是 README 里的接口清单和 api.py 的路由是否对得上，以及 21 条接口用例（冒烟 7 条、改进项 14 条）有没有覆盖鉴权和主流程。'
    ))
    T(story, '2-4', '本人在实验一中的任务与产出',
      ['任务', '工时（人时）', '产出', '评审对象'],
      [
          ['核对项目范围与 E 模块边界', '1.0', '表 1-1、表 1-3', 'README 与源码目录'],
          ['拆 WBS 与排进度', '2.0', '表 3-1、表 4-1', '任务粒度与依赖'],
          ['成本、风险、沟通测算', '1.5', '表 5-1、表 9-1、表 8-1', '数字合计与责任人'],
          ['报告统稿、自评与问答册', '1.5', '本 PDF、问答册', '与正文一致性'],
      ],
      [6.0, 2.4, 3.6, 3.0])
    T(story, '2-5', '个人任务清单与状态',
      ['类别', '任务', '状态', '依据'],
      [
          ['计划', '范围与边界核对、接口清单与页面流', '已完成', '表 1-1、表 2-3、§1.4'],
          ['计划', 'WBS、进度基线、里程碑与关键路径', '已完成', '表 3-1、表 4-1、表 4-2'],
          ['计划', '成本、质量、风险、沟通、采购、干系人', '已完成', '第五章至第十一章'],
          ['计划', '报告、问答册、操作手册', '已完成', 'docs/ 与本 PDF'],
          ['实现', '小程序登录、首页、对话页、公告中心', '已完成', 'miniprogram/，游客模式编译通过'],
          ['实现', '开放 API 4 个接口、X-API-Key 鉴权与限流', '已完成', 'api.py、ratelimit.py，21 条用例'],
          ['修复', '缺陷 D-001 至 D-003 的定位、修复与复测', '已完成', '表 6-3'],
          ['留痕', '仓库提交与文档版本记录', '已完成，2 次提交', '§12.6、Git 日志'],
      ],
      [1.6, 7.4, 3.0, 3.0], font_size=9)

    # ---------- 三 项目任务 ----------
    H1(story, 'c3', '三 项目任务')
    H2(story, 's3-1', '3.1 WBS 分解方法')
    story.append(P(
        'WBS 按“模块—阶段—任务包”分三层，编码采用 1、1.1、1.1.1 的形式。'
        '任务包粒度控制在 4—16 人时，每个包有唯一负责人、交付物和前置依赖，避免出现无法验收的任务[1]。'
        'E 模块共 6 个任务包、28 人时，全部由我负责。'
    ))
    H2(story, 's3-2', '3.2 E 模块 WBS')
    T(story, '3-1', 'E 模块 WBS',
      ['WBS 编码', '任务名称', '交付物', '工时（人时）', '前置依赖', '负责人'],
      [
          ['1', 'E-多端接入', '小程序端 + 开放 API', '28', '—', '本人'],
          ['1.1', '需求与设计', '接口清单、页面流', '8', '实验二需求基线', '本人'],
          ['1.1.1', '双端接入需求梳理', '需求要点与边界', '4', '—', '本人'],
          ['1.1.2', '页面流与接口契约', '页面说明、接口表', '4', '1.1.1', '本人'],
          ['1.2', '编码实现', '小程序与 API 源码', '16', '1.1', '本人'],
          ['1.2.1', '登录与首页', 'app.js、index 页', '4', '1.1.2、A 登录接口', '本人'],
          ['1.2.2', '对话页交互', 'chat 页、场景与快捷问题', '8', '1.1.2、B 会话接口', '本人'],
          ['1.2.3', '开放 API 与鉴权', 'api.py、4 个接口', '4', '1.1.2、C 回复服务', '本人'],
          ['1.3', '验证与交付', '测试结果、操作手册', '4', '1.2', '本人'],
          ['1.3.1', '联调、冒烟与文档', '21 条用例、手册', '4', '1.2.3', '本人'],
      ],
      [1.6, 3.6, 3.4, 1.8, 3.4, 1.2], font_size=9.5)

    H2(story, 's3-3', '3.3 WBS 校验')
    story.append(P(
        '校验从覆盖、均衡、依赖三方面做。覆盖看需求、设计、编码、测试、文档五段是否都有任务包；'
        '均衡看工时是否落在 4—16 人时；依赖看是否存在环和断头。'
    ))
    T(story, '3-2', 'WBS 校验结果',
      ['校验项', '检查内容', '结果', '依据'],
      [
          ['覆盖', '五段产出均有任务包', '通过', '表 3-1 的 1.1—1.3'],
          ['均衡', '任务包 4—16 人时', '通过', '最小 4、最大 8'],
          ['依赖', '无环、无断头', '通过', '1.1→1.2→1.3 单向'],
          ['可点数', '每人任务、工时、交付物清楚', '通过', '表 3-1 与表 2-4'],
      ],
      [2.6, 5.6, 2.0, 4.8])

    H2(story, 's3-4', '3.4 关键路径与缓冲')
    story.append(P(
        'E 模块关键路径为 1.1.1→1.1.2→1.2.1→1.2.2→1.3.1，共 24 人时；1.2.3 可与 1.2.2 并行，因此计划总投入 28 人时。'
        '在第 6 周预留 2 人时缓冲，用于接口字段调整或小程序编译问题。关键路径上任何一项延期超过 2 人时，就触发进度纠偏。'
    ))

    # ---------- 四 进度计划 ----------
    H1(story, 'c4', '四 进度计划')
    H2(story, 's4-1', '4.1 进度基线')
    story.append(P(
        '项目按 8 周排期，W1 对应第 10 教学周（2026-11-09 至 11-15），W8 对应第 17 教学周（2026-12-28 至 2027-01-03）。'
        '实验一计划基线在 2026-11-16 冻结，之后的需求、设计、编码按课程实验节点推进。'
    ))
    rows = []
    plan = {
        '1.1.1': ('需求梳理', '█', '', '', '', '', '', '', ''),
        '1.1.2': ('接口契约', '', '█', '', '', '', '', '', ''),
        '1.2.1': ('登录与首页', '', '', '█', '', '', '', '', ''),
        '1.2.2': ('对话页交互', '', '', '', '█', '█', '', '', ''),
        '1.2.3': ('开放 API', '', '', '', '', '█', '█', '', ''),
        '1.3.1': ('联调与文档', '', '', '', '', '', '█', '█', ''),
    }
    for code, (name, *marks) in plan.items():
        rows.append([code, name] + list(marks))
    T(story, '4-1', 'E 模块进度基线',
      ['任务', '名称', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'],
      rows,
      [1.8, 3.0, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27, 1.27], font_size=9)

    H2(story, 's4-2', '4.2 里程碑')
    T(story, '4-2', 'E 模块里程碑',
      ['里程碑', '时间', '完成判据', '责任人'],
      [
          ['M1 计划基线', '2026-11-16', '十三节报告、WBS、接口清单定稿', '本人'],
          ['M2 接口契约冻结', '2026-11-29', '8 个依赖接口路径与字段确认', '本人 + A—D 负责人'],
          ['M3 主流程跑通', '2026-12-20', '登录→选场景→提问→回复→历史可演示', '本人'],
          ['M4 交付验证', '2027-01-03', '测试 7/7、手册可照做、证据齐全', '本人'],
      ],
      [3.0, 2.8, 6.4, 2.8])

    H2(story, 's4-3', '4.3 进度控制与纠偏')
    story.append(P(
        '进度以周为单位对照基线检查。每周末记录计划完成量与实际完成量，偏差超过 2 人时就调整下周任务或申请顺延，并写入变更记录。'
        '纠偏优先保证关键路径，非关键任务可以后移。'
    ))
    T(story, '4-3', '进度偏差与纠偏',
      ['偏差情形', '判定阈值', '纠偏动作', '审批'],
      [
          ['关键路径任务延期', '超过 2 人时', '下周优先补做，暂停非关键任务', '周五例会确认'],
          ['接口未按期冻结', '晚于 M2 一天', '发起接口变更评审，冻结前不编码', '本人 + 接口提供方'],
          ['测试不通过', '阻断主流程', '当天修复，次日复测', '本人'],
      ],
      [3.6, 3.4, 5.6, 2.4])

    # ---------- 五 成本计划 ----------
    H1(story, 'c5', '五 成本计划')
    H2(story, 's5-1', '5.1 成本估算口径')
    story.append(P(
        '本项目不采购服务器和商业软件，成本以人力为主。人力单价按课程项目口径取 50 元/人时，'
        '工时取自 WBS 和组内计划；非人力成本只计可选的 AI 接口费用。估算保留 10% 不可预见费，作为成本基线。'
    ))
    H2(story, 's5-2', '5.2 人力成本')
    T(story, '5-1', '人力成本估算',
      ['成员', '业务线', '工时（人时）', '单价（元/人时）', '小计（元）'],
      [
          ['荣宇', 'A-对话引擎（Web 前端）', '24', '50', '1,200'],
          ['曾明琦', 'B-知识库（Web 后端）', '24', '50', '1,200'],
          ['李博', 'C-意图路由（Web 后端）', '24', '50', '1,200'],
          ['冯昊', 'D-管理后台（Web 前端）', '23', '50', '1,150'],
          ['金鹏宇（本人）', 'E-多端接入（小程序+API）', '28', '50', '1,400'],
          ['合计', '—', '123', '—', '6,150'],
      ],
      [2.4, 5.0, 2.6, 2.6, 2.4], font_size=9.5)
    story.append(P('E 模块 28 人时、1,400 元；全项目 123 人时、6,150 元。两项数字与表 3-1、表 7-1 一致。', ))

    H2(story, 's5-3', '5.3 非人力成本与不可预见费')
    T(story, '5-2', '非人力成本与不可预见费',
      ['项目', '口径', '金额（元）', '说明'],
      [
          ['AI 接口调用', '可选，按 100 元封顶', '100', '未配置 Key 时走本地模板，不产生费用'],
          ['开发工具', '学生版/免费', '0', '微信开发者工具、Git、Python 均免费'],
          ['服务器与域名', '本机开发，不采购', '0', '生产部署留到后续实验'],
          ['不可预见费', '人力与 AI 费用之和的 10%', '625', '用于返工与临时调用'],
          ['成本基线', '合计', '6,875', '超出需周五例会确认'],
      ],
      [3.0, 5.6, 2.6, 3.8])

    H2(story, 's5-4', '5.4 成本监控')
    T(story, '5-3', '成本基线与监控口径',
      ['监控项', '基线', '检查频率', '超支处理'],
      [
          ['人力工时', '123 人时', '每周', '超 5% 说明原因并调整任务'],
          ['E 模块工时', '28 人时', '每周', '优先压缩非关键任务'],
          ['AI 调用费', '100 元', '每月', '超限改用本地模板'],
          ['总成本', '6,875 元', '里程碑', '周五例会确认后动用储备'],
      ],
      [3.2, 3.6, 3.0, 5.2])

    # ---------- 六 质量计划 ----------
    H1(story, 'c6', '六 质量计划')
    H2(story, 's6-1', '6.1 质量目标')
    story.append(P(
        'E 模块的质量目标围绕“接得上、鉴权住、说得清”三条：小程序主流程能跑通，开放 API 全部鉴权且错误码正确，'
        '文档能让他人按步骤复现。质量指标全部可在本地验证，不写无法核对的形容词。'
    ))
    T(story, '6-1', '质量目标与量化指标',
      ['指标', '目标值', '实测值', '验证方式', '状态'],
      [
          ['开放 API 鉴权覆盖', '4/4 接口', '4/4', 'before_request 统一校验', '达成'],
          ['鉴权分支用例', '缺失/错误/正确 3 条', '3/3 通过', 'test_e_module.py', '达成'],
          ['E 模块接口用例', '21 条全部通过', '21/21（冒烟 7 + 改进项 14）', '2026-11-11 运行 0.700+1.226 秒', '达成'],
          ['模板命中置信度', '不低于 0.75', '0.95（订单问题）', '接口返回 confidence', '达成'],
          ['本地接口响应', '单次低于 50 毫秒', '7.306 毫秒（模板命中）', 'response_time 字段', '达成'],
          ['小程序可编译', '开发者工具无报错', '游客模式下编译通过', '开发者工具', '部分达成'],
          ['操作手册可复现', '他机按步骤可启动', '本机验证通过', 'docs/操作手册.md', '达成'],
      ],
      [3.2, 3.2, 3.6, 3.2, 1.8], font_size=9.5)

    H2(story, 's6-2', '6.2 质量活动与检查点')
    T(story, '6-2', '质量活动与检查点',
      ['活动', '时点', '检查内容', '不合格处理'],
      [
          ['接口评审', 'M2 前', '路径、字段、鉴权、错误码', '退回修改后再冻结'],
          ['代码自查', '每次提交前', '密钥硬编码、异常分支、日志', '修复后再提交'],
          ['冒烟测试', '每周五', '21 条用例', '失败当天定位'],
          ['文档核对', '里程碑前', '命令、端口、账号、截图', '更新文档'],
          ['报告自查', '提交前', '63 项清单与四条红线', '逐项补齐'],
      ],
      [3.0, 2.6, 6.0, 3.4])

    H2(story, 's6-3', '6.3 缺陷管理')
    story.append(P(
        '缺陷记录编号、现象、定位、修复、复测五项。实验一期间发现并关闭 3 个缺陷，'
        '除接口参数校验外，还包括 AI 服务的两处判定缺陷，均已补入回归用例。'
    ))
    T(story, '6-3', '缺陷记录',
      ['编号', '现象', '定位', '修复', '复测'],
      [
          ['D-001', '/api/v1/chat 传入空白问题返回 200', 'api_chat 只判断 question 是否为真，未判断 strip 后是否为空', '先 strip 再判空，返回 400', '7/7 通过，用例固化'],
          ['D-002', '配置任意 AI Key 都按未配置处理，大模型从未被调用', '_ai_configured 把空字符串列入占位前缀，startswith 恒真', '占位判定改为精确匹配占位值集合', 'test_improvements 用例固化'],
          ['D-003', '大模型回复被弱匹配模板覆盖', '模板置信度低于阈值时仍用模板替换 AI 结果', '已配置真实 Key 时以大模型结果为准', 'test_improvements 用例固化'],
      ],
      [1.4, 4.0, 4.4, 3.0, 2.2], font_size=9.5)

    # ---------- 七 资源计划 ----------
    H1(story, 'c7', '七 资源计划')
    H2(story, 's7-1', '7.1 人力资源')
    T(story, '7-1', '人力资源分配',
      ['模块', '人员', '投入工时', '主要职责', '可替代人'],
      [
          ['A-对话引擎', '荣宇', '24', '对话界面、会话管理、多模型切换与流式', '李博'],
          ['B-知识库', '曾明琦', '24', '文档上传、分段、检索与向量库', '荣宇'],
          ['C-意图路由', '李博', '24', '意图分类、FAQ 匹配、转人工与工单', '曾明琦'],
          ['D-管理后台', '冯昊', '23', '质量评分、报表看板、用户管理', '荣宇'],
          ['E-多端接入', '金鹏宇（本人）', '28', '小程序、开放 API、公告与联调', '冯昊（临时）'],
      ],
      [3.0, 2.8, 2.4, 5.4, 1.6], font_size=9.5)

    H2(story, 's7-2', '7.2 环境资源')
    story.append(P(
        '三套环境共用同一套代码，差异在配置和数据库。开发环境用于日常调试，测试环境用临时 SQLite 和 Flask test_client 跑用例，'
        '生产环境按 ProductionConfig 规划但本阶段未部署。当前数据库路径在模型中固定为 instance/ai_qa_service.db，'
        '切换 PostgreSQL 需要改模型初始化代码，这一点已列入已知差距。'
    ))
    T(story, '7-2', '三套环境对照',
      ['环境', '配置类', '数据库', '启动方式', '用途', '状态'],
      [
          ['dev', 'DevelopmentConfig', 'instance/ai_qa_service.db', 'python backend/app.py，端口 5000', '日常开发与小程序联调', '已验证'],
          ['test', 'TestingConfig', '临时目录 test.db', 'test_e_module + test_improvements', '接口冒烟与回归', '21/21 通过'],
          ['prod', 'ProductionConfig', '计划 PostgreSQL（未接入）', '计划 gunicorn 启动', '对外提供服务', '未部署'],
      ],
      [1.3, 3.2, 2.9, 3.3, 2.3, 2.0], font_size=9)
    if not figure(story, '7-1', 'dev/test/prod 部署拓扑', 'fig-7-1-deploy.png', 'model/AIQAService-Plan.qea') and WARN_MISSING[0]:
        print('[缺失] 图 7-1（EA 部署图）未插入：docs/assets/fig-7-1-deploy.png')

    H2(story, 's7-3', '7.3 工具与版本')
    T(story, '7-3', '工具与版本清单',
      ['工具/依赖', '版本', '用途', '许可证'],
      [
          ['Python', '3.14.6', '运行后端与测试', 'PSF License'],
          ['Flask', '3.0.0', 'Web 框架', 'BSD-3-Clause'],
          ['Flask-CORS', '4.0.0', '跨域支持', 'MIT'],
          ['Peewee', '4.0.3', 'ORM 与 SQLite 访问', 'MIT'],
          ['PyJWT', '2.8.0', 'JWT 签发与校验', 'MIT'],
          ['requests', '2.31.0', '调用微信与大模型接口', 'Apache-2.0'],
          ['python-dotenv', '1.0.0', '读取 .env', 'BSD-3-Clause'],
          ['微信开发者工具', '稳定版', '小程序编译与预览', '腾讯免费工具许可'],
          ['Enterprise Architect', '17（未安装）', 'EA 模型图', '商业许可'],
          ['reportlab', '5.1.0', '本报告 PDF 排版', 'BSD'],
      ],
      [4.0, 3.2, 5.2, 2.6], font_size=9.5)

    H2(story, 's7-4', '7.4 资源日历')
    T(story, '7-4', '资源日历',
      ['资源', '可用时间', '占用说明'],
      [
          ['本人', '每周一至周五晚、周末', '本模块开发与文档'],
          ['荣宇、曾明琦、李博、冯昊', '每周五 20:00 例会', '接口确认与评审'],
          ['本机开发环境', '全周期', '端口 5000，需保持可用'],
          ['微信开发者工具', '全周期', '游客模式预览，无需 AppID'],
          ['EA 17', '安装后使用', '模型绘制与导出'],
      ],
      [3.4, 5.2, 6.4])

    # ---------- 八 沟通计划 ----------
    H1(story, 'c8', '八 沟通计划')
    H2(story, 's8-1', '8.1 沟通对象与内容')
    story.append(P(
        '沟通按对象分四类：组内接口确认、课程教师节点确认、小程序与 API 使用方反馈、平台限制确认。'
        '每类都有固定渠道和响应时限，避免临时口头约定后找不到依据。'
    ))
    T(story, '8-1', '沟通矩阵',
      ['对象', '沟通内容', '频率', '渠道', '责任人'],
      [
          ['荣宇、曾明琦、李博、冯昊', '接口路径、字段、错误码', '每周', '微信群 + 周五例会', '本人'],
          ['组内例会（全员）', '进度、风险、变更确认', '每周', '例会 + 仓库 Issue', '轮值'],
          ['课程教师', '节点、格式、答辩安排', '按公告', '泛雅公告 + 课堂', '本人'],
          ['API 使用方', 'Key 申请、限流、错误码', '按需', '邮件或群内说明', '本人'],
          ['平台限制', '小程序审核、登录能力', '按需', '微信官方文档', '本人'],
      ],
      [3.0, 5.2, 2.2, 3.0, 1.6], font_size=9.5)

    H2(story, 's8-2', '8.2 会议与渠道')
    T(story, '8-2', '会议与沟通节奏',
      ['活动', '时间', '时长', '输出'],
      [
          ['组内周会', '每周五 20:00', '30 分钟', '进度、风险、下周任务'],
          ['接口确认会', 'M2 前一次', '45 分钟', '接口清单与变更单'],
          ['实验课', '按课表', '当堂', '任务确认与答辩'],
          ['日常异步', '随时', '—', '群消息、提交记录、Issue'],
      ],
      [3.6, 3.8, 2.4, 5.2])

    H2(story, 's8-3', '8.3 接口变更沟通')
    story.append(P(
        '接口变更是 E 模块最大的外部风险。任何路径、字段、鉴权方式的改动，需提前 24 小时在群里说明，'
        '填写变更单，由提供方和本人确认影响范围后再改。未确认的变更不进入代码。'
    ))

    # ---------- 九 风险计划 ----------
    H1(story, 'c9', '九 风险计划')
    H2(story, 's9-1', '9.1 风险识别与评估口径')
    story.append(P(
        '风险按概率和影响各 1—5 分评分，两者相乘为风险值；风险值不低于 12 判为高，8—11 为中，低于 8 为低。'
        '每项风险有责任人、触发条件和应对动作，周会复核一次。'
    ))
    H2(story, 's9-2', '9.2 风险登记册')
    T(story, '9-1', '风险登记册',
      ['编号', '风险', '概率', '影响', '分值', '等级', '应对', '责任人', '触发条件'],
      [
          ['R1', '无真实 AppID，真机登录与截图受限', '4', '3', '12', '高', '先用游客模式预览，申请测试号后补真机验证', '本人', '真机登录失败'],
          ['R2', 'AI Key 缺失或额度耗尽', '3', '3', '9', '中', '本地模板兜底，保证主流程可用', '本人', '接口返回兜底话术'],
          ['R3', '接口字段变更导致小程序返工', '3', '4', '12', '高', '接口冻结 + 24 小时变更通知', '本人 + 接口提供方', '字段与清单不符'],
          ['R4', 'EA 17 未安装，模型图缺失', '5', '5', '25', '高', '已安装 EA 17，图 2-1、7-1、12-1 已补齐', '本人', 'V2.0 已关闭'],
          ['R5', '其他成员进度延误影响联调', '3', '4', '12', '高', '周会跟踪，关键路径留 2 人时缓冲', '全员', '任务晚于基线'],
          ['R6', '测试只在本机，环境不独立', '3', '3', '9', '中', '使用临时库与 test_client，生产后补独立环境', '本人', '用例互相污染'],
          ['R7', 'API Key 泄露或鉴权遗漏', '2', '5', '10', '中', '统一 before_request 校验，Key 只放环境变量', '本人', '出现未鉴权路径'],
          ['R8', '数据库文件丢失', '2', '3', '6', '低', '代码入库，定期备份 SQLite 文件', '本人', 'instance 目录损坏'],
      ],
      [1.1, 3.2, 0.9, 0.9, 0.9, 0.9, 3.9, 1.4, 1.8], font_size=8.5)

    H2(story, 's9-3', '9.3 高优先级风险应对')
    T(story, '9-2', '高优先级风险应对',
      ['风险', '应对动作', '完成时点', '验证方式'],
      [
          ['R4 EA 模型缺失', '安装 EA 17，按图 2-1、7-1、12-1 清单手工绘制并导出 PNG', '2026-11-11 已完成', '三图已插入本报告，源文件 model/AIQAService-Plan.qea'],
          ['R1 AppID 受限', '使用 touristappid 预览；申请测试号后替换并重测登录', '2026-11-29', '开发者工具编译与登录截图'],
          ['R3 接口变更', '接口清单一经冻结即走变更单', '2026-11-29', '变更记录与提交记录'],
          ['R5 进度延误', '周会检查关键路径，使用 2 人时缓冲', '每周五', '进度表与偏差记录'],
      ],
      [3.2, 6.6, 2.8, 2.4])

    # ---------- 十 采购计划 ----------
    H1(story, 'c10', '十 采购计划')
    H2(story, 's10-1', '10.1 采购原则')
    story.append(P(
        '本项目优先使用免费、开源、可在他机复现的工具。确需新增依赖时，先查许可证和 Python 3.14 兼容性，再写入依赖清单。'
        '商业软件只使用学校提供的授权，不以个人名义采购。'
    ))
    H2(story, 's10-2', '10.2 软件与许可证')
    T(story, '10-1', '软件与许可证清单',
      ['名称', '版本', '获取方式', '许可证', '用途'],
      [
          ['Python', '3.14.6', '官网安装', 'PSF', '运行时'],
          ['Flask', '3.0.0', 'pip', 'BSD-3-Clause', 'Web 框架'],
          ['Peewee', '4.0.3', 'pip', 'MIT', 'ORM'],
          ['PyJWT', '2.8.0', 'pip', 'MIT', 'JWT'],
          ['requests', '2.31.0', 'pip', 'Apache-2.0', '外部调用'],
          ['SQLite', 'Python 内置', '随 Python', 'Public Domain', '开发数据库'],
          ['微信开发者工具', '稳定版', '官网下载', '免费工具许可', '小程序编译'],
          ['Enterprise Architect', '17', '学校授权', '商业许可', 'EA 建模'],
          ['reportlab', '5.1.0', 'pip', 'BSD', '报告排版（非运行依赖）'],
      ],
      [4.0, 3.0, 3.2, 2.8, 2.0], font_size=9.5)

    H2(story, 's10-3', '10.3 采购预算与获取方式')
    T(story, '10-2', '采购预算与获取方式',
      ['项目', '是否采购', '预算（元）', '获取方式', '备注'],
      [
          ['开发软件', '否', '0', '开源/免费', '无 License 费用'],
          ['EA 17', '否', '0', '学校授权', '不安装则模型缺失，见 R4'],
          ['AI 接口', '可选', '100', '按量付费', '未配置时走模板'],
          ['服务器', '否', '0', '本机', '生产部署后续实验'],
          ['合计', '—', '100', '—', '不含人力成本'],
      ],
      [3.0, 2.4, 2.4, 4.0, 3.2])

    # ---------- 十一 干系人管理 ----------
    H1(story, 'c11', '十一 干系人管理')
    H2(story, 's11-1', '11.1 干系人识别')
    story.append(P(
        '干系人按影响力和关注度分四类。教师关注格式、计划合理性与真实性；同组其他四位成员关注接口与进度；'
        '管理员和用户关注可用性；平台方关注合规。每类都有对应的沟通方式。'
    ))
    T(story, '11-1', '干系人登记表',
      ['干系人', '角色', '关注点', '影响力', '管理策略'],
      [
          ['课程教师', '评价者', '格式、计划、真实性、答辩', '高', '按公告节点提交，材料可追溯'],
          ['荣宇、曾明琦、李博、冯昊', '协作者', '接口字段、联调时间', '高', '接口清单 + 群内确认'],
          ['管理员/运营方', '使用者', '公告好发、模板可改', '中', '保留管理接口，不纳入 E 交付'],
          ['小程序用户', '最终用户', '能登录、能提问、回复快', '中', '主流程冒烟与错误提示'],
          ['API 调用方', '外部系统', 'Key 鉴权、错误码稳定', '中', '接口文档与统一响应体'],
          ['微信平台', '平台方', '审核、登录能力', '高', '遵守平台规范，游客模式预览'],
      ],
      [3.2, 1.8, 5.0, 1.6, 3.4], font_size=9.5)

    H2(story, 's11-2', '11.2 参与策略')
    T(story, '11-2', '干系人参与策略',
      ['类型', '策略', '频率', '负责人'],
      [
          ['高影响高关注', '主动汇报、共同评审', '每周', '轮值'],
          ['高影响低关注', '按节点提交、一次说清', '里程碑', '本人'],
          ['低影响高关注', '及时答疑、给操作手册', '按需', '本人'],
          ['低影响低关注', '公告或文档告知', '按需', '本人'],
      ],
      [3.6, 6.6, 2.6, 2.2])

    H2(story, 's11-3', '11.3 期望管理')
    story.append(P(
        '对教师，明确本阶段交的是原型，不把未做的生产部署说成已完成；对同组其他四位成员，明确 E 模块只做接入，不替别人的模块改业务规则；'
        '对用户，明确未配置 AI Key 时使用模板回复，并给出兜底话术。所有“尚未完成”的项都在表 1-4 与自我测评中列出。'
    ))

    # ---------- 十二 配置管理 ----------
    H1(story, 'c12', '十二 配置管理')
    H2(story, 's12-1', '12.1 配置项识别')
    T(story, '12-1', '配置项清单',
      ['类别', '配置项', '位置', '版本标识'],
      [
          ['源码', '小程序与开放 API', 'miniprogram/、backend/routes/api.py', 'Git 提交号'],
          ['文档', 'README、操作手册、问答册、报告', 'README.md、docs/、本 PDF', 'V2.3'],
          ['模型', 'EA 工程', 'model/AIQAService-Plan.qea', 'V2.0（已建立）'],
          ['测试', '接口测试用例（冒烟+改进项）', 'test/test_e_module.py、test_improvements.py', '随代码提交'],
          ['环境', '依赖清单与环境变量模板', 'requirements.txt、.env.example', '随代码提交'],
      ],
      [2.2, 4.0, 6.4, 2.4])

    H2(story, 's12-2', '12.2 基线与版本')
    T(story, '12-2', '基线定义',
      ['基线', '内容', '建立时点', '变更方式'],
      [
          ['功能基线', 'E 模块范围与接口清单', 'M1（2026-11-16）', '变更单 + 例会确认'],
          ['分配基线', 'WBS、进度、成本', 'M1', '偏差超阈值时调整'],
          ['产品基线', '源码、测试、文档、模型', 'M4（2027-01-03）', 'tag 标记，PR 合入'],
      ],
      [2.6, 6.0, 3.6, 2.8])
    story.append(P(
        '文档版本从 V1.0 起，每改一轮升一个次版本号；终稿从 V2.0 起。版本号、日期、修改人三者对应，'
        '改了内容不升版本视为说不清来源。'
    ))

    H2(story, 's12-3', '12.3 分支与提交规范')
    story.append(P(
        '仓库计划采用 main、develop、feature/学号-模块三分支。main 只放可交付版本，develop 做集成，'
        '个人开发在 feature/2024210560-duoduan 上完成；main 与 develop 开分支保护，必须走合并请求并由至少一名其他成员评审。'
        '截至 2026-11-11，仓库只有 main 分支，共 2 次提交，develop、feature 分支和首个 tag 还没建，'
        '这两项放到实验二开头完成。'
    ))
    T(story, '12-3', '分支与提交规范',
      ['分支/动作', '用途', '规则', '示例'],
      [
          ['main', '可交付版本', '禁止直推，PR 合入', 'main'],
          ['develop', '日常集成', '禁止直推，PR 合入', 'develop'],
          ['feature/学号-模块', '个人业务', '合并后删除', 'feature/<br/>2024210560-duoduan'],
          ['提交信息', '说明改了什么', '类型: 简短说明', 'fix: 校验空白问题'],
          ['tag', '基线归档', '实验名 + 版本', 'lab1-plan-v1.0'],
      ],
      [3.2, 3.4, 4.6, 3.8], font_size=9.5)
    if not figure(story, '12-1', '分支与配置管理流程', 'fig-12-1-branch.png', 'model/AIQAService-Plan.qea') and WARN_MISSING[0]:
        print('[缺失] 图 12-1（EA 活动图）未插入：docs/assets/fig-12-1-branch.png')

    H2(story, 's12-4', '12.4 变更控制')
    T(story, '12-4', '变更控制流程',
      ['步骤', '动作', '责任人', '输出'],
      [
          ['1 提出', '填写变更单，说明原因与影响', '提出人', '变更单'],
          ['2 评估', '检查接口、进度、成本影响', '本人 + 接口提供方', '影响说明'],
          ['3 审批', '例会集体确认是否执行', '全员', '审批结论'],
          ['4 实施', '改代码/文档，跑回归', '本人', '提交记录、测试结果'],
          ['5 关闭', '更新版本与修订记录', '本人', '新版本号'],
      ],
      [2.0, 6.4, 4.0, 2.6])

    H2(story, 's12-5', '12.5 AI 辅助记录与留痕')
    story.append(P(
        '我用 AI 辅助的范围限于代码复核、测试用例起草、文档结构与文字压缩、报告排版脚本。'
        '模型图、截图、测试数据不由 AI 生成；AI 给出的结论逐条对照源码和运行结果核验后再写入报告。'
        '下表按“模型与版本、日期、用途、输入要点、人工修改、核验依据”六项记录。'
    ))
    T(story, '12-5', 'AI 辅助记录',
      ['模型与版本', '日期', '用途', '输入要点', '人工修改', '核验依据'],
      [
          ['DeepSeek-V4.1-Flash', '2026-11-11', '复核开放 API 鉴权、起草冒烟测试', '附 api.py、README、测试目标，要求列出鉴权绕过点', '保留统一 before_request；补空白问题校验', '读代码 + 7 条用例通过'],
          ['DeepSeek-V4.1-Flash', '2026-11-11', '起草操作手册与报告排版脚本', '附目录结构、接口清单、V3.0 要求', '删套话与空泛表述，逐条核对接口与表结构', '对照源码与测试输出'],
          ['DeepSeek-V4.1-Flash', '2026-11-11', '报告结构重排与文字压缩', '贴入 V3.0 要求与本人素材', '重写各节结论，删除“首先/其次”', '对照 63 项自查'],
      ],
      [3.4, 2.0, 2.6, 3.0, 2.4, 1.6], font_size=8)
    story.append(PNI(
        '工具类型：IDE 集成对话与编码智能体（TraeCode）。原始对话由本人从 IDE 会话导出留档，报告只引用核验后的结论。'
    ))

    H2(story, 's12-6', '12.6 文档修订记录')
    T(story, '12-6', '文档修订记录',
      ['版本', '日期', '修改内容', '修改人'],
      [
          ['V1.0', '2026-11-16', '按 V3.0 要求建立十三节结构，补充 E 模块计划与自评', '金鹏宇'],
          ['V2.0', '2026-11-11', '补入 EA 17 手工绘制的图 2-1、7-1、12-1，风险 R4 关闭，模型维度重计分', '金鹏宇'],
          ['V2.1', '2026-11-11', '补入运行环境截图（图 1-1），证据 E1-1 状态更新，证据维度 4→5 分', '金鹏宇'],
          ['V2.2', '2026-11-11', '同步功能改进批次（限流、越权防护、AI 判定修复等），测试扩至 21 条，缺陷 D-002/D-003 关闭', '金鹏宇'],
          ['V2.3', '2026-11-11', '按小组分工表统一成员姓名与 A—D 模块名，组织表、资源表、沟通表与干系人表同步改写；学号更正为 2024210560', '金鹏宇'],
          ['V2.4', '2026-11-11', '补入 E1-2、E2-1、E3-1、E4-1、E5-1、E7-1 六张实拍截图（图 1-2 至图 1-7），表 1-4 状态更新，证据维度 5→8 分', '金鹏宇'],
          ['V2.5', '2026-11-11', '补入 E5-2 鉴权对比截图（图 1-7），E7-1 顺延为图 1-8；表 1-4 全部达成项除小程序外齐备，证据维度 8→9 分', '金鹏宇'],
      ],
      [2.0, 3.2, 8.2, 1.6])

    # ---------- 十三 沟通计划方式 ----------
    H1(story, 'c13', '十三 沟通计划方式')
    H2(story, 's13-1', '13.1 沟通方式与适用场景')
    story.append(P(
        '本项目常用的五种沟通方式、适用场景、响应时限和留痕位置已在 §8.1、§8.2 写明，这里不再重复列表。'
        '本节只补两点执行口径：一是所有涉及接口的沟通，结论必须落到群消息或 Issue 里，口头说的不算；'
        '二是每周五例会前，各自把本周改动和下周计划写进 Issue，会上只处理分歧和阻塞。'
    ))

    H2(story, 's13-2', '13.2 变更请求处理流程')
    story.append(P(
        '变更请求统一走“提出—评估—审批—实施—关闭”五步，口头提出的变更要在群里补一条文字记录。'
        '涉及接口的变更必须同时通知提供方和使用方，未审批的变更不得合入 develop。'
    ))

    H2(story, 's13-3', '13.3 本实验已执行的变更')
    T(story, '13-1', '本实验已执行的变更',
      ['编号', '变更内容', '原因', '影响', '验证', '日期'],
      [
          ['C-001', '开放 API 鉴权统一到 before_request', '原实现只在一个接口内校验，存在绕过风险', '4 个 /v1 接口全部校验 X-API-Key', '缺失/错误/正确 3 条用例通过', '2026-11-11'],
          ['C-002', '空白问题返回 400', '空白字符串绕过非空判断', 'chat 接口参数校验', 'D-001 复测通过', '2026-11-11'],
          ['C-003', '限流、越权防护、AI 判定与模板优先级修复', '健壮性与越权风险复核', '后端 9 文件、小程序 6 文件', '改进项 14 条用例通过', '2026-11-11'],
      ],
      [1.3, 3.6, 3.6, 3.1, 2.4, 1.0], font_size=9)


# ==================== 小组报告部分 ====================
def group_part(story):
    part_divider(story, 'group', '小组报告部分', '项目组：cs24108　项目：P08 智能问答客服平台　版本：V2.3')

    H1(story, 'c14', '十四 立项背景与整体目标', first=True)
    H2(story, 's14-1', '14.1 项目背景')
    story.append(P(
        '课程项目要求每个小组完成一个可运行、可演示、可追溯的软件系统。本组选择智能问答客服平台，'
        '原因是问答场景需求清楚、接口边界明确，适合五人按业务线纵向分工，也便于在八个教学周内做出可演示的原型。'
    ))
    H2(story, 's14-2', '14.2 整体目标与范围')
    story.append(P(
        '整体目标是提供“小程序 + 开放 API”两条接入通道，后台支持微信登录、会话与消息、场景化回复、公告推送和统计。'
        '本阶段交付系统原型：核心流程可跑通，开发环境可用，文档与测试可复核；生产部署、真实小程序发布和 PostgreSQL 迁移不在本阶段。'
    ))
    T(story, '14-1', '整体能力清单',
      ['能力', '对应模块', '完成情况', '说明'],
      [
          ['微信登录与用户信息', 'D-管理后台', '已实现', '未配置 AppID 时使用 mock openid'],
          ['对话与会话管理', 'A-对话引擎', '已实现', '支持历史、重新生成、场景切换'],
          ['意图分类与场景回复', 'C-意图路由', '部分实现', '原型用关键词加模板替代分类模型'],
          ['知识库检索（RAG）', 'B-知识库', '规划中', '向量库与 Embedding 未接入原型'],
          ['公告与已读', 'E-多端接入', '已实现', '支持列表、未读数、已读标记'],
          ['小程序端与开放 API', 'E-多端接入', '已实现', '登录、首页、对话页；4 个开放接口'],
      ],
      [4.4, 2.6, 2.4, 5.6])

    H1(story, 'c15', '十五 组织与协作')
    H2(story, 's15-1', '15.1 五条业务线与责任边界')
    story.append(P(
        '五条业务线各自从需求做到运维，接口是唯一的协作面。E 模块不直接调用 A—D 的内部函数，'
        '荣宇、曾明琦、李博、冯昊也不直接改小程序页面，减少互相覆盖。'
    ))
    T(story, '15-1', '业务线与责任边界',
      ['业务线', '负责人', '边界', '对外接口'],
      [
          ['A-对话引擎<br/>（Web 前端）', '荣宇', '消息收发界面、会话管理、多模型切换与流式', '/api/chat/*（会话与消息）'],
          ['B-知识库<br/>（Web 后端）', '曾明琦、荣宇', '文档上传、分段、检索、向量库维护', '/api/kb/*'],
          ['C-意图路由<br/>（Web 后端）', '李博', '意图分类、FAQ 匹配、转人工与工单', '/api/intent/*、/api/ticket/*'],
          ['D-管理后台<br/>（Web 前端）', '冯昊', '质量评分、热词分析、趋势报表、用户管理', '/api/admin/*、/api/auth/*'],
          ['E-多端接入<br/>（小程序+API）', '金鹏宇（本人）', '小程序、开放 API、公告推送、自动回复模板', 'miniprogram/<br/>/api/v1/*<br/>/api/announcement/*'],
      ],
      [3.2, 1.95, 6.05, 3.8], font_size=9.5)

    H2(story, 's15-2', '15.2 接口对接与协作机制')
    story.append(P(
        '协作按“接口先定、变更留痕、每周对齐”执行。接口清单在 M2 冻结，联调问题在群里当天提出，'
        '每周五例会核对进度与风险。答辩时每个人都能说清自己那块与相邻模块的对接点。'
    ))

    H1(story, 'c16', '十六 整体成果与技术结论')
    H2(story, 's16-1', '16.1 已实现的整体能力')
    story.append(P(
        '后端共 6 张表，覆盖用户、会话、消息、公告、已读和快捷回复。五类场景共 10 条初始模板，'
        '模板命中时直接返回，未命中且未配置 AI Key 时使用兜底话术，保证演示不中断。'
    ))
    T(story, '16-1', '原型模块与接口对应',
      ['原型模块', '关键文件', '对外能力', '正式归属'],
      [
          ['用户与登录', 'backend/routes/auth.py', '微信登录、账号登录、注册、资料', 'D-管理后台'],
          ['会话与消息', 'backend/routes/chat.py', '会话、消息、场景、快捷回复', 'A-对话引擎、C-意图路由'],
          ['回复生成', 'backend/services/ai_service.py', '模板匹配、AI 调用、兜底', 'C-意图路由、B-知识库'],
          ['公告与已读', 'backend/routes/announcement.py', '公告、未读、已读', 'E-多端接入'],
          ['多端接入', 'miniprogram/、backend/routes/api.py', '小程序页面、4 个开放接口', 'E-多端接入'],
      ],
      [2.4, 5.2, 4.4, 3.0], font_size=9.5)
    story.append(PNI(
        '表 16-1 按文件归属列出原型里已经跑起来的模块。这四块后台能力是原型阶段为打通联调先做的，'
        '实验二由 A—D 各自按表 15-1 的分工接管并替换成自己的实现，E 只保留接入部分。'
    ))

    H2(story, 's16-2', '16.2 技术结论')
    T(story, '16-2', '技术选型结论',
      ['选择', '理由', '代价'],
      [
          ['Flask + Peewee', '轻量、启动快、SQLite 零配置，适合课程原型', '生产并发与迁移能力有限'],
          ['JWT（小程序）', '无状态、易注入请求头、适合多端', '过期与刷新需要额外处理'],
          ['X-API-Key（开放 API）', '外部系统接入简单，密钥可轮换', '需自行管理 Key 与配额'],
          ['模板优先 + AI 兜底', '无 Key 也能演示，响应稳定', '回答覆盖面受模板限制'],
      ],
      [3.6, 6.8, 4.6])

    H2(story, 's16-3', '16.3 已知差距')
    story.append(P(
        '生产环境未部署，数据库还是单文件 SQLite；真实小程序 AppID 没配，真机登录没验证；'
        '截图已补到 E1-2、E2-1、E3-1、E4-1、E5-1、E5-2、E7-1（图 1-2 至图 1-8），只剩 E6-1、E6-2 小程序界面没截；'
        '仓库分支和 PR 记录没建。'
        '这些都在风险登记册和自我测评里列了，没有用示意图代替。'
    ))

    H1(story, 'c17', '十七 过程复盘')
    H2(story, 's17-1', '17.1 做得好的')
    story.append(P(
        '接口先定让 E 模块可以独立开发；统一鉴权把安全边界收在一处；模板兜底让演示不依赖外部 AI 服务；'
        '冒烟测试在实验一就固化，后续改动能快速回归。'
    ))
    H2(story, 's17-2', '17.2 问题与改进')
    T(story, '17-1', '问题与改进',
      ['问题', '影响', '改进'],
      [
          ['仓库只有 main 分支', '缺少 PR 与评审证据', '实验一终稿前建立 develop 与 feature 分支'],
          ['EA 模型图曾缺失', 'V1.0 模型维度记 0 分', 'V2.0 已用 EA 17 手工补齐图 2-1、7-1、12-1'],
          ['小程序界面未截', 'E6-1、E6-2 证据缺失', '在微信开发者工具补齐首页与对话页截图'],
          ['生产环境未部署', '三套环境不完整', '后续实验补 gunicorn 与 PostgreSQL'],
      ],
      [4.0, 5.6, 5.4])


# ==================== 自我测评与参考文献 ====================
def self_assessment(story):
    H1(story, 'self', '自我测评')
    story.append(P(
        f'自评分数：{SELF_SCORE}/100。分数按七个维度逐项核算，每条写明依据位置与证据编号。'
        '这次自评对应 V2.5 报告，EA 模型图已用 EA 17 手工补齐（图 2-1、7-1、12-1），模型维度按 12 分计；'
        '实拍截图已补到八张（图 1-1 至图 1-8），证据维度按 9 分计；小程序界面截图（E6-1、E6-2）还没补，扣 1 分。'
    ))
    T(story, '18-1', '逐项自评依据',
      ['评分维度', '分值', '自评', '依据位置', '证据编号'],
      [[d, str(full), str(score), where, ev] for d, full, score, where, ev in SELF_SCORES]
      + [['合计', '100', str(SELF_SCORE), '—', '—']],
      [4.2, 1.6, 1.8, 4.2, 3.2])
    story.append(Spacer(1, 6))
    story.append(PNI('本实验支撑课程目标 1、4，对应毕业要求指标点 1.2 工程知识、11.1 项目管理。'))
    story.append(Spacer(1, 6))
    T(story, '18-2', '达标清单',
      ['结论', '项目', '说明'],
      [
          ['达成', '计划十要素', '范围、进度、成本、质量、资源、沟通、风险、采购、干系人、配置变更均有量化口径'],
          ['达成', 'WBS 三层', '6 个任务包，4—8 人时，依赖与关键路径明确'],
          ['达成', '接口与鉴权', '4 个 /v1 接口统一校验，测试 21/21 通过'],
          ['达成', '文档与问答册', 'README、操作手册、问答册与报告口径一致'],
          ['部分达成', '三套环境', 'dev 与 test 已验证，prod 未部署'],
          ['部分达成', '仓库管理', '仅 main 分支 2 次提交，缺 develop、feature、PR、tag'],
          ['部分达成', '七类证据', 'E2、E3、E7 达成；E1、E4、E5 部分达成；E6 未达成'],
          ['达成', 'EA 模型图', '图 2-1、7-1、12-1 已用 EA 17 手工绘制，源文件 model/AIQAService-Plan.qea'],
          ['未达成', '全组统稿', '本报告个人部分只含本人 E 模块，其他成员小节未合入'],
      ],
      [2.0, 4.0, 9.0])


def references(story):
    H1(story, 'ref', '参考文献')
    refs = [
        '[1] 毛新军. 现代软件工程：在线实训版 [M]. 北京：人民邮电出版社，2025. ISBN 978-7-115-66719-9.',
        '[2] GB/T 8567-2006 计算机软件文档编制规范 [S]. 北京：中国标准出版社，2006.',
        '[3] 微信开放文档. 小程序登录 [EB/OL]. [2026-11-11]. https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html.',
        '[4] Pallets Projects. Flask Documentation (3.0.x) [EB/OL]. [2026-11-11]. https://flask.palletsprojects.com/.',
        '[5] Peewee ORM. Peewee Documentation [EB/OL]. [2026-11-11]. http://docs.peewee-orm.com/.',
    ]
    for ref in refs:
        story.append(Paragraph(ref, STYLES['body_ni']))


# ==================== 构建 ====================
def build_once(out_path, page_reg, front_total, body_total):
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
        topMargin=2.4 * cm, bottomMargin=2.2 * cm,
        title=f'{FULL_PROJECT}{EXPERIMENT}报告',
        author=f'{STUDENT_NAME} {STUDENT_ID}',
    )
    FRONT_TOTAL[0] = front_total
    BODY_TOTAL[0] = body_total

    story = []
    cover(story)
    story.append(PageBreak())
    front = front_matter(page_reg)
    story.extend(front)

    body = []
    part_divider(body, 'personal', '个人报告部分',
                 '撰写：金鹏宇（2024210560）　业务线：E-多端接入（微信小程序 + 开放 API）')
    personal_part(body)
    group_part(body)
    self_assessment(body)
    references(body)
    story.extend(body)

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)


def main():
    global FIGURE_ENTRIES
    FIGURE_ENTRIES = [(num, title) for num, title, filename, _ in PLANNED_FIGURES
                      if os.path.exists(os.path.join(ASSET_DIR, filename))]
    SHOTS = [
        ('1-1', '运行环境与依赖版本核验（E1-1）', 'shot-e1-1-env.png'),
        ('1-2', '后端启动与 5000 端口监听（E1-2）', 'shot-e1-2-start-crop.png'),
        ('1-3', '工程目录与接口实现（E2-1）', 'shot-e2-1-tree.png'),
        ('1-4', 'EA 工程与模型树（E3-1）', 'shot-e3-1-ea.png'),
        ('1-5', '仓库提交与分支记录（E4-1）', 'shot-e4-1-repo.png'),
        ('1-6', '接口测试运行结果（E5-1，21 条全部通过）', 'shot-e5-1-test-crop.png'),
        ('1-7', '开放 API 鉴权分支对比（E5-2）', 'shot-e5-2-401-crop.png'),
        ('1-8', '操作手册的启动与 API 说明（E7-1）', 'shot-e7-1-manual.png'),
    ]
    FIGURE_ENTRIES = [(n, t) for n, t, f in SHOTS
                      if os.path.exists(os.path.join(ASSET_DIR, f))] + FIGURE_ENTRIES

    tmp = os.path.join(ROOT, '.report_pass1.pdf')
    # 反复构建直到页码收敛（目录条目自身也会影响分页）
    prev = None
    for _ in range(6):
        build_once(tmp, PAGE_REG, 0, 0)
        snap = dict(PAGE_REG)
        if snap == prev:
            break
        prev = snap
    total_pages = max(PAGE_REG.values()) if PAGE_REG else 1
    body_start = PAGE_REG.get('h1:personal', 1)
    front_total = body_start - 2
    body_total = total_pages - body_start + 1

    display = {}
    for key, physical in PAGE_REG.items():
        if physical >= body_start:
            display[key] = physical - body_start + 1
        else:
            display[key] = physical - 1

    WARN_MISSING[0] = True
    build_once(OUT_FILE, display, front_total, body_total)
    if os.path.exists(tmp):
        os.remove(tmp)

    print(f'[完成] {os.path.basename(OUT_FILE)}')
    print(f'[页码] 封面 1 页；目录区 {front_total} 页；正文 {body_total} 页；合计 {total_pages} 页')
    used = {key.split(':', 1)[1] for key in PAGE_REG if key.startswith('table:')}
    declared = {num for num, _ in TABLE_TITLES}
    if used != declared:
        print('[表号不一致] 已用未登记：', sorted(used - declared), ' 已登记未使用：', sorted(declared - used))
    missing = [f for f in PLANNED_FIGURES if not os.path.exists(os.path.join(ASSET_DIR, f[2]))]
    if missing:
        print('[缺图] 以下 EA 图未找到，报告中未插入：')
        for num, title, filename, _ in missing:
            print(f'  - 图 {num} {title}: docs/assets/{filename}')
    if not os.path.exists(LOGO_PATH):
        print('[缺图] 校徽缺失：docs/assets/school-logo.png')


if __name__ == '__main__':
    main()
