# External Trigger (IPC)

[![](https://img.shields.io/badge/←_⚙️_Configuration-30363d?style=for-the-badge)](./Configuration.md)

InputBar listens on a local pipe `InputBar_Singleton_Lock`.  

Compatible with AutoHotkey, PowerShell, or any tool that can launch a process.

It can be triggered from any external script:

## Bash / Shell / CMD
```bash
# Show InputBar
python InputBar.pyw

# Pre-fill the search bar
python InputBar.pyw --search "premiere"
```

## Autohotkey
```bash
Ctrl+Space::{
    pipeReady := DllCall("WaitNamedPipe", "Str", "\\.\pipe\InputBar_Singleton_Lock", "UInt", 50)

    if (pipeReady) {
        try {
            pipe := FileOpen("\\.\pipe\InputBar_Singleton_Lock", "w")
            pipe.Write("SHOW")
            pipe.Close()
            return ; Succes, show the InputBar.
        } catch {
            ; If an error is thrown -> Fallback
        }
    }
    ; Fallback -> Run "InputBar.exe/.pyw"
    Target := 'C:\Program Files (x86)\InputBar\InputBar.exe" --show'
    try {
        Run(Target, , "Hide")
    } catch as err {
        MsgBox("Error : " . err.Message)
    }
}
```