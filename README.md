# AFixL

**AFixL** (AFL + Fix + LLM) is an automated code repair framework that integrates fuzz testing and large language models (LLMs) to identify, patch, and validate bugs in C/C++ programs.

---

## 🚀 Features

- 🔍 **Fuzzing with AFL**: Detects vulnerabilities and crashes using American Fuzzy Lop (AFL).
- 🤖 **LLM-Powered Code Repair**: Uses large language models to analyze crash-inducing inputs and suggest code fixes.
- ✅ **Automated Validation**: Verifies the effectiveness of generated patches by re-running fuzz tests and regression inputs.

---

## 📦 Requirements

- Python 3.8+
- AFL++
- clang or gcc (with instrumentation support)
- OpenAI or local LLM API access

---

## 🛠️ Installation

```bash
git clone https://github.com/yourusername/AFixL.git
cd AFixL
pip install -r requirements.txt
```

---

## ⚙️ Usage

```bash
python afixl.py --target /path/to/target/source.c --input seeds/ --model openai
```

### Arguments
- `--target`: Path to the C/C++ source file
- `--input`: Directory of seed inputs for AFL
- `--model`: LLM backend to use (e.g., `openai`, `local-llm`)

---

## 📈 Workflow

1. **Instrument & Compile**: The target source is compiled with instrumentation.
2. **Fuzzing Phase**: AFL generates inputs that trigger crashes or abnormal behavior.
3. **Fault Localization**: Crash logs are analyzed to locate potential bugs.
4. **LLM Repair**: A large language model proposes one or more fixes.
5. **Patch Validation**: Fixed code is recompiled and tested using known crashing inputs and AFL regression.

---

## 🧪 Example

```bash
python afixl.py --target examples/crashme.c --input seeds/ --model openai
```

---

## 🔒 Disclaimer
This tool is experimental and should not be used in production environments without thorough testing.

---

## 📄 License
MIT License

---

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first.

---

## 📫 Contact
Feel free to reach out via [GitHub Issues](https://github.com/yourusername/AFixL/issues) for questions, feedback, or bug reports.

