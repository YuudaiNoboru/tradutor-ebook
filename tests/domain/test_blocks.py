from tradutor.domain import Block, Chapter


def test_block_defaults():
    block = Block(id=0, kind="paragrafo", text="oi")
    assert block.id == 0
    assert block.kind == "paragrafo"
    assert block.text == "oi"
    assert block.protected is False


def test_block_protected():
    block = Block(id=1, kind="codigo", text="x = 1", protected=True)
    assert block.protected is True


def test_chapter_defaults():
    chapter = Chapter()
    assert chapter.blocks == []
    assert chapter.path == ""
    assert chapter.title == ""


def test_chapter_with_blocks():
    blocks = [Block(id=0, kind="titulo", text="Capitulo 1")]
    chapter = Chapter(blocks=blocks, path="cap1.xhtml", title="Capitulo 1")
    assert chapter.blocks == blocks
    assert chapter.path == "cap1.xhtml"
    assert chapter.title == "Capitulo 1"
