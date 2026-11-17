# Atualização diária do Portal de Taxas de Renda Fixa

Roteiro para o Claude atualizar o portal (https://aateixeiraana.github.io/portal-taxas/), gerar os PDFs e enviar à Ana.
Tudo o que é preciso está nesta pasta `ferramentas/`.

## Regras que a Ana definiu

- **Emissão Bancária**: só mercado primário (filtro "Primário" ligado).
- **Crédito Privado, Letras Fin./LIG e Títulos Públicos**: todos os ativos.
- Taxas sem nome de nível para o cliente: **Taxa 1 = mínima, Taxa 2 = média, Taxa 3 = máxima**. Os PDFs dizem só "TAXA" e o arquivo leva `_taxa_1`, `_taxa_2` ou `_taxa_3`.
- Destaques: top 5 emissores por prazo, de 6 meses a 5 anos, ordenados pelo Gross Up da XP.
- PDF completo ("Diário de Renda Fixa"): por indexador, lista de Crédito Privado e LF, depois resumo da Emissão Bancária; Pré-Fixado com todas as categorias; Títulos Públicos no fim; sem destaques; com a coluna Aplicação mínima (P.U × quantidade mínima).
- Sem marca de empresa nos materiais. Português, sem travessão.

## 1. Preparar a sessão

```bash
git clone https://github.com/aateixeiraana/portal-taxas /home/claude/portal-taxas
cd /home/claude/portal-taxas/ferramentas
pip install --break-system-packages playwright numpy pillow reportlab >/dev/null 2>&1 || true
python3 -m playwright install chromium >/dev/null 2>&1 || true
```

## 2. Extrair do Hub XP (Claude in Chrome, no Chrome da Ana)

Abra uma aba nova em `https://hub.xpi.com.br/new/renda-fixa/` (a Ana já está logada). Clique nas abas pela tela; mudar só o endereço não troca a tabela.
Cole o conteúdo de `extrair.js` uma vez com a ferramenta de JavaScript.

Em cada aba, abra o seletor de colunas (ícone de colunas à direita da busca de ativo; limite de 11 colunas contando "Ativos"), deixe marcadas exatamente estas e clique em Aplicar:

| Aba | Colunas | Chave |
|---|---|---|
| Emissão Bancária (clique em **Primário** antes) | Vencimento, Liquidez, Taxa Mín., Taxa Max., Gross Up Mín., Gross Up Max., P.U, Qtd. min, Rating, Risco | `eb` |
| Crédito Privado | Vencimento, Taxa Mín., Taxa Max., Gross Up Mín., Gross Up Max., P.U, Qtd. min, Rating, Risco, Tipo de produto | `cp` |
| Letras Fin./LIG | as mesmas do Crédito Privado | `lf` |
| Títulos Públicos | Vencimento, Taxa Mín., Taxa Max., P.U, Qtd. min, Risco | `tp` |

Depois, em cada aba, rode `__coletar('eb')` (ou `cp`, `lf`, `tp`) uma vez por página, esperando uns 2 segundos entre as chamadas (uma chamada por vez, com `await new Promise(r=>setTimeout(r,1500)); __coletar('cp')`), até o retorno dizer **FIM**. Se uma chamada falhar na extensão, confira a página atual e siga; a função não duplica linhas.

Atenção: depois do fechamento do mercado a XP mostra poucos ativos (no Crédito Privado cai de ~540 para ~20). Se alguma aba vier muito menor que o normal, avise a Ana em vez de publicar dados incompletos.

## 3. Trazer os dados para a sessão

Os retornos da ferramenta de JavaScript são cortados em ~1.000 caracteres, então os dados vêm por imagem:

1. `await __empacotar()` mostra quantas linhas por aba e quantos quadros.
2. Para cada quadro N: `__quadro(N)`, depois um **zoom** da região `[0, 0, 1320, 760]` com `scale: 1` e `save_to_disk: true`, e `python3 decode_frames.py <png salvo> /home/claude/xfer`.
3. `__quadro(-1)` remove o desenho da tela.
4. Junte: `cat /home/claude/xfer/frame*.bin > /home/claude/xfer/dados.json.gz` (frames em ordem 0,1,2...) e confira com `python3 -c "import gzip,json;print(list(json.loads(gzip.decompress(open('/home/claude/xfer/dados.json.gz','rb').read()))))"`.
5. Descompacte para `/home/claude/xfer/dados.json`.

## 4. Gerar o portal e os PDFs

```bash
cd /home/claude/portal-taxas/ferramentas
python3 build_portal.py /home/claude/xfer/dados.json DD/MM/AAAA HH:MM      # grava ../index.html
mkdir -p /home/claude/envio && python3 gerar_pdfs.py /home/claude/portal-taxas/index.html /home/claude/envio
```

Confira um PDF de cada (abra a página 1 e uma de destaques). Depois publique:

```bash
cd /home/claude/portal-taxas && git add -A && git commit -m "Ofertas de DD/MM/AAAA" && git -c push.negotiate=true push
```

Se o push for recusado por falta de acesso, siga com os PDFs e avise a Ana.

## 5. Enviar no WhatsApp Web

Abra `https://web.whatsapp.com/` numa aba nova, busque **Ana Teixeira 306315** e abra a conversa "(você)".

Anexar PDFs (o input de arquivo que aparece sozinho aceita só imagens; é preciso o de **Documento**):

1. Rode no WhatsApp, com a ferramenta de JavaScript, para o seletor nativo não abrir:
   `const o=HTMLInputElement.prototype.click; HTMLInputElement.prototype.click=function(){ if(this.type==='file'){ if(!this.isConnected){this.style.display='none'; document.body.appendChild(this);} return; } return o.call(this); }`
2. Clique no "+" (Anexar) e depois no item de menu **Documento** (pelo ref do `find`).
3. Use `find` para achar o `file-input` novo (o que não aceita só `image/*`) e envie os 6 PDFs para ele com a ferramenta de upload.
4. Clique no botão **"Enviar 6 itens selecionados"** pelo ref (não por coordenada).
5. Confira as últimas linhas: `[...document.querySelectorAll('#main [role=row]')].slice(-7).map(r=>r.innerText.slice(0,60))`.

Mande o texto como mensagem separada (digite na caixa e clique em enviar), por exemplo:

> Esse relatório foi gerado por IA
>
> Taxas de Renda Fixa · DD/MM/AAAA
>
> Seguem os arquivos de hoje, em Taxa 1 mínima, 2 média e 3 máxima:
>
> • Diário de Renda Fixa: Crédito Privado, LF e Títulos Públicos, com o resumo da Emissão Bancária por emissor e prazo
>
> • Destaques: os 5 melhores emissores por prazo, de 6 meses a 5 anos, em Emissão Bancária e Crédito Privado
>
> Portal com filtros: https://aateixeiraana.github.io/portal-taxas/
>
> Taxas indicativas da XP, sujeitas a alteração conforme estoque e mercado. Antes de envio ao cliente faça uma rápida verificação nas taxas. Você pode usar o portal para enviar prints diretamente ao cliente.

Use exatamente esse texto, trocando só a data. Use Shift+Enter para quebrar linha. Se algo falhar duas vezes, pare e entregue os PDFs na conversa com a Ana.
