#!/usr/bin/env python3
"""Build thesis/dokumentacja.docx on a copy of the supervisor's template.

1. pandoc renders dokumentacja.md -> body.docx using the template as --reference-doc
   (page size, margins, Normal/Heading styles come from the template);
2. the template's title page (logo + text up to the first page break) is copied in
   front of the body, with placeholders replaced;
3. section 1 is assembled into the template's two-column table from the blocks
   between the %%CELL ...%% / %%ENDTABLE%% marker paragraphs;
4. the remaining (pandoc) tables get borders and explicit column widths;
5. styles pandoc expects but the template lacks (Table, Source Code, Verbatim Char,
   Image Caption, Compact, Body Text, First Paragraph) are added.
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "wzor_dokumentacji_projektowej.docx"
MD = HERE / "dokumentacja.md"
OUT = HERE / "dokumentacja.docx"
BUILD = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "_build"

TEXT_WIDTH = 9070  # A4 11906 - 2 * 1418 (template margins), in twips

TITLE_REPLACEMENTS = {
    "Jan Kowalski": "<IMIĘ I NAZWISKO>",
    "studia niestacjonarne": "studia <stacjonarne/niestacjonarne>",
    "nr albumu 123456": "nr albumu <NR ALBUMU>",
    "Aplikacja internetowa: platforma e-commerce":
        "MAGGuarantee: system zarządzania wnioskami o gwarancję kilometrową dla firmy transportowej",
    "dra inż. X Y Z": "<TYTUŁ> Marcina Kacprowicza",
    "Warszawa, 2022": "Warszawa 2026",
}

# column widths (twips) for the pandoc tables, in document order after section 1
PANDOC_TABLE_WIDTHS = [
    [3700, 5370],                   # 2.2 reguła biznesowa / mechanizm
    [2600, 3000],                   # 2.6 progi autoryzacji
    [2900, 1300, 900, 900, 3070],   # 4 wyniki testów
]

BORDERS = (
    '<w:tblBorders>'
    '<w:top w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:left w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:right w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="808080"/>'
    '</w:tblBorders>'
)
CELL_MARGINS = (
    '<w:tblCellMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
    '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar>'
)

EXTRA_STYLES = """
<w:style w:type="table" w:styleId="Table"><w:name w:val="Table"/><w:basedOn w:val="TableNormal"/>
<w:tblPr>%s%s</w:tblPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/>
<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
<w:style w:type="character" w:customStyle="1" w:styleId="VerbatimChar"><w:name w:val="Verbatim Char"/>
<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas" w:eastAsia="Consolas"/><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="SourceCode"><w:name w:val="Source Code"/><w:basedOn w:val="Normal"/><w:link w:val="VerbatimChar"/>
<w:pPr><w:keepLines/><w:wordWrap w:val="off"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="113"/>
<w:shd w:val="clear" w:color="auto" w:fill="F3F4F6"/></w:pPr>
<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas" w:eastAsia="Consolas"/><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Compact"><w:name w:val="Compact"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="BodyText"><w:name w:val="Body Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="160"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="FirstParagraph"><w:name w:val="First Paragraph"/><w:basedOn w:val="BodyText"/></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="ImageCaption"><w:name w:val="Image Caption"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepLines/><w:spacing w:before="80" w:after="320"/><w:jc w:val="both"/></w:pPr><w:rPr><w:i/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="CaptionedFigure"><w:name w:val="Captioned Figure"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="Figure"><w:name w:val="Figure"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr></w:style>
<w:style w:type="paragraph" w:customStyle="1" w:styleId="TableCaption"><w:name w:val="Table Caption"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/></w:pPr><w:rPr><w:i/></w:rPr></w:style>
""" % (BORDERS, CELL_MARGINS)


def unzip(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    with zipfile.ZipFile(src) as z:
        z.extractall(dst)
    for p in dst.rglob("*"):
        if p.is_symlink():
            p.unlink()


def zip_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        dst.unlink()
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        ct = src / "[Content_Types].xml"
        z.write(ct, "[Content_Types].xml")
        for p in sorted(src.rglob("*")):
            if p.is_file() and p != ct:
                z.write(p, p.relative_to(src).as_posix())


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def split_top_level(body: str) -> list[str]:
    """Split <w:body> inner XML into top-level blocks (paragraphs, tables, sectPr)."""
    blocks, i, n = [], 0, len(body)
    while i < n:
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        if body.startswith("<w:p>", i) or body.startswith("<w:p ", i):
            j = body.index("</w:p>", i) + len("</w:p>")
        elif body.startswith("<w:tbl>", i) or body.startswith("<w:tbl ", i):
            j = body.index("</w:tbl>", i) + len("</w:tbl>")
        elif body.startswith("<w:sectPr", i):
            j = body.index("</w:sectPr>", i) + len("</w:sectPr>")
        elif body.startswith("<w:bookmarkStart", i) or body.startswith("<w:bookmarkEnd", i):
            j = body.index("/>", i) + 2
        else:
            raise SystemExit("unexpected top-level element at: " + body[i:i + 80])
        blocks.append(body[i:j])
        i = j
    return blocks


def para_text(p: str) -> str:
    return "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p))


def build_section1_table(blocks: list[str]) -> list[str]:
    out, i = [], 0
    while i < len(blocks):
        b = blocks[i]
        if b.startswith("<w:p") and para_text(b).startswith("%%CELL "):
            rows = []
            label = para_text(b)[len("%%CELL "):].rstrip("%")
            cells: list[str] = []
            i += 1
            while True:
                b = blocks[i]
                t = para_text(b) if b.startswith("<w:p") else ""
                if t.startswith("%%CELL "):
                    rows.append((label, cells))
                    label, cells = t[len("%%CELL "):].rstrip("%"), []
                elif t.startswith("%%ENDTABLE%%"):
                    rows.append((label, cells))
                    i += 1
                    break
                else:
                    cells.append(b)
                i += 1
            w1, w2 = 2150, TEXT_WIDTH - 2150
            tr = []
            for label, cells in rows:
                lab = ('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>'
                       '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr>'
                       '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p></w:tc>' % (w1, xml_escape(label)))
                body = "".join(cells) or "<w:p/>"
                val = '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>%s</w:tc>' % (w2, body)
                tr.append("<w:tr>" + lab + val + "</w:tr>")
            tbl = ('<w:tbl><w:tblPr><w:tblStyle w:val="Table"/><w:tblW w:w="%d" w:type="dxa"/>'
                   '<w:tblLayout w:type="fixed"/>%s%s</w:tblPr>'
                   '<w:tblGrid><w:gridCol w:w="%d"/><w:gridCol w:w="%d"/></w:tblGrid>%s</w:tbl>'
                   % (TEXT_WIDTH, BORDERS, CELL_MARGINS, w1, w2, "".join(tr)))
            out.append(tbl)
            out.append('<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr></w:p>')
            continue
        out.append(b)
        i += 1
    return out


def fix_pandoc_table(tbl: str, widths: list[int]) -> str:
    total = sum(widths)
    tblpr = ('<w:tblPr><w:tblStyle w:val="Table"/><w:tblW w:w="%d" w:type="dxa"/>'
             '<w:tblLayout w:type="fixed"/>%s%s</w:tblPr>' % (total, BORDERS, CELL_MARGINS))
    tbl = re.sub(r"<w:tblPr>.*?</w:tblPr>", lambda _: tblpr, tbl, count=1, flags=re.S)
    grid = "<w:tblGrid>" + "".join('<w:gridCol w:w="%d"/>' % w for w in widths) + "</w:tblGrid>"
    tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", lambda _: grid, tbl, count=1, flags=re.S)

    def fix_row(m: re.Match, first: list[bool]) -> str:
        row = m.group(0)
        cells = re.findall(r"<w:tc>.*?</w:tc>", row, flags=re.S)
        new_cells = []
        for idx, c in enumerate(cells):
            w = widths[idx] if idx < len(widths) else widths[-1]
            c = re.sub(r"<w:tcPr\s*/>|<w:tcPr>.*?</w:tcPr>",
                       '<w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>' % w, c, count=1, flags=re.S)
            if first[0]:
                c = re.sub(r"<w:r>(?!<w:rPr>)", "<w:r><w:rPr><w:b/></w:rPr>", c)
                c = re.sub(r"<w:r><w:rPr>(?!<w:b/>)", "<w:r><w:rPr><w:b/>", c)
            new_cells.append(c)
        first[0] = False
        head = row[: row.index("<w:tc>")]
        return head + "".join(new_cells) + "</w:tr>"

    first = [True]
    tbl = re.sub(r"<w:tr(?: [^>]*)?>.*?</w:tr>", lambda m: fix_row(m, first), tbl, flags=re.S)
    return tbl


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    body_docx = BUILD / "body.docx"
    subprocess.run(
        ["pandoc", str(MD), "-o", str(body_docx), f"--reference-doc={TEMPLATE}",
         f"--resource-path={HERE}", "--from=markdown+smart", "--highlight-style=monochrome"],
        check=True,
    )
    tdir, bdir = BUILD / "tpl", BUILD / "body"
    unzip(TEMPLATE, tdir)
    unzip(body_docx, bdir)

    tdoc = (tdir / "word/document.xml").read_text(encoding="utf-8")
    bdoc = (bdir / "word/document.xml").read_text(encoding="utf-8")

    # ---------- title page from the template
    tbody = tdoc[tdoc.index("<w:body>") + len("<w:body>"):]
    m = re.search(r"<w:p>(?:(?!</w:p>).)*?<w:br w:type=\"page\"/>.*?</w:p>", tbody, flags=re.S)
    if not m:
        sys.exit("page break after the title page not found in the template")
    title_xml = tbody[: m.end()]
    for old, new in TITLE_REPLACEMENTS.items():
        if old not in title_xml:
            sys.exit(f"title placeholder not found: {old!r}")
        title_xml = title_xml.replace(old, xml_escape(new))

    trels = (tdir / "word/_rels/document.xml.rels").read_text(encoding="utf-8")
    blip = re.search(r'r:embed="(rId\d+)"', title_xml).group(1)
    target = re.search(rf'<Relationship Id="{blip}"[^>]*Target="([^"]+)"', trels).group(1)
    logo_dst = bdir / "word/media/logo_vizja.png"
    logo_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tdir / "word" / target, logo_dst)
    title_xml = title_xml.replace(f'r:embed="{blip}"', 'r:embed="rIdLogoVizja"')
    title_xml = re.sub(r'<wp:docPr id="\d+"', '<wp:docPr id="90001"', title_xml)

    brels_path = bdir / "word/_rels/document.xml.rels"
    brels = brels_path.read_text(encoding="utf-8")
    brels = brels.replace(
        "</Relationships>",
        '<Relationship Id="rIdLogoVizja" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="media/logo_vizja.png"/></Relationships>')
    brels_path.write_text(brels, encoding="utf-8")

    root_tag = re.search(r"<w:document[^>]*>", bdoc).group(0)
    needed = {
        "xmlns:wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
        "xmlns:a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "xmlns:pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
        "xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    new_root = root_tag
    for k, v in needed.items():
        if k + "=" not in new_root:
            new_root = new_root[:-1] + f' {k}="{v}">'
    bdoc = bdoc.replace(root_tag, new_root, 1)

    # ---------- body: section-1 table + pandoc tables
    head, rest = bdoc.split("<w:body>", 1)
    inner, tail = rest.rsplit("</w:body>", 1)
    blocks = split_top_level(inner)
    blocks = build_section1_table(blocks)
    ti = 0
    for k, b in enumerate(blocks):
        if b.startswith("<w:tbl") and 'w:styleId' not in b and "%%" not in b and "gen_random" not in b:
            if 'w:tblW w:w="%d" w:type="dxa"' % TEXT_WIDTH in b and "Nazwa projektu" in b:
                continue  # the section-1 table built above
            widths = PANDOC_TABLE_WIDTHS[ti] if ti < len(PANDOC_TABLE_WIDTHS) else None
            ti += 1
            if widths is None:
                ncols = b.count("<w:gridCol")
                widths = [TEXT_WIDTH // ncols] * ncols
            blocks[k] = fix_pandoc_table(b, widths)
            # a small spacer after each table so the following paragraph does not stick to it
            blocks[k] += '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/></w:pPr></w:p>'
    bdoc = head + "<w:body>" + title_xml + "".join(blocks) + "</w:body>" + tail
    (bdir / "word/document.xml").write_text(bdoc, encoding="utf-8")

    # ---------- styles the template lacks
    spath = bdir / "word/styles.xml"
    styles = spath.read_text(encoding="utf-8")
    styles = re.sub(r'<w:style [^>]*w:styleId="SourceCode".*?</w:style>', "", styles, flags=re.S)
    for sid in re.findall(r'w:styleId="([A-Za-z]+)"', EXTRA_STYLES):
        styles = re.sub(r'<w:style [^>]*w:styleId="%s".*?</w:style>' % sid, "", styles, flags=re.S)
    styles = styles.replace("</w:styles>", EXTRA_STYLES + "</w:styles>")
    spath.write_text(styles, encoding="utf-8")

    ct_path = bdir / "[Content_Types].xml"
    ct = ct_path.read_text(encoding="utf-8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
        ct_path.write_text(ct, encoding="utf-8")

    zip_dir(bdir, OUT)
    used = set(re.findall(r'<w:pStyle w:val="([^"]+)"', bdoc)) | set(re.findall(r'<w:rStyle w:val="([^"]+)"', bdoc))
    defined = set(re.findall(r'w:styleId="([^"]+)"', styles))
    print("styles used but undefined:", sorted(used - defined))
    print("written", OUT, OUT.stat().st_size, "bytes; tables fixed:", ti)


if __name__ == "__main__":
    main()
