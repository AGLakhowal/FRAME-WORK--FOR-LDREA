# Reproduce E4

```bash
./.venv/bin/python -c "from agentdojo_integration.audit import concurrency_scaling as c; c.run('experiments/stress', 200000, [1, 2, 4, 8, 16, 32, 64])"
```
