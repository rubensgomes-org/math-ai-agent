"""Executes the math-ai-agent package code at startup

``poetry run python -m math-ai-agent``
"""

# pylint: disable=invalid-name

from math_ai_agent.cli import main

raise SystemExit(main())
