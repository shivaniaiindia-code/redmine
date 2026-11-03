# Start Company Intelligence Platform (Backend + Frontend)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Starting Company Intelligence Platform  " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Start Backend in separate window
Write-Host "`n[1/2] Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\Activate.ps1; `$env:PYTHONPATH='.'; python -m uvicorn main:app --reload --port 8000"

Start-Sleep -Seconds 2

# 2. Start Frontend in separate window
Write-Host "[2/2] Starting Next.js Dashboard on port 3000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`n✓ Platform is starting!" -ForegroundColor Green
Write-Host "  - Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  - API Swagger Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Frontend UI: http://localhost:3000" -ForegroundColor White
Write-Host "  - Default Admin: admin@company.com / admin123" -ForegroundColor White
Write-Host "`nPress any key to exit this launcher window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

