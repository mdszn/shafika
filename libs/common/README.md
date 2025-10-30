# common

Shared utilities for Web3 DaaS services (block-poller, processor, api).

## Installation

Install as editable from any service:

```toml
dependencies = [
  "common @ file://../../libs/common",
]
```

Or during local dev:

```bash
pip install -e libs/common
```

## Usage

```python
from common.queue import RedisQueueManager

queue = RedisQueueManager()
queue.push("blocks", "21234567")
block_num = queue.pop("blocks")
```

