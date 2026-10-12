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
    throw new Error(typeof detail === "string" ? detail : `A requisição falhou (HTTP ${response.status}).`);
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

function renderTools(results) {
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
      details.style.whiteSpace = "pre-wrap"; card.append(details);
      const controls = document.createElement("div"); controls.className = "row";
      const confirm = document.createElement("button"); confirm.textContent = "Confirmar ação";
      const cancel = document.createElement("button"); cancel.textContent = "Cancelar"; cancel.className = "secondary";
      const resolve = accepted => {
        if (busy) return;
        run("Processando sua decisão…", async () => {
          const response = await (await api(`/tools/approvals/${result.approval_id}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({session_id: result.session_id || session, accepted})})).json();
          confirm.disabled = true; cancel.disabled = true;
          text.textContent = labels[response.status] + (response.error ? `: ${response.error}` : "");
          notice(response.status === "completed" ? "Ação concluída. Você pode continuar a conversa." : text.textContent, response.status === "failed");
        });
      };
      confirm.addEventListener("click", () => resolve(true)); cancel.addEventListener("click", () => resolve(false));
      controls.append(confirm, cancel); card.append(controls);
    }
    $("messages").append(card);
  }
}

$("connect-form").addEventListener("submit", event => {
  event.preventDefault();
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
