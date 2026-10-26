<#
.SYNOPSIS
    Setup completo do Respostas de Nimb no Windows: ambiente Python (.venv),
    backend, construtor do banco vetorial (Ollama ou sentence-transformers) e front.

.DESCRIPTION
    Pode ser executado de novo sem problema: só instala o que estiver faltando.
    Rode na raiz do projeto:

        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings local
        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings ollama -InstalarOllama
        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings nenhum -SemFrontend

.PARAMETER Embeddings
    Quem vai gerar os embeddings do banco vetorial:
      ollama  (padrão) servidor local do Ollama, sem PyTorch
      local   sentence-transformers dentro do Python (instala o PyTorch, ~2 GB)
      nenhum  não instala o construtor (só API e front)

.PARAMETER ModeloEmbeddings
    Modelo de embeddings a baixar no Ollama (padrão: bge-m3).

.PARAMETER InstalarOllama
    Instala o Ollama pelo winget se ele não estiver instalado.

.PARAMETER SemFrontend
    Não instala as dependências do front (npm ci).
#>
param(
    [ValidateSet("ollama", "local", "nenhum")]
    [string]$Embeddings = "ollama",
    [string]$ModeloEmbeddings = "bge-m3",
    [switch]$InstalarOllama,
    [switch]$SemFrontend
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Ok($text) { Write-Host "    $text" -ForegroundColor Green }
function Warn($text) { Write-Host "    AVISO: $text" -ForegroundColor Yellow }
function Fail($text) { Write-Host "    ERRO: $text" -ForegroundColor Red; exit 1 }
function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { Fail "falhou: $exe $($arguments -join ' ')" }
}

# ---------------------------------------------------------------------------
Step "Python"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { Fail "Python não encontrado. Instale o Python 3.14 (versão testada): winget install -e --id Python.Python.3.14" }
$version = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ([version]$version -lt [version]"3.12") { Fail "Python $version encontrado; é preciso 3.12 ou mais novo (testado: 3.14)." }
Ok "Python $version"

$longPaths = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -ErrorAction SilentlyContinue).LongPathsEnabled
if ($longPaths -ne 1) {
    Warn "Caminhos longos do Windows desativados. Se o pip falhar com 'No such file or directory', ative (PowerShell como administrador):"
    Write-Host '      New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force'
}

# ---------------------------------------------------------------------------
Step "Ambiente virtual (.venv)"
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Run python @("-m", "venv", ".venv")
    Ok "criado em .venv"
} else {
    Ok ".venv já existe"
}
Run $venvPython @("-m", "pip", "install", "-q", "-U", "pip")

Step "Dependências do backend"
Run $venvPython @("-m", "pip", "install", "-q", "-r", "backend\requirements.txt")
Ok "backend/requirements.txt"

# ---------------------------------------------------------------------------
if ($Embeddings -ne "nenhum") {
    Step "Construtor do banco vetorial ($Embeddings)"
    if ($Embeddings -eq "local") {
        Run $venvPython @("-m", "pip", "install", "-q", "-r", "backend\vector_builder\requirements-local.txt")
        Ok "sentence-transformers instalado (o modelo baixa na primeira construção)"
    } else {
        Run $venvPython @("-m", "pip", "install", "-q", "-r", "backend\vector_builder\requirements.txt")
        Ok "dependências do construtor instaladas"
    }
}

# A LLM do chat é o DeepSeek (API externa): o Ollama só gera os embeddings
if ($Embeddings -eq "ollama") {
    Step "Ollama"
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
        if ($InstalarOllama) {
            Run winget @("install", "-e", "--id", "Ollama.Ollama", "--accept-source-agreements", "--accept-package-agreements")
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        } else {
            Fail "Ollama não instalado. Instale (winget install -e --id Ollama.Ollama) ou rode o script com -InstalarOllama."
        }
    }
    $online = $false
    try { Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null; $online = $true } catch {}
    if (-not $online) {
        Ok "iniciando o servidor do Ollama..."
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
        for ($i = 0; $i -lt 20 -and -not $online; $i++) {
            Start-Sleep -Seconds 1
            try { Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null; $online = $true } catch {}
        }
        if (-not $online) { Fail "o servidor do Ollama não respondeu em http://localhost:11434" }
    }
    Ok "servidor no ar"
    Run ollama @("pull", $ModeloEmbeddings)
    Ok "modelo de embeddings: $ModeloEmbeddings"
}

# ---------------------------------------------------------------------------
Step "Configuração (backend/.env)"
$envFile = "backend\.env"
if (-not (Test-Path $envFile)) {
    $provider = if ($Embeddings -eq "local") { "sentence-transformers" } else { "ollama" }
    $model = if ($Embeddings -eq "ollama") { $ModeloEmbeddings } else { "" }
    $content = Get-Content "backend\.env.example" -Encoding UTF8
    $content = $content -replace "^EMBEDDING_PROVIDER=.*", "EMBEDDING_PROVIDER=$provider"
    $content = $content -replace "^EMBEDDING_MODEL=.*", "EMBEDDING_MODEL=$model"
    [IO.File]::WriteAllLines((Join-Path $Root $envFile), $content, (New-Object Text.UTF8Encoding $false))
    Ok "backend/.env criado a partir do .env.example (EMBEDDING_PROVIDER=$provider)"
} else {
    Ok "backend/.env já existe (não foi alterado). Confira EMBEDDING_PROVIDER e EMBEDDING_MODEL."
}
if (-not (Select-String -Path $envFile -Pattern "^GOOGLE_CLIENT_ID=\S" -Quiet)) {
    Warn "GOOGLE_CLIENT_ID vazio em backend/.env: sem ele ninguém entra no sistema (ver Setup-Front-Tela.md, seção 3.1)."
}

# ---------------------------------------------------------------------------
if (-not $SemFrontend) {
    Step "Frontend (frontend/V2 - front Studio)"
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Warn "Node.js não encontrado: instale o Node 20+ (winget install -e --id OpenJS.NodeJS.LTS) e rode o script de novo."
    } else {
        Push-Location "frontend\V2 - front Studio"
        try { Run npm @("ci", "--no-audit", "--no-fund") } finally { Pop-Location }
        Ok "npm ci concluído"
    }
}

# ---------------------------------------------------------------------------
Step "Pronto. Próximos passos"
Write-Host @"
    1. Ative o ambiente:      .venv\Scripts\activate
    2. Suba a API:            cd backend; python main.py
    3. Suba a tela (outro terminal):
                              cd "frontend\V2 - front Studio"; npm run dev
    4. Construa o banco de um livro (dentro de backend\):
                              python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro" --dry-run
                              python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro"
"@
