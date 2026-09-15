#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 CONVERSOR/SEGMENTADOR DE PDF COM DOCLING — Projeto PAC-Resposta-de-Nimb
=============================================================================
Repositório de referência: https://github.com/radsrei/PAC-Resposta-de-Nimb

O QUE ESTE SCRIPT FAZ
----------------------
1. Recebe um PDF de um livro (ex.: RPG) e um "mapa de sumário" (capítulos e
   subcapítulos com página inicial), montado a partir da página de SUMÁRIO
   do próprio livro.
2. Calcula automaticamente a página final de cada trecho (pega a página
   inicial do próximo trecho - 1), mas permite EDITAR manualmente cada
   intervalo antes de processar — é aqui que você pode "cortar" pedaços
   como agradecimentos, ficha técnica, prefácio protocolar etc.
3. Cada trecho tem uma flag `incluir` (True/False). Só entra na conversão
   quem estiver com `incluir = True`.
4. Existe também uma condição pelo NOME DO LIVRO: se o nome do arquivo/],
   livro não estiver na lista de livros permitidos, o processamento inteiro
   é abortado (proteção contra rodar o script no arquivo errado).
5. Para cada trecho incluído:
     a) separa (split) as páginas correspondentes do PDF original usando
        `pypdf` (gera um PDF menor, só daquele capítulo/seção);
     b) converte esse PDF menor com o Docling, gerando Markdown estruturado;
     c) varre o documento Docling em busca de TABELAS e grava cada uma
        separadamente em CSV (e também embutida no Markdown).
6. Tudo é salvo em uma estrutura de pastas organizada por capítulo.

COMO USAR
---------
1. Ajuste a seção "1. CONFIGURAÇÃO GERAL" com o caminho do seu PDF.
2. Ajuste a lista `SUMARIO` na seção "2. MAPA DO SUMÁRIO" — ela já vem
   pré-preenchida com os capítulos do livro que você enviou (baseado na
   imagem do sumário). Confira/corrija as páginas antes de rodar de verdade.
3. Rode o script. Ele primeiro mostra o "modo revisão" (loop interativo)
   para você validar/editar cada intervalo de página e decidir o que entra
   ou não na conversão.
4. Depois disso, ele processa cada trecho incluído.

DEPENDÊNCIAS
------------
    pip install docling pypdf pandas
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# =============================================================================
# 1. CONFIGURAÇÃO GERAL — EDITE AQUI
# =============================================================================

CONFIG = {
    # Caminho do PDF original do livro
    "pdf_entrada": "/mnt/user-data/uploads/tormenta20_livro_basico.pdf",

    # Pasta onde tudo será salvo (será criada se não existir)
    "pasta_saida": "/mnt/user-data/outputs/tormenta20_segmentado",

    # Nome "lógico" deste livro (usado na condição de segurança abaixo)
    "nome_livro": "Tormenta20 - Livro Básico",

    # Total de páginas do PDF final do índice remissivo/ficha (opcional,
    # só usado para fechar o último intervalo do sumário). Ajuste conforme
    # o PDF real, ou deixe None para o script perguntar/inferir automaticamente.
    "total_paginas_pdf": 404,
}

# -----------------------------------------------------------------------------
# CONDIÇÃO PELO NOME DO LIVRO
# -----------------------------------------------------------------------------
# Só livros cujo "nome_livro" (ou parte do nome do arquivo) estiver nesta
# lista terão o processo de conversão executado. Isso evita rodar o script
# sem querer em cima do arquivo errado. Adicione quantos nomes quiser.
LIVROS_PERMITIDOS = [
    "Tormenta20 - Livro Básico",
    "Tormenta20 - Ameacas de Arton",
    "Tormenta20 - Guia de Cavaleiro",
]


def checar_condicao_livro(nome_livro: str, permitidos: list[str]) -> bool:
    """Verifica (com correspondência flexível) se o livro pode ser processado.

    Faz uma comparação "normalizada" (minúsculas, sem acento simples) para
    não travar por causa de maiúscula/minúscula ou hífen.
    """

    def normaliza(txt: str) -> str:
        txt = txt.lower().strip()
        troca = str.maketrans("áàâãéèêíìîóòôõúùûç", "aaaaeeeiiioooouuuc")
        return txt.translate(troca)

    alvo = normaliza(nome_livro)
    return any(normaliza(p) == alvo for p in permitidos)


# =============================================================================
# 2. MAPA DO SUMÁRIO — EDITE AQUI
# =============================================================================
# Estrutura extraída da página de SUMÁRIO enviada (nível 1 = capítulo,
# nível 2 = seção/subseção dentro do capítulo). As páginas de INÍCIO foram
# transcritas do sumário; a página de FIM é calculada automaticamente como
# "início do próximo item do MESMO nível, menos 1" — revise no loop interativo.
#
# O campo `incluir` já vem marcado como False para trechos tipicamente
# "protocolares" (prefácio, playtesters, índice remissivo etc.), que
# normalmente não interessam para extração de conteúdo de regras.


@dataclass
class TrechoSumario:
    nivel: int              # 1 = capítulo, 2 = subseção
    titulo: str
    pagina_inicio: int
    pagina_fim: Optional[int] = None   # calculado depois, se None
    incluir: bool = True
    capitulo_pai: Optional[str] = None  # preenchido automaticamente

    def slug(self) -> str:
        s = re.sub(r"[^\w\s-]", "", self.titulo, flags=re.UNICODE).strip().lower()
        s = re.sub(r"[\s_-]+", "_", s)
        return s or "trecho"


SUMARIO: list[TrechoSumario] = [
    TrechoSumario(1, "Prefácio", 4, incluir=False),
    TrechoSumario(1, "Introdução", 6, incluir=True),
    TrechoSumario(2, "O que é Tormenta20?", 8, capitulo_pai="Introdução"),
    TrechoSumario(2, "Mecânica Básica", 9, capitulo_pai="Introdução"),
    TrechoSumario(2, "Termos Importantes", 11, capitulo_pai="Introdução"),
    TrechoSumario(2, "20 Coisas a Saber", 12, capitulo_pai="Introdução"),

    TrechoSumario(1, "Capítulo 1 - Construção de Personagem", 14),
    TrechoSumario(2, "Conceito de Personagem", 16, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Atributos Básicos", 17, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Raças", 18, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Classes", 32, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Origens", 85, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Deuses", 96, capitulo_pai="Capítulo 1"),
    TrechoSumario(2, "Toques Finais", 106, capitulo_pai="Capítulo 1"),

    TrechoSumario(1, "Capítulo 2 - Perícias & Poderes", 112),
    TrechoSumario(2, "Perícias", 114, capitulo_pai="Capítulo 2"),
    TrechoSumario(2, "Poderes Gerais", 123, capitulo_pai="Capítulo 2"),

    TrechoSumario(1, "Capítulo 3 - Equipamento", 138),
    TrechoSumario(2, "Armas", 142, capitulo_pai="Capítulo 3"),
    TrechoSumario(2, "Armaduras & Escudos", 152, capitulo_pai="Capítulo 3"),
    TrechoSumario(2, "Itens Gerais", 155, capitulo_pai="Capítulo 3"),
    TrechoSumario(2, "Itens Superiores", 164, capitulo_pai="Capítulo 3"),

    TrechoSumario(1, "Capítulo 4 - Magia", 168),
    TrechoSumario(2, "Regras de Magias", 170, capitulo_pai="Capítulo 4"),
    TrechoSumario(2, "Lista de Magias Arcanas", 174, capitulo_pai="Capítulo 4"),
    TrechoSumario(2, "Lista de Magias Divinas", 176, capitulo_pai="Capítulo 4"),
    TrechoSumario(2, "Descrição das Magias", 178, capitulo_pai="Capítulo 4"),

    TrechoSumario(1, "Capítulo 5 - Jogando", 212),
    TrechoSumario(2, "Interpretando", 214, capitulo_pai="Capítulo 5"),
    TrechoSumario(2, "Regras do Jogo", 220, capitulo_pai="Capítulo 5"),
    TrechoSumario(2, "Combate", 230, capitulo_pai="Capítulo 5"),

    TrechoSumario(1, "Capítulo 6 - O Mestre", 240),
    TrechoSumario(2, "Como Mestrar", 242, capitulo_pai="Capítulo 6"),
    TrechoSumario(2, "Sessões, Aventuras e Campanhas", 248, capitulo_pai="Capítulo 6"),
    TrechoSumario(2, "NPCs", 257, capitulo_pai="Capítulo 6"),
    TrechoSumario(2, "Ambientes de Aventura", 263, capitulo_pai="Capítulo 6"),
    TrechoSumario(2, "Tempo entre Aventuras", 276, capitulo_pai="Capítulo 6"),

    TrechoSumario(1, "Capítulo 7 - Ameaças", 280),
    TrechoSumario(2, "Construindo Combates", 282, capitulo_pai="Capítulo 7"),
    TrechoSumario(2, "Criaturas", 282, capitulo_pai="Capítulo 7"),
    TrechoSumario(2, "Perigos", 322, capitulo_pai="Capítulo 7"),
    TrechoSumario(2, "Fichas de NPCs", 322, capitulo_pai="Capítulo 7"),

    TrechoSumario(1, "Capítulo 8 - Recompensas", 324),
    TrechoSumario(2, "Pontos de Experiência", 326, capitulo_pai="Capítulo 8"),
    TrechoSumario(2, "Tesouros", 327, capitulo_pai="Capítulo 8"),
    TrechoSumario(2, "Itens Mágicos", 333, capitulo_pai="Capítulo 8"),
    TrechoSumario(2, "Artefatos", 346, capitulo_pai="Capítulo 8"),

    TrechoSumario(1, "Capítulo 9 - Mundo de Arton", 350),
    TrechoSumario(2, "História Parcial", 352, capitulo_pai="Capítulo 9"),
    TrechoSumario(2, "O Reinado", 358, capitulo_pai="Capítulo 9"),
    TrechoSumario(2, "Além do Reinado", 370, capitulo_pai="Capítulo 9"),

    # --- Trechos protocolares/apêndices: desligados por padrão ---
    TrechoSumario(1, "Playtesters", 392, incluir=False),
    TrechoSumario(1, "Lista de Condições", 394, incluir=True),
    TrechoSumario(1, "Índice Remissivo", 396, incluir=False),
    TrechoSumario(1, "Ficha de Personagem", 400, incluir=True),
]


def calcular_paginas_fim(sumario: list[TrechoSumario], total_paginas: Optional[int]) -> None:
    """Preenche `pagina_fim` de cada trecho com base no início do PRÓXIMO
    trecho do mesmo nível (capítulo fecha no próximo capítulo, subseção
    fecha na próxima subseção/capítulo). Só sobrescreve quando `pagina_fim`
    ainda está None, então edições manuais feitas antes não são perdidas.
    """
    n = len(sumario)
    for i, item in enumerate(sumario):
        if item.pagina_fim is not None:
            continue
        proxima_pagina = None
        for j in range(i + 1, n):
            candidato = sumario[j]
            if candidato.nivel <= item.nivel:
                proxima_pagina = candidato.pagina_inicio
                break
        if proxima_pagina is not None:
            item.pagina_fim = max(item.pagina_inicio, proxima_pagina - 1)
        else:
            item.pagina_fim = total_paginas or item.pagina_inicio


# =============================================================================
# 3. LOOP DE REVISÃO/EDIÇÃO INTERATIVA
# =============================================================================
# Aqui é onde você pode, trecho a trecho:
#   [Enter]  -> aceitar como está
#   i <n>    -> mudar página de início para n
#   f <n>    -> mudar página de fim para n
#   x        -> alternar incluir/excluir (liga/desliga o trecho)
#   s        -> pular a revisão dos itens restantes (aceita o resto como está)
#   q        -> abortar tudo
#
# Use isso para remover na hora trechos como "agradecimentos", "expediente",
# "ficha técnica" etc., mesmo que eles não estejam explicitamente mapeados
# como um TrechoSumario — basta ajustar início/fim do trecho vizinho para
# "engolir" ou "pular" aquelas páginas.


def revisar_sumario_interativo(sumario: list[TrechoSumario], interativo: bool = True) -> None:
    if not interativo:
        return

    print("\n=== REVISÃO DO SUMÁRIO (edite início/fim e incluir/excluir) ===")
    print("Comandos por trecho: [Enter]=ok | i <pag>=muda início | f <pag>=muda fim")
    print("                     x=liga/desliga | s=pular revisão | q=abortar\n")

    for item in sumario:
        while True:
            status = "INCLUI" if item.incluir else "EXCLUI"
            prefixo = "  └─" if item.nivel == 2 else "●"
            pai = f" (em: {item.capitulo_pai})" if item.capitulo_pai else ""
            print(
                f"{prefixo} [{status}] {item.titulo}{pai} "
                f"— páginas {item.pagina_inicio}–{item.pagina_fim}"
            )
            resposta = input("   > ").strip().lower()

            if resposta == "":
                break
            elif resposta == "s":
                print("Revisão interrompida — mantendo o restante como está.")
                return
            elif resposta == "q":
                print("Processo abortado pelo usuário.")
                sys.exit(0)
            elif resposta == "x":
                item.incluir = not item.incluir
                continue
            elif resposta.startswith("i "):
                try:
                    item.pagina_inicio = int(resposta.split()[1])
                except (IndexError, ValueError):
                    print("   Uso: i <numero_da_pagina>")
                continue
            elif resposta.startswith("f "):
                try:
                    item.pagina_fim = int(resposta.split()[1])
                except (IndexError, ValueError):
                    print("   Uso: f <numero_da_pagina>")
                continue
            else:
                print("   Comando não reconhecido, tente de novo.")
                continue


# =============================================================================
# 4. SEPARAÇÃO DO PDF (split por intervalo de páginas)
# =============================================================================

def separar_pdf(pdf_entrada: Path, pagina_inicio: int, pagina_fim: int, destino: Path) -> Path:
    """Extrai o intervalo [pagina_inicio, pagina_fim] (1-based, inclusive) do
    PDF original e salva como um novo PDF em `destino`.
    """
    from pypdf import PdfReader, PdfWriter

    leitor = PdfReader(str(pdf_entrada))
    escritor = PdfWriter()

    total = len(leitor.pages)
    ini = max(1, pagina_inicio)
    fim = min(total, pagina_fim)

    for pagina_num in range(ini - 1, fim):  # pypdf é 0-based internamente
        escritor.add_page(leitor.pages[pagina_num])

    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "wb") as f:
        escritor.write(f)

    return destino


# =============================================================================
# 5. CONVERSÃO COM DOCLING (Markdown + Tabelas)
# =============================================================================

def converter_com_docling(pdf_path: Path):
    """Converte um PDF (ou um trecho já separado) usando o Docling e retorna
    o objeto `document` (com estrutura, texto e tabelas) e o Markdown gerado.
    """
    from docling.document_converter import DocumentConverter

    conversor = DocumentConverter()
    resultado = conversor.convert(str(pdf_path))
    documento = resultado.document

    markdown = documento.export_to_markdown()
    return documento, markdown


def salvar_tabelas(documento, pasta_tabelas: Path, prefixo: str) -> list[Path]:
    """Percorre as tabelas identificadas pelo Docling no documento e salva
    cada uma em CSV (via pandas) e também em Markdown, para fácil conferência.
    """
    import pandas as pd

    pasta_tabelas.mkdir(parents=True, exist_ok=True)
    arquivos_gerados: list[Path] = []

    tabelas = getattr(documento, "tables", [])
    for i, tabela in enumerate(tabelas, start=1):
        try:
            df = tabela.export_to_dataframe()
        except Exception as erro:
            print(f"   [aviso] não foi possível ler a tabela {i}: {erro}")
            continue

        nome_base = f"{prefixo}_tabela_{i:02d}"
        caminho_csv = pasta_tabelas / f"{nome_base}.csv"
        df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        arquivos_gerados.append(caminho_csv)

        try:
            caminho_md = pasta_tabelas / f"{nome_base}.md"
            caminho_md.write_text(tabela.export_to_markdown(), encoding="utf-8")
            arquivos_gerados.append(caminho_md)
        except Exception:
            pass

    return arquivos_gerados


# =============================================================================
# 6. ORQUESTRAÇÃO (main)
# =============================================================================

def processar(config: dict, sumario: list[TrechoSumario], interativo: bool = True) -> None:
    pdf_entrada = Path(config["pdf_entrada"])
    pasta_saida = Path(config["pasta_saida"])
    nome_livro = config["nome_livro"]

    # --- Condição pelo nome do livro -------------------------------------
    if not checar_condicao_livro(nome_livro, LIVROS_PERMITIDOS):
        print(
            f"[BLOQUEADO] O livro '{nome_livro}' não está na lista de livros "
            "permitidos (LIVROS_PERMITIDOS). Nenhum processamento foi feito."
        )
        return

    if not pdf_entrada.exists():
        print(f"[ERRO] PDF de entrada não encontrado: {pdf_entrada}")
        return

    # --- Calcula páginas de fim e abre o loop de revisão -------------------
    calcular_paginas_fim(sumario, config.get("total_paginas_pdf"))
    revisar_sumario_interativo(sumario, interativo=interativo)

    pasta_saida.mkdir(parents=True, exist_ok=True)
    manifesto = []

    incluidos = [t for t in sumario if t.incluir]
    print(f"\n=== Processando {len(incluidos)} de {len(sumario)} trechos ===\n")

    for item in incluidos:
        print(f"-> {item.titulo} (páginas {item.pagina_inicio}-{item.pagina_fim})")

        pasta_item = pasta_saida / item.slug()
        pdf_parcial = pasta_item / f"{item.slug()}.pdf"

        # 1) separar as páginas correspondentes
        separar_pdf(pdf_entrada, item.pagina_inicio, item.pagina_fim, pdf_parcial)

        # 2) converter com docling
        try:
            documento, markdown = converter_com_docling(pdf_parcial)
        except Exception as erro:
            print(f"   [ERRO] falha ao converter com Docling: {erro}")
            continue

        caminho_md = pasta_item / f"{item.slug()}.md"
        caminho_md.write_text(markdown, encoding="utf-8")

        # 3) extrair e salvar tabelas
        pasta_tabelas = pasta_item / "tabelas"
        arquivos_tabelas = salvar_tabelas(documento, pasta_tabelas, item.slug())

        manifesto.append(
            {
                "titulo": item.titulo,
                "nivel": item.nivel,
                "capitulo_pai": item.capitulo_pai,
                "pagina_inicio": item.pagina_inicio,
                "pagina_fim": item.pagina_fim,
                "pdf_parcial": str(pdf_parcial),
                "markdown": str(caminho_md),
                "qtd_tabelas": len(arquivos_tabelas) // 2,  # csv + md por tabela
            }
        )
        print(f"   ok -> {caminho_md} ({len(arquivos_tabelas)//2} tabela(s))")

    caminho_manifesto = pasta_saida / "manifesto.json"
    caminho_manifesto.write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nManifesto salvo em: {caminho_manifesto}")


if __name__ == "__main__":
    # Passe --auto para pular o loop interativo e usar o sumário como está.
    modo_interativo = "--auto" not in sys.argv
    processar(CONFIG, SUMARIO, interativo=modo_interativo)
