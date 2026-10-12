"use strict";
const $ = id => document.getElementById(id);
let session = null, lastReply = "", busy = false, recorder = null, recordingStream = null, audioUrl = null;
const buttons = [...document.querySelectorAll("button")];

function notice(text, error = false) {
  $("notice").textContent = text;
  $("notice").classList.toggle("error", error);
  $("notice").hidden = !text;
}

async function api(path, options = {}) {
  const token = $("token").value.trim();
  if (!token) throw new Error("Informe o token de acesso do backend na seção Conexão.");
  const response = await fetch(path, {...options, headers: {...options.headers, Authorization: `Bearer ${token}`}});
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* erro sem JSON */ }
    if (detail && typeof detail === "object" && detail.message) {
      if (detail.session_id) { session = detail.session_id; $("session").value = session; }
      renderTools(detail.tool_results || []);
      throw new Error(detail.message);
    }
    const error = new Error(typeof detail === "string" ? detail : `A requisição falhou (HTTP ${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return response;
}

async function run(label, task) {
  if (busy) return;
  busy = true;
  buttons.forEach(button => button.disabled = true);
  notice(label);
  try { await task(); }
  catch (error) { notice(error.message || "Falha de conexão com o backend.", true); }
  finally { busy = false; buttons.forEach(button => button.disabled = false); }
}

function message(role, text) {
  $("empty")?.remove();
  const element = document.createElement("div");
  element.className = `message ${role === "user" ? "user" : "assistant"}`;
  const title = document.createElement("strong");
  title.textContent = role === "user" ? "VOCÊ" : "CRONOS";
  const content = document.createElement("span");
  content.textContent = text;
  element.append(title, content);
  $("messages").append(element);
  $("messages").scrollTop = $("messages").scrollHeight;
}

function clearAudio() {
  $("player").pause();
  $("player").removeAttribute("src");
  $("player").hidden = true;
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = null;
}

function renderTools(results, target = $("messages")) {
  const resolved = new Set(results.filter(result => result.status !== "pending_confirmation").map(result => result.approval_id));
  for (const result of results) {
    if (result.status === "pending_confirmation" && resolved.has(result.approval_id)) continue;
    const card = document.createElement("div"); card.className = "message";
    const title = document.createElement("strong"); title.textContent = `FERRAMENTA · ${result.name}`;
    const text = document.createElement("span");
    const labels = {completed: "Concluída", failed: "Falhou", pending_confirmation: "Aguardando sua confirmação", cancelled: "Cancelada", expired: "Confirmação expirada", resolved: "Confirmação já respondida"};
    text.textContent = (labels[result.status] || result.status) + (result.error ? `: ${result.error}` : "");
    card.append(title, text);
    if (result.status === "pending_confirmation") {
      const details = document.createElement("pre"); details.textContent = JSON.stringify(result.arguments, null, 2);
      card.append(details);
      const controls = document.createElement("div"); controls.className = "row";
      const confirm = document.createElement("button"); confirm.textContent = "Confirmar ação";
      const cancel = document.createElement("button"); cancel.textContent = "Cancelar"; cancel.className = "secondary";
      const resolve = accepted => {
        if (busy) return;
        run("Processando sua decisão…", async () => {
          const response = await (await api(`/tools/approvals/${result.approval_id}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({session_id: result.session_id || session, accepted})})).json();
          confirm.disabled = true; cancel.disabled = true;
          if (target === $("module-approvals")) showModuleOutput(response);
          text.textContent = (response.result?.status === "running" ? "Operação em andamento; consulte o resultado posteriormente" : labels[response.status]) + (response.error ? `: ${response.error}` : "");
          notice(response.status === "completed" ? "Solicitação atendida. Confira o resultado; uma operação em andamento ainda não terminou." : text.textContent, response.status === "failed");
        });
      };
      confirm.addEventListener("click", () => resolve(true)); cancel.addEventListener("click", () => resolve(false));
      controls.append(confirm, cancel); card.append(controls);
    }
    target.append(card);
  }
}

$("connect-form").addEventListener("submit", event => {
  event.preventDefault();
  pauseMonitor();
  run("Verificando conexão…", async () => {
    [...$("status").children].forEach((item, index) => { item.textContent = `${["Backend", "IA", "Voz", "Personalidade"][index]}: não verificado`; item.classList.remove("good"); });
    const result = await (await api("/status")).json();
    const values = [
      ["Backend: conectado", true],
      [`IA: ${result.provider}${!result.provider_configured ? " · falta configuração" : " · acesso ainda não testado"}`, result.provider_configured],
      [result.fish_configured ? "Voz: configurada · acesso ainda não testado" : "Voz: falta chave", result.fish_configured],
      [result.personality_available ? "Personalidade: disponível" : "Personalidade: arquivo ausente", result.personality_available]
    ];
    $("status").replaceChildren(...values.map(([text, good]) => {
      const item = document.createElement("span"); item.textContent = text; item.classList.toggle("good", good); return item;
    }));
    $("alert-voice").disabled = !result.fish_configured;
    if (!result.fish_configured) $("alert-voice").checked = false;
    startMonitor();
    await loadModules();
    openEmbeddedModule();
    notice("Backend conectado. Envie uma mensagem e teste o áudio para validar os provedores.");
  });
});

$("chat-form").addEventListener("submit", event => {
  event.preventDefault();
  const text = $("message").value.trim();
  if (!text) return;
  run("Cronos está respondendo…", async () => {
    const result = await (await api("/chat", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({message: text, session_id: session})})).json();
    session = result.session_id;
    $("session").value = session;
    message("user", text); message("assistant", result.reply);
    renderTools(result.tool_results || []);
    lastReply = result.reply;
    $("message").value = "";
    $("notes").replaceChildren();
    const notes = result.notes.length ? result.notes : ["Nenhum tema registrado nesta resposta."];
    notes.forEach((path, index) => {
      const item = document.createElement("li");
      item.textContent = result.topics[index] ? `${result.topics[index]} — ${path}` : path;
      $("notes").append(item);
    });
    notice(result.warnings?.length ? result.warnings.join("\n") : "Resposta recebida e conversa salva.", Boolean(result.warnings?.length));
  });
});

$("message").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault(); if (!busy) $("chat-form").requestSubmit();
  }
});

$("new-chat").addEventListener("click", () => {
  session = null; lastReply = "";
  $("session").value = ""; $("message").value = "";
  $("messages").replaceChildren(); $("notes").replaceChildren();
  $("speech-text").value = ""; clearAudio();
  notice("Nova conversa iniciada. O histórico anterior continua salvo no vault.");
  $("message").focus();
});

$("history").addEventListener("click", () => run("Carregando histórico…", async () => {
  const id = $("session").value.trim();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) throw new Error("Informe um ID de conversa válido.");
  const result = await (await api(`/conversations/${encodeURIComponent(id)}`)).json();
  if (!result.messages.length) throw new Error("Não há histórico salvo para esse ID.");
  session = id; lastReply = "";
  $("messages").replaceChildren(); $("notes").replaceChildren();
  clearAudio();
  for (const item of result.messages) {
    message(item.role, item.content);
    if (item.role === "assistant") lastReply = item.content;
  }
  renderTools(result.tool_results || []);
  notice("Histórico carregado. As próximas mensagens continuarão esta conversa.");
}));

$("use-reply").addEventListener("click", () => {
  if (!lastReply) return notice("Envie uma mensagem ou carregue uma conversa primeiro.", true);
  if (lastReply.length > 50000) return notice("A resposta supera 50.000 caracteres. Divida-a em trechos para gerar a voz.", true);
  $("speech-text").value = lastReply;
  notice("Resposta copiada para o teste de voz.");
});

$("speak").addEventListener("click", () => run("Gerando áudio pelo Fish Audio…", async () => {
  const text = $("speech-text").value.trim();
  if (!text) throw new Error("Digite um texto para gerar a voz.");
  if (text.length > 50000) throw new Error("Divida o texto em trechos de até 50.000 caracteres.");
  const response = await api("/voice/speech", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({text})});
  const blob = await response.blob();
  clearAudio(); audioUrl = URL.createObjectURL(blob);
  $("player").src = audioUrl; $("player").hidden = false;
  notice("Áudio recebido. Use o player para ouvir.");
}));

async function transcribe(blob) {
  if (!blob || !blob.size) throw new Error("Selecione ou grave um áudio primeiro.");
  if (blob.size > 10 * 1024 * 1024) throw new Error("O áudio deve ter no máximo 10 MiB.");
  const result = await (await api("/voice/transcribe", {method: "POST", headers: {"Content-Type": blob.type || "application/octet-stream"}, body: blob})).json();
  $("message").value = result.text;
  $("message").focus();
  notice("Áudio transcrito. Revise a mensagem e clique em Enviar.");
}

$("transcribe").addEventListener("click", () => run("Transcrevendo arquivo…", () => transcribe($("audio-file").files[0])));

function releaseMicrophone() {
  recordingStream?.getTracks().forEach(track => track.stop());
  recordingStream = null;
}

$("record").addEventListener("click", async () => {
  if (recorder?.state === "recording") { recorder.stop(); return; }
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return notice("Este navegador não oferece gravação. Use um arquivo de áudio ou abra em localhost/HTTPS.", true);
  if (!$("token").value.trim()) return notice("Informe o token antes de gravar.", true);
  busy = true; buttons.forEach(button => button.disabled = true);
  notice("Solicitando acesso ao microfone…");
  try {
    recordingStream = await navigator.mediaDevices.getUserMedia({audio: true});
    const mimeType = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"].find(type => MediaRecorder.isTypeSupported(type));
    recorder = mimeType ? new MediaRecorder(recordingStream, {mimeType}) : new MediaRecorder(recordingStream);
    const chunks = []; let total = 0, recordingFailed = false;
    const timeout = setTimeout(() => { if (recorder?.state === "recording") recorder.stop(); }, 60000);
    recorder.ondataavailable = event => {
      chunks.push(event.data); total += event.data.size;
      if (total > 10 * 1024 * 1024 && recorder.state === "recording") recorder.stop();
    };
    recorder.onstop = () => {
      clearTimeout(timeout);
      const blob = new Blob(chunks, {type: recorder.mimeType});
      releaseMicrophone(); recorder = null;
      busy = false; buttons.forEach(button => button.disabled = false);
      $("record").textContent = "Gravar pelo microfone";
      if (!recordingFailed) run("Transcrevendo gravação…", () => transcribe(blob));
    };
    recorder.onerror = () => {
      recordingFailed = true;
      clearTimeout(timeout); releaseMicrophone();
      busy = false; buttons.forEach(button => button.disabled = false);
      $("record").textContent = "Gravar pelo microfone";
      notice("A gravação falhou. Tente enviar um arquivo de áudio.", true);
    };
    recorder.start(1000);
    $("record").disabled = false;
    $("record").textContent = "Parar e transcrever";
    notice("Gravando… clique em Parar e transcrever. Limite de 60 segundos.");
  } catch (error) {
    releaseMicrophone(); recorder = null;
    busy = false; buttons.forEach(button => button.disabled = false);
    notice(`Não foi possível gravar: ${error.message}`, true);
  }
});

$("player").addEventListener("error", () => notice("O navegador não conseguiu reproduzir o áudio recebido.", true));
window.addEventListener("beforeunload", () => { releaseMicrophone(); if (audioUrl) URL.revokeObjectURL(audioUrl); });

// Apenas consulta o diagnóstico; não chama modelos nem escaneia arquivos do usuário.
let monitorTimer = null, monitorCursor = 0, monitorConnected = false, monitorPolling = false, monitorGeneration = 0;
let alertAudioUrl = null, alertSpeaking = false;
const pendingAlertSpeech = new Map();

function stopAlertAudio() {
  $("alert-player").pause(); $("alert-player").removeAttribute("src");
  if (alertAudioUrl) URL.revokeObjectURL(alertAudioUrl);
  alertAudioUrl = null;
}

async function speakAlert(alert) {
  if (!$("alert-voice").checked || alertSpeaking || busy || !$("alert-player").paused || ($("player").src && !$("player").paused)) return false;
  alertSpeaking = true;
  try {
    const response = await api("/voice/speech", {method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text:`Atenção. ${alert.message} ${alert.suggestion}`})});
    if (!$("alert-voice").checked) return;
    stopAlertAudio(); alertAudioUrl = URL.createObjectURL(await response.blob());
    $("alert-player").src = alertAudioUrl;
    await $("alert-player").play();
    $("alert-audio-status").textContent = "Alerta falado pelo Kronos.";
  } catch {
    $("alert-audio-status").textContent = "Não foi possível falar o alerta. Consulte o aviso escrito; não haverá repetição automática.";
  } finally { alertSpeaking = false; }
  return true;
}

function renderMonitor(result) {
  const stale = !result.checked_at || Date.now() - new Date(result.checked_at).getTime() > result.interval_seconds * 3000;
  $("radar").classList.toggle("paused", stale);
  $("radar").classList.toggle("attention", result.alerts.length > 0);
  const time = result.checked_at ? new Date(result.checked_at).toLocaleTimeString("pt-BR") : "pendente";
  $("monitor-status").textContent = `${stale ? "Diagnóstico atrasado; estado atual não confirmado" : result.alerts.length ? `${result.alerts.length} alerta(s) ativo(s)` : "Sem alertas ativos nos sinais monitorados"}. Última verificação: ${time}.`;
  const ram = result.resources.ram_used_percent;
  const disk = result.resources.disk_free_mib;
  $("monitor-resources").textContent = `RAM: ${ram == null ? "medição indisponível" : `${ram}% em uso`} · Disco do vault: ${disk == null ? "medição indisponível" : `${disk} MiB livres`}`;
  $("monitor-alerts").replaceChildren();
  for (const alert of result.alerts) {
    const card = document.createElement("li"); card.className = `monitor-alert ${alert.severity}`;
    const title = document.createElement("strong"); title.textContent = alert.message;
    const detail = document.createElement("p"); detail.textContent = alert.suggestion;
    card.append(title, detail);
    const acknowledge = document.createElement("button"); acknowledge.className = "secondary";
    acknowledge.textContent = alert.acknowledged ? "Você já tomou ciência" : "Estou ciente";
    acknowledge.disabled = alert.acknowledged;
    acknowledge.addEventListener("click", async () => {
      acknowledge.disabled = true;
      try { await api(`/monitor/alerts/${alert.id}/ack`, {method:"POST"}); await pollMonitor(); }
      catch { acknowledge.disabled = false; $("monitor-status").textContent = "Não foi possível registrar sua ciência. O alerta continua ativo."; }
    });
    card.append(acknowledge); $("monitor-alerts").append(card);
  }
}

async function pollMonitor() {
  if (monitorPolling || !monitorConnected) return;
  monitorPolling = true;
  const generation = monitorGeneration;
  try {
    const response = await api(`/monitor?after=${monitorCursor}`, {signal:AbortSignal.timeout(5000)});
    const result = await response.json();
    if (generation !== monitorGeneration || !monitorConnected) return;
    if (result.cursor < monitorCursor) monitorCursor = 0; // backend reiniciado
    renderMonitor(result);
    const fresh = result.events.filter(event => event.status === "active" && event.id > monitorCursor &&
      result.alerts.some(alert => alert.id === event.id && !alert.acknowledged));
    monitorCursor = result.cursor;
    // Uma fala por lote: prioriza o alerta crítico e evita sobrepor vários áudios.
    fresh.sort((a,b) => Number(b.severity === "critical") - Number(a.severity === "critical"));
    for (const event of fresh) if ($("alert-voice").checked && event.code !== "service_voice") pendingAlertSpeech.set(event.id, event);
    for (const id of pendingAlertSpeech.keys()) {
      if (!result.alerts.some(alert => alert.id === id && !alert.acknowledged)) pendingAlertSpeech.delete(id);
    }
    const waiting = [...pendingAlertSpeech.values()].sort((a,b) => Number(b.severity === "critical") - Number(a.severity === "critical"));
    if (waiting.length && await speakAlert(waiting[0])) pendingAlertSpeech.delete(waiting[0].id);
  } catch (error) {
    if (generation !== monitorGeneration) return;
    if ([401, 403, 429].includes(error.status)) { monitorConnected = false; clearInterval(monitorTimer); }
    $("radar").classList.add("paused");
    $("monitor-status").textContent = "Monitor sem conexão. Não é possível confirmar o estado atual. Verifique a conexão para retomar.";
  } finally { monitorPolling = false; }
}

function pauseMonitor() {
  monitorGeneration++; monitorConnected = false; clearInterval(monitorTimer);
  pendingAlertSpeech.clear(); stopAlertAudio();
  $("radar").classList.add("paused");
  $("monitor-status").textContent = "Monitor pausado. Verifique a conexão para acompanhar o estado atual.";
}
$("token").addEventListener("input", pauseMonitor);
function startMonitor() {
  monitorGeneration++;
  clearInterval(monitorTimer); monitorConnected = true; monitorCursor = 0;
  pollMonitor(); monitorTimer = setInterval(pollMonitor, 5000);
}
$("alert-voice").addEventListener("change", () => { if (!$("alert-voice").checked) { stopAlertAudio(); pendingAlertSpeech.clear(); } });
document.addEventListener("visibilitychange", () => { if (!document.hidden) pollMonitor(); });
window.addEventListener("beforeunload", () => { clearInterval(monitorTimer); stopAlertAudio(); });

// Central de funções. Todas as respostas são renderizadas como texto, nunca HTML.
const moduleNames = [
  ["processing","Processamento"],["vision","Visão computacional"],["voice","Síntese de voz"],
  ["language","Entendimento de linguagem"],["planning","Planejamento"],["tools","Ferramentas"],
  ["integrations","Integrações"],["database","Banco de dados"],["internet","Internet"],
  ["devices","Dispositivos"],["security","Segurança"],["monitoring","Monitoramento"]
];
let moduleCatalog = moduleNames.map(([id,name]) => ({id,name,description:"Conecte para consultar disponibilidade e usar as operações deste módulo."}));
let selectedModule = null, selectedVision = null, visionUrl = null, toolCatalog = [], providerOptions = [];
const checkLabels = {passed:"Verificação realizada",failed:"Verificação falhou",unavailable:"Indisponível",configuration_only:"Somente configuração; serviço ainda não testado"};
const availabilityLabels = {available:"Disponível; valide a operação",configuration_required:"Requer configuração",windows_required:"Requer Windows local",disabled:"Desativado neste modo"};
function showModuleOutput(result) { $("module-output").textContent = typeof result === "string" ? result : JSON.stringify(result,null,2); }
function renderModules() {
  $("modules-grid").replaceChildren();
  for (const item of moduleCatalog) {
    const button = document.createElement("button"); button.type="button"; button.className="module-button secondary";
    button.dataset.moduleId = item.id;
    const name=document.createElement("strong"); name.textContent=item.name;
    const state=document.createElement("small"); state.textContent=item.last_check ? checkLabels[item.last_check.status] : availabilityLabels[item.availability] || "Ainda não verificado";
    button.append(name,state); button.addEventListener("click",()=>{ if (!busy) openModule(item.id); });
    $("modules-grid").append(button);
  }
}
function openModule(id) {
  selectedModule=id;
  const item=moduleCatalog.find(item=>item.id===id);
  $("module-detail").hidden=false; $("module-title").textContent=item.name; $("module-description").textContent=item.description;
  document.querySelectorAll("[data-module]").forEach(element=>element.hidden=!element.dataset.module.split(" ").includes(id));
  showModuleOutput(item.last_check || "Use as ações abaixo ou faça uma verificação. Nenhum sucesso foi presumido.");
  $("module-check").textContent=["voice","vision"].includes(id) ? "Verificar configuração (sem chamada paga)" : "Verificar este módulo";
}
async function loadModules() {
  moduleCatalog=(await (await api("/modules")).json()).modules; renderModules();
}
$("module-check").addEventListener("click",()=>run("Verificando módulo…",async()=>{
  if (!selectedModule) return;
  const result=await (await api(`/modules/${selectedModule}/check`,{method:"POST"})).json();
  showModuleOutput(result); await loadModules();
  notice(checkLabels[result.status],result.status==="failed" || result.status==="unavailable");
}));
function bindOperation(id, label, operation) {
  $(id).addEventListener("click",()=>run(label,async()=>showModuleOutput(await operation())));
}
async function jsonApi(path,method="GET",body) {
  return (await api(path,{method,...(body===undefined?{}:{headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})})).json();
}
bindOperation("module-resources","Consultando diagnóstico…",()=>jsonApi("/monitor"));
$("module-voice").addEventListener("click",()=>$("voice-title").scrollIntoView({block:"start"}));
$("module-chat").addEventListener("click",()=>{ $("chat-title").scrollIntoView({block:"start"}); $("message").focus(); });

async function setVision(blob) {
  selectedVision=null; $("vision-consent").checked=false;
  if (!blob || !blob.size || blob.size>2*1024*1024) throw new Error("Escolha uma imagem PNG/JPEG de até 2 MiB.");
  const response=await api("/vision/preview",{method:"POST",headers:{"Content-Type":blob.type||"application/octet-stream"},body:blob});
  blob=await response.blob(); selectedVision=blob; $("vision-consent").checked=false;
  if (visionUrl) URL.revokeObjectURL(visionUrl);
  visionUrl=URL.createObjectURL(blob); $("vision-preview").src=visionUrl; $("vision-preview").hidden=false;
}
$("vision-file").addEventListener("change",()=>{
  selectedVision=null; $("vision-consent").checked=false;
  run("Validando a imagem localmente, sem envio à IA…",()=>setVision($("vision-file").files[0]));
});
$("vision-camera").addEventListener("click",()=>run("Solicitando câmera para uma fotografia…",async()=>{
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("Câmera indisponível nesta janela. Envie uma imagem.");
  let stream;
  try {
    stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720}},audio:false});
    const video=document.createElement("video"); video.srcObject=stream; video.muted=true;
    await video.play();
    const canvas=document.createElement("canvas"); canvas.width=video.videoWidth; canvas.height=video.videoHeight;
    if (!canvas.width || !canvas.height) throw new Error("A câmera não forneceu imagem.");
    canvas.getContext("2d").drawImage(video,0,0);
    await setVision(await new Promise(resolve=>canvas.toBlob(resolve,"image/jpeg",.85)));
    video.srcObject=null;
    showModuleOutput("Fotografia capturada para revisão. A câmera foi desligada; nada foi enviado à IA.");
  } finally { stream?.getTracks().forEach(track=>track.stop()); }
}));
$("vision-screen").addEventListener("click",()=>run("Capturando sua tela local para revisão…",async()=>{
  const response=await api("/vision/screen",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({consent:true})});
  await setVision(await response.blob()); showModuleOutput("Captura local disponível para revisão. Nada foi enviado à IA.");
}));
$("vision-analyze").addEventListener("click",()=>run("Analisando a imagem pelo Gemini…",async()=>{
  if (!selectedVision || !$("vision-consent").checked) throw new Error("Escolha a imagem e autorize explicitamente seu envio ao Gemini.");
  const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(",")[1]);reader.onerror=reject;reader.readAsDataURL(selectedVision);});
  const result=await jsonApi("/vision/analyze","POST",{image_base64:encoded,prompt:$("vision-prompt").value,consent:true});
  showModuleOutput(result); await loadModules(); notice("Imagem analisada. Nenhuma ação no computador foi executada.");
}));

function renderMissions(missions) {
  $("missions-list").replaceChildren();
  for (const mission of missions) {
    const card=document.createElement("article"); card.className="mission-card";
    const title=document.createElement("h4"); title.textContent=mission.plan.title;
    const objective=document.createElement("p"); objective.textContent=mission.objective;
    card.append(title,objective);
    mission.plan.steps.forEach((step,index)=>{
      const label=document.createElement("label"); label.className="monitor-voice";
      const checkbox=document.createElement("input"); checkbox.type="checkbox"; checkbox.checked=step.done;
      const text=document.createElement("span"); text.textContent=step.title;
      checkbox.addEventListener("change",async()=>{
        checkbox.disabled=true;
        try { await jsonApi(`/missions/${mission.id}/steps/${index}`,"POST",{done:checkbox.checked}); }
        catch(error) {checkbox.checked=!checkbox.checked;notice(error.message,true);}
        finally {checkbox.disabled=false;}
      });
      label.append(checkbox,text);card.append(label);
    });
    const hint=document.createElement("p");hint.className="hint";hint.textContent="As caixas registram etapas concluídas por você; o plano não executa ações automaticamente.";
    card.append(hint);$("missions-list").append(card);
  }
}
async function createMission(use_ai) {
  const result=await jsonApi("/missions","POST",{objective:$("mission-objective").value,
    steps:$("mission-steps").value.split("\n").filter(value=>value.trim()),use_ai});
  renderMissions([result]); showModuleOutput("Plano salvo. Retomar planos recupera seu progresso após reiniciar.");await loadModules();
}
$("mission-manual").addEventListener("click",()=>run("Salvando plano…",()=>createMission(false)));
$("mission-ai").addEventListener("click",()=>run("Solicitando plano à IA…",()=>createMission(true)));
bindOperation("missions-load","Carregando planos…",async()=>{const result=await jsonApi("/missions");renderMissions(result.missions);return `${result.missions.length} plano(s) carregado(s).`;});

function updateToolSchema() {
  const tool=toolCatalog.find(tool=>tool.name===$("tool-name").value);
  $("tool-schema").textContent=tool?JSON.stringify(tool.parameters,null,2):"";
  $("tool-description").textContent=tool?`${tool.description} ${tool.requires_confirmation?"Exige confirmação humana.":""}`:"";
}
bindOperation("tools-load","Carregando ferramentas…",async()=>{
  const result=await jsonApi("/tools");toolCatalog=result.tools;
  $("tool-name").replaceChildren(...toolCatalog.map(tool=>{const option=document.createElement("option");option.value=tool.name;option.textContent=tool.name;return option;}));
  updateToolSchema();return `${toolCatalog.length} ferramenta(s) disponíveis.`;
});
$("tool-name").addEventListener("change",updateToolSchema);
async function executeTool(name,args) {
  const result=await jsonApi("/tools/execute","POST",{name,arguments:args,session_id:session});
  session=result.session_id;$("session").value=session;showModuleOutput(result);
  if (result.status==="pending_confirmation") renderTools([result],$("module-approvals"));
  return result;
}
bindOperation("tool-execute","Solicitando ferramenta…",async()=>{
  let args;try{args=JSON.parse($("tool-arguments").value);}catch{throw new Error("Os argumentos precisam ser JSON válido.");}
  if (!$("tool-name").value) throw new Error("Carregue e selecione uma ferramenta.");
  return executeTool($("tool-name").value,args);
});

bindOperation("providers-load","Consultando provedores…",async()=>{
  const result=await jsonApi("/providers");
  providerOptions=result.providers;
  $("provider-select").replaceChildren(...result.providers.map(provider=>{const option=document.createElement("option");option.value=provider.id;option.textContent=`${provider.id} · ${provider.model}${provider.configured?"":" · falta configuração"}`;option.disabled=!provider.configured||!provider.allowed;return option;}));
  $("provider-select").value=result.selected;
  $("provider-model").value=providerOptions.find(item=>item.id===result.selected)?.model || "";
  return result;
});
$("provider-select").addEventListener("change",()=>{ $("provider-model").value=providerOptions.find(item=>item.id===$("provider-select").value)?.model || ""; });
bindOperation("provider-use","Selecionando provedor…",async()=>{
  const result=await jsonApi("/providers/select","POST",{provider:$("provider-select").value,...($("provider-model").value.trim()?{model:$("provider-model").value.trim()}:{})});
  await loadModules();
  $("status").children[1].textContent=`IA: ${result.selected} · seleção alterada; valide uma geração`;
  return result;
});
bindOperation("provider-models","Consultando catálogo de modelos…",async()=>jsonApi(`/providers/${encodeURIComponent($("provider-select").value)}/models`));
bindOperation("memory-check","Consultando memória…",()=>jsonApi("/memory/status"));
bindOperation("memory-sync","Sincronizando notas…",()=>jsonApi("/memory/sync","POST"));
bindOperation("memory-search","Buscando na memória…",()=>jsonApi("/memory/search","POST",{query:$("memory-query").value,limit:8}));
bindOperation("memory-read","Lendo nota…",()=>jsonApi(`/memory/note?path=${encodeURIComponent($("memory-path").value)}`));
bindOperation("web-search","Pesquisando na internet…",()=>executeTool("web_search",{query:$("web-query").value,limit:5}));
bindOperation("web-browser","Abrindo pesquisa no navegador local…",()=>executeTool("browser_search",{query:$("web-query").value}));
bindOperation("devices-query","Consultando dispositivos locais…",()=>jsonApi("/devices"));
bindOperation("browser-devices","Consultando dispositivos disponíveis na janela…",async()=>{
  if (!navigator.mediaDevices?.enumerateDevices) throw new Error("Enumeração indisponível nesta janela.");
  return (await navigator.mediaDevices.enumerateDevices()).map(device=>({kind:device.kind,label:device.label||"Nome oculto até autorizar o dispositivo"}));
});
bindOperation("wake-status","Consultando ouvinte local…",()=>jsonApi("/wake/status"));
bindOperation("windows-audit","Auditando Windows sem alterar configurações…",()=>jsonApi("/windows/audit"));
bindOperation("windows-jobs","Consultando operações…",()=>jsonApi("/windows/jobs"));
document.querySelectorAll("[data-windows-action]").forEach(button=>button.addEventListener("click",()=>run("Preparando ação para sua confirmação…",()=>executeTool("windows_security_action",{action:button.dataset.windowsAction}))));
window.addEventListener("beforeunload",()=>{if(visionUrl)URL.revokeObjectURL(visionUrl);});
renderModules();

// A janela holográfica transmite apenas o token em memória, para esta origem.
window.addEventListener("message", event => {
  if (window.parent === window || event.origin !== window.location.origin || event.source !== window.parent) return;
  if (event.data?.type !== "cronos:connect" || typeof event.data.token !== "string") return;
  $("token").value = event.data.token;
  $("connect-form").requestSubmit();
});
function openEmbeddedModule() {
  const id = new URLSearchParams(window.location.hash.slice(1)).get("module");
  if (!id || !moduleNames.some(([name]) => name === id)) return;
  openModule(id);
  if (window.parent !== window) {
    document.body.classList.add("module-embedded");
    document.body.classList.toggle("monitor-view", id === "monitoring");
    document.body.classList.toggle("voice-view", id === "voice");
  }
}
openEmbeddedModule();
function moduleActivity() {
  if (window.parent === window) return;
  const state = recorder?.state === "recording" ? "LISTENING" : !$("player").paused || !$("alert-player").paused ? "SPEAKING" : "IDLE";
  window.parent.postMessage({type:"cronos:activity",state},window.location.origin);
}
$("player").addEventListener("playing", moduleActivity); $("player").addEventListener("ended", moduleActivity);
$("player").addEventListener("pause", moduleActivity);
$("alert-player").addEventListener("playing", moduleActivity); $("alert-player").addEventListener("ended", moduleActivity);
const activityObserver = new MutationObserver(moduleActivity);
activityObserver.observe($("record"), {childList:true});
window.addEventListener("beforeunload",()=>activityObserver.disconnect());

window.cronosPanelClose = () => {
  if (recorder?.state === "recording") { recorder.onstop = null; recorder.stop(); }
  releaseMicrophone(); recorder = null;
  busy = false; buttons.forEach(button => button.disabled = false);
  $("record").textContent = "Gravar pelo microfone";
  $("player").pause(); $("alert-player").pause(); stopAlertAudio();
  clearInterval(monitorTimer); monitorConnected = false;
};
window.addEventListener("pagehide", window.cronosPanelClose);
