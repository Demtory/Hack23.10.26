$pptx = Resolve-Path "pitch/risk-desk-pitch.pptx"
$pdf = [System.IO.Path]::ChangeExtension($pptx, ".pdf")
Write-Output "Converting $pptx to $pdf"

$ppt = New-Object -ComObject PowerPoint.Application
try {
    $presentation = $ppt.Presentations.Open($pptx, 2, 0, 0)
    $presentation.SaveAs($pdf, 32)
    $presentation.Close()
    Write-Output "Successfully saved $pdf"
} finally {
    $ppt.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
