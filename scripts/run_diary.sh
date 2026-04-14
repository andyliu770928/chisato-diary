#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${CHISATO_PYTHON_BIN:-$HOME/.hermes/hermes-agent/venv/bin/python}"

# timeout 秒數（macOS 用 perl alarm 實現）
DIARY_TIMEOUT="${DIARY_TIMEOUT:-300}"

# 用 perl alarm 實作 timeout：超時會被 SIGALRM 殺掉
exec perl -e '
    use strict;
    use File::Basename;
    $| = 1;
    my $timeout = $ARGV[0] // 300;
    my @cmd = @ARGV[1..$#ARGV];
    $0 = $cmd[0];  # 程序名稱

    eval {
        local $SIG{ALRM} = sub { die "alarm\n" };
        alarm $timeout;
        exec(@cmd) or die "exec failed: $!\n";
        alarm 0;
    };
    if ($@) {
        if ($@ eq "alarm\n") {
            print STDERR "ERROR: command timed out after ${timeout}s\n";
            exit 124;
        }
        exit 1;
    }
' "$DIARY_TIMEOUT" "$PYTHON_BIN" "$SCRIPT_DIR/generate_diary.py" "$@"
