"""Read a public foreground page on request. No clipboard or keyboard shortcuts."""
import json
import os
import subprocess
import sys
from urllib.parse import urlsplit


def active_url():
    if sys.platform!='win32':return None
    try:
        import ctypes
        from ctypes import wintypes
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.GetForegroundWindow.restype=wintypes.HWND
        handle=user.GetForegroundWindow()
        title=ctypes.create_unicode_buffer(1024)
        user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.GetWindowTextW(handle,title,len(title))
        if not any(word in title.value.casefold() for word in ('chrome','edge','firefox','brave','opera')):return None
        import clr
        clr.AddReference('UIAutomationClient');clr.AddReference('UIAutomationTypes')
        from System import IntPtr
        from System.Windows.Automation import AutomationElement,PropertyCondition,ControlType,TreeScope,ValuePattern
        element=AutomationElement.FromHandle(IntPtr(handle))
        edits=element.FindAll(TreeScope.Descendants,PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Edit))
        for index in range(min(edits.Count,100)):
            edit=edits.Item[index];name=str(edit.Current.Name).casefold()
            if not any(word in name for word in ('address','endere','direcci','url','location','search or enter')):continue
            value=str(edit.GetCurrentPattern(ValuePattern.Pattern).Current.Value)
            parsed=urlsplit(value)
            if parsed.scheme in {'http','https'} and parsed.hostname and parsed.username is None and len(value)<=2000:return value
    except Exception:return None
    return None


def page_context():
    if sys.platform!='win32':return None
    from cronos.wake import independent_environment,python_windowless
    try:
        result=subprocess.run([str(python_windowless()),'-m','cronos.desktop_page','--read'],
            env=independent_environment(),shell=False,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode or len(result.stdout)>80000:return None
        data=json.loads(result.stdout.decode('utf-8'))
        if isinstance(data,dict) and isinstance(data.get('text'),str) and len(data['text'])<=12000:return data
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return None


def main():
    result={}
    url=active_url()
    if url:
        try:
            from cronos.studio.network import public_fetch
            from cronos.studies import _PageText
            page=public_fetch(url,max_bytes=1_500_000)
            if page['status']==200 and 'text/html' in page['headers'].get('content-type',''):
                parser=_PageText();parser.feed(page['body'].decode('utf-8',errors='replace'))
                text='\n'.join(parser.parts).strip()
                if text:result={'url':page['url'],'title':' '.join(parser.title_parts)[:200],
                                'text':text[:12000],'truncated':len(text)>12000}
        except Exception:pass
    os.write(1,json.dumps(result,ensure_ascii=False).encode('utf-8'))


if __name__=='__main__':main()
