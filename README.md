# Pokibot

## Setup


- Run at python3.7 (minimum 3.6 for fstring)

Generate Virtual environment

```bash
cd {pokibot_directory}
python -m venv POKI
```

Activate Environment

```bash
source POKI/bin/activate
```

Setup requirements

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Use an unique authentication token (from Botfahter) in bot.py

```python
def main():
	updater = Updater("specialstring", use_context=True)
```

Run 

```bash
python bot_modified.py
```


Run Server

```bash
python server.py
```



## Quit


Exit Virtual Environment

```bash
deactivate
```
