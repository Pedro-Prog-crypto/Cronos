Option Explicit
Dim fs, shell, root, helper, runner, folder, picker, command
Set fs = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fs.GetParentFolderName(fs.GetParentFolderName(WScript.ScriptFullName))
helper = root & "\tools\start_bundle.py"
shell.CurrentDirectory = root
If Not fs.FileExists(helper) Then
    MsgBox "Extraia o ZIP completo antes de abrir o Cronos.", 48, "Cronos"
    WScript.Quit 1
End If
runner = root & "\.venv\Scripts\pythonw.exe"
If fs.FileExists(runner) Then
    shell.Run Quote(runner) & " " & Quote(helper), 0, False
    WScript.Quit 0
End If
If TryLauncher("pyw.exe") Then WScript.Quit 0
If TryLauncher("py.exe") Then WScript.Quit 0
Set picker = CreateObject("Shell.Application").BrowseForFolder(0, "Escolha a pasta do Cronos que voce ja usa. Suas configuracoes serao mantidas.", 0)
If picker Is Nothing Then WScript.Quit 0
folder = picker.Self.Path
runner = folder & "\.venv\Scripts\pythonw.exe"
If Not fs.FileExists(runner) Then
    MsgBox "Nao encontrei o Python da instalacao. Escolha a pasta que contem .venv e Iniciar-Cronos-Web.bat.", 48, "Cronos"
    WScript.Quit 1
End If
shell.Run Quote(runner) & " " & Quote(helper) & " --target " & Quote(folder), 0, False
Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function

Function TryLauncher(name)
    Dim status, check
    On Error Resume Next
    check = "import sys, tkinter; sys.exit(0 if sys.version_info >= (3,11) else 1)"
    status = shell.Run(name & " -3 -c " & Quote(check), 0, True)
    If Err.Number <> 0 Then
        Err.Clear
        TryLauncher = False
    ElseIf status <> 0 Then
        TryLauncher = False
    Else
        shell.Run name & " -3 " & Quote(helper), 0, False
        TryLauncher = (Err.Number = 0)
        Err.Clear
    End If
    On Error GoTo 0
End Function
