# Verify the ticket base before delegation or the completed squash in daily main.
[CmdletBinding(DefaultParameterSetName = 'Delegation')]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^(?:[0-9a-f]{40}|[0-9a-f]{64})$')]
    [string]$ExpectedBase,

    [Parameter(Mandatory, ParameterSetName = 'Delegation')]
    [string]$TicketWorktree,

    [Parameter(Mandatory, ParameterSetName = 'Squash')]
    [ValidatePattern('^(?:[0-9a-f]{40}|[0-9a-f]{64})$')]
    [string]$SourceCommit,

    [Parameter(ParameterSetName = 'Squash')]
    [string]$DailyWorktree = 'C:/TOOL/Rhino/mcp/almond-mcp'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath

function Invoke-GitRead([string]$Path, [string[]]$Arguments) {
    $result = & git --no-optional-locks -C $Path @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed in $Path." }
    $result
}

$path = if ($PSCmdlet.ParameterSetName -eq 'Delegation') { $TicketWorktree } else { $DailyWorktree }
$checkout = (Resolve-Path -LiteralPath $path).ProviderPath
$topLevel = Invoke-GitRead $checkout @('rev-parse', '--show-toplevel')
if ((Resolve-Path -LiteralPath $topLevel).ProviderPath -ne $checkout) {
    throw "Specify the worktree root: $topLevel"
}
$common = Invoke-GitRead $repo @('rev-parse', '--path-format=absolute', '--git-common-dir')
$otherCommon = Invoke-GitRead $checkout @('rev-parse', '--path-format=absolute', '--git-common-dir')
if ((Resolve-Path -LiteralPath $common).ProviderPath -ne (Resolve-Path -LiteralPath $otherCommon).ProviderPath) {
    throw "Worktree belongs to another repository: $checkout"
}
$head = Invoke-GitRead $checkout @('rev-parse', '--verify', 'HEAD^{commit}')
if ($PSCmdlet.ParameterSetName -eq 'Delegation') {
    if ($head -ne $ExpectedBase) { throw "Ticket HEAD $head differs from expected $ExpectedBase in $checkout." }
    [pscustomobject]@{ Worktree = $checkout; Head = $head; ExpectedBase = $ExpectedBase }
    return
}

$branch = Invoke-GitRead $checkout @('branch', '--show-current')
if ($branch -cne 'main') { throw "Daily worktree must have main checked out: $checkout" }
$parents = (Invoke-GitRead $checkout @('rev-list', '--parents', '-n', '1', $head)) -split ' '
if ($parents.Count -ne 2 -or $parents[1] -ne $ExpectedBase) {
    throw "main must have exactly one squash commit on the expected base $ExpectedBase."
}
$expectedTree = Invoke-GitRead $repo @('rev-parse', '--verify', "$SourceCommit^{commit}^{tree}")
$tree = Invoke-GitRead $checkout @('rev-parse', '--verify', 'HEAD^{tree}')
if ($tree -ne $expectedTree) { throw "Squash tree $tree differs from source tree $expectedTree." }
if (Invoke-GitRead $checkout @('status', '--porcelain=v1', '--untracked-files=no')) {
    throw "Daily worktree has staged or unstaged changes to tracked files: $checkout"
}
[pscustomobject]@{ Worktree = $checkout; Branch = $branch; Head = $head; Tree = $tree }
