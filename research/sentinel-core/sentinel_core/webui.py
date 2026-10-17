"""Interface visual original e local do Sentinel Atlas. Nenhum recurso remoto."""
DOCUMENT = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel Atlas • Audit Terminal</title>
<style>
:root{color-scheme:dark;--bg:#080b11;--surface:#10151f;--border:#242c38;--text:#f0f4fb;--muted:#8793a7;--teal:#62e6c6;--amber:#ebc079;--red:#f68189;--blue:#86a9ff}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text)}
button,select{font:inherit}button{cursor:pointer}button:focus-visible,select:focus-visible{outline:2px solid var(--teal);outline-offset:3px}a{color:var(--teal)}
.wrap{display:grid;grid-template-columns:242px minmax(0,1fr);min-height:100vh}
aside{border-right:1px solid var(--border);background:#0c1018;padding:26px 16px;display:flex;flex-direction:column;gap:30px}
.brand{display:flex;align-items:center;gap:12px;font-weight:850;font-size:18px;letter-spacing:-.8px;margin-left:9px}.logo{width:33px;height:33px;border-radius:9px;background:linear-gradient(145deg,#73ffe1,#177962);color:#07140f;display:grid;place-items:center;font-size:18px}
.eyebrow{color:var(--muted);font-size:10px;letter-spacing:1.8px;text-transform:uppercase;font-weight:800;margin:0 0 12px}
nav{display:grid;gap:8px}nav button{background:none;color:#9aa6b8;border:1px solid transparent;border-radius:10px;text-align:left;padding:12px 15px;display:flex;align-items:center;gap:10px}
nav button.active{background:#17322f;color:var(--teal);border-color:#27514a;font-weight:700}
nav button:hover{background:#18212d;color:#fff}.sidebarFoot{margin-top:auto;background:var(--surface);border:1px solid var(--border);padding:16px;border-radius:12px;color:var(--muted);font-size:12px}
.dot{display:inline-block;width:7px;height:7px;background:var(--teal);border-radius:50%;margin-right:5px}
main{padding:28px 38px 70px;max-width:1600px;width:100%}
header{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:28px}
.small{font-size:12px;color:var(--muted)}h1{font-size:29px;margin:4px 0 7px;line-height:1.2;letter-spacing:-.8px}h2{font-size:17px;letter-spacing:-.3px;margin:0}p{margin:0;color:var(--muted)}
.status{border:1px solid #584b32;background:#282214;color:#f2cb82;border-radius:100px;padding:7px 13px;font-size:11px;font-weight:800;letter-spacing:.6px}
.banner{border:1px solid #36584f;border-radius:13px;background:linear-gradient(90deg,#122824,#111820);padding:15px 18px;color:#a2d6c9;font-size:13px;margin-bottom:26px}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:20px}
.card,.panel{border:1px solid var(--border);border-radius:14px;background:var(--surface);padding:19px}
.metricLabel{color:var(--muted);font-size:12px}.metricValue{font-weight:750;letter-spacing:-1px;font-size:25px;margin-top:9px;display:block}
.green{color:var(--teal)}.orange{color:var(--amber)}.red{color:var(--red)}
.grid2{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(290px,1fr);gap:17px}.stack{display:grid;gap:17px}
.panelHead{display:flex;justify-content:space-between;gap:15px;align-items:center;margin-bottom:19px;flex-wrap:wrap}
select,.btn{background:#1a2330;border:1px solid #303e4e;color:#f4f7ff;border-radius:8px;padding:9px 12px}
.btn{font-size:12px}.btn:hover{background:#293344}
.chart{height:300px;display:flex;justify-content:center;align-items:center;color:var(--muted);font-size:13px}
svg{max-width:100%;height:100%}.gridlines line{stroke:#2a3440;stroke-dasharray:3 5}
.tableWrap{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}th{text-align:left;font-weight:600;color:var(--muted);font-size:11px;letter-spacing:.7px;text-transform:uppercase}td,th{padding:13px 10px;border-bottom:1px solid var(--border)}td{font-variant-numeric:tabular-nums}
.meta{font-size:11px;color:var(--muted)}.empty{background:#141e29;border:1px dashed #394454;color:#91a2b6;border-radius:10px;padding:27px;text-align:center;line-height:1.8}
.infoGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.info{background:#151d29;padding:16px;border-radius:9px}
.view{display:none}.view.active{display:block}.pill{font-size:10px;border-radius:20px;padding:4px 8px;background:#193b31;color:#8bf0d5;font-weight:800}.warning{color:#f7c784}
.flex{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
@media(max-width:1050px){.grid2{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:740px){.wrap{grid-template-columns:1fr}aside{padding:13px 18px;border-right:0;border-bottom:1px solid var(--border);gap:10px}.brand{margin-left:0}nav{display:flex;overflow-x:auto}nav button{white-space:nowrap;padding:8px 10px}.sidebarFoot{display:none}main{padding:23px 17px 60px}h1{font-size:24px}.metrics{gap:9px}.metricValue{font-size:21px}.card,.panel{padding:14px}.chart{height:235px}}
</style>
</head>
<body><div class="wrap">
<aside><div class="brand"><span class="logo">◈</span><span>SENTINEL <span class="green">ATLAS</span></span></div>
<div><div class="eyebrow">Research workspace</div><nav>
<button data-view="overview" class="active">◫ &nbsp; Visão geral</button>
<button data-view="research">⌗ &nbsp; Dados históricos</button>
<button data-view="signals">◎ &nbsp; Alertas simulados</button>
<button data-view="reports">▣ &nbsp; Backtests &amp; relatórios</button>
<button data-view="method">◇ &nbsp; Metodologia</button>
</nav></div>
<div class="sidebarFoot"><div><span class="dot"></span> Auditoria offline</div><p style="margin-top:9px;font-size:12px">Dados locais. Nenhuma ordem, chave de exchange ou execução automática.</p><div style="margin-top:12px" class="meta">Core v0.4 • Research</div></div></aside>
<main><header><div><div class="eyebrow">INTELLIGENCE / AUDIT</div><h1 id="pageTitle">Visão geral do mercado</h1><p id="pageSubtitle">Monitor de pesquisa independente com dados locais verificáveis.</p></div><span class="status">● PAPER ONLY · OFFLINE</span></header>
<div class="banner">◈ &nbsp; <strong>Ambiente experimental.</strong> Sem cotações em tempo real, sem resultados de rentabilidade comprovada. Séries importadas exigem auditoria da origem antes de uso financeiro.</div>
<section class="view active" id="overview">
<div class="metrics">
<div class="card"><div class="metricLabel">Mercados no SQLite</div><strong id="metricMarket" class="metricValue">—</strong><span class="meta">Ativos únicos</span></div>
<div class="card"><div class="metricLabel">Candles locais</div><strong id="metricBars" class="metricValue">—</strong><span class="meta">Todas as séries</span></div>
<div class="card"><div class="metricLabel">Relatórios disponíveis</div><strong id="metricReports" class="metricValue">—</strong><span class="meta">Arquivos JSON locais</span></div>
<div class="card"><div class="metricLabel">Execução</div><strong class="metricValue green">Desligada</strong><span class="meta">Leitura apenas</span></div>
</div>
<div class="grid2"><div class="panel"><div class="panelHead"><div><h2>Histórico de preços</h2><p class="small">OHLCV local — último candle importado</p></div><div class="flex"><select id="symbol" aria-label="Ativo"></select><select id="timeframe" aria-label="Intervalo"><option>15m</option><option>1h</option><option>4h</option><option>1d</option><option>5m</option><option>1m</option></select></div></div>
<div class="chart" id="chart"><div class="empty">Importe candles para visualizar o histórico. Não exibimos preços fictícios.</div></div><div class="meta" id="chartInfo"></div></div>
<div class="stack">
<div class="panel"><div class="panelHead"><h2>Integridade da pesquisa</h2><span class="pill">READ ONLY</span></div><div class="infoGrid"><div class="info"><div class="meta">Fonte</div><strong>SQLite local</strong></div><div class="info"><div class="meta">Cotações live</div><strong class="warning">Não conectadas</strong></div><div class="info"><div class="meta">Sinais automáticos</div><strong>Desabilitados</strong></div><div class="info"><div class="meta">Operações reais</div><strong>0</strong></div></div></div>
<div class="panel"><div class="panelHead"><h2>Próxima validação</h2></div><p>Importar histórico autorizado de Binance Futures ou CSV, registrar checksums e executar avaliação walk-forward. Comparar apenas resultados com mesma exposição, custos e período.</p><div style="margin-top:15px"><button class="btn" data-target="method">Ver metodologia →</button></div></div>
</div></div></section>
<section class="view" id="research"><div class="panel"><div class="panelHead"><div><h2>Conjuntos de dados registrados</h2><p class="small">Cobertura registrada no arquivo local — autenticidade externa não comprovada.</p></div><button id="refresh" class="btn">Atualizar</button></div>
<div class="tableWrap"><table><thead><tr><th>Ativo</th><th>Intervalo</th><th>Candles</th><th>Primeiro candle UTC</th><th>Último candle UTC</th><th>Origem</th></tr></thead><tbody id="marketTable"></tbody></table></div><div class="meta" id="marketInfo"></div></div></section>
<section class="view" id="signals">
<div class="panel"><div class="panelHead"><div><h2>Ciclo de alertas em duas etapas</h2><p class="small">Eventos históricos PRELIMINARY → CONFIRMED / INVALIDATED / EXPIRED. Nenhuma publicação ao vivo.</p></div><button class="btn" id="refreshSignals">Atualizar</button></div>
<div class="tableWrap"><table><thead><tr><th>Momento UTC</th><th>Ativo</th><th>Estado</th><th>Direção</th><th>Preço observado</th><th>RSI14</th><th>Histórico</th></tr></thead><tbody id="signalsTable"></tbody></table></div><div class="meta" id="signalsInfo"></div></div></section>
<section class="view" id="reports"><div class="grid2"><div class="panel"><div class="panelHead"><div><h2>Relatórios de pesquisa</h2><p class="small">Arquivos JSON produzidos por avaliação local.</p></div><button id="refreshReports" class="btn">Atualizar</button></div><div id="reportList" class="stack"></div></div>
<div class="panel"><div class="panelHead"><h2>Detalhes do relatório</h2><span class="pill">RESEARCH</span></div><div id="reportDetail" class="empty">Selecione um arquivo de relatório para visualizar as métricas, os períodos de teste e as ressalvas.</div></div></div></section>
<section class="view" id="method"><div class="panel"><div class="panelHead"><h2>Regras de interpretação</h2></div>
<div class="stack">
<div><strong>01 • Verificabilidade</strong><p>Nunca substituir dados faltantes por candles inventados. Verificar UTC, intervalos, cobertura, duplicidades, checksums e proveniência do CSV.</p></div>
<div><strong>02 • Teste temporal</strong><p>Um sinal só pode depender de velas fechadas. O backtest executa na vela seguinte e dá prioridade ao stop se ambos os limites forem atingidos intrabar.</p></div>
<div><strong>03 • Custo realista</strong><p>Resultado de pesquisa deve declarar taxa, slippage, funding, tamanho da posição e modelo de execução. Dados históricos OHLCV não reproduzem o livro de ofertas.</p></div>
<div><strong>04 • Fora da amostra</strong><p>As janelas OOS não se sobrepõem. Após observar OOS e ajustar estratégia, ele deixa de ser totalmente intocado; separar períodos futuros novamente.</p></div>
<div><strong>05 • Limites de segurança</strong><p>Este projeto não oferece ordens reais, não solicita chaves API, não promete lucros e deve executar somente em 127.0.0.1, jamais em servidor público.</p></div>
</div></div></section>
<footer class="meta" style="margin-top:28px">Sentinel Atlas · Software original de pesquisa · Sem aconselhamento financeiro</footer>
</main></div>
<script>
const state={markets:[],reports:[],view:"overview"};
const $=id=>document.getElementById(id);
const fmt=t=>t===null||t===undefined?"—":new Date(Number(t)).toLocaleString("pt-BR",{timeZone:"UTC",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})+" UTC";
const integer=n=>Number(n||0).toLocaleString("pt-BR");
const numeric=n=>typeof n==="number"&&Number.isFinite(n)?n.toLocaleString("pt-BR",{maximumFractionDigits:4}):"—";
async function api(path){const r=await fetch(path,{cache:"no-store"});const x=await r.json();if(!r.ok)throw Error(x.details||x.error||"Falha");return x}
function element(tag,text,cls){const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x}
function empty(node,msg){node.replaceChildren(element("div",msg,"empty"))}
function activate(view){
 state.view=view;document.querySelectorAll(".view").forEach(x=>x.classList.toggle("active",x.id===view));
 document.querySelectorAll("nav button").forEach(x=>x.classList.toggle("active",x.dataset.view===view));
 const titles={overview:["Visão geral do mercado","Pesquisa independente, somente dados locais."],research:["Qualidade e proveniência","Séries armazenadas com rastreabilidade."],signals:["Alertas simulados","Ciclos históricos: antecipação, confirmação e invalidação."],reports:["Backtesting & estratégias","Resultados experimentais auditáveis."],method:["Metodologia e segurança","As regras que tornam cada resultado verificável."]};
 $("pageTitle").textContent=titles[view][0];$("pageSubtitle").textContent=titles[view][1];
}
document.querySelectorAll("nav button").forEach(b=>b.addEventListener("click",()=>activate(b.dataset.view)));
document.querySelectorAll("[data-target]").forEach(b=>b.addEventListener("click",()=>activate(b.dataset.target)));
async function loadMarkets(){
 try{const d=await api("/api/markets");state.markets=d.markets||[];
 $("metricMarket").textContent=integer(new Set(state.markets.map(x=>x.symbol)).size);
 $("metricBars").textContent=integer(state.markets.reduce((a,b)=>a+b.candles,0));
 const unique=[...new Set(state.markets.map(x=>x.symbol))];
 const symbol=$("symbol"),last=symbol.value;symbol.replaceChildren();
 if(!unique.length)symbol.append(element("option","SEM DADOS"));
 unique.forEach(v=>{let x=element("option",v);x.value=v;symbol.append(x)});
 if(unique.includes(last))symbol.value=last;
 const body=$("marketTable");body.replaceChildren();
 if(!state.markets.length){const tr=element("tr");const td=element("td","Nenhuma série disponível — importar dados com a CLI");td.colSpan=6;tr.append(td);body.append(tr)}
 state.markets.forEach(m=>{const tr=element("tr");[m.symbol,m.interval,integer(m.candles),fmt(m.first_open_ms),fmt(m.last_open_ms),"Local não autenticado"].forEach(v=>tr.append(element("td",v)));body.append(tr)});
 $("marketInfo").textContent=state.markets.length+" série(s) em armazenamento local. Nenhuma garantia de origem externa.";
 await loadChart();
 }catch(e){$("metricBars").textContent="Erro";empty($("chart"),"Não foi possível carregar SQLite: "+e.message);$("marketInfo").textContent=e.message}
}
function plot(data){
 const w=900,h=300,p=27;const nums=data.map(x=>Number(x.close)).filter(Number.isFinite);
 if(nums.length<2)return null;
 const low=Math.min(...nums),high=Math.max(...nums),delta=high-low||1;
 const pts=nums.map((v,i)=>{const x=p+i*(w-2*p)/(nums.length-1);const y=h-p-(v-low)/delta*(h-2*p);return [x,y]});
 const line=pts.map(q=>q.map(n=>n.toFixed(2)).join(",")).join(" ");
 const polygon=p+","+ (h-p)+" "+line+" "+(w-p)+","+(h-p);
 const grid=[.25,.5,.75].map(k=>'<line x1="'+p+'" y1="'+(p+(h-2*p)*k)+'" x2="'+(w-p)+'" y2="'+(p+(h-2*p)*k)+'"/>').join("");
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 300" preserveAspectRatio="none" role="img" aria-label="Gráfico de fechamento com dados históricos locais"><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#62e6c6" stop-opacity=".20"/><stop offset="1" stop-color="#62e6c6" stop-opacity="0"/></linearGradient></defs><g class="gridlines">'+grid+'</g><polygon points="'+polygon+'" fill="url(#fill)"/><polyline points="'+line+'" fill="none" stroke="#62e6c6" stroke-width="2.4" vector-effect="non-scaling-stroke"/></svg>';
}
async function loadChart(){
 if(!state.markets.length){empty($("chart"),"Nenhum dado importado. A interface não simula cotações.");$("chartInfo").textContent="";return}
 const symbol=$("symbol").value,interval=$("timeframe").value;
 try{const d=await api("/api/candles?symbol="+encodeURIComponent(symbol)+"&interval="+interval+"&limit=350");
 if(!d.candles?.length){empty($("chart"),"Não há histórico "+interval+" para "+symbol+".");$("chartInfo").textContent="";return}
 const chart=plot(d.candles);if(!chart){empty($("chart"),"Dados insuficientes");return}
 $("chart").innerHTML=chart;
 const last=d.candles[d.candles.length-1];
 $("chartInfo").textContent=symbol+" • "+interval+" • "+d.candles.length+" candles • último fechamento "+numeric(last.close)+" • "+fmt(last.close_time)+" • origem não auditada";
 }catch(e){empty($("chart"),"Falha ao consultar candles: "+e.message)}
}
async function loadSignals(){
 const target=$("signalsTable");target.replaceChildren();
 try{
  const x=await api("/api/alerts");const alerts=x.alerts||[];
  $("signalsInfo").textContent=alerts.length+" alerta(s) no arquivo local runs/alerts.json; esses eventos NÃO são sinais em tempo real.";
  if(!alerts.length){
   const tr=element("tr"),td=element("td","Sem eventos. Gere o replay offline para visualizar os estágios.");
   td.colSpan=7;tr.append(td);target.append(tr);return;
  }
  alerts.slice().reverse().forEach(a=>{
   const tr=element("tr");
   [fmt(a.at_ms),a.symbol||"—",a.event_type||"—",a.side||"—",
    numeric(a.observed_price),numeric(a.rsi14),
    a.preliminary_seen?"Com antecipação":"Sem antecipação prévia"].forEach(t=>tr.append(element("td",t)));
   target.append(tr);
  });
 }catch(e){$("signalsInfo").textContent="Falha na leitura local: "+e.message}
}
async function loadReports(){
 const list=$("reportList");try{const d=await api("/api/reports");state.reports=d.reports||[];
 $("metricReports").textContent=integer(state.reports.length);
 list.replaceChildren();
 if(!state.reports.length){empty(list,"Nenhum JSON de backtest na pasta de relatórios.");return}
 state.reports.forEach(rep=>{const btn=element("button",rep.name+" · "+integer(rep.bytes)+" bytes","btn");btn.style.textAlign="left";btn.addEventListener("click",()=>loadReport(rep.name));list.append(btn)});
 }catch(e){empty(list,"Falha na listagem: "+e.message);$("metricReports").textContent="Erro"}
}
async function loadReport(name){
 const target=$("reportDetail");empty(target,"Lendo e verificando relatório...");
 try{const x=await api("/api/report?name="+encodeURIComponent(name));const r=x.report;
 target.replaceChildren();
 const head=element("div");head.append(element("div",name,"eyebrow"));
 const report=r.evaluation||r;
 const wf=report.walk_forward;
 let blocks=[];
 if(wf?.results)blocks=wf.results.map(f=>({
  label:"Janela "+f.fold,returnPct:f.test?.return_pct,trades:f.test?.trades,
  dd:f.test?.max_conservative_intrabar_drawdown_pct,from:f.test_start_ms,to:f.test_end_exclusive_ms
 }));
 else if(report.test)blocks=[{label:"Período de teste",returnPct:report.test.return_pct,trades:report.test.trades,dd:report.test.max_conservative_intrabar_drawdown_pct}];
 else if(report.return_pct!==undefined)blocks=[{label:"Simulação",returnPct:report.return_pct,trades:report.trades,dd:report.max_conservative_intrabar_drawdown_pct}];
 target.append(head,element("p","Números relatados pelo arquivo; proveniência e execução NÃO verificadas.","warning"));
 if(!blocks.length){target.append(element("div","Estrutura não reconhecida ou sem métricas. Consulte o arquivo JSON original.","empty"));return}
 blocks.forEach(b=>{const card=element("div",undefined,"info");card.style.marginTop="12px";card.append(element("strong",b.label));
 const p=element("p","Retorno: "+numeric(b.returnPct)+"% | Trades: "+integer(b.trades)+" | DD estimado: "+numeric(b.dd)+"%","small");card.append(p);
 if(b.from)card.append(element("div",fmt(b.from)+" → "+fmt(b.to),"meta"));target.append(card)});
 }catch(e){empty(target,"Não foi possível abrir o relatório: "+e.message)}
}
$("symbol").addEventListener("change",loadChart);$("timeframe").addEventListener("change",loadChart);
$("refresh").addEventListener("click",loadMarkets);$("refreshReports").addEventListener("click",loadReports);$("refreshSignals").addEventListener("click",loadSignals);
Promise.all([loadMarkets(),loadReports(),loadSignals()]);
</script>
</body></html>"""
