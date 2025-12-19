"""
Tux Assistant - System Commands

Execute system commands with proper privilege handling.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable, Optional
from enum import Enum


class CommandStatus(Enum):
    """Command execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class CommandResult:
    """Result of a command execution."""
    status: CommandStatus
    return_code: int
    stdout: str
    stderr: str
    command: list[str]
    
    @property
    def success(self) -> bool:
        return self.status == CommandStatus.SUCCESS and self.return_code == 0
    
    @property
    def output(self) -> str:
        """Combined stdout and stderr."""
        return f"{self.stdout}\n{self.stderr}".strip()


def command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(cmd) is not None


def run(
    command: list[str],
    timeout: Optional[int] = None,
    capture_output: bool = True,
    check: bool = False,
    env: Optional[dict] = None,
    cwd: Optional[str] = None
) -> CommandResult:
    """
    Run a command and return the result.
    
    Args:
        command: List of command and arguments
        timeout: Timeout in seconds (None for no timeout)
        capture_output: Whether to capture stdout/stderr
        check: If True, raise exception on non-zero return code
        env: Environment variables (merged with current env)
        cwd: Working directory
    
    Returns:
        CommandResult with status, output, etc.
    """
    # Merge environment if provided
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            env=run_env,
            cwd=cwd
        )
        
        status = CommandStatus.SUCCESS if result.returncode == 0 else CommandStatus.FAILED
        
        return CommandResult(
            status=status,
            return_code=result.returncode,
            stdout=result.stdout if capture_output else '',
            stderr=result.stderr if capture_output else '',
            command=command
        )
    
    except subprocess.TimeoutExpired:
        return CommandResult(
            status=CommandStatus.TIMEOUT,
            return_code=-1,
            stdout='',
            stderr=f'Command timed out after {timeout} seconds',
            command=command
        )
    
    except FileNotFoundError:
        return CommandResult(
            status=CommandStatus.FAILED,
            return_code=-1,
            stdout='',
            stderr=f'Command not found: {command[0]}',
            command=command
        )
    
    except Exception as e:
        return CommandResult(
            status=CommandStatus.FAILED,
            return_code=-1,
            stdout='',
            stderr=str(e),
            command=command
        )


def run_sudo(
    command: list[str],
    timeout: Optional[int] = None,
    capture_output: bool = True
) -> CommandResult:
    """
    Run a command with sudo.
    
    Args:
        command: List of command and arguments (without 'sudo')
        timeout: Timeout in seconds
        capture_output: Whether to capture output
    
    Returns:
        CommandResult
    """
    sudo_command = ['sudo'] + command
    return run(sudo_command, timeout=timeout, capture_output=capture_output)


def run_with_callback(
    command: list[str],
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
    on_complete: Optional[Callable[[CommandResult], None]] = None,
    timeout: Optional[int] = None
) -> threading.Thread:
    """
    Run a command in a background thread with real-time output callbacks.
    
    Useful for long-running commands where you want to show progress.
    
    Args:
        command: List of command and arguments
        on_stdout: Callback for each line of stdout
        on_stderr: Callback for each line of stderr  
        on_complete: Callback when command completes
        timeout: Timeout in seconds
    
    Returns:
        The thread running the command
    """
    def _run():
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # Read stdout in real-time
            def read_stdout():
                for line in process.stdout:
                    line = line.rstrip('\n')
                    stdout_lines.append(line)
                    if on_stdout:
                        on_stdout(line)
            
            # Read stderr in real-time
            def read_stderr():
                for line in process.stderr:
                    line = line.rstrip('\n')
                    stderr_lines.append(line)
                    if on_stderr:
                        on_stderr(line)
            
            # Start reader threads
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process with timeout
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                if on_complete:
                    on_complete(CommandResult(
                        status=CommandStatus.TIMEOUT,
                        return_code=-1,
                        stdout='\n'.join(stdout_lines),
                        stderr=f'Command timed out after {timeout} seconds',
                        command=command
                    ))
                return
            
            # Wait for readers to finish
            stdout_thread.join()
            stderr_thread.join()
            
            # Call completion callback
            if on_complete:
                status = CommandStatus.SUCCESS if process.returncode == 0 else CommandStatus.FAILED
                on_complete(CommandResult(
                    status=status,
                    return_code=process.returncode,
                    stdout='\n'.join(stdout_lines),
                    stderr='\n'.join(stderr_lines),
                    command=command
                ))
        
        except Exception as e:
            if on_complete:
                on_complete(CommandResult(
                    status=CommandStatus.FAILED,
                    return_code=-1,
                    stdout='',
                    stderr=str(e),
                    command=command
                ))
    
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def check_sudo_access() -> bool:
    """Check if we can run sudo without password (or have cached credentials)."""
    result = run(['sudo', '-n', 'true'], timeout=5)
    return result.success


def get_sudo_password_prompt() -> str:
    """Get the sudo password prompt string."""
    return "This operation requires administrator privileges."


# File operations with sudo
def sudo_write_file(path: str, content: str) -> CommandResult:
    """Write content to a file using sudo tee."""
    # Use tee to write with sudo
    result = subprocess.run(
        ['sudo', 'tee', path],
        input=content,
        capture_output=True,
        text=True
    )
    
    status = CommandStatus.SUCCESS if result.returncode == 0 else CommandStatus.FAILED
    return CommandResult(
        status=status,
        return_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        command=['sudo', 'tee', path]
    )


def sudo_append_file(path: str, content: str) -> CommandResult:
    """Append content to a file using sudo tee -a."""
    result = subprocess.run(
        ['sudo', 'tee', '-a', path],
        input=content,
        capture_output=True,
        text=True
    )
    
    status = CommandStatus.SUCCESS if result.returncode == 0 else CommandStatus.FAILED
    return CommandResult(
        status=status,
        return_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        command=['sudo', 'tee', '-a', path]
    )


def sudo_copy(src: str, dest: str) -> CommandResult:
    """Copy a file with sudo."""
    return run_sudo(['cp', src, dest])


def sudo_move(src: str, dest: str) -> CommandResult:
    """Move a file with sudo."""
    return run_sudo(['mv', src, dest])


def sudo_mkdir(path: str, parents: bool = True) -> CommandResult:
    """Create a directory with sudo."""
    cmd = ['mkdir']
    if parents:
        cmd.append('-p')
    cmd.append(path)
    return run_sudo(cmd)


def sudo_chmod(path: str, mode: str) -> CommandResult:
    """Change file permissions with sudo."""
    return run_sudo(['chmod', mode, path])


def sudo_chown(path: str, owner: str, recursive: bool = False) -> CommandResult:
    """Change file ownership with sudo."""
    cmd = ['chown']
    if recursive:
        cmd.append('-R')
    cmd.extend([owner, path])
    return run_sudo(cmd)


def get_terminal_commands(script_path: str) -> list:
    """
    Get list of terminal emulator commands to try.
    
    Returns a list of (name, command_list) tuples for all supported terminals.
    The script_path will be executed in the terminal.
    """
    return [
        # KDE
        ('konsole', ['konsole', '-e', 'bash', script_path]),
        # GNOME (new)
        ('kgx', ['kgx', '-e', 'bash', script_path]),
        ('gnome-console', ['gnome-console', '-e', 'bash', script_path]),
        # GNOME (classic)
        ('gnome-terminal', ['gnome-terminal', '--', 'bash', script_path]),
        # XFCE
        ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash {script_path}']),
        # MATE
        ('mate-terminal', ['mate-terminal', '-e', f'bash {script_path}']),
        # LXQt/LXDE
        ('qterminal', ['qterminal', '-e', 'bash', script_path]),
        ('lxterminal', ['lxterminal', '-e', f'bash {script_path}']),
        # Popular third-party
        ('tilix', ['tilix', '-e', f'bash {script_path}']),
        ('terminator', ['terminator', '-e', f'bash {script_path}']),
        ('alacritty', ['alacritty', '-e', 'bash', script_path]),
        ('kitty', ['kitty', 'bash', script_path]),
        ('foot', ['foot', 'bash', script_path]),
        ('wezterm', ['wezterm', 'start', '--', 'bash', script_path]),
        # Lightweight
        ('sakura', ['sakura', '-e', f'bash {script_path}']),
        ('terminology', ['terminology', '-e', f'bash {script_path}']),
        ('urxvt', ['urxvt', '-e', 'bash', script_path]),
        ('rxvt', ['rxvt', '-e', 'bash', script_path]),
        ('st', ['st', '-e', 'bash', script_path]),
        # Fallback
        ('xterm', ['xterm', '-e', f'bash {script_path}']),
    ]


def find_terminal() -> Optional[str]:
    """Find the first available terminal emulator."""
    terminals = [
        'konsole', 'kgx', 'gnome-console', 'gnome-terminal',
        'xfce4-terminal', 'mate-terminal', 'qterminal', 'lxterminal',
        'tilix', 'terminator', 'alacritty', 'kitty', 'foot', 'wezterm',
        'sakura', 'terminology', 'urxvt', 'rxvt', 'st', 'xterm'
    ]
    for term in terminals:
        if command_exists(term):
            return term
    return None


def run_in_terminal(script_path: str) -> bool:
    """
    Run a script in the first available terminal emulator.
    
    Args:
        script_path: Path to the script to execute
        
    Returns:
        True if terminal was launched, False if no terminal found
    """
    for term_name, term_cmd in get_terminal_commands(script_path):
        if command_exists(term_name):
            try:
                subprocess.Popen(term_cmd)
                return True
            except Exception:
                continue
    return False
