def build_ted_query(q):

    q = clean_query(q)

    if not q:
        q = "archaeology"

    # Pesquisa por texto completo no TED
    return f'FT~"{q}"'
