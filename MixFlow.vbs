' MixFlow — launcher sin ventana de consola
Option Explicit
Dim sh, fso, dir, gui
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
gui = dir & "\MixFlowGUI.py"
sh.CurrentDirectory = dir

' 0 = ventana oculta; False = no esperar
On Error Resume Next
sh.Run "pyw """ & gui & """", 0, False
If Err.Number <> 0 Then
  Err.Clear
  sh.Run "pythonw """ & gui & """", 0, False
End If
If Err.Number <> 0 Then
  MsgBox "No se encontro pyw/pythonw." & vbCrLf & "Instala Python con el launcher e intenta de nuevo.", vbCritical, "MixFlow"
End If
