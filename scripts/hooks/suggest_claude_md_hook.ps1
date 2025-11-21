# Claude Hook: Suggest CLAUDE.md Improvements
# Trigger: SessionEnd, PreCompact
# Purpose: Analyze conversation history and generate CLAUDE.md improvement suggestions
#
# Usage: Called automatically by Claude Hooks with HOOK_PAYLOAD_PATH environment variable
# Output: Saves suggestions to %TEMP%/suggest-claude-md/<session_id>-<timestamp>.md

param(
    [Parameter(Mandatory=$false)]
    [string]$PayloadPath = $env:HOOK_PAYLOAD_PATH
)

# Re-entry prevention
if ($env:SUGGEST_CLAUDE_MD_RUNNING -eq "1") {
    Write-Host "[suggest-claude-md] Already running, skipping to prevent recursion"
    exit 0
}

$env:SUGGEST_CLAUDE_MD_RUNNING = "1"

try {
    # Validate payload path
    if (-not $PayloadPath -or -not (Test-Path $PayloadPath)) {
        Write-Error "[suggest-claude-md] Hook payload not found: $PayloadPath"
        exit 1
    }

    # Parse hook payload JSON
    $payload = Get-Content $PayloadPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $sessionId = $payload.session_id
    $transcriptPath = $payload.transcript_path

    Write-Host "[suggest-claude-md] Processing session: $sessionId"

    # Strategy 1: Use transcript_path from payload
    $conversationLog = $null
    if ($transcriptPath -and (Test-Path $transcriptPath)) {
        Write-Host "[suggest-claude-md] Reading transcript from: $transcriptPath"
        $conversationLog = Get-Content $transcriptPath -Raw -Encoding UTF8
    }
    # Strategy 2: Search for session JSONL in projects directory
    elseif ($sessionId) {
        Write-Host "[suggest-claude-md] Searching for session JSONL: $sessionId"
        $projectsDir = Join-Path $env:USERPROFILE ".claude\projects"
        $sessionFiles = Get-ChildItem -Path $projectsDir -Recurse -Filter "$sessionId.jsonl" -ErrorAction SilentlyContinue

        if ($sessionFiles -and $sessionFiles.Count -gt 0) {
            $sessionFile = $sessionFiles[0].FullName
            Write-Host "[suggest-claude-md] Found session file: $sessionFile"
            $conversationLog = Get-Content $sessionFile -Raw -Encoding UTF8
        }
        # Strategy 3: Fallback to debug log
        else {
            $debugPath = Join-Path $env:USERPROFILE ".claude\debug\$sessionId.txt"
            if (Test-Path $debugPath) {
                Write-Host "[suggest-claude-md] Fallback to debug log: $debugPath"
                $conversationLog = Get-Content $debugPath -Raw -Encoding UTF8
            }
            else {
                Write-Error "[suggest-claude-md] No conversation log found for session: $sessionId"
                exit 1
            }
        }
    }
    else {
        Write-Error "[suggest-claude-md] No session_id or transcript_path in payload"
        exit 1
    }

    # Check if conversation log is too short (likely empty session)
    if ($conversationLog.Length -lt 100) {
        Write-Host "[suggest-claude-md] Conversation too short, skipping analysis"
        exit 0
    }

    # Load template (from project root)
    $projectRoot = Join-Path $PSScriptRoot "..\..\"
    $templatePath = Join-Path $projectRoot ".claude\commands\suggest-claude-md.md"
    if (-not (Test-Path $templatePath)) {
        Write-Error "[suggest-claude-md] Template not found: $templatePath"
        exit 1
    }

    $template = Get-Content $templatePath -Raw -Encoding UTF8

    # Replace placeholder with conversation log
    # Truncate if too long (Claude CLI has token limits)
    $maxLength = 100000  # ~25k tokens
    if ($conversationLog.Length -gt $maxLength) {
        Write-Host "[suggest-claude-md] Truncating conversation log from $($conversationLog.Length) to $maxLength chars"
        $conversationLog = $conversationLog.Substring($conversationLog.Length - $maxLength)
    }

    $prompt = $template -replace '\{\{conversation_log\}\}', $conversationLog

    # Prepare output directory
    $outputDir = Join-Path $env:TEMP "suggest-claude-md"
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir | Out-Null
    }

    # Clean up old files (older than 14 days)
    Get-ChildItem -Path $outputDir -Filter "*.md" -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } |
        Remove-Item -Force

    # Generate output filename
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $outputFile = Join-Path $outputDir "$sessionId-$timestamp.md"

    # Check if Claude CLI is available
    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $claudeCmd) {
        Write-Error "[suggest-claude-md] Claude CLI not found. Please install: https://docs.claude.com"

        # Send warning to Context Orchestrator (if available)
        $contextCmd = Get-Command context-orchestrator -ErrorAction SilentlyContinue
        if ($contextCmd) {
            Write-Host "[suggest-claude-md] Notifying Context Orchestrator of missing Claude CLI"
            # Future: Implement RPC call to Context Orchestrator
        }

        exit 1
    }

    # Execute Claude CLI with the prompt
    Write-Host "[suggest-claude-md] Running Claude CLI analysis..."

    # Save prompt to temp file
    $promptFile = Join-Path $env:TEMP "suggest-claude-md-prompt-$sessionId.txt"
    $prompt | Out-File -FilePath $promptFile -Encoding UTF8 -NoNewline

    # Run Claude in non-interactive mode
    $claudeOutput = & claude -p $promptFile --dangerously-skip-permissions 2>&1

    # Remove temp prompt file
    Remove-Item $promptFile -Force -ErrorAction SilentlyContinue

    # Save output
    $claudeOutput | Out-File -FilePath $outputFile -Encoding UTF8

    Write-Host "[suggest-claude-md] Analysis saved to: $outputFile"
    Write-Host "[suggest-claude-md] Review the suggestions and update CLAUDE.md as needed"

    # Success - output file path for potential post-processing
    Write-Output $outputFile

} catch {
    Write-Error "[suggest-claude-md] Error: $_"
    Write-Error $_.ScriptStackTrace
    exit 1
} finally {
    # Clear re-entry flag
    Remove-Item Env:\SUGGEST_CLAUDE_MD_RUNNING -ErrorAction SilentlyContinue
}
