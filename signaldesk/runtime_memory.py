from __future__ import annotations

import gc


def release_cuda_memory() -> None:
    """Release model references and cached CUDA blocks after a bounded local job."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except (ImportError, RuntimeError):
        # Rule-only and CPU environments must remain valid installations.
        return
