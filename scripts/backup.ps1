<#
.SYNOPSIS
  Kopia zapasowa "Rejestr zmian IT" (Windows / PowerShell 5.1 i 7): baza (pg_dump,
  format custom) + pliki (wolumen storage) + sumy SHA-256, z retencją.

.DESCRIPTION
  Odpowiednik scripts/backup.sh (ADR 0019 §6, docs/deployment.md). Uruchamiaj z
  katalogu głównego repozytorium (docker-compose.yml, .env) przy działającej
  usłudze db. Pliki binarne są kopiowane przez "docker cp" (bez przekierowań
  strumieni PowerShella, które w 5.1 psują dane binarne).

  Zrzut wykonuje superużytkownik "postgres" (app_rw podlega RLS); zawiera
  właścicieli i uprawnienia, ale nie same role (tworzy je init bazy).

  Szyfrowanie programem age (ADR 0019 §10): gdy podano -AgeRecipient /
  BACKUP_AGE_RECIPIENT (klucz publiczny age1..., kilka rozdziel przecinkami;
  age -r) lub -AgeRecipientsFile / BACKUP_AGE_RECIPIENTS (plik kluczy
  publicznych; age -R), zrzut i archiwum plików są szyfrowane STRUMIENIOWO
  (proces pg_dump/tar -> proces age, kopiowanie bajtów bez potoku PowerShella;
  żaden niezaszyfrowany plik nie trafia na dysk hosta). Powstają pliki
  *.dump.age i *-storage.tar.gz.age, sumy SHA-256 liczone są z plików
  zaszyfrowanych. Brak age.exe przy ustawionej zmiennej = błąd (kopia nie
  powstaje). Klucz prywatny nie jest potrzebny do kopii.

.EXAMPLE
  .\scripts\backup.ps1
  .\scripts\backup.ps1 -BackupDir D:\kopie -RetentionDays 30 -SkipStorage
  $env:BACKUP_AGE_RECIPIENT = 'age1...'; .\scripts\backup.ps1
#>
[CmdletBinding()]
param(
    [string]$BackupDir = $(if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { '.\backups' }),
    [int]$RetentionDays = $(if ($env:BACKUP_RETENTION_DAYS) { [int]$env:BACKUP_RETENTION_DAYS } else { 14 }),
    [string]$Database = $(if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { 'rejestr' }),
    [string]$AgeRecipient = $env:BACKUP_AGE_RECIPIENT,
    [string]$AgeRecipientsFile = $env:BACKUP_AGE_RECIPIENTS,
    [switch]$SkipStorage
)

$ErrorActionPreference = 'Stop'

function ConvertTo-NativeArgument {
    # Quoting for ProcessStartInfo.Arguments (CommandLineToArgvW rules; PowerShell
    # 5.1 / .NET Framework has no ArgumentList).
    param([string]$Value)
    if ($Value -eq '') { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', { param($m) ($m.Groups[1].Value * 2) + '\"' })
    $escaped = [regex]::Replace($escaped, '(\\+)$', { param($m) $m.Groups[1].Value * 2 })
    return '"' + $escaped + '"'
}

function Start-NativeProcess {
    param([string]$File, [string[]]$Arguments, [switch]$RedirectInput, [switch]$RedirectOutput)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command $File -CommandType Application | Select-Object -First 1).Source
    $psi.Arguments = (@($Arguments) | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = [bool]$RedirectInput
    $psi.RedirectStandardOutput = [bool]$RedirectOutput
    $savedEncoding = $null
    if ($RedirectInput -and [Console]::InputEncoding.GetPreamble().Length -gt 0) {
        # .NET Framework (PowerShell 5.1) writes the preamble of Console.InputEncoding
        # (UTF-8 BOM) into a redirected stdin as soon as the process starts, which
        # would corrupt the binary stream. No preamble = nothing is written.
        $savedEncoding = [Console]::InputEncoding
        [Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
    }
    try {
        return [System.Diagnostics.Process]::Start($psi)
    } finally {
        if ($savedEncoding) { [Console]::InputEncoding = $savedEncoding }
    }
}

function Invoke-NativePipe {
    # Binary-safe "From | To": the bytes are copied between the processes' streams.
    # A PowerShell pipeline would decode native output as text and corrupt it.
    param([string]$From, [string[]]$FromArgs, [string]$To, [string[]]$ToArgs)
    $consumer = Start-NativeProcess $To $ToArgs -RedirectInput
    try {
        $producer = Start-NativeProcess $From $FromArgs -RedirectOutput
    } catch {
        try { $consumer.Kill() } catch { }
        throw
    }
    $copyError = $null
    try {
        $producer.StandardOutput.BaseStream.CopyTo($consumer.StandardInput.BaseStream)
    } catch {
        # The consumer exited early (broken pipe); stop the producer so it does not block.
        $copyError = $_
        try { if (-not $producer.HasExited) { $producer.Kill() } } catch { }
    } finally {
        try { $consumer.StandardInput.Close() } catch { }
    }
    $producer.WaitForExit()
    $consumer.WaitForExit()
    if ($producer.ExitCode -ne 0) {
        throw "Polecenie nie powiodło się ($($producer.ExitCode)): $From $($FromArgs -join ' ')"
    }
    if ($consumer.ExitCode -ne 0) {
        throw "Polecenie nie powiodło się ($($consumer.ExitCode)): $To $($ToArgs -join ' ')"
    }
    if ($copyError) { throw $copyError }
}

# --- szyfrowanie age (opcjonalne) ---------------------------------------------
$ageArgs = @()
if ($AgeRecipient) {
    foreach ($key in ($AgeRecipient -split ',')) {
        if ($key.Trim()) { $ageArgs += @('-r', $key.Trim()) }
    }
    if (-not $ageArgs) { throw 'BACKUP_AGE_RECIPIENT nie zawiera żadnego klucza publicznego.' }
}
if ($AgeRecipientsFile) {
    if (-not (Test-Path -LiteralPath $AgeRecipientsFile -PathType Leaf)) {
        throw "BACKUP_AGE_RECIPIENTS: brak pliku z kluczami publicznymi: $AgeRecipientsFile"
    }
    $ageArgs += @('-R', (Resolve-Path -LiteralPath $AgeRecipientsFile).Path)
}
$encrypt = $ageArgs.Count -gt 0
$suffix = ''
if ($encrypt) {
    if (-not (Get-Command age -CommandType Application -ErrorAction SilentlyContinue)) {
        throw ('Ustawiono BACKUP_AGE_RECIPIENT(S), ale nie znaleziono programu age w PATH. ' +
            'Kopia NIE została wykonana (nie zapisujemy kopii bez szyfrowania). ' +
            'Instalacja: winget install FiloSottile.age')
    }
    # Fail before dumping anything if a recipient is malformed.
    $probe = Start-NativeProcess age $ageArgs -RedirectInput -RedirectOutput
    $probe.StandardInput.Close()
    $probe.StandardOutput.BaseStream.CopyTo([IO.Stream]::Null)
    $probe.WaitForExit()
    if ($probe.ExitCode -ne 0) { throw 'Nieprawidłowy klucz publiczny age w BACKUP_AGE_RECIPIENT(S).' }
    $suffix = '.age'
}

function Write-Encrypted {
    # From (native command) -> age -> $Target, via $Target.part renamed on success.
    param([string]$From, [string[]]$FromArgs, [string]$Target)
    $partial = "$Target.part"
    try {
        Invoke-NativePipe $From $FromArgs age ($ageArgs + @('-o', $partial))
        Move-Item -LiteralPath $partial -Destination $Target
    } catch {
        Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        throw
    }
}

function Invoke-Native {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Polecenie nie powiodło się ($LASTEXITCODE): $File $($Arguments -join ' ')"
    }
}

function Get-NativeOutput {
    param([string]$File, [string[]]$Arguments)
    $out = & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Polecenie nie powiodło się ($LASTEXITCODE): $File $($Arguments -join ' ')"
    }
    return ($out | Out-String).Trim()
}

$dbContainer = (& docker compose ps -q db | Out-String).Trim()
if (-not $dbContainer) { throw 'Usługa db nie działa (docker compose up -d db).' }

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$BackupDir = (Resolve-Path $BackupDir).Path
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd'T'HHmmss'Z'")
$base = "rejestr-$stamp"
$dump = "$base.dump$suffix"
$pgDump = @('compose', 'exec', '-T', 'db', 'pg_dump', '-U', 'postgres', '-d', $Database,
    '--format=custom', '--compress=6')

if ($encrypt) {
    Write-Host "==> pg_dump bazy $Database (format custom, szyfrowanie age)"
    Write-Encrypted docker $pgDump (Join-Path $BackupDir $dump)
} else {
    Write-Host "==> pg_dump bazy $Database (format custom)"
    $tmpInContainer = "/tmp/$dump"
    Invoke-Native docker ($pgDump + @("--file=$tmpInContainer"))
    Invoke-Native docker @('compose', 'cp', "db:$tmpInContainer", (Join-Path $BackupDir $dump))
    Invoke-Native docker @('compose', 'exec', '-T', 'db', 'rm', '-f', $tmpInContainer)
}
$files = @($dump)

if (-not $SkipStorage) {
    # JSON instead of a Go template with quotes (PowerShell 5.1 mangles embedded quotes).
    $project = (Get-NativeOutput docker @('inspect', $dbContainer) | ConvertFrom-Json)[0].Config.Labels.'com.docker.compose.project'
    $volume = Get-NativeOutput docker @('volume', 'ls', '-q',
        '--filter', "label=com.docker.compose.project=$project",
        '--filter', 'label=com.docker.compose.volume=storage')
    if (-not $volume) {
        Write-Warning "Nie znaleziono wolumenu storage projektu $project - pomijam pliki."
    } else {
        Write-Host "==> archiwum plików (wolumen $volume)"
        $storage = "$base-storage.tar.gz$suffix"
        $image = Get-NativeOutput docker @('inspect', '--format', '{{.Config.Image}}', $dbContainer)
        if ($encrypt) {
            # tar to stdout -> age (no unencrypted archive, not even in the helper container).
            Write-Encrypted docker @('run', '--rm', '-v', "${volume}:/data:ro", $image,
                'tar', '-C', '/data', '-czf', '-', '.') (Join-Path $BackupDir $storage)
        } else {
            $helper = "rejestr-backup-$stamp".ToLower()
            try {
                Invoke-Native docker @('run', '--name', $helper, '-v', "${volume}:/data:ro", $image,
                    'tar', '-C', '/data', '-czf', '/tmp/storage.tar.gz', '.')
                Invoke-Native docker @('cp', "${helper}:/tmp/storage.tar.gz", (Join-Path $BackupDir $storage))
            } finally {
                try { & docker rm -f $helper *> $null } catch { }
            }
        }
        $files += $storage
    }
}

Write-Host '==> sumy SHA-256'
# Format zgodny z "sha256sum -c" (skrót, dwie spacje, nazwa pliku).
$lines = foreach ($f in $files) {
    $hash = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $BackupDir $f)).Hash.ToLower()
    "$hash  $f"
}
$sumsPath = Join-Path $BackupDir "$base.sha256"
[IO.File]::WriteAllText($sumsPath, (($lines -join "`n") + "`n"))

if ($RetentionDays -gt 0) {
    # rejestr-* covers *.dump[.age], *-storage.tar.gz[.age], *.sha256 and *.part leftovers.
    Write-Host "==> retencja: usuwam kopie starsze niż $RetentionDays dni"
    $limit = (Get-Date).AddDays(-$RetentionDays)
    Get-ChildItem -Path $BackupDir -File -Filter 'rejestr-*' |
        Where-Object { $_.LastWriteTime -lt $limit } |
        ForEach-Object { Write-Host "    $($_.Name)"; Remove-Item -LiteralPath $_.FullName -Confirm:$false }
}

Write-Host "Gotowe: $(Join-Path $BackupDir $base).*"
