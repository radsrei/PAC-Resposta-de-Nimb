 #!/usr/bin/env python3
"""
Extrai o Tormenta20 (PDF do InDesign, 407 páginas, 2 colunas) para um XML
hierárquico: capítulo > seção > subseção > ... > conteúdo.
 
    A hierarquia vem de duas fontes que se completam:
    1. os 299 marcadores do próprio PDF (títulos oficiais e níveis);
    2. as assinaturas tipográficas do livro, que descem mais fundo que os marcadores.
 
Assinaturas identificadas na análise do documento:
    Tormenta20-Regular  74-100pt  título de capítulo
    Tormenta20-Regular  26-27pt   seção grande (nome de raça, classe, etc.)
    Tormenta20-Regular  21pt      seção
    Tormenta20-Regular  16pt      subseção
    Tormenta20-Regular  11pt      número de página (descartado)
    Tormenta20-Regular  9pt       linha de metadados de magia ("Arcana 1 (Abjuração)")
    IowanOldStyle-Bold  12pt/8598561   título de tabela ("Tabela 1-5: O Arcanista")
    IowanOldStyle-Bold  10pt/8598561   cabeçalho corrido (descartado)
    IowanOldStyle-Bold  9.5pt/12003883 nome de verbete ("Versátil.")
    IowanOldStyle-Bold  8.5pt          rótulo de ficha ("Execução:", "Alcance:")
    IowanOldStyle-Italic             texto de ficção/ambientação
    IowanOldStyle-Roman              corpo de texto
    SourceSansPro-Regular 9pt        célula de tabela
    SourceSansPro-Bold    9pt        cabeçalho de tabela
    SourceSansPro-Bold    8pt        legenda de arte
    Helvetica / e-mail               marca d'água (descartada)
 """
import html
import re
import sys
import unicodedata
import collections

# PyMuPDF exposes the `pymupdf` module name in current versions.
import importlib

# O nome do módulo varia conforme a versão/instalação do PyMuPDF.
try:
    pymupdf = importlib.import_module("pymupdf")
except ImportError:
    pymupdf = importlib.import_module("fitz")

PDF = sys.argv[1] if len(sys.argv) > 1 else "C:\\Users\\rafab\\Documentos\\PAC-Resposta-de-Nimb\\Livros\\T20_teste.pdf"
SAIDA = sys.argv[2] if len(sys.argv) > 2 else "tormenta20.xml"
COR_TITULO = 13576745      # laranja dos títulos Tormenta20
COR_VERBETE = 12003883     # vermelho dos nomes de verbete
COR_TABELA = 8598561
COR_EPIGRAFE = 16374138    # dourado das citações de abertura       # marrom dos títulos de tabela e do cabeçalho corrido
 
# ---------------------------------------------------------------- utilidades
def limpar(txt: str) -> str:
     """Junta hifenização de texto justificado e normaliza espaços."""
     txt = txt.replace("­", "").replace("\t", " ")
    # "pe- rícias" -> "perícias" (hífen de quebra, seguido de minúscula)
     txt = re.sub(r"(\w)-\s+-([A-Za-zÀ-ÿ])", r"\1-\2", txt)   # "Rainha- -Imperatriz"
     txt = re.sub(r"(\w)-\s+([a-zà-öø-ÿ])", r"\1\2", txt)
     txt = re.sub(r"\s+", " ", txt).strip()
     return txt
 
 
def desduplicar(txt: str) -> str:
     """
     Títulos grandes e legendas são desenhados duas vezes (camada de sombra do
     InDesign), o que faz o texto sair dobrado: 'Introdução Introdução'.
     """
     t = txt.strip()
     meio = len(t) // 2
     if len(t) > 6 and t[:meio].strip() == t[meio:].strip():
         return t[:meio].strip()
     # dobra palavra a palavra: 'Caldela Caldela CAssaro CAssaro'
     p = t.split()
     if len(p) >= 4 and len(p) % 2 == 0 and p[: len(p) // 2] == p[len(p) // 2 :]:
         return " ".join(p[: len(p) // 2])
     if len(p) >= 2 and all(p[i] == p[i + 1] for i in range(0, len(p) - 1, 2)):
         return " ".join(p[::2])
     return t
 
 
def titulo_descartavel(txt: str) -> bool:
     """Capitulares, numerais soltos e a palavra CAPÍTULO não são títulos de verdade."""
     t = txt.strip()
     if len(t) <= 2 and not t.isdigit():       # capitular ("D", "T", "C")
         return True
     if re.fullmatch(r"[\dIVXLC]{1,4}[ºª°]?", t):
         return True
     if sem_acento(t) in ("capitulo", "sumario", "indice"):
         return True
     if "......" in t or "…" in t:              # linha do sumário impresso
         return True
     return False
 
 
def x(txt: str) -> str:
     return html.escape(txt, quote=True)
 
 
def sem_acento(s: str) -> str:
     return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
 
 
# ---------------------------------------------------------------- classificação
def classificar(span, linha_bbox, altura_pagina):
    """Devolve (tipo, nivel) para um trecho de texto."""
    f, tam, cor = span["font"], round(span["size"], 1), span["color"]
    y = linha_bbox[1]
    rodape = y > altura_pagina - 60
 
    if "Helvetica" in f:
        return ("ruido", 0)
    if "Tormenta20" in f:
        # o "nível" aqui é a CLASSE TIPOGRÁFICA (1 = maior). O nível real na
        # árvore é calculado depois, relativo ao marcador do PDF mais próximo.
        if tam >= 60:
            return ("titulo", 1)
        if tam >= 40:
            return ("titulo", 2) if not rodape else ("ruido", 0)
        if tam >= 25:
            return ("titulo", 2)
        if tam >= 19:
            return ("titulo", 3)
        if tam >= 14:
            return ("titulo", 4)
        if 10 <= tam <= 12:
            return ("ruido", 0)          # número de página
        if tam <= 9.5:
            return ("magia_meta", 0)
        return ("titulo", 4)
    if "SourceSansPro" in f:
        if tam <= 8.5:
            return ("legenda", 0)
        return ("tabela_cabecalho", 0) if "Bold" in f else ("tabela_celula", 0)
    if "Iowan" in f:
        if "Bold" in f and cor == COR_TABELA:
            return ("ruido", 0) if rodape else ("tabela_titulo", 0)
        if "Bold" in f and cor == COR_VERBETE:
            return ("verbete", 0)
        if "Bold" in f and tam >= 11:
            return ("titulo", 4)
        if "Bold" in f and 9.8 <= tam <= 10.6 and cor == COR_EPIGRAFE:
            return ("epigrafe", 0)             # citação de abertura de capítulo
        if "Bold" in f and 9.8 <= tam <= 10.6 and cor == 0:
            # mesma aparência serve a duas coisas: rótulo de coluna (curto, sem frase)
            # e o parágrafo de abertura do capítulo (longo). O tamanho decide.
            texto_span = span["text"].strip()
            if len(texto_span) <= 28 and not texto_span.endswith((".", ",", ";")):
                return ("tabela_cabecalho", 0)
            return ("destaque", 0)
        if "Bold" in f:
            return ("rotulo", 0)
        if "Italic" in f:
            return ("ficcao", 0)
        return ("corpo", 0)
    return ("corpo", 0)

# ---------------------------------------------------------------- leitura da página
def colunas_da_pagina(itens, larg):
    """
    Descobre onde começam as colunas da página. O livro alterna entre duas colunas
    (regras) e três (listas de magias e de poderes), então isso não pode ser fixo:
    agrupa os inícios (x0) dos blocos estreitos e cada grupo vira uma coluna.
    """
    xs = sorted(round(i["bbox"][0]) for i in itens if not i["largo"])
    if not xs:
        return [0.0]
    grupos, atual = [], [xs[0]]
    for v in xs[1:]:
        if v - atual[-1] <= 25:          # mesma coluna
            atual.append(v) # type: ignore
        else:
            grupos.append(atual)
            atual = [v]
    grupos.append(atual)
    # descarta agrupamentos raros (caixas de texto soltas, legendas sobre arte)
    inicios = [sum(g) / len(g) for g in grupos if len(g) >= 2] or [sum(g) / len(g) for g in grupos]
    return sorted(inicios)
 
def blocos_ordenados(pagina):
    """Ordena os blocos na ordem de leitura, respeitando o número real de colunas."""
    larg = pagina.rect.width
    itens = []
    for b in pagina.get_text("dict")["blocks"]:
        if b.get("type") != 0 or not b.get("lines"):
            continue
        x0, y0, x1, y1 = b["bbox"]
        itens.append({"bbox": b["bbox"], "lines": b["lines"],
                      "largo": (x1 - x0) > 0.6 * larg})
    inicios = colunas_da_pagina(itens, larg)
    for i in itens:
        # cada bloco pertence à coluna cujo início é o mais próximo do dele
        i["col"] = min(range(len(inicios)), key=lambda k: abs(inicios[k] - i["bbox"][0]))
    itens.sort(key=lambda i: i["bbox"][1])

     # blocos que ocupam a largura toda (títulos, tabelas largas) separam faixas;
     # dentro de cada faixa lê-se a coluna esquerda inteira e depois a direita
    faixas, atual = [], []
    for it in itens:
        if it["largo"]:
            if atual:
                faixas.append(atual)
                atual = []
            faixas.append([it])
        else:
            atual.append(it)
    if atual:
        faixas.append(atual)

    saida = []
    for faixa in faixas:
        saida.extend(sorted(faixa, key=lambda i: (i["col"], i["bbox"][1], i["bbox"][0])))
    return saida
 
 
def elementos_da_pagina(doc, pno):
    """Converte a página numa lista linear de elementos já classificados."""
    pagina = doc[pno]
    alt = pagina.rect.height
    out = []
    capitular = []
    for bloco in blocos_ordenados(pagina):
        for linha in bloco["lines"]:
            spans = [s for s in linha["spans"] if s["text"].strip()]
            if not spans:
                continue
            texto = spans[0]["text"]
            for ant, s_ in zip(spans, spans[1:]):
                # se há um vão entre os dois trechos, é espaço de verdade (colunas de tabela)
                if s_["bbox"][0] - ant["bbox"][2] > 1.2 and not texto.endswith(" "):
                    texto += " "
                texto += re.sub(r"^\s*\d+[.)]?\s*", "", s_["text"], count=1)
            texto = re.sub(r"^\s*\d+[.)]?\s*", "", texto, count=1)
            if "rafael97pereira" in texto or "@gmail.com" in texto:
                continue
            tipo, nivel = classificar(spans[0], linha["bbox"], alt)
            if tipo == "ruido":
                continue
            # o nome do verbete vem em negrito colorido e o resto do parágrafo em seguida
            nome = None
            if tipo == "verbete":
                neg = []
                for s in spans:
                    if "Bold" in s["font"] and s["color"] == COR_VERBETE:
                        neg.append(s["text"])
                    else:
                        break
                nome = limpar("".join(neg)).rstrip(".").strip()
                texto = limpar("".join(s["text"] for s in spans[len(neg):]))
            else:
                texto = limpar(texto)
            if tipo in ("legenda", "titulo"):
                texto = desduplicar(texto)
            m_idx = re.match(r"^(.{2,60}?)[.\u2026]{3,}\s*([\d,\s\-]{1,30})$", texto)
            if m_idx:
                out.append({"tipo": "indice", "nivel": 0,
                            "texto": limpar(m_idx.group(2)), "nome": limpar(m_idx.group(1)),
                            "pag": pno + 1, "y": linha["bbox"][1], "x": linha["bbox"][0],
                            "col": bloco["col"], "tam": round(spans[0]["size"], 1)})
                continue
            if "......" in texto:              # pontilhado sem página: descarta
                continue
            if tipo == "titulo":
                if len(texto) == 1 and texto.isalpha() and spans[0]["size"] > 30:
                    capitular.append(texto)      # letra decorativa: volta ao texto seguinte
                    continue
                if titulo_descartavel(texto):
                     continue
            if capitular and tipo in ("corpo", "destaque", "ficcao", "epigrafe"):
                texto = capitular.pop() + texto
            if not texto and not nome:
                continue
            if tipo in ("tabela_celula", "tabela_cabecalho") and len(spans) > 1:
                # numa tabela, um vão grande entre trechos separa COLUNAS, não palavras
                grupo, saida_cel = [spans[0]], []
                for ant, s_ in zip(spans, spans[1:]):
                    if s_["bbox"][0] - ant["bbox"][2] > 6:
                        saida_cel.append(grupo); grupo = [s_]
                    else:
                        grupo.append(s_)
                saida_cel.append(grupo)
                if len(saida_cel) > 1:
                    for g in saida_cel:
                        t_ = limpar("".join(z["text"] for z in g))
                        if t_:
                            out.append({"tipo": tipo, "nivel": 0, "texto": t_, "nome": None,
                                        "pag": pno + 1, "y": linha["bbox"][1], "x": g[0]["bbox"][0],
                                        "col": bloco["col"], "tam": round(g[0]["size"], 1)})
                    continue
            out.append({"tipo": tipo, "nivel": nivel, "texto": texto, "nome": nome,
                        "pag": pno + 1, "y": linha["bbox"][1], "x": linha["bbox"][0],
                        "col": bloco["col"], "tam": round(spans[0]["size"], 1)})
    return out

# ---------------------------------------------------------------- junção de linhas
def juntar(elementos):
    """Une linhas consecutivas do mesmo tipo num parágrafo só."""
    juntos = []
    for e in elementos:
        a = juntos[-1] if juntos else None
        # títulos grandes ocupam várias linhas ("Construção de" / "personagem") e têm
        # entrelinha proporcional ao corpo da letra
        folga = 22
        if a and a["tipo"] == "titulo" == e["tipo"] and a["nivel"] == e["nivel"]:
            folga = max(22, a["tam"] * 1.6)
        mesmo_fluxo = (
            a and a["tipo"] == e["tipo"] and a["pag"] == e["pag"]
            and (a["col"] == e["col"] or e["tipo"] == "titulo")
            and e["tipo"] in ("corpo", "ficcao", "titulo", "legenda", "epigrafe", "destaque", "rotulo")
            and abs(e["y"] - a["y_fim"]) < folga
            and (e["tipo"] != "titulo" or a["nivel"] == e["nivel"])
        )
        if a and e["tipo"] == "verbete" and e["nome"] is None:
            mesmo_fluxo = False
        if mesmo_fluxo:
            if a and a["tipo"] == "titulo" and a["nivel"] != e["nivel"]:
                pass
            else:
                # a camada de sombra repete o mesmo texto num bloco à parte
                if (a and a["tipo"] in ("titulo", "legenda") and e["texto"] # type: ignore
                        and (e["texto"] == a["texto"] or a["texto"].endswith(" " + e["texto"]))): # type: ignore
                    a["y_fim"] = e["y"] # type: ignore
                    continue
                a["texto"] = limpar(a["texto"] + " " + e["texto"]) # type: ignore
                a["y_fim"] = e["y"] # pyright: ignore
                continue
        # ênfase em negrito no meio de um parágrafo: continua o mesmo parágrafo
        if (a and a["tipo"] in ("corpo", "destaque") and e["tipo"] in ("rotulo", "destaque")
                and a["pag"] == e["pag"] and a["col"] == e["col"] and abs(e["y"] - a["y_fim"]) < 22):
            a["texto"] = limpar(a["texto"] + " " + e["texto"])
            a["y_fim"] = e["y"]
            continue
        # continuação de um verbete/rótulo: o corpo que segue pertence a ele
        if (a and a["tipo"] in ("verbete", "rotulo") and e["tipo"] == "corpo"
                and a["pag"] == e["pag"] and a["col"] == e["col"] and abs(e["y"] - a["y_fim"]) < 22):
            a["texto"] = limpar(a["texto"] + " " + e["texto"])
            a["y_fim"] = e["y"]
            continue
        e = dict(e)
        e["y_fim"] = e["y"]
        juntos.append(e)
    for i, j in enumerate(juntos):
        if (j["tipo"] == "epigrafe" and j["texto"].lstrip().startswith(("—", "–", "-"))
                and i > 0 and juntos[i - 1]["tipo"] == "epigrafe"):
            juntos[i - 1]["autor"] = j["texto"].lstrip("—–- ").strip()
            j["texto"] = ""
    juntos = [j for j in juntos if j["texto"] or j.get("nome")]
    for j in juntos:
        if j["tipo"] in ("titulo", "legenda"):
            j["texto"] = desduplicar(j["texto"])
    return [j for j in juntos if not (j["tipo"] == "titulo" and titulo_descartavel(j["texto"]))]
 
 
# ---------------------------------------------------------------- tabelas
def agrupar_tabelas(elementos):
    """Transforma sequências de células em tabelas com linhas e colunas."""
    saida, buffer_ = [], []
 
    def descarregar():
        if not buffer_:
            return
        linhas = collections.defaultdict(list)
        for c in buffer_:
            chave = round(c["y"] / 6)          # tolerância vertical de uma linha
            linhas[chave].append(c)
        tabela = []
        for k in sorted(linhas):
            celulas = sorted(linhas[k], key=lambda c: c["x"])
            tabela.append([{"texto": c["texto"], "cab": c["tipo"] == "tabela_cabecalho"} for c in celulas])
        # numa ficha de criatura, linha que começa em minúscula continua a anterior
        if all(len(l) == 1 for l in tabela) and len(tabela) >= 3:
            juntada = []
            for l in tabela:
                t = l[0]["texto"]
                if juntada and (t[:1].islower() or t[:1] in "(+–-—" or t[:1].isdigit()):
                    juntada[-1][0]["texto"] = limpar(juntada[-1][0]["texto"] + " " + t)
                else:
                    juntada.append(l)
            tabela = juntada
        so_uma_coluna = all(len(l) == 1 for l in tabela)
        tipo = "estatisticas" if (so_uma_coluna and len(tabela) >= 3) else "tabela"
        saida.append({"tipo": tipo, "linhas": tabela, "pag": buffer_[0]["pag"], "titulo": None})
        buffer_.clear()
 
    for e in elementos:
        if e["tipo"] in ("tabela_celula", "tabela_cabecalho"):
            if buffer_ and (e["pag"] != buffer_[-1]["pag"] or abs(e["y"] - buffer_[-1]["y"]) > 40):
                descarregar()
            buffer_.append(e)
        else:
            descarregar()
            saida.append(e)
    descarregar()
 
    # "Tabela 1-4:" e "Níveis de Personagem" saem em linhas separadas: junta antes
    for i in range(len(saida) - 1):
        a, b = saida[i], saida[i + 1]
        if (a and b and a.get("tipo") == "tabela_titulo" == b.get("tipo")
                and a["pag"] == b["pag"] and abs(b["y"] - a["y"]) < 30):
            a["texto"] = limpar(a["texto"] + " " + b["texto"])
            saida[i + 1] = None
    saida = [e for e in saida if e]
 
    # o título "Tabela 3-3: Armas" aparece antes da tabela, na mesma página
    for i, e in enumerate(saida):
        if e.get("tipo") == "tabela" and not e["titulo"]:
            for j in range(i - 1, -1, -1):
                v = saida[j]
                if v is None:
                    continue
                if v.get("tipo") == "tabela_titulo" and v["pag"] == e["pag"] and e["tipo"] == "tabela":
                    e["titulo"] = v["texto"]
                    saida[j] = None
                    break
                if v.get("tipo") == "titulo":   # não atravessa um título de seção
                    break
    return [e for e in saida if e]
 
 
# ---------------------------------------------------------------- montagem do XML
def nivel_do_toc(toc):
    """Mapa: (página, texto normalizado) -> nível oficial do marcador."""
    m = {}
    for nivel, titulo, pag in toc:
        m[(pag, sem_acento(limpar(titulo)))] = (nivel, limpar(titulo))
    return m
 
 
def montar(doc):
    toc = doc.get_toc()
    mapa_toc = nivel_do_toc(toc)
    paginas_toc = collections.defaultdict(list)
    for nivel, titulo, pag in toc:
        paginas_toc[pag].append((nivel, limpar(titulo)))
    corpo = []
    for pno in range(doc.page_count):
        els = agrupar_tabelas(juntar(elementos_da_pagina(doc, pno)))
        corpo.extend(els)
        if (pno + 1) % 50 == 0:
            print(f"  ... {pno + 1}/{doc.page_count} páginas", file=sys.stderr)
 
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<livro titulo="Tormenta20" edicao="Livro Básico" paginas="%d">' % doc.page_count]
 
    # sumário oficial, para navegação rápida
    linhas.append("  <sumario>")
    for nivel, titulo, pag in toc:
        linhas.append(f'    <entrada nivel="{nivel}" pagina="{pag}">{x(limpar(titulo))}</entrada>')
    linhas.append("  </sumario>")
 
    pilha = []   # [(nivel, tag)]
    ancora = [1, 1]   # (classe tipográfica, nível na árvore) do último marcador visto
    ind = lambda: "  " * (len(pilha) + 1)
 
    def fechar_ate(nivel):
        while pilha and pilha[-1][0] >= nivel:
            n, tag = pilha.pop()
            linhas.append("  " * (len(pilha) + 1) + f"</{tag}>")

    TAGS = {1: "capitulo", 2: "secao", 3: "subsecao", 4: "topico", 5: "subtopico", 6: "item"}
    linhas.append("  <conteudo>")
 
    for e in corpo:
        t = e["tipo"]
        if t == "titulo":
            titulo = e["texto"]
            classe = e["nivel"]          # classe tipográfica (1 = título maior)
            m_nd = re.match(r"^ND\s+([\d/]+)$", titulo.strip())
            if m_nd:
                # nível de desafio: anota na criatura já aberta em vez de criar gaveta
                for k in range(len(linhas) - 1, -1, -1):
                    if re.search(r"<(capitulo|secao|subsecao|topico|subtopico|item) titulo=", linhas[k]):
                        if ' nd="' not in linhas[k]:
                            linhas[k] = linhas[k].rstrip(">") + f' nd="{x(m_nd.group(1))}">'
                        break
                continue
            # se o marcador do PDF conhece este título, o nível dele manda
            chave = (e["pag"], sem_acento(titulo))
            oficial = mapa_toc.get(chave)
            if not oficial:
                alvo = sem_acento(titulo)
                for niv, tit in paginas_toc.get(e["pag"], []):
                    t = sem_acento(tit)
                    if alvo and (alvo in t or t in alvo) and abs(len(t) - len(alvo)) < 24:
                        oficial = (niv, tit)
                        break
            if oficial:
                # o marcador manda no nível E reancora as classes tipográficas:
                # daqui pra frente, um título menor que este vira filho dele
                nivel = oficial[0]
                titulo = oficial[1]
                ancora[0], ancora[1] = classe, nivel
            elif e["pag"] < 10:
                # capa, prêmios e folha de rosto: texto decorativo, não é estrutura
                linhas.append(ind() + f'<p pagina="{e["pag"]}">{x(titulo)}</p>')
                continue
            else:
                # sem marcador: o nível sai da distância tipográfica até a âncora
                nivel = ancora[1] + (classe - ancora[0])
                if classe == 1:
                    nivel, ancora[0], ancora[1] = 1, 1, 1
            nivel = max(1, min(6, nivel))
            fechar_ate(nivel)
            tag = TAGS.get(nivel, "item")
            linhas.append(ind() + f'<{tag} titulo="{x(titulo)}" pagina="{e["pag"]}">')
            pilha.append((nivel, tag))
        elif t == "tabela":
            linhas.append(ind() + f'<tabela{f" titulo="+chr(34)+x(e["titulo"])+chr(34) if e["titulo"] else ""} pagina="{e["pag"]}">')
            for i, linha in enumerate(e["linhas"]):
                marca = "cabecalho" if all(c["cab"] for c in linha) and i == 0 else "linha"
                celulas = "".join(f"<c>{x(c['texto'])}</c>" for c in linha)
                linhas.append(ind() + f"  <{marca}>{celulas}</{marca}>")
            linhas.append(ind() + "</tabela>")
        elif t == "estatisticas":
            linhas.append(ind() + f'<estatisticas pagina="{e["pag"]}">')
            for linha in e["linhas"]:
                linhas.append(ind() + f'  <linha>{x(linha[0]["texto"])}</linha>')
            linhas.append(ind() + "</estatisticas>")
        elif t == "verbete":
            nome = e.get("nome") or ""
            linhas.append(ind() + f'<verbete nome="{x(nome)}" pagina="{e["pag"]}">{x(e["texto"])}</verbete>')
        elif t == "rotulo":
            # ficha de magia: "Execução: padrão; Alcance: curto; ... Duração: X." + descrição
            txt = e["texto"]
            m = re.match(r"^\s*(Execução|Execucao)\s*:", txt)
            if m:
                campos, resto = {}, txt
                padrao = r"(Execução|Alcance|Alvo|Área|Area|Efeito|Duração|Duracao|Resistência|Resistencia)\s*:\s*([^;.]*)(;|\.)"
                pos = 0
                for mm in re.finditer(padrao, txt):
                    if mm.start() > pos + 3:
                        break
                    campos[sem_acento(mm.group(1))] = mm.group(2).strip()
                    pos = mm.end()
                resto = txt[pos:].strip()
                attrs = "".join(f' {k}="{x(v)}"' for k, v in campos.items())
                if campos:
                    linhas.append(ind() + f'<ficha{attrs} pagina="{e["pag"]}">{x(resto)}</ficha>')
                    continue
            linhas.append(ind() + f'<campo pagina="{e["pag"]}">{x(txt)}</campo>')
        elif t == "magia_meta":
            linhas.append(ind() + f'<classificacao>{x(e["texto"])}</classificacao>')
        elif t == "epigrafe":
            aut = f' autor="{x(e["autor"])}"' if e.get("autor") else ""
            linhas.append(ind() + f'<epigrafe{aut} pagina="{e["pag"]}">{x(e["texto"])}</epigrafe>')
        elif t == "destaque":
            linhas.append(ind() + f'<p destaque="sim" pagina="{e["pag"]}">{x(e["texto"])}</p>')
        elif t == "ficcao":
            linhas.append(ind() + f'<ficcao pagina="{e["pag"]}">{x(e["texto"])}</ficcao>')
        elif t == "legenda":
            linhas.append(ind() + f'<legenda pagina="{e["pag"]}">{x(e["texto"])}</legenda>')
        elif t == "tabela_titulo":
            linhas.append(ind() + f'<titulo-tabela pagina="{e["pag"]}">{x(e["texto"])}</titulo-tabela>')
        elif t == "indice":
            linhas.append(ind() + f'<indice termo="{x(e.get("nome") or "")}" paginas="{x(e["texto"])}"/>')
        elif t == "corpo":
            linhas.append(ind() + f'<p pagina="{e["pag"]}">{x(e["texto"])}</p>')
 
    fechar_ate(1)
    linhas.append("  </conteudo>")
    linhas.append("</livro>")
    return "\n".join(linhas)


if __name__ == "__main__":
    print(f"lendo {PDF} ...", file=sys.stderr)
    doc = pymupdf.open(PDF)
    xml = montar(doc)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"gravado {SAIDA}: {len(xml)/1e6:.2f} MB", file=sys.stderr)
