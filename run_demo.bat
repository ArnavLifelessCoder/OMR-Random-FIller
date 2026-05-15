@echo off
echo ============================================================
echo OMR Synthetic Data Generator - Demo
echo ============================================================
echo.

echo Step 1: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies!
    pause
    exit /b 1
)
echo.

echo Step 2: Testing mark generation...
python test_mark_generation.py
if errorlevel 1 (
    echo Error in test script!
    pause
    exit /b 1
)
echo.

echo Step 3: Generating OMR samples for ALL templates...
python batch_fill_all_pdfs.py 10
if errorlevel 1 (
    echo Error generating samples!
    pause
    exit /b 1
)
echo.

echo ============================================================
echo Demo Complete!
echo ============================================================
echo.
echo Generated files:
echo   - mark_types_showcase.png
echo   - mark_types_comparison.png
echo   - generated_omr_samples\ (folder with PDFs)
echo.
echo Next steps:
echo   1. Review the PNG images
echo   2. Check PDFs in generated_omr_samples folder
echo   3. Run your OMR scanner on the PDFs
echo   4. Use analyze_results.py to compare results
echo.
pause
