Option Explicit

Dim fso, shell, args, root, folder, shortcut, desktop, launcher
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
Set args = WScript.Arguments

If args.Count > 0 Then
    root = fso.GetAbsolutePathName(args(0))
Else
    Set folder = CreateObject("Shell.Application").BrowseForFolder(0, _
        "Escolha a pasta do Cronos que voce usa", &H1 + &H10)
    If folder Is Nothing Then WScript.Quit 0
    root = folder.Self.Path
End If

launcher = fso.BuildPath(root, "Iniciar-Cronos-Web.bat")
If Not fso.FileExists(launcher) Then
    WScript.Echo "Nao encontrei Iniciar-Cronos-Web.bat nessa pasta."
    WScript.Quit 1
End If

desktop = shell.SpecialFolders("Desktop")
Set shortcut = shell.CreateShortcut(fso.BuildPath(desktop, "CRONOS.lnk"))
shortcut.TargetPath = launcher
shortcut.WorkingDirectory = root
shortcut.Description = "Abrir o CRONOS com seus dados"
shortcut.WindowStyle = 7
shortcut.Save

WScript.Echo "Atalho do CRONOS criado na Area de Trabalho."
