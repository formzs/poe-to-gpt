# 设置输出编码为UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

Write-Output "============================================="
Write-Output "              POE-to-GPT Server             "
Write-Output "============================================="
Write-Output ""
Write-Output "Starting server..."
Write-Output "Press Ctrl+C to stop the server"
Write-Output ""

# 启动服务器
try {
    python app.py
} catch {
    Write-Output ""
    Write-Output "Server exited with error: $_"
    Write-Output "Press Enter to exit..."
    $null = Read-Host
    exit 1
}

# 如果服务器正常退出
if ($LASTEXITCODE -ne 0) {
    Write-Output ""
    Write-Output "Server exited with code: $LASTEXITCODE"
    Write-Output "Press Enter to exit..."
    $null = Read-Host
} 