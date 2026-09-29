
# Iniciar main (versão ativa)
```bash
cd docs/nimb_prototipo/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py        # http://localhost:8000  (docs em /docs)
```

```bash
cd frontend/nimb-os-react
cp .env.example .env.local
```


## Dentro do .env
Apontar para o endereço

```bash
VITE_BACKEND_URL=http://localhost:8000
```

```bash
npm install
npm run dev            # http://localhost:3000
```

-- Enquanto VITE_BACKEND_URL estiver vazio, o app roda sozinho com respostas simuladas (útil para revisar a tela sem depender do backend); assim que a variável aponta pro FastAPI, ele passa a consumir os dados reais — sem precisar mexer no código. --
