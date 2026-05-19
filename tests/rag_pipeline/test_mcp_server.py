from rag_display import source_basename


def test_source_basename_matches_mcp_contract():
    assert source_basename(r"04_Legal_Corporate\map\doc.pdf") == "doc.pdf"
