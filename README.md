\# FinPilot AI



FinPilot AI é um agente inteligente de análise financeira desenvolvido em Python, Gemini e Streamlit.



O projeto combina cálculos financeiros determinísticos com Inteligência Artificial Generativa para ajudar usuários a compreender seus gastos e simular decisões financeiras de forma explicável.



\---



\## Problema



Muitas pessoas conhecem o saldo da conta, mas não conseguem responder perguntas simples como:



\- Posso realizar determinada compra?

\- Quanto do meu dinheiro já está comprometido?

\- Em qual categoria estou gastando mais?

\- Quanto ainda posso gastar mantendo uma margem de segurança?



O FinPilot AI foi criado para transformar dados financeiros em respostas simples e contextualizadas.



\---



\## Principais funcionalidades



\### Dashboard financeiro



O sistema calcula automaticamente:



\- receitas totais;

\- despesas totais;

\- saldo;

\- despesas por categoria;

\- reserva financeira;

\- limite seguro para gastos.



\### Safe Spend



O usuário pode simular uma compra antes de realizá-la.



Exemplo:



```text

Posso gastar R$ 2.000 hoje?

O sistema calcula:

saldo atual;
saldo após a compra;
percentual do limite seguro utilizado;
limite restante;
valor excedente;
classificação de risco.

As classificações são:

Baixo
Moderado
Alto
FinPilot AI Assistant

O projeto utiliza Google Gemini para transformar resultados financeiros em explicações em linguagem natural.

Exemplos de perguntas:

Qual categoria está consumindo mais meu dinheiro?

Quanto gastei com alimentação?

Posso gastar R$ 700 em um tênis?

Posso gastar R$ 2.000 hoje?

Os cálculos não são realizados pelo modelo de IA.

Eles são executados por funções Python determinísticas e os resultados são enviados ao modelo apenas para interpretação.

Arquitetura
Usuário
   |
   v
Streamlit
   |
   v
Financial Agent
   |
   +------------------------+
   |                        |
   v                        v
Financial Tools        Gemini
   |
   v
Financial Metrics
   |
   v
Pandas
   |
   v
CSV de transações
Fluxo de decisão

Exemplo:

Usuário:
"Posso gastar R$ 2.000 hoje?"

        |
        v

Financial Agent identifica
uma intenção de compra

        |
        v

calculate_purchase_impact(2000)

        |
        v

Python calcula:

Saldo atual
Saldo após compra
Limite seguro
Uso do limite
Risco

        |
        v

Gemini explica o resultado
em linguagem natural
Tecnologias
Python
Pandas
NumPy
Streamlit
Google Gemini
Google GenAI SDK
python-dotenv
Git
GitHub
Estrutura do projeto
finpilot-ai-agent/
|
|-- app/
|   |
|   |-- agents/
|   |   `-- financial_agent.py
|   |
|   |-- services/
|   |   `-- gemini_service.py
|   |
|   `-- tools/
|       |-- financial_metrics.py
|       `-- financial_tools.py
|
|-- data/
|   `-- sample_transactions.csv
|
|-- main.py
|-- streamlit_app.py
|-- requirements.txt
|-- README.md
`-- .gitignore
Segurança

A chave da API do Gemini é armazenada localmente utilizando um arquivo:

.env

Esse arquivo está incluído no .gitignore e não é enviado para o GitHub.

Exemplo:

GEMINI_API_KEY=sua_chave
Como executar

Clone o projeto:

git clone https://github.com/stheffrancisca/finpilot-ai-agent.git

Entre na pasta:

cd finpilot-ai-agent

Crie o ambiente virtual:

python -m venv .venv

Ative o ambiente no Windows:

.venv\Scripts\Activate.ps1

Instale as dependências:

pip install -r requirements.txt

Crie o arquivo .env:

GEMINI_API_KEY=sua_chave

Execute:

streamlit run streamlit_app.py

A aplicação estará disponível em:

http://localhost:8501
Dados

Os dados utilizados neste projeto são fictícios e foram criados exclusivamente para demonstração.

Nenhuma informação bancária real é utilizada.

Roadmap

Próximas evoluções planejadas:

Function Calling automático com Gemini
detecção de despesas recorrentes;
comparação entre meses;
previsão de fluxo de caixa;
detecção de gastos anormais;
alertas financeiros;
upload de extratos;
RAG para educação financeira;
testes automatizados;
deploy online.
Objetivo do projeto

Este projeto foi desenvolvido como estudo aplicado de:

Inteligência Artificial Generativa;
agentes de IA;
análise financeira;
automação;
arquitetura baseada em ferramentas;
explicabilidade em sistemas de IA.
Autor

Sthefani Francisca

Projeto desenvolvido como parte dos estudos em Dados, Inteligência Artificial e aplicação de agentes de IA no contexto financeiro.

