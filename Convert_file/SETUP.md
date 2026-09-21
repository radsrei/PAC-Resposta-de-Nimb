```bash

cd Convert_file
python -m venv .venv
# Windows
 .venv\Scripts\activate

pip install -U pip
cd ..
pip install -r requirements.txt

```

```bash
#sair da Venv
deactivate  
```

```bash
#Convert MD
pip install markitdown[pdf] langchain-text-splitters
python convert_file.py
```

```bash
#Convert HTML
pip install pymupdf beautifulsoup4 langchain-text-splitters
python convert_html.py
```

```bash
#Convert usando docling
pip install docling # Já existe no Requirements.txt
python convert_html_docling.py
```

```bash
pip install pymupdf # Já existe no Requirements.txt
python convert_xml.py  
```