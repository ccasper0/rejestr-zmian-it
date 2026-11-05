<#
.SYNOPSIS
  Odtworzenie "Rejestr zmian IT" z kopii scripts/backup.ps1 / backup.sh + weryfikacja
  łańcuchów audytu (Windows / PowerShell 5.1 i 7).

.DESCRIPTION
  Odpowiednik scripts/restore.sh (ADR 0019 §6, docs/deployment.md):
    1. sprawdza sumy SHA-256 (plik KOPIA.sha256 obok zrzutu);
    2. tworzy PUSTĄ bazę (domyślnie rejestr) z uprawnieniami ról app_owner/app_rw
       (role muszą istnieć - tworzy je init bazy); istniejąca baza z danymi jest
       usuwana TYLKO z -Force;
    3. pg_restore jako postgres (jedna transakcja, przerwanie przy błędzie);
    4. opcjonalnie odtwarza pliki (wolumen storage) z -Storage;
    5. python -m app.cli verify-audit --global oraz --company dla każdej spółki.

  Przed odtworzeniem bazy produkcyjnej: docker compose stop api worker web

  Kopie zaszyfrowane (*.dump.age, *-storage.tar.gz.age; ADR 0019 §10): sumy
  SHA-256 plików zaszyfrowanych są sprawdzane PRZED odszyfrowaniem, potem
  próbne odszyfrowanie całości (klucz, integralność) zanim cokolwiek zostanie
  usunięte; odszyfrowanie strumieniowe (age -d -> pg_restore / tar, bez
  odszyfrowanego pliku na dysku) kluczem prywatnym z -Identity albo
  BACKUP_AGE_IDENTITY (age -d -i). Klucz prywatny przynieś na czas odtworzenia
  (nie przechowuj go na serwerze produkcyjnym) i usuń po nim.

.EXAMPLE
  .\scripts\restore.ps1 .\backups\rejestr-20261103T020000Z.dump -Storage .\backups\rejestr-20261103T020000Z-storage.tar.gz -Force
  .\scripts\restore.ps1 .\backups\rejestr-20261103T020000Z.dump.age -Storage .\backups\rejestr-20261103T020000Z-storage.tar.gz.age -Identity E:\klucze\rejestr-backup.key -Force
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Dump,
    [string]$Storage,
    [string]$Database = $(if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { 'rejestr' }),
    [string]$Identity = $env:BACKUP_AGE_IDENTITY,
    [switch]$Force,
    [switch]$SkipVerify,
    [switch]$NoChecksum
)

$ErrorActionPreference = 'Stop'

function Invoke-Native {
    param([string]$File, [string[]]$Arguments)
    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Polecenie nie powiodło się ($LASTEXITCODE): $File $($Arguments -join ' ')"
    }
}

function Invoke-Sql {
    param([string]$Db, [string]$Sql)
    $out = & docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -At -d $Db -c $Sql
    if ($LASTEXITCODE -ne 0) { throw "SQL nie powiodło się: $Sql" }
    return ($out | Out-String).Trim()
}

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
    # Binary-safe "From | To" (To = $null: discard the output). The bytes are copied
    # between the processes' streams; a PowerShell pipeline would corrupt them.
    param([string]$From, [string[]]$FromArgs, [string]$To, [string[]]$ToArgs)
    $consumer = $null
    if ($To) { $consumer = Start-NativeProcess $To $ToArgs -RedirectInput }
    try {
        $producer = Start-NativeProcess $From $FromArgs -RedirectOutput
    } catch {
        if ($consumer) { try { $consumer.Kill() } catch { } }
        throw
    }
    $target = if ($consumer) { $consumer.StandardInput.BaseStream } else { [IO.Stream]::Null }
    $copyError = $null
    try {
        $producer.StandardOutput.BaseStream.CopyTo($target)
    } catch {
        # The consumer exited early (broken pipe); stop the producer so it does not block.
        $copyError = $_
        try { if (-not $producer.HasExited) { $producer.Kill() } } catch { }
    } finally {
        if ($consumer) { try { $consumer.StandardInput.Close() } catch { } }
    }
    $producer.WaitForExit()
    if ($consumer) { $consumer.WaitForExit() }
    if ($producer.ExitCode -ne 0) {
        throw "Polecenie nie powiodło się ($($producer.ExitCode)): $From $($FromArgs -join ' ')"
    }
    if ($consumer -and $consumer.ExitCode -ne 0) {
        throw "Polecenie nie powiodło się ($($consumer.ExitCode)): $To $($ToArgs -join ' ')"
    }
    if ($copyError) { throw $copyError }
}

function Test-Encrypted { param([string]$Path) return $Path -like '*.age' }

if ($Database -notmatch '^[a-z0-9_]+$') { throw 'Nazwa bazy: tylko a-z, 0-9, _' }
if ($Dump -notmatch '\.dump(\.age)?$') { throw "Oczekiwany plik *.dump albo *.dump.age: $Dump" }
$Dump = (Resolve-Path $Dump).Path
if ($Storage) { $Storage = (Resolve-Path $Storage).Path }

$encrypted = (Test-Encrypted $Dump) -or ($Storage -and (Test-Encrypted $Storage))
if ($encrypted) {
    if (-not (Get-Command age -CommandType Application -ErrorAction SilentlyContinue)) {
        throw 'Kopia jest zaszyfrowana (*.age), a programu age nie ma w PATH (winget install FiloSottile.age).'
    }
    if (-not $Identity) {
        throw 'Kopia jest zaszyfrowana (*.age): wskaż plik klucza prywatnego age (-Identity PLIK albo BACKUP_AGE_IDENTITY).'
    }
    if (-not (Test-Path -LiteralPath $Identity -PathType Leaf)) { throw "Brak pliku klucza prywatnego: $Identity" }
    $Identity = (Resolve-Path -LiteralPath $Identity).Path
}

# 1. sumy kontrolne -----------------------------------------------------------
if (-not $NoChecksum) {
    $sums = ($Dump -replace '\.dump(\.age)?$', '') + '.sha256'
    if (-not (Test-Path $sums)) { throw "Brak pliku sum kontrolnych $sums (-NoChecksum, aby pominąć)" }
    Write-Host "==> sprawdzam SHA-256 ($sums)"
    $dir = Split-Path $sums
    foreach ($line in (Get-Content $sums | Where-Object { $_.Trim() })) {
        $expected, $name = $line -split '\s+\*?', 2
        $actual = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $dir $name)).Hash.ToLower()
        if ($actual -ne $expected.ToLower()) { throw "Suma SHA-256 się nie zgadza: $name" }
        Write-Host "    ${name}: OK"
    }
}

if ($encrypted) {
    # Trial decryption (output discarded): a wrong key or a damaged file fails here,
    # before the existing database or files are touched.
    foreach ($f in @($Dump, $Storage)) {
        if ($f -and (Test-Encrypted $f)) {
            Write-Host "==> sprawdzam odszyfrowanie $(Split-Path -Leaf $f)"
            try {
                Invoke-NativePipe age @('-d', '-i', $Identity, $f) $null $null
            } catch {
                throw "Nie udało się odszyfrować $f (zły klucz prywatny lub uszkodzony plik)."
            }
        }
    }
}

$dbContainer = (& docker compose ps -q db | Out-String).Trim()
if (-not $dbContainer) { throw 'Usługa db nie działa (docker compose up -d db).' }

foreach ($role in 'app_owner', 'app_rw') {
    if ((Invoke-Sql 'postgres' "SELECT 1 FROM pg_roles WHERE rolname = '$role'") -ne '1') {
        throw "Brak roli ${role}: baza docelowa musi być zainicjalizowana skryptem deploy/postgres/init."
    }
}

# 2. pusta baza ----------------------------------------------------------------
if ((Invoke-Sql 'postgres' "SELECT 1 FROM pg_database WHERE datname = '$Database'") -eq '1') {
    $tables = Invoke-Sql $Database "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"
    if ($tables -ne '0' -and -not $Force) {
        throw "Baza $Database zawiera $tables tabel. Odtworzenie ją USUNIE - użyj -Force (najpierw: docker compose stop api worker web)."
    }
    Write-Host "==> usuwam istniejącą bazę $Database"
    Invoke-Sql 'postgres' "DROP DATABASE $Database WITH (FORCE)" | Out-Null
}
Write-Host "==> tworzę pustą bazę $Database"
Invoke-Sql 'postgres' "CREATE DATABASE $Database TEMPLATE template0 ENCODING 'UTF8' LOCALE 'C.UTF-8'" | Out-Null
foreach ($sql in @(
        "REVOKE ALL ON DATABASE $Database FROM PUBLIC",
        "GRANT CONNECT, TEMPORARY, CREATE ON DATABASE $Database TO app_owner",
        "GRANT CONNECT, TEMPORARY ON DATABASE $Database TO app_rw",
        'REVOKE ALL ON SCHEMA public FROM PUBLIC',
        'ALTER SCHEMA public OWNER TO app_owner',
        'GRANT USAGE ON SCHEMA public TO app_rw')) {
    Invoke-Sql $Database $sql | Out-Null
}

# 3. pg_restore ----------------------------------------------------------------
Write-Host "==> pg_restore $(Split-Path -Leaf $Dump) -> $Database"
$pgRestore = @('compose', 'exec', '-T', 'db', 'pg_restore', '-U', 'postgres', '-d', $Database,
    '--exit-on-error', '--single-transaction')
if (Test-Encrypted $Dump) {
    # Streamed: age -d -> pg_restore stdin (no decrypted dump on disk).
    Invoke-NativePipe age @('-d', '-i', $Identity, $Dump) docker $pgRestore
} else {
    $tmpInContainer = "/tmp/restore-$PID.dump"
    try {
        Invoke-Native docker @('compose', 'cp', $Dump, "db:$tmpInContainer")
        Invoke-Native docker ($pgRestore + @($tmpInContainer))
    } finally {
        try { & docker compose exec -T db rm -f $tmpInContainer *> $null } catch { }
    }
}
$tables = Invoke-Sql $Database "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"
$entries = Invoke-Sql $Database 'SELECT count(*) FROM audit_log'
Write-Host "    tabele: $tables, wpisy audytu: $entries"

# 4. pliki ---------------------------------------------------------------------
if ($Storage) {
    # JSON instead of a Go template with quotes (PowerShell 5.1 mangles embedded quotes).
    $project = ((& docker inspect $dbContainer | Out-String) | ConvertFrom-Json)[0].Config.Labels.'com.docker.compose.project'
    $volume = (& docker volume ls -q --filter "label=com.docker.compose.project=$project" --filter 'label=com.docker.compose.volume=storage' | Out-String).Trim()
    if (-not $volume) {
        $volume = "${project}_storage"
        Invoke-Native docker @('volume', 'create', '--label', "com.docker.compose.project=$project",
            '--label', 'com.docker.compose.volume=storage', $volume) | Out-Null
    }
    $image = (& docker inspect --format '{{.Config.Image}}' $dbContainer | Out-String).Trim()
    $helper = "rejestr-restore-$PID"
    Write-Host "==> odtwarzam pliki do wolumenu $volume"
    if (Test-Encrypted $Storage) {
        # Streamed: age -d -> tar stdin in the helper container.
        Invoke-NativePipe age @('-d', '-i', $Identity, $Storage) docker @('run', '--rm', '-i',
            '-v', "${volume}:/data", $image, 'sh', '-c',
            'find /data -mindepth 1 -delete && tar -C /data -xzf -')
    } else {
        try {
            Invoke-Native docker @('create', '--name', $helper, '-v', "${volume}:/data", $image, 'sh', '-c',
                'find /data -mindepth 1 -delete && tar -C /data -xzf /tmp/storage.tar.gz') | Out-Null
            Invoke-Native docker @('cp', $Storage, "${helper}:/tmp/storage.tar.gz")
            Invoke-Native docker @('start', '-a', $helper)
        } finally {
            try { & docker rm -f $helper *> $null } catch { }
        }
    }
}

# 5. weryfikacja łańcuchów audytu ------------------------------------------------
if (-not $SkipVerify) {
    Write-Host '==> weryfikacja łańcuchów audytu'
    $failed = $false
    $targets = @(, @('--global'))
    $prefixes = Invoke-Sql $Database 'SELECT prefix FROM companies ORDER BY prefix'
    foreach ($p in ($prefixes -split "`r?`n" | Where-Object { $_ })) { $targets += , @('--company', $p) }
    foreach ($t in $targets) {
        # The api image with DATABASE_URL pointed at the restored database (app_rw).
        & docker compose run --rm --no-deps -T -e "RESTORE_DB=$Database" --entrypoint sh api -c `
            'DATABASE_URL=${DATABASE_URL%/*}/$RESTORE_DB exec python -m app.cli verify-audit $@' verify-audit @t
        if ($LASTEXITCODE -ne 0) { $failed = $true }
    }
    if ($failed) { throw 'UWAGA: weryfikacja co najmniej jednego łańcucha nie powiodła się (patrz wyżej).' }
}

Write-Host 'Odtworzenie zakończone. Uruchom aplikację: docker compose up -d'
