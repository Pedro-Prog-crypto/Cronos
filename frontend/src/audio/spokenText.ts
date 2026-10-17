/** Remove transport/storage decorations before chunking; code remains on screen. */
export function spokenText(value:string):string {
 let text=value.trim();
 if(text.startsWith('{'))try{const data=JSON.parse(text);if(Array.isArray(data.tool_calls??[])&&!(data.tool_calls??[]).length&&typeof data.reply==='string')text=data.reply;}catch{}
 text=text.replace(/^\s*(?:\[)?(?:[A-Z]:[\\/]|\/(?:home|workspace|tmp|Users)\/|(?:Temas|Memorias|Conversas)\/)[^\n]*(?:\n|$)/gm,'');
 const footer=/^\s*(?:#{1,6}\s*)?(?:resumo (?:da conversa|para (?:a )?mem[oó]ria)|metadados(?: de mem[oó]ria)?|mem[oó]ria interna|topics|tool_calls)\s*[:：]/im.exec(text);
 if(footer&&text.slice(0,footer.index).trim())text=text.slice(0,footer.index);
 text=text.replace(/\n\s*\n(?:O usu[aá]rio|A usu[aá]ria) (?:disse|falou|mencionou|relatou|afirmou|perguntou)\b[^\n]*(?:\n[^\n]+)*\s*$/i,'');
 text=text.replace(/```[^\n]*\n[\s\S]*?(?:```|$)/g,' O código está disponível na tela. ')
  .replace(/!?\[([^\]]+)\]\([^\n)]*\)/g,'$1').replace(/https?:\/\/[^\s<>]+/g,'')
  .replace(/\b[A-Z]:[\\/][^\s<>]+/g,'').replace(/^\s*#{1,6}\s*/gm,'').replace(/\*\*|__|`/g,'');
 return text.replace(/\s+/g,' ').trim();
}
