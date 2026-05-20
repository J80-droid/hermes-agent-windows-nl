# Exit 0 = geen ingest.py actief; exit 1 = al bezig (toon PID).
$found = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and $_.CommandLine -like '*rag_pipeline\ingest.py*' }
if ($found) {
    foreach ($p in $found) {
        Write-Host "[WARN] RAG-ingest draait al (PID $($p.ProcessId))."
    }
    exit 1
}
exit 0
