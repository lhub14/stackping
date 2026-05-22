# stackping

Lightweight uptime monitor that reads a YAML service list and sends alerts via webhook.

---

## Installation

```bash
pip install stackping
```

Or clone and install locally:

```bash
git clone https://github.com/yourname/stackping.git && cd stackping && pip install .
```

---

## Usage

Define your services in a `services.yaml` file:

```yaml
services:
  - name: My API
    url: https://api.example.com/health
    interval: 60

  - name: Company Website
    url: https://example.com
    interval: 300

webhook:
  url: https://hooks.slack.com/services/your/webhook/url
```

Then run the monitor:

```bash
stackping --config services.yaml
```

stackping will poll each service at the defined interval (in seconds) and fire a webhook alert if a service becomes unreachable or returns a non-2xx status code.

### Options

| Flag | Description |
|------|-------------|
| `--config` | Path to your YAML config file (default: `services.yaml`) |
| `--timeout` | Request timeout in seconds (default: `10`) |
| `--verbose` | Enable verbose logging |
| `--dry-run` | Validate config and print services without starting the monitor |

---

## Configuration Reference

| Field | Required | Description |
|-------|----------|-------------|
| `services[].name` | Yes | Display name for the service |
| `services[].url` | Yes | URL to poll |
| `services[].interval` | No | Polling interval in seconds (default: `60`) |
| `webhook.url` | No | Webhook URL to receive alert payloads |

---

## License

MIT © 2024 [yourname](https://github.com/yourname)
