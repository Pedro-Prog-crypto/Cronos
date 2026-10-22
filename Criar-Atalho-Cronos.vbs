Option Explicit

Dim fso, shell, root, launcher, desktop, shortcut
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = fso.BuildPath(root, "ABRIR-CRONOS.bat")
If Not fso.FileExists(launcher) Then
    WScript.Echo "Nao encontrei ABRIR-CRONOS.bat nesta pasta."
    WScript.Quit 1
End If

desktop = shell.SpecialFolders("Desktop")
Set shortcut = shell.CreateShortcut(fso.BuildPath(desktop, "CRONOS.lnk"))
shortcut.TargetPath = launcher
shortcut.WorkingDirectory = root
shortcut.Description = "Abrir esta instalacao local do CRONOS"
shortcut.WindowStyle = 7
shortcut.Save
WScript.Echo "Atalho criado para esta pasta do CRONOS."
