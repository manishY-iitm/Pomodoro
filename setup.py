from setuptools import setup, find_packages

setup(
    name="pomodoro-productivity-clock",
    version="1.0.0",
    description="Cross-Platform Pomodoro Productivity Clock for Windows, macOS, and Linux",
    author="Antigravity",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # Core timer engine, database, daemon and CLI run with zero third-party dependencies!
    ],
    extras_require={
        "gui": [
            "PyQt6>=6.4.0; platform_system != 'Darwin' or platform_machine != 'arm64'",
            "PyQt6; platform_system == 'Darwin'",
        ],
    },
    entry_points={
        "console_scripts": [
            "pomodoroctl=pomodoro.cli:main",
            "pomodoro-app=pomodoro.app_entry:main",
            "pomodoro-daemon=pomodoro.daemon_entry:main",
        ],
    },
    include_package_data=True,
)
