import subprocess


def qemu_processes() -> str:
    """Command lines of running QEMU processes (to check nothing is left behind)."""
    result = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, check=True)
    return "\n".join(line for line in result.stdout.splitlines() if "qemu-system" in line)
