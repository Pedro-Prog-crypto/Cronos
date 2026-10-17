"""Normalize packaging, preserving design and the existing sandbox validation."""
import re
from html import escape
from html.parser import HTMLParser


class Packaging(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts=[];self.css=[];self.js=[];self.mode=None;self.lifted=False
    def handle_decl(self,value):self.parts.append('<!'+value+'>')
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='style':self.mode='css';self.lifted=True;return
        if tag=='script' and not values.get('src') and values.get('type','') in {'','text/javascript','application/javascript'}:
            self.mode='js';self.lifted=True;return
        changed=False
        for key in ('href','src'):
            if values.get(key) in {'./styles.css','./app.js'}:values[key]=values[key][2:];changed=True
        if 'style' in values:
            identifier='studio-inline-'+str(len(self.css));self.css.append('.'+identifier+'{'+values.pop('style')+'}')
            values['class']=(values.get('class','')+' '+identifier).strip();changed=True;self.lifted=True
        if changed:
            self.parts.append('<'+tag+''.join(' '+key+('="'+escape(value,quote=True)+'"' if value is not None else '') for key,value in values.items())+'>')
        else:self.parts.append(self.get_starttag_text())
    def handle_endtag(self,tag):
        if self.mode and tag==('style' if self.mode=='css' else 'script'):self.mode=None;return
        self.parts.append('</'+tag+'>')
    def handle_data(self,value):
        (self.css if self.mode=='css' else self.js if self.mode=='js' else self.parts).append(value)
    def handle_entityref(self,value):self.handle_data('&'+value+';')
    def handle_charref(self,value):self.handle_data('&#'+value+';')
    def handle_comment(self,value):
        if self.mode:self.handle_data('/*'+value+'*/')
        else:self.parts.append('<!--'+value+'-->')
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.parts and self.parts[-1].endswith('>') and not self.parts[-1].endswith('/>'):self.parts[-1]=self.parts[-1][:-1]+'/>'


def normalize(files):
    files={k:re.sub(r'^```(?:html|css|javascript|js)\s*|\s*```$','',v.strip(),flags=re.I) if v.strip().startswith('```') else v for k,v in files.items()}
    # Leave valid packages byte-for-byte unchanged; never rewrite ordinary SVG/HTML.
    text=files['index.html']
    if not re.search(r'<style\b|<script(?![^>]*\bsrc=)|\sstyle\s*=|[\'"]\./(?:styles.css|app.js)',text,re.I):return files
    compiler=Packaging();compiler.feed(text);compiler.close()
    html=''.join(compiler.parts)
    if compiler.css:
        files['styles.css']+='\n'+''.join(compiler.css)
        if not re.search(r'<link\b[^>]*href=[\'"]styles.css[\'"]',html,re.I):html=html.replace('</head>','<link rel="stylesheet" href="styles.css"></head>',1)
    if compiler.js:
        files['app.js']+='\n'+''.join(compiler.js)
        if not re.search(r'<script\b[^>]*src=[\'"]app.js[\'"]',html,re.I):html=html.replace('</head>','<script src="app.js" defer></script></head>',1)
    return {**files,'index.html':html}
