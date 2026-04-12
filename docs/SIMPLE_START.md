# Quick Start - 3 Commands

## 1. Start Ollama (Terminal 1)

```bash
ollama serve
```

## 2. Pull Models (Terminal 2)

```bash
# You already have gemma3:1b - verify it's there
ollama list | grep gemma3:1b

# Pull vision model (if not already downloaded)
ollama pull llava:7b
```

## 3. Start Backend & Frontend (Terminal 2)

```bash
cd "d:\CAPSTONE\project 10\app"
python main.py
```

Then visit: **http://localhost:8000**

---

## Troubleshooting

### "Address already in use"

```bash
netstat -ano | findstr 8000
taskkill /PID <PID> /F
```

### "Cannot connect to Ollama"

- Make sure `ollama serve` is running in Terminal 1

### "Models not found"

```bash
ollama list
ollama pull llava:7b
ollama pull llama2:7b
```

### Just want to test the API?

```bash
curl -X POST http://localhost:8000/api/health
```
